# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
# Copyright (c) 2009 by penryu <penryu@gmail.com>
# Copyright (c) 2010 by Blake Winton <bwinton@latte.ca>
# Copyright (c) 2010 by Aron Griffis <agriffis@n01se.net>
# Copyright (c) 2010 by Jani Kesänen <jani.kesanen@gmail.com>
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
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2014-08-02, Nils Görs <weechatter@arcor.de>
#  version 0.14: add time to detach message. (idea by Mikaela)
# 2014-06-19, Anders Bergh <anders1@gmail.com>
#  version 0.13: Fix a simple typo in an option description.
# 2014-01-12, Phyks (Lucas Verney) <phyks@phyks.me>
#  version 0.12: Added an option to check status of relays to set unaway in
#                   case of a connected relay.
# 2013-08-30, Anders Einar Hilden <hildenae@gmail.com>
#  version: 0.11: Fix reading of set_away
# 2013-06-16, Renato Botelho <rbgarga@gmail.com>
#  version 0.10: add option to don't set away, only change nick
#                   allow multiple commands on attach/dettach
#                   do not add suffix if nick already have it
# 2012-12-29, David Flatz <david@upcs.at>
#  version 0.9: add option to ignore servers and don't set away status for them
#               add descriptions to config options
# 2010-08-07, Filip H.F. "FiXato" Slagter <fixato@gmail.com>
#  version 0.8: add command on attach feature
# 2010-05-07, Jani Kesänen <jani.kesanen@gmail.com>
#  version 0.7: add command on detach feature
# 2010-03-07, Aron Griffis <agriffis@n01se.net>
#  version 0.6: move socket check to register,
#               add hook_config for interval,
#               reduce default interval from 60 to 5
# 2010-02-19, Blake Winton <bwinton@latte.ca>
#  version 0.5: add option to change nick when away
# 2010-01-18, xt
#  version 0.4: only update servers that are connected
# 2009-11-30, xt <xt@bash.no>
#  version 0.3: do not touch servers that are manually set away
# 2009-11-27, xt <xt@bash.no>
#  version 0.2: code for TMUX from penryu
# 2009-11-27, xt <xt@bash.no>
#  version 0.1: initial release

import weechat as w
import re
import os
import datetime, time

SCRIPT_NAME    = "screen_away"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.14"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set away status on screen detach"

settings = {
        'message': ('Detached from screen', 'Away message'),
        'time_format': ('since %Y-%m-%d %H:%M:%S%z', 'time format append to away message'),
        'interval': ('5', 'How often in seconds to check screen status'),
        'away_suffix': ('', 'What to append to your nick when you\'re away.'),
        'command_on_attach': ('', 'Commands to execute on attach, separated by semicolon'),
        'command_on_detach': ('', 'Commands to execute on detach, separated by semicolon'),
        'ignore': ('', 'Comma-separated list of servers to ignore.'),
        'set_away': ('on', 'Set user as away.'),
        'ignore_relays': ('off', 'Only check screen status and ignore relay interfaces'),
}

TIMER = None
SOCK = None
AWAY = False
CONNECTED_RELAY = False

def set_timer():
    '''Update timer hook with new interval'''

    global TIMER
    if TIMER:
        w.unhook(TIMER)
    TIMER = w.hook_timer(int(w.config_get_plugin('interval')) * 1000,
            0, 0, "screen_away_timer_cb", '')

def screen_away_config_cb(data, option, value):
    if option.endswith(".interval"):
        set_timer()
    return w.WEECHAT_RC_OK

def get_servers():
    '''Get the servers that are not away, or were set away by this script'''

    ignores = w.config_get_plugin('ignore').split(',')
    infolist = w.infolist_get('irc_server','','')
    buffers = []
    while w.infolist_next(infolist):
        if not w.infolist_integer(infolist, 'is_connected') == 1 or \
               w.infolist_string(infolist, 'name') in ignores:
            continue
        if not w.config_string_to_boolean(w.config_get_plugin('set_away')) or \
                not w.infolist_integer(infolist, 'is_away') or \
                    w.config_get_plugin('message') in w.infolist_string(infolist, 'away_message'):
#                    w.infolist_string(infolist, 'away_message') == \
#                    w.config_get_plugin('message'):
            buffers.append((w.infolist_pointer(infolist, 'buffer'),
                w.infolist_string(infolist, 'nick')))
    w.infolist_free(infolist)
    return buffers

def screen_away_timer_cb(buffer, args):
    '''Check if screen is attached, update awayness'''

    global AWAY, SOCK, CONNECTED_RELAY

    set_away = w.config_string_to_boolean(w.config_get_plugin('set_away'))
    check_relays = not w.config_string_to_boolean(w.config_get_plugin('ignore_relays'))
    suffix = w.config_get_plugin('away_suffix')
    attached = os.access(SOCK, os.X_OK) # X bit indicates attached

    # Check wether a client is connected on relay or not
    CONNECTED_RELAY = False
    if check_relays:
        infolist = w.infolist_get('relay', '', '')
        if infolist:
            while w.infolist_next(infolist):
                status = w.infolist_string(infolist, 'status_string')
                if status == 'connected':
                    CONNECTED_RELAY = True
                    break
            w.infolist_free(infolist)

    if (attached and AWAY) or (check_relays and CONNECTED_RELAY and not attached and AWAY):
        w.prnt('', '%s: Screen attached. Clearing away status' % SCRIPT_NAME)
        for server, nick in get_servers():
            if set_away:
                w.command(server,  "/away")
            if suffix and nick.endswith(suffix):
                nick = nick[:-len(suffix)]
                w.command(server,  "/nick %s" % nick)
        AWAY = False
        for cmd in w.config_get_plugin("command_on_attach").split(";"):
            w.command("", cmd)

    elif not attached and not AWAY:
        if not CONNECTED_RELAY:
            w.prnt('', '%s: Screen detached. Setting away status' % SCRIPT_NAME)
            for server, nick in get_servers():
                if suffix and not nick.endswith(suffix):
                    w.command(server, "/nick %s%s" % (nick, suffix));
                if set_away:
                    w.command(server, "/away %s %s" % (w.config_get_plugin('message'), time.strftime(w.config_get_plugin('time_format'))))
            AWAY = True
            for cmd in w.config_get_plugin("command_on_detach").split(";"):
                w.command("", cmd)

    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    version = w.info_get('version_number', '') or 0
    for option, default_desc in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_desc[0])
        if int(version) >= 0x00030500:
            w.config_set_desc_plugin(option, default_desc[1])

    if 'STY' in os.environ.keys():
        # We are running under screen
        cmd_output = os.popen('env LC_ALL=C screen -ls').read()
        match = re.search(r'Sockets? in (/.+)\.', cmd_output)
        if match:
            SOCK = os.path.join(match.group(1), os.environ['STY'])

    if not SOCK and 'TMUX' in os.environ.keys():
        # We are running under tmux
        socket_data = os.environ['TMUX']
        SOCK = socket_data.rsplit(',',2)[0]

    if SOCK:
        set_timer()
        w.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
            "screen_away_config_cb", "")
