import numpy as np
import pandas as pd
import os
import re
from .config import NUC_DAT_PATH
from .calc_energy_coverage import calc_energy_coverage
from .calc_relative_error import calc_relative_error
from .calc_chi_squared import calc_chi_squared


class Reaction:
    def __init__(self, notation, MT):
        self.notation = notation
        self.energy_coverage = np.float64(0.0)
        self.eval_precision = np.float64(0.0)
        self.num_measurements = np.int32(1)
        self.MT = MT
        # self.deviation_from_ENDF = 0.0

    def increment(self):
        self.num_measurements += 1


class Nuclide:
    def __init__(self, Z, A, symbol):
        self.Z = int(Z)
        self.A = int(A)
        self.N = A - Z
        self.symbol = symbol
        self.num_experiments = np.int32(0)
        self.percent_energy_unc = np.float64(0.0)
        self.percent_xs_unc = np.float64(0.0)
        self.average_energy_completeness = np.float64(0.0)
        self.reactions = {}
        self.SIG_measurements = {}
        self.num_reaction_channels = np.int32(0)
        self.num_xs_measurements = np.int32(0)
        self.error_energies = np.float64([])
        self.relative_error = np.float64([])
        self.chi_energies = np.float64([])
        self.chi_squared_values = np.float64([])
        self.chi_squared_per_degree_of_freedom = np.float64([])
        self.EXFOR_IDs = []
        self.dataset_IDs = []
        self.application_fit = np.float32(1.0)

    def get_exfor_ids(self, isotope_data):
        self.EXFOR_IDs = isotope_data.EXFOR_Entry.unique()
        self.dataset_IDs = isotope_data.Dataset_Number.unique()
        self.num_experiments = len(self.EXFOR_IDs)

    def print_experiments(self, exfor_data):
        for exp_id in self.EXFOR_IDs:
            sample_point = exfor_data.loc[exfor_data['EXFOR_Entry'] == exp_id].sample()
            print("{0}: [{2}] {3}, {1}".format(
                sample_point["Reaction_Notation"].item(),
                sample_point["Title"].item(),
                sample_point["EXFOR_Entry"].item(),
                sample_point["Author"].item()))
    # (EXFOR.loc[EXFOR['EXFOR_Entry'] == i].sample())

    def print_report(self, options):
        report_s = ""
        report_s += "Nuclide: {0}{1}\n".format(self.A, self.symbol)
        report_s += "    Overall fit for application: {0}\n".format(self.application_fit)
        report_s += "    Number of experiments: {0}\n".format(self.num_experiments)
        # Report XS uncertainty
        if options.xs_uncertainty_check:
            report_s += "    Percent reporting uncertainty on cross section: {0}%\n".format(round(self.percent_xs_unc, 2))
        # Report energy uncertainty
        if options.energy_uncertainty_check:
            report_s += "    Percent reporting uncertainty on energy: {0}%\n".format(round(self.percent_energy_unc, 2))
        report_s += "    Number of cross section datasets: {0}  ({1} required)\n".format(self.num_xs_measurements,
                                                                                 options.num_xs_threshold)
        report_s += "    SIG measurements:\n"

        # Report how many measurements there are for each reaction channel, and if desired report energy completion
        if options.upper_energy is not None and options.lower_energy is not None:
            report_s += "    Reporting energy completion from {0} MeV to {1} MeV with spacing of {2} eV\n".format(
                options.lower_energy * 1E-6, options.upper_energy * 1E-6, options.energy_width)
        for channel in self.SIG_measurements.keys():
            reaction = self.SIG_measurements[channel]
            if reaction.MT not in options.required_reaction_channels:
                continue
            report_s += "    {0} -> {1} XS measurements [MT = {2}]\n".format(channel, reaction.num_measurements, reaction.MT)
            if options.energy_width is not None:
                report_s += "        Energy Completeness: {0}%\n".format(round(reaction.energy_coverage, 2))
            if options.precision_reference is not None:
                if reaction.eval_precision != 0:
                    report_s += "        Average Absolute Relative Error: {0}%\n".format(
                        round(reaction.eval_precision, 3))
                else:
                    report_s += "        No measurements in energy range.\n"
        print(report_s)
        report_s = report_s.replace('\n', '<br>')
        return report_s


    def get_metrics(self, isotope_data, options):
        self.get_exfor_ids(isotope_data)
        num_xs_unc = np.int32(0)
        num_energy_unc = np.int32(0)

        # Check how many experiments report cross section uncertainty
        if options.xs_uncertainty_check:
            for exp_id in self.EXFOR_IDs:
                sample_point = isotope_data.loc[isotope_data['EXFOR_Entry'] == exp_id].sample()
                ddata = sample_point['dData']
                if not ddata.isnull().values.any():
                    num_xs_unc += 1
            self.percent_xs_unc = num_xs_unc / self.num_experiments
            self.application_fit *= self.percent_xs_unc

        # Check how many experiments report energy uncertainty
        # Fit is multiplied by that value.
        if options.energy_uncertainty_check:
            for exp_id in self.EXFOR_IDs:
                sample_point = isotope_data.loc[isotope_data['EXFOR_Entry'] == exp_id].sample()
                denergy = sample_point['dEnergy']
                if not denergy.isnull().values.any():
                    num_energy_unc += 1
            self.percent_energy_unc = num_energy_unc / self.num_experiments
            self.application_fit *= self.percent_energy_unc

        # Determine reaction channel statistics on a dataset basis
        for dataset_id in self.dataset_IDs:
            sample_point = isotope_data.loc[isotope_data['Dataset_Number'] == dataset_id].sample()
            reaction_type = sample_point['Reaction_Notation'].item()
            MT = int(sample_point['MT'].item())
            if "SIG" in reaction_type:
                channel = reaction_type
                if channel[0] == "(":
                    channel = channel[1:]
                channel = channel.split("(")[1].split(")")[0]
                channel = "(" + channel + ")"
                if channel in self.SIG_measurements.keys():
                    self.SIG_measurements[channel].increment()
                    self.num_xs_measurements += 1
                else:
                    self.SIG_measurements[channel] = Reaction(reaction_type, MT)
                    self.num_xs_measurements += 1
            if reaction_type in self.reactions.keys():
                self.reactions[reaction_type].increment()
            else:
                self.reactions[reaction_type] = Reaction(reaction_type, MT)

        # Check if there are enough experiments compared to the threshold.
        # The more experiments compared to the threshold, the better.
        # Otherwise, the fit is dropped to 0.
        if 0 < options.num_xs_threshold <= self.num_xs_measurements:
            self.application_fit *= self.num_xs_measurements/options.num_xs_threshold
        elif 0 < options.num_xs_threshold:
            self.application_fit *= 0

        # Check to see if all of the required reactions are present.
        if len(options.required_reaction_channels) > 0:
            measured_mts = []
            for react in self.reactions.values():
                measured_mts += [react.MT]
            for required_reaction in options.required_reaction_channels:
                if required_reaction not in measured_mts:
                    self.application_fit *= 0
                    print("Required reaction MT = {0} not found.".format(required_reaction))

        # Calculate reaction-channel level metrics if energies are provided
        if options.upper_energy is not None and options.lower_energy is not None:
            for channel in self.SIG_measurements.keys():
                reaction_notation = self.SIG_measurements[channel].notation
                MT = self.SIG_measurements[channel].MT
                if MT not in options.required_reaction_channels:
                    continue
                channel_data = isotope_data.loc[reaction_notation == isotope_data['Reaction_Notation']]
                energy_array = channel_data['Energy'].to_numpy().astype(np.float)
                sorted_energy_array = _sort_channel_energy(energy_array, options.lower_energy, options.upper_energy)
                if len(sorted_energy_array) == 0:
                    continue

                # Calculate energy completeness
                if options.energy_width is not None:
                    energy_array = channel_data['Energy'].to_numpy().astype(np.float)
                    self.SIG_measurements[channel].energy_coverage = calc_energy_coverage(
                        sorted_energy_array, options.lower_energy, options.upper_energy, options.energy_width)

                # Calculate precision relative to an evaluation
                if options.precision_reference is not None:
                    MT_str = "{:03d}".format(MT)
                    A_str = "{:03d}".format(self.A)
                    isotope_str = self.symbol + A_str
                    reaction_file = "n-{0}-MT{1}.{2}".format(isotope_str, MT_str,
                                                             options.precision_reference)
                    file_path = os.path.join(NUC_DAT_PATH, "Evaluated_Data/neutrons/{0}/{1}/tables/xs/{2}".format(
                        isotope_str, options.precision_reference, reaction_file))
                    try:
                        evaluation_df = pd.read_csv(file_path, sep=" ", names=["E(eV)", "xs(mb)", "xslow(mb)", "xsupp(mb)"],
                                                    skipinitialspace=True, skiprows=5)
                    except:
                        print("{0} not found. Does an evaluation exist for this reaction?".format(reaction_file))
                        continue
                    evaluation_df['E(eV)'] = evaluation_df['E(eV)'].apply(lambda x: x * 1E6)
                    evaluation_df['xs(mb)'] = evaluation_df['xs(mb)'].apply(lambda x: x / 1000.0)
                    evaluation_energy = evaluation_df['E(eV)'].to_numpy().astype(np.float)
                    evaluation_xs = evaluation_df['xs(mb)'].to_numpy().astype(np.float)

                    average_stdev = np.float64(0.0)
                    applicable_datasets = np.int32(0)
                    for dataset_ID in self.dataset_IDs:
                        # print("MT: {0} Dataset: {1}".format(MT,dataset_ID))
                        exfor_dataset = channel_data.loc[dataset_ID == channel_data['Dataset_Number']]
                        average_relative_error, error_x, relative_error = calc_relative_error(exfor_dataset,
                                                                                              evaluation_energy,
                                                                                              evaluation_xs,
                                                                                              options.lower_energy,
                                                                                              options.upper_energy)
                        print("{0}: {1}%".format(dataset_ID, average_relative_error))
                        if average_relative_error is None:
                            pass
                        else:
                            self.error_energies = np.append(self.error_energies, error_x)
                            self.relative_error = np.append(self.relative_error, relative_error)
                            average_stdev += average_relative_error
                            applicable_datasets += 1
                        chi_squared_per_degree, chi_x, chi_squared_values = calc_chi_squared(exfor_dataset,
                                                                                             evaluation_energy,
                                                                                             evaluation_xs,
                                                                                             options.lower_energy,
                                                                                             options.upper_energy)
                        if chi_squared_per_degree is None:
                            pass
                        else:
                            self.chi_energies = np.append(self.chi_energies, chi_x)
                            self.chi_squared_values = np.append(self.chi_squared_values, chi_squared_values)
                    if applicable_datasets > 0:
                        self.SIG_measurements[channel].eval_precision = average_stdev / applicable_datasets
                        precision_fit = 1 - self.SIG_measurements[channel].eval_precision/100
                        if precision_fit > 0:
                            self.application_fit *= precision_fit
                        else:
                            self.application_fit *= 0
                    else:
                        self.SIG_measurements[channel].eval_precision = np.float64(0.0)

        self.num_reaction_channels = len(self.SIG_measurements.keys())


def _sort_channel_energy(energy_array, lower_energy, upper_energy):
    sorted_energy_array = np.sort(energy_array)
    filtered_booleans = np.where(
        np.logical_and(sorted_energy_array >= lower_energy, sorted_energy_array <= upper_energy))
    sorted_energy_array = sorted_energy_array[filtered_booleans]
    sorted_energy_array = np.unique(sorted_energy_array)
    return sorted_energy_array
