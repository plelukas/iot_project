#!/usr/bin/env python

# ----- BEGIN INITIALIZATION -----
from __future__ import print_function

import os
import thread
from copernicus import Copernicus
from serial import Serial

from paho.mqtt import publish
import psutil

import urllib2
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SERIAL_PATH = os.path.join(BASE_DIR, 'dev', 'ttyS0')

serial = Serial(SERIAL_PATH, 38400)


# ----- END INITIALIZATION -----

shared = {
    'field': 'cpu', # possible: ram, cpu
    'cpu': 0.0,
    'ram': 0.0
}

channelID = "262303"
writeApiKey = "KTEHFDWRQG324W7L"
readApiKey = "7ECPT0P7EYV0KE6M"

# measure CPU and RAM usage and send to MQTT broker on ThingSpeak
def measure_cpu_ram_and_send():
    # ThingSpeak configuration
    mqttHost = "mqtt.thingspeak.com"

    tTransport = "tcp"
    tPort = 1883  # default MQTT port
    tTLS = None

    topic = "channels/" + channelID + "/publish/" + writeApiKey

    # every 10 seconds measure CPU and RAM usage
    while True:

        cpuPercent = psutil.cpu_percent(interval=30)
        ramPercent = psutil.virtual_memory().percent

        print("MEASURED CPU = " + str(cpuPercent) + "\t RAM = " + str(ramPercent))

        tPayload = "field1=" + str(cpuPercent) + "&field2=" + str(ramPercent)

        # publish data to ThingSpeak
        try:
            publish.single(topic, payload=tPayload, hostname=mqttHost, port=tPort,
                           tls=tTLS, transport=tTransport)

        except KeyboardInterrupt:
            break

        except Exception:
            print("Error: Sending data to ThingSpeak.com failed.")

thread.start_new_thread(measure_cpu_ram_and_send, ())


# get data from ThingSpeak's REST API
def get_data():
    try:
        response = urllib2.urlopen('https://api.thingspeak.com/channels/{}/feeds/last.json?api_key={}'
                                   .format(channelID, readApiKey)).read()
    except:
        print("Error: Failed getting data from ThingSpeak.com")
        return

    json_response = json.loads(response)

    shared['cpu'] = float(json_response['field1'])
    shared['ram'] = float(json_response['field2'])

    print("GET: CPU = " + str(shared['cpu']) + "\t RAM = " + str(shared['ram']))


# Servo will display last data (RAM or CPU)
# Button 1 will change between displaying RAM/CPU
# Button 2 will read data
# LED: red - CPU, green - RAM

api = Copernicus(connection=serial)

def button1_handler(state):
    if state:
        # pressed
        color = 'off'
        if shared['field'] == 'cpu':
            shared['field'] = 'ram'
            color = 'green'
        elif shared['field'] == 'ram':
            shared['field'] = 'cpu'
            color = 'red'

        api.command('rgb', color)
        api.command('servo', int(shared[shared['field']] * 31 / 100))

def button2_handler(state):
    if state:
        # pressed
        get_data()
        api.command('servo', int(shared[shared['field']] * 31 / 100))


api.set_handler('button1', button1_handler)
api.set_handler('button2', button2_handler)
api.command('subscribe', 'button1', 'button2')

while True:
    api.listen()

