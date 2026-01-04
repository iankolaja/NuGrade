from nugrade import *
import unittest


class TestDatabaseParsing(unittest.TestCase):
    def test_database_parsing(self):
        options = MetricOptions()
        options.set_neutrons()
        test_isotope = "7Li"
        test_Z = 3
        test_A = 7
        test_nuclide_metrics = grade_isotope(test_Z, test_A, test_isotope, options)

        # Verify that all expected datasets were found
        found_num_datasets = test_nuclide_metrics.num_datasets
        expected_num_datasets = 17
        self.assertEqual(found_num_datasets, expected_num_datasets)

        found_ntot_measurements = test_nuclide_metrics.reactions['N,TOT'].num_measurements
        expected_ntot_measurements = 17
        self.assertEqual(found_ntot_measurements, expected_ntot_measurements)

        # Verify that all expected data points are found
        found_ntot_datapoints = test_nuclide_metrics.reactions['N,TOT'].num_datapoints
        expected_ntot_datapoints = 8107
        self.assertEqual(found_ntot_datapoints, expected_ntot_datapoints)


if __name__ == '__main__':
    unittest.main()
