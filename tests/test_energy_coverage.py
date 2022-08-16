from nugrade.nuclide import _sort_channel_energy
from nugrade.calc_energy_coverage import calc_energy_coverage
from nugrade import *
import unittest


class TestEnergyCoverage(unittest.TestCase):
    def test_energy_coverage(self):
        # Test hand-verified case 1
        lower_energy = 0.0
        upper_energy = 1.0
        energy_grid_1 = [0.25, 0.55, 0.2, 0.95, 0.7]
        sorted_energy_grid_1 = _sort_channel_energy(energy_grid_1,
                                                    lower_energy, upper_energy)
        self.assertEqual(calc_energy_coverage(sorted_energy_grid_1,
                                              lower_energy, upper_energy, 0.2), 75)

        # Test hand-verified case 2
        energy_grid_2 = [0.2, 0.95, 0.25, 0.7]
        sorted_energy_grid_2 = _sort_channel_energy(energy_grid_2,
                                                    lower_energy, upper_energy)
        self.assertEqual(calc_energy_coverage(sorted_energy_grid_2,
                                              lower_energy, upper_energy, 0.2), 60)

        # Test previously-calculated case for consistency
        # TODO: Manually calculate energy coverage for this case
        options = MetricOptions()
        options.lower_energy = 0.0
        options.upper_energy = 2.0E6
        options.energy_width = 2000
        options.precision_reference = "endfb8.0"
        options.energy_uncertainty_check = True
        options.xs_uncertainty_check = True
        options.num_xs_threshold = 10
        options.required_reaction_channels = [1]
        test_isotope = "7Li"
        test_metric = grade_isotope(exfor_data, test_isotope, options)
        self.assertEqual(test_metric.SIG_measurements['(N,TOT)'].energy_coverage, 65.6)


if __name__ == '__main__':
    unittest.main()
