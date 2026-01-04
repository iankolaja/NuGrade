from nugrade import *
import unittest
import pandas as pd
from nugrade.calc_energy_coverage import calc_energy_coverage

class TestEnergyCoverage(unittest.TestCase):
    def test_energy_coverage_linear(self):
        options = MetricOptions()
        options.lower_energy = 0.0
        options.upper_energy = 1.0
        options.energy_width = 0.2
        options.energy_coverage_scale = "linear"

        energy_grid_1 = pd.DataFrame({"Energy": [0.2, 0.25, 0.55, 0.7, 0.95]})
        calculated_coverage_1 = calc_energy_coverage(energy_grid_1, options)
        expected_coverage_1 = 75
        self.assertEqual(calculated_coverage_1, expected_coverage_1)

    def test_energy_coverage_log(self):
        options = MetricOptions()
        options.lower_energy = 1E1
        options.upper_energy = 1E5
        options.energy_width = 0.5
        options.energy_coverage_scale = "log"

        energy_grid_2 = pd.DataFrame({"Energy": [1.0E2, 1.0E3, 1.0E4]})
        calculated_coverage_2 = calc_energy_coverage(energy_grid_2, options)

        expected_coverage_2 = 37.5
        self.assertEqual(calculated_coverage_2, expected_coverage_2)

    def test_energy_coverage_sort(self):
        options = MetricOptions()
        options.lower_energy = 0.0
        options.upper_energy = 1.0
        options.energy_width = 0.2
        options.energy_coverage_scale = "linear"

        energy_grid_1 = pd.DataFrame({"Energy": [0.2, 0.95, 0.55, 0.25, 0.7]})
        try:
            calculated_coverage_1 = calc_energy_coverage(energy_grid_1, options)
            raise Exception("Energy sort check failed.")
        except AssertionError:
            pass

    def test_energy_coverage_sort(self):
        options = MetricOptions()
        options.set_neutrons()

        options.lower_energy = 1.0E3
        options.upper_energy = 1.0E6
        options.energy_width = 0.2
        options.energy_coverage_scale = "linear"


        test_isotope = "7Li"
        test_Z = 3
        test_A = 7
        test_nuclide_metrics = grade_isotope(test_Z, test_A, test_isotope, options)

        options.evaluation = "endf8"
        options.required_reaction_channels = [(1, 'N,TOT')]
        options.projectile = "n"
        options.user_defined = False
        options.scored_metric = "chi_squared"
        options.weighting_function = None
        options.mode = "reactor_physics"

        calculated_energy_coverage = test_nuclide_metrics.reactions['N,TOT'].energy_coverage

        expected_energy_coverage = 0.0954354
        self.assertEqual(calculated_energy_coverage,  expected_energy_coverage)


if __name__ == '__main__':
    unittest.main()
