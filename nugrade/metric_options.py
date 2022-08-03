class MetricOptions:
    def __init__(self):
        self.lower_energy = None  # eV Lower bound for spectral calculations
        self.upper_energy = None  # eV Upper bound for spectral calculations
        self.energy_width = None  # eV Width associated with data points for energy completeness
        self.calc_energy_completeness = False  # Whether to calculate energy completeness
        self.calc_eval_precision = False  # Whether to calculate precision to an evaluation
        self.precision_reference = None  # Evaluation to be used for precision calculation
        self.energy_uncertainty_check = False  # Cutoff value for energy uncertainty
        self.xs_uncertainty_check = False  # Cutoff value for cross section uncertainty
        self.num_xs_threshold = 0  # The number of cross section measurements needed to pass
        self.required_reaction_channels = []  # What reaction channels should be measured for the application

    def set_slow_neutrons(self):
        self.lower_energy = 0.0
        self.upper_energy = 2.0E6
        self.energy_width = 2000
        self.calc_energy_completeness = True
        self.calc_eval_precision = True
        self.precision_reference = "endfb8.0"
        self.energy_uncertainty_check = True
        self.xs_uncertainty_check = True
        self.num_xs_threshold = 10
        self.required_reaction_channels = []

    def set_energy_completeness(self, lower, upper, width):
        if None in (lower, upper, width) or False in (lower, upper, width):
            self.calc_energy_completeness = False
            self.energy_width = False
        else:
            self.lower_energy = lower
            self.upper_energy = upper
            self.energy_width = width
            self.calc_energy_completeness = True
            print("Calculating energy completeness between {0} eV and {1} eV with width of {2} eV".format(
                lower, upper, width))
