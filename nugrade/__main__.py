from pathlib import Path
from flask import Flask
from flask import request, session, jsonify
from flask import render_template
from . import *
from .ai_agent import NuclearDataAgent
import os
import uuid
import copy
import json
import html as html_lib
from markdown_it import MarkdownIt
import sqlite3

BASE_DIR = Path(__file__).parent.parent
app = Flask(__name__,
            template_folder=str(BASE_DIR / 'templates'),
            static_folder=str(BASE_DIR / 'static'))
app.secret_key = 'nugrade-dev-secret-change-in-prod'

md = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": True,
        "typographer": True,
    }
)

version = '0.0.1'
DB_PATH = str(BASE_DIR / 'data' / 'nugrade_data.db')
CACHE_DB_PATH = str(BASE_DIR / 'data' / 'nugrade_cache.db')

sql_con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
_nuclide_index = load_nuclide_index()

cache_con = sqlite3.connect(CACHE_DB_PATH, check_same_thread=False)
cache_con.executescript("""
    CREATE TABLE IF NOT EXISTS results_cache (
        options_key TEXT PRIMARY KEY,
        plot_script TEXT NOT NULL,
        plot_component TEXT NOT NULL,
        db_mtime REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS report_cache (
        options_key TEXT NOT NULL,
        nuclide TEXT NOT NULL,
        report_html TEXT NOT NULL,
        db_mtime REAL NOT NULL,
        PRIMARY KEY (options_key, nuclide)
    );
""")
cache_con.commit()

# --- Cache helpers (defined before startup so they can be used during init) ---

_session_data = {}
_results_cache = {}
_report_cache = {}

def _db_mtime():
    """Return the source database's modification time, used to invalidate stale cache entries."""
    return os.path.getmtime(DB_PATH) if os.path.isfile(DB_PATH) else 0.0

def _key_to_str(key):
    """Serialise a cache key tuple to a JSON string suitable for use as a SQLite TEXT key."""
    def to_list(obj):
        return [to_list(i) for i in obj] if isinstance(obj, tuple) else obj
    return json.dumps(to_list(list(key)))

def options_cache_key(options):
    """Return a hashable, order-stable tuple representing all fields that affect grading output.

    Derived from MetricOptions.to_dict() so that adding a new field to that method
    automatically includes it in the cache key.
    """
    d = options.to_dict()
    return tuple(sorted(
        (k, tuple(sorted(v)) if isinstance(v, list) else v)
        for k, v in d.items()
    ))

def get_or_compute_grades(options):
    """Return (metrics, plot_script, plot_component) for the given options, using caches.

    Checks the in-memory cache first, then the SQLite plot cache. On a hit, metrics are
    provided as a LazyMetrics instance (computed per nuclide on demand). On a full miss,
    all nuclides are graded and the resulting plot strings are saved to SQLite.
    The cache is automatically invalidated when the source database's mtime changes.
    """
    key = options_cache_key(options)
    if key not in _results_cache:
        key_str = _key_to_str(key)
        mtime = _db_mtime()
        row = cache_con.execute(
            "SELECT plot_script, plot_component FROM results_cache WHERE options_key = ? AND db_mtime = ?",
            (key_str, mtime)
        ).fetchone()
        if row:
            # Plots are cached — compute individual nuclides on demand
            plot_script, plot_component = row
            _results_cache[key] = (LazyMetrics(_nuclide_index, options, sql_con), plot_script, plot_component)
        else:
            metrics = grade_many_isotopes(options, sql_con)
            plot_script, plot_component = plot_grades(metrics, options)
            cache_con.execute(
                "INSERT OR REPLACE INTO results_cache VALUES (?, ?, ?, ?)",
                (key_str, plot_script, plot_component, mtime)
            )
            cache_con.commit()
            _results_cache[key] = (metrics, plot_script, plot_component)
    return _results_cache[key]


