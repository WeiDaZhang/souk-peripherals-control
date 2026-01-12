from typing import Literal
from dataclasses import dataclass
from i2c_devices import I2CDevice


@dataclass
class LTC2481CDDSignal:
    sign: int
    overflow: bool
    magnitude: int
    count: int
    value: float


class TCA9548(I2CDevice):
    def __init__(
        self,
        dev_name,
        i2c_bus,
        a0: Literal["high", "low"],
        a1: Literal["high", "low"],
        a2: Literal["high", "low"],
    ):
        match (a2, a1, a0):
            case ("low", "low", "low"):
                dev_addr = 0x70
            case ("low", "low", "high"):
                dev_addr = 0x71
            case ("low", "high", "low"):
                dev_addr = 0x72
            case ("low", "high", "high"):
                dev_addr = 0x73
            case ("high", "low", "low"):
                dev_addr = 0x74
            case ("high", "low", "high"):
                dev_addr = 0x75
            case ("high", "high", "low"):
                dev_addr = 0x76
            case ("high", "high", "high"):
                dev_addr = 0x77
            case _:
                raise ValueError(f"Invalid combination of a2={a2}, a1={a1} and a0={a0}")
        self._a0 = a0
        self._a1 = a1
        self._a2 = a2
        super().__init__(dev_name, i2c_bus, dev_addr)

    # Fixed properties
    @property
    def addr_pin_a0(self) -> Literal["high", "low"]:
        return self._a0

    @property
    def addr_pin_a1(self) -> Literal["high", "low"]:
        return self._a1

    @property
    def addr_pin_a2(self) -> Literal["high", "low"]:
        return self._a2

    @property
    def dev_addr(self) -> int:
        return self.addr

    # Configurable properties
    @property
    def intra_meas(self) -> bool:
        return self._config.im

    @intra_meas.setter
    def intra_meas(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("intra_meas must be a boolean value")
        self._write_config(im=value)

    def _write_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise KeyError(f"Invalid configuration key: {key}")
        self.write(self._config.config_byte)

    def read_data(self) -> LTC2481CDDOUT:
        raw_data = self.read(length=3)
        raw24 = (raw_data[0] << 16) | (raw_data[1] << 8) | raw_data[2]
        return LTC2481CDDOUT(raw24=raw24, v_reference=self.v_reference)

    def read_voltage(self) -> float:
        if self.intra_meas:
            self.intra_meas = False  # switch to voltage mode if in temp mode
        data_out = self.read_data()
        return data_out.signal["value"]

    def read_temperature(self) -> float:
        if not self.intra_meas:
            self.intra_meas = True  # switch to temp mode if in voltage mode
        data_out = self.read_data()
        return data_out.signal["value"]
