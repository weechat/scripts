#
# Copyright (c) 2009 by Eric Gach <eric.gach@gmail.com>
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

import weechat
import re
import os
import subprocess
import traceback

__desc__ = 'Amarok2 control and now playing script for Weechat.'
__version__ = '1.0.0'
__author__ = 'Eric Gach <eric.gach@gmail.com>'

debug = {}
infobar = {}
output = {}
ssh = {'enabled': False}

STATUS_PLAYING = 0
STATUS_PAUSED = 1
STATUS_STOPPED = 2

class amarok2_exception(Exception):
	pass

def amarok2_command(server, args):
    try:
        args = args.split(' ')
        if args[0] == 'infobar':
            if infobar['enabled']:
                infobar['enabled'] = False
                weechat.set_plugin_config('infobar_enabled', '0')
                weechat.remove_timer_handler('amarok2_infobar_update')
                weechat.remove_infobar(0)
                weechat.prnt('Infobar disabled')
            else:
                infobar['enabled'] = True
                weechat.set_plugin_config('infobar_enabled', '1')
                amarok2_infobar_update()
                weechat.add_timer_handler(infobar['update'], 'amarok2_infobar_update')
                weechat.prnt('Amarok2 infobar enabled')
            return weechat.PLUGIN_RC_OK
        elif args[0] == 'next':
			if _get_status() == STATUS_STOPPED:
				weechat.prnt('Amarok2: Not playing, cannot go to next song.')
				return weechat.PLUGIN_RC_KO
			else:
				_execute_command(_dbus_command('Next'))
				weechat.prnt('Amarok2: Playing next song.')
				return weechat.PLUGIN_RC_OK
        elif args[0] == 'np':
            return amarok2_now_playing(server)
        elif args[0] == 'pause':
			if _get_status() == STATUS_PAUSED:
				weechat.prnt('Amarok2: Already paused')
				return weechat.PLUGIN_RC_KO
			else:
				_execute_command(_dbus_command('Pause'))
				weechat.prnt('Amarok2: Song paused.')
				return weechat.PLUGIN_RC_OK
        elif args[0] == 'play':
			if _get_status() == STATUS_PLAYING:
				weechat.prnt('Amarok2: Already playing')
				return weechat.PLUGIN_RC_KO
			else:
				_execute_command(_dbus_command('Play'))
				weechat.prnt('Amarok2: Started playing.')
				return weechat.PLUGIN_RC_OK
        elif args[0] == 'prev':
			if _get_status() == STATUS_STOPPED:
				weechat.prnt('Amarok2: Not playing, cannot go to previous song.')
				return weechat.PLUGIN_RC_KO
			else:
				_execute_command(_dbus_command('Prev'))
				weechat.prnt('Amarok2: Playing previous song.')
				return weechat.PLUGIN_RC_OK
        elif args[0] == 'stop':
            _execute_command(_dbus_command('Stop'))
            weechat.prnt('Amarok2: Stop playing.')
            return weechat.PLUGIN_RC_OK
        elif args[0] == '':
            return amarok2_display_help(server)
        else:
            weechat.prnt('Amarok2: Unknown command %s' % (args[0]), '', server)
            return weechat.PLUGIN_RC_OK
    except amarok2_exception, ex:
        return weechat.PLUGIN_RC_KO
    except:
        file = open(debug['file'], 'w')
        traceback.print_exc(None, file)
        weechat.prnt('Unknown Exception encountered. Stack dumped to %s' % (debug['file']), '', server)
        return weechat.PLUGIN_RC_KO

def amarok2_display_help(server):
	weechat.prnt('%s - Version: %s' % (__desc__, __version__), '', server)
	weechat.prnt('Author: %s' % (__author__), '', server)
	weechat.prnt('', '', server)
	weechat.prnt('Commands Available', '', server)
	weechat.prnt('  /amarok2 next    - Move to the next song in the playlist.', '', server)
	weechat.prnt('  /amarok2 np      - Display currently playing song.', '', server)
	weechat.prnt('  /amarok2 play    - Start playing music.', '', server)
	weechat.prnt('  /amarok2 pause   - Toggle between pause/playing.', '', server)
	weechat.prnt('  /amarok2 prev    - Move to the previous song in the playlist.', '', server)
	weechat.prnt('  /amarok2 stop    - Stop playing music.', '', server)
	weechat.prnt('  /amarok2 infobar - Toggle the infobar display.', '', server)
	weechat.prnt('', '', server)
	weechat.prnt('Formatting', '', server)
	weechat.prnt('  %artist%    - Replaced with the song artist.', '', server)
	weechat.prnt('  %title%     - Replaced with the song title.', '', server)
	weechat.prnt('  %album%     - Replaced with the song album.', '', server)
	weechat.prnt('  %year%      - Replaced with the song year tag.', '', server)
	weechat.prnt('  %cTime%     - Replaced with how long the song has been playing.', '', server)
	weechat.prnt('  %tTime%     - Replaced with the length of the song.', '', server)
	weechat.prnt('  %bitrate%   - Replaced with the bitrate of the song.', '', server)
	weechat.prnt('  %C##        - Make ## the number code of the color you want to use. Use %C by itself to end the color.', '', server)
	weechat.prnt('', '', server)
	weechat.prnt('To see all available settings, please check /setp amarok2')
	return weechat.PLUGIN_RC_OK

