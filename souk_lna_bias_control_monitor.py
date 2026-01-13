from typing import Literal
from dataclasses import dataclass

from smbus2 import SMBus

from lna_monitor import LNAMonitor, LNAMonitorHWConfig
from tca9548 import TCA9548HWConfig, TCA9548

REFDES_LNA_MONITOR_CHN_MAP = {
    "M17": 1,
    "M18": 2,
    "M19": 3,
    "M20": 4,
    "M21": 5,
    "M22": 6,
    "M23": 7,
    "M24": 8,
    "M25": 9,
    "M26": 10,
    "M27": 11,
    "M28": 12,
    "M29": 13,
    "M30": 14,
}

SWITCH_ADDR_RESISTOR_MAP = {
    "root": {"A0": ["R8", "R10"], "A1": ["R7", "R5"], "A2": ["R6", "R4"]},
    "leaf": {"A0": ["R15", "R14"], "A1": ["R13", "R11"], "A2": ["R12", "R9"]},
}


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
        if self.r14_r15 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A0"]:
            raise ValueError(
                f"r14_r15 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A0']}"
            )
        if self.r11_r13 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A1"]:
            raise ValueError(
                f"r11_r13 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A1']}"
            )
        if self.r9_r12 not in SWITCH_ADDR_RESISTOR_MAP["leaf"]["A2"]:
            raise ValueError(
                f"r9_r12 must be one of {SWITCH_ADDR_RESISTOR_MAP['leaf']['A2']}"
            )
        if self.r8_r10 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A0"]:
            raise ValueError(
                f"r8_r10 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A0']}"
            )
        if self.r7_r5 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A1"]:
            raise ValueError(
                f"r7_r5 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A1']}"
            )
        if self.r6_r4 not in SWITCH_ADDR_RESISTOR_MAP["root"]["A2"]:
            raise ValueError(
                f"r6_r4 must be one of {SWITCH_ADDR_RESISTOR_MAP['root']['A2']}"
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

    @property
    def r14_r15_mapping(self) -> Literal["high", "low"]:
        return (
            "high"
            if self.r14_r15 == SWITCH_ADDR_RESISTOR_MAP["leaf"]["A0"][1]
            else "low"
        )

    @property
    def r11_r13_mapping(self) -> Literal["high", "low"]:
        return (
            "high"
            if self.r11_r13 == SWITCH_ADDR_RESISTOR_MAP["leaf"]["A1"][1]
            else "low"
        )

    @property
    def r9_r12_mapping(self) -> Literal["high", "low"]:
        return (
            "high"
            if self.r9_r12 == SWITCH_ADDR_RESISTOR_MAP["leaf"]["A2"][1]
            else "low"
        )

    @property
    def r8_r10_mapping(self) -> Literal["high", "low"]:
        return (
            "high"
            if self.r8_r10 == SWITCH_ADDR_RESISTOR_MAP["root"]["A0"][1]
            else "low"
        )

    @property
    def r7_r5_mapping(self) -> Literal["high", "low"]:
        return (
            "high" if self.r7_r5 == SWITCH_ADDR_RESISTOR_MAP["root"]["A1"][1] else "low"
        )

    @property
    def r6_r4_mapping(self) -> Literal["high", "low"]:
        return (
            "high" if self.r6_r4 == SWITCH_ADDR_RESISTOR_MAP["root"]["A2"][1] else "low"
        )


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
            a0=hw_config.r8_r10_mapping,
            a1=hw_config.r7_r5_mapping,
            a2=hw_config.r6_r4_mapping,
        )
        self._leaf_switch = TCA9548(
            dev_name="leaf_switch",
            i2c_bus=i2c_bus,
            a0=hw_config.r14_r15_mapping,
            a1=hw_config.r11_r13_mapping,
            a2=hw_config.r9_r12_mapping,
        )
        self._hw_config = hw_config

    def read_local_voltage(self, chn: int | list[int]) -> list[float]:
        """Reads the local voltage based on the current DAC resistance.
        Args:
            chn (int): The channel number (1-14), or
            chn (list[int]): A list of channel numbers.
        Returns:
            list[float]: The local voltage in volts.
        """
        if isinstance(chn, int):
            chn = [chn]
        for c in chn:
            if c not in REFDES_LNA_MONITOR_CHN_MAP.values():
                raise ValueError(f"Invalid channel number: {c}")
        voltages: list[float] = []
        for c in chn:
            refdes = next(
                key for key, value in REFDES_LNA_MONITOR_CHN_MAP.items() if value == c
            )
            lna_monitor = self._lna_monitors.get(refdes, None)
            if lna_monitor is None:
                voltages.append(float("nan"))
            else:
                voltages.append(lna_monitor.read_local_voltage())
        return voltages
