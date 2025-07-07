import argparse
from smbus2 import SMBus
I2C_BUS = 1
DEV_ADDR = {"adc0": 0x24, "adc1": 0x25, "rdac": 0x2C, "eeprom": 0x2C}
RDAC_READ_CMD = 0x05
RDAC_WRITE_CMD = 0x02
RDAC_UPDATE_EEPROM_CMD = 0x01

SIG = 23
MSB = 22
LSB = 6
PG = (0x7,3)
IM = 1
SPD = 0
MAX_INT17 = 255*256 + 255
ADC_REF = 5.0
CORR_FACTOR = 1.00589

class ADC:
    def __init__(self, dev_name: str, i2c_bus: SMBus):
        self.addr = DEV_ADDR.get(dev_name, None)
        if not self.addr:
            raise KeyError(f"Device Name: {dev_name} is not defined")
        self.name = dev_name
        self.bus = i2c_bus

def read_adc(bus, adc_name):
    status_dict = {}
    status = bus.read_i2c_block_data(DEV_ADDR[adc_name], 0x00, length=3)
    status_uint24 = (status[0] << 16) + (status[1] << 8) + status[2]
    if (status_uint24 & (1 << SIG)) == (status_uint24 & (1 << MSB)):
        status_dict.update({"over_range": True})
        status_dict.update({"positive_over_range": bool(status_uint24 & (1 << SIG))})
    else:
        status_dict.update({"over_range": False})
        status_dict.update({"positive_over_range": None})
        value_uint17 = (status_uint24 & ~(1 << SIG)) >> LSB
        if value_uint17 > MAX_INT17:
            status_dict.update({"value": (value_uint17 - 2 * (MAX_INT17 + 1)) / MAX_INT17})
            status_dict.update({"voltage":status_dict["value"] * (ADC_REF/2) * CORR_FACTOR})
        else:
            status_dict.update({"value": value_uint17 / MAX_INT17})
            status_dict.update({"voltage":status_dict["value"] * (ADC_REF/2) * CORR_FACTOR})
    status_dict.update({"pg_status": status_uint24 & (PG[0] << PG[1])})
    status_dict.update({"im_status": status_uint24 & (1 << IM)})
    status_dict.update({"spd_status": status_uint24 & (1 << SPD)})
    status_dict.update({"voltage_valid": True})
    if status_dict["im_status"]:
        status_dict.update({"voltage_valid": False})
        status_dict.update({"message": "Temperature sensor read, voltage invalid."})
    if status_dict["pg_status"]:
        status_dict.update({"voltage_valid": False})
        status_dict.update({"message": "Programmable Gain enabled, voltage invalid."})
    return status_dict

def read_rdac(bus):
    bus.write_byte_data(DEV_ADDR["rdac"],RDAC_READ_CMD, 0)
    return bus.read_byte(DEV_ADDR["rdac"])

def write_rdac(bus, value):
    bus.write_byte_data(DEV_ADDR["rdac"], RDAC_WRITE_CMD, value)
    return read_rdac(bus)

def write_rdac_E2PROM(bus):
    bus.write_byte_data(DEV_ADDR["rdac"], RDAC_UPDATE_EEPROM_CMD, 0)
    while True:
        try:
            value = read_rdac(bus)
        except OSError:
            continue
        break 
    return value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--read", action="store_true")
    parser.add_argument("-d", "--dev", choices=list(DEV_ADDR.keys()), required=True)
    parser.add_argument("-v", "--value", type=int)
    args = parser.parse_args()
    with SMBus(I2C_BUS) as bus:
        if args.read:
            match args.dev:
                case "rdac":
                    value = read_rdac(bus=bus)
                    print(value)
                case "adc0"|"adc1":
                    value = read_adc(bus=bus, adc_name=args.dev)
                    print(value)
                case _:
                    pass
        else:
            match args.dev:
                case "rdac":
                    value = write_rdac(bus=bus, value=args.value)
                    print(value)
                case "eeprom":
                    value = write_rdac_E2PROM(bus=bus)
                    print(value)
                case _:
                    pass


if __name__ == "__main__":
    main()
