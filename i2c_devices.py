from smbus2 import SMBus


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

    def _read_byte(self, register: int) -> int:
        return self._bus.read_byte_data(self.addr, register)

    def _write_byte(self, register: int, value: int) -> None:
        self._bus.write_byte_data(self.addr, register, value)

    def _read_block(self, register: int, length: int) -> list:
        return self._bus.read_i2c_block_data(self.addr, register, length)

    def _write_block(self, register: int, data: list) -> None:
        try:
            data = [int(byte) for byte in data]
        except ValueError:
            raise ValueError("All elements in data must be integers.")
        self._bus.write_i2c_block_data(self.addr, register, data)

    def read(self, length: int = 1, register: int = None) -> list:
        if length == 1:
            if register is None:
                return [self._bus.read_byte(self.addr)]
            else:
                return [self._bus.read_byte_data(self.addr, register)]
        else:
            if register is None:
                register = 0x00  # default register
            return self._bus.read_i2c_block_data(self.addr, register, length)

    def write(self, data, register: int = None) -> None:
        if isinstance(data, int):
            if register is None:
                self._bus.write_byte(self.addr, data)
            else:
                self._bus.write_byte_data(self.addr, register, data)
        elif isinstance(data, list):
            if register is None:
                register = 0x00  # default register
            self._bus.write_i2c_block_data(self.addr, register, data)
        else:
            raise ValueError("Data must be an integer or a list of integers.")
