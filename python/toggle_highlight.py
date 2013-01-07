# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Adam Spiers <weechat@adamspiers.org>
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
# (this script probably requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2013-01-07 Adam Spiers <weechat@adamspiers.org>
#     version 0.2: bugfixes
# 2013-01-06 Adam Spiers <weechat@adamspiers.org>
#     version 0.1: initial release

# http://www.weechat.org/files/doc/stable/weechat_scripting.en.html

import weechat as w

SCRIPT_NAME    = "toggle_highlight"
SCRIPT_AUTHOR  = "Adam Spiers <weechat@adamspiers.org>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Toggles notifications of normal messages for the current buffer"

SCRIPT_COMMAND = "highlight"

SILENCE_DESCR  = "notifications for normal messages silenced"
NOTIFY_DESCR   = "notifications for normal messages enabled"

settings = {
}

def show_message(buf, msg):
    w.prnt(buf, '[%s] %s' % (SCRIPT_COMMAND, msg))

def get_setting_name(buf):
    bufchan = w.buffer_get_string(buf, 'localvar_channel')
    bufserv = w.buffer_get_string(buf, 'localvar_server')
    return "weechat.notify.irc.%s.%s" % (bufserv, bufchan)

def is_current_buffer_highlight_set(buf):
    return w.config_string(w.config_get(get_setting_name(buf))) == 'highlight'

def display_current(buf):
    if not ensure_channel_buffer(buf):
        return

    if is_current_buffer_highlight_set(buf):
        show_message(buf, SILENCE_DESCR)
    else:
        show_message(buf, NOTIFY_DESCR)

def get_buffers_list():
    buffers = w.config_get_plugin('buffers')
    if buffers == '':
        return []
    else:
        return buffers.split(',')

def ensure_channel_buffer(buf):
    buftype = w.buffer_get_string(buf, 'localvar_type')

    if buftype != 'channel':
        show_message(
            buf,
            "current buffer type is %s not a channel!\n"
            "run this in a channel buffer." % buftype)
        return False

    return True

def set_highlight(buf, unset=False):
    if not ensure_channel_buffer(buf):
        return

    if unset:
        command = "/unset %s" % get_setting_name(buf)
        message = NOTIFY_DESCR
    else:
        command = "/set %s highlight" % get_setting_name(buf)
        message = SILENCE_DESCR

    w.command('', command)
    show_message(buf, message)

def set_highlight_cmd_cb(data, buf, args):
    ''' Command /highlight '''
    if args == '':
        display_current(buf)
    else:
        if args == 'toggle':
            if is_current_buffer_highlight_set(buf):
                set_highlight(buf, unset=True)
            else:
                set_highlight(buf)
        elif args == 'unset':
            set_highlight(buf, unset=True)
        elif args == 'set':
            set_highlight(buf)
        else:
            show_message(buf,
                         "Invalid arguments %s to /%s" %
                         (args, SCRIPT_COMMAND))

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_command(SCRIPT_COMMAND,
                   "Toggle / set highlight notification level on current buffer",
                   "[unset|set|toggle]",
                   "   set : silence notifications for normal messages in current channel\n"
                   " unset : enable notifications for normal messages in current channel\n"
                   "toggle : toggle the setting\n\n"
                   "with no parameter, shows the current state",
                   "unset|set|toggle",
                   "set_highlight_cmd_cb", "")
