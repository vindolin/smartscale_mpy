from collections import deque, OrderedDict
import struct
import asyncio
import time
import sys
from json import dumps

import network
import machine
import aioble
import bluetooth
import ntptime
import umqtt.simple
import gc

import config
import utils
import calculations
import progress
import localtime_cet

USERS = OrderedDict({
    1: {'p_id': 1, 'age': 50, 'height': 159, 'is_male': False, 'activity_level': 2},
    2: {'p_id': 2, 'age': 55, 'height': 180, 'is_male': True, 'activity_level': 2},
})

BLUE_LED_PIN = 8
BOOT_BUTTON_PIN = 9

ROOT_TOPIC = "smartscaleX"

SCALE_DEVICE_NAME = 'Shape100'

SVC_BATTERY = bluetooth.UUID(0x180f)
CHR_BATTERY_LEVEL = bluetooth.UUID(0x2a19)

SVC_CURRENT_TIME = bluetooth.UUID(0x1805)
CHR_CURRENT_TIME = bluetooth.UUID(0x2a2b)
SVC_USER_DATA = bluetooth.UUID(0x181c)
CHR_USER_CONTROL_POINT = bluetooth.UUID(0x2a9f)

SVC_SOEHNLE = bluetooth.UUID('352e3000-28e9-40b8-a361-6db4cca4147c')
CHR_MEASUREMENT_NOTIFY = bluetooth.UUID('352e3001-28e9-40b8-a361-6db4cca4147c')
CHR_REQUEST_HISTORY = bluetooth.UUID('352e3002-28e9-40b8-a361-6db4cca4147c')

MEASUREMENT_OPCODE = 0x09

REQUEST_DELAY_S = 15
COLLECT_DELAY_S = 5
SERIAL_STARTUP_DELAY_S = 1

BOOT_COUNT_TOPIC = f"{ROOT_TOPIC}/_meta/bootCount"
BOOT_TIME_TOPIC = f"{ROOT_TOPIC}/_meta/bootTime"
MEASUREMENT_COUNT_TOPIC = f"{ROOT_TOPIC}/_meta/measurementCount"
GC_MEMORY_TOPIC = f"{ROOT_TOPIC}/_meta/gcMemory"
LOOP_COUNT_TOPIC = f"{ROOT_TOPIC}/_meta/loopCount"

BATTERY_LEVEL_TOPIC = f"{ROOT_TOPIC}/battery"
MEASUREMENT_TOPIC = f"{ROOT_TOPIC}/measurement"
MEASUREMENT_TIME_TOPIC = f"{ROOT_TOPIC}/measurementTime"

mqtt_client = umqtt.simple.MQTTClient("smartscale_client", config.MQTT_SERVER_IP, port=config.MQTT_SERVER_PORT, user=config.MQTT_SERVER_USER, password=config.MQTT_SERVER_PASSWORD)


