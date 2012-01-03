# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 xt <xt@bash.no>
# Copyright (C) 2009-2012 Sebastien Helleu <flashcode@flashtux.org>
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
#
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: make script compatible with Python 3.x,
#                  use string_match of WeeChat API
# 2010-06-03, Nils Görs <weechatter@arcor.de>:
#     version 0.6: option "toggle" added
# 2010-02-03, Alex Barrett <al.barrett@gmail.com>:
#     version 0.5: support wildcards in buffers list
# 2009-06-23, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: use modifier to show/hide nicklist on a buffer
# 2009-06-23, xt <xt@bash.no>:
#     version 0.3: use hiding/showing instead of disabling nicklist
# 2009-06-23, xt <xt@bash.no>:
#     version 0.2: use better check if buffer has nicklist
# 2009-06-22, xt <xt@bash.no>:
#     version 0.1: initial release

import weechat as w

SCRIPT_NAME    = "toggle_nicklist"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.7"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto show and hide nicklist depending on buffer name"

SCRIPT_COMMAND = "toggle_nicklist"

settings = {
    'action'  : 'hide', # show or hide nicklist in buffers list (next option)
    'buffers' : '',     # comma separated list
}

def display_action():
    w.prnt('', '%s: action = "%s"' % (SCRIPT_NAME, w.config_get_plugin("action")))

def display_buffers():
    w.prnt('', '%s: buffers = "%s"' % (SCRIPT_NAME, w.config_get_plugin("buffers")))

def get_buffers_list():
    buffers = w.config_get_plugin('buffers')
    if buffers == '':
        return []
    else:
        return buffers.split(',')

def nicklist_cmd_cb(data, buffer, args):
    ''' Command /nicklist '''
    if args == '':
        display_action()
        display_buffers()
    else:
        current_buffer_name = w.buffer_get_string(buffer, 'plugin') + '.' + w.buffer_get_string(buffer, 'name')
        if args == 'toggle':
            toggle = w.config_get_plugin('action')
            if toggle == 'show':
                w.config_set_plugin('action', 'hide')
                w.command('', '/window refresh')
            elif toggle == 'hide':
                w.config_set_plugin('action', 'show')
                w.command('', '/window refresh')
        if args == 'show':
            w.config_set_plugin('action', 'show')
            #display_action()
            w.command('', '/window refresh')
        elif args == 'hide':
            w.config_set_plugin('action', 'hide')
            #display_action()
            w.command('', '/window refresh')
        elif args == 'add':
            list = get_buffers_list()
            if current_buffer_name not in list:
                list.append(current_buffer_name)
                w.config_set_plugin('buffers', ','.join(list))
                #display_buffers()
                w.command('', '/window refresh')
            else:
                w.prnt('', '%s: buffer "%s" is already in list' % (SCRIPT_NAME, current_buffer_name))
        elif args == 'remove':
            list = get_buffers_list()
            if current_buffer_name in list:
                list.remove(current_buffer_name)
                w.config_set_plugin('buffers', ','.join(list))
                #display_buffers()
                w.command('', '/window refresh')
            else:
                w.prnt('', '%s: buffer "%s" is not in list' % (SCRIPT_NAME, current_buffer_name))

    return w.WEECHAT_RC_OK

def check_nicklist_cb(data, modifier, modifier_data, string):
    ''' The callback that checks if nicklist should be displayed '''

    buffer = w.window_get_pointer(modifier_data, "buffer")
    if buffer:
        buffer_name = w.buffer_get_string(buffer, 'plugin') + '.' + w.buffer_get_string(buffer, 'name')
        buffers_list = w.config_get_plugin('buffers')
        if w.config_get_plugin('action') == 'show':
            for buffer_mask in buffers_list.split(','):
                if w.string_match(buffer_name, buffer_mask, 1):
                    return "1"
            return "0"
        else:
            for buffer_mask in buffers_list.split(','):
                if w.string_match(buffer_name, buffer_mask, 1):
                    return "0"
            return "1"
    return "1"

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_command(SCRIPT_COMMAND,
                   "Show or hide nicklist on some buffers",
                   "[show|hide|toggle|add|remove]",
                   "  show: show nicklist for buffers in list (hide nicklist for other buffers by default)\n"
                   "  hide: hide nicklist for buffers in list (show nicklist for other buffers by default)\n"
                   "toggle: show/hide nicklist for buffers in list\n"
                   "   add: add current buffer to list\n"
                   "remove: remove current buffer from list\n\n"
                   "Instead of using add/remove, you can set buffers list with: "
                   "/set plugins.var.python.%s.buffers \"xxx\". Buffers set in this "
                   "manner can start or end with * as wildcards to match multiple buffers."
                   % SCRIPT_NAME,
                   "show|hide|toggle|add|remove",
                   "nicklist_cmd_cb", "")
    w.hook_modifier('bar_condition_nicklist', 'check_nicklist_cb', '')
