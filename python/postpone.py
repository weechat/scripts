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
# 2015-04-29, Colgate Minuette <rabbit@minuette.net>
#   version 0.2.3: add option to send queued messages on /nick
# 2013-11-08, Stefan Huber <shuber@sthu.org>
#   version 0.2.2: add match_prefix setting, recall timestamp of message
# 2012-12-29, Stefan Huber <shuber@sthu.org>
#   version 0.2.1: fix channel determination in join_cb
# 2010-05-20, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.2: removed InfoList code
# 2010-05-15, Alexander Schremmer <alex@alexanderweb.de>
#   version 0.1: initial release

import weechat as w
import re
from datetime import datetime
from time import strftime

SCRIPT_NAME    = "postpone"
SCRIPT_AUTHOR  = "Alexander Schremmer <alex@alexanderweb.de>"
SCRIPT_VERSION = "0.2.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Postpones written messages for later dispatching if target nick is not on channel"

postpone_data = {}

settings = {
        'match_prefix': ('', 'Postpone message if prefix before "nick:" is matched. (Default: "")'),
        'message_on_nick': ('off', 'Send message on /nick in addition to /join (Default: off)')
}

def send_messages(server, channel, nick):
    buffer = w.buffer_search("", "%s.%s" % (server, channel))
    messages = postpone_data[server][channel][nick]
    for time, msg in messages:
        tstr = strftime("%Y-%m-%d %H:%M:%S", time.timetuple())
        w.command(buffer, msg + " (This message has been postponed on " + tstr + ".)")
    messages[:] = []

def join_cb(data, signal, signal_data):
    server = signal.split(',')[0] # EFNet,irc_in_JOIN
    channel = re.match('.* JOIN :?(?P<channel>.+)$', signal_data).groups()[0]
    nick = re.match(':(?P<nick>.+)!', signal_data).groups()[0].lower()
    buffer = w.buffer_search("", "%s.%s" % (server, channel))
    if server in postpone_data and channel in postpone_data[server] and\
            nick in postpone_data[server][channel]:
        send_messages(server, channel, nick)
    return w.WEECHAT_RC_OK

def nick_cb(data, signal, signal_data):

    if not w.config_is_set_plugin('message_on_nick'):
        return w.WEECHAT_RC_OK
    if not w.config_get_plugin('message_on_nick').lower() == "on":
        return w.WEECHAT_RC_OK

    server = signal.split(",")[0]
    if server in postpone_data:
        nick = signal_data.split(" ")[2]
        if nick.startswith(":"):
           nick = nick[1:]
        nick = nick.lower()
        for channel in postpone_data[server]:
            if nick in postpone_data[server][channel]:
                send_messages(server, channel, nick)
    return w.WEECHAT_RC_OK

def channel_has_nick(server, channel, nick):
    buffer = w.buffer_search("", "%s.%s" % (server, channel))
    return bool(w.nicklist_search_nick(buffer, "", nick))

def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    if command == "/input return": # As in enter was pressed.
        input_s = w.buffer_get_string(buffer, 'input')
        server = w.buffer_get_string(buffer, 'localvar_server')
        channel = w.buffer_get_string(buffer, 'localvar_channel')
        match_prefix = w.config_get_plugin('match_prefix')

        match = re.match(match_prefix + r'([\w-]+?): (.*)$', input_s)
        if match:
            nick, message = match.groups()
            if not channel_has_nick(server, channel, nick):
                w.prnt(buffer, "| Enqueued message for %s: %s" % (nick, message))
                save = datetime.now(), nick + ": " + message
                postpone_data.setdefault(server, {}).setdefault(channel,
                        {}).setdefault(nick.lower(), []).append(save)
                w.buffer_set(buffer, 'input', "")
                # XXX why doesn't this work? i want to have the typed text
                # in the history
                #history_list = w.infolist_get("history", buffer, "")
                #history_item = w.infolist_new_item(history_list)
                #w.infolist_new_var_string(history_item, "text", input_s)
    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):

    version = w.info_get('version_number', '') or 0
    for option, default_desc in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_desc[0])
        if int(version) >= 0x00030500:
            w.config_set_desc_plugin(option, default_desc[1])

    w.hook_command_run("/input return", "command_run_input", "")
    w.hook_signal('*,irc_in2_join', 'join_cb', '')
    w.hook_signal('*,irc_in2_nick', 'nick_cb', '')
