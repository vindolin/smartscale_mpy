import machine
import asyncio
import test


BLUE_LED_PIN = 8

def install_packages():
    import mip
    mip.install("aioble")

async def pause_before_run():
    for i in range(5, 0, -1):
        print(f"Starting in {i} seconds...")
        await asyncio.sleep(1)

def run():
    # asyncio.run(pause_before_run()) # not working :(
    asyncio.run(test.main())

pause_before_run()
machine.PWM(machine.Pin(BLUE_LED_PIN), freq=5000, duty_u16=65535)
# run()
