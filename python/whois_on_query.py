# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2012 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2011 Elián Hanisch <lambdae2@gmail.com>
# Copyright (C) 2011 ArZa <arza@arza.us>
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
# Send "whois" on nick when receiving (or opening) new IRC query.
# (this script requires WeeChat 0.3.2 or newer)
#
# History:
#
# 2017-05-28, Jos Ahrens <buughost@gmail.com>:
#     version 0.6.1: Corrected a typo in help description for option self_query
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: make script compatible with Python 3.x
# 2011-10-17, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: add option "self_query" to do whois on self query,
#       add help for options (WeeChat >= 0.3.5)
# 2011-07-06, ArZa <arza@arza.us>:
#     version 0.4: fix target buffer for command
# 2011-05-31, Elián Hanisch <lambdae2@gmail.com>:
#     version 0.3: depends on WeeChat 0.3.2
#       use irc_is_nick instead of irc_is_channel.
#       only /whois when somebody opens a query with you.
# 2009-05-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes
# 2009-02-08, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

SCRIPT_NAME    = 'whois_on_query'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.6.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Whois on query'

# script options
woq_settings_default = {
    'command'   : ('/whois $nick $nick', 'the command sent to do the whois ($nick is replaced by nick)'),
    'self_query': ('off', 'if on, send whois for self queries'),
}

irc_pv_hook = ''

def unhook_irc_pv():
    """Remove irc_pv hook."""
    global irc_pv_hook
    if irc_pv_hook:
        weechat.unhook(irc_pv_hook)
    irc_pv_hook = ''

def exec_command(buffer, nick):
    """Execute the whois command."""
    command = weechat.config_get_plugin('command').replace('$nick', nick)
    weechat.command(buffer, command)

def signal_irc_pv_opened(data, signal, signal_data):
    """Callback for signal 'irc_pv_opened'."""
    global irc_pv_hook
    if weechat.buffer_get_string(signal_data, 'plugin') == 'irc':
        nick = weechat.buffer_get_string(signal_data, 'localvar_channel')
        if weechat.info_get('irc_is_nick', nick) == '1':
            unhook_irc_pv()
            if weechat.config_get_plugin('self_query') == 'on':
                exec_command(signal_data, nick)
            else:
                # query open, wait for a msg to come (query was open by user) or if we send a msg out
                # (query was open by us)
                server = weechat.buffer_get_string(signal_data, 'localvar_server')
                irc_pv_hook = weechat.hook_signal('irc_pv', 'signal_irc_pv',
                                                  '%s,%s' % (signal_data, nick))
    return weechat.WEECHAT_RC_OK

def signal_irc_pv(data, signal, signal_data):
    """Callback for signal 'irc_pv'."""
    buffer, nick = data.split(',')
    if signal_data.startswith(':' + nick + '!'):
        # ok, run command
        exec_command(buffer, nick)
    unhook_irc_pv()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, '', ''):
        # set default settings
        version = weechat.info_get('version_number', '') or 0
        for option, value in woq_settings_default.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, value[0])
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

        # hook signal 'irc_pv_opened'
        weechat.hook_signal('irc_pv_opened', 'signal_irc_pv_opened', '')
