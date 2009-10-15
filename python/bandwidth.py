# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
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
#
#
#
# to make bandwidth visible you have to add ",[bandwidth]" (without "")
# in your weechat.bar.status.items

#
# History:
#
# 2009-10-15, xt <xt@bash.no>:
#     version 0.2: error checking from output command
# 2009-10-14, xt <xt@bash.no>:
#     version 0.1: initial release inspired by nils' perl script
#

SCRIPT_NAME    = "bandwidth"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Displays network interface bandwidth on a bar"

import os
import_ok = True

try:
    import weechat
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

# script options
bandwidth_settings = {
    "device"                : "eth0",       # Network interface
    "refresh_rate"          : "5",          # in s
    "display_unit"          : "on",         # on/off
}

last_i = 0
last_o = 0

def bandwidth_timer_cb(data, remaining_calls):
    weechat.bar_item_update('bandwidth')
    
    return weechat.WEECHAT_RC_OK


def bandwidth_item_cb(data, buffer, args):
    """ Callback for building hlpv item. """

    global last_i, last_o
    
    device = weechat.config_get_plugin('device')
    pipe = os.popen(''' awk -v interface="%s"     'BEGIN { gsub(/\./, "\\\\.", interface) } \\
                $1 ~ "^" interface ":" {
                    split($0, a, /: */); $0 = a[2]; \
                    print "" $1 "\\n" $9 \
                }'     /proc/net/dev''' %device)
    pipeoutput = pipe.read()
    if not pipeoutput:
        # Problem with reading
        return ''
    if not len(pipeoutput.split()) == 2:
        # Problem with reading
        return ''

    cur_i, cur_o = pipeoutput.split()
    pipe.close()

    cur_i = float(cur_i)
    cur_o = float(cur_o)

    i = (cur_i - last_i)/1024 # KiB
    o = (cur_o - last_o)/1024 # KiB

    if last_i == cur_i:
        return ''

    last_i = cur_i
    last_o = cur_o

    if not last_i or not last_o:
        return ''

    i_unit = ''
    o_unit = ''
    if weechat.config_get_plugin('display_unit') == 'on':
        i_unit = 'KiB/s'
        o_unit = 'KiB/s'
        if i > 1023:
            i = i/1024
            i_unit = 'MiB/s'
        if o > 1023:
            o = o/1024
            o_unit = 'MiB/s'

    return "i: %(in)d %(i_unit)s, o: %(out)d %(o_unit)s" %{
            'in': i,
            'out': o,
            'i_unit': i_unit,
            'o_unit': o_unit,
            }

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "", ""):
        # set default settings
        for option, default_value in bandwidth_settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        # new item
        weechat.bar_item_new('bandwidth', 'bandwidth_item_cb', '')
        weechat.hook_timer(int(weechat.config_get_plugin("refresh_rate")) * 1000, 0, 0, "bandwidth_timer_cb", "")
