# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by nils_2 <weechatter@arcor.de>
#
# mark buffer as unread
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
# idea by Phyks
#
# 2015-03-13: nils_2, (freenode.#weechat)
#       1 : initial release

try:
    import weechat
    import time

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "unread_buffer"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "1"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "mark buffer as unread"

def unread_buffer_cb(data, buffer, args):

    arguments = args.lower().split(' ')
    if not len(arguments) == 2:
        return weechat.WEECHAT_RC_OK

    if arguments[0] == 'low':
        priority = "0"
    elif arguments[0] == 'message':
        priority = "1"
    elif arguments[0] == 'private':
        priority = "2"
    elif arguments[0] == 'highlight':
        priority = "3"
    else:
        return weechat.WEECHAT_RC_OK
    # search for either buffer_name or buffer_number
    ptr_buffer = buffer_infolist(arguments[1])

    # check if buffer is *not* in hotlist
    if not check_hotlist(ptr_buffer):
        weechat.buffer_set(ptr_buffer, "hotlist", priority)

    return weechat.WEECHAT_RC_OK

def buffer_infolist(buf_name):
    ptr_buffer = 0
    infolist = weechat.infolist_get('buffer', '', '')
    while weechat.infolist_next(infolist):
        short_name = weechat.infolist_string(infolist, 'short_name')
        name = weechat.infolist_string(infolist, 'name')
        number = weechat.infolist_integer(infolist, 'number')
        matching = name.lower().find(buf_name) >= 0
        if matching:
            ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
            break
        if not matching and buf_name.isdigit():
            matching = str(number).startswith(buf_name)
            if len(buf_name) == 0 or matching:
                ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
                break
    weechat.infolist_free(infolist)
    if ptr_buffer:
        buf_type = weechat.buffer_get_string(ptr_buffer, "localvar_type")
        # buffer has no type (e.g. channel, private, server, weechat)
        if buf_type == '':
            ptr_buffer = 0
    return ptr_buffer

def check_hotlist(check_pointer):
    ptr_buffer = 0
    infolist = weechat.infolist_get('hotlist', '', '')
    while weechat.infolist_next(infolist):
        pointer = weechat.infolist_pointer(infolist, 'buffer_pointer')
        if pointer == check_pointer:
            ptr_buffer = pointer
            break
    weechat.infolist_free(infolist)
    return ptr_buffer
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        WEECHAT_VERSION = weechat.info_get("version_number", "") or 0

        if int(WEECHAT_VERSION) >= 0x01000000:
            weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'low <buffer>||message <buffer>||private <buffer>||highlight <buffer>',
                                 'Notify levels:\n'
                                 '  low      : message with low importance (for example irc join/part/quit)\n'
                                 '  message  : message from a user\n'
                                 '  private  : message in a private buffer\n'
                                 '  highlight: message with highlight\n'
                                 '\n'
                                 '<buffer> can be a buffer name or a buffer number\n'
                                 '\n'
                                 'Example:\n'
                                 '  /unread_buffer highlight 3\n'
                                 '  /unread_buffer message freenode.#weechat\n',
                                 'low|message|private|highlight %(buffers_names)|%(buffers_numbers) %-',
                                 'unread_buffer_cb',
                                 '')
        else:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 1.0 or higher'))
