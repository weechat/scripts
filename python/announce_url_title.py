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
#   URLs from channels where its name matches any of these patterns will be
#   ignored.
#   Wildcards '*', '?' and char groups [..] can be used.
#   An ignore exception can be added by prefixing '!' in the pattern.
#
#       Example:
#       *ubuntu*,!#ubuntu-offtopic
#       any urls from a 'ubuntu' channel will be ignored,
#       except from #ubuntu-offtopic
#
#   * plugins.var.python.announce_url_title.url_ignore
#     simply does partial match, so specifying 'google' will ignore every url
#     with the word google in it
#
#
# History:
#
# 2021-06-05, Sébastien Helleu <flashcode@flashtux.org>
#   version 19: make script compatible with Python 3, fix PEP8 errors
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#   version 18: change hook_print callback argument type of displayed/highlight
#               (WeeChat >= 1.0)
# 2013-11-07, excalibr
#   version 17: add more characters to exclude in escaping (this fix problem
#               with youtube urls)
# 2012-11-15, xt
#   version 16: improve escaping
# 2011-09-04, Deltafire
#   version 15: fix remote execution exploit due to unescaped ' character in
#               urls; small bug fix for version 14 changes
# 2011-08-23, Deltafire
#   version 14: ignore filtered lines
# 2011-03-11, Sébastien Helleu <flashcode@flashtux.org>
#   version 13: get python 2.x binary for hook_process (fix problem when
#               python 3.x is default python version)
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

from time import time as now
from fnmatch import fnmatch
from html import unescape
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import weechat
import re

SCRIPT_NAME = "announce_url_title"
SCRIPT_AUTHOR = "xt <xt@bash.no>"
SCRIPT_VERSION = "19"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Announce URL titles to channel or locally"

settings = {
    # comma separated list of buffers
    "buffers": "libera.#testing,",
    # comma separated list of buffers
    "buffers_notice": "libera.#testing,",
    # comma separated list of buffers to be ignored by this module
    "ignore_buffers": "grep,",
    "title_max_length": "80",
    # comma separated list of strings in url to ignore
    "url_ignore": "",
    # 5 minutes delay
    "reannounce_wait": "5",
    "prefix": "",
    "suffix": "",
    # print it or msg the buffer
    "announce_public": "off",
    # whether to enable for all buffers
    "global": "off",
    # user-agent format string
    "user_agent": "WeeChat/%(version)s (https://weechat.org)",
    # Prefix for when not public announcement
    "global_prefix": "url",
}


octet = r"(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})"
ipAddr = r"%s(?:\,.%s){3}" % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r"[0-9a-z][-0-9a-z]*[0-9a-z]?"
domain = r"%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?" % (label, label)
urlRe = re.compile(
    r"(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)" % (domain, ipAddr), re.I
)

buffer_name = ""

urls = {}
script_nick = "url"


def say(s, buffer=""):
    """Display message."""
    weechat.prnt(buffer, "%s\t%s" % (script_nick, s))


def url_print_cb(
    data, buffer, time, tags, displayed, highlight, prefix, message
):
    global buffer_name, urls, ignore_buffers

    # Do not trigger on filtered lines and notices
    if not int(displayed) or prefix == "--":
        return weechat.WEECHAT_RC_OK

    msg_buffer_name = weechat.buffer_get_string(buffer, "name")

    # Skip ignored buffers
    if msg_buffer_name in ignore_buffers:
        return weechat.WEECHAT_RC_OK

    found = False
    if weechat.config_get_plugin("global") == "on":
        found = True
        buffer_name = msg_buffer_name
    else:
        buffers = weechat.config_get_plugin("buffers").split(",")
        for active_buffer in buffers:
            if active_buffer.lower() == msg_buffer_name.lower():
                found = True
                buffer_name = msg_buffer_name
                break
        buffers_notice = weechat.config_get_plugin("buffers_notice").split(",")
        for active_buffer in buffers_notice:
            if active_buffer.lower() == msg_buffer_name.lower():
                found = True
                buffer_name = msg_buffer_name
                break

    if not found:
        return weechat.WEECHAT_RC_OK

    ignorelist = weechat.config_get_plugin("url_ignore").split(",")
    for url in urlRe.findall(message):

        url_esc = quote(url, "%/:=&?~#+!$,;@()*[]")  # Escape URL
        ignore = False
        for ignore_part in ignorelist:
            if ignore_part.strip():
                if ignore_part in url_esc:
                    ignore = True
                    weechat.prnt(
                        "",
                        "%s: Found %s in URL: %s, ignoring."
                        % (SCRIPT_NAME, ignore_part, url_esc),
                    )
                    break

        if ignore:
            continue

        if url_esc in urls:
            continue
        else:
            urls[url_esc] = {}

    url_process_launcher()

    return weechat.WEECHAT_RC_OK


