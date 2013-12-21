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

#
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2013-12-21, Sebastien Helleu <flashcode@flashtux.org>
#   version 0.5: fix parsing of INVITE message
# 2013-11-28, sakkemo <scajanus@gmail.com>
#   version 0.4: add whitelist for nicks/channels
# 2009-11-09, xt <xt@bash.no>
#   version 0.3: add ignore option for channels
# 2009-10-29, xt <xt@bash.no>
#   version 0.2: add ignore option
# 2009-10-28, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "autojoin_on_invite"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto joins channels when invited"

# script options
settings = {
        'whitelist_nicks': '', # comma separated list of nicks,
                               # overrides ignore_nicks
        'whitelist_channels': '', # comma separated list of channels,
                               # overrides ignore_channels
        'ignore_nicks': '', # comma separated list of nicks
                            #that we will not accept auto invite from
        'ignore_channels': '', # comma separated list of channels to not join
}

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_signal('*,irc_in2_invite', 'invite_cb', '')


def invite_cb(data, signal, signal_data):
    server = signal.split(',')[0] # EFNet,irc_in_INVITE
    channel = signal_data.split()[-1].lstrip(':') # :nick!ident@host.name INVITE yournick :#channel
    from_nick = re.match(':(?P<nick>.+)!', signal_data).groups()[0]

    if len(w.config_get_plugin('whitelist_nicks')) > 0 and len(w.config_get_plugin('whitelist_channels')) > 0: # if there's two whitelists, accept both
        if from_nick in w.config_get_plugin('whitelist_nicks').split(',') or channel in w.config_get_plugin('whitelist_channels').split(','):
            w.prnt('', 'Automatically joining %s on server %s, invitation from %s (whitelist).' \
                %(channel, server, from_nick))
            w.command('', '/quote -server %s JOIN %s' % (server, channel))
        else:
            w.prnt('', 'Ignoring invite from %s to channel %s. Neither inviter nor channel in whitelist.' %(from_nick, channel))

    elif len(w.config_get_plugin('whitelist_nicks')) > 0: # if there's a whitelist, accept nicks in it
        if from_nick in w.config_get_plugin('whitelist_nicks').split(','):
            w.prnt('', 'Automatically joining %s on server %s, invitation from %s (whitelist).' \
                %(channel, server, from_nick))
            w.command('', '/quote -server %s JOIN %s' % (server, channel))
        else:
            w.prnt('', 'Ignoring invite from %s to channel %s. Inviter not in whitelist.' %(from_nick, channel))

    elif len(w.config_get_plugin('whitelist_channels')) > 0: # if there's a whitelist, accept channels in it
        if channel in w.config_get_plugin('whitelist_channels').split(','):
            w.prnt('', 'Automatically joining %s on server %s, invitation from %s (whitelist).' \
                %(channel, server, from_nick))
            w.command('', '/quote -server %s JOIN %s' % (server, channel))
        else:
            w.prnt('', 'Ignoring invite from %s to channel %s. Channel not in whitelist.' %(from_nick, channel))

    else: # use the ignore lists to make the decision
        if from_nick in w.config_get_plugin('ignore_nicks').split(','):
            w.prnt('', 'Ignoring invite from %s to channel %s. Invite from ignored inviter.' %(from_nick, channel))
        elif channel in w.config_get_plugin('ignore_channels').split(','):
            w.prnt('', 'Ignoring invite from %s to channel %s. Invite to ignored channel.' %(from_nick, channel))
        else:
            w.prnt('', 'Automatically joining %s on server %s, invitation from %s.' \
                %(channel, server, from_nick))
            w.command('', '/quote -server %s JOIN %s' % (server, channel))

    return w.WEECHAT_RC_OK
