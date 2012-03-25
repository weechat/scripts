# HighlightXMPP 0.4 for IRC. Requires WeeChat >= 0.3.0 and Python >= 2.6.
# Repo: https://github.com/jpeddicord/weechat-highlightxmpp
# 
# Copyright (c) 2009-2012 Jacob Peddicord <jpeddicord@ubuntu.com>
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
#######
#
# You must configure this plugin before using:
#
#   JID messages are sent from:
#     /set plugins.var.python.highlightxmpp.jid someid@jabber.org
#   alternatively, to use a specific resource:
#     /set plugins.var.python.highlightxmpp.jid someid@jabber.org/resource
#
#   Password for the above JID:
#     /set plugins.var.python.highlightxmpp.password abcdef
#
#   JID messages are sent *to* (if not set, defaults to the same jid as above):
#     /set plugins.var.python.highlightxmpp.to myid@jabber.org

from time import sleep
import warnings
import weechat as w

# the XMPP module currently has a lot of deprecations
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import xmpp

info = (
    'highlightxmpp',
    'Jacob Peddicord <jpeddicord@ubuntu.com>',
    '0.4',
    'GPL3',
    "Relay highlighted & private IRC messages over XMPP (Jabber)",
    '',
    ''
)

settings = {
    'jid': '',
    'password': '',
    'to': '',
}

client = None

def connect_xmpp():
    global client
    # connected if not connected
    # & if we were disconnected, try to connect again
    if client and client.isConnected():
        return True
    w.prnt('', "XMPP: Connecting")
    jid_name = w.config_get_plugin('jid')
    password = w.config_get_plugin('password')
    try:
        jid = xmpp.protocol.JID(jid_name)
        client = xmpp.Client(jid.getDomain(), debug=[])
        client.connect()
        client.auth(jid.getNode(), password)
    except:
        w.prnt('', "XMPP: Could not connect or authenticate to server.")
        client = None
        return False
    return True

def send_xmpp(data, signal, msgtxt, trial=1):
    global client

    # ignore XMPP's deprecation warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # connect to xmpp if we need to
        if not connect_xmpp():
            return w.WEECHAT_RC_OK
        jid_to = w.config_get_plugin('to')

        # send to self if no target set
        if not jid_to:
            jid_to = w.config_get_plugin('jid')

        # send the message
        msg = xmpp.protocol.Message(jid_to, msgtxt, typ='chat')
        try:
            client.send(msg)
        except IOError:
            # every now and then the connection will still exist but a send will
            # fail. catch that here and try to reconnect. isConnected() should
            # start to realize that once this exception is triggered.
            if trial > 3:
                w.prnt('', "XMPP: Could not send to server.")
            else:
                sleep(0.5)
                send_xmpp(data, signal, msgtxt, trial + 1)
        return w.WEECHAT_RC_OK

# register with weechat
if w.register(*info):
    # add our settings
    for setting in settings:
        if not w.config_is_set_plugin(setting):
            w.config_set_plugin(setting, settings[setting])
    # and finally our hooks
    w.hook_signal('weechat_highlight', 'send_xmpp', '')
    w.hook_signal('weechat_pv', 'send_xmpp', '')
