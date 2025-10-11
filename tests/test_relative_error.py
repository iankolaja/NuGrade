from nugrade.nuclide import _sort_channel_energy
from nugrade.calc_relative_error import calc_relative_error
from nugrade import *
import pandas as pd
import unittest


class TestEvalPrecision(unittest.TestCase):
    def test_eval_precision(self):
        # Test hand-verified case 1
        lower_energy = 0.5
        upper_energy = 2.5
        evaluation_energy = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2,2.1,2.2,2.3,2.4,2.5,2.6,2.7]
        evaluation_xs = [9.090909091,8.333333333,7.692307692,7.142857143,6.666666667,6.25,5.882352941,5.555555556,5.263157895,5,4.761904762,4.545454545,4.347826087,4.166666667,4,3.846153846,3.703703704,3.571428571,3.448275862,3.333333333,3.225806452,3.125,3.03030303,2.941176471,2.857142857,2.777777778,2.702702703]
        measurement_energy = [0.11,0.175841081,0.210774438,0.259486805,0.310731648,0.380702303,0.445958013,0.445958013,0.535252178,0.550612413,0.628978921,0.720215051,0.772918731,0.843825243,0.843825243,0.843825243,0.944593157,1.030118367,1.123854863,1.136367509,1.163212361,1.194143436,1.265205172,1.27938332,1.34426159,1.410671871,1.485583742,1.555495058,1.641332603,1.698119552,1.712578599,1.732075801,1.762485626,1.787417832,1.816118851,1.84850701,1.939412609,1.991677309,2.057680907,2.077603876,2.124609077,2.179622699,2.219632436,2.272945927,2.362096077,2.39978947,2.405157903,2.482366934,2.537385722,2.592185408]
        measurement_xs = [10.74586084,10.19679834,8.563365388,7.372048194,6.121897047,6.656013592,6.863630273,7.234623,7.449609001,7.576228268,6.273958192,6.943485546,6.647939571,4.782623101,4.601171194,5.853057948,5.874445479,4.586499241,4.76140639,4.424777994,4.595587182,5.400831883,3.593203017,5.166918344,4.875438581,4.583990846,3.510275789,3.169097122,3.972622588,4.155544717,4.245912232,3.194247828,4.333128685,3.134886569,4.219465847,3.544728872,3.306041221,3.428497677,3.748657454,3.751726685,2.965809828,3.468397716,3.511347273,2.928786983,3.421485518,3.205610492,2.424477586,3.216676727,2.685661226,3.278911002]
        measurement_data = {'Energy': measurement_energy, 'Data': measurement_xs}
        measurement_df = pd.DataFrame(measurement_data)
        average_relative_error, energy, relative_error = calc_relative_error(measurement_df, evaluation_energy,
                                                                             evaluation_xs, lower_energy, upper_energy)
        average_relative_error = round(average_relative_error,3)
        self.assertEqual(average_relative_error, 11.656)

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
        self.assertEqual(round(test_metric.SIG_measurements['(N,TOT)'].eval_precision, 3), 317.092)


if __name__ == '__main__':
    unittest.main()
