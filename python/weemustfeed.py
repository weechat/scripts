# -*- coding: utf-8 -*-
# Licensed under the MIT license:
# Copyright (c) 2013 Bit Shift <bitshift@bigmacintosh.net>
# Copyright (c) 2016 Pol Van Aubel <dev@polvanaubel.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# http://www.opensource.org/licenses/mit-license.php
#
# Revision log:
# 0.3   Pol Van Aubel <dev@polvanaubel.com>
#       Make Python3 compatible.
#       Feed fetching should now timeout after 15 seconds.
#       Handle negative return values correctly.
#       Fix deleting from active iteration object in unload.
#
# 0.2.3 Pol Van Aubel <dev@polvanaubel.com>
#       Changed weechat.prnt to weechat.prnt_date_tags where messages
#       are not a direct result from user input; errors get tagged with
#       irc_error and notify_message, messages get tagged with
#       notify_message.
#
# 0.2.2 Version from Bit Shift

import weechat
import string
import feedparser

import sys # Only required for python version check.
PY2 = sys.version_info < (3,)

weechat.register(
        "weemustfeed",
        "Bit Shift <bitshift@bigmacintosh.net>",
        "0.3",
        "MIT",
        "RSS/Atom/RDF aggregator for weechat",
        "",
        ""
        )


default_settings = {
        "interval": "300",
        "feeds": ""
        }

weemustfeed_buffer = None
weemustfeed_timer = None
fetch_hooks = {}
updating = set()
partial_feeds = {}

help_message = """
COMMANDS:
a <name> <url>        Add a feed with display name of <name> and URL of <url>.
d <name>              Delete the feed with display name <name>.
u <name> <url>        Update the feed with display name <name> to use URL <url>.
l                     List all feeds known to WeeMustFeed.
t <name>              Toggle a feed - disable/enable it temporarily without fully removing it.
?                     Display this help message.

CONFIG:
plugins.var.python.weemustfeed.interval
    Interval between update checks, in seconds. Must be a number, but is stored
    as a string. Blame the scripting API.
    default: "300"
""".strip()


def show_help():
    for line in help_message.split("\n"):
        weechat.prnt(weemustfeed_buffer, "\t\t" + line)


