from .nuclide import Nuclide
from bokeh.models import ColumnDataSource, LabelSet, CategoricalColorMapper
from bokeh.plotting import figure, show
from bokeh.embed import components
from bokeh.palettes import inferno
import numpy as np
import pandas as pd


def grade_isotope(Z, A, symbol, options):
    nuc = Nuclide(int(Z), int(A), symbol)
    nuc.get_metrics(options)
    return nuc


def grade_many_isotopes(options):
    all_isotopes = pd.read_csv("data/all_reactions.csv")
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


def _get_rgb(fit, denominator_weight=0.2):
    if fit == 0 or np.isnan(fit):
        marker = (0.0, 0.0, 0.0, 1.0)
    else:
        marker = (30, 255*fit/(fit+denominator_weight), 30)
    text = (225, 1-marker[1], 225, 1.0)
    return marker, text


def plot_grades(metrics, options, show_plot=False):
    n_vals = []
    z_vals = []
    data_scores = []
    nuclide_colors = []
    nuclide_labels = []
    energy_coverage_labels = []
    average_absolute_relative_error_labels = []
    text_colors = []

    for metric in metrics.values():
        N = metric.N
        Z = metric.Z
        if options.scored_channel in metric.reactions.keys():
            fit = metric.reactions[options.scored_channel].score
            energy_coverage = "{0}%".format(np.round(
                metric.reactions[options.scored_channel].energy_coverage,1))
            average_absolute_relative_error = "{0}%".format(np.round(
                metric.reactions[options.scored_channel].average_absolute_relative_error,1))
        else:
            fit = np.nan
            energy_coverage = "0%"
            average_absolute_relative_error = "N/A"
        if np.isnan(fit):
            data_scores += [0.0]
            energy_coverage = "0%"
            average_absolute_relative_error = "N/A"
        else:
            data_scores += [fit]
        color_codes = _get_rgb(fit)
        nuclide_text = str(metric.A) + metric.symbol
        nuclide_rgb = color_codes[0]
        text_rgb = color_codes[1]

        n_vals += [N]
        z_vals += [Z]
        nuclide_colors += [nuclide_rgb]
        text_colors += [text_rgb]
        nuclide_labels += [nuclide_text]
        energy_coverage_labels += [energy_coverage]
        average_absolute_relative_error_labels += [average_absolute_relative_error]

    source = ColumnDataSource(data=dict(n_vals=n_vals, z_vals=z_vals, scores=data_scores, nuclide_colors=nuclide_colors,
                                        text_colors=text_colors, nuclide_labels=nuclide_labels,
                                        energy_coverage=energy_coverage_labels,
                                        average_absolute_relative_error=average_absolute_relative_error_labels))

    tooltip_format = [
        ("Nuclide", "@nuclide_labels"),
        ("Data Score", "@scores"),
        ("Energy Coverage", "@energy_coverage"),
        ("Relative Error", "@average_absolute_relative_error")
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


