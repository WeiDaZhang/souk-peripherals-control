from typing import Tuple
from dataclasses import dataclass
import logging

from smbus2 import SMBus

from lna_voltages_utils import parallel_resistance, reverse_parallel_resistance
from ad511_0_2_4bcpz_5_10_80 import (
    AD511_0_2_4BCPZ_5_10_80,
    AD511_0_2_4BCPZ_5_10_80HWConfig,
)
from ltc2481cdd import LTC2481CDD, LTC2481CDDHWConfig


@dataclass(frozen=True)
class LNAMonitorHWConfig:
    r_dac_hw_config: AD511_0_2_4BCPZ_5_10_80HWConfig
    remote_adc_hw_config: LTC2481CDDHWConfig
    imonitor_adc_hw_config: LTC2481CDDHWConfig
    switch_status: bool = True  # True = ON (short), False = OFF (open)
    r_RTop1_kOhm: float = 2.7  # switched resistor
    r_RBot1_kOhm: float = 20.0  # fixed resistor
    r_RAdj1_kOhm: float = 18.0  # parallel resistor to the digital potentiometer
    r_LDO_set_kOhm: float = 82.0  # Set resistor for LDO on source
    r_RSENSE_OHMS: float = 100.0  # Sense resistor for Imonitor
    i_set_LDO: float = 0.1e-3  # 100 µA set current for LDO on source (MUST NOT CHANGE)

    def __post_init__(self):
        if self.i_set_LDO != 0.1e-3:
            raise ValueError("i_set_LDO must NOT be changed.")


class LNAMonitor:
    def __init__(self, i2c_bus: SMBus, hw_config: LNAMonitorHWConfig):
        self._r_dac = AD511_0_2_4BCPZ_5_10_80(
            dev_name="r_dac",
            i2c_bus=i2c_bus,
            res=hw_config.r_dac_hw_config.RESOLUTION,
            r_full_scale_kOhm=hw_config.r_dac_hw_config.R_FULL_SCALE_KOHM,
            dev_addr=hw_config.r_dac_hw_config.DEV_ADDR,
        )
        self._remote_adc = LTC2481CDD(
            dev_name="remote_adc",
            i2c_bus=i2c_bus,
            ca0=hw_config.remote_adc_hw_config.CA0,
            ca1=hw_config.remote_adc_hw_config.CA1,
            references=hw_config.remote_adc_hw_config.REFERENCES,
            v_operation=hw_config.remote_adc_hw_config.V_OPERATION,
        )
        self._imonitor_adc = LTC2481CDD(
            dev_name="imonitor_adc",
            i2c_bus=i2c_bus,
            ca0=hw_config.imonitor_adc_hw_config.CA0,
            ca1=hw_config.imonitor_adc_hw_config.CA1,
            references=hw_config.imonitor_adc_hw_config.REFERENCES,
            v_operation=hw_config.imonitor_adc_hw_config.V_OPERATION,
        )
        self._hw_config = hw_config

    @property
    def local_voltage_range(self) -> Tuple[float, float]:
        """Calculates the achievable local voltage range based on the hardware configuration.
        Returns:
            tuple[float, float]: (min_voltage, max_voltage) in volts.
        """
        v_min = self._r_dac_r_aw_to_local_voltage(self._r_dac.r_aw_range[0])
        v_max = self._r_dac_r_aw_to_local_voltage(self._r_dac.r_aw_range[1])
        return (v_min, v_max)

    def _local_voltage_to_r_dac_r_aw(self, v_local: float) -> float:
        return reverse_parallel_resistance(
            reverse_parallel_resistance(
                v_local / self._hw_config.i_set_LDO,
                self._hw_config.r_LDO_set_kOhm * 1000,
            )
            - (
                self._hw_config.r_RTop1_kOhm * 1000
                if not self._hw_config.switch_status
                else 0
            )
            - self._hw_config.r_RBot1_kOhm * 1000,
            self._hw_config.r_RAdj1_kOhm * 1000,
        )

    def _r_dac_r_aw_to_local_voltage(self, r_aw: float) -> float:
        r_paral = parallel_resistance(r_aw, self._hw_config.r_RAdj1_kOhm * 1000)
        r_total = parallel_resistance(
            r_paral
            + (
                self._hw_config.r_RTop1_kOhm * 1000
                if not self._hw_config.switch_status
                else 0
            )
            + self._hw_config.r_RBot1_kOhm * 1000,
            self._hw_config.r_LDO_set_kOhm * 1000,
        )
        logging.debug(
            f"r_aw: {r_aw:.2f} Ohm, r_paral: {r_paral:.2f} Ohm, r_total: {r_total:.2f} Ohm"
        )
        return self._hw_config.i_set_LDO * r_total

    def set_local_voltage(self, v_local: float) -> float:
        """Calculates and sets the DAC resistance to achieve the desired local voltage.
        Args:
            v_local (float): Desired local voltage in volts.
        Returns:
            float: The actual local voltage set after adjusting the DAC.
        """
        r_aw = self._local_voltage_to_r_dac_r_aw(v_local)
        self._r_dac.r_aw = r_aw
        return self._r_dac_r_aw_to_local_voltage(self._r_dac.r_aw)

    def read_local_voltage(self) -> float:
        """Reads the local voltage based on the current DAC resistance.
        Returns:
            float: The local voltage in volts.
        """
        return self._r_dac_r_aw_to_local_voltage(self._r_dac.r_aw)

    def read_remote_voltage(self) -> float:
        """Reads the remote voltage from the remote ADC.
        Returns:
            float: The remote voltage in volts.
        """
        return self._remote_adc.read_voltage()

    def read_bias_current(self) -> float:
        """Reads the bias current from the imonitor ADC.
        Returns:
            float: The bias current in amperes.
        """
        return self._imonitor_adc.read_voltage() / self._hw_config.r_RSENSE_OHMS
