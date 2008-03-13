#
# Copyright (c) 2006 by Olivier Bornet <Olivier.Bornet@puck.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

# WeeChat python script for auto-join on invite

import weechat

MYNAME = 'auto_invite'

weechat.register (MYNAME, '0.1', 'wpyend', 'WeeChat auto-join on invite')

# a message handler
weechat.add_message_handler ('invite', 'join_on_invite')

def join_on_invite (server, args):
    '''Join the channel on invite message'''

    # the arguments are like: ':from_nick!~user@his.host INVITE my_nick :#CHANNEL'
    from_nick, dummy, to_nick, channel = args.split ()
    from_nick = from_nick [1:].split ('!') [0]
    channel = channel [1:]

    # a small debug
    weechat.prnt ('%s invite %s to %s' % (from_nick, to_nick, channel))

    # join the channel
    weechat.command ('/join %s' % channel, '', server)

    # OK. :)
    return weechat.PLUGIN_RC_OK

def wpyend ():
    weechat.prnt ('%s: unloaded.' % MYNAME)
    return weechat.PLUGIN_RC_OK

