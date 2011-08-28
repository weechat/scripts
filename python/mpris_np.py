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

import dbus

try:
    import weechat
    weechat.register( 'mpris_np',
                      'Johannes Nixdorf <mixi@shadowice.org>',
                      '0.1',
                      'BSD',
                      'Print information on the currently played song',
                      '',
                      '' )
except ImportError:
    print 'This script must be called from inside weechat'

def getPlayerIf():
    player = bus.get_object( dbus_name,
                             '/Player' )
    return dbus.Interface( player,
                           dbus_interface='org.freedesktop.MediaPlayer' )
def getRootIf():
    root = bus.get_object( dbus_name,
                           '/' )
    return dbus.Interface( root,
                           dbus_interface='org.freedesktop.MediaPlayer' )
def getMetadata( name ):
    return getPlayerIf().GetMetadata()[name]
def getIdent():
    return getRootIf().Identity()

def print_info( data, buffer, args ):
    string = 'np: "' + getMetadata('artist') + '" - "' + getMetadata('title') + '" on "' + getMetadata( 'album' ) + '" using "' + getIdent() + '"'
    weechat.command( buffer, string )
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__':
    global bus
    global dbus_name

    bus = dbus.SessionBus()
    # get dbus_name
    dbus_root = bus.get_object( 'org.freedesktop.DBus',
                                '/' )
    dbus_if = dbus.Interface( dbus_root,
                              dbus_interface='org.freedesktop.DBus' )

    # TODO: err with multiple matches -> configurable?
    # TODO: err with no matches
    for name in dbus_if.ListNames():
        if name.startswith( 'org.mpris.' ):
            dbus_name = name
            break

    weechat.hook_command( 'np',
                          'Print information on the currently played song',
                          '',
                          '',
                          '',
                          'print_info',
                          '' )

