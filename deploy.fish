#!/usr/bin/fish
vf activate system
mpremote connect /dev/ttyACM2 fs ls
mpremote mip install aioble
mpremote fs cp ./fs/*.py :
