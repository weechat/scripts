#
# Copyright (c) 2009 by Benjamin Neff <info@benjaminneff.ch>
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

# moc control and now playing script for Weechat.
# (this script requires WeeChat 0.3.0 (or newer) and moc)
#
# History:
#
# 2020-06-21, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.9: make call to bar_new compatible with WeeChat >= 2.9
# 2019-10-16, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.8: - add python 3 support
# 2009-10-26, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.7.3: - Bugfix ( "/me" --> "output_nothing" ) 2
# 2009-10-25, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.7.2: - Fix if moc isn't running
# 2009-10-24, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.7.1: - Bugfix ( "/me" --> "output_nothing" )
# 2009-10-16, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.7: - AvgBitrate bug
#                  - format Time
# 2009-09-15, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.6: - bugfixing ;-)
#                  - hook_config
#                  - remove i|o|ot (color-bug)
# 2009-09-08, Benjamin Neff <info@benjaminneff.ch>:
#     version 1.5: initial release / port to weechat 0.3.0
#

from __future__ import print_function

SCRIPT_NAME    = "moc_control"
SCRIPT_AUTHOR  = "SuperTux88 (Benjamin Neff) <info@benjaminneff.ch>"
SCRIPT_VERSION = "1.9"
SCRIPT_LICENSE = "GPL2"
SCRIPT_DESC    = "moc control and now playing script for Weechat"

SCRIPT_COMMAND = "moc"

import_ok      = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

try:
    import os
    import subprocess
    import traceback
except ImportError as message:
    print('Missing package(s) for {}: {}'.format(SCRIPT_NAME, message))
    import_ok = False

# =================================[ config ]=================================

infobar        = {}
output         = {}

STATUS_NOT_RUNNING = 'NOT_RUNNING'
STATUS_PLAYING     = 'PLAY'
STATUS_PAUSED      = 'PAUSE'
STATUS_STOPPED     = 'STOP'

def load_settings(data, option, value):
    """load all settings"""
    infobar['enabled'] = _load_setting('infobar_enabled', 'off', 'bool')
    infobar['format']  = _load_setting('infobar_format', 'Now Playing: %mocTitle%')
    infobar['update']  = _load_setting('infobar_update', '10', 'int')
    output['format']   = _load_setting('output_format', '/me is listening to %C04%title%%C %artist%%album%::: %C07%file%%C ::: %cTime%/%tTime% @ %bitrate%')
    output['artist']   = _load_setting('output_format_artist', '- %C03%artist%%C ')
    output['album']    = _load_setting('output_format_album', '(%C12%album%%C) ')
    output['nothing']  = _load_setting('output_nothing', '/me is listening to nothing')

    #update config for 1.6 (i|o|ot -> +/me)
    if weechat.config_is_set_plugin('output_type'):
        if weechat.config_get_plugin('output_type') == 'ot':
            weechat.config_set_plugin('output_format', "/me " + output['format'])
            weechat.config_set_plugin('output_nothing', "/me " + output['nothing'])
            output['format'] = "/me " + output['format']
            output['nothing'] = "/me " + output['nothing']
        weechat.config_unset_plugin('output_type')

    return weechat.WEECHAT_RC_OK

def _load_setting(setting, default=None, type=None):
    """load setting or create it"""
    value = weechat.config_get_plugin(setting)
    if value == '' and default != None:
        weechat.config_set_plugin(setting, default)
        value = default

    if type == 'int':
        value = int(value)

    if type == 'bool':
        if value == "on":
            value = True
        elif value == "off":
            value = False
        else:
            weechat.config_set_plugin(setting, default)
            if default == "on":
                value = True
            elif default == "off":
                value = False

    return value

# ================================[ command ]=================================

