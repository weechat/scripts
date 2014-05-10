# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
# Borrowed parts from pagetitle.py by xororand
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
#
# If someone posts an URL in a configured channel
# this script will post back title

# Explanation about ignores:
#   * plugins.var.python.announce_url_title.ignore_buffers:
#   Comma separated list of patterns for define ignores.
#   URLs from channels where its name matches any of these patterns will be ignored.
#   Wildcards '*', '?' and char groups [..] can be used.
#   An ignore exception can be added by prefixing '!' in the pattern.
#
#       Example:
#       *ubuntu*,!#ubuntu-offtopic
#       any urls from a 'ubuntu' channel will be ignored,
#       except from #ubuntu-offtopic
#
#   * plugins.var.python.announce_url_title.url_ignore
#     simply does partial match, so specifying 'google' will ignore every url with the word google in it
#
#
# History:
#
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#   version 18: change hook_print callback argument type of displayed/highlight
#               (WeeChat >= 1.0)
# 2013-11-07, excalibr
#   version 17: add more characters to exclude in escaping (this fix problem with youtube urls)
# 2012-11-15, xt
#   version 16: improve escaping
# 2011-09-04, Deltafire
#   version 15: fix remote execution exploit due to unescaped ' character in urls;
#               small bug fix for version 14 changes
# 2011-08-23, Deltafire
#   version 14: ignore filtered lines
# 2011-03-11, Sébastien Helleu <flashcode@flashtux.org>
#   version 13: get python 2.x binary for hook_process (fix problem when python 3.x is default python version)
# 2010-12-10, xt
#   version 12: add better ignores (code based on m4v inotify.py)
# 2010-11-02, xt
#   version 11: add prefix
# 2010-11-01, xt
#   version 10: add ignored buffers feature
# 2010-10-29, add ignore buffers feature
#   version 0.9: WeeChat user-agent option
# 2010-10-11, xt
#   version 0.8: support multiple concurrent url lookups
# 2010-10-11, xt
#   version 0.7: do not trigger on notices
# 2010-08-25, xt
#   version 0.6: notice some buffers instead of msg
# 2009-12-08, Chaz6
#   version 0.5: only announce for specified channels
# 2009-12-08, Chaz6 <chaz@chaz6.com>
#   version 0.4: add global option
# 2009-12-08, xt
#   version 0.3: option for public announcing or not
# 2009-12-07, xt <xt@bash.no>
#   version 0.2: don't renannounce same urls for a time
#                add optional prefix and suffix
# 2009-12-02, xt
#   version 0.1: initial

import weechat
w = weechat
import re
import htmllib
from time import time as now
from fnmatch import fnmatch
from urllib import quote

SCRIPT_NAME    = "announce_url_title"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "18"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Announce URL titles to channel or locally"

settings = {
    "buffers"        : 'freenode.#testing,',     # comma separated list of buffers
    "buffers_notice" : 'freenode.#testing,',     # comma separated list of buffers
    'ignore_buffers' : 'grep,',     # comma separated list of buffers to be ignored by this module
    'title_max_length': '80',
    'url_ignore'     : '', # comma separated list of strings in url to ignore
    'reannounce_wait': '5', # 5 minutes delay
    'prefix':   '',
    'suffix':   '',
    'announce_public': 'off', # print it or msg the buffer
    'global': 'off', # whether to enable for all buffers
    'user_agent': 'WeeChat/%(version)s (http://www.weechat.org)', # user-agent format string
    'global_prefix':'url', # Prefix for when not public announcement
}


octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\,.%s){3}' % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
urlRe = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr), re.I)

buffer_name = ''

