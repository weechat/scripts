# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by Alexander Schremmer <alex@alexanderweb.de>
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
# 2010-05-20, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.2: also handle users that do not send a TYPING 0 msg before quitting
#                removed InfoList code
# 2010-05-16, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "bitlbee_typing_notice"
SCRIPT_AUTHOR  = "Alexander Schremmer <alex@alexanderweb.de>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Shows when somebody is typing on bitlbee and sends the notice as well"


bitlbee_channel = "&bitlbee"
bitlbee_server_name = "bitlbee"

KEEP_TYPING_TIMEOUT = 1
STOP_TYPING_TIMEOUT = 7

typing = {}
sending_typing = {}


def channel_has_nick(server, channel, nick):
    buffer = w.buffer_search("", "%s.%s" % (server, channel))
    return bool(w.nicklist_search_nick(buffer, "", nick))


def redraw(nick):
    w.bar_item_update("bitlbee_typing_notice")


def ctcp_cb(data, modifier, modifier_data, string):
    if modifier_data != bitlbee_server_name:
        return string
    match = re.match(r'(.*) PRIVMSG (.*)', string)
    if match:
        host, msg = match.groups()
        match = re.search('\001TYPING ([0-9])\001', msg)
        if match:
            nick = re.match(':(?P<nick>.+)!', string).groups()[0]
            typing_level = int(match.groups()[0])
            if typing_level == 0:
                try:
                    del typing[nick]
                except KeyError:
                    pass
                redraw(nick)
            elif typing_level == 1:
                typing[nick] = 1
                # XXX add ICQ/Yahoo hack
                redraw(nick)
            elif typing_level == 2:
                typing[nick] = 2
                redraw(nick)
            return ""
    return string
    buffer = w.buffer_search("", "%s.%s" % (server, channel))

def stop_typing(data, signal, signal_data):
    nick = re.match(':(?P<nick>.+)!', signal_data).groups()[0]
    try:
        del typing[nick]
    except KeyError:
        pass
    redraw(nick)
    return w.WEECHAT_RC_OK

def typed_char(data, signal, signal_data):
    buffer = w.current_buffer()
    input_s = w.buffer_get_string(buffer, 'input')
    server = w.buffer_get_string(buffer, 'localvar_server')
    channel = w.buffer_get_string(buffer, 'localvar_channel')
    buffer_type = w.buffer_get_string(buffer, 'localvar_type')

    if server != bitlbee_server_name or input_s.startswith("/"):
        return w.WEECHAT_RC_OK
    if buffer_type == "private":
        if input_s:
            send_typing(channel, 1)
    elif channel == bitlbee_channel:
        nick_completer = w.config_string("weechat.completion.nick_completer")
        parts = input_s.split(":", 1)
        if len(parts) > 1:
            nick = parts[0]
            send_typing(nick, 1)

    return w.WEECHAT_RC_OK


def typing_disable_timer(data, remaining_calls):
    nick, cookie = data.rsplit(":", 1)
    cookie = int(cookie)
    if sending_typing[nick] == cookie:
        send_typing_ctcp(nick, 0)
        sending_typing[nick] = False
    return w.WEECHAT_RC_OK

def send_typing_ctcp(nick, level):
    buffer = w.buffer_search("irc", "%s.%s" % (bitlbee_server_name, bitlbee_channel))
    w.command(buffer, "/mute -all /ctcp %s TYPING %i" % (nick, level))

def send_typing(nick, level):
    if not channel_has_nick(bitlbee_server_name, bitlbee_channel, nick):
        return
    cookie = sending_typing.get(nick, 1) + 1
    if not sending_typing.get(nick, None):
        send_typing_ctcp(nick, level)
    sending_typing[nick] = cookie
    w.hook_timer(4000, 0, 1, "typing_disable_timer", "%s:%i" % (nick, cookie))


def typing_notice_item_cb(data, buffer, args):
    if typing:
        msgs = []
        for key, value in typing.items():
            msg = key
            if value == 2:
                msg += " (stale)"
            msgs.append(msg)
        return "typing: " + ", ".join(sorted(msgs))
    return ""


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    w.hook_signal("input_text_changed", "typed_char", "")
    w.hook_signal(bitlbee_server_name + ",irc_in_quit", "stop_typing", "")
    w.hook_signal(bitlbee_server_name + ",irc_in_privmsg", "stop_typing", "")
    w.bar_item_new('bitlbee_typing_notice', 'typing_notice_item_cb', '')
    w.hook_modifier("irc_in_privmsg", "ctcp_cb", "")

