#! /usr/bin/python
# pi_power.py

# Robert Jones 2016 jones@craic.com

# The code for reading the MCP3008 analog to digital convertor (readadc) was
# written by Limor "Ladyada" Fried for Adafruit Industries, (c) 2015
# This code is released into the public domain


# Works with an Adafruit PowerBoost 1000C LiPo battery charger

# Writes the fraction of battery remaining as well as the current power source to the file /home/pi/.pi_power

# format:  <float 0.00 - 1.00>,<string [battery|usb]>
# 0.75,battery
# 1.00,usb

import time
import os
import argparse
from gpiozero import MCP3008, Button
import numpy as np

# Calculate the output of a voltage divider
# voltage_divider layout is:
# Vin ---[ R1 ]---[ R2 ]---GND
#               |
#              Vout
#
# Vout = R2 / (R1 + R2) * Vin
# e.g. if R1 = 6800 and R2 = 10000 and Vin is 5.2V then Vout is 3.095
#
def voltage_divider(r1, r2, vin):
    vout = vin * (r2 / (r1 + r2))
    return vout



# Set up a trigger to shutdown the system when the power button is pressed
# define a setup routine and the actual shutdown method

# User has pressed shutdown button - initiate a clean shutdown
def user_shutdown():
    global safe_mode

    shutdown_delay = 5 # seconds

    # in Safe Mode, wait 2 mins before actually shutting down
    if safe_mode:
        cmd = "sudo wall 'System shutting down in 2 minutes - SAFE MODE'"
        os.system(cmd)
        time.sleep(120)

    cmd = f"sudo wall 'System shutting down in {shutdown_delay} seconds'"
    os.system(cmd)
    time.sleep(shutdown_delay)

    # Log message is added to /var/log/messages
    os.system("sudo logger -t 'pi_power' '** User initiated shut down **'")
    os.system("sudo shutdown now")


# Shutdown system because of low battery
def low_battery_shutdown():
    global safe_mode

    shutdown_delay = 30 # seconds

    # in Safe Mode, wait 2 mins before actually shutting down
    if safe_mode:
        cmd = "sudo wall 'System shutting down in 2 minutes - SAFE MODE'"
        os.system(cmd)
        time.sleep(120)

    cmd = f"sudo wall 'System shutting down in {shutdown_delay} seconds'"
    os.system(cmd)
    time.sleep(shutdown_delay)
    # Log message is added to /var/log/messages
    os.system("sudo logger -t 'pi_power' '** Low Battery - shutting down now **'")
    os.system("sudo shutdown now")


class MovingAverageFilter:
    def __init__(self, window_size):
        self.window_size = window_size
        self.measurements = []

    def update(self, new_measurement):
        self.measurements.append(new_measurement)
        if len(self.measurements) > self.window_size:
            self.measurements.pop(0)

    def get_average(self):
        if not self.measurements:
            return 0  # or any default value you prefer
        return sum(self.measurements) / len(self.measurements)

# MAIN -----------------------

# Command Line Arguments
# --log    write time, voltage, etc to a log file
# --debug  write time, voltage, etc to STDOUT

parser = argparse.ArgumentParser(description='Pi Power - Monitor battery status on RasPi projects powered via Adafruit PowerBoost 1000C')

parser.add_argument('-d', '--debug', action='store_true')
parser.add_argument('-l', '--log',   action='store_true')
parser.add_argument('-s', '--safe',  action='store_true')

args = parser.parse_args()

safe_mode = False
if args.safe:
    safe_mode = True


# Setup the GPIO pin to use with the use shutdown button
shutdown_pin = Button(0, pull_up = False)
# shutdown_pin goes high when the switch is in the off position https://github.com/NeonHorizon/lipopi/issues/21
shutdown_pin.when_released = user_shutdown


# Vbat to adc #0, Vusb connected to #1
v_bat_adc_pin = 7
v_usb_adc_pin = 5

# Voltage divider drops the PowerBoost voltage from around 5V to under 3.3V which is the limit for the Pi
voltage_divider_r1 =  6800.0
voltage_divider_r2 = 10000.0

