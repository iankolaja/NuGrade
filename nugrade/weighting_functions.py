import numpy as np

def maxwell_boltzmann_room_temp(energy):
    """Maxwell-Boltzmann neutron flux spectrum at room temperature (293.61 K).

    Returns the flux weight for the given energy (eV), used to emphasize data points
    relevant to thermal reactor conditions.
    """
    mass = 1.674E-27 # Nucleon mass
    kT = 8.6173033E-5 * 293.61  # (eV/K) Boltzmann constant times room temp (K)
    return np.sqrt(2 * energy / mass) * (2 * np.pi * np.sqrt(energy)) / \
        (np.pi * kT) ** (3 / 2) * np.exp(-energy / kT)

def maxwell_boltzmann_320C(energy):
    """Maxwell-Boltzmann neutron flux spectrum at 320°C (593 K).

    Returns the flux weight for the given energy (eV), used to emphasize data points
    relevant to elevated-temperature reactor conditions (e.g. FHR coolant temperature).
    """
    mass = 1.674E-27 # Nucleon mass
    kT = 8.6173033E-5 * 593  # (eV/K) Boltzmann constant times room temp (K)
    return np.sqrt(2 * energy / mass) * (2 * np.pi * np.sqrt(energy)) / \
        (np.pi * kT) ** (3 / 2) * np.exp(-energy / kT)

def watt(energy):
    """Watt fission neutron spectrum.

    Returns the flux weight for the given energy (eV), used to emphasize data points
    relevant to fast fission neutron energies.
    """
    a = 0.453
    b = 1.036
    c = 2.29
    return a*np.exp(-b*energy/1E6)*np.sinh(np.sqrt(c*energy/1E6))

def constant_flux(energy):
    """Uniform flux weighting (no spectral preference). Returns 1.0 for all energies."""
    return 1.0
