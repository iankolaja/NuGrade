from nugrade import *
import pandas as pd
import unittest


class TestEvalPrecision(unittest.TestCase):
    def test_relative_error(self):
        options = MetricOptions()
        options.set_neutrons()
        test_isotope = "7Li"
        test_Z = 3
        test_A = 7
        evaluation = 'endf7-1'
        test_nuclide_metrics = grade_isotope(test_Z, test_A, test_isotope, options)

        channel_data = test_nuclide_metrics.reactions['N,TOT'].data
        channel_data = channel_data.dropna()



        channel_data["computed_error"] = (channel_data['Data'] - channel_data[evaluation]) / \
                         channel_data[evaluation] * 100
        error_match = channel_data[evaluation+'_relative_error'].round(4).equals(channel_data['computed_error'].round(4))
        self.assertTrue(error_match)


if __name__ == '__main__':
    unittest.main()