def moc_command(data, buffer, args):
    """run command"""
    args = args.split(' ')
    if args[0] == '':
        return moc_now_playing(buffer)

    elif args[0] == 'pause' or args[0] == 'pp':
        if _get_status() == STATUS_STOPPED:
            weechat.prnt(buffer, 'moc: Not playing')
            return weechat.WEECHAT_RC_OK
        else:
            _execute_command('mocp -G')
            weechat.prnt(buffer, 'moc: Song paused / Continue playing')
            return weechat.WEECHAT_RC_OK
    elif args[0] == 'play':
        if _get_status() == STATUS_PLAYING:
            weechat.prnt(buffer, 'moc: Already playing')
            return weechat.WEECHAT_RC_OK
        elif _get_status() == STATUS_PAUSED:
            _execute_command('mocp -U')
            weechat.prnt(buffer, 'moc: Continue playing.')
            return weechat.WEECHAT_RC_OK
        else:
            _execute_command('mocp -p')
            weechat.prnt(buffer, 'moc: Started playing.')
            return weechat.WEECHAT_RC_OK
    elif args[0] == 'stop':
        _execute_command('mocp -s')
        weechat.prnt(buffer, 'moc: Stop playing.')
        return weechat.WEECHAT_RC_OK
    elif args[0] == 'prev':
        if _get_status() == STATUS_STOPPED:
            weechat.prnt(buffer, 'moc: Not playing, cannot go to previous song.')
            return weechat.WEECHAT_RC_OK
        else:
            _execute_command('mocp -r')
            weechat.prnt(buffer, 'moc: Playing previous song.')
            return weechat.WEECHAT_RC_OK
    elif args[0] == 'next':
        if _get_status() == STATUS_STOPPED:
            weechat.prnt(buffer, 'moc: Not playing, cannot go to next song.')
            return weechat.WEECHAT_RC_OK
        else:
            _execute_command('mocp -f')
            weechat.prnt(buffer, 'moc: Playing next song.')
            return weechat.WEECHAT_RC_OK
    elif args[0] == 'infobar':
        if infobar['enabled']:
            infobar['enabled'] = False
            weechat.config_set_plugin('infobar_enabled', 'off')
            _remove_infobar()
        else:
            infobar['enabled'] = True
            weechat.config_set_plugin('infobar_enabled', 'on')
            _add_infobar()
        return weechat.WEECHAT_RC_OK
    elif args[0] == 'help':
        weechat.command(buffer, '/help moc')
        return weechat.WEECHAT_RC_OK
    else:
        weechat.prnt(buffer, 'moc: Unknown command %s' % (args[0]))
        return weechat.WEECHAT_RC_OK

# ================================[ infobar ]=================================

def moc_infobar_update(data, buffer, args):
    """Callback for the bar item"""
    if _get_status() == STATUS_NOT_RUNNING:
        return 'moc is not running'
    if _get_status() == STATUS_STOPPED:
        return 'moc is not currently playing'
    else:
        song = _get_song_info()
        return _format_np(infobar['format'], song, 'infobar')

def moc_infobar_updater(data,cals):
    """Update the bar item"""
    if infobar['enabled']:
        weechat.bar_item_update('moc_infobar')
    return weechat.WEECHAT_RC_OK

def _add_infobar():
    """add the infobar for moc_control"""
    version = int(weechat.info_get('version_number', '')) or 0
    if version >= 0x02090000:
        weechat.bar_new(SCRIPT_NAME, "off", "750", "window", "", "bottom", "horizontal", "vertical", "1", "0", "default", "blue", "cyan", "cyan", "off", "[moc_infobar]")
    else:
        weechat.bar_new(SCRIPT_NAME, "off", "750", "window", "", "bottom", "horizontal", "vertical", "1", "0", "default", "blue", "cyan", "off", "[moc_infobar]")

def _remove_infobar():
    """remove the infobar for moc_control"""
    weechat.bar_remove(weechat.bar_search(SCRIPT_NAME))

# ==============================[ now playing ]===============================

def moc_now_playing(buffer):
    """print now playing"""
    format = ''

    status = _get_status()
    if status == STATUS_STOPPED or status == STATUS_NOT_RUNNING:
        format = output['nothing']
    else:
        song = _get_song_info()
        format = _format_np(output['format'], song, 'chat')

    weechat.command(buffer, format)

    return weechat.WEECHAT_RC_OK

def _format_np(np, song, npType):
    """format the 'now Playing'-String"""
    np = np.replace('%mocTitle%', song['Title'])
    np = np.replace('%title%', song['SongTitle'])

    if npType == 'chat':
        if song['Artist'] != 'unknown':
            np = np.replace('%artist%', output['artist'])
            np = np.replace('%artist%', song['Artist'])
        else:
            np = np.replace('%artist%', '')

        if song['Album'] != 'unknown':
            np = np.replace('%album%', output['album'])
            np = np.replace('%album%', song['Album'])
        else:
            np = np.replace('%album%', '')
    else:
        np = np.replace('%artist%', song['Artist'])
        np = np.replace('%album%', song['Album'])

    np = np.replace('%cTime%', song['CurrentTime'])
    np = np.replace('%cSec%', song['CurrentSec'])
    np = np.replace('%tTime%', song['TotalTime'])
    np = np.replace('%tSec%', song['TotalSec'])
    np = np.replace('%bitrate%', song['Bitrate'])
    np = np.replace('%avgBitrate%', song['AvgBitrate'])
    np = np.replace('%rate%', song['Rate'])
    np = np.replace('%file%', song['File'])
    np = np.replace('%C', chr(3))

    if _get_status() == STATUS_PAUSED:
        np = np + " - [PAUSED]"

    return np

