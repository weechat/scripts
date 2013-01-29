# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by nils_2 <weechatter@arcor.de>
#
# stick buffer to a window, irssi like
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
# idea by shad0VV@freenode.#weechat
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.2 : make script compatible with Python 3.x
#           : smaller improvements
#
# 2013-01-21: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.0
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat, sys

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "stick_buffer"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.2"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "stick buffer to a window, irssi like"

# ===============================[ infolist() ]=============================
def infolist_get_buffer_name_and_ptr(str_buffer_number):
    infolist = weechat.infolist_get('buffer', '', '')
    full_name = ''
    ptr_buffer = ''
    if infolist:
        while weechat.infolist_next(infolist):
            if int(str_buffer_number) == weechat.infolist_integer(infolist, 'number'):
                full_name = weechat.infolist_string(infolist, 'full_name')
                ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
                break
    weechat.infolist_free(infolist)
    return full_name, ptr_buffer

def get_current_buffer_number():
    ptr_buffer = weechat.window_get_pointer(weechat.current_window(), 'buffer')
    return weechat.buffer_get_integer(ptr_buffer, 'number')

# return empty string if no number is found
def get_buffer_number_as_string(data):
    if sys.version_info < (3,):
        return filter(lambda x: x.isdigit(), data)
    return [x for x in data if x.isdigit()]

# ===============================[ callback() ]=============================
def buffer_switch_cb(signal, callback, callback_data):
    if callback_data == '':
        return weechat.WEECHAT_RC_OK

    argv = callback_data.strip().split(' ',)[1:]
    if len(argv) == 0 or len(argv) > 1:
        return weechat.WEECHAT_RC_OK

    # check out if string is a number
    str_buffer_number = get_buffer_number_as_string(argv[0])
    if not str_buffer_number:
        return weechat.WEECHAT_RC_OK

    curren_buffer_number = get_current_buffer_number()
    if not curren_buffer_number:
        return weechat.WEECHAT_RC_OK
    if argv[0][0] == '-':
        switch_to_buffer = curren_buffer_number - int(argv[0][1:])      # [1:] don't use first sign
        if switch_to_buffer < 1:
            switch_to_buffer = 1
    elif argv[0][0] == '+':
        switch_to_buffer = curren_buffer_number + int(argv[0][1:])      # [1:] don't use first sign
    else:
        switch_to_buffer = int(str_buffer_number[0])

    buffer_name, ptr_buffer = infolist_get_buffer_name_and_ptr(switch_to_buffer)
    if not buffer_name or not ptr_buffer:
        return weechat.WEECHAT_RC_OK

    if ptr_buffer == weechat.window_get_pointer(weechat.current_window(),'buffer'):
        return weechat.WEECHAT_RC_OK

    window_number = weechat.buffer_get_string(ptr_buffer,'localvar_stick_buffer_to_window')
    if window_number:
        weechat.command('','/window %s' % window_number)
    return weechat.WEECHAT_RC_OK


def open_buffer_cmd_cb(data, buffer, args):
    argv = args.strip().split(' ', 1)
    if len(argv) == 0:
        return weechat.WEECHAT_RC_OK

    if argv[0].lower() == 'list':
        weechat.command('','/set *.localvar_set_stick_buffer_to_window')

    return weechat.WEECHAT_RC_OK
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'list',
                            '\n'
                            'You have to create a localvar, \"stick_buffer_to_window\", for the buffer you want to stick to a specific window.\n'
                            'You will need script \"buffer_autoset.py\" to make local variabe persistent (see examples, below)!!\n'
                            '\n'
                            'Examples:\n'
                            ' temporarily stick the current buffer to window 3:\n'
                            '   /buffer set localvar_set_stick_buffer_to_window 3\n'
                            ' stick buffer #weechat to window 2:\n'
                            '   /autosetbuffer add irc.freenode.#weechat stick_buffer_to_window 2\n'
                            ' lists buffer who are bind to a specific window (only persistent ones!):\n'
                            '   /' + SCRIPT_NAME + ' list\n'
                            ' display local variables for current buffer:\n'
                            '   /buffer localvar\n'
                            '',
                            'list %-',
                            'open_buffer_cmd_cb', '')

        weechat.hook_command_run('/buffer *', 'buffer_switch_cb', '')
#        weechat.prnt("","%s.%s" % (sys.version_info[0], sys.version_info[1]))

