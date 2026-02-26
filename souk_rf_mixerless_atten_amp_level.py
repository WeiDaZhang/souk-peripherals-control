import logging
from typing import Literal, List, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

ZX60_53LNB_S_BYPASS_IL = -2.2
ZX60_53LNB_S_GAIN = 20.2
ZX60_53LNB_S_GAIN_1dB_COMP = 20.0
ZX60_53LNB_S_BYPASS_1dB_COMP = 33.0
BFCV_2895_IL = -1.8
VEQY_5_63_IL = -3.5
ZX76_31R5A_PNS_IL = -1.5
ZX76_31R5A_PNS_RANGE = -31.5
ZX76_31R5A_PNS_STEP = -0.5
BW_S5W2_IL = -5.0


@dataclass
class Amplifier:
    _type: str = "ZX60-53LNB-S+"
    _bypass_il: float = ZX60_53LNB_S_BYPASS_IL
    _gain: float = ZX60_53LNB_S_GAIN
    _bypass_1dB_comp: float = ZX60_53LNB_S_BYPASS_1dB_COMP
    _gain_1dB_comp: float = ZX60_53LNB_S_GAIN_1dB_COMP
    bypass_state: bool = False

    @property
    def type(self) -> str:
        return self._type

    @property
    def bypass_il(self) -> float:
        return self._bypass_il

    @property
    def gain(self) -> float:
        return self._gain

    @property
    def input_1dB_comp(self) -> float:
        return (
            self._gain_1dB_comp - self._gain
            if not self.bypass_state
            else self._bypass_1dB_comp
        )

    @property
    def total_gain_il(self) -> float:
        return self._bypass_il if self.bypass_state else self._gain


@dataclass
class Filter:
    _type: str = "BFCV-2895"
    _filter_num: int = 2
    _filter_il: float = BFCV_2895_IL
    _atten: float = -3.0
    _atten_num: int = 1

    @property
    def type(self) -> str:
        return self._type

    @property
    def filter_num(self) -> int:
        return self._filter_num

    @property
    def filter_il(self) -> float:
        return self._filter_il

    @property
    def atten(self) -> float:
        return self._atten

    @property
    def atten_num(self) -> int:
        return self._atten_num

    @property
    def total_gain_il(self) -> float:
        return self._filter_il * self._filter_num + self._atten * self._atten_num


@dataclass
class Equalizer:
    _type: str = "VEQY-5-63+"
    _insert_loss: float = VEQY_5_63_IL

    @property
    def type(self) -> str:
        return self._type

    @property
    def total_gain_il(self) -> float:
        return self._insert_loss


@dataclass
class VariableAtten:
    _type: str = "ZX76-31R5A-PNS+"
    _insert_loss: float = ZX76_31R5A_PNS_IL
    _atten_range: float = ZX76_31R5A_PNS_RANGE
    _atten_step: float = ZX76_31R5A_PNS_STEP
    _atten: float = 0.0

    @property
    def type(self) -> str:
        return self._type

    @property
    def insert_loss(self) -> float:
        return self._insert_loss

    @property
    def atten_range(self) -> float:
        return self._atten_range

    @property
    def atten_step(self) -> float:
        return self._atten_step

    @property
    def atten(self) -> float:
        return self._atten

    @atten.setter
    def atten(self, value: float) -> None:
        if value < ZX76_31R5A_PNS_RANGE:
            logging.warning(
                f"Attenuation value {value} dB is below the minimum of {ZX76_31R5A_PNS_RANGE} dB. Using minimum in calculation."
            )
            self._atten = ZX76_31R5A_PNS_RANGE
        elif value > 0:
            logging.warning(
                f"Attenuation value {value} dB is above the maximum of 0 dB. Using maximum in calculation."
            )
            self._atten = 0
        else:
            self._atten = value

    @property
    def total_gain_il(self) -> float:
        return self._insert_loss + self._atten


@dataclass
class FixedAtten:
    _type: str = "BW-S5W2+"
    _insert_loss: float = BW_S5W2_IL

    @property
    def type(self) -> str:
        return self._type

    @property
    def total_gain_il(self) -> float:
        return self._insert_loss


