from .nuclide import Nuclide
from bokeh.models import ColumnDataSource, LabelSet, CategoricalColorMapper, Div
from bokeh.plotting import figure, show
from bokeh.embed import components
from bokeh.palettes import inferno
from bokeh.layouts import column
import numpy as np
import pandas as pd
import re 

def nuclide_symbol_format(input_nuclide):
    input_str = str(input_nuclide).replace(" ","")
    if "-" in input_str:
        input_split = input_str.split("-")
        symbol = input_split[0]
        A = input_split[1]
    else:
        symbol = re.sub(r'[0-9]+', '', input_str) 
        filtered_chars = filter(str.isdigit, input_str)
        A = ''.join(filtered_chars)
    return f"{A}{symbol.title()}"

def grade_isotope(Z, A, symbol, options):
    nuc = Nuclide(int(Z), int(A), symbol)
    nuc.get_metrics(options)
    return nuc


def grade_many_isotopes(options):
    all_reactions = pd.read_csv("data/all_reactions.csv")
    all_isotopes = all_reactions[["Z","A","Symbol"]].drop_duplicates()
    metrics = {}
    for index, row in all_isotopes.iterrows():
        z_val = row["Z"]
        a_val = row["A"]
        symbol = row["Symbol"]
        if symbol == "Heavy Water" or symbol == "n" or a_val == 0:
            continue
        isotope = str(a_val)+symbol
        print("Evaluating {0}...".format(isotope))
        this_metric = grade_isotope(z_val, a_val, symbol, options)
        if len(this_metric.reactions.keys()) > 0:
            metrics[isotope] = this_metric
    return metrics


def _get_rgb(score, q5, q95):
    if np.isnan(score):
        marker = (30.0, 0.0, 30.0, 1.0)
    else:
        percentile_norm = (score-q5)/(q95-q5)
        scale = np.clip(percentile_norm,0,1)
        marker = (30, 255*scale, 30)
    text = (225, 1-marker[1], 225, 1.0)
    return marker, text


def plot_grades(metrics, options, show_plot=False):
    n_vals = []
    z_vals = []
    score_values = []
    score_labels = []
    nuclide_colors = []
    nuclide_labels = []
    energy_coverage_labels = []
    metric_labels = []
    metric_values = []
    text_colors = []

    for metric in metrics.values():
        N = metric.N
        Z = metric.Z

        # If grading multiple reactions, average together the energy coverage,
        # metric, and overall score for each reaction.
        nuclide_score_list = []
        nuclide_metric_list = []
        nuclide_energy_coverage_list = []
        for scored_channel in options.required_reaction_channels:
            reaction_name = scored_channel[1]
            reaction_score = metric.reactions[reaction_name].score
            reaction_metric = metric.reactions[reaction_name].average_metric
            reaction_energy_coverage = metric.reactions[reaction_name].energy_coverage

            nuclide_score_list += [metric.reactions[reaction_name].score]
            nuclide_metric_list += [reaction_metric]
            nuclide_energy_coverage_list += [reaction_energy_coverage]

        nuclide_mean_score = np.mean(nuclide_score_list)
        nuclide_mean_metric = np.mean(nuclide_metric_list)
        nuclide_mean_energy_coverage = np.mean(nuclide_energy_coverage_list)
        nuclide_text = str(metric.A) + metric.symbol

        n_vals += [N]
        z_vals += [Z]

        # Store values and prepare corresponding labels
        nuclide_labels += [nuclide_text]
        energy_coverage_labels += [str(round(nuclide_mean_energy_coverage,2))]

        metric_values += [nuclide_mean_metric]
        metric_labels += [str(round(nuclide_mean_metric,2))]

        score_values += [nuclide_mean_score]
        score_labels += [str(round(nuclide_mean_score,2))]

    score_q05 = np.quantile(score_values, 0.05)
    score_q95 = np.quantile(score_values, 0.95)
    for i in range(len(score_values)):
        color_codes = _get_rgb(score_values[i], score_q05, score_q95)
        nuclide_rgb = color_codes[0]
        text_rgb = color_codes[1]
        nuclide_colors += [nuclide_rgb]
        text_colors += [text_rgb]

    source = ColumnDataSource(data=dict(n_vals=n_vals, z_vals=z_vals, scores=score_labels, nuclide_colors=nuclide_colors,
                                        text_colors=text_colors, nuclide_labels=nuclide_labels,
                                        energy_coverage=energy_coverage_labels,
                                        metrics=metric_labels))

    tooltip_format = [
        ("Nuclide", "@nuclide_labels"),
        ("Overall Score", "@scores"),
        ("Energy Coverage", "@energy_coverage"),
        (options.get_metric_text(), "@metrics")
    ]

    labels = LabelSet(x='n_vals', y='z_vals', text='nuclide_labels', text_color='text_colors',
                      x_offset=0, y_offset=0, source=source, text_align='center',
                      text_baseline='middle', text_font_size='13px')
    p = figure(x_range=(-0.5, 15.5), y_range=(-0.5, 10.5), sizing_mode="scale_both", width=750, height=500,
               tools=("pan","hover"), toolbar_location=None, tooltips=tooltip_format)  # ,zoom_in,zoom_out,wheel_zoom,reset")
    p.circle('n_vals', 'z_vals', radius=0.5, color='nuclide_colors', source=source)
    # p.square('n_vals', 'z_vals', size=50, color='nuclide_colors', source=source)
    p.add_layout(labels)
    p.xaxis[0].axis_label = 'Number of Neutrons (N)'
    p.yaxis[0].axis_label = 'Number of Protons (Z)'

    script, div = components(p)
    if show_plot:
        show(p)
    return script, div


