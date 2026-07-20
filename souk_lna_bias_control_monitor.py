import time
from typing import List, Literal, Dict, Tuple, Union
from dataclasses import dataclass
import logging
from lna_voltages_utils import v_remote
from smbus2 import SMBus

from ad511_0_2_4bcpz_5_10_80 import AD511_0_2_4BCPZ_5_10_80HWConfig
from ltc2481cdd import LTC2481CDDHWConfig
from lna_monitor import LNAMonitor, LNAMonitorHWConfig
from tca9548 import TCA9548
from max732_8_9 import MAX732_8_9

REFDES_LNA_MONITOR_CHN_MAP = {
    "M17": {1: ["root", 0]},
    "M18": {2: ["root", 1]},
    "M19": {3: ["root", 2]},
    "M20": {4: ["root", 3]},
    "M21": {5: ["root", 4]},
    "M22": {6: ["root", 5]},
    "M23": {7: ["root", 6]},
    "M24": {8: ["leaf", 0]},
    "M25": {9: ["leaf", 1]},
    "M26": {10: ["leaf", 2]},
    "M27": {11: ["leaf", 3]},
    "M28": {12: ["leaf", 4]},
    "M29": {13: ["leaf", 5]},
    "M30": {14: ["leaf", 6]},
}

REFDES_OE_CHN_MAP = {
    1: ["U7", 4],
    2: ["U6", 7],
    3: ["U6", 4],
    4: ["U6", 5],
    5: ["U6", 3],
    6: ["U6", 2],
    7: ["U6", 1],
    8: ["U6", 0],
    9: ["U7", 2],
    10: ["U7", 1],
    11: ["U7", 0],
    12: ["U7", 7],
    13: ["U7", 6],
    14: ["U7", 5],
}

SWITCH_ADDR_RESISTOR_MAP = {
    "root": {
        "A0": {"R8": "high", "R10": "low"},
        "A1": {"R5": "high", "R7": "low"},
        "A2": {"R4": "high", "R6": "low"},
    },
    "leaf": {
        "A0": {"R14": "high", "R15": "low"},
        "A1": {"R11": "high", "R13": "low"},
        "A2": {"R9": "high", "R12": "low"},
    },
}

OE_ADDR_RESISTOR_MAP = {
    "U6": {
        "ad0": {"R28": "high", "R30": "low"},
        "ad1": {"R29": "high", "R31": "low"},
        "ad2": {"R32": "high", "R33": "low"},
    },
    "U7": {
        "ad0": {"R34": "high", "R36": "low"},
        "ad1": {"R35": "high", "R37": "low"},
        "ad2": {"R38": "high", "R39": "low"},
    },
}

ROOT_LEAF_CONN = 7

OE_PIN_I2C_SWITCH_RESET = 6

AWAIT_TURN_ON_DELAY = 1  # seconds


