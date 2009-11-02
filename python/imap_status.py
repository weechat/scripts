# -*- coding: utf-8 -*-
# Copyright (c) 2009 by xt <xt@bash.no>
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-11-02, xt
#   version 0.2: remove the imap "client" buffer, just do the unread count
# 2009-06-18, xt <xt@bash.no>
#   version 0.1: initial release.
#
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
'''  
Usage: put [imap] in your status bar items.  (Or any other bar to your liking)
"/set weechat.bar.status.items".

Warning: If you have a slow imap server, weechat might "freeze" while doing operations against remove server as this script does not do any background processing and weechat is single threaded.
'''

import weechat as w
import imaplib as i
import re

SCRIPT_NAME    = "imap_status"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with unread imap messages count"

# script options
settings = {
    "username"          : '',
    "password"          : '',
    "hostname"          : '',
    "port"              : '993',
    'mailbox'           : 'INBOX',
    'message'           : 'Mail: ',
    'message_color'     : 'default',
    'count_color'       : 'default',
    'interval'          : '5',
    'time_format'       : '%H:%M',
}

class Imap(object):
    ''' Simple helper class for interfacing with IMAP server '''

    iRe = re.compile("UNSEEN (\d+)")
    conn = False

    def __init__(self):
        ''' Connect and login'''
        username = w.config_get_plugin('username')
        password = w.config_get_plugin('password')
        hostname = w.config_get_plugin('hostname')
        port = int(w.config_get_plugin('port'))

        if username and password and hostname and port:
             M = i.IMAP4_SSL(hostname, port)
             M.login(username, password)
             self.conn = M

    def unreadCount(self, mailbox='INBOX'):
        if self.conn:
            unreadCount = int(self.iRe.search(\
                self.conn.status(mailbox, "(UNSEEN)")[1][0]).group(1))
            return unreadCount
        else:
            w.prnt('', 'Problem with IMAP connection. Please check settings.')
            return 0

    def logout(self):
        if not self.conn:
            return
        try:
            self.conn.close()
        except Exception, e:
            self.conn.logout()
            

def imap_cb(*kwargs):
    ''' Callback for the bar item with unread count '''

    imap = Imap()
    unreadCount = imap.unreadCount(w.config_get_plugin('mailbox'))
    imap.logout()

    if not unreadCount == 0:
        return '%s%s%s%s%s' % (\
             w.color(w.config_get_plugin('message_color')),
             w.config_get_plugin('message'),
             w.color(w.config_get_plugin('count_color')),
             unreadCount,
             w.color('reset'))
    return ''

def imap_update(*kwargs):
    w.bar_item_update('imap')

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)


    w.bar_item_new('imap', 'imap_cb', '')
    w.hook_timer(\
            int(w.config_get_plugin('interval'))*1000*60,
            0,
            0,
            'imap_update',
            '')
