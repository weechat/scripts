# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by FlashCode <flashcode@flashtux.org>
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
# Send "whois" on nick when receiving new IRC query.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes
# 2009-02-08, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release
#

import weechat

SCRIPT_NAME    = "whois_on_query"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Whois on query"

# script options
settings = {
    "command": "/whois $nick $nick",
}

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                 SCRIPT_DESC, "", "")
weechat.hook_signal("irc_pv_opened", "signal_irc_pv_opened", "")
for option, default_value in settings.iteritems():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

def signal_irc_pv_opened(data, signal, signal_data):
    if weechat.buffer_get_string(signal_data, "plugin") == "irc":
        channel = weechat.buffer_get_string(signal_data, "localvar_channel")
        if weechat.info_get("irc_is_channel", channel) != "1":
            weechat.command(signal_data, weechat.config_get_plugin("command").replace("$nick", channel))
    return weechat.WEECHAT_RC_OK
