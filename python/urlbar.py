# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by FlashCode <flashcode@flashtux.org>
# Copyright (c) 2009 by xt <xt@bash.no>
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

#
# Bar with URLs (easy click on long URLs)
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#     version 12: fix error on empty prefix
# 2014-03-01, Lars Kiesow <lkiesow@uos.de>
#     version 11: Fixed autocompletion of /urlbar arguments
# 2010-12-20, xt <xt@bash.no>
#     version 10: use API for nick color, strip nick prefix
# 2009-12-17, FlashCode <flashcode@flashtux.org>
#     version 0.9: fix option name "show_index" (spaces removed)
# 2009-12-12, FlashCode <flashcode@flashtux.org>
#     version 0.8: update WeeChat site
# 2009-11-05, xt <xt@bash.no>
#     version 0.7: config option to turn off index
# 2009-10-20, xt <xt@bash.no>
#     version 0.6: removed priority on the bar
# 2009-07-01, xt <xt@bash.no>
#     version 0.5: changed script command to /urlbar, comma separated ignore list
# 2009-05-22, xt <xt@bash.no>
#     version 0.4: added configurable showing of buffer name, nick and time
# 2009-05-21, xt <xt@bash.no>
#     version 0.3: bug fixes, add ignore feature from sleo
# 2009-05-19, xt <xt@bash.no>
#     version 0.2-dev: fixes
# 2009-05-04, FlashCode <flashcode@flashtux.org>
#     version 0.1-dev: dev snapshot
#

SCRIPT_NAME    = "urlbar"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "12"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar with URLs. For easy clicking or selecting."
SCRIPT_COMMAND = "urlbar"

settings = {
    "visible_amount"        : '5',     # Amount of URLS visible in urlbar at any given time
    "visible_seconds"       : '5',     # Amount of seconds URLbar is visible
    "use_popup"             : 'on',    # Pop up automatically
    "remember_amount"       : '25',    # Max amout of URLs to keep in RAM
    "ignore"                : 'grep',  # List of buffers to ignore. (comma separated)
    "show_timestamp"        : 'on',    # Show timestamp in list
    "show_nick"             : 'on',    # Show nick in list
    "show_buffername"       : 'on',    # Show buffer name in list
    "show_index"            : 'on',    # Show url index in list
    "time_format"           : '%H:%M', # Time format
}

import_ok = True
try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import re
from time import strftime, localtime
octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\.%s){3}' % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
urlRe = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr), re.I)


# list of URL-objects
urls = []

# Display ALL, a toggle
DISPLAY_ALL = False



def urlbar_item_cb(data, item, window):
    ''' Callback that prints the lines in the urlbar '''
    global DISPLAY_ALL, urls
    try:
        visible_amount = int(weechat.config_get_plugin('visible_amount'))
    except ValueError:
        weechat.prnt('', 'Invalid value for visible_amount setting.')

    if not urls:
        return 'Empty URL list'

    if DISPLAY_ALL:
        DISPLAY_ALL = False
        printlist = urls
    else:
        printlist = urls[-visible_amount:]

    result = ''
    for index, url in enumerate(printlist):
        if weechat.config_get_plugin('show_index') == 'on':
            index = index+1
            result += '%s%2d%s %s \r' %\
                (weechat.color("yellow"), index, weechat.color("bar_fg"), url)
        else:
            result += '%s%s \r' %(weechat.color('bar_fg'), url)
    return result


def get_buffer_name(bufferp, long=False):
    if not weechat.buffer_get_string(bufferp, "short_name") or long:
        bufferd = weechat.buffer_get_string(bufferp, "name")
    else:
        bufferd = weechat.buffer_get_string(bufferp, "short_name")
    return bufferd

class URL(object):
    ''' URL class that holds the urls in the URL list '''

    def __init__(self, url, buffername, timestamp, nick):
        self.url = url
        self.buffername = buffername
        self.time = strftime(
                weechat.config_get_plugin('time_format'),
                localtime(int(timestamp)))
        self.time = self.time.replace(':', '%s:%s' %
                (weechat.color(weechat.config_string(
                weechat.config_get('weechat.color.chat_time_delimiters'))),
                weechat.color('reset')))
        self.nick = irc_nick_find_color(nick.strip('%&@+'))

    def __str__(self):
        # Format options
        time, buffername, nick = '', '', ''
        if weechat.config_get_plugin('show_timestamp') == 'on':
            time = self.time + ' '
        if weechat.config_get_plugin('show_buffername') == 'on':
            buffername = self.buffername + ' '
        if weechat.config_get_plugin('show_nick') == 'on':
            nick = self.nick + ' '

        return '%s%s%s%s' % (time, nick, buffername, self.url)

    def __cmp__(this, other):
        if this.url == other.url:
            return 0
        return 1

