from smbus2 import SMBus
import logging
import time

RETRY_DELAY_SECONDS = 1.2345


class I2CDevice:
    def __init__(self, dev_name: str, i2c_bus: SMBus, dev_addr: int):
        self.addr = dev_addr
        self.name = dev_name
        self._bus = i2c_bus
        try:
            self._bus.read_byte(self.addr)
        except Exception as e:
            raise ConnectionError(
                f"Failed to communicate with device at address {self.addr}: {e}"
            )

    @property
    def dev_addr(self) -> int:
        return self.addr

    @property
    def dev_name(self) -> str:
        return self.name

    def read(self, length: int = 1, register: int = None) -> list:
        logging.debug(
            f"Reading {length} bytes from device {self.name} at address {self.addr}"
        )
        if length == 1:
            if register is None:
                try:
                    return [self._bus.read_byte(self.addr)]
                except OSError as e:
                    logging.error(
                        f"Error reading byte from device {self.name} at address {self.addr}: {e}, trying again after delay ..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                    return [self._bus.read_byte(self.addr)]
            else:
                try:
                    return [self._bus.read_byte_data(self.addr, register)]
                except OSError as e:
                    logging.error(
                        f"Error reading byte data from device {self.name} at address {self.addr}, register {register}: {e}, trying again after delay ..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                    return [self._bus.read_byte_data(self.addr, register)]
        else:
            if register is None:
                register = 0x00  # default register
            try:
                return self._bus.read_i2c_block_data(self.addr, register, length)
            except OSError as e:
                logging.error(
                    f"Error reading i2c block data from device {self.name} at address {self.addr}, register {register}: {e}, trying again after delay ..."
                )
                time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                return self._bus.read_i2c_block_data(self.addr, register, length)

    def write(self, data, register: int = None) -> None:
        logging.debug(
            f"Writing {len(data) if isinstance(data, list) else 1} byte(s) of data to device {self.name} at address {self.addr}"
        )
        if isinstance(data, int):
            if register is None:
                try:
                    self._bus.write_byte(self.addr, data)
                except OSError as e:
                    logging.error(
                        f"Error writing byte to device {self.name} at address {self.addr}: {e}, trying again after delay ..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                    self._bus.write_byte(self.addr, data)
            else:
                try:
                    self._bus.write_byte_data(self.addr, register, data)
                except OSError as e:
                    logging.error(
                        f"Error writing byte data to device {self.name} at address {self.addr}, register {register}: {e}, trying again after delay ..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                    self._bus.write_byte_data(self.addr, register, data)
        elif isinstance(data, list):
            if register is None:
                register = 0x00  # default register
            try:
                self._bus.write_i2c_block_data(self.addr, register, data)
            except OSError as e:
                logging.error(
                    f"Error writing i2c block data to device {self.name} at address {self.addr}, register {register}: {e}, trying again after delay ..."
                )
                time.sleep(RETRY_DELAY_SECONDS)  # small delay before retry
                self._bus.write_i2c_block_data(self.addr, register, data)
        else:
            raise ValueError("Data must be an integer or a list of integers.")
