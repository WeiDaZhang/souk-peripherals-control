import logging
import time
from typing import Literal, Dict, List
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


class SOUKRFMixerlessModule:
    def __init__(
        self, i2c_bus: SMBus, hw_config_list: List[SOUKRFMixerlessModuleChnHWConfig]
    ):
        if len(hw_config_list) >= 2:
            raise ValueError("Only up to 2 channels are supported.")
        else:
            self._n_channels = len(hw_config_list)
        self._recv_atten = []
        self._transmit_atten = []
        self._hw_config_list = hw_config_list
        for chn_idx, hw_config in enumerate(hw_config_list):
            self._recv_atten.append(
                MAX732_8_9(
                    dev_name="recv_atten",
                    i2c_bus=i2c_bus,
                    ad2=GPIO_ADDR_RESISTOR_MAP["recv"]["ad2"][hw_config.r12_r17],
                    ad1=GPIO_ADDR_RESISTOR_MAP["recv"]["ad1"][hw_config.r9_r14],
                    ad0=GPIO_ADDR_RESISTOR_MAP["recv"]["ad0"][hw_config.r8_r13],
                    dev_type=hw_config.u4_type,
                )
            )
            self._transmit_atten.append(
                MAX732_8_9(
                    dev_name="transmit_atten",
                    i2c_bus=i2c_bus,
                    ad2=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad2"][hw_config.r20_r23],
                    ad1=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad1"][hw_config.r19_r22],
                    ad0=GPIO_ADDR_RESISTOR_MAP["transmit"]["ad0"][hw_config.r18_r21],
                    dev_type=hw_config.u8_type,
                )
            )
            # add attributes to store current attenuation values
            self._recv_atten[chn_idx].value_dB = 0.0
            self._transmit_atten[chn_idx].value_dB = 0.0
        self._latch_bit = [
            atten_map["bit"]
            for atten_map in list(ATTEN_CONN_MAP.values())
            if atten_map["atten"] == "latch"
        ][0]
        self.set_attenuation("recv_atten", 0.0)
        self.set_attenuation("transmit_atten", 0.0)

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
        atten_states = 6 * [False]
        for bit in range(6):
            if tap_pos >> bit & 0x01 == 1:
                for attens_map in list(ATTEN_CONN_MAP.values()):
                    if attens_map["atten"] == 0.5 * (2**bit):
                        atten_states[attens_map["bit"]] = True
                        atten_bits_list.append(attens_map["bit"])
        if chn_idx >= self._n_channels or chn_idx < 0:
            raise ValueError(f"Invalid channel index: {chn_idx}.")
        for selfattr_str in dir(self):
            selfattr: List[MAX732_8_9] = getattr(self, selfattr_str)
            if isinstance(selfattr, list):
                if all(
                    isinstance(selfattr_item, MAX732_8_9) for selfattr_item in selfattr
                ):
                    if dev_name == selfattr[chn_idx].dev_name:
                        target_attenuator: MAX732_8_9 = selfattr[chn_idx]
                        break
        target_attenuator.set_gpio_bit(bits=atten_bits_list, states=atten_states)
        target_attenuator.pulse_gpio_bit(bit=self._latch_bit, pulse_width_ms=10)
        target_attenuator.value_dB = tap_pos * 0.5
        logging.info(f"Set {dev_name} attenuation to {target_attenuator.value_dB} dB.")

    def recv_attenuation_value(self, chn_idx: int) -> float:
        return self._recv_atten[chn_idx].value_dB

    def transmit_attenuation_value(self, chn_idx: int) -> float:
        return self._transmit_atten[chn_idx].value_dB

    def bypass_amplifier(
        self,
        chn_idx: int,
        dev_name: Literal["recv_atten", "transmit_atten"],
        bypass: bool,
    ) -> None:
        for selfattr_str in dir(self):
            selfattr: List[MAX732_8_9] = getattr(self, selfattr_str)
            if isinstance(selfattr, list):
                if all(
                    isinstance(selfattr_item, MAX732_8_9) for selfattr_item in selfattr
                ):
                    if dev_name == selfattr[chn_idx].dev_name:
                        target_attenuator: MAX732_8_9 = selfattr[chn_idx]
                        break
        target_attenuator.set_gpio_bit(bits=[AMP_BYPASS_BIT], states=[bypass])
        state_str = "bypassed" if bypass else "enabled"
        logging.info(f"Amplifier on channel {chn_idx} {dev_name} is {state_str}.")

    def recv_amplifier_bypass_state(self, chn_idx: int) -> bool:
        states = self._recv_atten[chn_idx].get_gpio_bit(bits=[AMP_BYPASS_BIT])
        return states[0]

    def transmit_amplifier_bypass_state(self, chn_idx: int) -> bool:
        states = self._transmit_atten[chn_idx].get_gpio_bit(bits=[AMP_BYPASS_BIT])
        return states[0]
