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
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-23, xt
#     version 0.2: use better check if buffer has nicklist
# 2009-06-22, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w

SCRIPT_NAME    = "nicklist_autoshow"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto show and hide nicklist depending on channel name"

settings = {
    "display_channels"              : '', # Comma separated
    "hide_channels"                 : '', # Comma separated
}

def check_nicklist_cb(data, signal, signal_data):
    ''' The callback that checks if nicklist should be displayed '''

    current_buffer = w.current_buffer()

    # Check if current buffer has a nicklist
    infolist = w.infolist_get('nicklist', current_buffer, '')
    counter = 0
    while w.infolist_next(infolist):
        counter += 1
    w.infolist_free(infolist)

    if counter == 1: # Means the buffer does not have an nicklist
        return w.WEECHAT_RC_OK


    current_buffer_name = w.buffer_get_string(current_buffer, 'name')
    display_channels = w.config_get_plugin('display_channels')
    hide_channels = w.config_get_plugin('hide_channels')

    if display_channels:
        for buffer_name in display_channels.split(','):
            if unicode(current_buffer_name) == unicode(buffer_name):
                w.command(current_buffer, '/buffer set nicklist 1')
                break
        else:
            w.command(current_buffer, '/buffer set nicklist 0')
    else:
        if hide_channels:
            for buffer_name in hide_channels.split(','):
                if unicode(current_buffer_name) == unicode(buffer_name):
                    w.command(current_buffer, '/buffer set nicklist 0')
                    break
            else:
                w.command(current_buffer, '/buffer set nicklist 1')

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_signal('buffer_switch', 'check_nicklist_cb', '')

