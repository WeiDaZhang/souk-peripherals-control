from typing import Literal
from dataclasses import dataclass

from smbus2 import SMBus

from ad511_0_2_4bcpz_5_10_80 import AD511_0_2_4BCPZ_5_10_80HWConfig
from ltc2481cdd import LTC2481CDDHWConfig
from lna_monitor import LNAMonitor, LNAMonitorHWConfig
from tca9548 import TCA9548

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

SWITCH_ADDR_RESISTOR_MAP = {
    "root": {
        "A0": {"R8": "high", "R10": "low"},
        "A1": {"R7": "high", "R5": "low"},
        "A2": {"R6": "high", "R4": "low"},
    },
    "leaf": {
        "A0": {"R15": "high", "R14": "low"},
        "A1": {"R13": "high", "R11": "low"},
        "A2": {"R12": "high", "R9": "low"},
    },
}

ROOT_LEAF_CONN = 7


@dataclass(frozen=True)
class SOUKLNABiasControlMonitorHWConfig:
    lna_monitor_hw_configs: dict[str, LNAMonitorHWConfig | None]
    r9_r12: Literal["R9", "R12"]  # resistor selection for i2c address
    r8_r10: Literal["R8", "R10"]  # resistor selection for i2c address
    r7_r5: Literal["R7", "R5"]  # resistor selection for i2c address
    r11_r13: Literal["R11", "R13"]  # resistor selection for i2c address
    r14_r15: Literal["R14", "R15"]  # resistor selection for i2c address
    r6_r4: Literal["R6", "R4"]  # resistor selection for i2c address

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
        self._lna_monitors: dict[str, LNAMonitor | None] = {}
        for refdes, lna_hw_config in hw_config.lna_monitor_hw_configs.items():
            if lna_hw_config is not None:
                self._lna_monitors[refdes] = LNAMonitor(
                    i2c_bus=i2c_bus, hw_config=lna_hw_config
                )
            else:
                self._lna_monitors[refdes] = None
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
        self._hw_config = hw_config

    @property
    def lna_local_voltage_ranges(self) -> dict[int, tuple[float, float]]:
        """Gets the achievable local voltage ranges for all LNAs.
        Returns:
            dict[int, tuple[float, float]]: The local voltage ranges as {chn: (min_voltage, max_voltage)}.
        """
        voltage_ranges: dict[int, tuple[float, float]] = {}
        for refdes, lna_monitor in self._lna_monitors.items():
            chn = list(REFDES_LNA_MONITOR_CHN_MAP[refdes].keys())[0]
            if lna_monitor is None:
                voltage_ranges[chn] = (float("nan"), float("nan"))
            else:
                voltage_ranges[chn] = lna_monitor.get_local_voltage_range
        return voltage_ranges

    def read_lna_status(
        self,
        chn: int | list[int],
    ) -> dict[int, dict[str, float]]:
        """Reads the local voltage based on the current DAC resistance.
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
        Returns:
            dict[int, dict[str, float]]: The lna status values as {chn: {"remote": ..., "local": ..., "bias": ...}}.
        """
        if isinstance(chn, int):
            chn = [chn]
        for c in chn:
            if c not in [
                list(chn_map.keys())[0]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            ]:
                raise ValueError(f"Invalid channel number: {c}")
        status: dict[int, dict[str, float]] = {}
        for c in chn:
            refdes = next(
                key
                for key, value in REFDES_LNA_MONITOR_CHN_MAP.items()
                if list(value.keys())[0] == c
            )
            lna_monitor = self._lna_monitors.get(refdes, None)
            if lna_monitor is None:
                status[c] = {
                    "remote": float("nan"),
                    "local": float("nan"),
                    "bias": float("nan"),
                }
            else:
                self._turn_on_channel(c)
                status[c] = {
                    "remote": lna_monitor.read_remote_voltage(),
                    "local": lna_monitor.read_local_voltage(),
                    "bias": lna_monitor.read_bias_current(),
                }
                self._turn_off_all_channels()
        return status

    def set_lna_bias_local(
        self, chn: int | list[int], v_local: float
    ) -> dict[int, float]:
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
        actual_v_locals: dict[int, float] = {}
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
                list(chn_map.values())[0][1]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
                if list(chn_map.keys())[0] == chn
            )
        elif chn in [
            list(chn_map.keys())[0]
            for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
            if list(chn_map.values())[0][0] == "leaf"
        ]:
            self._leaf_switch.turn_on_channel(
                list(chn_map.values())[0][1]
                for chn_map in list(REFDES_LNA_MONITOR_CHN_MAP.values())
                if list(chn_map.keys())[0] == chn
            )
        else:
            raise ValueError(f"Invalid channel number: {chn}")

    def _turn_off_all_channels(self, except_chn: int | None = ROOT_LEAF_CONN) -> None:
        self._leaf_switch.turn_off_channel()
        self._root_switch.turn_off_channel()
        if except_chn is not None:
            self._root_switch.turn_on_channel(except_chn)