def url_read(url):
    """Read URL."""
    user_agent = weechat.config_get_plugin("user_agent") % {
        "version": weechat.info_get("version", "")
    }
    req = Request(
        url,
        headers={
            "User-agent": user_agent,
        },
    )
    try:
        head = urlopen(req).read(8192).decode("utf-8", errors="ignore")
    except URLError:
        return ""
    match = re.search("(?i)<title>(.*?)</title>", head)
    return unescape(match.group(1)) if match else ""


def url_process_cb(data, command, rc, stdout, stderr):
    """Process callback."""

    global buffer_name, urls

    title = stdout
    max_len = int(weechat.config_get_plugin("title_max_length"))
    if len(title) > max_len:
        title = "%s [...]" % title[0:max_len]

    splits = buffer_name.split(".")  # FIXME bad code
    server = splits[0]
    buffer = ".".join(splits[1:])
    output = (
        weechat.config_get_plugin("prefix")
        + title
        + weechat.config_get_plugin("suffix")
    )
    announce_public = weechat.config_get_plugin("announce_public")
    if announce_public == "on":
        found = False
        buffers = weechat.config_get_plugin("buffers").split(",")
        for active_buffer in buffers:
            if active_buffer.lower() == buffer_name.lower():
                weechat.command(
                    "",
                    "/msg -server %s %s %s" % (server, buffer, output),
                )
                found = True
        buffers_notice = weechat.config_get_plugin("buffers_notice").split(",")
        for active_buffer in buffers_notice:
            if active_buffer.lower() == buffer_name.lower():
                weechat.command(
                    "",
                    "/notice -server %s %s %s" % (server, buffer, output),
                )
                found = True
        if not found:
            say(output, weechat.buffer_search("", buffer_name))
    else:
        say(output, weechat.buffer_search("", buffer_name))

    return weechat.WEECHAT_RC_OK


def url_process_launcher():
    """Iterate found urls, fetch title if hasn't been launched."""
    global urls

    for url, url_d in urls.items():
        if not url_d:  # empty dict means not launched
            url_d["launched"] = now()
            url_d["url_hook_process"] = weechat.hook_process(
                "func:url_read",
                30 * 1000,
                "url_process_cb",
                url,
            )

    return weechat.WEECHAT_RC_OK


def purge_cb(*args):
    """Purge the url list on configured intervals."""

    global urls

    t_now = now()
    reannounce_wait = int(weechat.config_get_plugin("reannounce_wait")) * 60
    for url in list(urls):
        if t_now - urls[url]["launched"] > reannounce_wait:
            del urls[url]

    return weechat.WEECHAT_RC_OK


class Ignores(object):
    def __init__(self, ignore_type):
        self.ignore_type = ignore_type
        self.ignores = []
        self.exceptions = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(",")
        ignores = [s.lower() for s in ignores if s]
        self.ignores = [s for s in ignores if s[0] != "!"]
        self.exceptions = [s[1:] for s in ignores if s[0] == "!"]

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
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__":
    if weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    ):

        # Set default settings
        for option, default_value in settings.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        ignore_buffers = Ignores("ignore_buffers")

        weechat.hook_print("", "", "://", 1, "url_print_cb", "")
        weechat.hook_timer(
            int(weechat.config_get_plugin("reannounce_wait")) * 1000 * 60,
            0,
            0,
            "purge_cb",
            "",
        )
        weechat.hook_config(
            "plugins.var.python.%s.ignore_buffers" % SCRIPT_NAME,
            "ignore_update",
            "",
        )
    color_chat_delimiters = weechat.color("chat_delimiters")
    color_chat_nick = weechat.color("chat_nick")
    color_reset = weechat.color("reset")
    color_chat_buffer = weechat.color("chat_buffer")
    # pretty printing
    script_nick = "%s[%s%s%s]%s" % (
        color_chat_delimiters,
        color_chat_nick,
        weechat.config_get_plugin("global_prefix"),
        color_chat_delimiters,
        color_reset,
    )
