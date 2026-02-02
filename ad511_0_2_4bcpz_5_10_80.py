from typing import Literal, Tuple
from dataclasses import dataclass
from i2c_devices import I2CDevice

RES_ROUNDING_ERROR = 1  # Ohm


@dataclass(frozen=True)
class AD511_0_2_4BCPZ_5_10_80HWConfig:
    RESOLUTION: Literal[32, 64, 128]
    R_FULL_SCALE_KOHM: Literal[5, 10, 80]
    DEV_ADDR: Literal[0x2C, 0x2F]

    @classmethod
    def default_config(cls):
        return cls(
            RESOLUTION=128,
            R_FULL_SCALE_KOHM=10,
            DEV_ADDR=0x2C,
        )


@dataclass(frozen=True)
class AD511_0_2_4BCPZ_5_10_80CMD:
    UPDATE_EEPROM_CMD: int = 0x01
    WRITE_RDAC_CMD: int = 0x02
    LOAD_EEPROM_TO_RDAC_CMD: int = 0x04
    READ_RDAC_CMD: int = 0x05
    READ_EEPROM_CMD: int = 0x06


@dataclass
class AD511_0_2_4BCPZ_5_10_80DOUT:
    raw8: int
    res: int
    r_ab: float
    r_bs: float = 0.0
    r_ts: float = 0.0
    r_w: float = 0.0

    def __post_init__(self):
        self.MSB_BIT = 7
        if self.res == 32:
            LSB_BIT = 2
        elif self.res == 64:
            LSB_BIT = 1
        elif self.res == 128:
            LSB_BIT = 0
        self.LSB_BIT = LSB_BIT

        if not (0 <= self.raw8 <= 0xFF):
            raise ValueError("raw8 must be an 8-bit unsigned integer (0 to 255).")

        self.data = self.parse_raw()

    def parse_raw(self) -> dict:
        """
        Bit mapping (MSb -> LSb):
           bit7: MSB
           ...
           bit1:   applicapable for res = 64, 128 only
           bit0:   applicapable for res = 128 only
        """

        value = (self.raw8 >> self.LSB_BIT) & (
            (1 << (self.MSB_BIT - self.LSB_BIT + 1)) - 1
        )
        if (value < 0 or value > self.res) and (value != 0xFF):
            raise ValueError("Invalid RDAC value for the specified resolution.")
        r_wb = value / self.res * self.r_ab + self.r_w
        r_aw = (self.res - value) / self.res * self.r_ab + self.r_w
        if value == 0xFF:  # Bottom Scale
            r_aw = self.r_ab + self.r_w
            r_wb = self.r_bs
        elif value == self.res:  # Top Scale
            r_aw = self.r_ts

        return {
            "tap_pos": value,
            "r_aw": r_aw,
            "r_wb": r_wb,
        }


