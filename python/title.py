''' Title-setter '''
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
# Set screen title
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2015-06-07, t3chguy
#     version 0.6, Strip Colour Codes from Title
# 2012-12-09, WakiMiko
#     version 0.5, update title when switching window (for WeeChat >= 0.3.7)
# 2009-06-18, xt
#     version 0.4, option to use short_name
# 2009-06-15, xt
#     version 0.3, free infolist
# 2009-05-15, xt
#     version 0.2: add names from hotlist to title
# 2009-05-10, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w

SCRIPT_NAME    = "title"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.6"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set screen title to current buffer name + hotlist items with configurable priority level"

# script options
settings = {
    "title_priority"       : '2',
    "short_name"           : 'on',
}

hooks = (
        'buffer_switch',
        'window_switch',
        'hotlist_*',
)


def update_title(data, signal, signal_data):
    ''' The callback that adds title. '''

    if w.config_get_plugin('short_name') == 'on':
        title = w.buffer_get_string(w.current_buffer(), 'short_name')
    else:
        title = w.buffer_get_string(w.current_buffer(), 'name')

    title = w.string_remove_color(title, '')
    hotlist = w.infolist_get('hotlist', '', '')
    while w.infolist_next(hotlist):
        priority = w.infolist_integer(hotlist, 'priority')
        if priority >= int(w.config_get_plugin('title_priority')):
            number = w.infolist_integer(hotlist, 'buffer_number')
            thebuffer = w.infolist_pointer(hotlist, 'buffer_pointer')
            name = w.buffer_get_string(thebuffer, 'short_name')

            title += ' %s:%s' % (number, name)
    w.infolist_free(hotlist)

    w.window_set_title(title)

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    for hook in hooks:
        w.hook_signal(hook, 'update_title', '')

    update_title('', '', '')