def urlbar_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):


    buffer_name = get_buffer_name(buffer, long=True)
    # Skip ignored buffers
    for ignored_buffer in weechat.config_get_plugin('ignore').split(','):
        if ignored_buffer.lower() == buffer_name.lower():
            return weechat.WEECHAT_RC_OK

    # Clean list of URLs
    for i in range(len(urls) - int(weechat.config_get_plugin('remember_amount'))):
        # Delete the oldest
        urls.pop(0)

    for url in urlRe.findall(message):
        urlobject = URL(url, get_buffer_name(buffer), time, prefix)
        # Do not add duplicate URLs
        if urlobject in urls:
            continue
        urls.append(urlobject)
        if weechat.config_get_plugin('use_popup') == 'on':
            weechat.command("", "/bar show urlbar")
            # auto hide bar after delay
            try:
                weechat.command('', '/wait %s /bar hide urlbar' %
                        int(weechat.config_get_plugin('visible_seconds')))
            except ValueError:
                weechat.prnt('', 'Invalid visible_seconds')

        weechat.bar_item_update("urlbar_urls")

    return weechat.WEECHAT_RC_OK


def urlbar_cmd(data, buffer, args):
    """ Callback for /url command. """
    global urls, DISPLAY_ALL

    if args == "list":
        if urls:
            DISPLAY_ALL = True
            weechat.command("", '/bar show urlbar')
            weechat.bar_item_update("urlbar_urls")
        else:
            weechat.prnt('', 'URL list empty.')
    if args == "show":
        weechat.command('', '/bar show urlbar')
    elif args == 'hide':
        weechat.command("", "/bar hide urlbar")
    elif args == 'toggle':
        weechat.command("", "/bar toggle urlbar")
    elif args == 'clear':
        urls = []
    elif not args.startswith('url '):
        weechat.command("", "/help %s" % SCRIPT_COMMAND)

    return weechat.WEECHAT_RC_OK

def urlbar_completion_urls_cb(data, completion_item, buffer, completion):
    """ Complete with URLS, for command '/url'. """
    for url in urls:
        weechat.hook_completion_list_add(completion, url.url,
                                         0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def irc_nick_find_color(nick):
    if not nick: # nick (actually prefix) is empty, irc_nick_color returns None on empty input
        return ''

    color = weechat.info_get('irc_nick_color', nick)
    if not color:
        # probably we're in WeeChat 0.3.0
        color = 0
        for char in nick:
            color += ord(char)
        
        color %= weechat.config_integer(weechat.config_get("weechat.look.color_nicks_number"))
        color = weechat.config_get('weechat.color.chat_nick_color%02d' %(color+1))
        color = w.color(weechat.config_string(color))
    return '%s%s%s' %(color, nick, weechat.color('reset'))


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        # Set default settings
        for option, default_value in settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

        weechat.hook_command(SCRIPT_COMMAND,
                             "URL bar control",
                             "[list | hide | show | toggle | url URL]",
                             "   list: list all URL and show URL bar\n"
                             "   hide: hide URL bar\n"
                             "   show: show URL bar\n"
                             "   toggle: toggle showing of URL bar\n",
                             "list || hide || show || toggle || url %(urlbar_urls)",
                             "urlbar_cmd", "")
        weechat.hook_completion("urlbar_urls", "list of URLs",
                                "urlbar_completion_urls_cb", "")
        weechat.bar_item_new("urlbar_urls", "urlbar_item_cb", "");
        weechat.bar_new("urlbar", "on", "0", "root", "", "top", "horizontal",
                        "vertical", "0", "0", "default", "default", "default", "0",
                        "urlbar_urls");
        weechat.hook_print("", "", "://", 1, "urlbar_print_cb", "")
