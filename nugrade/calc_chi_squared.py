import numpy as np


def calc_chi_squared(exfor_dataset, evaluation_energy, evaluation_xs, lower_energy, upper_energy):
    # Convert dataframe to numpy and filter out data out of energy range
    exfor_energy = exfor_dataset['Energy'].to_numpy()
    exfor_xs_unc = exfor_dataset['dData'].to_numpy()
    exfor_xs = exfor_dataset['Data'].to_numpy()
    filtered_booleans = np.where(np.logical_and(exfor_energy >= lower_energy, exfor_energy <= upper_energy,
                                                ~np.isnan(exfor_xs_unc)))
    exfor_energy = exfor_energy[filtered_booleans]
    exfor_xs_unc = exfor_xs_unc[filtered_booleans]
    exfor_xs = exfor_xs[filtered_booleans]
    if len(exfor_energy) == 0:
        return None, None, None
    # Interpolate evaluation cross sections at the exfor energy points
    interpolated_xs = np.interp(exfor_energy, evaluation_energy, evaluation_xs)
    # Calculate average absolute relative error between measurements and interpolated points
    chi_squared_values = ((exfor_xs - interpolated_xs)**2) / exfor_xs_unc
    chi_squared_per_degree_of_freedom = np.sum( chi_squared_values )
    return chi_squared_per_degree_of_freedom, exfor_energy, chi_squared_values
