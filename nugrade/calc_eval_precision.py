import numpy as np


def calc_eval_precision(exfor_dataset, evaluation_energy, evaluation_xs, lower_energy, upper_energy):
    exfor_energy = exfor_dataset['Energy'].to_numpy()
    exfor_xs = exfor_dataset['Data'].to_numpy()
    filtered_booleans = np.where(np.logical_and(exfor_energy >= lower_energy, exfor_energy <= upper_energy))
    exfor_energy = exfor_energy[filtered_booleans]
    exfor_xs = exfor_xs[filtered_booleans]
    if len(exfor_energy) == 0:
        return None
    _, unique_indices = np.unique(exfor_energy, return_index=True)
    exfor_energy = exfor_energy[unique_indices]
    exfor_xs = exfor_xs[unique_indices]
    _, _, evaluation_indices = np.intersect1d(exfor_energy, evaluation_energy, return_indices=True)
    standard_deviation = np.sqrt(np.sum(np.square(exfor_xs - evaluation_xs[evaluation_indices])) /
                                 len(evaluation_indices))
    return standard_deviation
