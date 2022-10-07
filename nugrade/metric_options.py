class MetricOptions:
    def __init__(self):
        self.lower_energy = None  # eV Lower bound for spectral calculations
        self.upper_energy = None  # eV Upper bound for spectral calculations
        self.energy_width = None  # eV Width associated with data points for energy completeness
        self.calc_energy_coverage = False  # Whether to calculate energy completeness
        self.calc_eval_error = False  # Whether to calculate precision to an evaluation
        self.calc_chi_squared = False
        self.precision_reference = None  # Evaluation to be used for precision calculation
        self.energy_uncertainty_check = False  # Cutoff value for energy uncertainty
        self.xs_uncertainty_check = False  # Cutoff value for cross section uncertainty
        self.num_xs_threshold = 0  # The number of cross section measurements needed to pass
        self.required_reaction_channels = []  # What reaction channels should be measured for the application
        self.user_defined = False
        self.mode = None

    def to_dict(self):
        opt_dict = dict()
        opt_dict['lower_energy'] = self.lower_energy
        opt_dict['upper_energy'] = self.upper_energy
        opt_dict['energy_width'] = self.energy_width
        opt_dict['calc_energy_coverage'] = self.calc_energy_coverage
        opt_dict['calc_eval_error'] = self.calc_eval_error
        opt_dict['precision_reference'] = self.precision_reference
        opt_dict['energy_uncertainty_check'] = self.energy_uncertainty_check
        opt_dict['xs_uncertainty_check'] = self.xs_uncertainty_check
        opt_dict['num_xs_threshold'] = self.num_xs_threshold
        opt_dict['required_reaction_channels'] = self.required_reaction_channels
        opt_dict['user_defined'] = self.user_defined
        opt_dict['mode'] = self.mode
        return opt_dict

    def set_neutrons(self):
        self.lower_energy = 0.0
        self.upper_energy = 2.0E6
        self.energy_width = 2000
        self.calc_energy_coverage = True
        self.calc_eval_error = True
        self.calc_chi_squared = True
        self.precision_reference = "endfb8.0"
        self.energy_uncertainty_check = True
        self.xs_uncertainty_check = True
        self.num_xs_threshold = 10
        self.required_reaction_channels = [1,2]
        self.user_defined = False
        self.mode = "reactor_physics"


