from typing import Literal
from dataclasses import dataclass, asdict
from i2c_devices import I2CDevice


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
    def gain(self) -> int:
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

    @staticmethod
    def parse_raw(raw24, v_reference: float = 5.0) -> dict:
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
        sign = (raw24 >> SIG_BIT) & 0x1
        overflow = (raw24 >> MSB_BIT) & 0x1 == sign
        # extract 16-bit measurement (bits 21..6)
        magnitude = (raw24 >> LSB_BIT) & (2 ** (MSB_BIT - LSB_BIT) - 1)  # 16 bits
        # signed conversion: sign bit indicates negative (two's complement-like handling)
        # Interpret as signed 16-bit magnitude with separate sign bit:
        if sign == 1:
            signed = magnitude
        else:
            signed = magnitude - (1 << (MSB_BIT - LSB_BIT))  # negative value

        # extract PG2..PG0 (bits5..3)
        pg = (raw24 >> PG_BITS[1]) & PG_BITS[0]
        # IM (bit1), SPD (bit0)
        im = (raw24 >> IM_BIT) & 0x1
        spd = (raw24 >> SPD_BIT) & 0x1

        config = LTC2481CDDConfig(gs=pg, im=bool(im), spd=bool(spd))  # validate config
        if config.im:
            value = (
                signed / 2 ** (MSB_BIT - LSB_BIT) * v_reference / T_SLOPE
            )  # temp mode
        else:
            value = signed / 2 ** (MSB_BIT - LSB_BIT) * (v_reference / config.gain)

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
        ca0: Literal["high", "float"],
        ca1: Literal["high", "float", "low"],
        reference: dict[
            bool, float
        ],  # {True: 5.0 in volts (ref+), False: 2.5 in volts (ref-)}
        v_operation: float = 5,
    ):
        match (ca1, ca0):
            case ("low", "high"):
                dev_addr = 0x14
            case ("low", "float"):
                dev_addr = 0x15
            case ("float", "high"):
                dev_addr = 0x17
            case ("float", "float"):
                dev_addr = 0x24
            case ("high", "high"):
                dev_addr = 0x26
            case ("high", "float"):
                dev_addr = 0x27
            case _:
                raise ValueError(f"Invalid combination of ca1={ca1} and ca0={ca0}")
        self.addr_pins = {"ca0": ca0, "ca1": ca1}
        if (
            isinstance(reference, dict)
            and all((True in reference, False in reference))
            and all(v_operation > v > 0 for v in reference.values())
        ):
            self.v_operation = v_operation
            self.v_reference = reference[True] - reference[False]
            self.reference = reference
        else:
            raise ValueError(f"Invalid reference voltage configuration: {reference}.")
        super().__init__(dev_name, i2c_bus, dev_addr)
        self.config = LTC2481CDDConfig()  # default config

    def get_config(self) -> dict:
        return {
            "ca0": self.addr_pins["ca0"],
            "ca1": self.addr_pins["ca1"],
            "reference": self.reference,
            "config": asdict(self.config),
        }

    def write_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise KeyError(f"Invalid configuration key: {key}")
        self.write(self.config.config_byte)

    def read_data(self) -> LTC2481CDDOUT:
        raw_data = self.read(length=3)
        raw24 = (raw_data[0] << 16) | (raw_data[1] << 8) | raw_data[2]
        return LTC2481CDDOUT(raw24=raw24, v_reference=self.v_reference)
