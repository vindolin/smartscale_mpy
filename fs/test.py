from collections import deque, OrderedDict
import struct
import asyncio
import time
import sys
from json import dumps

import network
import machine
import aioble
import ntptime
import umqtt.simple
import gc

import config
import localtime_cet
import ansi_colors as c

BLUE_LED_PIN = 8

SERIAL_STARTUP_DELAY_S = 1

ROOT_TOPIC = "smartscale_test"

BOOT_TIME_TOPIC = f"{ROOT_TOPIC}/bootTime"
GC_MEMORY_TOPIC = f"{ROOT_TOPIC}/gcMemory"
LOOP_COUNT_TOPIC = f"{ROOT_TOPIC}/loopCount"


class BlueLED:
    def __init__(self):
        self._freq = 5000
        self._off_duty = 1023
        self._on_duty = 800
        self._led = machine.PWM(machine.Pin(BLUE_LED_PIN), freq=self._freq, duty=self._off_duty)
        self._state = True
        self.set(self._state)

    def set(self, state):
        self._state = state
        self._led.duty(self._on_duty if state else self._off_duty)  # reversed

    def toggle(self):
        self.set(not self._state)

    def set_off(self):
        self.set(False)


def de_time(time):
    return f"{time[2]:02}.{time[1]:02}.{time[0]:04} {time[3]:02}:{time[4]:02}:{time[5]:02}"


def en_time(time):
    return f"{time[0]:04}-{time[1]:02}-{time[2]:02} {time[3]:02}:{time[4]:02}:{time[5]:02}"


async def wifi_connect():
    global wlan
    print(c.color("WIFI active", c.SUCCESS))

    if not wlan.isconnected():
        print("Connecting to network...")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        while not wlan.isconnected():
            await asyncio.sleep(1)
            print(".", end="")

        print()

    print(c.color("WIFI connected:", c.SUCCESS), wlan.ipconfig('addr4'))


def wifi_disconnect():
    global wlan
    wlan.active(False)
    print(c.color("WIFI disconnected", c.ERROR))


def get_ntp_time():
    try:
        ntptime.host = config.NTP_SERVER
        ntptime.settime()
        print(f"Formatted time: {de_time(localtime_cet.localtime())}")
    except:
        print(c.color("Failed to synchronize NTP time", c.ERROR))


async def publish_messages(mqtt_client, messages):
    for _ in range(5):
        try:
            for topic, payload, retain in messages:
                mqtt_client.publish(topic, payload, retain=retain)
                print(f"Published to MQTT: {topic} -> {payload}")

            await asyncio.sleep(1)  # give some time to send the messages before disconnecting
            break
        except Exception as e:
            print(f"Failed to publish messages to MQTT server: {e}")
            print("Reconnecting to WIFI and MQTT server...")
            await wifi_connect()
            mqtt_client.connect()


async def gc_collect():
    print(f"Memory before GC: {gc.mem_alloc() / 1024} KiB")
    gc.collect()
    mem_after_gc = gc.mem_alloc()
    print(f"Memory after GC: {mem_after_gc / 1024} KiB")

    await publish_messages(mqtt_client, [
        (LOOP_COUNT_TOPIC, str(loop_count), True),
        (GC_MEMORY_TOPIC, str(mem_after_gc), True),
    ])


async def ble_scan():
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


blue_led = BlueLED()
wlan = network.WLAN()
mqtt_client = umqtt.simple.MQTTClient("smartscale_test", config.MQTT_SERVER_IP, port=config.MQTT_SERVER_PORT, user=config.MQTT_SERVER_USER, password=config.MQTT_SERVER_PASSWORD)
watchdog = machine.WDT(timeout=3 * 60 * 1000)  # 3 minutes
ble_devices = OrderedDict()
loop_count = 0


async def main():
    global loop_count
    gc.enable()

    print()
    print("*** Testing ***")
    print()
    print("Getting local time...")

    await wifi_connect()
    get_ntp_time()
    mqtt_client.connect()

    boot_time = localtime_cet.localtime()

    # run the ble scan in the background
    asyncio.create_task(ble_scan())

    await publish_messages(mqtt_client, [
        (BOOT_TIME_TOPIC, en_time(boot_time), True),
    ])

    while True:
        watchdog.feed()
        print(f"Used memory: {gc.mem_alloc() / 1024} KiB")

        await publish_messages(mqtt_client, [
            (LOOP_COUNT_TOPIC, str(loop_count), True),
        ])

        loop_count += 1
        await asyncio.sleep(3)

# asyncio.run(main())