class SOUKRFMixerlessAttenAmpLevel(ABC):
    @property
    @abstractmethod
    def total_gain_il(self):
        pass

    @property
    @abstractmethod
    def range_gain_il(self):
        pass

    @property
    @abstractmethod
    def input_1dB_comp(self):
        pass

    @property
    @abstractmethod
    def atten(self):
        pass

    @atten.setter
    def atten(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def bypass_state(self):
        pass

    @bypass_state.setter
    def bypass_state(self, value: bool) -> None:
        pass


@dataclass
class SOUKRFMixerlessTransmitAttenAmpLevel(SOUKRFMixerlessAttenAmpLevel):
    amp: Amplifier = field(default_factory=Amplifier)
    filter: Filter = field(default_factory=Filter)
    equalizer: Equalizer = field(default_factory=Equalizer)
    variable_atten: VariableAtten = field(default_factory=VariableAtten)
    fixed_atten: FixedAtten = field(default_factory=FixedAtten)

    @property
    def total_gain_il(self) -> float:
        return (
            self.amp.total_gain_il
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.total_gain_il
            + self.fixed_atten.total_gain_il
        )

    @property
    def atten(self) -> float:
        return self.variable_atten.atten

    @atten.setter
    def atten(self, value: float) -> None:
        self.variable_atten.atten = value

    @property
    def bypass_state(self) -> bool:
        return self.amp.bypass_state

    @bypass_state.setter
    def bypass_state(self, value: bool) -> None:
        self.amp.bypass_state = value

    @property
    def range_gain_il(self) -> Tuple[float, float]:
        min_il = (
            self.amp.bypass_il
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.atten_range
            + self.fixed_atten.total_gain_il
        )
        max_il = (
            self.amp.gain
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.insert_loss
            + self.fixed_atten.total_gain_il
        )
        return (min_il, max_il)

    @property
    def input_1dB_comp(self) -> float:
        return (
            self.amp.input_1dB_comp
            - self.filter.total_gain_il
            - self.equalizer.total_gain_il
            - self.variable_atten.insert_loss
        )


@dataclass
class SOUKRFMixerlessRecvAttenAmpLevel(SOUKRFMixerlessAttenAmpLevel):
    preamp: Amplifier = field(default_factory=Amplifier)
    amp: Amplifier = field(default_factory=Amplifier)
    filter: Filter = field(default_factory=Filter)
    equalizer: Equalizer = field(default_factory=Equalizer)
    variable_atten: VariableAtten = field(default_factory=VariableAtten)
    fixed_atten: FixedAtten = field(default_factory=FixedAtten)

    @property
    def total_gain_il(self) -> float:
        return (
            self.preamp.total_gain_il
            + self.amp.total_gain_il
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.total_gain_il
            + self.fixed_atten.total_gain_il
        )

    @property
    def atten(self) -> float:
        return self.variable_atten.atten

    @atten.setter
    def atten(self, value: float) -> None:
        self.variable_atten.atten = value

    @property
    def bypass_state(self) -> bool:
        return self.amp.bypass_state

    @bypass_state.setter
    def bypass_state(self, value: bool) -> None:
        self.amp.bypass_state = value

    @property
    def range_gain_il(self) -> Tuple[float, float]:
        min_il = (
            self.preamp.total_gain_il
            + self.amp.bypass_il
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.atten_range
            + self.fixed_atten.total_gain_il
        )
        max_il = (
            self.preamp.total_gain_il
            + self.amp.gain
            + self.filter.total_gain_il
            + self.equalizer.total_gain_il
            + self.variable_atten.insert_loss
            + self.fixed_atten.total_gain_il
        )
        return (min_il, max_il)

    @property
    def input_1dB_comp(self) -> float:
        return min(
            self.amp.input_1dB_comp
            - self.fixed_atten.total_gain_il
            - self.variable_atten.insert_loss
            - self.preamp.total_gain_il
            - self.filter.total_gain_il
            - self.equalizer.total_gain_il,
            self.preamp.input_1dB_comp
            - self.equalizer.total_gain_il
            - self.filter.total_gain_il,
        )
