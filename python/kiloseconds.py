# -*- coding: utf-8 -*-
# Copyright (c) 2009 by Wraithan <XWraithanX@gmail.com>
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-06-18, Wraithan <XWraithanX@gmail.com>
#   version 0.1: initial release.
#
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
''' Kilosecond display. 

Usage: /ks to display the current time in kiloseconds,
Also makes availbe [kiloseconds] for your status bar. 
" weechat.bar.status.items".
'''

import weechat
import time

SCRIPT_NAME    = "kiloseconds"
SCRIPT_AUTHOR  = "Wraithan <XWraithanX@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Script to display the current time in kiloseconds in various ways."

SCRIPT_COMMAND = "ks"

def getKiloseconds():
    """Get current time in kiloseconds"""
    tm = time.localtime()
    return (tm.tm_hour*3600+tm.tm_min*60+tm.tm_sec)/1000.0 
    

def kiloseconds_cmd(data, buffer, args):
    """Callback for /ks command"""
    weechat.command(buffer,"The current time is " + str(getKiloseconds()) + " KS")
    return weechat.WEECHAT_RC_OK

def kiloseconds_cb(data, buffer, args):
    """Callback for the bar item"""
    return "%06.3f" % getKiloseconds()

def kiloseconds_update(data,cals):
    """Update the bar item"""
    weechat.bar_item_update('kiloseconds')
    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, '', ''):

    weechat.hook_command(SCRIPT_COMMAND,
                         "Display current time in kiloseconds",
                         "",
                         "Add 'kiloseconds' to any bar to have it show the time in kiloseconds.",
                         "",
                         "kiloseconds_cmd", "")

    weechat.bar_item_new('kiloseconds', 'kiloseconds_cb', '')
    weechat.hook_timer(1000,1,0,'kiloseconds_update','')

