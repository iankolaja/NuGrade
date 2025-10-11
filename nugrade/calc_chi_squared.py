def calc_chi_squared(channel_data, evaluation):
    # Calculate average absolute relative error between measurements and interpolated points
    channel_data[evaluation+'_chi_squared'] = ((channel_data['Data'] - channel_data[evaluation])**2) / channel_data['dData']
    return channel_data[evaluation+'_chi_squared']
