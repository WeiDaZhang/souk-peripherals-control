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
    r_fixed = 18000  # Ohms
    r_highside = 30  # Ohms
    r_lowside = 30  # Ohms
    r_meas = 100  # 1 kOhm DUT
    r_paral = 18000  # Ohms

    # Potentiometer is the main variable
    r_pot_values = np.linspace(0, 10000, 128)  # 0 to 10k Ohms

    # R parallel resistance is the secondary variable
    r_paral_values = np.array(
        [18000, 36000, 120000]
    )  # np.linspace(10000, 20000, 5)  # Ohms #
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