def get_or_compute_report(metrics, options, nuclide):
    """Return the HTML report string for a nuclide, using caches.

    Triggers per-nuclide metric computation via metrics[nuclide] if not yet computed.
    Report HTML is cached in SQLite keyed on (options, nuclide) and invalidated by DB mtime.
    Returns 'Nuclide not found.' if the nuclide is not in the metrics index.
    """
    key = (options_cache_key(options), nuclide)
    if key not in _report_cache:
        options_key_str = _key_to_str(options_cache_key(options))
        mtime = _db_mtime()
        if nuclide not in metrics:
            return "Nuclide not found."
        row = cache_con.execute(
            "SELECT report_html FROM report_cache WHERE options_key = ? AND nuclide = ? AND db_mtime = ?",
            (options_key_str, nuclide, mtime)
        ).fetchone()
        if row:
            _report_cache[key] = row[0]
        else:
            report_html = metrics[nuclide].gen_report(options, for_web=True)
            cache_con.execute(
                "INSERT OR REPLACE INTO report_cache VALUES (?, ?, ?, ?)",
                (options_key_str, nuclide, report_html, mtime)
            )
            cache_con.commit()
            _report_cache[key] = report_html
    return _report_cache[key]

# --- Startup defaults ---
# On a warm start, load plots from SQLite and defer metric computation to first request.
# On a cold start, compute everything and seed the cache.

default_options = MetricOptions()
default_options.set_neutrons()
_default_key = options_cache_key(default_options)
_default_key_str = _key_to_str(_default_key)
_startup_mtime = _db_mtime()

_cached_defaults = cache_con.execute(
    "SELECT plot_script, plot_component FROM results_cache WHERE options_key = ? AND db_mtime = ?",
    (_default_key_str, _startup_mtime)
).fetchone()

if _cached_defaults:
    print("Loaded default plots from cache. Metrics will be computed on first request.")
    default_metrics = None
    default_plot_script, default_plot_component = _cached_defaults
else:
    print("No cache found. Computing default grades...")
    default_metrics = grade_many_isotopes(default_options, sql_con)
    default_plot_script, default_plot_component = plot_grades(default_metrics, default_options)
    cache_con.execute(
        "INSERT OR REPLACE INTO results_cache VALUES (?, ?, ?, ?)",
        (_default_key_str, default_plot_script, default_plot_component, _startup_mtime)
    )
    cache_con.commit()
    _results_cache[_default_key] = (default_metrics, default_plot_script, default_plot_component)

default_options_text = default_options.gen_html_description()


if os.path.isfile(str(BASE_DIR / 'keys' / 'claude.txt')):
    with open(str(BASE_DIR / 'keys' / 'claude.txt'), "r") as f:
        anthropic_api_key = f.read()
    try:
        claude_agent = NuclearDataAgent(api_key=anthropic_api_key)
        ai_available = True
    except:
        print("Access to Claude failed. Is your key correct, and "+\
            " are you connected to the internet?")
        ai_available = False
else:
    print("No API key found in keys/claude.txt for Claude.")
    ai_available = False

if ai_available:
    print("Connected to Claude.")
else:
    print("AI overview will not be available.")

ai_chat_history_default = (
    "<p class='agent-message'>Ask me anything about the nuclear data loaded in NuGrade.</p>"
    if ai_available else
    "<p class='agent-message'>Claude API access failed. AI summary not available.</p>"
)


def get_session_data():
    sid = session.get('_sid')
    if not sid or sid not in _session_data:
        sid = str(uuid.uuid4())
        session['_sid'] = sid
        _session_data[sid] = {
            'options': copy.deepcopy(default_options),
            'metrics': default_metrics,
            'plot_script': default_plot_script,
            'plot_component': default_plot_component,
            'options_text': default_options_text,
            'text_report': '',
            'chat_history': [],
            'chat_html': ai_chat_history_default,
        }
    return _session_data[sid]


def render_for_particle():
    sdata = get_session_data()
    particle = sdata['options'].projectile
    template = "neutrons.html" if particle == "n" else "protons.html"
    return render_template(template,
                           options=sdata['options'],
                           version=version,
                           text_report=sdata['text_report'],
                           plot_script=sdata['plot_script'],
                           plot_component=sdata['plot_component'],
                           ai_chat_history=sdata['chat_html'],
                           options_text=sdata['options_text'])


@app.route('/')
def index():
    sdata = get_session_data()
    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


