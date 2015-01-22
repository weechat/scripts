# -*- coding: utf-8 -*-

###
# Copyright (c) 2011, Johannes Nixdorf <mixi@shadowice.org>
# Copyright (c) 2014, Mantas Mikulėnas <grawity@gmail.com>
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
#  0.4.3 - grawity:
#   * allow the default player to be set
#  0.4.2 - grawity:
#   * show a better message in "Stopped" state
#  0.4.1 - grawity:
#   * inform the user about MPRIS v1 players
#  0.4 - grawity:
#   * ported to MPRIS v2
#  0.3 - Johannes:
#   * don't excpect every metadata key to be available
#  0.2 - Johannes:
#   * fix an error when the player isn't running
#   * don't display the song if it playing is paused/stopped
#   * fix an error when the player is changed while the plugin is loaded
#   * make fewer dbus calls
#  0.1 - Johannes:
#   * first version
###

from __future__ import print_function

import dbus

try:
    import weechat
    weechat.register('mpris2_np',
                     'Mantas Mikulėnas <grawity@gmail.com>',
                     '0.4.3',
                     'BSD',
                     'Print information on the currently played song',
                     '',
                     '')
except ImportError:
    print('This script must be called from inside weechat')
    raise

BUS_NAME_PREFIX_V2 = 'org.mpris.MediaPlayer2.'
BUS_NAME_PREFIX_V1 = 'org.mpris.'

IF_MPRIS_ROOT   = 'org.mpris.MediaPlayer2'
IF_MPRIS_PLAYER = 'org.mpris.MediaPlayer2.Player'
IF_DBUS_PROP    = 'org.freedesktop.DBus.Properties'

class FubarException(Exception):
    """

    For some reason, reloading either mpris2_np or the python plugin always
    breaks the DBus connection irrecoverably.

    """

def list_players(prefix=BUS_NAME_PREFIX_V2):
    bus = dbus.SessionBus()
    return [name[len(prefix):] for name in bus.list_names()
                               if name.startswith(prefix)]

def get_player(name):
    bus = dbus.SessionBus()
    try:
        return bus.get_object(BUS_NAME_PREFIX_V2 + name, '/org/mpris/MediaPlayer2')
    except TypeError:
        raise FubarException()

def print_info(data, buffer, args):
    err = None
    msg = None

    player_name = args.strip()

    if not player_name:
        player_name = weechat.config_get_plugin('default_player')

    if player_name:
        try:
            player_obj = get_player(player_name)
            prop_if = dbus.Interface(player_obj, IF_DBUS_PROP)

            _props = prop_if.GetAll(IF_MPRIS_ROOT)
            identity = _props.get('Identity', player_name)

            _props = prop_if.GetAll(IF_MPRIS_PLAYER)
            status   = _props.get('PlaybackStatus', 'Stopped')
            metadata = _props.get('Metadata', {})

            if status == 'Stopped':
                msg = u'not listening to anything on %s' % identity
            else:
                artist = u', '.join(metadata.get('xesam:artist', [u'Unknown artist']))
                genre  = u'/'.join(metadata.get('xesam:genre', []))
                album  = metadata.get('xesam:album', None)
                track  = metadata.get('xesam:trackNumber', None)
                title  = metadata.get('xesam:title', u'Unknown title')
                year   = metadata.get('xesam:contentCreated', None)

                msg = u'"%s" by %s' % (title, artist)
                if album:
                    msg += u' from "%s"' % album
                if year:
                    msg += u' (%s)' % year

            msg = msg.encode('utf-8')

        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() == 'org.freedesktop.DBus.Error.ServiceUnknown':
                err = 'player "%s" is not running' % player_name
            else:
                err = 'DBus error %s: "%s"' % (e.get_dbus_name(), e.get_dbus_message())

        except FubarException:
            err = 'player "%s" is not running (or pydbus is broken again)' % player_name

    else:
        players = list_players()
        if players:
            players.sort()
            err = 'running players: %s' % ', '.join(players)
        else:
            err = 'no MPRIS v2 players are running'
            v1_players = [p for p in list_players(BUS_NAME_PREFIX_V1) if '.' not in p]
            if v1_players:
                err += ' (I found "%s", but it only supports MPRIS v1)' \
                       % ('" and "'.join(v1_players))

    if err:
        weechat.prnt(buffer, 'np: %s' % err)
    else:
        weechat.prnt(buffer, 'np: %s' % msg)
        weechat.command(buffer, 'np: %s' % msg)
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__':
    weechat.hook_command('np',
                         'Print information on the currently played song',
                         '',
                         '',
                         '',
                         'print_info',
                         '')

    if not weechat.config_is_set_plugin('default_player'):
        weechat.config_set_plugin('default_player', '')
        weechat.config_set_desc_plugin('default_player',
            'Player name to use for "/np" (default: "", shows a list)')
