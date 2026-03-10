import logging
import os
from typing import Literal, List, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np

ZX60_53LNB_S_BYPASS_IL = -2.2
ZX60_53LNB_S_GAIN = 20.2
ZX60_53LNB_S_GAIN_1dB_COMP = 20.0 - ZX60_53LNB_S_GAIN
ZX60_53LNB_S_BYPASS_1dB_COMP = 33.0
BFCV_2895_IL = -1.8
BFCV_2895_1dB_COMP = 36.99  # max input power
VEQY_5_63_IL = -3.5
VEQY_5_63_1dB_COMP = 31.0  # max input power
ZX76_31R5A_PNS_IL = -1.5
ZX76_31R5A_PNS_RANGE = -31.5
ZX76_31R5A_PNS_STEP = -0.5
ZX76_31R5A_PNS_1dB_COMP = 24.0  # 0.2dB compression point
BW_S5W2_IL = -5.0
BW_S5W2_1dB_COMP = 33.0  # max input power
CYRO_INPUT_CABLE_IL = (
    -8.5
)  # estimated insertion loss of the cable from room temp to cryo
CYRO_OUTPUT_CABLE_IL = (
    -8.5
)  # estimated insertion loss of the cable from cryo to room temp
CYRO_COLD_ATTEN = -20.0  # estimated attenuation from the cold attenuator in the cryo
CRYO_LNA_GAIN = 31.0  # estimated gain of the cryo LNA
CRYO_LNA_1dB_COMP = -29.0  # estimated 1dB compression point of the cryo LNA


@dataclass
class RFComponent:
    _type: str = None
    _insert_loss: float = None
    _1dB_comp: float = None

    @property
    def type(self) -> str:
        return self._type

    @property
    def total_gain_il(self) -> float:
        return self._insert_loss

    @property
    def input_1dB_comp(self) -> float:
        return self._1dB_comp


@dataclass
class Equalizer(RFComponent):
    _type: str = "VEQY-5-63+"
    _insert_loss: float = VEQY_5_63_IL
    _1dB_comp: float = VEQY_5_63_1dB_COMP


@dataclass
class FixedAtten(RFComponent):
    _type: str = "BW-S5W2+"
    _insert_loss: float = BW_S5W2_IL
    _1dB_comp: float = BW_S5W2_1dB_COMP


@dataclass
class Amplifier(RFComponent):
    _type: str = "ZX60-53LNB-S+"
    _bypass_il: float = ZX60_53LNB_S_BYPASS_IL
    _gain: float = ZX60_53LNB_S_GAIN
    _bypass_1dB_comp: float = ZX60_53LNB_S_BYPASS_1dB_COMP
    _gain_1dB_comp: float = ZX60_53LNB_S_GAIN_1dB_COMP
    bypass_state: bool = False

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
class Filter(RFComponent):
    _type: str = "BFCV-2895"
    _filter_num: int = 2
    _filter_il: float = BFCV_2895_IL
    _atten: float = -3.0
    _atten_num: int = 1
    _1dB_comp: float = BFCV_2895_1dB_COMP

    @property
    def total_gain_il(self) -> float:
        return self._filter_il * self._filter_num + self._atten * self._atten_num

    @property
    def input_1dB_comp(self) -> float:
        return self._1dB_comp


@dataclass
class SampleCryo(RFComponent):
    _type: str = "SampleCryo"
    _in_cable_il: float = CYRO_INPUT_CABLE_IL
    _cold_atten: float = CYRO_COLD_ATTEN
    _out_cable_il: float = CYRO_OUTPUT_CABLE_IL
    _lna_gain: float = CRYO_LNA_GAIN
    _lna_1dB_comp: float = CRYO_LNA_1dB_COMP

    @property
    def sample_il(self) -> float:
        return self._in_cable_il + self._cold_atten

    @property
    def total_gain_il(self) -> float:
        return (
            self._in_cable_il + self._cold_atten + self._out_cable_il + self._lna_gain
        )

    @property
    def input_1dB_comp(self) -> float:
        return self._lna_1dB_comp - self._in_cable_il - self._cold_atten


@dataclass
class VariableAtten(RFComponent):
    _type: str = "ZX76-31R5A-PNS+"
    _insert_loss: float = ZX76_31R5A_PNS_IL
    _atten_range: float = ZX76_31R5A_PNS_RANGE
    _atten_step: float = ZX76_31R5A_PNS_STEP
    _atten: float = 0.0
    _1dB_comp: float = ZX76_31R5A_PNS_1dB_COMP

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

    @property
    def input_1dB_comp(self) -> float:
        return self._1dB_comp


