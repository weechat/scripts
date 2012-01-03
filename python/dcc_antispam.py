# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Sebastien Helleu <flashcode@flashtux.org>
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
# Antispam for DCC file/chat requests.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: make script compatible with Python 3.x
# 2010-02-09, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

import_ok = True

try:
    import weechat
except:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

import re

SCRIPT_NAME    = "dcc_antispam"
SCRIPT_AUTHOR  = "Sebastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Antispam for DCC file/chat requests"

# script options
dcc_settings = {
    "display" : "on",          # display blocked dcc on core buffer?
    # comma separated lists:
    "server"  : "",            # restricts anti-spam on these servers (internal names)
    "name"    : "",            # list of names (regex) to block
    "ip"      : "^0.0.0.0",    # list of IPs (regex) to block
    "port"    : "^0$,^\D+$",   # list of ports (regex) to block
    "size"    : "0",           # list of sizes to block (should be "0" or empty string)
}
dcc_settings_regex_allowed = [ "name", "ip", "port" ]
dcc_settings_regex = {}

# DCC message looks like:
#   SEND:
#     :nick!user@host.com PRIVMSG mynick :\01DCC SEND filename.txt 2130706433 40017 123456\01
#                                                     \----------/ \--------/ \---/ \----/
#                                                         name         ip     port   size
#   CHAT:
#     :nick!user@host.com PRIVMSG mynick :\01DCC CHAT chat 2130706433 40017\01
#                                                          \--------/ \---/
#                                                              ip     port

dcc_regex_dcc_send = re.compile(r"\S+ PRIVMSG \S+ :\01DCC (SEND|CHAT) ([^\01]+)\01")


def dcc_is_blocked(dcc):
    """ Return True if dcc is blocked, False if dcc is not blocked. """
    global dcc_settings_regex
    for key, value in dcc.items():
        if key in dcc_settings_regex:
            if weechat.config_get_plugin(key) != "":
                for regex in dcc_settings_regex[key]:
                    if regex.search(value):
                        return True
        else:
            for str in weechat.config_get_plugin(key).split(","):
                if value == str:
                    return True
    # dcc NOT blocked
    return False

def dcc_parse(type, message):
    """ Parse dcc request, return dict with values. """
    dcc = {}
    for arg in [ "size", "port", "ip" ]:
        if type == "CHAT" and arg == "size":
            continue;
        pos = message.rfind(" ")
        if pos < 0:
            # problem with parsing, dcc is not blocked
            return None
        dcc[arg] = message[pos+1:]
        message = message[:pos]
    if type == "SEND":
        if message.startswith("\"") and message.endswith("\""):
            message = message[1:len(message)-1]
        dcc["name"] = message
    ip = int(dcc["ip"])
    dcc["ip"] = "%d.%d.%d.%d" % (ip >> 24, (ip >> 16) & 0xff, (ip >> 8) & 0xff, ip & 0xff)
    return dcc

def dcc_privmsg_modifier_cb(data, modifier, modifier_data, string):
    """ Modifier callback for IRC PRIVMSG messages. """
    match = dcc_regex_dcc_send.match(string)
    if match:
        server = weechat.config_get_plugin("server")
        if server == "" or modifier_data in server.split(","):
            dcctype = match.group(1)
            dcc = dcc_parse(dcctype, match.group(2))
            if dcc and dcc_is_blocked(dcc):
                if weechat.config_get_plugin("display") == "on":
                    if dcctype == "CHAT":
                        weechat.prnt("", "%s: dcc blocked (chat from %s, ip: %s, port: %s)" %
                                     (SCRIPT_NAME, weechat.info_get("irc_nick_from_host", string),
                                      dcc["ip"], dcc["port"]))
                    else:
                        weechat.prnt("", "%s: dcc blocked (file: '%s' from %s, size: %s bytes, ip: %s, port: %s)" %
                                     (SCRIPT_NAME, dcc["name"], weechat.info_get("irc_nick_from_host", string),
                                      dcc["size"], dcc["ip"], dcc["port"]))
                return ""

    return string

def dcc_build_regex():
    """ Build regex for all options. """
    global dcc_settings_regex_allowed, dcc_settings_regex
    for key in dcc_settings_regex_allowed:
        dcc_settings_regex[key] = []
        try:
            for string in weechat.config_get_plugin(key).split(","):
                dcc_settings_regex[key].append(re.compile(string, re.I))
        except:
            weechat.prnt("", "%s%s: error compiling regex in '%s' (option %s)" %
                         (weechat.prefix("error"), SCRIPT_NAME,
                          weechat.config_get_plugin(key), key))
            dcc_settings_regex[key] = []

def dcc_config_cb(data, option, value):
    """ Callback called when a script option is changed. """
    dcc_build_regex()
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "", ""):
        # set default settings
        for option, default_value in dcc_settings.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        dcc_build_regex()
        # modifier for privmsg messages
        weechat.hook_modifier("irc_in_privmsg", "dcc_privmsg_modifier_cb", "")
        # config
        weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "dcc_config_cb", "")
