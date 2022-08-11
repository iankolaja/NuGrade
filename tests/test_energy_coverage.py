from nugrade.nuclide import _sort_channel_energy
from nugrade.calc_energy_coverage import calc_energy_coverage
import unittest


class TestEnergyCoverage(unittest.TestCase):
    def test_energy_coverage(self):
        lower_energy = 0.0
        upper_energy = 1.0
        energy_grid_1 = [0.25, 0.55, 0.2, 0.95, 0.7]
        sorted_energy_grid_1 = _sort_channel_energy(energy_grid_1,
                                                    lower_energy, upper_energy)
        self.assertEqual(calc_energy_coverage(sorted_energy_grid_1,
                                              lower_energy, upper_energy, 0.2), 75)

        energy_grid_2 = [0.2, 0.95, 0.25, 0.7]
        sorted_energy_grid_2 = _sort_channel_energy(energy_grid_2,
                                                    lower_energy, upper_energy)
        self.assertEqual(calc_energy_coverage(sorted_energy_grid_2,
                                              lower_energy, upper_energy, 0.2), 60)


if __name__ == '__main__':
    unittest.main()
