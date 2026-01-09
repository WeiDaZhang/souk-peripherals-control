import numpy as np
import matplotlib.pyplot as plt


def v_source(r_switched, r_fixed, r_paral, switch_state, r_pot, i_set=1e-4):
    """
    r_set: list or array of 3 fixed resistances [R1, R2, R3]
    switch_state: boolean, True if the switch is closed, False if open
    r_pot: float, resistance of the potentiometer
    i_set: float, set current of the LDO, default is 100 µA
    Returns the source voltage based on the configuration.
    """
    return i_set * (
        (0 if switch_state else r_switched)
        + r_fixed
        + r_paral * r_pot / (r_paral + r_pot)
    )


def v_remote(v_source, r_meas, r_highside, r_lowside, i_meas):
    """
    r_meas: float, measured resistance of the DUT
    r_highside: float, high-side resistance
    r_lowside: float, low-side resistance
    i_meas: float, measurement current
    """
    return v_source - i_meas * (r_meas + r_highside + r_lowside)


def main():
    # Fixed resistances
    r_switched = 2500  # Ohms
    r_fixed = 15000  # Ohms
    r_highside = 60  # Ohms
    r_lowside = 30  # Ohms
    i_meas = 4e-3  # 4 mA
    r_meas = 100  # 1 kOhm DUT

    # Potentiometer is the main variable
    r_pot_values = np.linspace(0, 10000, 128)  # 0 to 10k Ohms

    # R parallel resistance is the secondary variable
    r_paral_values = np.array([10000])  # np.linspace(10000, 20000, 5)  # Ohms

    v_source_closed_list = []
    v_source_open_list = []
    v_remote_closed_list = []
    v_remote_open_list = []
    # Calculate voltages for each potentiometer value
    for r_paral in r_paral_values:
        v_source_closed = v_source(r_switched, r_fixed, r_paral, True, r_pot_values)
        v_source_open = v_source(r_switched, r_fixed, r_paral, False, r_pot_values)
        v_remote_closed = v_remote(
            v_source_closed, r_meas, r_highside, r_lowside, i_meas
        )
        v_remote_open = v_remote(v_source_open, r_meas, r_highside, r_lowside, i_meas)
        v_source_closed_list.append(v_source_closed)
        v_source_open_list.append(v_source_open)
        v_remote_closed_list.append(v_remote_closed)
        v_remote_open_list.append(v_remote_open)
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
        np.array(v_remote_closed_list).T,
        label="V_remote (Switch Closed)",
        color="green",
        marker="o",
        markersize=2,
    )
    plt.plot(
        r_pot_values,
        np.array(v_remote_open_list).T,
        label="V_remote (Switch Open)",
        color="red",
        marker="o",
        markersize=2,
    )
    plt.title("Source and Remote Voltages vs Potentiometer Resistance")
    plt.xlabel("Potentiometer Resistance (Ohms)")
    plt.ylabel("Voltage (V)")
    plt.legend()
    plt.grid()
    plt.show()


# Example usage and plotting
if __name__ == "__main__":
    main()
