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

import weechat, subprocess, re

SCRIPT_COMMAND = 'memon'
SCRIPT_AUTHOR = 'Paul Barbu - Gheorghe <paullik.paul@gmail.com>'
SCRIPT_VERSION = '0.3'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Freenode memo notifications, see /help memon'

MEMOSERVICE = 'MemoServ!MemoServ@services'

new_memo_from = re.compile('.+:You have a new memo from');
connect_memo = re.compile('.+:You have \d+ new memo')

state = None
time = '5000'

def set_args(data, buffer, args):
    """On user's command switch the script on or off and set the time a
    notification is displayed
    """
    global state
    global time

    if 'on' == args or '' == args or args is None:
        weechat.config_set_plugin('state', 'on')
        state = 1
    elif 'off' == args:
        weechat.config_set_plugin('state', 'off')
        state = 0
    elif 't' == args.split(' ')[0] or 'time' == args.split(' ')[0]:
        time = args.split(' ')[1]
        weechat.config_set_plugin('time', time)

    return weechat.WEECHAT_RC_OK

def get_state(data, buffer, args):
    """Get the state of the script from the configuration file
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

def get_time(data, buffer, args):
    """Get the expiry time in milliseconds a notification should be dismissed
    after
    """
    global time

    cfg_time = weechat.config_get_plugin('time')

    if None == cfg_time or '' == cfg_time:
        weechat.config_set_plugin('time', time)
    else:
        time = cfg_time

    return weechat.WEECHAT_RC_OK

def notify(data, signal, signal_data):
    if state and MEMOSERVICE in signal_data:
        if new_memo_from.match(signal_data) or connect_memo.match(signal_data):
            msg = signal_data.rpartition(':')[2]

            subprocess.call(['/usr/bin/notify-send', 'MemoN', '{0}'.format(msg), '-t', time], shell=False)

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_COMMAND, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, '', ''):
    get_state('', '', '')
    get_time('', '', '')

weechat.hook_config('plugins.var.python.' + SCRIPT_COMMAND + '.state', 'get_state', '')
weechat.hook_config('plugins.var.python.' + SCRIPT_COMMAND + '.time', 'get_time', '')
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
""", '[on|off] | [t|time <expiry-time>]',
"""on - you get notifications on new memos
off - plugin disabled
t or time - allows you to set the duration of a notification in milliseconds, so
    if you want a notification to be displayed for 3 seconds you should write: /memon t 3000
    the default duration is 5 seconds (5000 ms)
""", 'on'
' || off'
' || time|t', 'set_args', '')
