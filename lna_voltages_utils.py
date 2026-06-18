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
I_MEAS_DATA = {  # 2026-02-17_16-10-09 channel 1
    1.102: 2.110e-03,
    1.103: 2.161e-03,
    1.105: 2.228e-03,
    1.107: 2.274e-03,
    1.110: 2.327e-03,
    1.113: 2.407e-03,
    1.117: 2.502e-03,
    1.118: 2.563e-03,
    1.121: 2.621e-03,
    1.122: 2.659e-03,
    1.125: 2.735e-03,
    1.127: 2.808e-03,
    1.129: 2.872e-03,
    1.131: 2.949e-03,
    1.133: 3.025e-03,
    1.137: 3.107e-03,
    1.139: 3.216e-03,
    1.141: 3.296e-03,
    1.145: 3.334e-03,
    1.147: 3.448e-03,
    1.149: 3.407e-03,
    1.151: 3.544e-03,
    1.152: 3.586e-03,
    1.154: 3.670e-03,
    1.155: 3.719e-03,
    1.157: 3.738e-03,
    1.159: 3.838e-03,
    1.162: 3.886e-03,
    1.165: 4.017e-03,
    1.167: 4.074e-03,
    1.168: 4.097e-03,
    1.170: 4.131e-03,
    1.172: 4.208e-03,
    1.175: 4.326e-03,
    1.176: 4.246e-03,
    1.179: 4.393e-03,
    1.183: 4.475e-03,
    1.184: 4.513e-03,
    1.185: 4.551e-03,
    1.188: 4.604e-03,
    1.190: 4.658e-03,
    1.193: 4.688e-03,
    1.195: 4.734e-03,
    1.196: 4.761e-03,
    1.200: 4.833e-03,
    1.202: 4.887e-03,
    1.203: 4.925e-03,
    1.206: 4.978e-03,
    1.208: 5.064e-03,
    1.212: 5.130e-03,
    1.215: 5.169e-03,
    1.217: 5.241e-03,
    1.219: 5.253e-03,
    1.220: 5.314e-03,
    1.222: 5.337e-03,
    1.224: 5.400e-03,
    1.228: 5.466e-03,
    1.229: 5.520e-03,
    1.231: 5.554e-03,
    1.233: 5.615e-03,
    1.236: 5.674e-03,
    1.238: 5.737e-03,
    1.242: 5.772e-03,
    1.243: 5.821e-03,
    1.247: 5.881e-03,
    1.248: 5.943e-03,
    1.251: 5.970e-03,
    1.252: 6.004e-03,
    1.253: 6.077e-03,
    1.254: 6.088e-03,
    1.256: 6.153e-03,
    1.258: 6.199e-03,
    1.260: 6.226e-03,
    1.261: 6.264e-03,
    1.262: 6.367e-03,
    1.263: 6.294e-03,
    1.265: 6.393e-03,
    1.267: 6.454e-03,
    1.269: 6.489e-03,
    1.270: 6.535e-03,
    1.272: 6.573e-03,
    1.274: 6.638e-03,
    1.275: 6.653e-03,
    1.278: 6.718e-03,
    1.280: 6.786e-03,
    1.283: 6.859e-03,
    1.285: 6.901e-03,
    1.286: 6.962e-03,
    1.290: 7.015e-03,
    1.293: 7.046e-03,
    1.294: 7.118e-03,
    1.295: 7.130e-03,
    1.296: 7.195e-03,
    1.298: 7.244e-03,
    1.301: 7.313e-03,
    1.302: 7.328e-03,
    1.306: 7.421e-03,
    1.307: 7.488e-03,
    1.308: 7.526e-03,
    1.309: 7.595e-03,
    1.312: 7.626e-03,
    1.314: 7.671e-03,
    1.315: 7.729e-03,
    1.318: 7.790e-03,
    1.319: 7.828e-03,
    1.320: 7.862e-03,
    1.321: 7.919e-03,
    1.323: 7.965e-03,
    1.325: 7.999e-03,
    1.326: 8.060e-03,
    1.329: 8.175e-03,
    1.330: 8.118e-03,
    1.332: 8.194e-03,
    1.334: 8.217e-03,
    1.335: 8.263e-03,
}
I_MEAS_DATA = {  # 2026-02-17_16-10-09 channel 12
    1.109: 2.075e-03,
    1.111: 2.136e-03,
    1.112: 2.178e-03,
    1.116: 2.228e-03,
    1.118: 2.304e-03,
    1.121: 2.369e-03,
    1.122: 2.445e-03,
    1.124: 2.506e-03,
    1.127: 2.567e-03,
    1.129: 2.632e-03,
    1.132: 2.720e-03,
    1.135: 2.834e-03,
    1.136: 2.903e-03,
    1.140: 2.972e-03,
    1.142: 3.033e-03,
    1.144: 3.078e-03,
    1.145: 3.170e-03,
    1.148: 3.242e-03,
    1.151: 3.307e-03,
    1.152: 3.319e-03,
    1.155: 3.425e-03,
    1.158: 3.590e-03,
    1.159: 3.529e-03,
    1.161: 3.654e-03,
    1.163: 3.700e-03,
    1.165: 3.754e-03,
    1.168: 3.826e-03,
    1.170: 3.872e-03,
    1.173: 3.944e-03,
    1.175: 3.986e-03,
    1.176: 4.044e-03,
    1.177: 4.101e-03,
    1.179: 4.131e-03,
    1.183: 4.196e-03,
    1.184: 4.242e-03,
    1.185: 4.314e-03,
    1.190: 4.394e-03,
    1.192: 4.444e-03,
    1.194: 4.505e-03,
    1.196: 4.555e-03,
    1.200: 4.618e-03,
    1.202: 4.677e-03,
    1.206: 4.740e-03,
    1.209: 4.818e-03,
    1.210: 4.845e-03,
    1.213: 4.887e-03,
    1.214: 4.925e-03,
    1.217: 4.944e-03,
    1.218: 5.005e-03,
    1.220: 5.058e-03,
    1.224: 5.127e-03,
    1.226: 5.177e-03,
    1.227: 5.219e-03,
    1.229: 5.241e-03,
    1.230: 5.291e-03,
    1.233: 5.337e-03,
    1.234: 5.375e-03,
    1.238: 5.446e-03,
    1.240: 5.482e-03,
    1.242: 5.550e-03,
    1.243: 5.585e-03,
    1.245: 5.638e-03,
    1.247: 5.661e-03,
    1.248: 5.688e-03,
    1.250: 5.737e-03,
    1.254: 5.817e-03,
    1.256: 5.878e-03,
    1.257: 5.917e-03,
    1.258: 5.966e-03,
    1.262: 6.010e-03,
    1.265: 6.111e-03,
    1.266: 6.081e-03,
    1.268: 6.180e-03,
    1.270: 6.229e-03,
    1.273: 6.290e-03,
    1.275: 6.313e-03,
    1.278: 6.382e-03,
    1.279: 6.428e-03,
    1.282: 6.487e-03,
    1.284: 6.599e-03,
    1.285: 6.561e-03,
    1.288: 6.645e-03,
    1.289: 6.691e-03,
    1.291: 6.748e-03,
    1.294: 6.828e-03,
    1.295: 6.783e-03,
    1.297: 6.916e-03,
    1.298: 6.870e-03,
    1.300: 6.966e-03,
    1.302: 7.004e-03,
    1.303: 7.050e-03,
    1.306: 7.164e-03,
    1.307: 7.114e-03,
    1.308: 7.179e-03,
    1.312: 7.236e-03,
    1.313: 7.301e-03,
    1.314: 7.343e-03,
    1.318: 7.404e-03,
    1.319: 7.477e-03,
    1.322: 7.523e-03,
    1.323: 7.572e-03,
    1.325: 7.607e-03,
    1.328: 7.675e-03,
    1.329: 7.736e-03,
    1.331: 7.789e-03,
    1.333: 7.881e-03,
    1.336: 7.904e-03,
    1.337: 7.973e-03,
    1.341: 8.058e-03,
    1.343: 8.114e-03,
    1.346: 8.202e-03,
    1.347: 8.236e-03,
    1.350: 8.266e-03,
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


def v_remote_from_fitted_coef(
    v_source_values,
    r_meas,
    r_highside,
    r_lowside,
    fitted_slope,
    fitted_intercept,
    v_bias_step=0.001,
):
    """
    v_source: float, source voltage or list of voltages
    r_meas: float, measured resistance of the DUT
    r_highside: float, high-side resistance
    r_lowside: float, low-side resistance
    fitted_slope: float, slope of the fitted line from measurement data
    fitted_intercept: float, intercept of the fitted line from measurement data
    """
    if not isinstance(v_source_values, (list, np.ndarray)):
        v_source_values = [v_source_values]
    else:
        v_source_values = v_source_values

    def i_meas_from_fitted(v_bias):
        return (fitted_slope * v_bias + fitted_intercept) / 1000  # Convert from mA to A

    v_bias_i_meas = []
    for v_source in v_source_values:
        v_bias_values = np.linspace(0, v_source, int(v_source / v_bias_step) + 1)
        v_i_values_idx = np.argmin(
            abs(
                v_remote(
                    v_source,
                    r_meas,
                    r_highside,
                    r_lowside,
                    i_meas_from_fitted(v_bias_values),
                )
                - v_bias_values
            )
        )

        v_bias_i_meas.append(
            (
                v_bias_values[v_i_values_idx],
                i_meas_from_fitted(v_bias_values)[v_i_values_idx],
            )
        )
    v_bias_i_meas = np.array(v_bias_i_meas)
    return v_bias_i_meas[:, 0], v_bias_i_meas[:, 1]


def main():
    # Fixed resistances
    r_LDO_set = 150000  # Ohms
    r_RTop = 4700  # Ohms
    r_RBot = 8200  # Ohms
    r_highside = 30  # Ohms
    r_lowside = 0.1  # Ohms
    r_meas = 10  # 1 kOhm DUT
    r_paral = 200_000  # Ohms
    # fitted_slope = 25.114
    # fitted_intercept = -25.492

    # Potentiometer is the main variable
    r_pot_values = np.linspace(0, 10000, 128)  # 0 to 10k Ohms

    # R parallel resistance is the secondary variable
    r_paral_values = np.array([200_000, 1e9])  # np.linspace(10000, 20000, 5)  # Ohms #
    # R switched resistance is the secondary variable
    r_switched_values = np.array([18000])  # np.linspace(10000, 20000, 5)  # Ohms #
    # R fixed resistance is the secondary variable
    r_fixed_values = np.array([18000])  # np.linspace(10000, 20000, 5)  # Ohms #

    # Fitted coefficients as secondary variable
    fitted_coef_sets = [
        {
            "fitted_slope": 25.11365258983602,
            "fitted_intercept": -25.155769981576846,
        },
        {
            "fitted_slope": 25.11365258983602,
            "fitted_intercept": -25.18254179305732,
        },
        {
            "fitted_slope": 25.362331911649207,
            "fitted_intercept": -25.864177674637084,
        },
        {
            "fitted_slope": 25.362331911649207,
            "fitted_intercept": -25.72204673601962,
        },
        {
            "fitted_slope": 25.929008973226683,
            "fitted_intercept": -26.129411642399134,
        },
        {
            "fitted_slope": 25.929008973226683,
            "fitted_intercept": -26.167940498675218,
        },
    ]
    v_source_open_list = []
    v_remote_open_from_data_list = []
    i_meas_open_from_data_list = []
    for fitted_coef in fitted_coef_sets:
        # Calculate voltages for each potentiometer value
        v_source_open = v_source(
            r_LDO_set, r_RBot, r_RTop, r_paral, False, r_pot_values
        )

        v_remote_open_from_data, i_meas_open_from_data = v_remote_from_fitted_coef(
            v_source_open,
            r_meas,
            r_highside,
            r_lowside,
            fitted_coef["fitted_slope"],
            fitted_coef["fitted_intercept"],
        )
        v_source_open_list.append(v_source_open)
        v_remote_open_from_data_list.append(v_remote_open_from_data)
        i_meas_open_from_data_list.append(i_meas_open_from_data)

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(
        r_pot_values,
        np.array(v_source_open_list).T,
        label="V_source (Switch Open)",
        # color="orange",
        marker="o",
        markersize=2,
    )
    plt.plot(
        r_pot_values,
        np.array(v_remote_open_from_data_list).T,
        label=f"V_remote (Switch Open) in range: min {min(v_remote_open_from_data_list[0]):.3f} V, max {max(v_remote_open_from_data_list[-1]):.3f} V",
        # color="brown",
        marker="o",
        markersize=2,
    )
    plt.legend()
    plt.ylabel("Voltage (V)")

    # use twin y-axis to plot i_meas
    ax2 = plt.gca().twinx()
    ax2.plot(
        r_pot_values,
        np.array(i_meas_open_from_data_list).T * 1000,  # Convert to mA for plotting
        label="I_meas (Switch Open) From Data (mA)",
        # color="magenta",
        marker="x",
        linestyle="--",
        markersize=2,
    )
    plt.title("Source and Remote Voltages vs Potentiometer Resistance")
    plt.xlabel("Potentiometer Resistance (Ohms)")
    plt.ylabel("Current (mA)")
    plt.legend()
    plt.grid()
    plt.show()


def _main():
    # Fixed resistances
    r_LDO_set = 150000  # Ohms
    r_switched = 9880  # Ohms
    r_fixed = 12400  # Ohms
    r_highside = 30  # Ohms
    r_lowside = 30  # Ohms
    r_meas = 10  # 1 kOhm DUT
    # r_paral = 18000  # Ohms

    # Potentiometer is the main variable
    r_pot_values = np.linspace(0, 10000, 128)  # 0 to 10k Ohms

    # R parallel resistance is the secondary variable
    r_paral_values = np.array([18000, 1e9])  # np.linspace(10000, 20000, 5)  # Ohms #
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
        label=f"V_remote (Switch Closed) From Data: min {min(v_remote_closed_from_data_list[0]):.3f} V, max {max(v_remote_closed_from_data_list[-1]):.3f} V",
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
