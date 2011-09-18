"""Set channel priority

Based on the idea of Flavius Aspra <flavius.as@gmail.com>

When joining channels the buffers will be arranged from high to low priority.
Buffers containing high-priority channels will be in the head of the list:
Positions: 2, 3, 4, ...
They will be followed by low (normal) priority channels.

High-priority channels must be set using this command:
    /chanpriority [#channels]+

The argument must be a list of channels separated by commas, e.g.:
    /chanpriority #chan1, #chan2, #chan3

Channels can also be set using the format: network.#channel:
    /chanpriority #chan1, freenode.#weechat, network.org.#channel

LICENSE:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import weechat

SCRIPT_COMMAND = "chanpriority"
SCRIPT_AUTHOR = "Paul Barbu Gh. <paullik.paul@gmail.com>"
SCRIPT_VERSION = "0.4"
SCRIPT_NAME = "chanpriority"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Allows you to set high-priority channels, see /help chanpriority"

whitelist = []

def reorder_buffers():
    """Reorders the buffers once the whitelist has changed
    """

    count = 2
    chan = ""

    ilist = weechat.infolist_get("buffer", "", "")

    for chan in whitelist:
        if -1 == chan.find(".#"): #network name is not set, matching by short_name
            weechat.infolist_reset_item_cursor(ilist)

            while weechat.infolist_next(ilist):
                if weechat.infolist_string(ilist, "short_name") == chan:
                    chan = weechat.infolist_string(ilist, "name")
                    break

        buff = weechat.buffer_search("irc", chan)

        if buff:
            weechat.buffer_set(buff, "number", str(count))
            count += 1

    weechat.infolist_free(ilist)

    return weechat.WEECHAT_RC_OK

def get_whitelist(data, option, value):
    """Assign the config values of the whitelist option to the whitelist global
    """

    global whitelist

    t = weechat.config_get_plugin("whitelist")
    whitelist = t.split(",")

    reorder_buffers()

    return weechat.WEECHAT_RC_OK

def set_whitelist(data, option, value):
    """Sets the config directive whitelist
    """
    chanlist = ""

    t = value.replace(' ', '').split(",")
    for chan in t:
        if 2 <= len(chan) and ("#" == chan[0] or "#" == chan[chan.find(".#")+1]):
            chanlist = chanlist + chan + ","

    chanlist=chanlist[:-1] #remove the trailing comma

    weechat.config_set_plugin("whitelist", chanlist)
    weechat.prnt("", "Chanpriority list set to: '{0}'".format(chanlist))

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, "", ""):

    if not weechat.config_is_set_plugin("whitelist"):
        weechat.config_set_plugin("whitelist", "")
    else:
        get_whitelist("", "", "")

def on_join(data, signal, signal_data):
    """Used as callback, called when you join a channel

    If the channel joined is in the whitelist then its buffer will be prioritized
    """

    (chan, network, buffer) = join_meta(data, signal, signal_data)

    if network + "." + chan in whitelist or chan in whitelist:
        weechat.buffer_set(buffer, "number", "2")

    return weechat.WEECHAT_RC_OK

def join_meta(data, signal, signal_data):
    """Get meta info about the JOIN command

    @return a tuple containing the channel and the server joined, the buffer
    that will be opened after joining
    """

    chan = signal_data.rpartition(":")[-1]
    network = signal.partition(",")[0]
    buffer = weechat.buffer_search("irc", network + "." + chan)

    return (chan, network, buffer)

weechat.hook_signal("*,irc_in2_join", "on_join", "data")
weechat.hook_config("plugins.var.python.chanpriority.whitelist",
"get_whitelist", "")

weechat.hook_command(SCRIPT_COMMAND, "Set channel priority", "[#channels]+",
"""When joining channels the buffers will be arranged from high to low priority.
Buffers containing high-priority channels will be in the head of the list:
Positions: 2, 3, 4, ...
They will be followed by low (normal) priority channels.

High-priority channels must be set using this command:
    /chanpriority [#channels]+

The argument must be a list of channels separated by commas, e.g.:
    /chanpriority #chan1, #chan2, #chan3

Channels can also be set using the format: network.#channel:
    /chanpriority #chan1, freenode.#weechat, network.org.#channel

LICENSE: GPL v3

Based on the idea of Flavius Aspra <flavius.as@gmail.com>
""", "", "set_whitelist", "")
