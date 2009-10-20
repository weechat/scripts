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
#
# 2009-06-18, LBo <leon@tim-online.nl>
#     version 0.2: added autosaving of join channels
#     /set plugins.var.python.autojoin.autosave 'on'
#
# @TODO: find_channels() also returns channels which are already /part'ed but
#        are still in a buffer
# @TODO: plugin responds to all part messages, not only from self

import weechat as w

SCRIPT_NAME    = "autojoin"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Configure autojoin for all servers according to currently joined channels"
SCRIPT_COMMAND = "autojoin"

# script options
settings = {
    "autosave": "off",
}

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    # Init everything
    for option, default_value in settings.items():
        if w.config_get_plugin(option) == "":
            w.config_set_plugin(option, default_value)
    
    w.hook_command(SCRIPT_COMMAND,
                   SCRIPT_DESC,
                   "[--run]",
                   "   --run: actually run the commands instead of displaying\n",
                   "--run",
                   "autojoin_cb",
                   "")
    
    w.hook_signal('*,irc_in2_join', 'autosave_autojoin_channels', '')
    w.hook_signal('*,irc_in2_part', 'autosave_autojoin_channels', '')
    w.hook_signal('*,irc_in2_quit', 'autosave_autojoin_channels', '')
    w.hook_signal('quit',           'autosave_autojoin_channels', '')

def autosave_autojoin_channels(data, buffer, args):
    ''' Autojoin current channels '''
    if w.config_get_plugin("autosave") != "on":
        return w.WEECHAT_RC_OK
    items = find_channels()
    
    # print/execute commands
    for server, channels in items.iteritems():
        channels = channels.rstrip(',')
        command = "/set irc.server.%s.autojoin '%s'" % (server, channels)
        w.command('', command)
    
    return w.WEECHAT_RC_OK

def autojoin_cb(data, buffer, args):
    """Old behaviour: doesn't save empty channel list"""
    items = find_channels()
    
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

def find_channels():
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
    
    return items
