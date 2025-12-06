import machine
import ntptime
import network

import asyncio
import time

import localtime_cet
import ansi_colors as c

wlan = network.WLAN()


wifi_ssid = None
wifi_password = None
mqtt_client_global = None


def init(ssid, password, mqtt_client=None):
    global wifi_ssid, wifi_password
    wifi_ssid = ssid
    wifi_password = password
    if mqtt_client is not None:
        global mqtt_client_global
        mqtt_client_global = mqtt_client


class Uptime:
    def __init__(self):
        self.uptime_ms = 0
        self.start_tick = time.ticks_ms()
        self.last_tick = self.start_tick

    def __call__(self):
        self.last_tick = self.start_tick
        self.start_tick = time.ticks_ms()
        self.uptime_ms += time.ticks_diff(self.start_tick, self.last_tick)
        return self.uptime_ms


class LED:
    def __init__(self, pin):
        self._freq = 5000
        self._off_duty = 1023
        self._on_duty = 800
        self._led = machine.PWM(machine.Pin(pin), freq=self._freq, duty=self._off_duty)
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
    wlan.active(True)
    print(c.color("WIFI active", c.SUCCESS))

    if not wlan.isconnected():
        print("Connecting to network...")
        wlan.connect(wifi_ssid, wifi_password)
        while not wlan.isconnected():
            await asyncio.sleep(1)
            print(".", end="")

        print()

    print(c.color("WIFI connected:", c.SUCCESS), wlan.ipconfig('addr4'))


def wifi_disconnect():
    global wlan
    wlan.active(False)
    print(c.color("WIFI disconnected", c.ERROR))


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
            await wifi_connect(wifi_ssid, wifi_password)
            mqtt_client.connect()


def get_ntp_time(ntp_server):
    try:
        ntptime.host = ntp_server
        ntptime.settime()
        print(f"Formatted time: {de_time(localtime_cet.localtime())}")
    except:
        print(c.color("Failed to synchronize NTP time", c.ERROR))


def get_boot_count():
    try:
        with open("boot_count.txt", "r") as f:
            count = int(f.read().strip())
    except:
        count = 0

    count += 1

    with open("boot_count.txt", "w") as f:
        f.write(str(count))

    return count


def reset_boot_count():
    with open("boot_count.txt", "w") as f:
        f.write("0")
