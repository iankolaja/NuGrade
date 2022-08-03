import numpy as np


def calc_energy_coverage(sorted_energy_array, lower_energy, upper_energy, energy_width):
    sorted_energy_array = np.insert(sorted_energy_array, 0, lower_energy)
    sorted_energy_array = np.append(sorted_energy_array, upper_energy)
    total_energy_space = upper_energy - lower_energy
    energy_covered = 0.0
    for i in range(1, len(sorted_energy_array) - 1):
        # Calculate left side
        # If the last datapoint is within an energy width, calculate the distance between them
        # print("energy: {0}".format(sorted_energy_array[i]))
        if sorted_energy_array[i] - energy_width / 2.0 < sorted_energy_array[i - 1]:
            # print("branch 1")
            energy_covered += sorted_energy_array[i] - sorted_energy_array[i - 1]
            # print(energy_covered)
        else:
            # print("branch 2")
            energy_covered += energy_width / 2.0
            # print(energy_covered)

        # Calculate right side
        if sorted_energy_array[i] + energy_width <= sorted_energy_array[i + 1]:
            # print("branch 3")
            energy_covered += energy_width / 2.0
            # print(energy_covered)
        elif sorted_energy_array[i] + energy_width / 2 <= sorted_energy_array[i + 1]:
            # print("branch 4")
            energy_covered += sorted_energy_array[i + 1] - sorted_energy_array[i] - energy_width / 2.0
            # print(energy_covered)
        else:
            # print("branch 5")
            pass
            # print(energy_covered)
    if sorted_energy_array[-2] + energy_width / 2.0 > sorted_energy_array[-1]:
        energy_covered += sorted_energy_array[-1] - sorted_energy_array[-2]
    return round(energy_covered / total_energy_space * 100, 3)
