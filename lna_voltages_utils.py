import numpy as np
import matplotlib.pyplot as plt


def parallel_resistance(r1: float, r2: float) -> float:
    return (r1 * r2) / (r1 + r2)


def reverse_parallel_resistance(r_eq: float, r1: float) -> float:
    return (r_eq * r1) / (r1 - r_eq)


def v_source(r_ldo_set, r_switched, r_fixed, r_paral, switch_state, r_pot, i_set=1e-4):
    """
    r_set: list or array of 3 fixed resistances [R1, R2, R3]
    switch_state: boolean, True if the switch is closed, False if open
    r_pot: float, resistance of the potentiometer
    i_set: float, set current of the LDO, default is 100 µA
    Returns the source voltage based on the configuration.
    """
    return i_set * parallel_resistance(
        (0 if switch_state else r_switched)
        + r_fixed
        + parallel_resistance(r_paral, r_pot),
        r_ldo_set,
    )


def v_remote(v_source, r_meas, r_highside, r_lowside, i_meas):
    """
    r_meas: float, measured resistance of the DUT
    r_highside: float, high-side resistance
    r_lowside: float, low-side resistance
    i_meas: float, measurement current
    """
    return v_source - i_meas * (r_meas + r_highside + r_lowside)


I_MEAS_DATA = {1.15: 2.53e-3, 1.16: 2.71e-3, 1.2: 3.41e-3, 1.25: 4.29e-3}
I_MEAS_DATA = {
    1.117: 2.419e-03,
    1.119: 2.449e-03,
    1.121: 2.528e-03,
    1.123: 2.610e-03,
    1.125: 2.607e-03,
    1.127: 2.699e-03,
    1.128: 2.662e-03,
    1.129: 2.764e-03,
    1.131: 2.819e-03,
    1.133: 2.871e-03,
    1.135: 2.933e-03,
    1.137: 2.987e-03,
    1.139: 3.038e-03,
    1.141: 3.094e-03,
    1.142: 3.130e-03,
    1.143: 3.167e-03,
    1.146: 3.222e-03,
    1.147: 3.264e-03,
    1.148: 3.298e-03,
    1.149: 3.332e-03,
    1.151: 3.376e-03,
    1.152: 3.441e-03,
    1.153: 3.433e-03,
    1.154: 3.491e-03,
    1.155: 3.517e-03,
    1.157: 3.564e-03,
    1.158: 3.580e-03,
    1.160: 3.653e-03,
    1.161: 3.693e-03,
    1.163: 3.729e-03,
    1.165: 3.767e-03,
    1.166: 3.814e-03,
    1.167: 3.829e-03,
    1.168: 3.836e-03,
    1.169: 3.886e-03,
    1.170: 3.940e-03,
    1.171: 3.941e-03,
    1.172: 3.979e-03,
    1.173: 4.037e-03,
    1.174: 4.017e-03,
    1.175: 4.087e-03,
    1.176: 4.065e-03,
    1.177: 4.124e-03,
    1.178: 4.189e-03,
    1.179: 4.178e-03,
    1.180: 4.237e-03,
    1.181: 4.261e-03,
    1.182: 4.285e-03,
    1.183: 4.331e-03,
    1.186: 4.405e-03,
    1.187: 4.443e-03,
    1.188: 4.430e-03,
    1.189: 4.502e-03,
    1.191: 4.551e-03,
    1.192: 4.564e-03,
    1.194: 4.625e-03,
    1.196: 4.669e-03,
    1.197: 4.708e-03,
    1.198: 4.774e-03,
    1.199: 4.741e-03,
    1.200: 4.807e-03,
    1.201: 4.831e-03,
    1.202: 4.854e-03,
    1.203: 4.906e-03,
    1.204: 4.877e-03,
    1.205: 4.926e-03,
    1.206: 4.952e-03,
    1.207: 5.010e-03,
    1.208: 5.028e-03,
    1.211: 5.113e-03,
    1.212: 5.171e-03,
    1.213: 5.199e-03,
    1.214: 5.250e-03,
    1.215: 5.225e-03,
    1.216: 5.300e-03,
    1.217: 5.275e-03,
    1.218: 5.331e-03,
    1.219: 5.356e-03,
    1.220: 5.400e-03,
    1.222: 5.432e-03,
    1.223: 5.465e-03,
    1.224: 5.504e-03,
    1.225: 5.550e-03,
    1.226: 5.527e-03,
}
I_MEAS_DATA = {
    1.128: 2.412e-03,
    1.129: 2.463e-03,
    1.130: 2.504e-03,
    1.131: 2.527e-03,
    1.133: 2.560e-03,
    1.135: 2.605e-03,
    1.137: 2.657e-03,
    1.138: 2.705e-03,
    1.140: 2.729e-03,
    1.141: 2.779e-03,
    1.143: 2.814e-03,
    1.144: 2.840e-03,
    1.146: 2.881e-03,
    1.147: 2.925e-03,
    1.148: 2.960e-03,
    1.149: 2.979e-03,
    1.151: 3.011e-03,
    1.153: 3.055e-03,
    1.155: 3.111e-03,
    1.156: 3.149e-03,
    1.157: 3.179e-03,
    1.158: 3.208e-03,
    1.159: 3.240e-03,
    1.160: 3.269e-03,
    1.161: 3.287e-03,
    1.163: 3.320e-03,
    1.164: 3.352e-03,
    1.165: 3.386e-03,
    1.166: 3.423e-03,
    1.167: 3.430e-03,
    1.169: 3.499e-03,
    1.171: 3.542e-03,
    1.172: 3.593e-03,
    1.173: 3.567e-03,
    1.174: 3.625e-03,
    1.175: 3.635e-03,
    1.176: 3.690e-03,
    1.177: 3.674e-03,
    1.178: 3.695e-03,
    1.179: 3.738e-03,
    1.180: 3.765e-03,
    1.181: 3.793e-03,
    1.183: 3.833e-03,
    1.184: 3.856e-03,
    1.185: 3.902e-03,
    1.186: 3.929e-03,
    1.187: 3.905e-03,
    1.188: 3.962e-03,
    1.189: 3.984e-03,
    1.190: 3.997e-03,
    1.191: 4.039e-03,
    1.192: 4.108e-03,
    1.193: 4.119e-03,
    1.194: 4.082e-03,
    1.195: 4.181e-03,
    1.196: 4.166e-03,
    1.197: 4.208e-03,
    1.198: 4.228e-03,
    1.199: 4.251e-03,
    1.200: 4.289e-03,
    1.201: 4.309e-03,
    1.202: 4.329e-03,
    1.203: 4.368e-03,
    1.204: 4.406e-03,
    1.205: 4.383e-03,
    1.206: 4.443e-03,
    1.207: 4.462e-03,
    1.208: 4.468e-03,
    1.209: 4.506e-03,
    1.210: 4.489e-03,
}


