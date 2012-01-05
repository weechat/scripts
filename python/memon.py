"""Freenode memo notifications

If the user receives a memo on freenode a little notification window will apear

Requires libnotify!

Author: Barbu Paul - Gheorghe <paullik.paul@gmail.com>

LICENSE:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import weechat, subprocess

SCRIPT_COMMAND = 'memon'
SCRIPT_AUTHOR = 'Paul Barbu - Gheorghe <paullik.paul@gmail.com>'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Freenode memo notifications, see /help memon'

MEMOSERVICE = 'MemoServ!MemoServ@services'

state = None

def switch(data, buffer, args):
    """On user's command switch the script on or off
    """
    global state

    if 'on' == args or '' == args or args is None:
        weechat.config_set_plugin('state', 'on')
        state = 1
    else:
        weechat.config_set_plugin('state', 'off')
        state = 0

    return weechat.WEECHAT_RC_OK

def get_state(data, buffer, args):
    """Get the state of the scrit from the configuration file
    """
    global state

    cfg_state = weechat.config_get_plugin('state')

    if cfg_state is None or 'on' == cfg_state:
        weechat.config_set_plugin('state', 'on')
        state = 1
    else:
        state = 0
        weechat.config_set_plugin('state', 'off')

    return weechat.WEECHAT_RC_OK

def notify(data, signal, signal_data):
    if state and MEMOSERVICE in signal_data:
        msg = signal_data.rpartition(':')[2]

        subprocess.call(['/usr/bin/notify-send', 'MemoN', '{0}'.format(msg), '-t', '2000'], shell=False)

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_COMMAND, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, '', ''):
    get_state('', '', '');

weechat.hook_config('plugins.var.python.' + SCRIPT_COMMAND + '.state', 'get_state', '')
weechat.hook_signal('*,irc_in2_notice', 'notify', '')

weechat.hook_command(SCRIPT_COMMAND,
"""Freenode memo notifications

If the user receives a memo a little notification window will apear

Requires libnotify!

Author: Barbu Paul - Gheorghe <paullik.paul@gmail.com>

LICENSE:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
""", '[on|off]',
"""on - you get notifications on new memos
off - plugin disabled
""", 'on|off', 'switch', '')
