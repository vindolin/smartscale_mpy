esptool --port /dev/ttyACM2 erase-flash
esptool --port /dev/ttyACM2 --baud 921600 write-flash 0 firmware/ESP32_GENERIC_C3-20251129-v1.27.0-preview.468.g41acdd8083.bin