@dataclass(frozen=True)
class SOUKLNABiasControlMonitorHWConfig:
    lna_monitor_hw_configs: Dict[str, Union[LNAMonitorHWConfig, None]]
    r9_r12: Literal["R9", "R12"]  # resistor selection for i2c switch address
    r8_r10: Literal["R8", "R10"]  # resistor selection for i2c switch address
    r7_r5: Literal["R7", "R5"]  # resistor selection for i2c switch address
    r11_r13: Literal["R11", "R13"]  # resistor selection for i2c switch address
    r14_r15: Literal["R14", "R15"]  # resistor selection for i2c switch address
    r6_r4: Literal["R6", "R4"]  # resistor selection for i2c switch address
    r28_r30: Literal["R28", "R30"]  # resistor selection for OE i2c address
    r29_r31: Literal["R29", "R31"]  # resistor selection for OE i2c address
    r32_r33: Literal["R32", "R33"]  # resistor selection for OE i2c address
    r34_r36: Literal["R34", "R36"]  # resistor selection for OE i2c address
    r35_r37: Literal["R35", "R37"]  # resistor selection for OE i2c address
    r38_r39: Literal["R38", "R39"]  # resistor selection for OE i2c address
    u6_dev_type: Literal["MAX7328", "MAX7329"]  # OE device type
    u7_dev_type: Literal["MAX7328", "MAX7329"]  # OE device type

    def __post_init__(self):
        if self.r14_r15 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A0"].keys():
            raise ValueError(
                f"r14_r15 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A0'].keys()}"
            )
        if self.r11_r13 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A1"].keys():
            raise ValueError(
                f"r11_r13 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A1'].keys()}"
            )
        if self.r9_r12 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A2"].keys():
            raise ValueError(
                f"r9_r12 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A2'].keys()}"
            )
        if self.r8_r10 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A0"].keys():
            raise ValueError(
                f"r8_r10 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A0'].keys()}"
            )
        if self.r7_r5 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A1"].keys():
            raise ValueError(
                f"r7_r5 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A1'].keys()}"
            )
        if self.r6_r4 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A2"].keys():
            raise ValueError(
                f"r6_r4 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A2'].keys()}"
            )

        if self.r28_r30 not in OE_ADDR_RESISTOR_MAP["U6"]["ad0"].keys():
            raise ValueError(
                f"r28_r30 must be one of {OE_ADDR_RESISTOR_MAP['U6']['ad0'].keys()}"
            )
        if self.r29_r31 not in OE_ADDR_RESISTOR_MAP["U6"]["ad1"].keys():
            raise ValueError(
                f"r29_r31 must be one of {OE_ADDR_RESISTOR_MAP['U6']['ad1'].keys()}"
            )
        if self.r32_r33 not in OE_ADDR_RESISTOR_MAP["U6"]["ad2"].keys():
            raise ValueError(
                f"r32_r33 must be one of {OE_ADDR_RESISTOR_MAP['U6']['ad2'].keys()}"
            )
        if self.r34_r36 not in OE_ADDR_RESISTOR_MAP["U7"]["ad0"].keys():
            raise ValueError(
                f"r34_r36 must be one of {OE_ADDR_RESISTOR_MAP['U7']['ad0'].keys()}"
            )
        if self.r35_r37 not in OE_ADDR_RESISTOR_MAP["U7"]["ad1"].keys():
            raise ValueError(
                f"r35_r37 must be one of {OE_ADDR_RESISTOR_MAP['U7']['ad1'].keys()}"
            )
        if self.r38_r39 not in OE_ADDR_RESISTOR_MAP["U7"]["ad2"].keys():
            raise ValueError(
                f"r38_r39 must be one of {OE_ADDR_RESISTOR_MAP['U7']['ad2'].keys()}"
            )
        if self.u6_dev_type not in ["MAX7328", "MAX7329"]:
            raise ValueError("u6_dev_type must be either 'MAX7328' or 'MAX7329'")
        if self.u7_dev_type not in ["MAX7328", "MAX7329"]:
            raise ValueError("u7_dev_type must be either 'MAX7328' or 'MAX7329'")

        for key, lna_monitor in self.lna_monitor_hw_configs.items():
            if lna_monitor is not None and not isinstance(
                lna_monitor, LNAMonitorHWConfig
            ):
                raise ValueError(
                    "All lna_monitor_hw_configs values must be of type LNAMonitorHWConfig or None."
                )
            if key not in REFDES_LNA_MONITOR_CHN_MAP:
                raise ValueError(f"Invalid LNA monitor reference designator: {key}")