def process_base_form(options):
    options.lower_energy = float(request.form['lower_energy'])
    options.upper_energy = float(request.form['upper_energy'])
    print(request.form.get('energy_coverage_scale', False))
    if request.form.get('energy_coverage_scale', False):
        options.energy_coverage_scale = "log"
    else:
        options.energy_coverage_scale = "linear"
    options.energy_width = float(request.form['energy_width'])

    try:
        evaluation_response = request.form['evaluation-lib']
    except:
        print("Failed to access form evaluation-lib")
        evaluation_response = None
    if evaluation_response == "1" or evaluation_response is None:
        options.evaluation = "endf8"
    if evaluation_response == "2":
        options.evaluation = "endf7-1"

    try:
        scored_response = request.form['scored-metric']
    except:
        print("Failed to access form scored-metric")
        scored_response = None
    if scored_response == "1" or scored_response is None:
        options.scored_metric = "chi_squared"
    if scored_response == "2":
        options.scored_metric = "relative_error"

    try:
        weighting_response = request.form['weighting-function']
    except:
        print("Failed to access form weighting-function")
        weighting_response = None

    if weighting_response == "1" or weighting_response is None:
        options.weighting_function = None
    if weighting_response == "2":
        options.weighting_function = "maxwell-boltzmann-room-temp"
    if weighting_response == "3":
        options.weighting_function = "maxwell-boltzmann-320C"
    if weighting_response == "4":
        options.weighting_function = "watt"


@app.route('/generate_neutrons', methods=['POST'])
def generate_neutrons():
    sdata = get_session_data()
    process_base_form(sdata['options'])
    sdata['options'].required_reaction_channels = []
    if request.form.get('n,tot', False):
        sdata['options'].required_reaction_channels += [(1, 'N,TOT')]
    if request.form.get('n,el', False):
        sdata['options'].required_reaction_channels += [(2, 'N,EL')]
    if request.form.get('n,inl', False):
        sdata['options'].required_reaction_channels += [(3, 'N,INL')]
    if request.form.get('n,g', False):
        sdata['options'].required_reaction_channels += [(102, 'N,G')]

    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/generate_protons', methods=['POST'])
def generate_protons():
    sdata = get_session_data()
    process_base_form(sdata['options'])
    sdata['options'].required_reaction_channels = []
    if request.form.get('p,el', False):
        sdata['options'].required_reaction_channels += [(2, 'P,EL')]
    if request.form.get('p,inl', False):
        sdata['options'].required_reaction_channels += [(3, 'P,INL')]
    if request.form.get('p,g', False):
        sdata['options'].required_reaction_channels += [(102, 'P,G')]

    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/neutrons')
def set_neutrons():
    sdata = get_session_data()
    sdata['options'].set_neutrons()
    sdata['text_report'] = ""
    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/protons')
def set_protons():
    sdata = get_session_data()
    sdata['options'].set_protons()
    sdata['text_report'] = ""
    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/get_report', methods=['POST'])
def get_report():
    sdata = get_session_data()
    report_nuclide = nuclide_symbol_format(request.form['report_nuclide'])
    sdata['text_report'] = get_or_compute_report(sdata['metrics'], sdata['options'], report_nuclide)
    sdata['metrics'], sdata['plot_script'], sdata['plot_component'] = get_or_compute_grades(sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form.get('user_message', '').strip()
    if not user_message:
        return jsonify({'error': 'empty'}), 400
    if not ai_available:
        return jsonify({'agent_html': "<p class='agent-message'>AI is not available.</p>"})

    sdata = get_session_data()

    user_html = f'<div class="user-message-bubble"><p class="user-message">{html_lib.escape(user_message)}</p></div>'

    response_text, sdata['chat_history'] = claude_agent.chat(
        user_message, metrics=sdata['metrics'], options=sdata['options'],
        conversation_history=sdata['chat_history']
    )
    agent_html = f'<div class="agent-message-bubble"><p class="agent-message">{md.render(response_text)}</p></div>'
    sdata['chat_html'] += user_html + agent_html

    return jsonify({'agent_html': agent_html})


def main():
    app.run(port=4000, debug=False)


if __name__ == '__main__':
    main()
