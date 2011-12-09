# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 xt <xt@bash.no>
# Copyright (C) 2011 quazgaa <quazgaa@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#-------------------------------------------------------------------
#  To make bandwidth monitor visible you need to put "[bandwidth]"
#  (without "") in your weechat.bar.status.items setting
#-------------------------------------------------------------------

#
# History:
#
# 2011-12-02, quazgaa <quazgaa@gmail.com>
#     version 1.0: Complete rewrite.  Make script more featureful, robust, and accurate.
#                  Thanks to FlashCode and ze for helping debug.
# 2011-11-29, quazgaa <quazgaa@gmail.com>
#     version 0.2.1: fixed: take refresh_rate into account for bandwidth calculation
# 2009-10-15, xt <xt@bash.no>:
#     version 0.2: error checking from output command
# 2009-10-14, xt <xt@bash.no>:
#     version 0.1: initial release inspired by nils' perl script
#


# this is a weechat script
try:
    import weechat
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    raise SystemExit, 0

try:
    from time import time
except:
    print "Error importing time module."
    raise SystemExit, 0


# defines
SCRIPT_NAME     = "bandwidth"
SCRIPT_AUTHOR   = "xt <xt@bash.no>"
SCRIPT_VERSION  = "1.0"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Displays network interface bandwidth (KiB/s and MiB/s) on a bar"
SCRIPT_SETTINGS = {
    "device"         : ("eth0",                           "Network interface(s) to monitor, in order, separated by ';'"),
    "refresh_rate"   : ("5",                              "Refresh rate in seconds"),
    "format"         : (("%N(" + unichr(8595) + "%DV%DU/s " + unichr(8593) + "%UV%UU/s)").encode('utf-8'),
                        "Output formatting: %N = network interface, %DV = downstream value, %DU = downstream units (K or M), %UV = upstream value, %UU = upstream units (K or M).  Note: default setting uses UTF-8"),
    "separator"      : (" ",                              "String displayed between output for multiple devices"),
}
STATS_FILE      = "/proc/net/dev"


# global variables
last_device = []
last_down_bytes = []
last_up_bytes = []
last_time = 0


def main():
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        version = int(weechat.info_get('version_number', '')) or 0

        # unset unused setting from older versions of script
        if weechat.config_is_set_plugin('display_unit'):
            weechat.prnt("", "Option plugins.var.python.bandwidth.display_unit no longer used, removing.")
            weechat.config_unset_plugin('display_unit')

        # set default settings
        for option in SCRIPT_SETTINGS.iterkeys():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, SCRIPT_SETTINGS[option][0])
            if version >= 0x00030500:
                weechat.config_set_desc_plugin(option, SCRIPT_SETTINGS[option][1])

        # ensure sane refresh_rate setting
        if int(weechat.config_get_plugin('refresh_rate')) < 1:
            weechat.prnt("", "{}Invalid value for option plugins.var.python.bandwidth.refresh_rate, setting to default of {}".format(weechat.prefix("error"), SCRIPT_SETTINGS['refresh_rate'][0]))
            weechat.config_set_plugin('refresh_rate', SCRIPT_SETTINGS['refresh_rate'][0])

        # create the bandwidth monitor bar item
        weechat.bar_item_new('bandwidth', 'bandwidth_item_cb', '')
        # update it every plugins.var.python.bandwidth.refresh_rate seconds
        weechat.hook_timer(int(weechat.config_get_plugin('refresh_rate'))*1000, 0, 0, 'bandwidth_timer_cb', '')


def bandwidth_timer_cb(data, remaining_calls):
    weechat.bar_item_update('bandwidth')
    return weechat.WEECHAT_RC_OK