# Define the min and max voltage ranges for the inputs

usb_min_voltage = 0.0
usb_max_voltage = 5.2

gpio_min_voltage = 0.0
gpio_max_voltage = 3.3

# LiPo battery voltage range - actual range is 3.7V to 4.2V
# But in practice the measured range is reduced as Vbat always drops from 4.2 to around 4.05 when the
# USB cable is removed - so this is the effective range:

battery_min_voltage = 3.3
battery_max_voltage = 4.0

# this is the effective max voltage, prior to the divider, that the ADC can register
adc_conversion_factor = (gpio_max_voltage / voltage_divider(voltage_divider_r1, voltage_divider_r2, usb_max_voltage)) * usb_max_voltage


pi_power_status_path = '/home/pi/RPi-Jukebox-RFID/src/energy/.pi_power_status'
pi_power_log_path    = '/home/pi/RPi-Jukebox-RFID/src/energy/pi_power_log.csv'


# initialize an empty log file
if args.log:
    with open(pi_power_log_path, "w") as f:
        f.write('Time,Vbat,Vusb,Frac,Source\n')


# Take a measurement every poll_interval * seconds * - default 60
poll_interval = 60

power_source = ''
power_source_previous = ''

fraction_battery = 1.0

# Define the minimum battery level at which shutdown is triggered

fraction_battery_min = 0.075

# Create a moving average filter with a window size of 5
ma_filter = MovingAverageFilter(window_size=5)


if args.debug:
    print('Time     Vbat    Vusb    Frac    Source')


elapsed_time = 0
msg = ''

time.sleep(10)
while True:
    # read the analog pins on the ACD (range 0-1023) and convert to 0.0-1.0
    frac_v_bat = MCP3008(v_bat_adc_pin).value
    frac_v_usb = MCP3008(v_usb_adc_pin).value

    # Calculate the true voltage
    v_bat = frac_v_bat * adc_conversion_factor
    v_usb = frac_v_usb * adc_conversion_factor

    # moving average
    ma_filter.update(v_bat)
    v_bat = ma_filter.get_average()

    fraction_battery = (v_bat - battery_min_voltage) / (battery_max_voltage - battery_min_voltage)

    if fraction_battery > 1.0:
        fraction_battery = 1.0
    elif fraction_battery < 0.0:
        fraction_battery = 0.0


    # is the USB cable connected ? Vusb is either 0.0 or around 5.2V
    if v_usb > 1.0:
        power_source = 'usb'
    else:
        power_source = 'battery'

    if power_source == 'usb' and power_source_previous == 'battery':
        print('** USB cable connected')
    elif power_source == 'battery' and power_source_previous == 'usb':
        print('** USB cable disconnected')

    power_source_previous = power_source

    msg = ''
    # If battery is too low then shutdown
    if (fraction_battery < fraction_battery_min) and (power_source == 'battery'):
        msg = 'Low Battery - shutdown now'
        if args.debug:
            print("** LOW BATTERY - shutting down........")
            # shutdown after writing to the log file

    if args.debug:
        print(f'{elapsed_time:6d}   {v_bat:.3f}   {v_usb:.3f}   {fraction_battery:.3f}   {power_source:s}   {msg:s}')

    # Open log file, write one line and close
    # This handles the case where the battery is allowed to drain completely and
    # shutdown in which case the file may be corrupted
    if args.log:
        with open(pi_power_log_path, "a") as f:
            f.write(f'{elapsed_time:d},{v_bat:.3f},{v_usb:.3f},{fraction_battery:.3f},{power_source:s},{msg:s}\n')

    # Write the .pi_power status file - used by pi_power_leds.py and jukebox battery monitoring
    with open(pi_power_status_path, "w") as f:
        f.write(f'{int(1000*v_bat)},{fraction_battery:.3f},{power_source:s}\n')

    # Low battery shutdown - specify the time delay in seconds
    if (fraction_battery < fraction_battery_min) and (power_source == 'battery'):
        low_battery_shutdown()

    # sleep poll_interval seconds between updates
    time.sleep(poll_interval)

    elapsed_time += poll_interval
