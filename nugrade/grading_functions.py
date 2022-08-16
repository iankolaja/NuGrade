import re
from .nuclide import Nuclide
import matplotlib.pyplot as plt


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
    if fit == 0:
        marker = (0.0, 0.0, 0.0)
    elif fit >= 1:
        adjust = (1-overflow_thresh)*fit/(10+fit)
        marker = (0.1, overflow_thresh + adjust, 0.1)
    else:
        marker = (0.1, overflow_thresh*fit, 0.1)
    text = (1-marker[0], 1-marker[1], 1.0)
    return marker, text


def plot_grades(metrics, options):
    z_bound = 14
    n_bound = 10
    width_inches = 15
    box_size = (15*100/z_bound/2)**2
    fig = plt.figure()
    fig.set_figwidth(width_inches), fig.set_figheight(width_inches*n_bound/z_bound)
    ax = fig.add_subplot(111)
    ax.set_xlim(-0.5, z_bound+0.5)
    ax.set_ylim(-0.5, n_bound+0.5)
    ax.set_xlabel("Z")
    ax.set_ylabel("N")
    ax.set_xticks(range(0, z_bound+1))
    ax.set_yticks(range(0, n_bound+1))
    for metric in metrics.values():
        N = metric.N
        Z = metric.Z
        fit = metric.application_fit
        symbol = metric.symbol + str(metric.A)
        marker_rgb, text_rgb = _get_rgb(fit)
        ax.scatter(N, Z, color=marker_rgb, marker="s", s=box_size)
        ax.annotate(symbol,  # this is the text
                    (N, Z),  # these are the coordinates to position the label
                    color= text_rgb,
                    textcoords="offset points",  # how to position the text
                    xytext=(0, 0),  # distance from text to points (x,y)
                    ha='center', va="center")  # horizontal alignment can be left, right or center
    plt.show()