@dataclass
class SOUKRFMixerlessAttenAmpTransfer:
    atten_setting_range: np.ndarray = field(default_factory=lambda: np.array([]))
    bypass_tranfer_range: List[float] = field(default_factory=list)
    bypass_input_1dB_comp: List[float] = field(default_factory=list)
    amp_enable_tranfer_range: List[float] = field(default_factory=list)
    amp_enable_input_1dB_comp: List[float] = field(default_factory=list)
    atten_value_dB: float = 0.0
    bypass_state: bool = False
    total_gain_il: float = 0.0


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

    def _get_transfer(
        self, atten_range: float, atten_step: float
    ) -> SOUKRFMixerlessAttenAmpTransfer:
        transfer = SOUKRFMixerlessAttenAmpTransfer()
        transfer.atten_value_dB = self.atten
        transfer.bypass_state = self.bypass_state
        transfer.atten_setting_range = np.arange(
            0,
            atten_range,
            atten_step,
        )
        self.bypass_state = True
        for atten_setting in transfer.atten_setting_range:
            self.atten = atten_setting
            transfer.bypass_tranfer_range.append(self.total_gain_il)
            transfer.bypass_input_1dB_comp.append(self.input_1dB_comp)
        self.bypass_state = False
        for atten_setting in transfer.atten_setting_range:
            self.atten = atten_setting
            transfer.amp_enable_tranfer_range.append(self.total_gain_il)
            transfer.amp_enable_input_1dB_comp.append(self.input_1dB_comp)

        self.atten = transfer.atten_value_dB
        self.bypass_state = transfer.bypass_state
        transfer.total_gain_il = self.total_gain_il
        return transfer


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

    # order:
    # variable atten -> filter -> equalizer -> amplifier -> fixed atten

    @property
    def input_1dB_comp(self) -> float:
        return min(
            self.variable_atten.input_1dB_comp,
            self.filter.input_1dB_comp - self.variable_atten.total_gain_il,
            self.equalizer.input_1dB_comp
            - self.variable_atten.total_gain_il
            - self.filter.total_gain_il,
            self.amp.input_1dB_comp
            - self.equalizer.total_gain_il
            - self.filter.total_gain_il
            - self.variable_atten.total_gain_il,
            self.fixed_atten.input_1dB_comp
            - self.amp.total_gain_il
            - self.equalizer.total_gain_il
            - self.filter.total_gain_il
            - self.variable_atten.total_gain_il,
        )

    def get_transfer(self) -> SOUKRFMixerlessAttenAmpTransfer:
        return self._get_transfer(
            atten_range=self.variable_atten.atten_range,
            atten_step=self.variable_atten.atten_step,
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
            - self.variable_atten.total_gain_il
            - self.preamp.total_gain_il
            - self.filter.total_gain_il
            - self.equalizer.total_gain_il,
            self.preamp.input_1dB_comp
            - self.equalizer.total_gain_il
            - self.filter.total_gain_il,
        )

    def get_transfer(self) -> SOUKRFMixerlessAttenAmpTransfer:
        return self._get_transfer(
            atten_range=self.variable_atten.atten_range,
            atten_step=self.variable_atten.atten_step,
        )


@dataclass
class mimicAttenAmp:
    dev_name: Literal["recv_atten", "transmit_atten"]


@dataclass
class mimicSOUKRFMixerlessModuleChnAttenAmp:
    chn_idx: int
    atten_amp: mimicAttenAmp = field(init=False)
    atten_amp_level: SOUKRFMixerlessAttenAmpLevel = field(init=False)

    @property
    def atten_value_dB(self) -> float:
        return -self.atten_amp_level.atten

    @atten_value_dB.setter
    def atten_value_dB(self, value: float) -> None:
        self.atten_amp_level.atten = -value

    @property
    def amp_bypass(self) -> bool:
        return self.atten_amp_level.bypass_state

    @amp_bypass.setter
    def amp_bypass(self, value: bool) -> None:
        self.atten_amp_level.bypass_state = value


