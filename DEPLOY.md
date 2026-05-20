# Deployment Guide

## Prerequisites

- ESP32 board with MicroPython v1.28.0+ firmware
- AHT10 sensor + GM009605 OLED (SSD1306 driver) wired per README
- `mpremote`, `rshell`, `ampy`, or Thonny for file upload

## Flash MicroPython

```bash
# Erase
esptool.py --port /dev/ttyUSB0 erase_flash

# Flash (ESP32 generic firmware)
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x1000 ESP32_GENERIC-20260406-v1.28.0.bin
```

## Upload Files

```bash
# Using mpremote
mpremote cp boot.py :
mpremote cp ringbuf.py :
mpremote cp graph.py :
mpremote cp main.py :
mpremote cp ahtx0.py :
mpremote cp ssd1306.py :

# Or all at once
mpremote cp boot.py ringbuf.py graph.py ssd1306.py ahtx0.py main.py :

# Using rshell
rshell cp boot.py /pyboard/boot.py
rshell cp ringbuf.py /pyboard/ringbuf.py
rshell cp graph.py /pyboard/graph.py
rshell cp main.py /pyboard/main.py
rshell cp ahtx0.py /pyboard/ahtx0.py
rshell cp ssd1306.py /pyboard/ssd1306.py

# Using ampy
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put ringbuf.py
ampy --port /dev/ttyUSB0 put graph.py
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put ahtx0.py
ampy --port /dev/ttyUSB0 put ssd1306.py
```

## Verify

Reset the device (or press RST). The OLED should show:
1. Live temperature and humidity updating every 2 seconds
2. 24h graph (temperature or humidity, toggles every 10s)
3. Range label on the status line
