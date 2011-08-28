# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 by agreeabledragon <recognize@me.com>
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

# (this script requires Spotify for Mac v0.5.1.98 or newer)
#
# History:
# 2011-06-12, agreeabledragon <recognize@me.com>
#     version 0.1.1: rewrote it to use weechat.hook_process() to prevent it from blocking weechat as requested by Sébastien
#
# 2011-06-12, agreeabledragon <recognize@me.com>
#     version 0.1: initial release
#
# @TODO: add options for customizing the output
import weechat as w, re, subprocess, sys

SCRIPT_NAME    = "spotify_nowplaying"
SCRIPT_AUTHOR  = "agreeabledragon <recognize@me.com>"
SCRIPT_VERSION = "0.1.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Current song script for Spotify (v0.5.1.98 or newer) on OS X"
SCRIPT_COMMAND = "spotify"
# For executing the script
SCRIPT_TIMEOUT = 1500
SCRIPT_PROCESS = False
SCRIPT_BUFFER  = False

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "") and sys.platform == "darwin":
    w.hook_command(SCRIPT_COMMAND,
                   SCRIPT_DESC,
                   "",
                   "",
                   "",
                   "spotify_exec",
                   "")
else:
	w.prnt("", "WARNING: This now playing script for Spotify only works on OS X with Spotify version 0.5.1.98 (or newer)")

def spotify_process(data, command, rc, stdout, stderr):
	global SCRIPT_BUFFER, SCRIPT_PROCESS
	if stderr:
		w.prnt("", "There was an error executing the script - make sure you meet the requirements (OS X with Spotify v0.5.1.98 or newer)")
		SCRIPT_BUFFER  = False
		SCRIPT_PROCESS = False
		return w.WEECHAT_RC_ERROR
	else:
		w.command(SCRIPT_BUFFER, stdout)
		SCRIPT_BUFFER  = False
		SCRIPT_PROCESS = False
		return w.WEECHAT_RC_OK

def spotify_exec(data, buffer, args):
	global SCRIPT_TIMEOUT, SCRIPT_BUFFER, SCRIPT_PROCESS
	if SCRIPT_PROCESS:
		w.prnt("", "Please wait for the other command to finish")
		return w.WEECHAT_RC_ERROR
	else:
		script = """set AppleScript's text item delimiters to ASCII character 10
					set spotify_active to false
					set theString to \\"/me is not currently running Spotify.\\"
	
					tell application \\"Finder\\"
						if (get name of every process) contains \\"Spotify\\" then set spotify_active to true
					end tell
	
					if spotify_active then
						set got_track to false
		
						tell application \\"Spotify\\"
							if player state is playing then
								set theTrack to name of the current track
								set theArtist to artist of the current track
								set theAlbum to album of the current track
								set isStarred to starred of the current track
								set got_track to true
							end if
						end tell
		
						set theString to \\"/me is not playing anything in Spotify.\\"
		
						if got_track then
							if isStarred then
								set theString to \\"/me is listening to one of my favorite tracks \\\\\\"\\" & theTrack & \\"\\\\\\" by \\" & theArtist & \\" (Album: \\" & theAlbum & \\")\\"
							else
								set theString to \\"/me is listening to \\\\\\"\\" & theTrack & \\"\\\\\\" by \\" & theArtist & \\" (Album: \\" & theAlbum & \\")\\"
							end if
						end if
					end if
	
					return theString"""
		SCRIPT_BUFFER  = buffer;
		SCRIPT_PROCESS = w.hook_process('arch -i386 osascript -e "' + script + '"', SCRIPT_TIMEOUT, "spotify_process", "")
		return w.WEECHAT_RC_OK
