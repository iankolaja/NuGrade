import numpy as np
import pandas as pd
import os
import re
from .config import NUC_DAT_PATH
from .calc_energy_coverage import calc_energy_coverage
from bokeh.models import ColumnDataSource, CategoricalColorMapper
from bokeh.plotting import figure, show
from bokeh.embed import components
from bokeh.palettes import inferno



class Reaction:
    def __init__(self, mt,  reaction_name):
        self.energy_coverage = np.float32(0.0)
        self.energy_coverage_w_unc = np.float32(0.0)
        self.average_chi_squared_per_degree = np.float32(0.0)
        self.average_absolute_relative_error = np.float32(0.0)
        self.score = 0.0
        self.num_measurements = np.int32(1)
        self.mt = mt
        self.data = pd.DataFrame()
        self.name = reaction_name

    def load_data(self, dataset_path):
        data_file_columns = {'Energy': np.float64, 'dEnergy': np.float64, 'Data': np.float64, 'dData': np.float64,
                             'EXFOR_Entry': str, 'Year': np.int16, 'Author': str, 'Dataset_Number': str}
        try:
            self.data = pd.read_csv(dataset_path, dtype=data_file_columns)
        except FileNotFoundError:
            self.data = pd.DataFrame()
        return self.data

    def calc_metrics(self, options):
        channel_data = self.data[self.data['Energy'].between(options.lower_energy, options.upper_energy)]
        self.energy_coverage = calc_energy_coverage(channel_data, options)
        #self.energy_coverage_with_unc = calc_energy_coverage(channel_data, options)
        self.average_absolute_relative_error = np.nanmean(np.abs(channel_data[options.evaluation + '_relative_error']))
        self.average_chi_squared_per_degree = np.nanmean(np.abs(channel_data[options.evaluation+'_chi_squared']))
        self.scored_metric = channel_data[f"{options.evaluation}_{options.scored_metric}"]
        if options.weighting_function is "maxwell-boltzmann-room-temp":
            kT = 8.6173033E-5 * 293.61 # (eV/K) Boltzmann constant times room temp (K)
            mass = 1.674E-27
            weighting_function = lambda energy : np.sqrt(2*energy/mass)*(2*np.pi*np.sqrt(energy)) / (np.pi*kT)**(3/2) * np.exp(-energy/kT)
            normalizing_constant = weighting_function(kT)
        if options.weighting_function is "maxwell-boltzmann-320C":
            kT = 8.6173033E-5 * 593 # (eV/K) Boltzmann constant times room temp (K)
            normalizing_constant = weighting_function(kT)
            mass = 1.674E-27
            weighting_function = lambda energy : np.sqrt(2*energy/mass)*(2*np.pi*np.sqrt(energy)) / (np.pi*kT)**(3/2) * np.exp(-energy/kT)
        if options.weighting_function is "watt":
            a = 0.453
            b = 1.036
            c = 2.29
            weighting_function = lambda energy : a*np.exp(-b*energy/1E6)*np.sinh(np.sqrt(c*energy/1E6))
            normalizing_constant = weighting_function(7.23803E5)
        if options.weighting_function is not None:
            try:
                self.scored_metric = weighting_function(channel_data['Energy'])*self.scored_metric/normalizing_constant
            except:
                print("Invalid distribution provided.")
        self.num_measurements = len(pd.unique(self.data["Dataset_Number"]))
        self.score = self.energy_coverage/np.nanmean(self.scored_metric)


