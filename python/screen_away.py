# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
# Copyright (c) 2009 by penryu <penryu@gmail.com>
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
# History:
# 2009-11-27, xt <xt@bash.no>
#  version 0.2: code for TMUX from penryu
# 2009-11-27, xt <xt@bash.no>
#  version 0.1: initial release

import weechat as w
import re
import os

SCRIPT_NAME    = "screen_away"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set away status on screen detach"

settings = {
        'message': 'Detached from screen',
        'interval': '60' # How often in seconds to check screen status
}

IS_AWAY = False

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    w.hook_timer(\
            int(w.config_get_plugin('interval')) * 1000,
            0,
            0,
            "screen_away_timer_cb",
            '')

def get_socket():
    ''' Function that checks if we are running under tmux
    or screen and return socket '''

    socket = False

    if 'STY' in os.environ.keys():
        # We are running under screen

        cmd_output = os.popen('LC_ALL=C screen -ls').read()
        socket_path = re.findall('Sockets? in (?P<socket_path>.+)\.', cmd_output)[0]
        socket_file = os.environ['STY']
        socket = os.path.join(socket_path, socket_file)

    if 'TMUX' in os.environ.keys():
        # We are running under tmux
        
        socket_data = os.environ['TMUX']
        socket = socket_data.rsplit(',',2)[0]

    return socket

def screen_away_timer_cb(buffer, args):

    global IS_AWAY

    socket = get_socket()
    if not socket:
        # We got no socket. No screen or tmux detected
        return w.WEECHAT_RC_OK

    if os.access(socket, os.X_OK):
        # Screen is attached
        if IS_AWAY:
            # Only remove away status if it was set by this script
            w.command('', "/away -all")
            w.prnt('', '%s: Detected screen attach. Clearing away status' %SCRIPT_NAME)
            IS_AWAY = False
    else:
        # if it has X bit set screen is attached 
        if not IS_AWAY: # Do not set away if we are already set away
            w.command('', "/away -all %s" %w.config_get_plugin('message') );
            w.prnt('', '%s: Detected screen detach. Setting away status' %SCRIPT_NAME)
            IS_AWAY = True

    return w.WEECHAT_RC_OK
