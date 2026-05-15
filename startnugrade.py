from flask import Flask
from flask import request, session, jsonify
from flask import render_template
from nugrade import *
import pandas as pd
import os
import uuid
import copy
import html as html_lib
from anthropic import Anthropic
from nugrade.ai_agent import NuclearDataAgent
from markdown_it import MarkdownIt
import sqlite3

app = Flask(__name__)
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
sql_con = sqlite3.connect('data/nugrade_data.db', check_same_thread=False)
default_options = MetricOptions()
default_options.set_neutrons()
default_metrics = grade_many_isotopes(default_options, sql_con)
default_plot_script, default_plot_component = plot_grades(default_metrics, default_options)
default_options_text = default_options.gen_html_description()


if os.path.isfile("keys/claude.txt"):
    with open("keys/claude.txt","r") as f:
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

_session_data = {}

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
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
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

    sdata['metrics'] = grade_many_isotopes(sdata['options'], sql_con)
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
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

    sdata['metrics'] = grade_many_isotopes(sdata['options'], sql_con)
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/neutrons')
def set_neutrons():
    sdata = get_session_data()
    sdata['options'].set_neutrons()
    sdata['text_report'] = ""
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/protons')
def set_protons():
    sdata = get_session_data()
    sdata['options'].set_protons()
    sdata['text_report'] = ""
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
    sdata['options_text'] = sdata['options'].gen_html_description()
    return render_for_particle()


@app.route('/get_report', methods=['POST'])
def get_report():
    sdata = get_session_data()
    report_nuclide = nuclide_symbol_format(request.form['report_nuclide'])
    if report_nuclide in sdata['metrics'].keys():
        sdata['text_report'] = sdata['metrics'][report_nuclide].gen_report(sdata['options'], for_web=True)
    else:
        sdata['text_report'] = "Nuclide not found."
    sdata['plot_script'], sdata['plot_component'] = plot_grades(sdata['metrics'], sdata['options'])
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


if __name__ == '__main__':
    app.run(port=4000, debug=False)
