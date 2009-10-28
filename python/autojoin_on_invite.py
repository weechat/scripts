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
# 2009-10-28, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "autojoin_on_invite"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto joins channels when invited"


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    w.hook_signal('*,irc_in2_invite', 'invite_cb', '')


def invite_cb(data, signal, signal_data):
    server = signal.split(',')[0] # EFNet,irc_in_INVITE
    channel = signal_data.split(':')[-1] # :nick!ident@host.name INVITE yournick :#channel
    w.command('', '/quote -server %s JOIN %s' % (server, channel))
    w.prnt('', 'Automatically joining %s on server %s' %(channel, server))
    
    return w.WEECHAT_RC_OK
