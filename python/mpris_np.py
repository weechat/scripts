# -*- coding: utf-8 -*-

###
# Copyright (c) 2011, Johannes Nixdorf <mixi@shadowice.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

###
# ChangeLog:
#  0.3:
#   * don't excpect every metadata key to be available
#  0.2:
#   * fix an error when the player isn't running
#   * don't display the song if it playing is paused/stopped
#   * fix an error when the player is changed while the plugin is loaded
#   * make fewer dbus calls
#  0.1:
#   * first version
###

import dbus

try:
    import weechat
    weechat.register( 'mpris_np',
                      'Johannes Nixdorf <mixi@shadowice.org>',
                      '0.3',
                      'BSD',
                      'Print information on the currently played song',
                      '',
                      '' )
except ImportError:
    print 'This script must be called from inside weechat'

class NoPlayerException(Exception):
    pass

def getDBusName():
    dbus_root = bus.get_object( 'org.freedesktop.DBus',
                                '/' )
    dbus_if = dbus.Interface( dbus_root,
                              dbus_interface='org.freedesktop.DBus' )

    # TODO: err with multiple matches -> configurable?
    for name in dbus_if.ListNames():
        if name.startswith( 'org.mpris.' ):
            return name

    raise NoPlayerException

def getPlayerIf():
    player = bus.get_object( getDBusName(),
                             '/Player' )
    return dbus.Interface( player,
                           dbus_interface='org.freedesktop.MediaPlayer' )

def getRootIf():
    root = bus.get_object( getDBusName(),
                           '/' )
    return dbus.Interface( root,
                           dbus_interface='org.freedesktop.MediaPlayer' )

def getMetadata( name, player_if ):
    return player_if.GetMetadata()[name]

def getIdent( root_if ):
    return root_if.Identity()

def getPlayingState( player_if ):
    return player_if.GetStatus()[0]

def getPlayingStateString(x):
    if x == 0:
        return 'Playing'
    elif x == 1:
        return 'Paused'
    elif x == 2:
        return 'Stopped'

def print_info( data, buffer, args ):
    try:
        player_if = getPlayerIf()
        root_if = getRootIf()

        state = getPlayingState( player_if )
        if state == 0:
            artist = ''
            title = ''
            album = ''
            try:
                artist = getMetadata( 'artist', player_if )
            except KeyError:
                pass
            try:
                title = getMetadata( 'title', player_if )
            except KeyError:
                pass
            try:
                album = getMetadata( 'album', player_if )
            except KeyError:
                pass

            if title == '':
                string = 'np: no title available'
            else:
                string = 'np: '
                if artist != '':
                    string += '"' + artist + '" - '
                if title != '':
                    string += '"' + title + '"'
                if album != '':
                    string += ' on "' + album + '"'

            string += ' using "' + getIdent( root_if ) + '"'
        else:
            string = 'np: "' + getIdent( root_if ) + '": ' + getPlayingStateString( state )
    except NoPlayerException:
        string = 'np: no player running'

    #weechat.prnt( buffer, string )
    weechat.command( buffer, string )
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__':
    global bus

    bus = dbus.SessionBus()
    weechat.hook_command( 'np',
                          'Print information on the currently played song',
                          '',
                          '',
                          '',
                          'print_info',
                          '' )

