from flask import Flask
from flask import request, session
from flask import render_template
from nugrade import *
import pandas as pd
import os
from anthropic import Anthropic
from nugrade.ai_agent import NuclearDataAgent
from markdown_it import MarkdownIt

app = Flask(__name__)

md = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": True,
        "typographer": True,
    }
)

version = '0.0.1'
options = MetricOptions()
options.set_neutrons()
metrics = grade_many_isotopes(options)
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
    ai_chat_history = "Get a report for a specific nuclide to generate an AI summary."
    print("Connected to Claude.")
else:
    print("AI overview will not be available.")
    ai_chat_history = "Claude API access failed. AI summary not available."

if ai_available:
    chat_history = []
    response, chat_history = claude_agent.chat("How good is the 7Li (N,G) cross section for FHR design work?",conversation_history=chat_history,metrics=metrics, options=options)
    print(response)
    ai_chat_history = "<div class=\"user-message-bubble\"><p class=\"user-message\"> How good is the 7Li (N,G) cross section for FHR design work?</p></div>"
    formatted_response = md.render(response)
    #formatted_response = md.render("Here is some exmaple response text.")
    ai_chat_history += f"<p class=\"agent-message\"> {formatted_response}|safe </p>"




def render_for_particle(particle, options, version, text_report, plot_script, plot_component, ai_chat_history, options_text):
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
                               ai_chat_history=ai_chat_history,
                               options_text=options_text)

@app.route('/')
def index():
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_chat_history, options_text)


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
                               text_report, plot_script, plot_component, ai_chat_history, options_text)


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
                               text_report, plot_script, plot_component, ai_chat_history, options_text)


@app.route('/neutrons')
def set_neutrons():
    options.set_neutrons()
    text_report = ""
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_chat_history, options_text)

@app.route('/protons')
def set_protons():
    options.set_protons()
    text_report = ""
    plot_script, plot_component = plot_grades(metrics, options)
    options_text = options.gen_html_description()
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_chat_history, options_text)


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
                               text_report, plot_script, plot_component, ai_chat_history, options_text)


if __name__ == '__main__':
    app.run(port=4000,debug=False)