# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Jasper v. Blanckenburg <jasper@mezzo.de>
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
# Play back all messages the ZNC bouncer received since you last received a
# message locally
# (this requires the Playback module to be loaded on ZNC)
#
# Add znc.in/playback either to irc.server_default.capabilites or
# to the servers you want to use the Playback module on, then set
# plugins.var.python.zncplayback.servers
#
# History:
#
# 2016-08-27, Jasper v. Blanckenburg <jasper@mezzo.de>:
#     v0.1.0: Initial release

SCRIPT_NAME = "zncplayback"
SCRIPT_AUTHOR = "jazzpi"
SCRIPT_VERSION = "0.1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESCRIPTION = "Add support for the ZNC Playback module"

SCRIPT_SAVEFILE = "zncplayback_times.json"

import_ok = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

try:
    import json
    import os.path as path
    from time import time
except ImportError as message:
    print("Missing package(s) for {}: {}".format(SCRIPT_NAME, message))
    import_ok = False

# Script options
zncplayback_settings_default = {
    "servers": (
        "",
        "Comma-separated list of servers that playback should be fetched for")
}
zncplayback_settings = {}

zncplayback_hooks = {
    "config": None,
    "connected": None,
    "messages": {}
}
zncplayback_last_times = {}


def write_last_times():
    """Write the last message times of all servers to disk."""
    with open(SCRIPT_SAVEFILE, "w") as fh:
        json.dump(zncplayback_last_times, fh)


def read_last_times():
    """Read the last message times of all servers from disk."""
    global zncplayback_last_times
    if not path.exists(SCRIPT_SAVEFILE):
        for server in zncplayback_settings["servers"].split(","):
            zncplayback_last_times[server] = 0
        return
    with open(SCRIPT_SAVEFILE, "r") as fh:
        zncplayback_last_times = json.load(fh)


def zncplayback_config_cb(data, option, value):
    """Update in-memory settings when a script option is changed."""
    global zncplayback_settings
    pos = option.rfind(".")
    if pos > 0:
        name = option[pos+1:]
        if name in zncplayback_settings:
            if name == "servers":
                old_servers = zncplayback_settings["servers"].split(",")
                new_servers = value.split(",")
                # Unhook signals for old servers
                removed_servers = \
                    [s for s in old_servers if s not in new_servers]
                for serv in removed_servers:
                    weechat.unhook(zncplayback_hooks["messages"][serv])
                    del zncplayback_last_times[serv]
                # Hook signals for new servers
                added_servers = \
                    [s for s in new_servers if s not in old_servers]
                for serv in added_servers:
                    zncplayback_hooks["messages"][serv] = weechat.hook_signal(
                        "{},irc_raw_in_PRIVMSG".format(serv),
                        "zncplayback_message_cb", serv)
                    zncplayback_last_times[serv] = 0
            zncplayback_settings[name] = value
    return weechat.WEECHAT_RC_OK


def zncplayback_connected_cb(data, signal, server):
    """Fetch playback after connecting to a server."""
    if server not in zncplayback_settings["servers"].split(","):
        return weechat.WEECHAT_RC_OK
    buf = weechat.buffer_search("irc", "server.{}".format(server))
    weechat.command(buf,
        "/msg *playback PLAY * {}".format(zncplayback_last_times[server]))
    return weechat.WEECHAT_RC_OK


def zncplayback_message_cb(server, signal, message):
    """Update last time for a server when a PRIVMSG is sent."""
    global zncplayback_last_times
    if server not in zncplayback_settings["servers"].split(","):
        return weechat.WEECHAT_RC_OK
    zncplayback_last_times[server] = int(time())
    write_last_times()
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESCRIPTION, "", ""):
        SCRIPT_SAVEFILE = path.join(weechat.info_get("weechat_dir", ""),
                                    SCRIPT_SAVEFILE)
        # Set default settings
        version = weechat.info_get("version_number", "") or 0
        for option, value in zncplayback_settings_default.items():
            if weechat.config_is_set_plugin(option):
                zncplayback_settings[option] = weechat.config_get_plugin(
                    option)
            else:
                weechat.config_set_plugin(option, value[0])
                zncplayback_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(
                    option,
                    "%s (default: \"%s\")" % (value[1], value[0]))

        read_last_times()
        zncplayback_hooks["config"] = weechat.hook_config(
            "plugins.var.python.%s.*" % SCRIPT_NAME, "zncplayback_config_cb",
            "")
        zncplayback_hooks["connected"] = weechat.hook_signal(
            "irc_server_connected", "zncplayback_connected_cb", "")
        for serv in zncplayback_settings["servers"].split(","):
            zncplayback_hooks["messages"][serv] = weechat.hook_signal(
                "{},irc_raw_in_PRIVMSG".format(serv),
                "zncplayback_message_cb", serv)

        # TODO: Unhook when unloading script
