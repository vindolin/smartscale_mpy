import machine
import asyncio
import test


BLUE_LED_PIN = 8

def install_packages():
    import mip
    mip.install("aioble")

def run():
    asyncio.run(test.main())

machine.PWM(machine.Pin(BLUE_LED_PIN), freq=5000, duty_u16=65535)

# run()
