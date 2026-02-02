import logging
import time
from typing import Literal, Dict, List, Optional
from dataclasses import dataclass, field

from smbus2 import SMBus

from max732_8_9 import MAX732_8_9

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
    atten_value_dB: float = field(default=0.0)
    amp_bypass: bool = field(default=False)


class SOUKRFMixerlessModule:
    def __init__(
        self, i2c_bus: SMBus, hw_config_list: List[SOUKRFMixerlessModuleChnHWConfig]
    ):
        if len(hw_config_list) >= 2:
            raise ValueError("Only up to 2 channels are supported.")
        else:
            self._n_channels = len(hw_config_list)
        self._atten_amp_channel: List[SOUKRFMixerlessModuleChnAttenAmp] = []
        self._hw_config_list = hw_config_list
        for chn_idx, hw_config in enumerate(hw_config_list):
            self._atten_amp_channel.append(
                SOUKRFMixerlessModuleChnAttenAmp(
                    chn_idx=chn_idx,
                )
            )
            self._atten_amp_channel[-1].atten_amp = MAX732_8_9(
                dev_name="recv_atten",
                i2c_bus=i2c_bus,
                ad2=GPIO_ADDR_RESISTOR_MAP["recv"]["ad2"][hw_config.r12_r17],
                ad1=GPIO_ADDR_RESISTOR_MAP["recv"]["ad1"][hw_config.r9_r14],
                ad0=GPIO_ADDR_RESISTOR_MAP["recv"]["ad0"][hw_config.r8_r13],
                dev_type=hw_config.u4_type,
            )
            self._atten_amp_channel[-1].atten_value_dB = 0.0
            self._atten_amp_channel[-1].amp_bypass = False
            self._atten_amp_channel.append(
                SOUKRFMixerlessModuleChnAttenAmp(
                    chn_idx=chn_idx,
                )
            )
            self._atten_amp_channel[-1].atten_amp = MAX732_8_9(
                dev_name="transmit_atten",
                i2c_bus=i2c_bus,
                ad2=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad2"][hw_config.r20_r23],
                ad1=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad1"][hw_config.r19_r22],
                ad0=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad0"][hw_config.r18_r21],
                dev_type=hw_config.u8_type,
            )
            self._atten_amp_channel[-1].atten_value_dB = 0.0
            self._atten_amp_channel[-1].amp_bypass = False
        self._latch_bit = [
            atten_map["bit"]
            for atten_map in list(ATTEN_CONN_MAP.values())
            if atten_map["atten"] == "latch"
        ][0]
        for chn_idx in range(self._n_channels):
            self.set_attenuation(chn_idx, "recv_atten", 0.0)
            self.set_attenuation(chn_idx, "transmit_atten", 0.0)
            self.set_amp_bypass_state(chn_idx, "recv_atten", False)
            self.set_amp_bypass_state(chn_idx, "transmit_atten", False)

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
        if chn_idx >= self._n_channels or chn_idx < 0:
            raise ValueError(f"Invalid channel index: {chn_idx}.")
        target_atten_amp = None
        for atten_map in self._atten_amp_channel:
            if (
                atten_map.chn_idx == chn_idx
                and atten_map.atten_amp.dev_name == dev_name
            ):
                target_atten_amp = atten_map
                break
        if target_atten_amp is None:
            raise ValueError(
                f"Attenuator with dev_name {dev_name} on channel {chn_idx} not found."
            )
        logging.debug(
            f"Setting {dev_name} on channel {chn_idx} with bits {atten_bits_list} to states {atten_states} for {attenuation_dB} dB."
        )
        target_atten_amp.atten_amp.set_gpio_bit(
            bits=atten_bits_list, states=atten_states
        )
        target_atten_amp.atten_amp.pulse_gpio_bit(
            bit=self._latch_bit, pulse_width_ms=10
        )
        target_atten_amp.atten_value_dB = tap_pos * 0.5
        logging.info(
            f"Set {dev_name} attenuation to {target_atten_amp.atten_value_dB} dB."
        )

    def get_attenuation(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> float:
        target_atten_amp = None
        for atten_map in self._atten_amp_channel:
            if (
                atten_map.chn_idx == chn_idx
                and atten_map.atten_amp.dev_name == dev_name
            ):
                target_atten_amp = atten_map
                break
        if target_atten_amp is None:
            raise ValueError(
                f"Attenuator with dev_name {dev_name} on channel {chn_idx} not found."
            )
        return target_atten_amp.atten_value_dB

    def set_amp_bypass_state(
        self,
        chn_idx: int,
        dev_name: Literal["recv_atten", "transmit_atten"],
        bypass: bool,
    ) -> None:
        target_atten_amp = None
        for atten_map in self._atten_amp_channel:
            if (
                atten_map.chn_idx == chn_idx
                and atten_map.atten_amp.dev_name == dev_name
            ):
                target_atten_amp = atten_map
                break
        if target_atten_amp is None:
            raise ValueError(
                f"Attenuator with dev_name {dev_name} on channel {chn_idx} not found."
            )
        target_atten_amp.atten_amp.set_gpio_bit(
            bits=[AMP_BYPASS_BIT], states=[not bypass]
        )
        target_atten_amp.amp_bypass = bypass
        state_str = "bypassed" if bypass else "enabled"
        logging.info(f"Amplifier on channel {chn_idx} {dev_name} is {state_str}.")

    def get_amp_bypass_state(
        self, chn_idx: int, dev_name: Literal["recv_atten", "transmit_atten"]
    ) -> bool:
        target_atten_amp = None
        for atten_map in self._atten_amp_channel:
            if (
                atten_map.chn_idx == chn_idx
                and atten_map.atten_amp.dev_name == dev_name
            ):
                target_atten_amp = atten_map
                break
        if target_atten_amp is None:
            raise ValueError(
                f"Attenuator with dev_name {dev_name} on channel {chn_idx} not found."
            )
        states = target_atten_amp.atten_amp.get_gpio_bit(bits=[AMP_BYPASS_BIT])
        return not states[0]


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
        )  # Module A
    ]
    rfmixerless_module = SOUKRFMixerlessModule(i2c_bus, hw_config_list)
    for chn_idx in args.channels:
        dev_name = "recv_atten" if args.recv else "transmit_atten"
        rfmixerless_module.set_attenuation(chn_idx, dev_name, args.value)
        current_atten = rfmixerless_module.get_attenuation(chn_idx, dev_name)
        print(f"Channel {chn_idx} {dev_name} attenuation set to {current_atten} dB.")
        rfmixerless_module.set_amp_bypass_state(chn_idx, dev_name, args.bypass)
        current_bypass = rfmixerless_module.get_amp_bypass_state(chn_idx, dev_name)
        bypass_str = "bypassed" if current_bypass else "enabled"
        print(f"Channel {chn_idx} {dev_name} amplifier is {bypass_str}.")


if __name__ == "__main__":
    main()
