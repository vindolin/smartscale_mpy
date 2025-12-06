from collections import deque, OrderedDict
import asyncio
from json import dumps

import machine
import aioble
import umqtt.simple
import gc

import config
import localtime_cet
import ansi_colors as c
import utils

BLUE_LED_PIN = 8

SERIAL_STARTUP_DELAY_S = 1

ROOT_TOPIC = "smartscale_test"

BOOT_TIME_TOPIC = f"{ROOT_TOPIC}/bootTime"
GC_MEMORY_TOPIC = f"{ROOT_TOPIC}/gcMemory"
BOOT_COUNT_TOPIC = f"{ROOT_TOPIC}/bootCount"
LOOP_COUNT_TOPIC = f"{ROOT_TOPIC}/loopCount"
LOOP_TIME_TOPIC = f"{ROOT_TOPIC}/loopTime"



async def gc_collect():
    print(f"Memory before GC: {gc.mem_alloc() / 1024} KiB")
    gc.collect()
    mem_after_gc = gc.mem_alloc()
    print(f"Memory after GC: {mem_after_gc / 1024} KiB")

    await utils.publish_messages([
        (GC_MEMORY_TOPIC, str(mem_after_gc), True),
    ])



async def ble_scan():
    ble_devices = OrderedDict()

    async with aioble.scan(0, interval_us=30000, window_us=30000, active=True) as scanner:
    # async with aioble.scan(0) as scanner:
        async for result in scanner:
            # print(dir(result))
            # print(dir(result.device))
            name = result.name()

            if not name:
                continue

            addr_hex = result.device.addr_hex()

            if not name in ble_devices:
                ble_devices[name] = addr_hex
                print(c.color(f"device: {name} addr: {addr_hex}", c.INFO))


async def main():
    mqtt_client = umqtt.simple.MQTTClient("smartscale_test", config.MQTT_SERVER_IP, port=config.MQTT_SERVER_PORT, user=config.MQTT_SERVER_USER, password=config.MQTT_SERVER_PASSWORD)
    utils.init(config.WIFI_SSID, config.WIFI_PASSWORD, mqtt_client)

    loop_count = 0
    blue_led = utils.LED(BLUE_LED_PIN)
    boot_count = utils.get_boot_count()
    uptime_ms = utils.Uptime()
    watchdog = machine.WDT(timeout=3 * 60 * 1000)  # 3 minutes

    gc.enable()

    print()
    print("*** Testing ***")
    print()
    print("Getting local time...")

    await utils.wifi_connect()
    utils.get_ntp_time(config.NTP_SERVER)
    mqtt_client.connect()

    # run the ble scan in the background
    asyncio.create_task(ble_scan())

    await utils.publish_messages([
        (BOOT_COUNT_TOPIC, str(boot_count), True),
        (BOOT_TIME_TOPIC, utils.de_time(localtime_cet.localtime()), True),
    ])

    while True:
        watchdog.feed()
        mem = gc.mem_alloc()
        print(f"Used memory: {mem / 1024} KiB")

        uptime = uptime_ms() // 1000
        print(f"Uptime: {uptime // 3600:02}:{((uptime % 3600) // 60):02}:{uptime % 60:02}")

        await utils.publish_messages([
            (LOOP_COUNT_TOPIC, str(loop_count), True),
            (LOOP_TIME_TOPIC, utils.de_time(localtime_cet.localtime()), True),
            (GC_MEMORY_TOPIC, str(mem), True),
        ])

        loop_count += 1
        await asyncio.sleep(3)

# asyncio.run(main())
