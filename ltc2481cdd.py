from typing import Literal
from dataclasses import dataclass
from i2c_devices import I2CDevice

DEV_ADDRS = {
    ("low", "high"): 0x14,
    ("low", "float"): 0x15,
    ("float", "high"): 0x17,
    ("float", "float"): 0x24,
    ("float", "low"): 0x25,
    ("high", "high"): 0x26,
    ("high", "float"): 0x27,
}


@dataclass(frozen=True)
class LTC2481CDDHWConfig:
    CA0: Literal["low", "float", "high"]
    CA1: Literal["low", "float", "high"]
    REFERENCES: dict[bool, float] = {
        True: 5.0,
        False: 0.0,
    }  # {True: Vref+, False: Vref-}
    V_OPERATION: float = 5.0  # in volts


@dataclass
class LTC2481CDDConfig:
    gs: Literal[0, 1, 2, 3, 4, 5, 6, 7] = 0  # gain setting (0-7)
    im: bool = False  # internal temperature select if True
    spd: bool = False  # 2x speed if True
    rm: Literal[0, 1, 2] = 0  # rejection mode: 0 = 50/60Hz, 1=50Hz, 2=60Hz

    def __post_init__(self):
        if self.gs not in range(8):
            raise ValueError("Gain setting (gs) must be between 0 and 7.")
        if self.rm not in (0, 1, 2):
            raise ValueError("Rejection mode (rm) must be 0, 1, or 2.")
        if not isinstance(self.im, bool):
            raise ValueError("Internal temperature select (im) must be a boolean.")
        if not isinstance(self.spd, bool):
            raise ValueError("2x speed (spd) must be a boolean.")

    @property
    def gain(self) -> float:
        if self.spd:
            return 2**self.gs
        else:
            return 2 ** (self.gs + 1) if self.gs > 0 else 1

    def __setattr__(self, name, value):
        if name == "gs":
            if not isinstance(value, int) or not (0 <= value <= 7):
                raise ValueError("gs must be an integer in range 0..7")
        elif name == "im":
            if not isinstance(value, bool):
                raise ValueError("im must be a boolean value")
        elif name == "spd":
            if not isinstance(value, bool):
                raise ValueError("spd must be a boolean value")
        elif name == "rm":
            if not isinstance(value, int) or value not in (0, 1, 2):
                raise ValueError("rm must be an integer in (0, 1, 2)")
        super().__setattr__(name, value)

    @property
    def config_byte(self) -> int:
        GS_BITS = (0x07, 5)  # mask, shift
        IM_BIT = 3
        RM_BITS = (0x03, 1)  # mask, shift
        SPD_BIT = 0
        byte = (
            (self.gs << GS_BITS[1])
            | (int(self.im) << IM_BIT)
            | (int(self.spd) << SPD_BIT)
            | (self.rm << RM_BITS[1])
        ) & 0xFF
        return byte


@dataclass
class LTC2481CDDSignal:
    sign: int
    overflow: bool
    magnitude: int
    count: int
    value: float


@dataclass
class LTC2481CDDOUT:
    raw24: int
    v_reference: float

    def __post_init__(self):
        if not (0 <= self.raw24 <= 0xFFFFFF):
            raise ValueError("raw24 must be a 24-bit unsigned integer (0 to 16777215).")

        data_dict = self.parse_raw(self.raw24)
        self.signal = LTC2481CDDSignal(**data_dict["signal"])
        self.config = data_dict["config"]

    def parse_raw(self) -> dict:
        """
        Bit mapping (MSb -> LSb):
           bit23: SGN
           bit22: OVERFLOW
           bits21..6: 16-bit measurement
           bits5..3: PG2..PG0
           bit2:   X (reserved)
           bit1:   IM (internal temp select)
           bit0:   SPD (2x speed)
        """
        SIG_BIT = 23
        MSB_BIT = 22
        LSB_BIT = 6
        PG_BITS = (0x7, 3)  # mask, shift
        IM_BIT = 1
        SPD_BIT = 0
        T_SLOPE = 0.0014  # V/°C

        # extract sign (bit22)
        sign = (self.raw24 >> SIG_BIT) & 0x1
        overflow = (self.raw24 >> MSB_BIT) & 0x1 == sign
        # extract 16-bit measurement (bits 21..6)
        magnitude = (self.raw24 >> LSB_BIT) & (2 ** (MSB_BIT - LSB_BIT) - 1)  # 16 bits
        # signed conversion: sign bit indicates negative (two's complement-like handling)
        # Interpret as signed 16-bit magnitude with separate sign bit:
        if sign == 1:
            signed = magnitude
        else:
            signed = magnitude - (1 << (MSB_BIT - LSB_BIT))  # negative value

        # extract PG2..PG0 (bits5..3)
        pg = (self.raw24 >> PG_BITS[1]) & PG_BITS[0]
        # IM (bit1), SPD (bit0)
        im = (self.raw24 >> IM_BIT) & 0x1
        spd = (self.raw24 >> SPD_BIT) & 0x1

        config = LTC2481CDDConfig(gs=pg, im=bool(im), spd=bool(spd))  # validate config
        if config.im:
            value = (
                signed / 2 ** (MSB_BIT - LSB_BIT) * self.v_reference / T_SLOPE
            )  # temp mode
        else:
            value = signed / 2 ** (MSB_BIT - LSB_BIT) * (self.v_reference / config.gain)

        return {
            "signal": {
                "sign": sign,
                "overflow": overflow,
                "magnitude": magnitude,
                "count": signed,
                "value": value,
            },
            "config": config,
        }