def weemustfeed_input_cb(data, buffer, input_data):
    global updating

    chunks = input_data.split()

    if chunks[0] == "a":
        if len(chunks) != 3:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is 'a <name> <url>'.")
            return weechat.WEECHAT_RC_ERROR
        elif any([c not in (string.ascii_letters + string.digits) for c in chunks[1]]):
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Only A-Z, a-z, and 0-9 permitted in names.")
            return weechat.WEECHAT_RC_ERROR
        else:
            current_feeds = weechat.config_get_plugin("feeds").strip().split(";")

            if chunks[1] in current_feeds:
                weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "A feed with that name already exists (note: feed names are case-insensitive).")
                return weechat.WEECHAT_RC_ERROR
            else:
                current_feeds.append(chunks[1])
                weechat.config_set_plugin("feed." + chunks[1].lower() + ".url", chunks[2])
                weechat.config_set_plugin("feeds", ";".join(current_feeds))
                weechat.prnt(weemustfeed_buffer, "Added '" + chunks[1] + "'.")
    elif chunks[0] == "d":
        if len(chunks) != 2:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is 'd <name>'.")
            return weechat.WEECHAT_RC_ERROR
        elif any([c not in (string.ascii_letters + string.digits) for c in chunks[1]]):
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Only A-Z, a-z, and 0-9 permitted in names.")
            return weechat.WEECHAT_RC_ERROR
        else:
            current_feeds = weechat.config_get_plugin("feeds").strip().split(";")
            if not chunks[1] in current_feeds:
                weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "No such feed exists.")
                return weechat.WEECHAT_RC_ERROR
            else:
                current_feeds.remove(chunks[1])
                weechat.config_set_plugin("feeds", ";".join(current_feeds))
                weechat.prnt(weemustfeed_buffer, "Deleted '" + chunks[1] + "'.")
    elif chunks[0] == "u":
        if len(chunks) != 3:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is 'u <name> <url>'.")
            return weechat.WEECHAT_RC_ERROR
        elif any([c not in (string.ascii_letters + string.digits) for c in chunks[1]]):
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Only A-Z, a-z, and 0-9 permitted in names.")
            return weechat.WEECHAT_RC_ERROR
        else:
            current_feeds = weechat.config_get_plugin("feeds").strip().split(";")

            if not chunks[1] in current_feeds:
                weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "No feed with that name currently exists (note: feed names are case-insensitive).")
                return weechat.WEECHAT_RC_ERROR
            else:
                weechat.config_set_plugin("feed." + chunks[1].lower() + ".url", chunks[2])
                weechat.config_set_plugin("feeds", ";".join(current_feeds))
                weechat.prnt(weemustfeed_buffer, "Updated '" + chunks[1] + "'.")
    elif chunks[0] == "l":
        if len(chunks) != 1:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is 'l'.")
            return weechat.WEECHAT_RC_ERROR
        else:
            current_feeds = weechat.config_get_plugin("feeds").strip().split(";")
            for feed in current_feeds:
                if feed != "":
                    if (weechat.config_is_set_plugin("feed." + feed.lower() + ".enabled") and
                        weechat.config_get_plugin("feed." + feed.lower() + ".enabled").lower() != "yes"):
                        feed_status = "disabled"
                    elif not (weechat.config_is_set_plugin("feed." + feed.lower() + ".last_id") and
                              weechat.config_get_plugin("feed." + feed.lower() + ".last_id") != ""):
                        feed_status = "new"
                    elif feed in updating:
                        feed_status = "updating"
                    elif (weechat.config_is_set_plugin("feed." + feed.lower() + ".enabled") and
                          weechat.config_get_plugin("feed." + feed.lower() + ".enabled").lower() != "yes"):
                        feed_status = "disabled"
                    else:
                        feed_status = "enabled"
                    weechat.prnt(weemustfeed_buffer, "\t" + feed + ": " + weechat.config_get_plugin("feed." + feed.lower() + ".url") + " [" + feed_status + "]")
    elif chunks[0] == "t":
        if len(chunks) != 2:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is 't <name>'.")
            return weechat.WEECHAT_RC_ERROR
        elif any([c not in (string.ascii_letters + string.digits) for c in chunks[1]]):
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Only A-Z, a-z, and 0-9 permitted in names.")
            return weechat.WEECHAT_RC_ERROR
        else:
            current_feeds = weechat.config_get_plugin("feeds").strip().split(";")
            if not chunks[1] in current_feeds:
                weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "No such feed exists.")
                return weechat.WEECHAT_RC_ERROR
            else:
                if not weechat.config_is_set_plugin("feed." + chunks[1].lower() + ".enabled"):
                    feed_enabled = True
                else:
                    feed_enabled = (weechat.config_get_plugin("feed." +
                        chunks[1].lower() + ".enabled").lower() == "yes")

                if feed_enabled:
                    weechat.config_set_plugin("feed." + chunks[1].lower() +
                            ".enabled", "no")
                    weechat.prnt(weemustfeed_buffer, "Disabled '" + chunks[1] + "'.")
                else:
                    weechat.config_set_plugin("feed." + chunks[1].lower() +
                            ".enabled", "yes")
                    weechat.prnt(weemustfeed_buffer, "Enabled '" + chunks[1] + "'.")
    elif chunks[0] == "?":
        if len(chunks) != 1:
            weechat.prnt(weemustfeed_buffer, weechat.prefix("error") + "Wrong number of parameters. Syntax is '?'.")
            return weechat.WEECHAT_RC_ERROR
        else:
            show_help()

    return weechat.WEECHAT_RC_OK


def weemustfeed_close_cb(data, buffer):
    global weemustfeed_buffer, weemustfeed_timer

    weemustfeed_buffer = None
    weechat.unhook(weemustfeed_timer)
    for feed in list(fetch_hooks):
        weechat.unhook(fetch_hooks[feed])
        del fetch_hooks[feed]
    weemustfeed_timer = None
    return weechat.WEECHAT_RC_OK


def weemustfeed_command_cb(data, buffer, args):
    global weemustfeed_buffer

    if weemustfeed_buffer is None:
        weemustfeed_buffer = weechat.buffer_new(
                "weemustfeed",
                "weemustfeed_input_cb", "",
                "weemustfeed_close_cb", ""
                )

        weechat.buffer_set(weemustfeed_buffer, "title",
                "WeeMustFeed - a: Add feed, d: Delete feed, u: Update URL, l: List feeds, t: Toggle feed, ?: Show help")

        set_timer()

    weechat.buffer_set(weemustfeed_buffer, "display", "1") # switch to it

    return weechat.WEECHAT_RC_OK


def weemustfeed_reset_timer_cb(data, option, value):
    if weemustfeed_timer is not None:
        unset_timer()
        set_timer()
    return weechat.WEECHAT_RC_OK