class SOUKLNABiasControlMonitor:
    def __init__(self, i2c_bus: SMBus, hw_config: SOUKLNABiasControlMonitorHWConfig):
        self._oe_u6 = MAX732_8_9(
            dev_name="oe_u6",
            i2c_bus=i2c_bus,
            ad2=OE_ADDR_RESISTOR_MAP["U6"]["ad2"][hw_config.r32_r33],
            ad1=OE_ADDR_RESISTOR_MAP["U6"]["ad1"][hw_config.r29_r31],
            ad0=OE_ADDR_RESISTOR_MAP["U6"]["ad0"][hw_config.r28_r30],
            dev_type=hw_config.u6_dev_type,
        )
        self._oe_u7 = MAX732_8_9(
            dev_name="oe_u7",
            i2c_bus=i2c_bus,
            ad2=OE_ADDR_RESISTOR_MAP["U7"]["ad2"][hw_config.r38_r39],
            ad1=OE_ADDR_RESISTOR_MAP["U7"]["ad1"][hw_config.r35_r37],
            ad0=OE_ADDR_RESISTOR_MAP["U7"]["ad0"][hw_config.r34_r36],
            dev_type=hw_config.u7_dev_type,
        )
        self._oe_u6.pulse_gpio_bit(OE_PIN_I2C_SWITCH_RESET, polarity=False)
        self.disable_all_lna_bias_outputs()
        self._root_switch = TCA9548(
            dev_name="root_switch",
            i2c_bus=i2c_bus,
            a0=SWITCH_ADDR_RESISTOR_MAP["root"]["A0"][hw_config.r8_r10],
            a1=SWITCH_ADDR_RESISTOR_MAP["root"]["A1"][hw_config.r7_r5],
            a2=SWITCH_ADDR_RESISTOR_MAP["root"]["A2"][hw_config.r6_r4],
        )
        self._root_switch.turn_off_channel()
        self._root_switch.turn_on_channel(ROOT_LEAF_CONN)
        self._leaf_switch = TCA9548(
            dev_name="leaf_switch",
            i2c_bus=i2c_bus,
            a0=SWITCH_ADDR_RESISTOR_MAP["leaf"]["A0"][hw_config.r14_r15],
            a1=SWITCH_ADDR_RESISTOR_MAP["leaf"]["A1"][hw_config.r11_r13],
            a2=SWITCH_ADDR_RESISTOR_MAP["leaf"]["A2"][hw_config.r9_r12],
        )
        self._leaf_switch.turn_off_channel()
        self._lna_monitors: Dict[str, Union[LNAMonitor, None]] = {}
        for refdes, lna_hw_config in hw_config.lna_monitor_hw_configs.items():
            if lna_hw_config is not None:
                logging.info(
                    f"Initialising monitor channel {list(REFDES_LNA_MONITOR_CHN_MAP[refdes].keys())[0]} ..."
                )
                self._turn_on_channel(
                    list(REFDES_LNA_MONITOR_CHN_MAP[refdes].keys())[0]
                )
                try:
                    self._lna_monitors[refdes] = LNAMonitor(
                        i2c_bus=i2c_bus, hw_config=lna_hw_config
                    )
                except OSError as e:
                    logging.warning(
                        f"Initialising monitor channel {list(REFDES_LNA_MONITOR_CHN_MAP[refdes].keys())[0]} failed: {e}, removed from the controlling channel list."
                    )
                    self._lna_monitors[refdes] = None
                self._turn_off_all_channels()
            else:
                self._lna_monitors[refdes] = None
        self._hw_config = hw_config

    @property
    def bias_oe_status(self) -> Dict[int, bool]:
        """Gets the bias output enable status for all channels.
        Returns:
            dict[int, bool]: The bias output enable status as {chn: status}.
        """
        status: Dict[int, bool] = {}
        for chn in range(1, 15):
            oe_dev_name, oe_bit = REFDES_OE_CHN_MAP[chn]
            if oe_dev_name == "U6":
                status[chn] = self._oe_u6.get_gpio_bit([oe_bit])[0]
            elif oe_dev_name == "U7":
                status[chn] = self._oe_u7.get_gpio_bit([oe_bit])[0]
            else:
                raise ValueError(f"Invalid OE device name: {oe_dev_name}")
        return status

    @property
    def lna_local_voltage_ranges(self) -> Dict[int, Tuple[float, float]]:
        """Gets the achievable local voltage ranges for all LNAs.
        Returns:
            dict[int, tuple[float, float]]: The local voltage ranges as {chn: (min_voltage, max_voltage)}.
        """
        voltage_ranges: Dict[int, Tuple[float, float]] = {}
        for refdes, lna_monitor in self._lna_monitors.items():
            chn = list(REFDES_LNA_MONITOR_CHN_MAP[refdes].keys())[0]
            if lna_monitor is None:
                voltage_ranges[chn] = (float("nan"), float("nan"))
            else:
                voltage_ranges[chn] = lna_monitor.local_voltage_range
        return voltage_ranges

    def read_lna_status(
        self,
        chn: Union[int, List[int]],
    ) -> Dict[int, Dict[str, float]]:
        """Reads the local voltage based on the current DAC resistance.
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
        Returns:
            dict[int, dict[str, float]]: The lna status values as {chn: {"remote voltage": ..., "local voltage": ..., "bias current": ..., "output enable": ...}}.
        """
        if isinstance(chn, int):
            chn = [chn]
        for c in chn:
            if c not in [
                list(chn_map.keys())[0]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            ]:
                raise ValueError(f"Invalid channel number: {c}")
        status: Dict[int, Dict[str, float]] = {}
        for c in chn:
            refdes = next(
                key
                for key, value in REFDES_LNA_MONITOR_CHN_MAP.items()
                if list(value.keys())[0] == c
            )
            lna_monitor = self._lna_monitors.get(refdes, None)
            if lna_monitor is None:
                status[c] = {
                    "remote voltage": float("nan"),
                    "local voltage": float("nan"),
                    "bias current": float("nan"),
                    "output enable": float("nan"),
                }
            else:
                self._turn_on_channel(c)
                status[c] = {
                    "remote voltage": lna_monitor.read_remote_voltage(),
                    "local voltage": lna_monitor.read_local_voltage(),
                    "bias current": lna_monitor.read_bias_current(),
                    "output enable": self.bias_oe_status.get(c, float("nan")),
                }
                self._turn_off_all_channels()
        return status

    def enable_lna_bias_output(self, chn: Union[int, List[int]]) -> None:
        """Enables the bias output for the specified channel(s).
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
            oe (bool): The output enable state (True to enable, False to disable).
        """
        if isinstance(chn, int):
            chn = [chn]
        await_turn_on = False
        # Find the channels that need to be turned on only
        oe_status_to_set = {
            c: True for c in chn if not self.bias_oe_status.get(c, False)
        }
        if oe_status_to_set:
            await_turn_on = True

        for c in chn:
            logging.info(f"Enable LNA chn {c} output ...")
            oe_dev_name, oe_bit = REFDES_OE_CHN_MAP[c]
            if oe_dev_name == "U6":
                self._oe_u6.set_gpio_bit([oe_bit], [True])
            elif oe_dev_name == "U7":
                self._oe_u7.set_gpio_bit([oe_bit], [True])
            else:
                raise ValueError(f"Invalid OE device name: {oe_dev_name}")

        if await_turn_on:
            time.sleep(AWAIT_TURN_ON_DELAY)

    def disable_lna_bias_output(self, chn: Union[int, List[int]]) -> None:
        """Disables the bias output for the specified channel(s).
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
        """
        if isinstance(chn, int):
            chn = [chn]

        for c in chn:
            logging.info(f"Disable LNA chn {c} output ...")
            oe_dev_name, oe_bit = REFDES_OE_CHN_MAP[c]
            if oe_dev_name == "U6":
                self._oe_u6.set_gpio_bit([oe_bit], [False])
            elif oe_dev_name == "U7":
                self._oe_u7.set_gpio_bit([oe_bit], [False])
            else:
                raise ValueError(f"Invalid OE device name: {oe_dev_name}")

    def enable_all_lna_bias_outputs(self) -> None:
        """Enables the bias output for all channels."""
        for c in REFDES_OE_CHN_MAP.keys():
            self.enable_lna_bias_output(c)

    def disable_all_lna_bias_outputs(self) -> None:
        """Disables the bias output for all channels."""
        for c in REFDES_OE_CHN_MAP.keys():
            self.disable_lna_bias_output(c)

    def set_lna_bias_local(
        self, chn: Union[int, List[int]], v_local: float
    ) -> Dict[int, float]:
        """Calculates and sets the DAC resistance to achieve the desired local voltage.
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
            v_local (float): Desired local voltage in volts.
        Returns:
            dict[int, float]: The actual local voltages set after adjusting the DAC.
        """
        if isinstance(chn, int):
            chn = [chn]
        for c in chn:
            if c not in [
                list(chn_map.keys())[0]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            ]:
                raise ValueError(f"Invalid channel number: {c}")
        actual_v_locals: Dict[int, float] = {}
        for c in chn:
            refdes = next(
                key
                for key, value in REFDES_LNA_MONITOR_CHN_MAP.items()
                if list(value.keys())[0] == c
            )
            lna_monitor = self._lna_monitors.get(refdes, None)
            if lna_monitor is None:
                actual_v_locals[c] = float("nan")
            else:
                self._turn_on_channel(c)
                actual_v_locals[c] = lna_monitor.set_local_voltage(v_local)
                self._turn_off_all_channels()
        return actual_v_locals

    def _turn_on_channel(self, chn: int) -> None:
        self._leaf_switch.turn_off_channel()
        self._root_switch.turn_off_channel()
        self._root_switch.turn_on_channel(ROOT_LEAF_CONN)

        if chn in [
            list(chn_map.keys())[0]
            for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            if list(chn_map.values())[0][0] == "root"
        ]:
            self._root_switch.turn_on_channel(
                [
                    list(chn_map.values())[0][1]
                    for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
                    if list(chn_map.keys())[0] == chn
                ][0]
            )
        elif chn in [
            list(chn_map.keys())[0]
            for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            if list(chn_map.values())[0][0] == "leaf"
        ]:
            self._leaf_switch.turn_on_channel(
                [
                    list(chn_map.values())[0][1]
                    for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
                    if list(chn_map.keys())[0] == chn
                ][0]
            )
        else:
            raise ValueError(f"Invalid channel number: {chn}")

    def _turn_off_all_channels(
        self, except_chn: Union[int, None] = ROOT_LEAF_CONN
    ) -> None:
        self._leaf_switch.turn_off_channel()
        self._root_switch.turn_off_channel()
        if except_chn is not None:
            self._root_switch.turn_on_channel(except_chn)

    def set_lna_bias_remote(
        self,
        chn: Union[int, List[int]],
        v_local: Union[float, List[float]],
        blind: bool = True,
    ) -> Dict[int, Tuple[float, str]]:
        """Calculates and sets the DAC resistance to achieve the desired local voltage.
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
            v_local (float): Desired local voltage in volts, or
            v_local (list[float]): A list of desired local voltages in volts.
            blind (bool): If True, skip checking the estimated LNA voltage validity, only check remote voltage.
        Returns:
            dict[int, Tuple[float, str]]: The actual local voltages set after adjusting the DAC and failed message.
        """
        if isinstance(chn, int):
            chn = [chn]
        for c in chn:
            if c not in [
                list(chn_map.keys())[0]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            ]:
                raise ValueError(f"Invalid channel number: {c}")
        if isinstance(v_local, float):
            v_local = [v_local] * len(chn)
        if len(v_local) != len(chn):
            raise ValueError("Length of v_local must match length of chn.")
        actual_v_locals: Dict[int, Tuple[float, str]] = {}
        estimate_v_remotes: Dict[int, List[float]] = {}
        for c, v in zip(chn, v_local):
            refdes = next(
                key
                for key, value in REFDES_LNA_MONITOR_CHN_MAP.items()
                if list(value.keys())[0] == c
            )
            logging.info(
                f"Setting LNA chn {c} at REFDES {refdes} to target remote voltage {v:.3f} V (blind={blind})..."
            )
            lna_monitor = self._lna_monitors.get(refdes, None)
            if lna_monitor is None:
                actual_v_locals[c] = (float("nan"), "LNA monitor not configured.")
            else:
                self._turn_on_channel(c)
                local_voltage_range = lna_monitor.local_voltage_range
                # set to lowest local voltage first
                lna_monitor.set_local_voltage(local_voltage_range[0])
                estimate_v_remotes[c] = []
                while True:
                    v_estimation = lna_monitor.estimate_lna_voltage()
                    estimate_v_remotes[c].append(v_estimation)
                    if not blind:
                        if not (
                            estimate_v_remotes[c][-1]["v_remote"]
                            > estimate_v_remotes[c][-1]["v_lna"]
                            > 0
                        ):
                            actual_v_locals[c] = (
                                estimate_v_remotes[c][-1]["v_remote"],
                                f"Cannot set remote voltage for channel {c}, "
                                + f"because estimated LNA voltage is not between 0 V and remote voltage {estimate_v_remotes[c][-1]['v_remote']:.3f} V. "
                                + "Resistor values or switch status may be incorrect for this channel.",
                            )
                            break
                        if estimate_v_remotes[c][-1]["v_lna"] >= v:
                            if len(estimate_v_remotes[c]) == 1:
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_lna"],
                                    "Lowest local voltage already exceeds desired remote voltage.",
                                )
                            elif abs(estimate_v_remotes[c][-2]["v_lna"] - v) < abs(
                                estimate_v_remotes[c][-1]["v_lna"] - v
                            ):
                                lna_monitor._r_dac.increase_tap_pos()
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-2]["v_lna"],
                                    "",
                                )
                            else:
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_lna"],
                                    "",
                                )
                            break
                        else:
                            decr_tap = lna_monitor._r_dac.decrease_tap_pos()
                            if not decr_tap:
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_lna"],
                                    f"Reached maximum local voltage for channel {c} but desired remote voltage not achieved.",
                                )
                                break
                    else:
                        if not self.bias_oe_status.get(c, False):
                            self.enable_lna_bias_output(c)
                        if estimate_v_remotes[c][-1]["v_remote"] >= v:
                            if len(estimate_v_remotes[c]) == 1:
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_remote"],
                                    "Lowest local voltage already exceeds desired remote voltage.",
                                )
                            elif abs(estimate_v_remotes[c][-1]["v_remote"] - v) < abs(
                                estimate_v_remotes[c][-2]["v_remote"] - v
                            ):
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_remote"],
                                    "",
                                )
                            else:
                                lna_monitor._r_dac.increase_tap_pos()
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-2]["v_remote"],
                                    "",
                                )
                            break
                        else:
                            decr_tap = lna_monitor._r_dac.decrease_tap_pos()
                            if not decr_tap:
                                actual_v_locals[c] = (
                                    estimate_v_remotes[c][-1]["v_remote"],
                                    f"Reached maximum local voltage for channel {c} but desired remote voltage not achieved.",
                                )
                                break
                self._turn_off_all_channels()
        return actual_v_locals