class Nuclide:
    def __init__(self, Z, A, symbol):
        self.Z = int(Z)
        self.A = int(A)
        self.N = A - Z
        self.symbol = symbol
        self.reactions = {}
        self.num_datasets = np.int16(0)


    def print_experiments(self, exfor_data):
        for exp_id in self.EXFOR_IDs:
            sample_point = exfor_data.loc[exfor_data['EXFOR_Entry'] == exp_id].sample()
            print("{0}: [{2}] {3}, {1}".format(
                sample_point["Reaction_Notation"].item(),
                sample_point["Dataset_Number"].item(),
                sample_point["EXFOR_Entry"].item(),
                sample_point["Author"].item()))
    # (EXFOR.loc[EXFOR['EXFOR_Entry'] == i].sample())

    def gen_report(self, options, for_web=False):
        report_s = ""
        if for_web:
            report_s += "<p>"
        report_s += "Nuclide: {0}{1}\n".format(self.A, self.symbol)
        report_s += "Number of datasets: {0}\n".format(self.num_datasets)
        report_s += "Reaction reports:\n"
        if for_web:
            report_s += "</p>"
            report_s = report_s.replace('\n', '<br>')
            report_s = report_s.replace(' ', '&nbsp;')
        for channel_name in self.reactions.keys():
            reaction = self.reactions[channel_name]
            reaction_s = ""
            if for_web:
                reaction_s += "<p>"
            reaction_s += "  ({0}) [MT = {1}]\n".format(reaction.name, reaction.mt)
            reaction_s += "    Energy Completeness: {0}%\n".format(reaction.energy_coverage)
            reaction_s += "    Energy Completeness with Uncertainty: {0}%\n".format(reaction.energy_coverage_w_unc)
            reaction_s += "    Average absolute relative error: {0}%\n".format(reaction.average_absolute_relative_error)
            reaction_s += "    Average Chi Squared Per Degree of Freedom: {0}\n".format(reaction.average_chi_squared_per_degree)
            reaction_s += "    Overall score: {0}\n".format(reaction.score)
            if for_web:
                reaction_s += "</p>"
                reaction_s = reaction_s.replace('\n', '<br>')
                reaction_s = reaction_s.replace(' ', '&nbsp;')
                plot = plot_precision_data(reaction, options.evaluation, show_plot=False)
                reaction_s += plot[0]
                reaction_s += plot[1]
            else:
                plot_precision_data(reaction, options.evaluation, show_plot=True)
            report_s += reaction_s
        return report_s


    def get_metrics(self, options):
        self.reactions = {}
        self.num_datasets = np.int16(0)
        for reaction_codes in options.required_reaction_channels:
            mt = reaction_codes[0]
            reaction_name = reaction_codes[1]
            self.reactions[reaction_name] = Reaction(mt, reaction_name)
            data_file = f"{options.projectile}_{self.Z}_{self.A}_{reaction_name}.csv"
            data_path = os.path.join(NUC_DAT_PATH, data_file)
            channel_data = self.reactions[reaction_name].load_data(data_path)
            if len(channel_data) > 0:
                self.reactions[reaction_name].data = channel_data
                self.reactions[reaction_name].calc_metrics(options)
            self.num_datasets += self.reactions[reaction_name].num_measurements


def plot_precision_data(reaction, evaluation_code, show_plot=False):
    evaluation_error_column = evaluation_code + '_relative_error'
    evaluation_chi_column = evaluation_code + '_chi_squared'
    reaction_data = reaction.data.rename(columns={evaluation_error_column: "Relative_Error",
                                                  evaluation_chi_column: "Chi_Squared"})
    x_lower_bound = np.min((1,np.min(reaction_data['Energy'])))
    x_upper_bound = np.max((1000,np.max(reaction_data['Energy'])))
    error_y_bound = np.max((np.abs(reaction_data["Relative_Error"]))) * 1.05
    chi_y_lower_bound = np.min((0.1, np.min(reaction_data["Chi_Squared"])))
    chi_y_upper_bound = np.max((1, np.max(reaction_data["Chi_Squared"])))* 1.05

    # Relative Uncertainty Plot
    source = ColumnDataSource(reaction_data)
    tooltip_format = [
        ("Energy (eV)", "@Energy"),
        ("Relative Error (%)", "@Relative_Error"),
        ("Dataset ID", "@Dataset_Number"),
        ("Year", "@Year"),
        ("Author", "@Author")
    ]

    p = figure(width=600, height=250, y_range=(-error_y_bound, error_y_bound),
               x_range=(x_lower_bound, x_upper_bound),
               tools="pan,wheel_zoom,box_zoom,reset,hover",
               x_axis_type="log", sizing_mode="scale_both", tooltips=tooltip_format)
    palette = inferno(len(reaction.data['Dataset_Number'].unique()))
    print(palette)
    color_map = CategoricalColorMapper(factors=reaction.data['Dataset_Number'].unique(),
                                       palette=palette)
    p.scatter('Energy', "Relative_Error", size=3,
              source=source,
              color={'field': 'Dataset_Number', 'transform': color_map})
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Relative Uncertainty (%)'
    p.border_fill_color = "#f1f1f1"
    script1, div1 = components(p)
    if show_plot:
        show(p)

    tooltip_format = [
        ("Energy (eV)", "@Energy"),
        ("Chi Squared", "@Chi_Squared"),
        ("Dataset ID", "@Dataset_Number"),
        ("Year", "@Year"),
        ("Author", "@Author")
    ]

    p = figure(width=600, height=250, y_range=(chi_y_lower_bound, chi_y_upper_bound),
               x_range=(x_lower_bound, x_upper_bound),
               y_axis_type="log",
               tools="pan,wheel_zoom,box_zoom,reset,hover",
               x_axis_type="log", sizing_mode="scale_both", tooltips=tooltip_format)
    color_map2 = CategoricalColorMapper(factors=reaction.data['Dataset_Number'].unique(),
                                        palette=palette)
    source2 = ColumnDataSource(reaction_data)
    p.scatter('Energy', "Chi_Squared", size=3,
              source=source2,
              color={'field': 'Dataset_Number', 'transform': color_map2})
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Chi Squared'
    p.border_fill_color = "#f1f1f1"
    script2, div2 = components(p)

    if show_plot:
        show(p)
    return script1 + script2, div1 + div2