class mimicSOUKRFMixerlessModule:
    def __init__(self):
        self._atten_amp_channels: List[mimicSOUKRFMixerlessModuleChnAttenAmp] = []
        for chn_idx in range(2):  # Assuming 2 channels for the mimic module
            atten_amp_channel = mimicSOUKRFMixerlessModuleChnAttenAmp(chn_idx=chn_idx)
            atten_amp_channel.atten_amp = mimicAttenAmp(dev_name="recv_atten")
            atten_amp_channel.atten_amp_level = (
                SOUKRFMixerlessRecvAttenAmpLevel()
            )  # initialize attenuator level object
            self._atten_amp_channels.append(atten_amp_channel)

            atten_amp_channel = mimicSOUKRFMixerlessModuleChnAttenAmp(chn_idx=chn_idx)
            atten_amp_channel.atten_amp = mimicAttenAmp(dev_name="transmit_atten")
            atten_amp_channel.atten_amp_level = (
                SOUKRFMixerlessTransmitAttenAmpLevel()
            )  # initialize attenuator level object
            self._atten_amp_channels.append(atten_amp_channel)

    def _get_atten_amp(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> mimicSOUKRFMixerlessModuleChnAttenAmp:
        target_atten_amp = None
        for atten_amp_channel in self._atten_amp_channels:
            if (
                atten_amp_channel.chn_idx == chn_idx
                and atten_amp_channel.atten_amp.dev_name == dev_name
            ):
                target_atten_amp = atten_amp_channel
                break
        if target_atten_amp is None:
            raise ValueError(
                f"Attenuator with dev_name {dev_name} on channel {chn_idx} not found."
            )
        return target_atten_amp

    def set_attenuation(
        self,
        chn_idx: int,
        dev_name: Literal["recv_atten", "transmit_atten"],
        attenuation_dB: float,
    ) -> None:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        target_atten_amp.atten_value_dB = attenuation_dB

    def get_attenuation_value(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> float:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        return target_atten_amp.atten_value_dB

    def set_amp_bypass_state(
        self,
        chn_idx: int,
        dev_name: Literal["recv_atten", "transmit_atten"],
        bypass: bool,
    ) -> None:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        target_atten_amp.amp_bypass = bypass

    def get_amp_bypass_state(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> bool:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        return target_atten_amp.amp_bypass

    def get_transfer(
        self, chn_idx: int
    ) -> Tuple[SOUKRFMixerlessAttenAmpTransfer, SOUKRFMixerlessAttenAmpTransfer]:
        transmit_atten_amp_level: SOUKRFMixerlessTransmitAttenAmpLevel = (
            self._get_atten_amp(chn_idx, "transmit_atten").atten_amp_level
        )
        transmit_transfer = transmit_atten_amp_level.get_transfer()

        recv_atten_amp_level: SOUKRFMixerlessRecvAttenAmpLevel = self._get_atten_amp(
            chn_idx, "recv_atten"
        ).atten_amp_level
        recv_transfer = recv_atten_amp_level.get_transfer()
        return transmit_transfer, recv_transfer

    def plot_transfer(
        self,
        chn_idx: int,
        total_input_power: float = None,
        num_tones: int = None,
        cryo_sample_component: SampleCryo = None,
        image_path_name: str = None,
    ) -> None:
        transmit_transfer, recv_transfer = self.get_transfer(chn_idx)

        # Determine figure size based on number of subplots
        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            plt.figure(figsize=(32, 8))
        else:
            plt.figure(figsize=(12, 8))

        plt.suptitle(f"Power budget analysis for Channel {chn_idx}")
        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            per_tone_input_power = total_input_power - 10 * np.log10(num_tones)

            def transmit_x_forward(x):
                return x + per_tone_input_power - transmit_transfer.atten_value_dB

            def transmit_x_inverse(x):
                return x - per_tone_input_power - transmit_transfer.atten_value_dB

            def transmit_y_forward(y):
                return y + per_tone_input_power

            def transmit_y_inverse(y):
                return y - per_tone_input_power

            def cryo_y_forward(y):
                return (
                    y
                    + cryo_sample_component.total_gain_il
                    - cryo_sample_component.sample_il
                )

            def cryo_y_inverse(y):
                return (
                    y
                    - cryo_sample_component.total_gain_il
                    + cryo_sample_component.sample_il
                )

            def recv_x_forward(x):
                return (
                    x
                    + per_tone_input_power
                    + transmit_transfer.total_gain_il
                    + cryo_sample_component.total_gain_il
                    - recv_transfer.atten_value_dB
                )

            def recv_x_inverse(x):
                return (
                    x
                    - per_tone_input_power
                    - transmit_transfer.total_gain_il
                    - cryo_sample_component.total_gain_il
                    - recv_transfer.atten_value_dB
                )

            def recv_y_forward(y):
                return (
                    y
                    + 10 * np.log10(num_tones)
                    + per_tone_input_power
                    + transmit_transfer.total_gain_il
                    + cryo_sample_component.total_gain_il
                )

            def recv_y_inverse(y):
                return (
                    y
                    - 10 * np.log10(num_tones)
                    - per_tone_input_power
                    - transmit_transfer.total_gain_il
                    - cryo_sample_component.total_gain_il
                )

            plt.subplot(1, 5, 1)
            plt.plot(
                transmit_transfer.atten_setting_range,
                transmit_transfer.bypass_input_1dB_comp,
                label="Input 1dB Compression with Amplifier Bypassed",
                marker="o",
                markersize=3,
                linestyle="--",
            )
            plt.plot(
                transmit_transfer.atten_setting_range,
                transmit_transfer.amp_enable_input_1dB_comp,
                label="Input 1dB Compression with Amplifier Enabled",
                marker="x",
                markersize=6,
                linestyle="--",
            )
            plt.axhline(
                total_input_power,
                color="red",
                linestyle="--",
                label=f"Total Input Power ({total_input_power:.2f} dBm)",
            )
            plt.title("Transmit Setting vs 1dB Compression")
            plt.xlabel("Attenuation Setting (dB)")
            plt.ylabel("Input 1dB Compression (dBm)")
            plt.legend()
            plt.grid(True)
            plt.subplot(1, 5, 2)
        else:
            plt.subplot(1, 2, 1)
        plt.plot(
            transmit_transfer.atten_setting_range,
            transmit_transfer.bypass_tranfer_range,
            label="Transmit Attenuation with Amplifier Bypassed",
            marker="o",
            markersize=3,
        )
        plt.plot(
            transmit_transfer.atten_setting_range,
            transmit_transfer.amp_enable_tranfer_range,
            label="Transmit Attenuation with Amplifier Enabled",
            marker="x",
            markersize=6,
        )
        plt.scatter(
            transmit_transfer.atten_value_dB,
            transmit_transfer.total_gain_il,
            color="red",
            marker="o",
            s=64,
            label="Current Setting",
        )
        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            secax_x = plt.gca().secondary_xaxis(
                "top", functions=(transmit_x_forward, transmit_x_inverse)
            )
            secax_x.set_xlabel("Per-Tone Input Power (dBm)")

            secax_y = plt.gca().secondary_yaxis(
                "right", functions=(transmit_y_forward, transmit_y_inverse)
            )
            secax_y.set_ylabel("Tone Power towards Cryo (dBm)")

            plt.axvline(
                transmit_transfer.atten_value_dB,
                color="grey",
                linestyle="--",
                label=f"Per-Tone Input Power ({per_tone_input_power:.2f} dBm)",
            )
            plt.axhline(
                transmit_transfer.total_gain_il,
                color="grey",
                linestyle="--",
                label=f"Tone Power towards Cryo ({per_tone_input_power + transmit_transfer.total_gain_il:.2f} dBm)",
            )
        plt.title("Transmit Setting vs Total Gain IL and Power Level")
        plt.xlabel("Attenuation Setting (dB)")
        plt.ylabel("Total Gain IL (dB)")
        plt.legend()
        plt.grid(True)
        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            plt.subplot(1, 5, 3)
            plt.plot(
                per_tone_input_power
                + transmit_transfer.total_gain_il
                + cryo_sample_component.sample_il,
                marker="o",
                markersize=6,
                linestyle="None",
                color="orange",
                label=f"Tone Power at Cryo Sample ({per_tone_input_power + transmit_transfer.total_gain_il + cryo_sample_component.sample_il:.2f} dBm)",
            )
            plt.plot(
                total_input_power
                + transmit_transfer.total_gain_il
                + cryo_sample_component.sample_il,
                marker="o",
                markersize=6,
                linestyle="None",
                color="blue",
                label=f"Total Power at Cryo Sample ({total_input_power + transmit_transfer.total_gain_il + cryo_sample_component.sample_il:.2f} dBm)",
            )
            plt.axhline(
                cryo_y_inverse(
                    cryo_sample_component.input_1dB_comp
                    + cryo_sample_component.total_gain_il
                ),
                color="red",
                linestyle="--",
                label=f"Cryo Output Total Power 1dB Compression ({cryo_sample_component.input_1dB_comp + cryo_sample_component.total_gain_il:.2f} dBm)",
            )
            secax_y = plt.gca().secondary_yaxis(
                "right", functions=(cryo_y_forward, cryo_y_inverse)
            )
            secax_y.set_ylabel("Cryo Output Power (dBm)")
            plt.xticks([])
            plt.legend()
            plt.title("Estimated Tone Power at Cryo Sample")
            plt.ylabel("Sample Input Power (dBm)")
            plt.grid(True)
            plt.subplot(1, 5, 4)
        else:
            plt.subplot(1, 2, 2)
        plt.plot(
            recv_transfer.atten_setting_range,
            recv_transfer.bypass_tranfer_range,
            label="Receive Attenuation with Amplifier Bypassed",
            marker="o",
            markersize=3,
        )
        plt.plot(
            recv_transfer.atten_setting_range,
            recv_transfer.amp_enable_tranfer_range,
            label="Receive Attenuation with Amplifier Enabled",
            marker="x",
            markersize=6,
        )
        plt.scatter(
            recv_transfer.atten_value_dB,
            recv_transfer.total_gain_il,
            color="red",
            marker="o",
            s=64,
            label="Current Setting",
        )
        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            secax_x = plt.gca().secondary_xaxis(
                "top", functions=(recv_x_forward, recv_x_inverse)
            )
            secax_x.set_xlabel(
                f"Tone Power from Cryo ({per_tone_input_power + transmit_transfer.total_gain_il + cryo_sample_component.total_gain_il:.2f} dBm)"
            )

            secax_y = plt.gca().secondary_yaxis(
                "right", functions=(recv_y_forward, recv_y_inverse)
            )
            secax_y.set_ylabel("Total Power towards RFSoC(dBm)")

            plt.axvline(
                recv_transfer.atten_value_dB,
                color="grey",
                linestyle="--",
                label=f"Tone Power from Cryo ({per_tone_input_power + transmit_transfer.total_gain_il + cryo_sample_component.total_gain_il:.2f} dBm)",
            )
            plt.axhline(
                recv_transfer.total_gain_il,
                color="grey",
                linestyle="--",
                label=f"Total Power towards RFSoC ({total_input_power + transmit_transfer.total_gain_il + cryo_sample_component.total_gain_il + recv_transfer.total_gain_il:.2f} dBm)",
            )
        plt.title("Receive Setting vs Total Gain IL and Power Level")
        plt.xlabel("Attenuation Setting (dB)")
        plt.ylabel("Total Gain IL (dB)")
        plt.legend()
        plt.grid(True)

        if (
            total_input_power is not None
            and num_tones is not None
            and cryo_sample_component is not None
        ):
            plt.subplot(1, 5, 5)
            plt.plot(
                recv_transfer.atten_setting_range,
                recv_transfer.bypass_input_1dB_comp,
                label="Input 1dB Compression with Amplifier Bypassed",
                marker="o",
                markersize=3,
                linestyle="--",
            )
            plt.plot(
                recv_transfer.atten_setting_range,
                recv_transfer.amp_enable_input_1dB_comp,
                label="Input 1dB Compression with Amplifier Enabled",
                marker="x",
                markersize=6,
                linestyle="--",
            )
            plt.axhline(
                total_input_power
                + transmit_transfer.total_gain_il
                + cryo_sample_component.total_gain_il,
                color="red",
                linestyle="--",
                label=f"Total Power from Cryo ({total_input_power + transmit_transfer.total_gain_il + cryo_sample_component.total_gain_il:.2f} dBm)",
            )
            plt.title("Receive Setting vs 1dB Compression")
            plt.xlabel("Attenuation Setting (dB)")
            plt.ylabel("Input 1dB Compression (dBm)")
            plt.legend()
            plt.grid(True)

        plt.subplots_adjust(wspace=0.35)

        if image_path_name is not None:
            if not image_path_name.endswith(".png"):
                image_path_name += ".png"
            if not os.path.exists(image_path_name):
                os.makedirs(os.path.dirname(image_path_name), exist_ok=True)
            plt.savefig(image_path_name, dpi=300, bbox_inches="tight")
        else:
            # Create .logdata directory if it doesn't exist
            os.makedirs(".logdata", exist_ok=True)

            plt.savefig(
                f".logdata/power_budget_channel_{chn_idx}.png",
                dpi=300,
                bbox_inches="tight",
            )
        plt.close()


def main():
    mimic_module = mimicSOUKRFMixerlessModule()
    mimic_module.set_attenuation(
        chn_idx=0, dev_name="transmit_atten", attenuation_dB=10
    )
    mimic_module.set_amp_bypass_state(chn_idx=0, dev_name="transmit_atten", bypass=True)
    mimic_module.set_attenuation(chn_idx=0, dev_name="recv_atten", attenuation_dB=3)
    mimic_module.set_amp_bypass_state(chn_idx=0, dev_name="recv_atten", bypass=False)
    mimic_module.plot_transfer(
        chn_idx=0,
        total_input_power=-15,
        num_tones=13,
        cryo_sample_component=SampleCryo(),
    )


if __name__ == "__main__":
    main()
