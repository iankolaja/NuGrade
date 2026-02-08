import numpy as np
#TODO: Delete "Scored channel"
class MetricOptions:
    def __init__(self):
        self.lower_energy = 0.0  # eV Lower bound for spectral calculations
        self.upper_energy = 0.0  # eV Upper bound for spectral calculations
        self.energy_width = 0.0  # eV Width associated with data points for energy completeness
        self.evaluation = ""  # Evaluation to be used for precision calculation
        self.required_reaction_channels = []  # What reaction channels should be measured for the application
        self.scored_channel = ""
        self.scored_metric = ""
        self.projectile = ""
        self.energy_coverage_scale = "linear"
        self.weighting_function = None

    def to_dict(self):
        opt_dict = dict()
        opt_dict['lower_energy'] = self.lower_energy
        opt_dict['upper_energy'] = self.upper_energy
        opt_dict['energy_width'] = self.energy_width
        opt_dict['energy_coverage_scale'] = self.energy_coverage_scale
        opt_dict['evaluation'] = self.evaluation
        opt_dict['required_reaction_channels'] = self.required_reaction_channels
        opt_dict['scored_metric'] = self.scored_metric
        opt_dict['weighting_function'] = self.weighting_function
        return opt_dict
    
    def gen_html_description(self, do_html=True):
        reactions_str = "("+self.required_reaction_channels[0][1]+")"
        for reaction in self.required_reaction_channels[1:]:
            reactions_str += f", ({reaction[1]})"

        metric_text_dict = {"chi_squared": "Chi Squared",
                          "reltaive_error": "Relative Error"}
        metrics_str = metric_text_dict[self.scored_metric]
        lower_energy_str = np.format_float_scientific(self.lower_energy, precision=4,exp_digits=1)
        upper_energy_str = np.format_float_scientific(self.upper_energy, precision=4,exp_digits=1)
        if do_html:
            param_text = f"""
            <p class=\"options-report-text\"><b>Scoring Parameters</b><br>
            Energy Range: {lower_energy_str} - {upper_energy_str} (eV)<br>
            Energy Spacing: {self.energy_width} eV ({self.energy_coverage_scale})<br>
            Evaluation: {self.evaluation}<br>
            Error Function: {metrics_str}<br>
            Reactions: {reactions_str}<br></p>
            """
        else:
            param_text = f"Scoring Parameters\n"+\
            f"Energy Range: {lower_energy_str} - {upper_energy_str} (eV)\n"+\
            f"Energy Spacing: {self.energy_width} eV ({self.energy_coverage_scale})\n"+\
            f"Evaluation: {self.evaluation}\n"+\
            f"Error Function: {metrics_str}\n"+\
            f"Reactions: {reactions_str}\n"
        return param_text

    def set_neutrons(self):
        self.lower_energy = 0.01
        self.upper_energy = 5.0E6
        self.energy_width = 100
        self.energy_coverage_scale = "linear"
        self.evaluation = "endf8"
        self.projectile = "n"
        self.required_reaction_channels = [(1, 'N,TOT')]#, (2, 'N,EL')]#, (3 'N,INL'), (102, 'N,G')]
        self.scored_channel = 'N,TOT'
        self.scored_metric = "chi_squared"
        self.weighting_function = None


    def set_protons(self):
        self.lower_energy = 0.01
        self.upper_energy = 5.0E6
        self.energy_width = 100
        self.energy_coverage_scale = "linear"
        self.evaluation = "endf8"
        self.projectile = "p"
        self.required_reaction_channels = [(2, 'P,EL'), (3, 'P,INL')]
        self.scored_channel = 'P,EL'
        self.weighting_function = None
        self.scored_metric = "chi_squared"


