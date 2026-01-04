import numpy as np

def maxwell_boltzmann_room_temp(energy, normalize=False):
    mass = 1.674E-27 # Nucleon mass
    kT = 8.6173033E-5 * 293.61  # (eV/K) Boltzmann constant times room temp (K)
    if normalize:
        energy = kT
    return np.sqrt(2 * energy / mass) * (2 * np.pi * np.sqrt(energy)) / \
        (np.pi * kT) ** (3 / 2) * np.exp(-energy / kT)

def maxwell_boltzmann_320C(energy, normalize=False):
    mass = 1.674E-27 # Nucleon mass
    kT = 8.6173033E-5 * 593  # (eV/K) Boltzmann constant times room temp (K)
    if normalize:
        energy = kT
    return np.sqrt(2 * energy / mass) * (2 * np.pi * np.sqrt(energy)) / \
        (np.pi * kT) ** (3 / 2) * np.exp(-energy / kT)

def watt(energy, normalize=False):
    a = 0.453
    b = 1.036
    c = 2.29
    if normalize:
        energy = 7.23803E5
    return a*np.exp(-b*energy/1E6)*np.sinh(np.sqrt(c*energy/1E6))

def constant_flux(energy, normalize=False):
    return 1.0