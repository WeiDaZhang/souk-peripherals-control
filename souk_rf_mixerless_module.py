import logging
import os
from typing import Literal, List, Tuple
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
from smbus2 import SMBus

from max732_8_9 import MAX732_8_9
from souk_rf_mixerless_atten_amp_level import (
    SOUKRFMixerlessAttenAmpLevel,
    SOUKRFMixerlessRecvAttenAmpLevel,
    SOUKRFMixerlessTransmitAttenAmpLevel,
    SOUKRFMixerlessAttenAmpTransfer,
    SampleCryo,
)

ATTEN_CONN_MAP = {
    "red_conn_pin2": {"bit": 2, "atten": 2.0},
    "orange_conn_pin1": {"bit": 3, "atten": 4.0},
    "yellow_conn_pin3": {"bit": 1, "atten": 1.0},
    "green_conn_pin4": {"bit": 0, "atten": 0.5},
    "white_conn_pin6": {"bit": 7, "atten": "latch"},
    "blue_conn_pin8": {"bit": 5, "atten": 16.0},
    "brown_conn_pin9": {"bit": 4, "atten": 8.0},
}

AMP_BYPASS_BIT = 6

GPIO_ADDR_RESISTOR_MAP = {
    "recv": {
        "ad0": {"R8": "high", "R13": "low"},
        "ad1": {"R9": "high", "R14": "low"},
        "ad2": {"R12": "high", "R17": "low"},
    },
    "transmit": {
        "ad0": {"R18": "high", "R21": "low"},
        "ad1": {"R19": "high", "R22": "low"},
        "ad2": {"R20": "high", "R23": "low"},
    },
}


@dataclass(frozen=True)
class SOUKRFMixerlessModuleChnHWConfig:
    r8_r13: Literal["R8", "R13"]  # resistor selection for i2c address
    r9_r14: Literal["R9", "R14"]  # resistor selection for i2c address
    r12_r17: Literal["R12", "R17"]  # resistor selection for i2c address
    r18_r21: Literal["R18", "R21"]  # resistor selection for i2c address
    r19_r22: Literal["R19", "R22"]  # resistor selection for i2c address
    r20_r23: Literal["R20", "R23"]  # resistor selection for i2c address
    u4_type: Literal["MAX7328", "MAX7329"]
    u8_type: Literal["MAX7328", "MAX7329"]

    def __post_init__(self):
        # validate resistor selections
        if self.r8_r13 not in GPIO_ADDR_RESISTOR_MAP["recv"]["ad0"].keys():
            raise ValueError(
                f"r8_r13 must be one of {GPIO_ADDR_RESISTOR_MAP['recv']['ad0'].keys()}"
            )
        if self.r9_r14 not in GPIO_ADDR_RESISTOR_MAP["recv"]["ad1"].keys():
            raise ValueError(
                f"r9_r14 must be one of {GPIO_ADDR_RESISTOR_MAP['recv']['ad1'].keys()}"
            )
        if self.r12_r17 not in GPIO_ADDR_RESISTOR_MAP["recv"]["ad2"].keys():
            raise ValueError(
                f"r12_r17 must be one of {GPIO_ADDR_RESISTOR_MAP['recv']['ad2'].keys()}"
            )
        if self.r18_r21 not in GPIO_ADDR_RESISTOR_MAP["transmit"]["ad0"].keys():
            raise ValueError(
                f"r18_r21 must be one of {GPIO_ADDR_RESISTOR_MAP['transmit']['ad0'].keys()}"
            )
        if self.r19_r22 not in GPIO_ADDR_RESISTOR_MAP["transmit"]["ad1"].keys():
            raise ValueError(
                f"r19_r22 must be one of {GPIO_ADDR_RESISTOR_MAP['transmit']['ad1'].keys()}"
            )
        if self.r20_r23 not in GPIO_ADDR_RESISTOR_MAP["transmit"]["ad2"].keys():
            raise ValueError(
                f"r20_r23 must be one of {GPIO_ADDR_RESISTOR_MAP['transmit']['ad2'].keys()}"
            )
        if self.u4_type not in ["MAX7328", "MAX7329"]:
            raise ValueError("u4_type must be either 'MAX7328' or 'MAX7329'")
        if self.u8_type not in ["MAX7328", "MAX7329"]:
            raise ValueError("u8_type must be either 'MAX7328' or 'MAX7329'")

    @classmethod
    def default_config(cls):
        return cls(
            r8_r13="R8",
            r9_r14="R9",
            r12_r17="R12",
            r18_r21="R18",
            r19_r22="R19",
            r20_r23="R20",
            u4_type="MAX7329",
            u8_type="MAX7329",
        )


