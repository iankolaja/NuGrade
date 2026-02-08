from flask import Flask
from flask import request
from flask import render_template
from nugrade import *


app = Flask(__name__)

version = '0.0.1'
options = MetricOptions()
options.set_neutrons()
metrics = grade_many_isotopes(options)
plot_script, plot_component = plot_grades(metrics, options)
text_report = ""
ai_output = "Get a report for a specific nuclide to generate an AI summary."


def render_for_particle(particle, options, version, text_report, plot_script, plot_component, ai_output):
    if particle == "n":
        return render_template("neutrons.html",
                           options=options,
                           version=version,
                           text_report=text_report,
                           plot_script=plot_script,
                           plot_component=plot_component,
                           ai_output=ai_output)
    elif particle == "p":
        return render_template("protons.html",
                               options=options,
                               version=version,
                               text_report=text_report,
                               plot_script=plot_script,
                               plot_component=plot_component,
                               ai_output=ai_output)

@app.route('/')
def index():
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)




@app.route('/generate_neutrons', methods=['POST'])
def generate_neutrons():
    options.lower_energy = float(request.form['lower_energy'])*1E6
    options.upper_energy = float(request.form['upper_energy'])*1E6
    if request.form.get('energy_coverage_scale', False):
        options.energy_coverage_scale = "linear"
    else:
        options.energy_coverage_scale = "log"
    options.energy_width = float(request.form['energy_width'])

    try:
        evaluation_response = request.form['evaluation-lib']
    except:
        print("Failed to access form evaluation-lib")
        evaluation_response = None
    if evaluation_response == 1 or evaluation_response is None:
        options.evaluation = "endf8"
    if evaluation_response == 2:
        options.evaluation = "endf7-1"

    try:
        scored_response = request.form['scored-metric']
    except:
        print("Failed to access form scored-metric")
        scored_response = None
    if scored_response == 1 or scored_response is None:
        options.scored_metric = "chi_squared"
    if scored_response == 2:
        options.evaluation = "relative_error"

    try:
        weighting_response = request.form['weighting-function']
    except:
        print("Failed to access form weighting-function")
        weighting_response = None

    if weighting_response == 1 or weighting_response is None:
        options.weighting_function = None
    if weighting_response == 2:
        options.weighting_function = "maxwell-boltzmann-room-temp"
    if weighting_response == 3:
        options.weighting_function = "maxwell-boltzmann-320C"
    if weighting_response == 4:
        options.weighting_function = "watt"

    if request.form.get('n,tot', False):
        options.required_reaction_channels += [(1, 'N,TOT')]
    if request.form.get('n,el', False):
        options.required_reaction_channels += [(2, 'N,EL')]
    if request.form.get('n,inl', False):
        options.required_reaction_channels += [(3, 'N,INL')]
    if request.form.get('n,g', False):
        options.required_reaction_channels += [(102, 'N,G')]
    #if bool(request.form['n,p']):
    #    options.required_reaction_channels += [(103, 'N,P')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options.required_reaction_channels = []
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)


@app.route('/generate_protons', methods=['POST'])
def generate_protons():
    options.lower_energy = float(request.form['lower_energy'])*1E6
    options.upper_energy = float(request.form['upper_energy'])*1E6
    if request.form.get('energy_coverage_scale', False):
        options.energy_coverage_scale = "linear"
    else:
        options.energy_coverage_scale = "log"
    options.energy_width = float(request.form['energy_width'])

    try:
        evaluation_response = request.form['evaluation-lib']
    except:
        print("Failed to access form evaluation-lib")
        evaluation_response = None
    if evaluation_response == 1 or evaluation_response is None:
        options.evaluation = "endf8"
    if evaluation_response == 2:
        options.evaluation = "endf7-1"

    try:
        scored_response = request.form['scored-metric']
    except:
        print("Failed to access form scored-metric")
        scored_response = None
    if scored_response == 1 or scored_response is None:
        options.scored_metric = "chi_squared"
    if scored_response == 2:
        options.evaluation = "relative_error"

    try:
        weighting_response = request.form['weighting-function']
    except:
        print("Failed to access form weighting-function")
        weighting_response = None

    if weighting_response == 1 or weighting_response is None:
        options.weighting_function = None
    if weighting_response == 2:
        options.weighting_function = "maxwell-boltzmann-room-temp"
    if weighting_response == 3:
        options.weighting_function = "maxwell-boltzmann-320C"
    if weighting_response == 4:
        options.weighting_function = "watt"

    if request.form.get('p,el', False):
        options.required_reaction_channels += [(2, 'P,EL')]
    if request.form.get('p,inl', False):
        options.required_reaction_channels += [(3, 'P,INL')]
    if request.form.get('p,g', False):
        options.required_reaction_channels += [(102, 'P,G')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options.required_reaction_channels = []
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)


@app.route('/neutrons')
def set_neutrons():
    options.set_neutrons()
    text_report = ""
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)

@app.route('/protons')
def set_protons():
    options.set_protons()
    text_report = ""
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)


@app.route('/get_report', methods=['POST'])
def get_report():
    report_nuclide = str(request.form['report_nuclide'])
    if report_nuclide in metrics.keys():
        nuclide_metric = metrics[report_nuclide]
        text_report = nuclide_metric.gen_report(options, for_web=True)
    else:
        text_report = "Nuclide not found."
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component, ai_output)


if __name__ == '__main__':
    app.run(port=4000,debug=True)