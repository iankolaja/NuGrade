import numpy as np


def calc_eval_precision(exfor_dataset, evaluation_energy, evaluation_xs, lower_energy, upper_energy):
    # Convert dataframe to numpy and filter out data out of energy range
    exfor_energy = exfor_dataset['Energy'].to_numpy()
    exfor_xs = exfor_dataset['Data'].to_numpy()
    filtered_booleans = np.where(np.logical_and(exfor_energy >= lower_energy, exfor_energy <= upper_energy))
    exfor_energy = exfor_energy[filtered_booleans]
    exfor_xs = exfor_xs[filtered_booleans]
    if len(exfor_energy) == 0:
        return None
    # Interpolate evaluation cross sections at the exfor energy points
    interpolated_xs = np.interp(exfor_energy, evaluation_energy, evaluation_xs)
    # Calculate average absolute relative error
    average_absolute_relative_error = np.sum(np.abs(exfor_xs - interpolated_xs)/exfor_xs)/len(exfor_energy)*100
    return average_absolute_relative_error
