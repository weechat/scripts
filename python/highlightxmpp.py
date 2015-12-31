# HighlightXMPP 0.5 for IRC. Requires WeeChat >= 0.3.0,
# Python >= 2.6, and sleekxmpp.
# Repo: https://github.com/jpeddicord/weechat-highlightxmpp
# 
# Copyright (c) 2009-2015 Jacob Peddicord <jacob@peddicord.net>
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

import sys
import weechat as w
import sleekxmpp

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')

info = (
    'highlightxmpp',
    'Jacob Peddicord <jacob@peddicord.net>',
    '0.5',
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

class SendMsgBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, recipient, message):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.jid = jid
        self.recipient = recipient
        self.msg = message
        self.add_event_handler("session_start", self.start, threaded=True)
    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.send_message(mto=self.recipient,
                          mbody=self.msg,
                          mtype='chat')
        self.disconnect(wait=True)


def send_xmpp(data, signal, message, trial=1):
    jid = w.config_get_plugin('jid')
    jid_to = w.config_get_plugin('to')
    if not jid_to:
        jid_to = jid
    password = w.config_get_plugin('password')

    xmpp = SendMsgBot(jid, password, jid_to, message)
    if not xmpp.connect():
        w.prnt('', "Unable to connect to XMPP server.")
        return w.WEECHAT_RC_OK
    xmpp.process(block=True)
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
