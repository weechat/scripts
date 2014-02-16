# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by Alexander Schremmer <alex@alexanderweb.de>
# Copyright (c) 2013 by Corey Halpin <chalpin@cs.wisc.edu>
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
# (this script requires WeeChat 0.3.6 or newer)
#
# History:
# 2014-02-15, Corey Halpin <chalpin@cs.wisc.edu>
#  version 0.5:
#    * Improve documentation for the 'server' setting
#    * Change the default for 'server' to bitlbee, as this is probably
#      what most people use.
# 2013-06-24, Priska Herger <policecar@23bit.net>
#  version 0.4: bug fix: if TYPING 0, don't show typing.
# 2013-04-27, Corey Halpin <chalpin@cs.wisc.edu>
#  version 0.3:
#    * Use irc_message_parse to extract nicks
#    * Send typing = 0 at message completion in private buffers
#    * Make server, channel, and timeout configurable w/o editing plugin code.
# 2010-05-20, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.2: also handle users that do not send a TYPING 0 msg before quitting
#                removed InfoList code
# 2010-05-16, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.1: initial release


# Configuration options via /set:
#
# 'channel'
#   description: Name of your bitlbee channel
#   command: /set plugins.var.python.bitlbee_typing_notice.channel &bitlbee
#
# 'server'
#   description: Name of the server running your bitlbee instance.  This will
#     be whatever you type after /connect to get to your bitlbee server
#     (e.g., localhost, bitlbee).
#   command: /set plugins.var.python.bitlbee_typing_notice.server bitlbee
#
# 'timeout'
#   description: Send "not typing" after this many seconds w/o typing.
#   command: /set plugins.var.python.bitlbee_typing_notice.timeout 4
#
# Note, the plugin must be reloaded after either of these settings are changed.
# /python reload works for this.


import weechat as w
import re

SCRIPT_NAME    = "bitlbee_typing_notice"
SCRIPT_AUTHOR  = "Alexander Schremmer <alex@alexanderweb.de>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Shows when somebody is typing on bitlbee and sends the notice as well"

typing = {} # Record nicks who sent typing notices.  key = subject nick, val = typing level.

sending_typing = {} # Nicks to whom we're sending typing notices.
#  key = target nick, val = sequence number used to determine when the typing notice
#    should be removed.

def channel_has_nick(server, channel, nick):
    buffer = w.buffer_search("", "%s.%s" % (server, channel))
    return bool(w.nicklist_search_nick(buffer, "", nick))

# Callback which checks for ctcp typing notices sent to us.
# Updates typing data, hides the ctcp notices.
def ctcp_cb(data, modifier, modifier_data, string):
    if modifier_data != w.config_get_plugin("server"):
        return string
    msg_hash = w.info_get_hashtable(
        "irc_message_parse", {"message": string} )
    if msg_hash["command"] != "PRIVMSG":
        return string
    match = re.search('\001TYPING ([0-9])\001', msg_hash["arguments"])
    if match:
        nick = msg_hash["nick"]
        typing_level = int(match.groups()[0])
        if typing_level == 0 and nick in typing:
            del typing[nick]
        elif typing_level > 0:
            typing[nick] = typing_level
        w.bar_item_update("bitlbee_typing_notice")
        return ""
    else:
        return string


def stop_typing(data, signal, signal_data):
    msg_hash = w.info_get_hashtable(
        "irc_message_parse", {"message": signal_data } )
    if msg_hash["nick"] in typing:
        del typing[msg_hash["nick"]]
    w.bar_item_update("bitlbee_typing_notice")
    return w.WEECHAT_RC_OK

def typed_char(data, signal, signal_data):
    buffer = w.current_buffer()
    input_s = w.buffer_get_string(buffer, 'input')
    server = w.buffer_get_string(buffer, 'localvar_server')
    channel = w.buffer_get_string(buffer, 'localvar_channel')
    buffer_type = w.buffer_get_string(buffer, 'localvar_type')

    if server != w.config_get_plugin("server") or input_s.startswith("/"):
        return w.WEECHAT_RC_OK
    if buffer_type == "private":
        if len(input_s)==0:
            send_typing(channel, 0) # Line sent or deleted -- no longer typing
        else:
            send_typing(channel, 1)
    elif channel == w.config_get_plugin("channel"):
        nick_completer = w.config_string("weechat.completion.nick_completer")
        parts = input_s.split(":", 1)
        if len(parts) > 1:
            nick = parts[0]
            send_typing(nick, 1)
    return w.WEECHAT_RC_OK


def typing_disable_timer(data, remaining_calls):
    nick, cookie = data.rsplit(":", 1)
    cookie = int(cookie)
    if nick in sending_typing and sending_typing[nick]==cookie:
        send_typing_ctcp(nick, 0)
        del sending_typing[nick]
    return w.WEECHAT_RC_OK


def send_typing_ctcp(nick, level):
    if not channel_has_nick(w.config_get_plugin("server"),
                            w.config_get_plugin("channel"), nick):
        return
    buffer = w.buffer_search("irc", "%s.%s" %
                             (w.config_get_plugin("server"),
                              w.config_get_plugin("channel")) )
    w.command(buffer, "/mute -all /ctcp %s TYPING %i" % (nick, level))


def send_typing(nick, level):
    if level == 0 and nick in sending_typing:
        send_typing_ctcp(nick, 0)
        del sending_typing[nick]
    elif level > 0 :
        if nick not in sending_typing:
            send_typing_ctcp(nick, level)
        cookie = sending_typing.get(nick, 0) + 1
        sending_typing[nick] = cookie
        w.hook_timer( int(1000 * float(w.config_get_plugin('timeout'))), 0, 1,
                      "typing_disable_timer", "%s:%i" % (nick, cookie))


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


# Main
if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):

        if not w.config_get_plugin('channel'):
            w.config_set_plugin('channel', "&bitlbee")
        if not w.config_get_plugin('server'):
            w.config_set_plugin('server', "bitlbee")
        if not w.config_get_plugin('timeout'):
            w.config_set_plugin('timeout', "4")

        w.hook_signal("input_text_changed", "typed_char", "")
        w.hook_signal(w.config_get_plugin("server")+",irc_in_quit", "stop_typing", "")
        w.hook_signal(w.config_get_plugin("server")+",irc_in_privmsg", "stop_typing", "")
        w.bar_item_new('bitlbee_typing_notice', 'typing_notice_item_cb', '')
        w.hook_modifier("irc_in_privmsg", "ctcp_cb", "")
