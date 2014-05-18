# Author and licensing
__Author__ = "Darth-O-Ring"
__Email__ = "darthoring@gmail.com"
__License__ = """
Copyright (C) 2014-2016  Darth-O-Ring   <darthoring@gmail.com>

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

# Imports
try:
    import weechat

except ImportError:
    import sys

    print '\nError: Script must be run under Weechat.\n'

    sys.exit(2)

import dbus


weechat.register('clemy', "Your mommy's boyfriend", '0.1.1', 'GPLv3', 'Control yo Clementine like boom-blaka!', '', '')

err_message     =       '\nSomething silly just happend.  Make sure Clementine is running mah dude.'


def help():
    """
    Print help menu to main
    weechat buffer.

    """
    weechat.prnt('', '\n            --Start Help--                ')
    weechat.prnt('', '--Option--                     --Command--')
    weechat.prnt('', '-Play                          /clemy play')
    weechat.prnt('', '-Pause                         /clemy pause')
    weechat.prnt('', '-Next                          /clemy next')
    weechat.prnt('', '-Previous                      /clemy prev')
    weechat.prnt('', '-Stop                          /clemy stop')
    weechat.prnt('', '-Play Track <n>                /clemy playtrack <n>')
    weechat.prnt('', '-Volume up by 4%               /clemy vol+')
    weechat.prnt('', '-Volume down by 4%             /clemy vol-')
    weechat.prnt('', '-Volume up by <n>              /clemy vol+by <n>')
    weechat.prnt('', '-Volume down by <n>            /clemy vol-by <n>')
    weechat.prnt('', '-Now Playing                   /clemynp')
    weechat.prnt('', '-Info                          /clemy info')
    weechat.prnt('', '\n            --End Help--                  ')
    return ''



def np():
    """
    Gather artist, song, and album
    info through dbus.

    """
    bus         =       dbus.Bus(dbus.Bus.TYPE_SESSION)
    try:
        bus_object  =       bus.get_object('org.mpris.clementine', '/Player')
        artist_info =       bus_object.GetMetadata()
        artist      =       artist_info['performer'][:]
        album       =       artist_info['album'][:]
        song        =       artist_info['title'][:]
        now_playing =       '{0} - {1} (album: {2})'.format(artist, song, album)

    except (dbus.DBusException, Exception):
        weechat.prnt('', err_message)

        return weechat.WEECHAT_RC_OK

    return now_playing


def process_cb(data, command, rc, out, err):
    process_output      =       ''
    if out != '':
        process_output  +=      out

    if int(rc) > 0:
        weechat.prnt('', process_output)

    return weechat.WEECHAT_RC_OK


def control(data, buffer, args):
    """
    Parse buffer for valid commands
    and build dictionary mapping from
    valid args to system commands.

    """
    args            =       args.split(' ')
    commands        =       {
                            'play'      :   'dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause',
                            'next'      :   'dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Next',
                            'prev'      :   'dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Previous',
                            'stop'      :   'dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Stop',
                            'vol+'      :   'clementine --volume-up',
                            'vol-'      :   'clementine --volume-down',
                            'vol+by'    :   'clementine --volume-increase-by {0}',
                            'vol-by'    :   'clementine --volume-decrease-by {0}',
                            'playtrack' :   'clementine --play-track {0}'
                            }

    try:
        if args[0].lower() == 'play':
            weechat.hook_process(commands['play'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Playing: {0}'.format(np()))

        elif args[0].lower() == 'pause':
            weechat.hook_process(commands['play'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Paused')

        elif args[0].lower() == 'next':
            weechat.hook_process(commands['next'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Playing Next Track Mah Dude...')

        elif args[0].lower() == 'prev':
            weechat.hook_process(commands['prev'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Playing Previous Track Mah Dude...')

        elif args[0].lower() == 'stop':
            weechat.hook_process(commands['stop'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Stopped Playback')

        elif args[0].lower() == 'playtrack':
            weechat.hook_process(commands['playtrack'].format(args[1]), 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Playing track {0}: {1}'.format(args[1], np()))

        elif args[0].lower() == 'vol+':
            weechat.hook_process(commands['vol+'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Volume Increased By 4%')

        elif args[0].lower() == 'vol-':
            weechat.hook_process(commands['vol-'], 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Volume Decreased By 4%')

        elif args[0].lower() == 'vol+by':
            weechat.hook_process(commands['vol+by'].format(args[1]), 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Volume Increased By {0}%'.format(args[1]))

        elif args[0].lower() == 'vol-by':
            weechat.hook_process(commands['vol-by'].format(args[1]), 10 * 1000, 'process_cb', '')
            weechat.prnt('', 'Volume Decreased By {0}%'.format(args[1]))

        elif args[0].lower() == 'help':
            weechat.prnt('', '{0}'.format(help()))

        elif args[0].lower() == 'info':
            weechat.prnt('', 'Currently listenting to: {0}'.format(np()))

        else:
            weechat.prnt('', "\nWhat are you doing dawg?  That's not a valid command!\n")
            help()

    except:
        weechat.prnt('', err_message)

        return ''

    return weechat.WEECHAT_RC_OK


def weechat_np(data, buffer, args):
    """
    Callback function for
    hooked clemynp command.

    """
    weechat.command(buffer, '/me is currently listening to: {0}'.format(np()))

    return weechat.WEECHAT_RC_OK


weechat.hook_command('clemynp', 'Get/output now playing info', '', '', '', 'weechat_np', '')
weechat.hook_command('clemy', 'Control Clementine', "[play] | [pause] | [next] | [prev] | [stop] | [vol+] | [vol-] | [vol+by <n>] | [vol-by <n>] | [playtrack <n>] | [help]",
"""
play:           Play song.
pause:          Pause song.
next:           Play next song.
prev:           Play previous song.
stop:           Stop playback
vol+:           Increase volume by 4%
vol-:           Decrease volume by 4%
vol+by <n>:     Increase volume by n%
vol-by <n>:     Decrease volume by n%
playtrack <n>:  Play track number n
help:  OG help information.

use: /clemynp if you want to print current song to the buffer that the command is launched from.
Get silly with it.

""", '', 'control', '')
