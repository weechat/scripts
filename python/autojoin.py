''' Autojoin current channels '''
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
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

# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-18, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w

SCRIPT_NAME    = "autojoin"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Configure autojoin for all servers according to currently joined channels"
SCRIPT_COMMAND = "autojoin"

def autojoin_cb(data, buffer, args):

    items = {}
    infolist = w.infolist_get('irc_server', '', '')
    # populate servers
    while w.infolist_next(infolist):
        items[w.infolist_string(infolist, 'name')] = ''

    w.infolist_free(infolist)

    # populate channels per server
    for server in items.keys():
        infolist = w.infolist_get('irc_channel', '',  server)
        while w.infolist_next(infolist):
            if w.infolist_integer(infolist, 'type') == 0:
                channel = w.infolist_string(infolist, "buffer_short_name")
                items[server] += '%s,' %channel
        w.infolist_free(infolist)

    # print/execute commands
    for server, channels in items.iteritems():
        channels = channels.rstrip(',')
        if not channels: # empty channel list
            continue
        command = '/set irc.server.%s.autojoin %s' % (server, channels)
        if args == '--run':
            w.command('', command)
        else:
            w.prnt('', command)

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):

    w.hook_command(SCRIPT_COMMAND,
                   SCRIPT_DESC,
                   "[--run]",
                   "   --run: actually run the commands instead of displaying\n",
                   "--run",
                   "autojoin_cb",
                   "")
