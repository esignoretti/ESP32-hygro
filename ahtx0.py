import utime
from micropython import const


class AHT10:
    AHTX0_I2CADDR_DEFAULT = const(0x38)
    AHTX0_CMD_INITIALIZE = 0xE1
    AHTX0_CMD_TRIGGER = const(0xAC)
    AHTX0_CMD_SOFTRESET = const(0xBA)
    AHTX0_STATUS_BUSY = const(0x80)
    AHTX0_STATUS_CALIBRATED = const(0x08)

    def __init__(self, i2c, address=AHTX0_I2CADDR_DEFAULT):
        utime.sleep_ms(20)
        self._i2c = i2c
        self._address = address
        self._buf = bytearray(6)
        self.reset()
        if not self.initialize():
            raise RuntimeError("Could not initialize")
        self._temp = None
        self._humidity = None

    def reset(self):
        self._buf[0] = self.AHTX0_CMD_SOFTRESET
        self._i2c.writeto(self._address, self._buf[0:1])
        utime.sleep_ms(20)

    def initialize(self):
        self._buf[0] = self.AHTX0_CMD_INITIALIZE
        self._buf[1] = 0x08
        self._buf[2] = 0x00
        self._i2c.writeto(self._address, self._buf[0:3])
        self._wait_for_idle()
        if not self.status & self.AHTX0_STATUS_CALIBRATED:
            return False
        return True

    @property
    def status(self):
        self._read_to_buffer()
        return self._buf[0]

    @property
    def relative_humidity(self):
        self._perform_measurement()
        self._humidity = (
            (self._buf[1] << 12) | (self._buf[2] << 4) | (self._buf[3] >> 4)
        )
        self._humidity = (self._humidity * 100) / 0x100000
        return self._humidity

    @property
    def temperature(self):
        self._perform_measurement()
        self._temp = ((self._buf[3] & 0xF) << 16) | (self._buf[4] << 8) | self._buf[5]
        self._temp = ((self._temp * 200.0) / 0x100000) - 50
        return self._temp

    def _read_to_buffer(self):
        self._i2c.readfrom_into(self._address, self._buf)

    def _trigger_measurement(self):
        self._buf[0] = self.AHTX0_CMD_TRIGGER
        self._buf[1] = 0x33
        self._buf[2] = 0x00
        self._i2c.writeto(self._address, self._buf[0:3])

    def _wait_for_idle(self, timeout_ms=1000):
        for _ in range(timeout_ms // 5):
            if not (self.status & self.AHTX0_STATUS_BUSY):
                return
            utime.sleep_ms(5)

    def _perform_measurement(self):
        self._trigger_measurement()
        self._wait_for_idle()
        self._read_to_buffer()
