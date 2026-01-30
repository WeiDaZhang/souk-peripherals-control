import logging
import time
from typing import Literal, Dict, List
from dataclasses import dataclass, field
from i2c_devices import I2CDevice

DEV_ADDRS_MAP = {
    0x20: {"MAX7328": {"ad2": "low", "ad1": "low", "ad0": "low"}},
    0x21: {"MAX7328": {"ad2": "low", "ad1": "low", "ad0": "high"}},
    0x22: {"MAX7328": {"ad2": "low", "ad1": "high", "ad0": "low"}},
    0x23: {"MAX7328": {"ad2": "low", "ad1": "high", "ad0": "high"}},
    0x24: {"MAX7328": {"ad2": "high", "ad1": "low", "ad0": "low"}},
    0x25: {"MAX7328": {"ad2": "high", "ad1": "low", "ad0": "high"}},
    0x26: {"MAX7328": {"ad2": "high", "ad1": "high", "ad0": "low"}},
    0x27: {"MAX7328": {"ad2": "high", "ad1": "high", "ad0": "high"}},
    0x38: {"MAX7329": {"ad2": "low", "ad1": "low", "ad0": "low"}},
    0x39: {"MAX7329": {"ad2": "low", "ad1": "low", "ad0": "high"}},
    0x3A: {"MAX7329": {"ad2": "low", "ad1": "high", "ad0": "low"}},
    0x3B: {"MAX7329": {"ad2": "low", "ad1": "high", "ad0": "high"}},
    0x3C: {"MAX7329": {"ad2": "high", "ad1": "low", "ad0": "low"}},
    0x3D: {"MAX7329": {"ad2": "high", "ad1": "low", "ad0": "high"}},
    0x3E: {"MAX7329": {"ad2": "high", "ad1": "high", "ad0": "low"}},
    0x3F: {"MAX7329": {"ad2": "high", "ad1": "high", "ad0": "high"}},
}


class MAX732_8_9(I2CDevice):
    def __init__(
        self,
        dev_name,
        i2c_bus,
        ad2: Literal["high", "float", "low"],
        ad1: Literal["high", "float", "low"],
        ad0: Literal["high", "float", "low"],
        dev_type: Literal["MAX7328", "MAX7329"],
    ):
        dev_addr = None
        for addr, info in DEV_ADDRS_MAP.items():
            if info.get(dev_type) and info[dev_type] == {
                "ad2": ad2,
                "ad1": ad1,
                "ad0": ad0,
            }:
                dev_addr = addr
                self._ad2 = ad2
                self._ad1 = ad1
                self._ad0 = ad0
                self._dev_type = dev_type
                break
        if dev_addr is None:
            raise ValueError(
                f"Invalid combination of ad2={ad2}, ad1={ad1}, and ad0={ad0} with dev_type={dev_type}"
            )
        super().__init__(dev_name, i2c_bus, dev_addr)

    def read_gpio(self) -> int:
        return self.read()  # length=1, register=0x00)[0]

    def write_gpio(self, value: int) -> None:
        if not (0 <= value <= 0xFF):
            raise ValueError("GPIO value must be an 8-bit unsigned integer (0 to 255).")
        logging.debug(
            f"Written GPIO value: {value:#04x} at device {self.dev_name}, address {self.dev_addr:#04x}"
        )
        self.write(data=value)  # , register=0x00)

    def get_gpio_bit(self, bits: List[int]) -> List[bool]:
        mask = 0
        for bit in bits:
            if not (0 <= bit <= 7):
                raise ValueError("Each bit must be between 0 and 7.")
            mask |= 1 << bit
        if not (1 <= mask <= 0xFF):
            raise ValueError("Mask must be an 8-bit unsigned integer (1 to 255).")
        current_value = self.read_gpio()
        current_value_masked_list = []
        for bit in bits:
            current_value_masked_list.append(bool(current_value & (1 << bit)))
        return current_value_masked_list

    def set_gpio_bit(self, bits: List[int], states: List[bool]) -> None:
        if len(bits) != len(states):
            raise ValueError(
                f"Length of bits {len(bits)} and states {len(states)} must be the same."
            )
        current_value = self.read_gpio()
        new_value = current_value
        for bit, state in zip(bits, states):
            if not (0 <= bit <= 7):
                raise ValueError("Each bit must be between 0 and 7.")
            if state:
                new_value |= 1 << bit
            else:
                new_value &= ~(1 << bit)
        self.write_gpio(new_value)

    def pulse_gpio_bit(self, bit: int, pulse_width_ms: int = 100) -> None:
        if not (0 <= bit <= 7):
            raise ValueError("Bit must be between 0 and 7.")
        self.set_gpio_bit([bit], [False])
        self.set_gpio_bit([bit], [True])
        time.sleep(pulse_width_ms / 1000.0)
        self.set_gpio_bit([bit], [False])

    @property
    def addr_pin_ad2(self) -> Literal["high", "low"]:
        return self._ad2

    @property
    def addr_pin_ad1(self) -> Literal["high", "low"]:
        return self._ad1

    @property
    def addr_pin_ad0(self) -> Literal["high", "low"]:
        return self._ad0

    @property
    def device_type(self) -> Literal["MAX7328", "MAX7329"]:
        return self._dev_type
