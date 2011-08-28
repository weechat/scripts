# -*- coding: utf-8 -*-
# Copyright (c) 2011 by Jani Kesänen <jani.kesanen@gmail.com>
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
# A common buffer for URLs 
#
# Collects received URLs from public and private messages into a single 
# buffer. This buffer is especially handy if you spend lot's of time afk
# and you don't want to miss any of the cat pictures/videos that were pasted
# while you were doing something meaningful.
#
# This script has been developed for WeeChat version 0.3.5. May not work
# properly (or at all) on older versions.
#
# History:
# 2011-06-07, Jani Kesänen <jani.kesanen@gmail.com>
#   version 0.1: - initial release.
#

SCRIPT_NAME    = "urlbuf"
SCRIPT_AUTHOR  = "Jani Kesänen <jani.kesanen@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "A common buffer for received URLs."

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

import re

octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\.%s){3}' % (octet, octet)
# Base domain regex off RFC 1034 and 1738
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
urlRe = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr), re.I)

urlbuf_buffer = None

urlbuf_settings = {
    "display_active_buffer" : "on",    # on = display URLs from the active buffer
    "display_private"       : "on",    # on = display URLs from private messages
    "display_buffer_number" : "on",    # on = display the buffer number before nick
    "display_nick"          : "off",   # on = display the nick of the user
    "skip_duplicates"       : "on",    # on = skip URL that is already in the urlbuf
    "skip_buffers"          : "",      # a comma separated list of buffer numbers to skip
}


def is_url_listed(buffer, url):
    """ Search for the URL from the buffer lines. """
    infolist = weechat.infolist_get("buffer_lines", buffer, "")

    found = False
    while weechat.infolist_next(infolist):
        message = weechat.infolist_string(infolist, "message").split(' ')[-1]
        if message == url:
            found = True
            break

    weechat.infolist_free(infolist)

    return found


def urlbuf_print_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    """ Called when a message is printed. """
    global urlbuf_buffer, urlbuf_tags

    # Exit immediately if the buffer does not exist
    if not urlbuf_buffer:
        return weechat.WEECHAT_RC_OK

    # Exit if there is not wanted tag in the message
    tagslist = tags.split(",")
    if not "notify_message" in tagslist:
        if weechat.config_get_plugin("display_private") == "on":
           if not "notify_private" in tagslist:
               return weechat.WEECHAT_RC_OK
        else:
           return weechat.WEECHAT_RC_OK

    # Exit if the message came into a buffer that is on the skip list
    buffer_number = str(weechat.buffer_get_integer(buffer, "number"))
    skips = set(weechat.config_get_plugin("skip_buffers").split(","))
    if buffer_number in skips:
        return weechat.WEECHAT_RC_OK

    if weechat.config_get_plugin("display_active_buffer") == "off":
        if buffer_number == weechat.buffer_get_integer(weechat.current_buffer(), "number"):
            return weechat.WEECHAT_RC_OK

    # Process all URLs from the message
    for url in urlRe.findall(message):
        output = ""

        if weechat.config_get_plugin("skip_duplicates") == "on":
            if is_url_listed(urlbuf_buffer, url):
                continue

        if weechat.config_get_plugin("display_buffer_number") == "on":
            output += "%s%-2d " % (weechat.color("reset"), weechat.buffer_get_integer(buffer, "number"))

        if weechat.config_get_plugin("display_nick") == "on":
            output += "%s " % (prefix)

        # Output the formatted URL into the buffer
        weechat.prnt(urlbuf_buffer, output + url)

    return weechat.WEECHAT_RC_OK


def urlbuf_input_cb(data, buffer, input_data):
    """ A Dummy callback for buffer input. """
    return weechat.WEECHAT_RC_OK


def urlbuf_close_cb(data, buffer):
    """ A callback for buffer closing. """
    global urlbuf_buffer

    urlbuf_buffer = None
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "urlbuf_close_cb", ""):
        # Set default settings
        for option, default_value in urlbuf_settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

        urlbuf_buffer = weechat.buffer_search("python", "urlbuf")

        if not urlbuf_buffer:
            # Create urlbuf. Sets notify to 0 as this buffer does not need to
            # be in hotlist.
            urlbuf_buffer = weechat.buffer_new("urlbuf", "urlbuf_input_cb", \
                                               "", "urlbuf_close_cb", "")
            weechat.buffer_set(urlbuf_buffer, "title", "URL buffer")
            weechat.buffer_set(urlbuf_buffer, "notify", "0")
            weechat.buffer_set(urlbuf_buffer, "nicklist", "0")

        # Hook all public and private messages (some may think this is too limiting)
        weechat.hook_print("", "notify_message", "", 1, "urlbuf_print_cb", "")
        weechat.hook_print("", "notify_private", "", 1, "urlbuf_print_cb", "")