urls = {}
script_nick = 'url'
def say(s, buffer=''):
    """normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(script_nick, s))

def unescape(s):
    """Unescape HTML entities"""
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()

def url_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):
    global buffer_name, urls, ignore_buffers

    # Do not trigger on filtered lines and notices
    if not int(displayed) or prefix == '--':
        return w.WEECHAT_RC_OK

    msg_buffer_name = w.buffer_get_string(buffer, "name")
    # Skip ignored buffers

    #if msg_buffer_name in w.config_get_plugin('ignore_buffers').split(','):
    #    return w.WEECHAT_RC_OK
    if msg_buffer_name in ignore_buffers:
        return w.WEECHAT_RC_OK

    found = False
    notice = False
    if w.config_get_plugin('global') == 'on':
        found = True
        buffer_name = msg_buffer_name
    else:
        for active_buffer in w.config_get_plugin('buffers').split(','):
            if active_buffer.lower() == msg_buffer_name.lower():
                found = True
                buffer_name = msg_buffer_name
                break
        for active_buffer in w.config_get_plugin('buffers_notice').split(','):
            if active_buffer.lower() == msg_buffer_name.lower():
                found = True
                buffer_name = msg_buffer_name
                break

    if not found:
        return w.WEECHAT_RC_OK

    ignorelist = w.config_get_plugin('url_ignore').split(',')
    for url in urlRe.findall(message):

        url = quote(url, "%/:=&?~#+!$,;@()*[]") # Escape URL
        ignore = False
        for ignore_part in ignorelist:
            if ignore_part.strip():
                if ignore_part in url:
                    ignore = True
                    w.prnt('', '%s: Found %s in URL: %s, ignoring.' %(SCRIPT_NAME, ignore_part, url))
                    break

        if ignore:
            continue

        if url in urls:
            continue
        else:
            urls[url] = {}
    url_process_launcher()

    return w.WEECHAT_RC_OK

def url_process_launcher():
    ''' Iterate found urls, fetch title if hasn't been launched '''
    global urls

    user_agent = w.config_get_plugin('user_agent') % {'version': w.info_get("version", "")}
    for url, url_d in urls.items():
        if not url_d: # empty dict means not launched
            url_d['launched'] = now()

            # Read 8192
            python2_bin = w.info_get("python2_bin", "") or "python"
            cmd = python2_bin + " -c \"import urllib2; opener = urllib2.build_opener();"
            cmd += "opener.addheaders = [('User-agent','%s')];" % user_agent
            cmd += "print opener.open('%s').read(8192)\"" % url

            url_d['stdout'] = ''
            url_d['url_hook_process'] = w.hook_process(cmd, 30 * 1000, "url_process_cb", "")

    return w.WEECHAT_RC_OK

def url_process_cb(data, command, rc, stdout, stderr):
    """ Callback parsing html for title """

    global buffer_name, urls

    url = command.split("'")[-2]
    if stdout != "":
        urls[url]['stdout'] += stdout
    if int(rc) >= 0:

        head = re.sub("[\r\n\t ]"," ", urls[url]['stdout'])
        title = re.search('(?i)\<title\>(.*?)\</title\>', head)
        if title:
            title = unescape(title.group(1))

            max_len = int(w.config_get_plugin('title_max_length'))
            if len(title) > max_len:
                title = "%s [...]" % title[0:max_len]

            splits = buffer_name.split('.') #FIXME bad code
            server = splits[0]
            buffer = '.'.join(splits[1:])
            output = w.config_get_plugin('prefix') + title + w.config_get_plugin('suffix')
            announce_public = w.config_get_plugin('announce_public')
            if announce_public == 'on':
                found = False
                for active_buffer in w.config_get_plugin('buffers').split(','):
                    if active_buffer.lower() == buffer_name.lower():
                        w.command('', '/msg -server %s %s %s' %(server, buffer, output))
                        found = True
                for active_buffer in w.config_get_plugin('buffers_notice').split(','):
                    if active_buffer.lower() == buffer_name.lower():
                        w.command('', '/notice -server %s %s %s' %(server, buffer, output))
                        found = True
                if found == False:
                    say(output,w.buffer_search('', buffer_name))
            else:
                say(output,w.buffer_search('', buffer_name))
        urls[url]['stdout'] = ''

    return w.WEECHAT_RC_OK

def purge_cb(*args):
    ''' Purge the url list on configured intervals '''

    global urls

    t_now = now()
    for url, url_d in urls.items():
        if (t_now - url_d['launched']) > \
            int(w.config_get_plugin('reannounce_wait'))*60:
                del urls[url]

    return w.WEECHAT_RC_OK

class Ignores(object):
    def __init__(self, ignore_type):
        self.ignore_type = ignore_type
        self.ignores = []
        self.exceptions = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(',')
        ignores = [ s.lower() for s in ignores if s ]
        self.ignores = [ s for s in ignores if s[0] != '!' ]
        self.exceptions = [ s[1:] for s in ignores if s[0] == '!' ]

    def __contains__(self, s):
        s = s.lower()
        for p in self.ignores:
            if fnmatch(s, p):
                for e in self.exceptions:
                    if fnmatch(s, e):
                        return False
                return True
        return False

def ignore_update(*args):
    ignore_buffers._get_ignores()
    return w.WEECHAT_RC_OK


if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):

        # Set default settings
        for option, default_value in settings.iteritems():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, default_value)
        ignore_buffers = Ignores('ignore_buffers')

        w.hook_print("", "", "://", 1, "url_print_cb", "")
        w.hook_timer(\
            int(w.config_get_plugin('reannounce_wait')) * 1000 * 60,
            0,
            0,
            "purge_cb",
            '')
        weechat.hook_config('plugins.var.python.%s.ignore_buffers' %SCRIPT_NAME, 'ignore_update', '')
    color_chat_delimiters = weechat.color('chat_delimiters')
    color_chat_nick       = weechat.color('chat_nick')
    color_reset           = weechat.color('reset')
    color_chat_buffer     = weechat.color('chat_buffer')
    # pretty printing
    script_nick = '%s[%s%s%s]%s' %(color_chat_delimiters,
                                   color_chat_nick,
                                   w.config_get_plugin('global_prefix'),
                                   color_chat_delimiters,
                                   color_reset)
