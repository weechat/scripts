# Copyright (c) 2015 by timss <timsateroy@gmail.com>
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

SCRIPT_NAME = 'lastfm2'
SCRIPT_AUTHOR = "timss <timsateroy@gmail.com>"
SCRIPT_VERSION = '0.2'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = "Sends latest played track for a Last.fm user to the current buffer"

SCRIPT_COMMAND = 'lastfm'
SCRIPT_HELP = \
"""Sends latest played track for a Last.fm user to the current buffer.

    /lastfm

By default, the script will use the username set in {SCRIPT_NAME} configuration:

    /set plugins.var.python.{SCRIPT_NAME}.user yourusername

In addition, an username may be specified as an argument:

    /lastfm anotherusername

The command which output will be sent to the buffer may be customized as well:

    /set plugins.var.python.{SCRIPT_NAME}.command I'm listening to {{track}}

Finally, the command when specifying another username can also be set:

    /set plugins.var.python.{SCRIPT_NAME}.command_arg {{user}} is litening to {{track}}

Inspiration and credit:
    - lastfm.py, Adam Saponara <saponara TA gmail TOD com>
    - lastfmnp.py, i7c <i7c AT posteo PERIOD de>
    - lastfmapi.py, Christophe De Troyer <christophe@call-cc.be>

""".format(SCRIPT_NAME=SCRIPT_NAME)

try:
    import weechat
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

import json

def init_config():
    """Set plugin options to defaults if not already done"""
    config = {
        'user': '',
        'command': '/me is listening to {track}',
        'command_arg': '{user} is listening to {track}',
        'api_key': 'ae51c9df97d4e90c35ffd302e987efd2',
        'api_url': 'https://ws.audioscrobbler.com/2.0/?method=user.getRecentTracks&user={user}&limit=1&api_key={api_key}&format=json',
        'timeout': '10000'
    }

    for option, default in config.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default)

def get_recent_track(data, command, rc, out, err):
    """Get last track played (artist - name)"""
    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt('', "Error with command '{}'".format(command))
    elif rc > 0:
        weechat.prnt('', "rc = {}".format(rc))

    try:
        data = json.loads(out)

        if 'error' in data:
            weechat.prnt('', "Last.fm API error: '{}'".format(data['message']))
        else:
            artist = data['recenttracks']['track'][0]['artist']['#text']
            name = data['recenttracks']['track'][0]['name']
            track = "{} - {}".format(artist, name)
            user = data['recenttracks']['@attr']['user'].lower()

            # print username or not, depending on config/arg
            if user == weechat.config_get_plugin('user').lower():
                cmd = weechat.config_get_plugin('command')
            else:
                cmd = weechat.config_get_plugin('command_arg')

            # format isn't picky, ignores {user} if not present
            cmd = cmd.format(user=user, track=track)

            weechat.command(weechat.current_buffer(), cmd)
    except (IndexError, KeyError):
        weechat.prnt('', "Error parsing Last.fm data")

    return weechat.WEECHAT_RC_OK

def lastfm_cmd(data, buffer, args):
    """Print last track played"""
    api_key = weechat.config_get_plugin('api_key')
    api_url = weechat.config_get_plugin('api_url')
    timeout = weechat.config_get_plugin('timeout')

    # use user in argument, or in config
    if args:
        user = args
    else:
        user = weechat.config_get_plugin('user')

    url = 'url:' + api_url.format(user=user.lower(), api_key=api_key)
    weechat.hook_process(url, int(timeout), 'get_recent_track', '')

    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        init_config()
        weechat.hook_command(SCRIPT_COMMAND, SCRIPT_HELP, '', '', '', 'lastfm_cmd', '')

