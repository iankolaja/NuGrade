import numpy as np



def calc_energy_coverage(channel_data, options):
    lower_energy = options.lower_energy
    upper_energy = options.upper_energy
    energy_width = options.energy_width
    scale = options.energy_coverage_scale
    energies = channel_data['Energy'].to_numpy()

    if scale == "log":
        energies = np.log10(channel_data['Energy'].to_numpy())
        lower_energy = np.log10(lower_energy)
        upper_energy = np.log10(upper_energy)

    elif scale == "linear":
        pass

    else:
        raise Exception(f"Unknown energy coverage scale option: {scale}")

    assert_message = "calc_energy_coverage failed, energies not ascending."
    assert np.all(energies[:-1] <= energies[1:]), assert_message

    energies = np.hstack((lower_energy, energies, upper_energy))
    total_energy_space = upper_energy - lower_energy
    differences = np.diff(energies)
    differences[0] += energy_width/2
    differences[-1] += energy_width/2
    unoccupied_space = np.sum(differences[differences>energy_width]-energy_width)
    return round((total_energy_space-unoccupied_space)/total_energy_space*100,7)
