from nugrade import *
import unittest
import pandas as pd
from nugrade import *

class TestDefaultPlot(unittest.TestCase):
    def test_generate_default_plot(self):
        options = MetricOptions()
        options.set_neutrons()
        metrics = grade_many_isotopes(options)
        plot_script, plot_component = plot_grades(metrics, options)

        with open("data/default_plot_script.html", "w") as f:
            f.write(plot_script)

        with open("data/default_plot_component.html", "w") as f:
            f.write(plot_component)