def _get_song_info():
    """Get the song information from moc"""
    song = {}
    song['TotalSec'] = '??'
    song['AvgBitrate'] = '???Kbps'

    info = _execute_command('mocp -i')
    for line in info.split('\n'):
        if line != '':
            index = line.find(': ')
            name = line[:index]
            value = line[index+2:]
            if value == '':
                value = 'unknown'
            song[name] = value.strip()

    if song['File'].find("://") < 0:
        song['File'] = os.path.basename(song['File'])

    if song['TotalSec'] == '??':
        song['TotalTime'] = '?:??'
    else:
        if song['TotalTime'].find("m") > 0:
            song['TotalTime'] = _format_seconds(song['TotalSec'])

    if song['CurrentTime'].find("m") > 0:
        song['CurrentTime'] = _format_seconds(song['CurrentSec'])

    return song

def _format_seconds(s):
    """return the formated time"""
    s = int(s)
    temp = float()
    temp = float(s) / (60 * 60 * 24)
    d = int(temp)
    temp = (temp - d) * 24
    h = int(temp)
    temp = (temp - h) * 60
    m = int(temp)
    temp = (temp - m) * 60
    sec = temp
    if d > 0:
        return "%id %i:%02i:%02i" % (d, h, m, sec)
    else:
        return "%i:%02i:%02i" % (h, m, sec)

def _get_status():
    """return the Status of moc"""
    return _execute_command('mocp -i | grep "State:" | cut -d " " -f 2').strip()

def _execute_command(cmd):
    """execute a command"""
    from subprocess import PIPE
    proc = subprocess.Popen(cmd, shell = True, stderr = PIPE, stdout = PIPE, close_fds = True)
    error = proc.stderr.read().decode('utf-8')
    if error != '':
        for line in error.split('\n'):
            if line == 'FATAL_ERROR: The server is not running':
                return STATUS_NOT_RUNNING

    output = proc.stdout.read().decode('utf-8')
    proc.wait()
    return output

# ==================================[ main ]==================================

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "moc_unload", ""):
        load_settings('', '', '')
        weechat.hook_config('plugins.var.python.moc_control.*', 'load_settings', '')

        weechat.bar_item_new('moc_infobar', 'moc_infobar_update', '')
        weechat.hook_timer(infobar['update']*1000,0,0,'moc_infobar_updater','')

        if infobar['enabled']:
            _add_infobar()
        weechat.hook_command(
            SCRIPT_COMMAND,
            'Control moc or display now playing information.',
            'play|pause|pp|stop|prev|next|infobar|help',
            'Commands Available\n'
            '  /moc         - Display currently playing song.\n'
            '  /moc play    - Start playing music.\n'
            '  /moc pause   - Toggle between pause/playing.\n'
            '  /moc pp      - Toggle between pause/playing.\n'
            '  /moc stop    - Stop playing music.\n'
            '  /moc prev    - Move to the previous song in the playlist.\n'
            '  /moc next    - Move to the next song in the playlist.\n'
            '  /moc infobar - Toggle the infobar display.\n'
            '\n'
            'Formatting\n'
            '  %mocTitle%   - Replaced with the title from moc.\n'
            '  %artist%     - Replaced with the song artist.\n'
            '  %title%      - Replaced with the song title.\n'
            '  %album%      - Replaced with the song album.\n'
            '  %file%       - Replaced with the filename/url of the song.\n'
            '  %cTime%      - Replaced with how long the song has been playing.\n'
            '  %cSec%       - Replaced with how long the song has been playing (seconcs).\n'
            '  %tTime%      - Replaced with the length of the song.\n'
            '  %tSec%       - Replaced with the length of the song (seconcs).\n'
            '  %bitrate%    - Replaced with the bitrate of the song.\n'
            '  %avgBitrate% - Replaced with the AvgBitrate of the song.\n'
            '  %rate%       - Replaced with the rate of the song.\n'
            '  %C##         - Make ## the number code of the color you want to use. Use %C by itself to end the color.\n'
            '\n'
            'To see all available settings, please check /set *moc_control*\n',
            'play|pause|pp|stop|prev|next|infobar|help',
            'moc_command',
            ''
        )

# ==================================[ end ]===================================

def moc_unload():
    """Unload the plugin from weechat"""
    if infobar['enabled']:
        _remove_infobar()
    return weechat.WEECHAT_RC_OK
