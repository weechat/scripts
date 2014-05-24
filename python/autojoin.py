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
# 2009-10-18, LBo <leon@tim-online.nl>
#     version 0.2: added autosaving of join channels
#     /set plugins.var.python.autojoin.autosave 'on'
#
# 2009-10-19, LBo <leon@tim-online.nl>
#     version 0.2.1: now only responds to part messages from self
#     find_channels() only returns join'ed channels, not all the buffers
#     updated description and docs
#
# 2009-10-20, LBo <leon@tim-online.nl>
#     version 0.2.2: fixed quit callback
#     removed the callbacks on part & join messages
#
# 2012-04-14, Filip H.F. "FiXato" Slagter <fixato+weechat+autojoin@gmail.com>
#     version 0.2.3: fixed bug with buffers of which short names were changed.
#                    Now using 'name' from irc_channel infolist.
#     version 0.2.4: Added support for key-protected channels
#
# 2014-05-22, Nathaniel Wesley Filardo <PADEBR2M2JIQN02N9OO5JM0CTN8K689P@cmx.ietfng.org>
#     version 0.2.5: Fix keyed channel support
#
# @TODO: add options to ignore certain buffers
# @TODO: maybe add an option to enable autosaving on part/join messages

import weechat as w
import re

SCRIPT_NAME    = "autojoin"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Configure autojoin for all servers according to currently joined channels"
SCRIPT_COMMAND = "autojoin"

# script options
settings = {
    "autosave": "off",
}

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):

    w.hook_command(SCRIPT_COMMAND,
                   SCRIPT_DESC,
                   "[--run]",
                   "   --run: actually run the commands instead of displaying\n",
                   "--run",
                   "autojoin_cb",
                   "")

    #w.hook_signal('*,irc_in2_join', 'autosave_channels_on_activity', '')
    #w.hook_signal('*,irc_in2_part', 'autosave_channels_on_activity', '')
    w.hook_signal('quit',           'autosave_channels_on_quit', '')

# Init everything
for option, default_value in settings.items():
    if w.config_get_plugin(option) == "":
        w.config_set_plugin(option, default_value)

def autosave_channels_on_quit(signal, callback, callback_data):
    ''' Autojoin current channels '''
    if w.config_get_plugin(option) != "on":
        return w.WEECHAT_RC_OK

    items = find_channels()

    # print/execute commands
    for server, channels in items.iteritems():
        channels = channels.rstrip(',')
        command = "/set irc.server.%s.autojoin '%s'" % (server, channels)
        w.command('', command)

    return w.WEECHAT_RC_OK


def autosave_channels_on_activity(signal, callback, callback_data):
    ''' Autojoin current channels '''
    if w.config_get_plugin(option) != "on":
        return w.WEECHAT_RC_OK

    items = find_channels()

    # print/execute commands
    for server, channels in items.iteritems():
        nick = w.info_get('irc_nick', server)

        pattern = "^:%s!.*(JOIN|PART) :?(#[^ ]*)( :.*$)?" % nick
        match = re.match(pattern, callback_data)

        if match: # check if nick is my nick. In that case: save
            channel = match.group(2)
            channels = channels.rstrip(',')
            command = "/set irc.server.%s.autojoin '%s'" % (server, channels)
            w.command('', command)
        else: # someone else: ignore
            continue

    return w.WEECHAT_RC_OK

def autojoin_cb(data, buffer, args):
    """Old behaviour: doesn't save empty channel list"""
    """In fact should also save open buffers with a /part'ed channel"""
    """But I can't believe somebody would want that behaviour"""
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
    """Return list of servers and channels"""
    #@TODO: make it return a dict with more options like "nicks_count etc."
    items = {}
    infolist = w.infolist_get('irc_server', '', '')
    # populate servers
    while w.infolist_next(infolist):
        items[w.infolist_string(infolist, 'name')] = ''

    w.infolist_free(infolist)

    # populate channels per server
    for server in items.keys():
        keys = []
        keyed_channels = []
        unkeyed_channels = []
        items[server] = '' #init if connected but no channels
        infolist = w.infolist_get('irc_channel', '',  server)
        while w.infolist_next(infolist):
            if w.infolist_integer(infolist, 'nicks_count') == 0:
                #parted but still open in a buffer: bit hackish
                continue
            if w.infolist_integer(infolist, 'type') == 0:
                key = w.infolist_string(infolist, "key")
                if len(key) > 0:
                    keys.append(key)
                    keyed_channels.append(w.infolist_string(infolist, "name"))
                else :
                    unkeyed_channels.append(w.infolist_string(infolist, "name"))
        items[server] = ','.join(keyed_channels + unkeyed_channels)
        if len(keys) > 0:
            items[server] += ' %s' % ','.join(keys)
        w.infolist_free(infolist)

    return items

