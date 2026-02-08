class MetricOptions:
    def __init__(self):
        self.lower_energy = None  # eV Lower bound for spectral calculations
        self.upper_energy = None  # eV Upper bound for spectral calculations
        self.energy_width = None  # eV Width associated with data points for energy completeness
        self.evaluation = None  # Evaluation to be used for precision calculation
        self.required_reaction_channels = [(1, 'N,TOT'), ]  # What reaction channels should be measured for the application
        self.scored_channel = 'N,TOT'
        self.scored_metric = "relative_error"
        self.projectile = "n"
        self.energy_coverage_scale = "linear"
        self.user_defined = False
        self.weighting_function = None
        self.mode = None

    def to_dict(self):
        opt_dict = dict()
        opt_dict['lower_energy'] = self.lower_energy
        opt_dict['upper_energy'] = self.upper_energy
        opt_dict['energy_width'] = self.energy_width
        opt_dict['energy_coverage_scale'] = self.energy_coverage_scale
        opt_dict['evaluation'] = self.evaluation
        opt_dict['required_reaction_channels'] = self.required_reaction_channels
        opt_dict['user_defined'] = self.user_defined
        opt_dict['mode'] = self.mode
        opt_dict['scored_metric'] = self.scored_metric
        opt_dict['weighting_function'] = self.weighting_function
        return opt_dict

    def set_neutrons(self):
        self.lower_energy = 0.01
        self.upper_energy = 5.0E6
        self.energy_coverage_scale = "linear"
        self.energy_width = 0.01
        self.evaluation = "endf8"
        self.required_reaction_channels = [(1, 'N,TOT')]#, (2, 'N,EL')]#, (3 'N,INL'), (102, 'N,G')]
        self.projectile = "n"
        self.user_defined = False
        self.scored_metric = "chi_squared"
        self.weighting_function = None
        self.mode = "reactor_physics"


    def set_protons(self):
        self.lower_energy = 0.01
        self.upper_energy = 5.0E6
        self.energy_width = 0.01
        self.energy_coverage_scale = "linear"
        self.evaluation = "endf8"
        self.projectile = "p"
        self.required_reaction_channels = [(2, 'P,EL'), (3, 'P,INL')]
        self.scored_channel = 'p,el'
        self.user_defined = False
        self.weighting_function = None
        self.scored_metric = "chi_squared"
        self.mode = "reactor_physics"