def read_set_local_voltage_demo(
    souk_lna_monitor: SOUKLNABiasControlMonitor, chn_idxes: List[int]
) -> None:
    import math
    import random

    lna_local_range = souk_lna_monitor.lna_local_voltage_ranges
    while True:
        for chn in chn_idxes:
            v_min, v_max = lna_local_range[chn]
            if any(math.isnan(v_range) for v_range in (v_min, v_max)):
                logging.info(f"Skipping LNA chn {chn} as it is not configured.")
                continue
            else:
                logging.info(
                    f"LNA chn {chn} local voltage range: {v_min:.3f} V - {v_max:.3f} V"
                )
            v_set = random.uniform(v_min, v_max)
            actual_v_set = souk_lna_monitor.set_lna_bias_local(chn=chn, v_local=v_set)
            logging.info(
                f"Set LNA chn {chn} local voltage to {v_set:.3f} V, actual: {actual_v_set[chn]:.3f} V"
            )

            status = souk_lna_monitor.read_lna_status(chn=chn_idxes)
            logging.info(
                f"LNA chn {chn} status before enable output: Remote Voltage = {status[chn]['remote voltage']:.3f} V, "
                + f"Local Voltage = {status[chn]['local voltage']:.3f} V, "
                + f"Bias Current = {status[chn]['bias current'] * 1e3:.3f} mA"
                + f"Output Enable = {status[chn]['output enable']}"
            )
            souk_lna_monitor.enable_lna_bias_output(chn=chn_idxes)
            status = souk_lna_monitor.read_lna_status(chn=chn_idxes)
            logging.info(
                f"LNA chn {chn} status after enable output: Remote Voltage = {status[chn]['remote voltage']:.3f} V, "
                + f"Local Voltage = {status[chn]['local voltage']:.3f} V, "
                + f"Bias Current = {status[chn]['bias current'] * 1e3:.3f} mA"
                + f"Output Enable = {status[chn]['output enable']}"
            )
            souk_lna_monitor.disable_lna_bias_output(chn=chn_idxes)