def bandwidth_item_cb(data, buffer, args):
    global last_device, last_down_bytes, last_up_bytes, last_time

    device = weechat.config_get_plugin('device').strip(';').split(';')
    output_format = weechat.config_get_plugin('format')
    separator = weechat.config_get_plugin('separator')
    invalid_settings = False

    # ensure sane settings
    if not device[0]:
        weechat.prnt("", "{}Option plugins.var.python.bandwidth.device should contain at least one device name, setting to default of {}".format(weechat.prefix("error"), SCRIPT_SETTINGS['device'][0]))
        weechat.config_set_plugin('device', SCRIPT_SETTINGS['device'][0])
        invalid_settings = True
    if int(weechat.config_get_plugin('refresh_rate')) < 1:
        weechat.prnt("", "{}Invalid value for option plugins.var.python.bandwidth.refresh_rate, setting to default of {}".format(weechat.prefix("error"), SCRIPT_SETTINGS['refresh_rate'][0]))
        weechat.config_set_plugin('refresh_rate', SCRIPT_SETTINGS['refresh_rate'][0])
        invalid_settings = True
    if '%DV' not in output_format and '%UV' not in output_format:
        weechat.prnt("", "{}Option plugins.var.python.bandwidth.format should contain at least one of: '%DV' or '%UV'. Setting to default of '{}'".format(weechat.prefix("error"), SCRIPT_SETTINGS['format'][0]))
        weechat.config_set_plugin('format', SCRIPT_SETTINGS['format'][0])
        invalid_settings = True
    if invalid_settings:
        return ''

    # open the network device status information file
    try:
        f = open(STATS_FILE)
    except:
        weechat.prnt("", "{}Error opening {}".format(weechat.prefix("error"), STATS_FILE))
        return ''
    else:
        current_time = time()
        try:
            foo = f.read()
        except:
            weechat.prnt("", "{}Error reading {}".format(weechat.prefix("error"), STATS_FILE))
            f.close()
            return ''
        f.close()

    current_down_bytes = []
    current_up_bytes = []
    num_devices = len(device)
    num_last_devices = len(last_device)
    lines = foo.splitlines()
    new_device_list = False
    device_exist = False

    # get the downstream and upstream byte counts
    for i in xrange(num_devices):
        for line in lines:
            if (device[i] + ':') in line:
                field = line.split(':')[1].strip().split()
                current_down_bytes.append(float(field[0]))
                current_up_bytes.append(float(field[8]))
                device_exist = True
                break
        if device_exist:
            device_exist = False
        else:
            current_down_bytes.append(0)
            current_up_bytes.append(0)

    # check if the set of network devices to monitor has changed while script is running,
    if last_device:
        if num_last_devices != num_devices:
            new_device_list = True
        else:
            for i in xrange(num_devices):
                if device[i] != last_device[i]:
                    new_device_list = True
                    break

    # if so, clear the global variables,
    if new_device_list:
        del last_device[:]
        del last_down_bytes[:]
        del last_up_bytes[:]

    # set them afresh (also if script first starting),
    if not last_device:
        if num_devices:
            for i in xrange(num_devices):
                last_device.append(device[i])
                last_down_bytes.append(current_down_bytes[i])
                last_up_bytes.append(current_up_bytes[i])
            last_time = current_time
        # and start from the beginning
        return ''

    # calculate downstream and upstream rates in KiB/s
    if num_devices:
        down_rate = []
        up_rate = []
        time_elapsed = current_time - last_time
        last_time = current_time

        for i in xrange(num_devices):
            down_rate.append((current_down_bytes[i] - last_down_bytes[i]) / time_elapsed / 1024)
            up_rate.append((current_up_bytes[i] - last_up_bytes[i]) / time_elapsed / 1024)
            last_down_bytes[i] = current_down_bytes[i]
            last_up_bytes[i] = current_up_bytes[i]

        output_item = [output_format for i in device]

    output = ''

    # determine downstream and upstream units; format the output
    for i in xrange(num_devices):
        if '%DU' in output_item[i]:
            if down_rate[i] >= 1024:
                down_rate[i] = round((down_rate[i]/1024), 1)
                down_rate_unit = 'M'
            else:
                down_rate[i] = int(round(down_rate[i]))
                down_rate_unit = 'K'
            output_item[i] = output_item[i].replace('%DU', down_rate_unit)

        if '%UU' in output_item[i]:
            if up_rate[i] >= 1024:
                up_rate[i] = round((up_rate[i]/1024), 1)
                up_rate_unit = 'M'
            else:
                up_rate[i] = int(round(up_rate[i]))
                up_rate_unit = 'K'
            output_item[i] = output_item[i].replace('%UU', up_rate_unit)

        output_item[i] = output_item[i].replace('%DV', str(down_rate[i]))
        output_item[i] = output_item[i].replace('%UV', str(up_rate[i]))
        output_item[i] = output_item[i].replace('%N', device[i])

        if output:
            output += separator + output_item[i]
        else:
            output = output_item[i]

    # return the result
    return output

if __name__ == "__main__":
    main()
