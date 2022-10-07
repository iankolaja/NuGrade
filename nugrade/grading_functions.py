import re
from .nuclide import Nuclide
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.plotting import figure, show
from bokeh.embed import components
import numpy as np


def grade_isotope(exfor_data, isotope, options):
    A = re.findall('[0-9]+', isotope)[0]
    symbol = isotope.replace(A, "")
    isotope_data = exfor_data.loc[exfor_data['Isotope'] == isotope]
    Z = isotope_data.sample()['Z'].item()
    nuc = Nuclide(int(Z), int(A), symbol)
    nuc.get_metrics(isotope_data, options)
    return nuc


def grade_many_isotopes(exfor_data, options, num_to_grade = None):
    isotope_array = exfor_data.Isotope.unique()
    metrics = {}
    if num_to_grade is None:
        num_to_grade = len(isotope_array)
    for i in range(num_to_grade):
        isotope = isotope_array[i]
        if isotope == "Heavy Water":
            continue
        print("Evaluating {0}...".format(isotope))
        metrics[isotope] = grade_isotope(exfor_data, isotope, options)
    return metrics


def _get_rgb(fit, overflow_thresh = 0.7):
    if fit <= 0 or np.isnan(fit):
        marker = (0.0, 0.0, 0.0, 1.0)
    elif fit >= 10:
        marker = (25, 255, 25, 1.0)
    elif fit >= 1:
        adjust = 255*(1-overflow_thresh)*fit/(10+fit)
        marker = (25, overflow_thresh + adjust, 25, 1.0)
    else:
        marker = (25, 255*overflow_thresh*fit, 25)
    text = (255-marker[0], 255-marker[1], 255, 1.0)
    return marker, text


def plot_grades(metrics, show_plot=False):
    n_vals = []
    z_vals = []
    data_scores = []
    nuclide_colors = []
    nuclide_labels = []
    text_colors = []

    for metric in metrics.values():
        N = metric.N
        Z = metric.Z
        fit = metric.application_fit
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

    source = ColumnDataSource(data=dict(n_vals=n_vals, z_vals=z_vals, scores=data_scores, nuclide_colors=nuclide_colors,
                                        text_colors=text_colors, nuclide_labels=nuclide_labels))

    tooltip_format = [
        ("Nuclide", "@nuclide_labels"),
        ("Data Score", "@scores")
    ]

    labels = LabelSet(x='n_vals', y='z_vals', text='nuclide_labels', text_color='text_colors',
                      x_offset=0, y_offset=0, render_mode='canvas', source=source, text_align='center',
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


def plot_precision_data(nuclide_metric, show_plot=False):
    source = ColumnDataSource(data=dict(error_energies=nuclide_metric.error_energies,
                                        relative_error=nuclide_metric.relative_error))
    plot_y_bound = np.max(np.abs(nuclide_metric.relative_error))*1.05
    x_lower_bound = np.min((nuclide_metric.error_energies,nuclide_metric.chi_energies))
    x_upper_bound = np.max((nuclide_metric.error_energies, nuclide_metric.chi_energies))
    tooltip_format = [
        ("Energy (eV)", "@error_energies"),
        ("Relative Error (%)", "@relative_error")
    ]

    p = figure(width=600, height=250, y_range=(-plot_y_bound, plot_y_bound),
               x_range=(x_lower_bound, x_upper_bound),
               tools="pan,wheel_zoom,box_zoom,reset,hover",
               x_axis_type="log", sizing_mode="scale_both", tooltips=tooltip_format)
    p.circle('error_energies', 'relative_error', size=3,
             color="navy", source=source)
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Relative Uncertainty (%)'
    p.border_fill_color = "#f1f1f1"
    script1, div1 = components(p)



    source = ColumnDataSource(data=dict(chi_energies=nuclide_metric.chi_energies,
                                        chi_squared_values=nuclide_metric.chi_squared_values))
    tooltip_format = [
        ("Energy (eV)", "@chi_energies"),
        ("Chi Squared", "@chi_squared_values")
    ]

    p = figure(width=600, height=250, y_range=(0, 1),
               x_range=(x_lower_bound, x_upper_bound),
               tools="pan,wheel_zoom,box_zoom,reset,hover",
               x_axis_type="log", sizing_mode="scale_both", tooltips=tooltip_format)
    p.circle('chi_energies', 'chi_squared_values', size=3,
             color="navy", source=source)
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Chi Squared'
    p.border_fill_color = "#f1f1f1"
    script2, div2 = components(p)

    if show_plot:
        show(p)
    return script1+script2, div1+div2