def main():
    import time

    i2c_bus = SMBus(1)

    hw_config = SOUKLNABiasControlMonitorHWConfig(
        lna_monitor_hw_configs={
            "M17": LNAMonitorHWConfig(
                r_dac_hw_config=AD511_0_2_4BCPZ_5_10_80HWConfig(
                    DEV_ADDR=0x2C, RESOLUTION=128, R_FULL_SCALE_KOHM=10.0
                ),
                remote_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="low",
                ),
                imonitor_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="float",
                ),
                switch_status=False,
                r_LDO_set_kOhm=82.0,
                r_RTop1_kOhm=18.0,
                r_RBot1_kOhm=18.0,
                r_RAdj1_kOhm=18.0,
            ),
            "M18": None,
            "M19": None,
            "M20": None,
            "M21": None,
            "M22": None,
            "M23": None,
            "M24": None,
            "M25": None,
            "M26": None,
            "M27": LNAMonitorHWConfig(
                r_dac_hw_config=AD511_0_2_4BCPZ_5_10_80HWConfig(
                    DEV_ADDR=0x2C, RESOLUTION=128, R_FULL_SCALE_KOHM=10.0
                ),
                remote_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="low",
                ),
                imonitor_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="float",
                ),
                switch_status=False,
                r_LDO_set_kOhm=82.0,
                r_RTop1_kOhm=18.0,
                r_RBot1_kOhm=18.0,
                r_RAdj1_kOhm=18.0,
            ),
            "M28": LNAMonitorHWConfig(
                r_dac_hw_config=AD511_0_2_4BCPZ_5_10_80HWConfig(
                    DEV_ADDR=0x2C, RESOLUTION=128, R_FULL_SCALE_KOHM=10.0
                ),
                remote_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="low",
                ),
                imonitor_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="float",
                ),
                switch_status=False,
                r_LDO_set_kOhm=82.0,
                r_RTop1_kOhm=18.0,
                r_RBot1_kOhm=18.0,
                r_RAdj1_kOhm=18.0,
            ),
            "M29": LNAMonitorHWConfig(
                r_dac_hw_config=AD511_0_2_4BCPZ_5_10_80HWConfig(
                    DEV_ADDR=0x2C, RESOLUTION=128, R_FULL_SCALE_KOHM=10.0
                ),
                remote_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="low",
                ),
                imonitor_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="float",
                ),
                switch_status=False,
                r_LDO_set_kOhm=82.0,
                r_RTop1_kOhm=18.0,
                r_RBot1_kOhm=18.0,
                r_RAdj1_kOhm=18.0,
            ),
            "M30": LNAMonitorHWConfig(
                r_dac_hw_config=AD511_0_2_4BCPZ_5_10_80HWConfig(
                    DEV_ADDR=0x2C, RESOLUTION=128, R_FULL_SCALE_KOHM=10.0
                ),
                remote_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="low",
                ),
                imonitor_adc_hw_config=LTC2481CDDHWConfig(
                    CA0="float",
                    CA1="float",
                ),
                switch_status=False,
                r_LDO_set_kOhm=82.0,
                r_RTop1_kOhm=18.0,
                r_RBot1_kOhm=18.0,
                r_RAdj1_kOhm=18.0,
            ),
        },
        r9_r12="R12",
        r8_r10="R8",
        r7_r5="R7",
        r11_r13="R13",
        r14_r15="R14",
        r6_r4="R6",
    )

    souk_lna_monitor = SOUKLNABiasControlMonitor(i2c_bus, hw_config)

    while True:
        status = souk_lna_monitor.read_lna_status(chn=[1, 3])
        print(status)
        time.sleep(2)


if __name__ == "__main__":
    main()
