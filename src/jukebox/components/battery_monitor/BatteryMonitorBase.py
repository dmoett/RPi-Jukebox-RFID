# MIT License
#
# Copyright (c) 2021 Arne Pagel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Contributing author(s):
# - Arne Pagel

import jukebox.plugs as plugs
import jukebox.cfghandler
import jukebox.publishing
import jukebox.multitimer as multitimer

batt_mon = None


class BattmonBase():
    '''Battery Monitor base class '''

    def __init__(self, cfg, logger):
        self._logger = logger
        self.batt_status = {}
        self.batt_status['soc'] = 0
        self.batt_status['charging'] = 0
        self.batt_status['voltage'] = 0
        self.interval = 5
        self.last_sample_time = -5
        # batt_voltage_mV = self.get_batt_voltage()[0]
        # charging = self.get_batt_voltage()[1]
        # soc = self.get_batt_voltage()[2]

        self.warning_action = cfg.setndefault('battmon', 'warning_action', value=None)
        self.all_clear_action = cfg.setndefault('battmon', 'all_clear_action', value=None)

        self.status_thread = multitimer.GenericEndlessTimerClass('batt_mon.timer_status', self.interval, self.publish_status)
        self.status_thread.start()

    def get_batt_voltage(self):
        self._logger.error("get_batt_voltage shall be overwritten")

    @plugs.tag
    def get_batt_status(self):
        return (self.batt_status)

    def publish_status(self):
        batt_voltage_mV = self.get_batt_voltage()[0]
        charging = self.get_batt_voltage()[1]
        soc = self.get_batt_voltage()[2]

        self._logger.info(f"SOC: {soc}%, Batt Voltage: {batt_voltage_mV}mV, charging:{charging}")

        self.batt_status['soc'] = soc
        self.batt_status['charging'] = charging
        self.batt_status['voltage'] = batt_voltage_mV

        jukebox.publishing.get_publisher().send('batt_status', self.batt_status)