@dataclass
class SOUKRFMixerlessModuleChnAttenAmp:
    chn_idx: int
    atten_amp: MAX732_8_9 = field(init=False)
    atten_amp_level: SOUKRFMixerlessAttenAmpLevel = field(init=False)
    atten_latch_bit: int = field(
        default=[
            atten_map["bit"]
            for atten_map in list(ATTEN_CONN_MAP.values())
            if atten_map["atten"] == "latch"
        ][0]
    )

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


class SOUKRFMixerlessModule:
    def __init__(
        self, i2c_bus: SMBus, hw_config_list: List[SOUKRFMixerlessModuleChnHWConfig]
    ):
        if len(hw_config_list) > 2:
            raise ValueError("Only up to 2 channels are supported.")
        else:
            self._n_channels = len(hw_config_list)
        self._atten_amp_channels: List[SOUKRFMixerlessModuleChnAttenAmp] = []
        self._hw_config_list = hw_config_list
        for chn_idx, hw_config in enumerate(hw_config_list):
            atten_amp_channel = SOUKRFMixerlessModuleChnAttenAmp(chn_idx=chn_idx)
            atten_amp_channel.atten_amp = MAX732_8_9(
                dev_name="recv_atten",
                i2c_bus=i2c_bus,
                ad2=GPIO_ADDR_RESISTOR_MAP["recv"]["ad2"][hw_config.r12_r17],
                ad1=GPIO_ADDR_RESISTOR_MAP["recv"]["ad1"][hw_config.r9_r14],
                ad0=GPIO_ADDR_RESISTOR_MAP["recv"]["ad0"][hw_config.r8_r13],
                dev_type=hw_config.u4_type,
            )
            atten_amp_channel.atten_amp_level = (
                SOUKRFMixerlessRecvAttenAmpLevel()
            )  # initialize attenuator level object
            self._get_amp_bypass(
                atten_amp_channel
            )  # initialize amp bypass state from hardware
            self._get_attenuation(
                atten_amp_channel
            )  # initialize attenuation value from hardware
            self._atten_amp_channels.append(atten_amp_channel)

            atten_amp_channel = SOUKRFMixerlessModuleChnAttenAmp(chn_idx=chn_idx)
            atten_amp_channel.atten_amp = MAX732_8_9(
                dev_name="transmit_atten",
                i2c_bus=i2c_bus,
                ad2=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad2"][hw_config.r20_r23],
                ad1=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad1"][hw_config.r19_r22],
                ad0=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad0"][hw_config.r18_r21],
                dev_type=hw_config.u8_type,
            )
            atten_amp_channel.atten_amp_level = (
                SOUKRFMixerlessTransmitAttenAmpLevel()
            )  # initialize attenuator level object
            self._get_amp_bypass(
                atten_amp_channel
            )  # initialize amp bypass state from hardware
            self._get_attenuation(
                atten_amp_channel
            )  # initialize attenuation value from hardware
            self._atten_amp_channels.append(atten_amp_channel)

    @property
    def n_channels(self) -> int:
        return self._n_channels

    def _get_atten_amp(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> SOUKRFMixerlessModuleChnAttenAmp:
        if chn_idx >= self._n_channels or chn_idx < 0:
            raise ValueError(f"Invalid channel index: {chn_idx}.")
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
        if not (0 <= attenuation_dB <= 31.5):
            raise ValueError("attenuation_dB must be between 0 and 31.5 dB.")
        tap_pos = int(attenuation_dB * 2)  # each step is 0.5 dB
        atten_bits_list = []
        atten_states = []
        for tap_bit in range(6):
            for attens_map in list(ATTEN_CONN_MAP.values()):
                if attens_map["atten"] == 0.5 * (2**tap_bit):
                    atten_bits_list.append(attens_map["bit"])
                    atten_states.append(tap_pos >> tap_bit & 0x01)
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        logging.debug(
            f"Setting {dev_name} on channel {chn_idx} with bits {atten_bits_list} to states {atten_states} for {attenuation_dB} dB."
        )
        target_atten_amp.atten_amp.set_gpio_bit(
            bits=atten_bits_list, states=atten_states
        )
        target_atten_amp.atten_amp.pulse_gpio_bit(
            bit=target_atten_amp.atten_latch_bit, pulse_width_ms=10
        )
        target_atten_amp.atten_value_dB = tap_pos * 0.5
        logging.info(
            f"Set {dev_name} attenuation to {target_atten_amp.atten_value_dB} dB."
        )

    def _get_attenuation(
        self, target_atten_amp: SOUKRFMixerlessModuleChnAttenAmp
    ) -> float:
        atten_bits_list = target_atten_amp.atten_amp.get_gpio_bit(
            bits=[
                attens_map["bit"]
                for attens_map in list(ATTEN_CONN_MAP.values())
                if attens_map["atten"] != "latch"
            ]
        )
        atten_value_dB = 0.0
        for bit_state, atten_value in zip(
            atten_bits_list,
            [
                attens_map["atten"]
                for attens_map in list(ATTEN_CONN_MAP.values())
                if attens_map["atten"] != "latch"
            ],
        ):
            if bit_state:
                atten_value_dB += atten_value
        target_atten_amp.atten_value_dB = atten_value_dB
        return target_atten_amp.atten_value_dB

    def get_attenuation_value(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> float:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        return self._get_attenuation(target_atten_amp)

    def set_amp_bypass_state(
        self,
        chn_idx: int,
        dev_name: Literal["recv_atten", "transmit_atten"],
        bypass: bool,
    ) -> None:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        target_atten_amp.atten_amp.set_gpio_bit(
            bits=[AMP_BYPASS_BIT], states=[not bypass]
        )
        target_atten_amp.amp_bypass = bypass
        state_str = "bypassed" if bypass else "enabled"
        logging.info(f"Amplifier on channel {chn_idx} {dev_name} is {state_str}.")

    def _get_amp_bypass(
        self, target_atten_amp: SOUKRFMixerlessModuleChnAttenAmp
    ) -> bool:
        states = target_atten_amp.atten_amp.get_gpio_bit(bits=[AMP_BYPASS_BIT])
        target_atten_amp.amp_bypass = not states[0]
        return target_atten_amp.amp_bypass

    def get_amp_bypass_state(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> bool:
        target_atten_amp = self._get_atten_amp(chn_idx, dev_name)
        return self._get_amp_bypass(target_atten_amp)

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
    import argparse

    parser = argparse.ArgumentParser(description="SOUK RF Mixerless Module Demo")
    parser.add_argument(
        "--channels",
        type=int,
        nargs="+",
        default=[0],
        help="List of RFMixerless module channels to operate on (0-indexed).",
    )
    parser.add_argument(
        "--recv",
        action="store_true",
        help="Target receive path attenuator if set; otherwise, target transmit path attenuator.",
    )
    parser.add_argument(
        "--value",
        type=float,
        default=1.2,
        help="attenuation value in dB to set (0 to 31.5 dB).",
    )
    parser.add_argument(
        "--bypass",
        action="store_true",
        help="Set amplifier to bypass mode if set; otherwise, set to normal mode.",
    )
    parser.add_argument(
        "--get",
        action="store_true",
        help="Get the current attenuation value and amplifier bypass state of all channels and paths.",
    )
    parser.add_argument(
        "--inpwr",
        type=float,
        default=-10.0,
        help="Total input power in dBm.",
    )
    parser.add_argument(
        "--ntones",
        type=int,
        default=16,
        help="Number of tones for power budget analysis.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    i2c_bus = SMBus(0)
    hw_config_list = [
        SOUKRFMixerlessModuleChnHWConfig(
            r8_r13="R8",
            r9_r14="R9",
            r12_r17="R17",
            r18_r21="R21",
            r19_r22="R19",
            r20_r23="R23",
            u4_type="MAX7329",
            u8_type="MAX7329",
        ),  # Module A
        SOUKRFMixerlessModuleChnHWConfig(
            r8_r13="R8",
            r9_r14="R14",
            r12_r17="R17",
            r18_r21="R21",
            r19_r22="R22",
            r20_r23="R23",
            u4_type="MAX7329",
            u8_type="MAX7329",
        ),  # Module B
    ]
    rfmixerless_module = SOUKRFMixerlessModule(i2c_bus, hw_config_list)
    if args.get:
        for chn_idx in range(rfmixerless_module.n_channels):
            for dev_name in ["recv_atten", "transmit_atten"]:
                current_atten = rfmixerless_module.get_attenuation_value(
                    chn_idx, dev_name
                )
                current_bypass = rfmixerless_module.get_amp_bypass_state(
                    chn_idx, dev_name
                )
                bypass_str = "bypassed" if current_bypass else "enabled"
                print(
                    f"Channel {chn_idx} {dev_name} attenuation: {current_atten} dB, amplifier is {bypass_str}."
                )
    else:
        for chn_idx in args.channels:
            dev_name = "recv_atten" if args.recv else "transmit_atten"
            rfmixerless_module.set_attenuation(chn_idx, dev_name, args.value)
            current_atten = rfmixerless_module.get_attenuation_value(chn_idx, dev_name)
            print(
                f"Channel {chn_idx} {dev_name} attenuation set to {current_atten} dB."
            )
            rfmixerless_module.set_amp_bypass_state(chn_idx, dev_name, args.bypass)
            current_bypass = rfmixerless_module.get_amp_bypass_state(chn_idx, dev_name)
            bypass_str = "bypassed" if current_bypass else "enabled"
            print(f"Channel {chn_idx} {dev_name} amplifier is {bypass_str}.")

    rfmixerless_module.plot_transfer(
        chn_idx=0,
        total_input_power=args.inpwr,
        num_tones=args.ntones,
        cryo_sample_component=SampleCryo(),
    )


if __name__ == "__main__":
    main()
