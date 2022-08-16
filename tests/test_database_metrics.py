from nugrade import *
import unittest


class TestDatabaseParsing(unittest.TestCase):
    def test_database_parsing(self):
        options = MetricOptions()
        options.set_slow_neutrons()
        test_isotope = "7Li"
        test_metric = grade_isotope(exfor_data, test_isotope, options)
        self.assertEqual(test_metric.num_experiments, 140)
        self.assertEqual(test_metric.SIG_measurements['(N,TOT)'].num_measurements, 41)


if __name__ == '__main__':
    unittest.main()
