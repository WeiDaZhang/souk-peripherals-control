
# SOUK LNA Bias Control and Monitoring

This repository provides I2C-based hardware abstraction, monitor and control interfaces for RF Module and CLKDist Module (LNA bias voltages).

## Features

- **I2C Device Abstraction**: Generic I2C device interface with automatic retries
- **Hardware Support**:
    - AD511 Digital Potentiometer (DAC)
    - LTC2481 ADC (Analog-to-Digital Converter)
    - TCA9548 I2C Multiplexer
    - MAX7328/7329 GPIO Expanders
    - RF Attenuators and Amplifiers
- **LNA Bias Voltage Control**: Set and monitor local and remote bias voltages
- **RF Component Management**: Attenuation, amplifier bypass, and transfer function analysis

## Project Structure

- `i2c_devices.py` - Base I2C device class with retry logic
- `ad511_0_2_4bcpz_5_10_80.py` - Digital potentiometer driver
- `ltc2481cdd.py` - 24-bit ADC driver
- `tca9548.py` - I2C multiplexer driver
- `max732_8_9.py` - GPIO expander driver
- `lna_monitor.py` - LNA monitoring and local voltage control
- `lna_voltages_utils.py` - Utility functions for voltage calculations and LNA V/I curve analysis
- `souk_rf_mixerless_atten_amp_level.py` - RF module insertion loss and gain calculation
- `souk_lna_bias_control_monitor.py` - Main control interface for multi-channel LNAs
- `souk_rf_mixerless_module.py` - RF attenuator and amplifier control
- `ldo_monitor.py` - Obsolete test code LDO monitoring utility

## Entrance Point

- `souk_lna_bias_control_monitor.py`
- `souk_rf_mixerless_module.py`

## Requirements

- Python 3.8+
- `smbus2` - I2C communication library
- `numpy` - Numerical computations
- `matplotlib` - Plotting (for transfer function analysis)

## Installation

```bash
pip install smbus2 numpy matplotlib
```

## Hardware Setup

- I2C Bus: `/dev/i2c-0` or `/dev/i2c-1`
- Ensure proper pull-up resistors on SDA/SCL lines
- Verify device address assignments via `i2cdetect`

## Testing

```bash
python3 souk_lna_bias_control_monitor.py --status --channels 1 12 13 14
python3 souk_rf_mixerless_module.py --get
```