def weemustfeed_update_single_feed_cb(feed, command, return_code, out, err):
    global partial_feeds, updating

    if not feed in partial_feeds:
        partial_feeds[feed] = ""

    if return_code == weechat.WEECHAT_HOOK_PROCESS_RUNNING:  # feed not done yet
        partial_feeds[feed] += out
        return weechat.WEECHAT_RC_OK
    elif return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Hook process error for feed '" + feed + "'. === " + command + " === " + out + " === " + err)
        status = weechat.WEECHAT_RC_ERROR
    elif return_code == 1:
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Invalid URL for feed '" + feed + "'.")
        status = weechat.WEECHAT_RC_ERROR
    elif return_code == 2:
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Transfer error while fetching feed '" + feed + "'.")
        status = weechat.WEECHAT_RC_ERROR
    elif return_code == 3:
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Out of memory while fetching feed '" + feed + "'.")
        status = weechat.WEECHAT_RC_ERROR
    elif return_code == 4:
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Error with a file while fetching feed '" + feed + "'.")
        status = weechat.WEECHAT_RC_ERROR
    elif return_code == 0:  # all good, and we have a complete feed
        if not weechat.config_is_set_plugin("feed." + feed.lower() + ".last_id"):
            weechat.config_set_plugin("feed." + feed.lower() + ".last_id", "")
            last_id = ""

        last_id = weechat.config_get_plugin("feed." + feed.lower() + ".last_id")

        parsed_feed = feedparser.parse(partial_feeds[feed] + out)

        entries = list(reversed(parsed_feed.entries))

        for entry in entries:
            if not hasattr(entry, "id"):
                entry.id = entry.link

        if (last_id == "") and len(entries) > 0:
            last_id = entries[-1].id
        else:
            if last_id in [entry.id for entry in entries]:
                only_new = False
            else:
                only_new = True

            for entry in entries:
                if PY2:
                    entrytitle = entry.title.encode("utf-8")
                    entryurl = entry.link.encode("utf-8")
                else:
                    entrytitle = entry.title
                    entryurl = entry.link

                if only_new:
                    weechat.prnt_date_tags(weemustfeed_buffer, 0, "notify_message", "{feed}\t{title} {url}".format(**{
                        "feed": feed,
                        "title": entrytitle,
                        "url": entryurl
                        }))
                    last_id = entry.id
                elif entry.id == last_id:
                    only_new = True  # everything else will be newer

        weechat.config_set_plugin("feed." + feed.lower() + ".last_id", last_id)

        status = weechat.WEECHAT_RC_OK

    else: # Unknown return code. Script must be updated.
        weechat.prnt_date_tags(weemustfeed_buffer, 0,
                "irc_error,notify_message",
                weechat.prefix("error") + "Unknown return code " + return_code + " for feed '" + feed + "'. Script must be updated.")
        status = weechat.WEECHAT_RC_ERROR

    partial_feeds[feed] = ""
    if feed in updating:
        updating.remove(feed)
    if feed in fetch_hooks:
        del fetch_hooks[feed]
    return status


def weemustfeed_update_feeds_cb(data, remaining_calls):
    global updating

    for feed in weechat.config_get_plugin("feeds").strip().split(";"):
        if weechat.config_is_set_plugin("feed." + feed.lower() + ".url"):
            if not (weechat.config_is_set_plugin("feed." + feed.lower() + ".enabled") and
                    weechat.config_get_plugin("feed." + feed.lower() + ".enabled").lower() != "yes"):
                updating.add(feed)
                if not feed in fetch_hooks:
                    fetch_hooks[feed] = weechat.hook_process(
                        "url:" + weechat.config_get_plugin("feed." + feed.lower() + ".url"),
                        15000,
                        "weemustfeed_update_single_feed_cb", feed
                        )
        elif feed != "":
            weechat.prnt_date_tags(weemustfeed_buffer, 0,
                    "irc_error,notify_message",
                    weechat.prefix("error") + "Feed '" + feed + "' has no URL set.")
    return weechat.WEECHAT_RC_OK


def set_timer():
    global weemustfeed_timer

    try:
        timer_interval = int(weechat.config_get_plugin("interval"))
    except ValueError:
        timer_interval = int(default_settings["interval"])

    weemustfeed_timer = weechat.hook_timer(
            timer_interval * 1000,
            0,
            0,
            "weemustfeed_update_feeds_cb", ""
            )


def unset_timer():
    if weemustfeed_timer is not None:
        weechat.unhook(weemustfeed_timer)


def init_script():
    global default_settings

    for option, default_value in list(default_settings.items()):
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    weechat.hook_command(
        "weemustfeed",
        "open/switch to weemustfeed buffer",
        "",
        "",
        "",
        "weemustfeed_command_cb", ""
        )

    weechat.hook_config(
        "plugins.var.python.weemustfeed.interval",
        "weemustfeed_reset_timer_cb", ""
        )


init_script()
