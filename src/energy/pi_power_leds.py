#!/usr/bin/env python

# pi_power_led.py

# Copyright (c) 2016 Robert Jones, Craic Computing LLC
# Freely distributed under the terms of the MIT License

# Read the contents of /home/pi/.pi_power_status and light red and green leds accordingly

# The default configuration for the LEDs is Common Anode which works for most RGB LEDs

# LED modes
# green blinking    - USB cable attached, charging battery
# green constant    - on battery, >= 0.5 fraction of battery life
# red constant      - on battery, < 0.20 fraction of battery life
# red blinking      - on battery, < 0.15 fraction of battery life
# red blinking fast - on battery, < 0.10 fraction of battery life

# .pi_power file format:
# one line - <battery fraction 0.0-1.0>,<power source - usb or battery>
# for example:
#1.00,usb
#0.50,battery


from time import sleep
from gpiozero import RGBLED

led = RGBLED(red=17,green=27,blue=4)

# check the pi_power file every poll_interval seconds

poll_interval = 60

# Path to the .pi_power status file

pi_power_file_path = '/home/pi/.pi_power_status'

power_source = 'unknown'
power_fraction = 1.0


# Read the .pi_power file at intervals and light the correct LED

while True:
    # read the .pi_power status file
    try:
        with open(pi_power_file_path, "r") as f:

            fields = f.read().rstrip().split(',')

            power_fraction = float(fields[1])
            power_source   = fields[2]
    except IOError:
        # dummy statement to handle python indentation...
        dummy = 1

    if power_source == 'usb':
        led.color=(0, 0, 0.1)

    elif power_source == 'battery':

        # Modify the colors and cutoff levels to suit your needs

        if power_fraction >= 0.25:
            led.color=(0, 0.1, 0)
            # if you have an RGB LED try this instead
            # yellow_constant()

        elif power_fraction >= 0.15:
            led.color = (0.1, 0, 0)

        elif power_fraction >= 0.10:
            led.blink(on_color=(0.1, 0, 0))

        else:
            led.blink(on_time=0.5, off_time=0.5, on_color=(0.1, 0, 0))
    else:
        # Leave LEDs off - just sleep
        pass
    sleep(poll_interval)