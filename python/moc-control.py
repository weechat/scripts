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
#

import weechat
import os
import subprocess
import traceback

infobar = {}
output = {}

STATUS_PLAYING = 'PLAY'
STATUS_PAUSED = 'PAUSE'
STATUS_STOPPED = 'STOP'

def moc_command(server, args):
	args = args.split(' ')
	if args[0] == '' or args[0] == 'i' or args[0] == 'o' or args[0] == 'ot':
		return moc_now_playing(server, args[0])
	elif args[0] == 'pause' or args[0] == 'pp':
		if _get_status() == STATUS_STOPPED:
			weechat.prnt('moc: Not playing')
			return weechat.PLUGIN_RC_OK
		else:
			_execute_command('mocp -G')
			weechat.prnt('moc: Song paused / Continue playing')
			return weechat.PLUGIN_RC_OK
	elif args[0] == 'play':
		if _get_status() == STATUS_PLAYING:
			weechat.prnt('moc: Already playing')
			return weechat.PLUGIN_RC_OK
		elif _get_status() == STATUS_PAUSED:
			_execute_command('mocp -U')
			weechat.prnt('moc: Continue playing.')
			return weechat.PLUGIN_RC_OK
		else:
			_execute_command('mocp -p')
			weechat.prnt('moc: Started playing.')
			return weechat.PLUGIN_RC_OK
	elif args[0] == 'stop':
		_execute_command('mocp -s')
		weechat.prnt('moc: Stop playing.')
		return weechat.PLUGIN_RC_OK
	elif args[0] == 'prev':
		if _get_status() == STATUS_STOPPED:
			weechat.prnt('moc: Not playing, cannot go to previous song.')
			return weechat.PLUGIN_RC_OK
		else:
			_execute_command('mocp -r')
			weechat.prnt('moc: Playing previous song.')
			return weechat.PLUGIN_RC_OK
	elif args[0] == 'next':
		if _get_status() == STATUS_STOPPED:
			weechat.prnt('moc: Not playing, cannot go to next song.')
			return weechat.PLUGIN_RC_OK
		else:
			_execute_command('mocp -f')
			weechat.prnt('moc: Playing next song.')
			return weechat.PLUGIN_RC_OK
	elif args[0] == 'infobar':
		if infobar['enabled']:
			infobar['enabled'] = False
			weechat.set_plugin_config('infobar_enabled', '0')
			weechat.remove_timer_handler('moc_infobar_update')
			weechat.remove_infobar(0)
			weechat.prnt('moc infobar disabled')
		else:
			infobar['enabled'] = True
			weechat.set_plugin_config('infobar_enabled', '1')
			moc_infobar_update()
			weechat.add_timer_handler(infobar['update'], 'moc_infobar_update')
			weechat.prnt('moc infobar enabled')
		return weechat.PLUGIN_RC_OK
	elif args[0] == 'help':
		weechat.command('/help moc')
		return weechat.PLUGIN_RC_OK
	else:
		weechat.prnt('moc: Unknown command %s' % (args[0]), '', server)
		return weechat.PLUGIN_RC_OK

def moc_infobar_update():
	_load_settings()
	if infobar['enabled'] == False:
		return weechat.PLUGIN_RC_OK

	if _get_status() == STATUS_STOPPED:
		weechat.print_infobar(infobar['update']+1, 'moc is not currently playing')
		return weechat.PLUGIN_RC_OK
	else:
		song = _get_song_info()
		format = _format_np(infobar['format'], song, 'infobar')
		weechat.print_infobar(infobar['update']+1, format)
		return weechat.PLUGIN_RC_OK

def moc_now_playing(server, formatType):
	_load_settings()
	format = ''
	if formatType == '':
		formatType = output['type']

	if _get_status() == STATUS_STOPPED:
		format = output['nothing']
	else:
		song = _get_song_info()
		format = _format_np(output['format'], song, 'chat')

	if formatType == 'i':
		weechat.prnt(format)
	elif formatType == 'o':
		weechat.command(format)
	elif formatType == 'ot':
		weechat.command('/me %s' % format)

	return weechat.PLUGIN_RC_OK

def moc_unload():
	"""Unload the plugin from weechat"""
	if infobar['enabled']:
		weechat.remove_infobar(0)
		weechat.remove_timer_handler('moc_infobar_update')
	return weechat.PLUGIN_RC_OK

def _execute_command(cmd):
	from subprocess import PIPE
	proc = subprocess.Popen(cmd, shell = True, stderr = PIPE, stdout = PIPE, close_fds = True)
	error = proc.stderr.read()
	if error != '':
		weechat.prnt(error)
	output = proc.stdout.read()
	proc.wait()
	return output

def _format_np(np, song, npType):
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
	song['TotalTime'] = '?:??'
	song['TotalSec'] = '??'

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

	return song

def _get_status():
	return _execute_command('mocp -i | grep "State:" | cut -d " " -f 2').strip()

def _load_settings():
    infobar['enabled'] = _load_setting('infobar_enabled', '0', 'bool')
    infobar['format'] = _load_setting('infobar_format', 'Now Playing: %mocTitle%')
    infobar['update'] = _load_setting('infobar_update', '10', 'int')
    output['format'] = _load_setting('output_format', 'is listening to %C04%title%%C %artist%%album%::: %C07%file%%C ::: %cTime%/%tTime% @ %bitrate%')
    output['artist'] = _load_setting('output_format_artist', '- %C03%artist%%C ')
    output['album'] = _load_setting('output_format_album', '(%C12%album%%C) ')
    output['type'] = _load_setting('output_type', 'ot')
    output['nothing'] = _load_setting('output_nothing', 'is listening to nothing')

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

if weechat.register('moc-control', '1.1.2', 'moc_unload', 'moc control and now playing script for Weechat'):
	_load_settings()
	if infobar['enabled']:
		moc_infobar_update()
		weechat.add_timer_handler(infobar['update'], 'moc_infobar_update')
	weechat.add_command_handler(
		'moc',
		'moc_command',
		'Control moc or display now playing information.',
		'i|o|ot|play|pause|pp|stop|prev|next|infobar|help',
		'Commands Available\n'
		'  /moc         - Display currently playing song.\n'
		'  /moc i       - Show info about current song\n'
		'  /moc o       - Display currently playing song as /msg\n'
		'  /moc ot      - Display currently playing song as /me\n'
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
		'To see all available settings, please check /setp moc\n',
		'i|o|ot|play|pause|pp|stop|prev|next|infobar|help'
	)
