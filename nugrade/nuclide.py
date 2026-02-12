import numpy as np
import pandas as pd
import os
import re
from .config import NUGRADE_DATA_PATH
from .calc_energy_coverage import calc_energy_coverage
from bokeh.models import ColumnDataSource, CategoricalColorMapper, Whisker
from bokeh.plotting import figure, show
from bokeh.embed import components
from bokeh.palettes import inferno
from nugrade.weighting_functions import maxwell_boltzmann_room_temp, maxwell_boltzmann_320C, watt, constant_flux



class Reaction:
    def __init__(self, mt,  reaction_name):
        self.energy_coverage = np.float32(0.0)
        self.energy_coverage_w_unc = np.float32(0.0)
        self.average_metric = np.float32(0.0)
        self.score = 0.0
        self.num_measurements = np.int32(1)
        self.num_datapoints = np.int32(1)
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
        # Calculate overall energy coverage for this reaction channel
        channel_data = self.data[self.data['Energy'].between(options.lower_energy, options.upper_energy)]
        channel_data_w_unc = channel_data[channel_data["dData"].notna()]
        print(len(channel_data))
        print(len(channel_data_w_unc))
        self.energy_coverage = calc_energy_coverage(channel_data, options)
        self.energy_coverage_w_unc = calc_energy_coverage(channel_data_w_unc, options)

        # Get unique identifiers for all experiments
        all_experiments = channel_data[["EXFOR_Entry", "Author"]].drop_duplicates()
        relevant_experiments = []

        # Assign the weighting function if using a flux spectrum
        if options.weighting_function == "maxwell-boltzmann-room-temp":
            weighting_function = maxwell_boltzmann_room_temp
        elif options.weighting_function == "maxwell-boltzmann-320C":
            weighting_function = maxwell_boltzmann_320C
        elif options.weighting_function == "watt":
            weighting_function = watt
        else:
            weighting_function = constant_flux
        
        #normalizing_constant = weighting_function(0, normalize=True)

        experiment_wise_metrics_weighted_means = []
        experiment_energy_coverage_values = []
        eval_metric_str = f"{options.evaluation}_{options.scored_metric}"

        # Compute everything per experiment
        for index, row in all_experiments.iterrows():

            # Grab the data for just this experiment
            experiment_data = channel_data[channel_data["EXFOR_Entry"] == row["EXFOR_Entry"]]
            if len(experiment_data.dropna()) == 0:
                experiment_wise_metrics_weighted_means += [0.0]
                experiment_energy_coverage_values += [0.0]
                continue
            #else:
            #    relevant_experiments += [row]

            # Calculate the error metric, energy coverage for this experiment
            if (len(experiment_data.dropna()) == 0) and "Chi" in options.scored_metric["chi_squared"]:
                experiment_wise_metrics_weighted_means += [0.0]
            else:
                experiment_wise_metric = weighting_function(experiment_data['Energy']) * experiment_data[eval_metric_str]
                experiment_wise_metric_mean = np.nanmean(np.abs(experiment_wise_metric))
            experiment_energy_coverage = calc_energy_coverage(experiment_data, options)

            experiment_wise_metrics_weighted_means += [experiment_energy_coverage*experiment_wise_metric_mean]
            experiment_energy_coverage_values += [experiment_energy_coverage]
        
        # The error metric computed for each experiment, is weighted by 
        # that experiment's relative energy coverage
        experiment_energy_coverage_sum = np.sum(experiment_energy_coverage_values)
        if experiment_energy_coverage_sum > 0.0:
            experiment_energy_coverage_fractions = np.array(experiment_energy_coverage_values)/\
                                                    experiment_energy_coverage_sum
            total_metric_average = np.mean(np.array(experiment_wise_metrics_weighted_means) * \
                                            experiment_energy_coverage_fractions)
        else:
            total_metric_average = 1.0

        self.metric_data = channel_data[eval_metric_str]

        # Store results by experiment 
        self.experiment_results = all_experiments
        self.experiment_results["avg_"+eval_metric_str] = experiment_wise_metrics_weighted_means
        self.experiment_results["energy_coverage"] = experiment_energy_coverage_values
        self.num_measurements = len(pd.unique(self.data["Dataset_Number"]))
        self.num_datapoints = len(self.data["Dataset_Number"])
        self.average_metric = total_metric_average
        if options.scored_metric == "chi_squared":
            self.score = self.energy_coverage * (1/(1+total_metric_average))
        else:
            self.score = self.energy_coverage * (1/(1+total_metric_average/100))


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
        report_s += options.gen_html_description(do_html=False)
        report_s += "Nuclide: {0}{1}\n".format(self.A, self.symbol)
        report_s += "Number of datasets: {0}\n".format(self.num_datasets)
        report_s += "Reaction reports:\n"
        if for_web:
            report_s += "</p>"
            report_s = report_s.replace('\n', '<br>')
            report_s = report_s.replace(' ', '&nbsp;')
        metric_name = options.get_metric_text()
        for channel_name in self.reactions.keys():
            reaction = self.reactions[channel_name]
            reaction_s = ""
            if for_web:
                reaction_s += "<p>"
            reaction_s += f"  ({reaction.name}) [MT = {reaction.mt}]\n"
            reaction_s += f"    Energy Completeness: {round(reaction.energy_coverage,3)}%\n"
            reaction_s += f"    Energy Completeness with Uncertainty: {round(reaction.energy_coverage_w_unc,3)}%\n"
            reaction_s += f"    Average {metric_name}: {round(reaction.average_metric, 3)}\n"
            reaction_s += f"    Overall score: {round(reaction.score,3)}\n"
            if for_web:
                reaction_s += "</p>"
                if len(reaction.data) > 0:
                    plot = plot_precision_data(reaction, options.evaluation, show_plot=False)
                else:
                    reaction_s += "No data to plot.\n"
                reaction_s = reaction_s.replace('\n', '<br>')
                reaction_s = reaction_s.replace(' ', '&nbsp;')
                reaction_s += plot[0]
                reaction_s += plot[1]
            report_s += reaction_s
        return report_s


    def get_metrics(self, options):
        self.reactions = {}
        self.num_datasets = np.int16(0)
        # Reset the reaction data and iterate over the reactions being graded
        for reaction_codes in options.required_reaction_channels:
            mt = reaction_codes[0]
            reaction_name = reaction_codes[1]
            self.reactions[reaction_name] = Reaction(mt, reaction_name)
            data_file = f"{options.projectile}_{self.Z}_{self.A}_{reaction_name}.csv"
            data_path = os.path.join(NUGRADE_DATA_PATH, data_file)
            channel_data = self.reactions[reaction_name].load_data(data_path)
            
            # Calculate the error metrics and count measurements for each
            if len(channel_data) > 0:
                self.reactions[reaction_name].data = channel_data
                self.reactions[reaction_name].calc_metrics(options)
            self.num_datasets += self.reactions[reaction_name].num_measurements



