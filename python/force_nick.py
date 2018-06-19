# -*- coding: utf-8 -*-
#
# Copyright (c) 2015-2018 by Simmo Saan <simmo.saan@gmail.com>
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
# History:
#
# 2018-06-19, Simmo Saan <simmo.saan@gmail.com>
#   version 0.5: ignore channel modes arguments
# 2015-08-07, Simmo Saan <simmo.saan@gmail.com>
#   version 0.4: option for invite-only channels
# 2015-08-07, Simmo Saan <simmo.saan@gmail.com>
#   version 0.3: options to control risky channel cycling
# 2015-07-03, Simmo Saan <simmo.saan@gmail.com>
#   version 0.2: ability to rejoin passworded channels
# 2015-07-01, Simmo Saan <simmo.saan@gmail.com>
#   version 0.1: initial script
#

"""
Force nick change on channels which disallow it
"""

from __future__ import print_function

SCRIPT_NAME = "force_nick"
SCRIPT_AUTHOR = "Simmo Saan <simmo.saan@gmail.com>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Force nick change on channels which disallow it"

IMPORT_OK = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    IMPORT_OK = False

SETTINGS = {
    "cycle_detach": (
        "off",
        "automatically cycle channels which are not open in WeeChat"),
    "cycle_key": (
        "on",
        "automatically cycle passworded channels (+k)"),
    "cycle_invite": (
        "off",
        "automatically cycle invite-only channels (+i)")
}

import re

servers = {}

def parse_message(signal_data):
    hashtable = weechat.info_get_hashtable("irc_message_parse", {"message": signal_data})

    # parse arguments string into usable pieces
    args = hashtable["arguments"].split(":", 1)
    hashtable["args"] = args[0].split()
    if len(args) > 1:
        hashtable["text"] = args[1]

    return hashtable

def channel_block(server, channel):
    fail = None
    config_cycle = lambda opt: weechat.config_string_to_boolean(weechat.config_get_plugin("cycle_%s" % opt))

    channels = weechat.infolist_get("irc_channel", "", "%s,%s" % (server, channel))
    if weechat.infolist_next(channels):
        modes = weechat.infolist_string(channels, "modes")
        if " " in modes:
            modes, modes_args = modes.split(" ", 1)

        if not config_cycle("key") and weechat.infolist_string(channels, "key") != "":
            fail = "cycle_key"
        elif not config_cycle("invite") and "i" in modes:
            fail = "cycle_invite"
    elif not config_cycle("detach"):
        fail = "cycle_detach"

    weechat.infolist_free(channels)

    if fail:
        weechat.prnt("", "%s: won't automatically cycle %s.%s: %s" % (SCRIPT_NAME, server, channel, fail))
    else:
        servers[server]["channels"].append(channel)
        buffer = weechat.buffer_search("irc", server)
        weechat.command(buffer, "/part %s" % channel)
        weechat.command(buffer, "/nick %s" % servers[server]["nick"])

def nick_out_cb(data, signal, signal_data):
    server = signal.split(",")[0]
    parsed = parse_message(signal_data)
    nick = parsed["args"][0]

    if server not in servers: # initialize new nickchange
        servers[server] = {}
        servers[server]["channels"] = []

    servers[server]["nick"] = nick

    return weechat.WEECHAT_RC_OK

def nick_in_cb(data, signal, signal_data):
    server = signal.split(",")[0]
    parsed = parse_message(signal_data)
    mynick = weechat.info_get("irc_nick", server)

    if parsed["nick"] == mynick: # nick change worked
        channels = weechat.infolist_get("irc_channel", "", server)
        keys = {}
        while weechat.infolist_next(channels):
            keys[weechat.infolist_string(channels, "name")] = weechat.infolist_string(channels, "key")

        buffer = weechat.buffer_search("irc", server)
        for channel in servers[server]["channels"]:
            weechat.command(buffer, "/join -noswitch %s %s" % (channel, keys.get(channel, "")))

        weechat.infolist_free(channels)

        servers.pop(server)

    return weechat.WEECHAT_RC_OK

def unreal_cb(data, signal, signal_data):
    server = signal.split(",")[0]
    parsed = parse_message(signal_data)

    match = re.match(r"Can not change nickname while on (#\w+) \(\+N\)", parsed["text"])
    if match:
        channel = match.group(1)
        channel_block(server, channel)

    return weechat.WEECHAT_RC_OK

def freenode_cb(data, signal, signal_data):
    server = signal.split(",")[0]
    parsed = parse_message(signal_data)

    channel_block(server, parsed["args"][2])

    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and IMPORT_OK:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_signal("*,irc_out1_nick", "nick_out_cb", "")
        weechat.hook_signal("*,irc_in_nick", "nick_in_cb", "")
        weechat.hook_signal("*,irc_in_447", "unreal_cb", "")
        weechat.hook_signal("*,irc_in_435", "freenode_cb", "")

        for option, value in SETTINGS.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, value[0])

            weechat.config_set_desc_plugin(option, "%s (default: \"%s\")" % (value[1], value[0]))
