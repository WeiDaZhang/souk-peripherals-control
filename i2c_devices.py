from smbus2 import SMBus
import logging
import time

RETRY_DELAY_SECONDS = 0.5
MAX_RETRIES = 5


class I2CDeviceError(OSError):
    """Raised when an I2C operation fails after exhausting retries."""


class I2CDevice:
    def __init__(self, dev_name: str, i2c_bus: SMBus, dev_addr: int):
        self.addr = dev_addr
        self.name = dev_name
        self._bus = i2c_bus
        self._retry("probing device", self._bus.read_byte, self.addr)

    @property
    def dev_addr(self) -> int:
        return self.addr

    @property
    def dev_name(self) -> str:
        return self.name

    def _retry(self, op_desc: str, func, *args):
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args)
            # OSError also covers BlockingIOError/TimeoutError, which are
            # the errors actually raised for a busy/unresponsive bus.
            except OSError as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    logging.warning(
                        f"Error {op_desc} on device {self.name} at address {self.addr} "
                        f"(attempt {attempt}/{MAX_RETRIES}): {e}, retrying after delay ..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
        logging.error(
            f"Failed {op_desc} on device {self.name} at address {self.addr} "
            f"after {MAX_RETRIES} attempts: {last_error}"
        )
        raise I2CDeviceError(
            f"Failed {op_desc} on device {self.name} at address {self.addr} "
            f"after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error

    def read(self, length: int = 1, register: int = None) -> list:
        logging.debug(
            f"Reading {length} bytes from device {self.name} at address {self.addr}"
        )
        if length == 1:
            if register is None:
                return [self._retry("reading byte", self._bus.read_byte, self.addr)]
            return [
                self._retry(
                    "reading byte data", self._bus.read_byte_data, self.addr, register
                )
            ]
        if register is None:
            register = 0x00  # default register
        return self._retry(
            "reading i2c block data",
            self._bus.read_i2c_block_data,
            self.addr,
            register,
            length,
        )

    def write(self, data, register: int = None) -> None:
        logging.debug(
            f"Writing {len(data) if isinstance(data, list) else 1} byte(s) of data to device {self.name} at address {self.addr}"
        )
        if isinstance(data, int):
            if register is None:
                self._retry("writing byte", self._bus.write_byte, self.addr, data)
            else:
                self._retry(
                    "writing byte data",
                    self._bus.write_byte_data,
                    self.addr,
                    register,
                    data,
                )
        elif isinstance(data, list):
            if register is None:
                register = 0x00  # default register
            self._retry(
                "writing i2c block data",
                self._bus.write_i2c_block_data,
                self.addr,
                register,
                data,
            )
        else:
            raise ValueError("Data must be an integer or a list of integers.")
