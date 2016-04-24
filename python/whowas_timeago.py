# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2015 - 2016 Jos Ahrens <zarthus@lovebytes.me>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ---
#
# WHOWAS TimeAgo hooks into your WHOWAS calls and adds an easier to read
# timestamp based from the time given by the ircd.
#
# Without this script, you will merely see:
#   [$nick] $server ($timestamp)
# When this script is installed, a new line will display this:
#   [$nick] last seen $time ago
#
# The timestamp sent by the server looks like this:
#   Wed Dec 16 03:06:14 2015
#
# Where time is a short formatted string like so:
#   1 day, 5 hours
#   5 hours, 15 minutes
#   and so on..
#
# Script options:
#   show_errors (default: false, options: true, false)
#     Display script errors (most often caused by unsupported IRCds, and /WHOIS). Asking the user
#     to please report the issue to the maintainer, along with informing how to turn
#     this option off.
#
#     Servers send both numeric 312 on WHOIS and WHOWAS, but they return different things.
#     This often is a cause of an error on WHOIS, and will get noisy very quickly. But this
#     option becomes useful when you're not getting feedback when it was on a WHOWAS.
#
#     Errors are noisy, but easy to fix once known.
#
# This script functions on WeeChat 1.3 and above, supporting both Python 2 and Python 3.
# It probably runs on earlier versions of WeeChat, but has not been tested.
#
# History:
#  version 1.0 - 2015-12-16
#    Script creation
#  version 1.1 - 2015-12-19
#    WHOIS shares the same numeric as WHOWAS uses, and returns different data.
#    This issue has been fixed by defaulting show_errors to false, and displaying extra
#    notices.
#  version 1.2 - 2015-12-19
#    The WHOWAS data is in the UTC timezone, but not everyone is. Ensure we get utctime()

try:
    import weechat as w
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

import datetime
import re


SCRIPT_NAME = "whowas_timeago"
SCRIPT_AUTHOR = "Zarthus <zarthus@lovebytes.me>"
SCRIPT_VERSION = "1.2"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Display a human-readable time string for WHOWAS data"

PARSE_TIMESTAMP_REGEXP = re.compile("^\w{3} (\w{3}) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) (\d{4})$")


def whowas_callback_timestamp(data, signal, signal_data):
    """When the WHOWAS date numeric comes by"""

    parsed = w.info_get_hashtable("irc_message_parse", {"message": signal_data})

    server = signal.split(",")[0]
    nick = parsed["arguments"].split(" ")[1]
    timestamp = parsed["arguments"].split(":", 1)[1]
    buff = find_target_buffer(server, nick)

    n = fmt_nick(nick)
    t = fmt_time(timestamp)

    if not t:
        # This was most likely a WHOIS, and contained the server description.
        if w.config_get_plugin("show_errors") in ["true", "yes", "on"]:
            w.prnt(buff, ("error: Failed to parse timestamp '{}' for {}."
                " You can neglect this error if this was a WHOIS request.").format(timestamp, nick))
            w.prnt(buff, "error: Please report this issue to the maintainer of the {} script.".format(SCRIPT_NAME))
            w.prnt(buff, "error: You can turn this notice off by setting `show_errors' to false.")
    else:
        w.prnt(buff, "{} last seen {} ago".format(n, t))

    return w.WEECHAT_RC_OK


def find_target_buffer(server, nick):
    """Return the buffer the user most likely wants their data printed to"""

    targets = {
        "current": w.current_buffer(),
        "weechat": w.buffer_search_main(),
        "server": w.buffer_search("irc", "server.{}".format(server)),
        "private": w.buffer_search("irc", "{}.{}".format(server, nick))
    }

    opt = w.config_string(w.config_get("irc.msgbuffer.whowas"))
    if not opt:
        opt = w.config_string(w.config_get("irc.look.msgbuffer_fallback"))

    target = ""

    if opt.lower() in targets:
        target = targets[opt]

    return target


def parse_timestamp(timestamp):
    """
    Interpret a string that represents time into a manipulatable object

    Timestamp string looks like this:
      Wed Dec 16 03:06:23 2015
    Tested on the following ircds:
      charybdis
      ircd-seven
      inspircd
      hybrid
    """

    m = PARSE_TIMESTAMP_REGEXP.match(timestamp)

    if not m:
        return False

    month_s, day, hours, mins, secs, year = m.groups()
    month = parse_month(month_s)

    return datetime.datetime(int(year), int(month), int(day), int(hours), int(mins), int(secs))


def parse_month(month):
    """Read the string month returned by the ircd and convert it to a number"""

    months = {
      "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
      "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
      "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    if month not in months:
        if w.config_get_plugin("show_errors") in ["true", "yes", "on"]:
            w.prnt("", "error: Unknown month '{}', probably caused by unsupported ircd.".format(month))
            w.prnt("", "error: Please report this issue to the maintainer of the {} script.".format(SCRIPT_NAME))
            w.prnt("", "error: You can turn this notice off by setting `show_errors' to false.")

        return int(datetime.datetime.utcnow().strftime("%m"))

    return months[month]


def fmt_nick(nick):
    """Format nick in colours for output colouring"""

    green = w.color("green")
    reset = w.color("reset")
    nick_col = w.color(w.info_get("irc_nick_color_name", nick))

    return "{}[{}{}{}]{}".format(green, nick_col, nick, green, reset)


def fmt_time(timestamp):
    """Interpret a timestamp and format it to a time-ago string."""

    then = parse_timestamp(timestamp)
    if not then:
        return False

    diff = datetime.datetime.utcnow() - then
    data = []

    hrdiff = diff.seconds / 3600
    mdiff = diff.seconds % 3600 / 60

    if diff.days != 0:
        data.append("{} day{}".format(diff.days, "s" if diff.days != 1 else  ""))
    if hrdiff != 0:
        data.append("{} hour{}".format(hrdiff, "s" if hrdiff != 1 else ""))
    if mdiff != 0:
        data.append("{} minute{}".format(mdiff, "s" if mdiff != 1 else ""))

    if not data:
         # IRCds will often have forgotten data past a week, so chances are it happened now.
         return str(diff.seconds) + " seconds"
    return ", ".join(data)


if import_ok and w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    settings = {
        "show_errors": ["false", "Display error messages when timestamp cannot be parsed. true or false"]
    }

    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value[0])
            w.config_set_desc_plugin(option, default_value[1])

    w.hook_signal("*,irc_in_312", "whowas_callback_timestamp", "")
