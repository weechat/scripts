# Copyright (C) 2013 - Isaac Ross <foxxysauce@gmail.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# Made as a port of cmus_xchat-v2.0, also made by Isaac Ross. Due to the nature of weechat's plugin/scripting API,
# this was mostly made using find/replace in a text editor

import commands
import weechat
import os

weechat.register("cmus", "Isaac Ross", "1.02", "GPL2", "Adds ability to control cmus and post the currently playing song in a channel", "", "")


def help():
    weechat.prnt('', ' --Option--              --Command--')
    weechat.prnt('', '-Play:                   /cmus play')
    weechat.prnt('', '-Pause:                  /cmus pause')
    weechat.prnt('', '-Stop:                   /cmus stop')
    weechat.prnt('', '-Next Track:             /cmus next')
    weechat.prnt('', '-Previous Track:         /cmus prev')
    weechat.prnt('', '-Toggle Shuffle:         /cmus shuffle')
    weechat.prnt('', '-Player Status:          /cmus status')
    weechat.prnt('', '-Now Playing:            /cmusnp')
    weechat.prnt('', '-NP (filename):          /cmus file')
    weechat.prnt('', ' ')
    weechat.prnt('', "-NOTE: If the currently playing file lacks artist, album, and title tags, use '/cmus file' to post the filename instead.")
    weechat.prnt('', '----------------------------------------------------------------------------------------')
    weechat.prnt('', "If you encounter any problems, feel free to email me at: <foxxysauce@gmail.com>")
    weechat.prnt('', "Keep in mind that most problems will probably be related to cmus-remote, not this script")

def np():
    cmus = commands.getoutput('cmus-remote -Q')
    lines = cmus.split('\n')

    #some redundant loops later, but streamline as needed

    #Only store lines marked as tags
    tags = [line.split(' ')[1:] for line in lines if line[:3] == 'tag']

    title, artist, album = '<unknown>', '<unknown>', '<unknown>'
    for tag in tags:
        if tag[0] == 'artist':
            artist = ' '.join(tag[1:])
        elif tag[0] == 'title':
            title = ' '.join(tag[1:])
        elif tag[0] == 'album':
            album = ' '.join(tag[1:])
        else:
            #Maybe eventually extend the functionality to print other tags?
            continue

    nowplaying = "%(artist)s - %(title)s (album: %(album)s)" % \
                        {"artist": artist, \
                        "title": title, \
                        "album": album}

    return nowplaying

def control(data, buffer, args):
    args = args.split(' ')
    if args[0].lower() == 'play':
        os.system('cmus-remote -p')
        weechat.prnt('', 'Playing...')
    elif args[0].lower() == 'pause':
        os.system('cmus-remote -u')
        weechat.prnt('', 'Paused.')
    elif args[0].lower() == 'stop':
        os.system('cmus-remote -s')
        weechat.prnt('', 'Stopped.')
    elif args[0].lower() == 'next':
        os.system('cmus-remote -n')
        weechat.prnt('', 'Playing next track...')
    elif args[0].lower() == 'prev':
        os.system('cmus-remote -r')
        weechat.prnt('', 'Playing previous track...')
    elif args[0].lower() == 'shuffle':
        os.system('cmus-remote -S')
        weechat.prnt('', 'Toggled shuffle on/off.')
    elif args[0].lower() == 'status':
        status = commands.getoutput('cmus-remote -Q')
        status = status.split('\n')
        for line in status:
            weechat.prnt('', " -- " + line)
    elif args[0].lower() == 'help':
        help()
    elif args[0].lower() == 'file':
        filename = commands.getoutput('cmus-remote -Q')
        filename = filename.split('\n')
        newname  = filename[1]
        newname = newname.replace('file', '', 1)
        newname = newname.replace(' ', '', 1)
        newname = newname.rpartition('/')
        newname = newname[-1]
        weechat.command('', '/me is currently listening to: ' + newname)
    else:
        weechat.prnt('', 'Not a valid option.')
        help()
    return weechat.WEECHAT_RC_OK

def weechat_np(data, buffer, args):
    weechat.command(buffer, '/me is currently listening to: ' + np())
    return weechat.WEECHAT_RC_OK

weechat.hook_command("cmusnp", "Get/send now playing info.", "", "", "", "weechat_np", "")
weechat.hook_command("cmus", "Control cmus.", "[file] | [next] | [pause] | [play] | [prev] | [shuffle] | [status] | [stop] | [help]",
"""
file: Get/send name of the currently playing file.
next: Play next file.
pause: Pause playback.
play: Resume playback.
prev: Play previous song.
shuffle: Enable shuffle.
status: Show status of cmus (same as "cmus-remote -Q" in your shell)
stop: Stop playback.
help: Alternative (original) help list.

Use /cmusnp if you're looking for the now-playing functionality of the script.
""" , "", "control", "")