def plot_precision_data(reaction, evaluation_code, show_plot=False):
    evaluation_error_column = evaluation_code + '_relative_error'
    evaluation_chi_column = evaluation_code + '_chi_squared'
    reaction_data = reaction.data.rename(columns={evaluation_error_column: "Relative_Error",
                                                  evaluation_chi_column: "Chi_Squared"})
    x_lower_bound = np.min((1,np.min(reaction_data['Energy'])))*0.95
    x_upper_bound = np.max((1000,np.max(reaction_data['Energy'])))*1.05

    data_y_lower_bound = np.max((1E-40, np.min(reaction_data["Data"])*0.1))
    data_y_upper_bound = np.max((np.abs(reaction_data["Data"]))) * 1.05

    error_y_bound = np.max((np.abs(reaction_data["Relative_Error"]))) * 1.05
    chi_y_lower_bound = np.min((0.1, np.min(reaction_data["Chi_Squared"])))
    chi_y_upper_bound = np.max((1, np.max(reaction_data["Chi_Squared"])))* 1.05

    reaction_data["Labeled_XS"] = (
    reaction_data["Data"].map("{:.3e}".format)
    + " ± "
    + reaction_data["dData"].map("{:.3e}".format)
)
    reaction_data["XS_lower"] = reaction_data["Data"] - reaction_data["dData"]
    reaction_data["XS_upper"] = reaction_data["Data"] + reaction_data["dData"]

    # Value Plot
    source = ColumnDataSource(reaction_data)
    tooltip_format = [
        ("Energy (eV)", "@Energy"),
        ("XS (b)", "@Labeled_XS"),
        ("Dataset ID", "@Dataset_Number"),
        ("Year", "@Year"),
        ("Author", "@Author")
    ]

    p = figure(width=600, height=250, #y_range=(-data_y_lower_bound, data_y_upper_bound),
               x_range=(x_lower_bound, x_upper_bound),
               y_axis_type="log",
               tools="pan,wheel_zoom,box_zoom,reset,hover",
               x_axis_type="log", sizing_mode="scale_both", tooltips=tooltip_format)
    palette = inferno(len(reaction.data['Dataset_Number'].unique()))
    print(palette)
    color_map = CategoricalColorMapper(factors=reaction.data['Dataset_Number'].unique(),
                                       palette=palette)

    
    error_bars = Whisker(
    source=source,
    base="Energy",
    upper="XS_upper",
    lower="XS_lower"
    )
    error_bars.upper_head.size = 4
    error_bars.lower_head.size = 4



    p.scatter('Energy', "Data", size=3,
              source=source,
              color={'field': 'Dataset_Number', 'transform': color_map})
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'EXFOR Cross Section (b)'
    p.border_fill_color = "#f1f1f1"
    p.add_layout(error_bars)
    script1, div1 = components(p)
    if show_plot:
        show(p)


    # Relative Uncertainty Plot
    source2 = ColumnDataSource(reaction_data)
    tooltip_format = [
        ("Energy (eV)", "@Energy"),
        ("XS (b)", "@Labeled_XS"),
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
              source=source2,
              color={'field': 'Dataset_Number', 'transform': color_map})
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Relative Error (%)'
    p.border_fill_color = "#f1f1f1"
    script2, div2 = components(p)
    if show_plot:
        show(p)


    # Chi Squared Plot
    tooltip_format = [
        ("Energy (eV)", "@Energy"),
        ("XS (b)", "@Labeled_XS"),
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
    source3 = ColumnDataSource(reaction_data)
    p.scatter('Energy', "Chi_Squared", size=3,
              source=source3,
              color={'field': 'Dataset_Number', 'transform': color_map2})
    p.xaxis[0].axis_label = 'Energy (eV)'
    p.yaxis[0].axis_label = 'Chi Squared'
    p.border_fill_color = "#f1f1f1"
    script3, div3 = components(p)

    if show_plot:
        show(p)
    return script1 + script2 + script3, div1 + div2 + div3