class ScaleClient:
    def __init__(self, device_name):
        self.device_name = device_name
        self.device = None
        self.connection = None
        self.measurements = []
        self.latest_measurement = None
        self.scale_time_updated = False
        print()
        print("ScaleClient initialized for device:", self.device_name)

    async def find_scale(self):
        print("Scanning for scale:", self.device_name)
        blue_led.set(False)

        # async with aioble.scan(5000) as scanner:
        async with aioble.scan(0, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                watchdog.feed()

                if not result.name():
                    continue

                progress.print_spinner(toggle_cb=blue_led.toggle)

                if result.name() == self.device_name:
                    print()
                    print("Found scale:", result.device)  # someone stepped onto the scale, enabling its BLE
                    self.device = result.device
                    return


    async def connect(self):
        print("Connecting to device:", self.device)
        self.connection = await self.device.connect()
        if not self.connection:
            print("Failed to connect to scale:", self.device)
            return

        blue_led.set(False)
        print("Connected to scale:", self.device)


    async def run(self):
        blue_led.set(False)

        self.measurements = []
        self.latest_measurement = None

        await self.find_scale()

        if self.device:
            await self.connect()

        async with self.connection:
            battery_level = await self.read_battery_level()
            if battery_level is not None:
                print("Battery Level:", battery_level, "%")
            else:
                print("Failed to read battery level.")

            await self.update_scale_time()

            print(f"Weighing takes about {REQUEST_DELAY_S}s to finish...")
            await progress.show_progress_bar(REQUEST_DELAY_S, REQUEST_DELAY_S, 30, blue_led.toggle, blue_led.set_off)

            await self.subscribe_to_measurements()  # subscribe to measurement notifications

            print("Requesting measurement history...")
            await self.query_user_measurement_history()

            print("Waiting for measurements...")
            # this is the time for the notifications to arrive
            await progress.show_progress_bar(COLLECT_DELAY_S, COLLECT_DELAY_S, 30, blue_led.toggle, blue_led.set_off)

            # parse received measurements
            for i, _measurement in enumerate(self.measurements):
                measurement = self.parse_measurement(i, _measurement)
                if not self.latest_measurement or measurement['timestamp'] > self.latest_measurement['timestamp']:
                    self.latest_measurement = measurement

            if self.latest_measurement:
                print("Latest measurement:", self.latest_measurement)
                await self.publish_latest_measurement(mqtt_client, self.latest_measurement)
            else:
                print("No measurements received.")

            print("Leaving scale connection...")

        await self.wait_for_scale_to_disappear()


    async def read_battery_level(self):
        if not self.connection:
            return None

        service = await self.connection.service(SVC_BATTERY)
        characteristic = await service.characteristic(CHR_BATTERY_LEVEL)
        battery_level = await characteristic.read()
        return int.from_bytes(battery_level, 'little')


    async def update_scale_time(self):
        if self.scale_time_updated:
            print("Scale time already updated, skipping.")
            return

        service = await self.connection.service(SVC_CURRENT_TIME)
        characteristic = await service.characteristic(CHR_CURRENT_TIME)

        now_cet = localtime_cet.localtime()

        year = time.localtime()[0]
        month = time.localtime()[1]
        day = now_cet[2]
        hour = now_cet[3]
        minute = now_cet[4]
        second = now_cet[5]
        weekday = now_cet[6] + 1  # in BLE, Monday=1, Sunday=7

        data = struct.pack('<H5B3B', year, month, day, hour, minute, second, weekday, 0, 0)
        await characteristic.write(data)
        self.scale_time_updated = True
        print(f"Updated scale time to: {utils.de_time(now_cet)}")


    async def query_user_measurement_history(self):
        service = await self.connection.service(SVC_SOEHNLE)

        for user in USERS.values():
            request_chr = await service.characteristic(CHR_REQUEST_HISTORY)
            cmd = struct.pack('BB', MEASUREMENT_OPCODE, user['p_id'])
            print("Requesting measurements for user", user['p_id'])
            await request_chr.write(cmd)


    async def handle_measurements(self, notify_chr):
        print("Awaiting measurement notifications...")

        while True:
            await asyncio.sleep(1)  # why do we need this delay?

            while len(queue := notify_chr._notify_queue) > 0:
                measurement = queue.popleft()
                # print("received measurement:", measurement )
                self.measurements.append(measurement)
            notify_chr._notify_event.clear()


    async def subscribe_to_measurements(self):
        print("Subscribing to measurements...")
        service = await self.connection.service(SVC_SOEHNLE)

        notify_chr = await service.characteristic(CHR_MEASUREMENT_NOTIFY)

        notify_chr._notify_queue = deque((), 64) # by default, the notify queue can only hold 1 item, increase to 64
        await notify_chr.subscribe(notify=True)

        asyncio.create_task(self.handle_measurements(notify_chr))


    def parse_measurement(self, i, data):
        p_id = data[1]
        user = USERS[p_id]

        year = (data[2] << 8) | data[3]
        month = data[4]
        day = data[5]
        hour = data[6]
        minute = data[7]
        second = data[8]
        weight_kg = ((data[9] << 8) | data[10]) / 10.0
        imp5 = (data[11] << 8) | data[12]
        imp50 = (data[13] << 8) | data[14]

        if imp50 > 0:
            fat_pct = calculations.calculate_fat(user, weight_kg, imp50)
            water_pct = calculations.calculate_water(user, weight_kg, imp50)
            muscle_pct = calculations.calculate_muscle(user, weight_kg, imp50, imp5)
        else:
            fat_pct = 0.0
            water_pct = 0.0
            muscle_pct = 0.0

        # print(f"{i:2} {p_id :2} {year:04}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}, Weight: {weight_kg:4.1f} kg, Fat: {fat_pct:4.1f}%, Water: {water_pct:4.1f}%, Muscle: {muscle_pct:4.1f}%")

        return {
            'p_id': p_id,
            'timestamp': f"{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}",
            'weight': weight_kg,
            'fat': fat_pct,
            'water': water_pct,
            'muscle': muscle_pct
        }


    async def publish_latest_measurement(self, mqtt_client, measurement):
        now_cet = localtime_cet.localtime()
        measurement_time = utils.de_time(now_cet)
        print(measurement_time)
        messages = (
            (MEASUREMENT_TOPIC, dumps(measurement)),
            (MEASUREMENT_TIME_TOPIC, measurement_time),
        )
        await utils.publish_messages(mqtt_client, messages, retain=True)


    async def wait_for_scale_to_disappear(self):
        # wait until scale disables its BLE advertising
        print("Waiting for scale to disable BLE advertising...")
        while True:
            found = False
            async with aioble.scan(3000, interval_us=30000, window_us=30000, active=True) as scanner:
                async for result in scanner:
                    if not result.name():
                        continue

                    if result.name() == self.device_name:
                        print(f"Waiting for {self.device_name} to disappear...")
                        found = True
                        break

            if not found:
                print(f"Can't see {self.device_name} anymore! Restarting loop...")
                return
            else:
                await progress.wait_spinner(5, blue_led.toggle, blue_led.set_off)


watchdog = machine.WDT(timeout=3 * 60 * 1000)  # 3 minutes
blue_led = utils.LED(BLUE_LED_PIN)


async def main():
    mqtt_client = umqtt.simple.MQTTClient("smartscaleX", config.MQTT_SERVER_IP, port=config.MQTT_SERVER_PORT, user=config.MQTT_SERVER_USER, password=config.MQTT_SERVER_PASSWORD)
    utils.init(config.WIFI_SSID, config.WIFI_PASSWORD, mqtt_client)

    loop_count = 0
    boot_count = utils.get_boot_count()

    gc.enable()

    progress.hide_cursor()

    print()
    print("*** Micropython Smart Scale Client started ***")
    print()
    print("Getting local time...")

    await utils.wifi_connect()
    utils.get_ntp_time(config.NTP_SERVER)
    mqtt_client.connect()

    await utils.publish_messages([
        (BOOT_COUNT_TOPIC, str(boot_count), True),
        (BOOT_TIME_TOPIC, utils.de_time(localtime_cet.localtime()), True),
    ])

    smart_scale = ScaleClient(SCALE_DEVICE_NAME)
    while True:
        await smart_scale.run()

        print(f"Memory before GC: {gc.mem_alloc() / 1024} KiB")
        mem_after_gc = gc.mem_alloc()
        print(f"Memory after GC: {mem_after_gc / 1024} KiB")

        await utils.publish_messages(mqtt_client, [
            (LOOP_COUNT_TOPIC, str(loop_count), True),
            (GC_MEMORY_TOPIC, str(mem_after_gc), True),
        ])
        loop_count += 1

# asyncio.run(main())
