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
# 2016-05-01, Ferus
#     version 0.8, Add ability to prefix and suffix the title, current
#     buffer, and hotlist buffers. As well as specify hotlist separator
# 2016-02-05, ixti
#     version 0.7, Add Python3 support
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
SCRIPT_VERSION = "0.8"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set screen title to current buffer name + hotlist items with configurable priority level"

# script options
settings = {
    "title_priority"       : '2',
    "short_name"           : 'on',
    "hotlist_separator"    : ':',
    "title_prefix"         : '[WeeChat ${info:version}] ',
    "title_suffix"         : '',
    "hotlist_number_prefix": '',
    "hotlist_number_suffix": '',
    "hotlist_buffer_prefix": '',
    "hotlist_buffer_suffix": '',
    "current_buffer_prefix": '',
    "current_buffer_suffix": '',
}

hooks = (
        'buffer_switch',
        'window_switch',
        'hotlist_*',
)


def update_title(data, signal, signal_data):
    ''' The callback that adds title. '''

    # prefix
    title = w.config_get_plugin('title_prefix')

    # current buffer
    title += w.config_get_plugin('current_buffer_prefix')
    if w.config_get_plugin('short_name') == 'on':
        title += w.buffer_get_string(w.current_buffer(), 'short_name')
    else:
        title += w.buffer_get_string(w.current_buffer(), 'name')
    title += w.config_get_plugin('current_buffer_suffix')

    # hotlist buffers
    hotlist = w.infolist_get('hotlist', '', '')
    pnumber = w.config_get_plugin('hotlist_number_prefix')
    snumber = w.config_get_plugin('hotlist_number_suffix')
    pname = w.config_get_plugin('hotlist_buffer_prefix')
    sname = w.config_get_plugin('hotlist_buffer_suffix')
    separator = w.config_get_plugin('hotlist_separator')
    while w.infolist_next(hotlist):
        priority = w.infolist_integer(hotlist, 'priority')
        if priority >= int(w.config_get_plugin('title_priority')):
            number = w.infolist_integer(hotlist, 'buffer_number')
            thebuffer = w.infolist_pointer(hotlist, 'buffer_pointer')
            name = w.buffer_get_string(thebuffer, 'short_name')
            title += ' {0}{1}{2}{3}{4}{5}{6}'.format(pnumber, \
                number, snumber, separator, pname, name, sname)
    w.infolist_free(hotlist)

    # suffix
    title += w.config_get_plugin('title_suffix')

    title = w.string_remove_color(title, '')
    w.window_set_title(title)

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    for hook in hooks:
        w.hook_signal(hook, 'update_title', '')

    update_title('', '', '')
