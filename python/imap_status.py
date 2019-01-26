# -*- coding: utf-8 -*-
# Copyright (c) 2009-2015 by xt <xt@bash.no>
# (this script requires WeeChat 0.4.2 or newer)
#
# History:
# 2019-01-26, nils_2@freenode
#   version 0.9: make script python3 compatible
#              : remove option "message_color" and "separator_color"
# 2016-05-07, Sebastien Helleu <flashcode@flashtux.org>:
#   version 0.8: add options "mailbox_color", "separator", "separator_color",
#                remove extra colon in bar item content, use hook_process
#                to prevent any freeze in WeeChat >= 1.5
# 2015-01-09, nils_2
#   version 0.7: use eval_expression()
# 2010-07-12, TenOfTen
#   version 0.6: beautify notification area
# 2010-03-17, xt
#   version 0.5: fix caching of return message
# 2010-01-19, xt
#   version 0.4: only run check when timer expired
# 2009-11-03, xt
#   version 0.3: multiple mailbox support
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
'''

import imaplib as i
import re
import weechat as w

SCRIPT_NAME = "imap_status"
SCRIPT_AUTHOR = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.9"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Bar item with unread imap messages count"


WEECHAT_VERSION = 0
IMAP_UNREAD = ''

# script options
settings = {
    'username': '',
    'password': '',
    'hostname': '',  # gmail uses imap.gmail.com
    'port': '993',
    'mailboxes': 'INBOX',  # comma separated list of mailboxes (gmail: "Inbox")
    'message': '${color:default}Mail: ',
    'mailbox_color': 'default',
    'separator': '${color:default}, ',
    'count_color': 'default',
    'interval': '5',
}


def string_eval_expression(text):
    return w.string_eval_expression(text, {}, {}, {})

class Imap(object):
    """Simple helper class for interfacing with IMAP server."""

    iRe = re.compile(br"UNSEEN (\d+)")
    conn = False

    def __init__(self):
        '''Connect and login.'''
        username = string_eval_expression(w.config_get_plugin('username'))
        password = string_eval_expression(w.config_get_plugin('password'))
        hostname = string_eval_expression(w.config_get_plugin('hostname'))
        port = int(w.config_get_plugin('port'))

        if username and password and hostname and port:
            M = i.IMAP4_SSL(hostname, port)
            M.login(username, password)
            self.conn = M

    def unreadCount(self, mailbox='INBOX'):
        if self.conn:
            unreadCount = int(
                self.iRe.search(
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
        except Exception:
            self.conn.logout()


def imap_get_unread(data):
    """Return the unread count."""
    imap = Imap()
    if not w.config_get_plugin('message'):
        output = ""
    else:
        output = '%s' % (
            string_eval_expression(w.config_get_plugin('message')))
    any_with_unread = False
    mailboxes = w.config_get_plugin('mailboxes').split(',')
    count = []
    for mailbox in mailboxes:
        mailbox = mailbox.strip()
        unreadCount = imap.unreadCount(mailbox)
        if unreadCount > 0:
            any_with_unread = True
            count.append('%s%s: %s%s' % (
                w.color(w.config_get_plugin('mailbox_color')),
                mailbox,
                w.color(w.config_get_plugin('count_color')),
                unreadCount))
    imap.logout()
    sep = '%s' % (
        string_eval_expression(w.config_get_plugin('separator')))
    output = output + sep.join(count) + w.color('reset')

    return output if any_with_unread else ''


def imap_item_cb(data, item, window):
    return IMAP_UNREAD


def imap_update_content(content):
    global IMAP_UNREAD
    if content != IMAP_UNREAD:
        IMAP_UNREAD = content
        w.bar_item_update('imap')


def imap_process_cb(data, command, rc, out, err):
    if rc == 0:
        imap_update_content(out)
    return w.WEECHAT_RC_OK


def imap_timer_cb(data, remaining_calls):
    """Timer callback to update imap bar item."""
    if WEECHAT_VERSION >= 0x01050000:
        w.hook_process('func:imap_get_unread', 30 * 1000,
                       'imap_process_cb', '')
    else:
        imap_update_content(imap_get_unread(None))  # this can block WeeChat!
    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
              SCRIPT_DESC, '', ''):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    WEECHAT_VERSION = int(w.info_get("version_number", "") or 0)

    w.bar_item_new('imap', 'imap_item_cb', '')
    imap_timer_cb(None, None)
    w.hook_timer(
        int(w.config_get_plugin('interval'))*1000*60,
        0,
        0,
        'imap_timer_cb',
        '')
