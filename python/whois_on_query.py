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
# (this script requires WeeChat 0.3.2 or newer)
#
# History:
#
# 2011-05-31, Elián Hanisch <lambdae2@gmail.com>:
#     version 0.3: depends on WeeChat 0.3.2
#       use irc_is_nick instead of irc_is_channel.
#       only /whois when somebody opens a query with you.
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes
# 2009-02-08, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release
#

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

SCRIPT_NAME    = "whois_on_query"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Whois on query"

# script options
settings = {
    "command": "/whois $nick $nick",
}

irc_pv_hook = irc_out_hook = ''
def unhook_all():
    global irc_pv_hook, irc_out_hook
    if irc_pv_hook:
        weechat.unhook(irc_pv_hook)
    if irc_out_hook:
        weechat.unhook(irc_out_hook)
    irc_pv_hook = irc_out_hook = ''

def signal_irc_pv_opened(data, signal, signal_data):
    global irc_pv_hook, irc_out_hook
    if weechat.buffer_get_string(signal_data, "plugin") == "irc":
        channel = weechat.buffer_get_string(signal_data, "localvar_channel")
        if weechat.info_get("irc_is_nick", channel) == "1":
            # query open, wait for a msg to come (query was open by user) or if we send a msg out
            # (query was open by us)
            unhook_all()
            server = weechat.buffer_get_string(signal_data, "localvar_server")
            irc_pv_hook = weechat.hook_signal("irc_pv", "signal_irc_pv", channel)
            irc_out_hook = weechat.hook_signal(server + ",irc_out_PRIVMSG", "signal_irc_out", '')
    return weechat.WEECHAT_RC_OK

def signal_irc_pv(data, signal, signal_data):
    if signal_data.strip(':').startswith(data):
        # ok, run command
        command = weechat.config_get_plugin("command").replace("$nick", data)
        weechat.command(signal_data, command)
    unhook_all()
    return weechat.WEECHAT_RC_OK

def signal_irc_out(data, signal, signal_data):
    unhook_all()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
            weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
                             SCRIPT_DESC, '', ''):

    weechat.hook_signal("irc_pv_opened", "signal_irc_pv_opened", "")

    for option, default_value in settings.iteritems():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value)

