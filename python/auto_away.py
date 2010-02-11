# auto_away.py : A simple auto-away script for Weechat in Python 
# Copyright (c) 2010 by Specimen <spinifer at gmail dot com>
#
# Inspired in yaaa.pl by jnbek
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
#
# Configuration options:
#
# 'idletime'
#   description: Period in minutes (n) of keyboard inactivity until 
#                being marked as being away
#   command: /set plugins.var.python.auto_away.idletime "n"
# 
# 'message'
#   description: Away message
#   command: /set plugins.var.python.auto_away.message "message"
#   
# 'hookinterval'
#   description: Frequency of hook_timer checks (n), default is 10, change
#                to 5 if you feel it doesn't update fast enough.
#   command: /set plugins.var.python.auto_away.hookinterval "n"
#
#
# Changelog:
#
#   2010-02-11 - 0.1    - Script created
#   2010-02-11 - 0.1.1  - '<' instead of '<='

import weechat

# Default Values
idletime = "20"
message = "Idle"
hookinterval = "10"

# Script registration
weechat.register("auto_away", "Specimen", "0.1.1", "GPL3", 
                    "Simple auto-away script in Python", "", "")

# Register configuration
if not weechat.config_get_plugin('status'): 
    weechat.config_set_plugin('status', "notaway")
	
if not weechat.config_get_plugin('idletime'): 
    weechat.config_set_plugin('idletime', idletime)
	
if not weechat.config_get_plugin('message'): 
    weechat.config_set_plugin('message', message)

if not weechat.config_get_plugin('hookinterval'): 
    weechat.config_set_plugin('hookinterval', hookinterval)

# Weechat hook
weechat.hook_timer(int(weechat.config_get_plugin('hookinterval')) * 1000, 
                    60, 0, "idle_chk", "")

# Inactivity check routine
def idle_chk (data, remaining_calls):
	
    if int(weechat.info_get("inactivity", "")) >= \
        int(weechat.config_get_plugin('idletime')) * 60:
        if weechat.config_get_plugin('status') != "away":
            weechat.config_set_plugin('status', "away")
            weechat.command("", "/away -all %s" 
                            % weechat.config_get_plugin('message'))
		
    elif int(weechat.info_get("inactivity", "")) < \
        int(weechat.config_get_plugin('idletime')) * 60:
        if weechat.config_get_plugin('status') == "away":
            weechat.config_set_plugin('status', "notaway")
            weechat.command("", "/away -all")

    return weechat.WEECHAT_RC_OK