def main():
    import argparse
    from datetime import datetime
    import os

    parser = argparse.ArgumentParser(description="SOUK LNA Bias Control Monitor")
    parser.add_argument(
        "--channels",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14],  # 9 disabled
        help="List of LNA channel indices to monitor, starting index 1",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Demo for reading and setting local voltage",
    )
    parser.add_argument(
        "--remote", action="store_true", help="Demo for setting remote voltage"
    )
    parser.add_argument(
        "--status", action="store_true", help="Demo for getting LNA bias status"
    )
    parser.add_argument(
        "--value",
        type=float,
        default=1.2,
        help="Voltage value for setting remote voltage demo",
    )
    # hardware version 2 confict with non blind mode, so disable blind mode for now
    # parser.add_argument(
    #     "--blind",
    #     action="store_true",
    #     default=False,
    #     help="Blindly setting remote voltage",
    # )

    parser.add_argument(
        "--disable_output",
        action="store_true",
        help="Disable LNA bias output after setting",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode logging",
    )

    args = parser.parse_args()

    now = datetime.now()
    datetime_str = now.strftime("%Y-%m-%d_%H-%M-%S")

    os.makedirs(".logdata", exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                f".logdata/souk_lna_bias_control_monitor_{datetime_str}.log", mode="w"
            ),
            logging.StreamHandler(),
        ],
    )
    logging.info("arguments: " + str(args))

    i2c_bus = SMBus(0)

    hw_config = SOUKLNABiasControlMonitorHWConfig(
        lna_monitor_hw_configs={
            "M17": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M18": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M19": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M20": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M21": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M22": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M23": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M24": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M25": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M26": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M27": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M28": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M29": LNAMonitorHWConfig.default_config(hw_version="v2"),
            "M30": LNAMonitorHWConfig.default_config(hw_version="v2"),
        },
        r9_r12="R12",
        r8_r10="R10",
        r7_r5="R5",
        r11_r13="R11",
        r14_r15="R14",
        r6_r4="R6",
        r28_r30="R28",
        r29_r31="R29",
        r32_r33="R32",
        r34_r36="R36",
        r35_r37="R35",
        r38_r39="R38",
        u6_dev_type="MAX7329",
        u7_dev_type="MAX7329",
    )

    souk_lna_monitor = SOUKLNABiasControlMonitor(i2c_bus, hw_config)

    if args.local:
        read_set_local_voltage_demo(souk_lna_monitor, args.channels)
    if args.disable_output:
        souk_lna_monitor.disable_lna_bias_output(args.channels)
        logging.info(f"Disabled LNA bias output for channels: {args.channels}")
    if args.remote:
        result = souk_lna_monitor.set_lna_bias_remote(
            chn=args.channels, v_local=args.value, blind=True
        )
        status = souk_lna_monitor.read_lna_status(chn=args.channels)
        for chn in args.channels:
            logging.info(
                f"Set LNA chn {chn} remote voltage to {args.value:.3f} V, "
                + f"actual: {result[chn][0]:.3f} V, message: {result[chn][1]}"
            )
            logging.info(
                f"LNA chn {chn} status: Remote Voltage = {status[chn]['remote voltage']:.3f} V, "
                + f"Local Voltage = {status[chn]['local voltage']:.3f} V, "
                + f"Bias Current = {status[chn]['bias current'] * 1e3:.3f} mA, "
                + f"Output Enable = {status[chn]['output enable']}"
            )
    if args.status:
        status = souk_lna_monitor.read_lna_status(chn=args.channels)
        for chn in args.channels:
            logging.info(
                f"LNA chn {chn} status: Remote Voltage = {status[chn]['remote voltage']:.3f} V, "
                + f"Local Voltage = {status[chn]['local voltage']:.3f} V, "
                + f"Bias Current = {status[chn]['bias current'] * 1e3:.3f} mA, "
                + f"Output Enable = {status[chn]['output enable']}"
            )
    if args.disable_output:
        souk_lna_monitor.disable_lna_bias_output(args.channels)
        logging.info(f"Disabled LNA bias output for channels: {args.channels}")


if __name__ == "__main__":
    main()
