from typing import Literal
from dataclasses import dataclass
from i2c_devices import I2CDevice

DEV_ADDRS = {
    ("low", "low", "low"): 0x70,
    ("low", "low", "high"): 0x71,
    ("low", "high", "low"): 0x72,
    ("low", "high", "high"): 0x73,
    ("high", "low", "low"): 0x74,
    ("high", "low", "high"): 0x75,
    ("high", "high", "low"): 0x76,
    ("high", "high", "high"): 0x77,
}


@dataclass
class ChannelConfig:
    _config_byte: int
    _n_channels: int = 8

    def __post_init__(self):
        if not (0 <= self.config_byte <= (1 << self._n_channels) - 1):
            raise ValueError(
                f"config_byte must be between 0 and {(1 << self._n_channels) - 1}"
            )
        self.channels: dict[int, bool] = {}
        for bit in range(self._n_channels):
            self.channels[bit] = bool((self.config_byte >> bit) & 0x01)

    @property
    def config_byte(self) -> int:
        return self._config_byte

    @config_byte.setter
    def config_byte(self, value: int):
        if not (0 <= value <= (1 << self._n_channels) - 1):
            raise ValueError(
                f"config_byte must be between 0 and {(1 << self._n_channels) - 1}"
            )
        self._config_byte = value
        for bit in range(self._n_channels):
            self.channels[bit] = bool((self._config_byte >> bit) & 0x01)


class TCA9548(I2CDevice):
    def __init__(
        self,
        dev_name,
        i2c_bus,
        a0: Literal["high", "low"],
        a1: Literal["high", "low"],
        a2: Literal["high", "low"],
    ):
        dev_addr = DEV_ADDRS.get((a2, a1, a0), None)
        if dev_addr is None:
            raise ValueError(f"Invalid combination of a2={a2}, a1={a1} and a0={a0}")
        self._a0 = a0
        self._a1 = a1
        self._a2 = a2
        super().__init__(dev_name, i2c_bus, dev_addr)
        self.update_channel_config()

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
    def channel_config(self) -> ChannelConfig:
        self.update_channel_config()
        return self._channel_config

    def update_channel_config(self) -> None:
        if not hasattr(self, "_channel_config"):
            self._channel_config = ChannelConfig(0)
        self._channel_config.config_byte = self.read()[0]

    def turn_on_channel(self, channel: int) -> ChannelConfig:
        if not (0 <= channel <= 7):
            raise ValueError("channel must be between 0 and 7")
        new_config_byte = self.channel_config.config_byte | (1 << channel)
        self.write(new_config_byte)
        self.update_channel_config()
        return self.channel_config

    def turn_off_channel(self, channel: int = None) -> ChannelConfig:
        """If channel is None, turn off all channels."""
        if channel is None:
            new_config_byte = ChannelConfig(0).config_byte
        elif not (0 <= channel <= 7):
            raise ValueError("channel must be between 0 and 7")
        else:
            new_config_byte = self.channel_config.config_byte & ~(1 << channel)
        self.write(new_config_byte)
        self.update_channel_config()
        return self.channel_config

    def get_channel_status(self, channel: int) -> bool:
        if not (0 <= channel <= 7):
            raise ValueError("channel must be between 0 and 7")
        return self.channel_config.channels[channel]
