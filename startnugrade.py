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


def render_for_particle(particle, options, version, text_report, plot_script, plot_component):
    if particle == "n":
        return render_template("neutrons.html",
                           options=options,
                           version=version,
                           text_report=text_report,
                           plot_script=plot_script,
                           plot_component=plot_component)
    elif particle == "p":
        return render_template("protons.html",
                               options=options,
                               version=version,
                               text_report=text_report,
                               plot_script=plot_script,
                               plot_component=plot_component)

@app.route('/')
def index():
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)




@app.route('/generate_neutrons', methods=['POST'])
def generate_neutrons():
    options.lower_energy = float(request.form['lower_energy'])*1E6
    options.upper_energy = float(request.form['upper_energy'])*1E6
    options.energy_width = float(request.form['energy_width'])

    try:
        evaluation_response = request.form['evaluation-lib']
    except:
        print("Failed to access form evaluation-lib")
        evaluation_response = None
    if evaluation_response == 1 or evaluation_response is None:
        options.evaluation = "endfb8.0"
    if evaluation_response == 2:
        options.evaluation = "jeff3.3"

    try:
        scored_response = request.form['scored-metric']
    except:
        print("Failed to access form scored-metric")
        scored_response = None
    if scored_response == 1 or scored_response is None:
        options.scored_metric = "chi-squared"
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

    if bool(request.form['n,tot']):
        options.required_reaction_channels += [(1, 'N,TOT')]
    if bool(request.form['n,el']):
        options.required_reaction_channels += [(2, 'N,EL')]
    if bool(request.form['n,inl']):
        options.required_reaction_channels += [(3, 'N,INL')]
    if bool(request.form['n,g']):
        options.required_reaction_channels += [(102, 'N,G')]
    #if bool(request.form['n,p']):
    #    options.required_reaction_channels += [(103, 'N,P')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options.required_reaction_channels = []
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)


@app.route('/generate_protons', methods=['POST'])
def generate_protons():
    options.lower_energy = float(request.form['lower_energy'])*1E6
    options.upper_energy = float(request.form['upper_energy'])*1E6
    options.energy_width = float(request.form['energy_width'])

    try:
        evaluation_response = request.form['evaluation-lib']
    except:
        print("Failed to access form evaluation-lib")
        evaluation_response = None
    if evaluation_response == 1 or evaluation_response is None:
        options.evaluation = "endf8"
    if evaluation_response == 2:
        options.evaluation = "endf7_1"

    try:
        scored_response = request.form['scored-metric']
    except:
        print("Failed to access form scored-metric")
        scored_response = None
    if scored_response == 1 or scored_response is None:
        options.scored_metric = "chi-squared"
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

    if bool(request.form['p,el']):
        options.required_reaction_channels += [(2, 'P,EL')]
    if bool(request.form['p,inl']):
        options.required_reaction_channels += [(3, 'P,INL')]
    if bool(request.form['p,g']):
        options.required_reaction_channels += [(102, 'P,G')]

    metrics = grade_many_isotopes(options)
    plot_script, plot_component = plot_grades(metrics, options)
    options.required_reaction_channels = []
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)


@app.route('/neutrons')
def set_neutrons():
    options.set_neutrons()
    text_report = ""
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)

@app.route('/protons')
def set_protons():
    options.set_protons()
    text_report = ""
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)


@app.route('/get_report', methods=['POST'])
def get_report():
    report_nuclide = str(request.form['report_nuclide'])
    if report_nuclide in metrics.keys():
        nuclide_metric = metrics[report_nuclide]
        text_report = nuclide_metric.gen_report(options, for_web=True)
    else:
        text_report = "Nuclide not found."
    return render_for_particle(options.projectile, options, version,
                               text_report, plot_script, plot_component)


if __name__ == '__main__':
    app.run(port=4000)