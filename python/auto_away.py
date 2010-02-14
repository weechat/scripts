# auto_away.py : A simple auto-away script for Weechat in Python 
# Copyright (c) 2010 by Specimen <spinifer at gmail dot com>
#
# Inspired in yaaa.pl by jnbek
# A very special thanks to Nils G. for helping me out with this script
# ---------------------------------------------------------------------
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
# This script requires WeeChat 0.3.0 or newer.
# 
# ---------------------------------------------------------------------
#
# Summary:
#
#   Sets status to away automatically after a given period of 
#   inactivity. Returns from away when you start typing, but not when
#   you change buffer or scroll. 
#
#
# Configuration options:
#
# 'idletime'
#   description: Period in minutes (n) of keyboard inactivity until 
#                being marked as being away.
#                Setting idletime to "0" disables auto-away.
#   command: /set plugins.var.python.auto_away.idletime "n"
# 
# 'message'
#   description: Away message.
#   command: /set plugins.var.python.auto_away.message "message"
#   
# 'hookinterval'
#   description: Frequency of hook_timer checks (n), default is 10,
#                change to 5 if you feel it doesn't update fast enough.
#   command: /set plugins.var.python.auto_away.hookinterval "n"
#
#
# Changelog:
#
#   2010-02-11 - 0.1    - Script created.
#   2010-02-11 - 0.1.1  - Various fixes with the help of Flashcode
#   2010-02-13 - 0.2    - Option to disable autoaway, return from away
#                         via hook_signal as suggested by Nils G.
#                         No longer uses plugin configuration to store
#                         away status.

import weechat

# Default Settings
idletime = "20"
message = "Idle"
hookinterval = "10"

# Script Variables
input_hook = ""
away_status = ""

# Script registration
weechat.register("auto_away", "Specimen", "0.2", "GPL3", 
                 "Simple auto-away script in Python", "", "")

# Register configuration	
if not weechat.config_get_plugin('idletime'): 
    weechat.config_set_plugin('idletime', idletime)
	
if not weechat.config_get_plugin('message'): 
    weechat.config_set_plugin('message', message)

if not weechat.config_get_plugin('hookinterval'): 
    weechat.config_set_plugin('hookinterval', hookinterval)

# Weechat time hook
weechat.hook_timer(int(weechat.config_get_plugin('hookinterval')) * 
                   1000, 60, 0, "idle_chk", "")

# Inactivity check routine
def idle_chk(data, remaining_calls):
	
    global away_status, input_hook
    
    if int(weechat.config_get_plugin('idletime')) != 0:
        if away_status != "away":
            if int(weechat.info_get("inactivity", "")) >= \
                int(weechat.config_get_plugin('idletime')) * 60:
                weechat.command("", "/away -all %s" 
                                % weechat.config_get_plugin('message'))
                away_status = "away"
                input_hook = weechat.hook_signal("input_text_changed",
                                                 "typing_chk", "")

    return weechat.WEECHAT_RC_OK

# Return from away routine
def typing_chk(data, signal, signal_data):

    global away_status, input_hook

    if int(weechat.config_get_plugin('idletime')) != 0:
        if away_status == "away":
            weechat.unhook(input_hook)
            away_status = "notaway"
            weechat.command("", "/away -all")

    return weechat.WEECHAT_RC_OK
