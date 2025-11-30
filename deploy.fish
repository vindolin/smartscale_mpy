#!/usr/bin/fish
vf activate system
mpremote connect /dev/ttyACM2 fs ls
mpremote mip install aioble
#mpremote fs cp ./fs/boot.py :
#mpremote fs cp ./fs/*.mpy :
mpremote fs cp ./fs/*.py :

