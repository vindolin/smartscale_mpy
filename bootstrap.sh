# use first first found ttyACM* if no argument is given

if [ -z "$1" ]; then
  PORT=$(ls /dev/ttyACM* | head -n 1 | sed 's/\/dev\///')
else
  PORT=$1
fi

echo "Using port: /dev/$PORT"

esptool --port /dev/$PORT erase-flash
# esptool --port /dev/$PORT --baud 921600 write-flash 0 firmware/ESP32_GENERIC_C3-20251129-v1.27.0-preview.468.g41acdd8083.bin
esptool --port /dev/$PORT --baud 921600 write-flash 0 firmware/ESP32_GENERIC_C3-20250911-v1.26.1.bin

