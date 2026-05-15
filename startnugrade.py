from flask import Flask
from flask import request, session, jsonify
from flask import render_template
from nugrade import *
import pandas as pd
import os
import uuid
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
sql_con = sqlite3.connect('data/nugrade_data.db')
options = MetricOptions()
options.set_neutrons()
metrics = grade_many_isotopes(options, sql_con)
plot_script, plot_component = plot_grades(metrics, options)
options_text = options.gen_html_description()
text_report = ""



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
        _session_data[sid] = {'chat_history': [], 'chat_html': ai_chat_history_default}
    return _session_data[sid]




def render_for_particle(particle, options, version, text_report, plot_script, plot_component, options_text):
    if particle == "n":
        template_extender = "neutrons.html"
    elif particle == "p":
        template_extender = "protons.html"
    return render_template(template_extender,
                               options=options,
                               version=version,
                               text_report=text_report,
                               plot_script=plot_script,
                               plot_component=plot_component,
                               ai_chat_history=get_session_data()['chat_html'],
                               options_text=options_text)

@app.route('/')
def index():
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)


def process_base_form():
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
    process_base_form()
    options.required_reaction_channels = []
    if request.form.get('n,tot', False):
        options.required_reaction_channels += [(1, 'N,TOT')]
    if request.form.get('n,el', False):
        options.required_reaction_channels += [(2, 'N,EL')]
    if request.form.get('n,inl', False):
        options.required_reaction_channels += [(3, 'N,INL')]
    if request.form.get('n,g', False):
        options.required_reaction_channels += [(102, 'N,G')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)


@app.route('/generate_protons', methods=['POST'])
def generate_protons():
    options.required_reaction_channels = []
    if request.form.get('p,el', False):
        options.required_reaction_channels += [(2, 'P,EL')]
    if request.form.get('p,inl', False):
        options.required_reaction_channels += [(3, 'P,INL')]
    if request.form.get('p,g', False):
        options.required_reaction_channels += [(102, 'P,G')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)


@app.route('/neutrons')
def set_neutrons():
    options.set_neutrons()
    text_report = ""
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)

@app.route('/protons')
def set_protons():
    options.set_protons()
    text_report = ""
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)


@app.route('/get_report', methods=['POST'])
def get_report():
    report_nuclide = nuclide_symbol_format(request.form['report_nuclide'])
    if report_nuclide in metrics.keys():
        nuclide_metric = metrics[report_nuclide]
        text_report = nuclide_metric.gen_report(options, for_web=True)
    else:
        text_report = "Nuclide not found."
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, options_text)


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
        user_message, metrics=metrics, options=options,
        conversation_history=sdata['chat_history']
    )
    agent_html = f'<div class="agent-message-bubble"><p class="agent-message">{md.render(response_text)}</p></div>'
    sdata['chat_html'] += user_html + agent_html

    return jsonify({'agent_html': agent_html})


if __name__ == '__main__':
    app.run(port=4000,debug=False)