def v_remote_from_data(v_source_values, r_meas, r_highside, r_lowside):
    """
    v_source: float, source voltage or list of voltages
    r_meas: float, measured resistance of the DUT
    r_highside: float, high-side resistance
    r_lowside: float, low-side resistance
    """
    if not isinstance(v_source_values, (list, np.ndarray)):
        v_source_values = [v_source_values]
    else:
        v_source_values = v_source_values
    n_interp_points = 1000
    coef = np.polyfit(list(I_MEAS_DATA.keys()), list(I_MEAS_DATA.values()), 2)
    v_bias_values = np.linspace(0, max(v_source_values), n_interp_points)
    i_meas_values = np.array([np.polyval(coef, v_bias) for v_bias in v_bias_values])
    v_i_values_idx = [
        np.argmin(
            abs(
                v_remote(v_source, r_meas, r_highside, r_lowside, i_meas_values)
                - v_bias_values
            )
        )
        for v_source in v_source_values
    ]
    return v_bias_values[v_i_values_idx], i_meas_values[v_i_values_idx]


def main():
    # Fixed resistances
    r_LDO_set = 82000  # Ohms
    r_switched = 10000  # Ohms
    r_fixed = 14500  # Ohms
    r_highside = 30  # Ohms
    r_lowside = 30  # Ohms
    r_meas = 10  # 1 kOhm DUT
    # r_paral = 18000  # Ohms

    # Potentiometer is the main variable
    r_pot_values = np.linspace(0, 10000, 128)  # 0 to 10k Ohms

    # R parallel resistance is the secondary variable
    r_paral_values = np.array([18000, 1e7])  # np.linspace(10000, 20000, 5)  # Ohms #
    # R switched resistance is the secondary variable
    r_switched_values = np.array([18000])  # np.linspace(10000, 20000, 5)  # Ohms #
    # R fixed resistance is the secondary variable
    r_fixed_values = np.array([18000])  # np.linspace(10000, 20000, 5)  # Ohms #

    v_source_closed_list = []
    v_source_open_list = []
    v_remote_closed_from_data_list = []
    v_remote_open_from_data_list = []
    i_meas_closed_from_data_list = []
    i_meas_open_from_data_list = []
    for r_paral in r_paral_values:
        # Calculate voltages for each potentiometer value
        v_source_closed = v_source(
            r_LDO_set, r_switched, r_fixed, r_paral, True, r_pot_values
        )
        v_source_open = v_source(
            r_LDO_set, r_switched, r_fixed, r_paral, False, r_pot_values
        )

        v_remote_closed_from_data, i_meas_closed_from_data = v_remote_from_data(
            v_source_closed, r_meas, r_highside, r_lowside
        )
        v_remote_open_from_data, i_meas_open_from_data = v_remote_from_data(
            v_source_open, r_meas, r_highside, r_lowside
        )
        v_source_closed_list.append(v_source_closed)
        v_source_open_list.append(v_source_open)
        v_remote_closed_from_data_list.append(v_remote_closed_from_data)
        v_remote_open_from_data_list.append(v_remote_open_from_data)
        i_meas_closed_from_data_list.append(i_meas_closed_from_data)
        i_meas_open_from_data_list.append(i_meas_open_from_data)

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(
        r_pot_values,
        np.array(v_source_closed_list).T,
        label="V_source (Switch Closed)",
        color="blue",
        marker="o",
        markersize=2,
    )
    plt.plot(
        r_pot_values,
        np.array(v_source_open_list).T,
        label="V_source (Switch Open)",
        color="orange",
        marker="o",
        markersize=2,
    )
    plt.plot(
        r_pot_values,
        np.array(v_remote_closed_from_data_list).T,
        label="V_remote (Switch Closed) From Data",
        color="purple",
        marker="o",
        markersize=2,
    )
    plt.plot(
        r_pot_values,
        np.array(v_remote_open_from_data_list).T,
        label="V_remote (Switch Open) From Data",
        color="brown",
        marker="o",
        markersize=2,
    )
    plt.legend()
    plt.ylabel("Voltage (V)")

    # use twin y-axis to plot i_meas
    ax2 = plt.gca().twinx()
    ax2.plot(
        r_pot_values,
        np.array(i_meas_closed_from_data_list).T * 1000,  # Convert to mA for plotting
        label="I_meas (Switch Closed) From Data (mA)",
        color="cyan",
        marker="o",
        markersize=2,
    )
    ax2.plot(
        r_pot_values,
        np.array(i_meas_open_from_data_list).T * 1000,  # Convert to mA for plotting
        label="I_meas (Switch Open) From Data (mA)",
        color="magenta",
        marker="o",
        markersize=2,
    )
    plt.title("Source and Remote Voltages vs Potentiometer Resistance")
    plt.xlabel("Potentiometer Resistance (Ohms)")
    plt.ylabel("Current (mA)")
    plt.legend()
    plt.grid()
    plt.show()


# Example usage and plotting
if __name__ == "__main__":
    main()
