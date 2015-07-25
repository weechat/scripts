# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2014 Germain Z. <germanosz@gmail.com>
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

import weechat


# Script info.
# ============

SCRIPT_NAME = "hatwidget"
SCRIPT_AUTHOR = "GermainZ <germanosz@gmail.com>"
SCRIPT_VERSION = "1.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = ("Shows hats (user modes like @ or +) in a handy bar item.")


# Callbacks.
# ==========

# Signals.
# --------

def cb_buffer_switch(data, signal, signal_data):
    weechat.bar_item_update("hats")
    return weechat.WEECHAT_RC_OK

def cb_irc_mode(data, buff, date, tags, displayed, highlight, prefix, message):
    weechat.bar_item_update("hats")
    return weechat.WEECHAT_RC_OK

# def cb_irc_mode_actual(data, remaining_calls):
    # return weechat.WEECHAT_RC_OK

# Bar items.
# ----------

def cb_hats(data, item, window):
    buf = weechat.current_buffer()
    plugin = weechat.buffer_get_string(buf, "localvar_plugin")
    if plugin == "irc":
        server = weechat.buffer_get_string(buf, "localvar_server")
        channel = weechat.buffer_get_string(buf, "localvar_channel")
        nick = weechat.buffer_get_string(buf, "localvar_nick")
        nicks = weechat.infolist_get("irc_nick", "", "{},{},{}".format(
            server, channel, nick))
        weechat.infolist_next(nicks)
        hats = weechat.infolist_string(nicks, "prefixes")
        weechat.infolist_free(nicks)
        return hats.replace(" ", "")
    return ""


# Main script.
# ============

if __name__ == "__main__":
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                     SCRIPT_LICENSE, SCRIPT_DESC, "", "")
    # Create bar items and setup hooks.
    weechat.bar_item_new("hats", "cb_hats", "")
    weechat.hook_print("", "irc_mode", "", 0, "cb_irc_mode", "")
    weechat.hook_signal("buffer_switch", "cb_buffer_switch", "")