class LTC2481CDD(I2CDevice):
    def __init__(
        self,
        dev_name,
        i2c_bus,
        ca0: Literal["high", "float", "low"],
        ca1: Literal["high", "float", "low"],
        references: dict[
            bool, float
        ],  # {True: 5.0 in volts (ref+), False: 2.5 in volts (ref-)}
        v_operation: float = 5,
    ):
        dev_addr = DEV_ADDRS.get((ca1, ca0), None)
        if dev_addr is None:
            raise ValueError(f"Invalid combination of ca1={ca1} and ca0={ca0}")
        self._ca0 = ca0
        self._ca1 = ca1
        if (
            isinstance(references, dict)
            and all((True in references, False in references))
            and all(v_operation > v > 0 for v in references.values())
        ):
            self._v_oper = v_operation
            self._v_ref = references[True] - references[False]
            self._refs = references
        else:
            raise ValueError(f"Invalid reference voltage configuration: {references}.")
        super().__init__(dev_name, i2c_bus, dev_addr)
        self._config = LTC2481CDDConfig()  # default config
        self._write_config()  # write default config to device

    # Fixed properties
    @property
    def addr_pin_ca0(self) -> Literal["high", "float"]:
        return self._ca0

    @property
    def addr_pin_ca1(self) -> Literal["high", "float", "low"]:
        return self._ca1

    @property
    def v_operation(self) -> float:
        return self._v_oper

    @property
    def v_reference(self) -> float:
        return self._v_ref

    @property
    def references(self) -> dict[bool, float]:
        return self._refs

    # Configurable properties
    @property
    def intra_meas(self) -> bool:
        return self._config.im

    @intra_meas.setter
    def intra_meas(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("intra_meas must be a boolean value")
        self._write_config(im=value)

    @property
    def speed_2x(self) -> bool:
        return self._config.spd

    @speed_2x.setter
    def speed_2x(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("speed_2x must be a boolean value")
        self._write_config(spd=value)

    @property
    def gain_setting(self) -> float:
        return self._config.gain

    @gain_setting.setter
    def gain_setting(self, value: float):
        if self.speed_2x:
            if value not in 2 ** range(8):
                raise ValueError(
                    "gain_setting must be one of 1,2,4,8,16,32,64,128 for 2x speed"
                )
            gs = {v: k for k, v in zip(range(8), 2 ** range(8))}[value]
        else:
            if value not in [1] + [2 ** (k + 1) for k in range(1, 8)]:
                raise ValueError(
                    "gain_setting must be one of 1,4,8,16,32,64,128,256 for normal speed"
                )
            gs = {
                v: k
                for k, v in zip(range(8), [1] + [2 ** (k + 1) for k in range(1, 8)])
            }[value]
        self._write_config(gain=gs)

    @property
    def rejection_mode(self) -> Literal[0, 1, 2]:
        return self._config.rm

    @rejection_mode.setter
    def rejection_mode(self, value: Literal[0, 1, 2]):
        if value not in (0, 1, 2):
            raise ValueError("rejection_mode must be 0, 1, or 2")
        self._write_config(rm=value)

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
