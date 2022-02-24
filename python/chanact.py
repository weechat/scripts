# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010 by xt <xt@bash.no>
# Copyright (c) 2011 by mythmon <mythmon@gmail.com>
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2020-06-10, Sébastien Helleu <flashcode@flashtux.org>
#   version 1.0: Fix undefined variable
# 2020-06-10, squigz
#   version 0.9: Update for Python 3
# 2013-09-16, d33tah
#   version 0.8: Added sort_by_number configuration variable.
# 2013-03-18, mythmon
#   version 0.7: Channels get a bonus based on priority in sorting.
# 2012-02-09, mythmon
#   version 0.6: Allow sorting of channels
# 2010-10-21, xt
#   version 0.5: use ^ for ctrl
# 2010-02-08, bazerka <bazerka@quakenet.org>
#   version 0.4: fix "[Act:]" being shown with no activity, when delimiter
#                is set to " ".
# 2009-05-26, xt <xt@bash.no>
#   version 0.3: only update keydict when key bindings change
# 2009-05-16, xt <xt@bash.no>
#   version 0.2: added support for using keybindings instead of names.
# 2009-05-10, xt <xt@bash.no>
#   version 0.1: initial release.
#
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
'''Hotlist replacement.

Usage: first, put [chanact] in your status bar items.
" weechat.bar.status.items".

Then you can bind keys to buffers with
/key bind meta-w /buffer #weechat

And then it will show as [Act: w] on your status bar.

You can change the order that windows appear in the status bar by setting a
sort rank with
/chanact sort [num]

If you leave off the number, it will print the current sort rank of a buffer.
'''

try:
    import weechat as w
except:
    import sys
    print("This script must be run inside weechat.")
    sys.exit(1)


SCRIPT_NAME    = "chanact"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Hotlist replacement, use names and keybindings instead of numbers"

# script options
settings = {
    "lowest_priority"       : '0',
    'message'               : 'Act: ',
    'item_length'           : '8',
    'color_default'         : 'default',
    'color_1'               : 'white',
    'color_2'               : 'cyan',
    'color_3'               : 'lightcyan',
    'color_4'               : 'yellow',
    'color_8'               : 'cyan',
    'use_keybindings'       : 'on',
    'delimiter'             : ',',
    'skip_number_binds'     : 'on',
    'sort_by_number'        : 'off',
}

hooks = (
    ('hotlist_*', 'chanact_update'),
    ('key_bind', 'keydict_update'),
    ('key_unbind', 'keydict_update'),
)

keydict = {}


def chanact_command(data, buffer, args):
    args = args.split(' ')
    if args[0] == 'sort':
        if len(args) == 1:
            s = sort_rank(buffer, 0)
            w.prnt(buffer, 'Sort rank of this buffer: %d' % s)
        elif len(args) == 2:
            s = args[1]
            w.buffer_set(buffer, 'localvar_set_sort', s)
            w.prnt(buffer, 'Sort rank of this buffer set to: %s' % s)

    return w.WEECHAT_RC_OK


def sort_rank(buffer, priority):
    rank = w.buffer_get_string(buffer, 'localvar_sort')
    priority = int(priority) if priority else 0

    if rank:
        return int(rank) + priority
    else:
        return priority


def keydict_update(*args):
    '''Populate a python dictionary with relevant key=>buffer mappings.'''

    global keydict

    keylist = w.infolist_get('key', '', '')
    if w.config_get_plugin('use_keybindings') == 'on':
        while w.infolist_next(keylist):
            key = w.infolist_string(keylist, 'key')
            # we dont want jump sequences
            if 'j' in key:
                continue
            key = key.replace('meta-', '')
            key = key.replace('ctrl-', '^')
            if w.config_get_plugin('skip_number_binds') == 'on':
                # skip entries where buffer number = key, typically entries below 11
                if key.isdigit():
                    continue
            command = w.infolist_string(keylist, 'command')
            # we only care about commands that leads to buffers
            if command.startswith('/buffer'):
                command = command.replace('/buffer ', '')
                buffer = command.lstrip('*')
                keydict[buffer] = key
    w.infolist_free(keylist)
    return w.WEECHAT_RC_OK


def chanact_cb(*args):
    ''' Callback ran on hotlist changes '''
    global keydict

    hotlist = w.infolist_get('hotlist', '', '')

    activity = []
    while w.infolist_next(hotlist):
        priority = w.infolist_integer(hotlist, 'priority')

        if priority < int(w.config_get_plugin('lowest_priority')):
            continue

        int_number = w.infolist_integer(hotlist, 'buffer_number')
        number = str(int_number)
        thebuffer = w.infolist_pointer(hotlist, 'buffer_pointer')
        name = w.buffer_get_string(thebuffer, 'short_name')

        color = w.config_get_plugin('color_default')
        if priority > 0:
            color = w.config_get_plugin('color_%s' %priority)

        if number in keydict:
            number = keydict[number]
            entry = '%s%s%s' % (w.color(color), number, w.color('reset'))
        elif name in keydict:
            name = keydict[name]
            entry = '%s%s%s' % (w.color(color), name, w.color('reset'))
        elif name:
            entry = '%s%s%s:%s%s%s' % (
                    w.color('default'),
                    number,
                    w.color('reset'),
                    w.color(color),
                    name[:int(w.config_get_plugin('item_length'))],
                    w.color('reset'))
        else:
            entry = '%s%s%s' % (
                    w.color(color),
                    number,
                    w.color('reset'))

        activity.append((entry, thebuffer, sort_rank(thebuffer, priority), int_number))

    if w.config_get_plugin('sort_by_number') == "on":
        activity.sort(key=lambda t: int(t[3]))
    else:
        activity.sort(key=lambda t: int(t[2]), reverse=True)

    w.infolist_free(hotlist)
    if activity:
        message = w.config_get_plugin('message')
        delim = w.config_get_plugin('delimiter')
        return message + delim.join(a[0] for a in activity)
    else:
        return ''

def chanact_update(*args):
    ''' Hooked to hotlist changes '''

    w.bar_item_update('chanact')

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, '', ''):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    for hook, cb in hooks:
        w.hook_signal(hook, cb, '')

    w.bar_item_new('chanact', 'chanact_cb', '')
    keydict_update()


w.hook_command('chanact', 'Manipulate chanact.', 'sort [rank]',
    'sort: Show or set the sort rank of the current buffer.',
    'sort', 'chanact_command', '')
