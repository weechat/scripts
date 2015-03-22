# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 by mccloud <cloudyster@gmail.com>
# Based on 'uppercase.py' by xt <xt@bash.no>
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
# (this script requires WeeChat 0.3.0 or newer)
#

import weechat as w
import re
weechat = w

SCRIPT_NAME    = "ws_replace"
SCRIPT_AUTHOR  = "mccloud"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Remove leading and trailing whitespace before sending"

# script options
settings = {
}



if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if w.config_get_plugin(option) == "":
            w.config_set_plugin(option, default_value)

    # Hooks we want to hook
    hook_command_run = {
        "input" : ("/input return",  "command_run_input"),
    }
    # Hook all hooks !
    for hook, value in hook_command_run.iteritems():
        w.hook_command_run(value[0], value[1], "")


def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    if command == "/input return": # As in enter was pressed.

        # Get input contents
        input_s = w.buffer_get_string(buffer, 'input')
        if input_s.startswith('/') and not input_s.startswith('//') and not input_s.startswith('/me'):
            return w.WEECHAT_RC_OK
        # Transform it
        input_s = input_s.strip()
        # Spit it out
        w.buffer_set(buffer, 'input', input_s)
    return w.WEECHAT_RC_OK