def amarok2_infobar_update():
	_load_settings()
	if infobar['enabled'] == False:
		return weechat.PLUGIN_RC_OK

	if _get_status() == STATUS_STOPPED:
		weechat.print_infobar(infobar['update'], 'Amarok is not currently playing')
		return weechat.PLUGIN_RC_OK
	else:
		song = _get_song_info()
		format = _format_np(infobar['format'], song)
		weechat.print_infobar(infobar['update'], format)
		return weechat.PLUGIN_RC_OK

def amarok2_now_playing(server):
	_load_settings()
	if _get_status() == STATUS_STOPPED:
		weechat.prnt('Amarok is not playing.', '', server)
		return weechat.PLUGIN_RC_KO
	else:
		song = _get_song_info()
		format = _format_np(output['format'], song)
		weechat.command(format)
		return weechat.PLUGIN_RC_OK

def amarok2_unload():
	"""Unload the plugin from weechat"""
	if infobar['enabled']:
		weechat.remove_infobar(0)
		weechat.remove_timer_handler('amarokInfobarUpdate')
	return weechat.PLUGIN_RC_OK

def _dbus_command(command):
	# we still have to use dbus-send because qdbus doesn't support complex types
	# yet. the GetStatus is one that isn't supported by qdbus yet.
	return 'DISPLAY=":0.0" dbus-send --type=method_call --print-reply --dest=org.kde.amarok /Player org.freedesktop.MediaPlayer.%s' % (command,)

def _execute_command(cmd):
	from subprocess import PIPE
	if ssh['enabled']:
		cmd = 'ssh -p %d %s@%s "%s"' % (ssh['port'], ssh['user'], ssh['host'], cmd)
	proc = subprocess.Popen(cmd, shell = True, stderr = PIPE, stdout = PIPE, close_fds = True)
	error = proc.stderr.read()
	if error != '':
		weechat.prnt(error)
	output = proc.stdout.read()
	proc.wait()
	return output

def _format_np(template, song):
	np = template.replace('%artist%', song['artist'])
	np = np.replace('%title%', song['title'])
	np = np.replace('%album%', song['album'])
	np = np.replace('%cTime%', song['cTime'])
	np = np.replace('%tTime%', song['time'])
	np = np.replace('%bitrate%', song['audio-bitrate'])
	np = np.replace('%year%', song['year'])
	np = np.replace('%C', chr(3))
	if _get_status() == STATUS_PAUSED:
		np = np + " - [PAUSED]"
	return np

def _format_seconds(s):
	# seconds should include milliseconds
	s = int(s) / 1000
	temp = float()
	temp = float(s) / (60*60*24)
	d = int(temp)
	temp = (temp - d) * 24
	h = int(temp)
	temp = (temp - h) * 60
	m = int(temp)
	temp = (temp - m) * 60
	sec = temp
	if d > 0:
		return "%id %i:%02i:%02i" % (d, h, m, sec)
	elif h > 0:
		return "%i:%02i:%02i" % (h, m, sec)
	else:
		return "%i:%02i" % (m, sec)

def _get_song_info():
	"""Get the song information from amarok"""
	song = {}
	info = _execute_command(_dbus_command('GetMetadata'))
	matches = re.findall('dict\s+entry\(\s+string\s+"([^"]+)"\s+variant\s+([a-z0-9]+)\s+([^\n]*)\s+\)', info)
	for x in matches:
		if x[1] == 'string':
			# Remove the quotes from strings
			song[x[0]] = x[2].strip('"')
		else:
			song[x[0]] = x[2]
	song['time'] = _format_seconds(song['mtime'])
	song['cTime'] = _format_seconds(re.findall('int32 ([0-9]+)', _execute_command(_dbus_command('PositionGet')))[0])
	return song

def _get_status():
	status = _execute_command(_dbus_command('GetStatus'))
	matches = re.findall('int32 ([0-9])', status)
	# first one is our playing status - 0 = playing, 1 = paused, 2 = stopped
	return int(matches[0])

def _load_settings():
    debug['file'] = os.path.expanduser(_load_setting('debug_file', '~/amarok2_debug.txt'))
    infobar['enabled'] = _load_setting('infobar_enabled', '0', 'bool')
    infobar['format'] = _load_setting('infobar_format', 'Now Playing: %title% by %artist%')
    infobar['update'] = _load_setting('infobar_update', '10', 'int')
    output['format'] = _load_setting('output_format', '/me is listening to %C04%title%%C by %C03%artist%%C from %C12%album%%C [%cTime% of %tTime% @ %bitrate%kbps]')
    ssh['enabled'] = _load_setting('ssh_enabled', '0', 'bool')
    ssh['host'] = _load_setting('ssh_host', 'localhost')
    ssh['port'] = _load_setting('ssh_port', '22', 'int')
    ssh['user'] = _load_setting('ssh_user', 'user')

def _load_setting(setting, default=None, type=None):
	value = weechat.get_plugin_config(setting)
	if value == '' and default != None:
		weechat.set_plugin_config(setting, default)
		value = default

	if type == 'int' or type == 'bool':
		value = int(value)

	if type == 'bool':
		value = bool(value)

	return value

if weechat.register('amarok2', __version__, 'amarok2_unload', __desc__):
	_load_settings()
	if infobar['enabled']:
		amarok2_infobar_update()
		weechat.add_timer_handler(infobar['update'], 'amarok2_infobar_update')
	weechat.add_command_handler('amarok2', 'amarok2_command', 'Control Amarok2 or display now playing information.', 'next|np|play|pause|prev|stop|infobar')
