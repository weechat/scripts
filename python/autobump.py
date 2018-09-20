# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Daniel Kessler <daniel@dkess.me>
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

# This script bumps buffers when there is activity on them,
# replicating the functionality of most mainstream chat programs.

# TODO: combine priorities of merged buffers

import weechat

SCRIPT_NAME = 'autobump'
SCRIPT_AUTHOR = 'Daniel Kessler <daniel@dkess.me>'
SCRIPT_VERSION = '0.0.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Bump buffers upon activity.'

DEFAULTS = {
    'lowprio_buffers': ('', 'List of buffers to be sorted with low priority'),
    'highprio_buffers': ('irc.server.*,core.weechat',
                         'List of buffers to be sorted with high priority')
}

def on_autobump_command(data, buffer, args):
    argv = args.split()
    if len(argv) < 2 or argv[0] not in {'add', 'del'} or argv[1] not in {'high', 'low'}:
        return weechat.WEECHAT_RC_ERROR

    bufname = weechat.buffer_get_string(buffer, 'full_name')

    key = argv[1] + 'prio_buffers'
    buflist = weechat.config_get_plugin(key).split(',')

    if argv[0] == 'add':
        if bufname not in buflist:
            buflist.append(bufname)
    elif bufname in buflist:
        buflist.remove(bufname)
    else:
        return weechat.WEECHAT_RC_ERROR

    weechat.config_set_plugin(key, ','.join(buflist))

    on_buffer_activity(buffer)

    return weechat.WEECHAT_RC_OK

def get_buffers():
    '''Get a list of all the buffers in weechat.'''
    hdata  = weechat.hdata_get('buffer')
    buffer = weechat.hdata_get_list(hdata, "gui_buffers");

    result = []
    while buffer:
        number = weechat.hdata_integer(hdata, buffer, 'number')
        result.append((number, buffer))
        buffer = weechat.hdata_pointer(hdata, buffer, 'next_buffer')
    return hdata, result

def buffer_priority(buffer):
    '''Get a buffer's priority. Higher number means higher priority.'''
    lowprio_match = weechat.config_get_plugin('lowprio_buffers')
    if weechat.buffer_match_list(buffer, lowprio_match):
        return 0

    highprio_match = weechat.config_get_plugin('highprio_buffers')
    if weechat.buffer_match_list(buffer, highprio_match):
        return 2

    return 1

def on_buffer_activity(buffer):
    prio = buffer_priority(buffer)
    if prio == 2:
        weechat.buffer_set(buffer, 'number', '1')
        return

    hdata, buffers = get_buffers()
    for num, buf in reversed(buffers):
        if prio < buffer_priority(buf):
            weechat.buffer_set(buffer, 'number', str(num + 1))
            return

    weechat.buffer_set(buffer, 'number', '1')

def on_print(data, buffer, date, tags, displayed, highlight, prefix, message):
    if int(displayed):
        on_buffer_activity(buffer)
    return weechat.WEECHAT_RC_OK

def on_signal(data, signal, signal_data):
    on_buffer_activity(signal_data)
    return weechat.WEECHAT_RC_OK

command_description = r'''/autobump add high: Add the current buffer to the high priority list
/autobump add low: Add the current buffer to the low priority list
/autobump del high: Remove the current buffer from the high priority list
/autobump del low: Remove the current buffer from the low priority list

You can manually modify the high/low priority lists (for instance, with custom patterns) with /set var.plugins.python.autobump.highprio_buffers and /set var.plugins.python.autobump.lowprio_buffers.

See /help filter for documentation on writing buffer lists.
'''

command_completion = 'add high || add low || del high || del low'

if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        for option, value in DEFAULTS.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, value[0])
            weechat.config_set_desc_plugin(option, value[1])

        weechat.hook_print('', 'log1,log3', '', 0, 'on_print', '')
        weechat.hook_signal('buffer_opened', 'on_signal', '')

        weechat.hook_command('autobump',
                             command_description,
                             '',
                             '',
                             command_completion,
                             'on_autobump_command',
                             '')