class AD511_0_2_4BCPZ_5_10_80(I2CDevice):
    def __init__(
        self,
        dev_name,
        i2c_bus,
        res: Literal[32, 64, 128],
        r_full_scale_kOhm: Literal[5, 10, 80],
        dev_addr: Literal[0x2C, 0x2F],
    ):
        if res in (32, 64, 128):
            self._res = res
        else:
            raise ValueError("Resolution must be one of 32, 64, or 128.")
        if r_full_scale_kOhm in (5, 10, 80):
            self._r_full_scale_kOhm = r_full_scale_kOhm
        else:
            raise ValueError("Maximum resistance must be one of 5, 10, or 80 kOhm.")
        if dev_addr not in (0x2C, 0x2F):
            raise ValueError("Address must be one of 0x2C or 0x2F.")
        super().__init__(dev_name, i2c_bus, dev_addr)
        self._cmd = AD511_0_2_4BCPZ_5_10_80CMD()
        self._r_ab = r_full_scale_kOhm * 1000  # convert to Ohm
        self._r_w = 50  # Ohm, wiper resistance
        self._r_bs = 50  # Ohm, resistance top_scale
        self._r_ts = 50  # Ohm, resistance bottom_scale

    # Fixed properties
    @property
    def resolution(self) -> Literal[32, 64, 128]:
        return self._res

    @property
    def r_full_scale_kOhm(self) -> int:
        return self._r_full_scale_kOhm

    # Configurable properties
    @property
    def r_ab(self) -> float:
        return self._r_ab

    @r_ab.setter
    def r_ab(self, value: float):
        """
        Setting the total resistance between terminals A and B after calibration.
        Allows actual r_ab to be set to a value different from the nominal full scale resistance.
        SHOULD BE CALIBRATED CAREFULLY TO AVOID ERRORS IN RESISTANCE VALUES.
        """
        if value <= 0:
            raise ValueError("r_ab must be a positive value.")
        self._r_ab = value

    @property
    def r_bs(self) -> float:
        return self._r_bs

    @r_bs.setter
    def r_bs(self, value: float):
        """
        Setting the bottom scale resistance after calibration.
        SHOULD BE CALIBRATED CAREFULLY TO AVOID ERRORS IN RESISTANCE VALUES.
        """
        if value < 0:
            raise ValueError("r_bs must be a non-negative value.")
        self._r_bs = value

    @property
    def r_ts(self) -> float:
        return self._r_ts

    @r_ts.setter
    def r_ts(self, value: float):
        """
        Setting the top scale resistance after calibration.
        SHOULD BE CALIBRATED CAREFULLY TO AVOID ERRORS IN RESISTANCE VALUES.
        """
        if value < 0:
            raise ValueError("r_ts must be a non-negative value.")
        self._r_ts = value

    @property
    def r_w(self) -> float:
        return self._r_w

    @r_w.setter
    def r_w(self, value: float):
        """
        Setting the wiper resistance after calibration.
        SHOULD BE CALIBRATED CAREFULLY TO AVOID ERRORS IN RESISTANCE VALUES.
        """
        if value < 0:
            raise ValueError("r_w must be a non-negative value.")
        self._r_w = value

    @property
    def r_aw(self) -> float:
        tap_pos = self.read_tap_pos()
        return AD511_0_2_4BCPZ_5_10_80DOUT(
            raw8=tap_pos,
            res=self.resolution,
            r_ab=self.r_ab,
            r_bs=self.r_bs,
            r_ts=self.r_ts,
            r_w=self.r_w,
        ).data["r_aw"]

    @r_aw.setter
    def r_aw(self, value: float):
        if value < self.r_w - RES_ROUNDING_ERROR or value > (
            self.r_ab + self.r_w + RES_ROUNDING_ERROR
        ):
            raise ValueError(
                f"r_aw value {value} must be between {self.r_w} Ohm and {self.r_ab + self.r_w} Ohm."
            )
        tap_pos = round((1 - (value - self.r_w) / self.r_ab) * self.resolution)
        self.write_tap_pos(tap_pos)

    @property
    def r_aw_range(self) -> Tuple[float, float]:
        return (self.r_ts, self.r_ab + self.r_w)

    @property
    def r_bw(self) -> float:
        tap_pos = self.read_tap_pos()
        return AD511_0_2_4BCPZ_5_10_80DOUT(
            raw8=tap_pos,
            res=self.resolution,
            r_ab=self.r_ab,
            r_bs=self.r_bs,
            r_ts=self.r_ts,
            r_w=self.r_w,
        )["r_wb"]

    @r_bw.setter
    def r_bw(self, value: float):
        if value < self.r_w - RES_ROUNDING_ERROR or value > (
            self.r_ab + self.r_w + RES_ROUNDING_ERROR
        ):
            raise ValueError(
                f"r_bw value {value} must be between {self.r_w} Ohm and {self.r_ab + self.r_w} Ohm."
            )
        tap_pos = round((value - self.r_w) / self.r_ab * self.resolution)
        self.write_tap_pos(tap_pos)

    @property
    def r_bw_range(self) -> Tuple[float, float]:
        return (self.r_w, self.r_ab + self.r_w)

    def read_tap_pos(self, eeprom: bool = False) -> int:
        if eeprom:
            self.write(0, self._cmd.READ_EEPROM_CMD)
        else:
            self.write(0, self._cmd.READ_RDAC_CMD)
        return self.read()[0]

    def write_tap_pos(self, value):
        self.write(value, self._cmd.WRITE_RDAC_CMD)

    def update_eeprom(self):
        self.write(0, self._cmd.UPDATE_EEPROM_CMD)

    def increase_tap_pos(self, step: int = 1) -> bool:
        # to increase resistance r_bw, decrease r_aw
        current_tap = self.read_tap_pos()
        if current_tap + step > self.resolution:
            return False
        else:
            new_tap = current_tap + step
            self.write_tap_pos(new_tap)
            return True

    def decrease_tap_pos(self, step: int = 1) -> bool:
        # to decrease resistance r_bw, increase r_aw
        current_tap = self.read_tap_pos()
        if current_tap - step < 0:
            return False
        else:
            new_tap = current_tap - step
            self.write_tap_pos(new_tap)
            return True

    def calibrate_scales_wiper(self):
        pass  # Placeholder for future calibration method
