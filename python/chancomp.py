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
# This script compares channels with a different user via WHOIS and returns which
# channels you share. The script comes with a command that can be used to force
# comparisons (/chancomp <nick>). Depending on your settings, the script will also
# function during normal /whois requests and alternatively offer extra messages
# when the verbose setting is turned on.
#
# Script options:
#   compare_only_on_command (default: off, options: on, off)
#     Require usage of /chancomp to do comparisons, and do not perform comparisons on
#     normal /whois requests.
#
#   ignored_servers (default: "", expects a comma separated string of servers to ignore.)
#     The script does not do comparisons on ignored servers. This setting expects
#     a comma separated list of servers (i.e.: "freenode,notfreenode") - ignored
#     servers will stop /chancomp from functioning and will not display comparisons
#     in your /whois data.
#
#   output_priority (default: smart, options: smart, shared, not_shared)
#     In order to not display too much information to consume, the output_priority
#     option allows you to either set a constant value to be displayed. `shared` will
#     only ever list comparisons of channels you both share, `not_shared` will do the
#     opposite: only list channels you do not share. The `smart` setting looks at
#     how many channels there are, and list the channels with the fewest amount of channels.
#
#   sorting (default: none, options: none, alpha, alpha_ignore_case)
#     In order to make it easier to do comparisons, sorting options are allowed
#     so that you roughly can know where to look. The none option does not ensure
#     any sorting at all, alpha sorts alphabetically, and alpha_ignore_case sorts
#     alphabetically but makes no distinguishment between 'a' or 'A'
#
#   verbose_output (default: on, options: on, off)
#     WHOIS comparisons always print something when verbose_output is on and an
#     unique case is occurring. For example, if you and the target are in the same channels,
#     verbose_output will allow "All channels are shared" to be printed, as opposed to
#     listing all channels. When the setting is off, nothing gets printed.
#
# This script functions on WeeChat 1.3 and above, supporting both Python 2 and Python 3.
# It probably runs on earlier versions of WeeChat, but has not been tested.
#
# History:
#  version 1.0 - 2015-10-29
#    Script creation
#  version 1.1 - 2015-12-16
#    Honour irc.look.msgbuffer_fallback
#  version 1.2 - 2023-02-05
#    Replace command /WHOIS by /whois (compatibility with WeeChat 3.9)
#
# TODOs:
#  - Possibly support a verbose output of "sharing all their channels"
#     when you and that user share all channels they are in. Currently
#     the script only looks for all channels you're in, and when that
#     is equal to the amount of channels they're in, it confirms all
#     channels are shared.
#     In addition, if the user is none, print "the target is in no channels"

try:
    import weechat as w
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

import re


SCRIPT_NAME = "chancomp"
SCRIPT_AUTHOR = "Zarthus <zarthus@lovebytes.me>"
SCRIPT_VERSION = "1.2"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "List shared channels with user on command or WHOIS"
SCRIPT_COMMAND = "chancomp"

_force_comparison = False  # Global variable set to True whenever a manual channel comparison is requested
_shared_channels = {"shared": [], "not_shared": []}


# Commands and callbacks
def cmd_chancomp(data, buffer, target):
    """Trigger for /chancomp <nick>"""

    global _force_comparison
    _force_comparison = True
    w.command("", "/whois {}".format(target))

    return w.WEECHAT_RC_OK


def whois_callback_chan(data, signal, signal_data):
    """When the WHOIS channel numeric comes by"""

    server = signal.split(",")[0]
    if not should_compare_channels(server):
        return w.WEECHAT_RC_OK

    chanlist = filter_channels_by_server(retrieve_channels(server), server)

    parsed = w.info_get_hashtable("irc_message_parse", {"message": signal_data})
    chanlist_target = parsed["text"].strip().split(":")[1]

    whois_regex = create_whois_regex_from_isupport(server)
    chanlist_target = whois_regex.sub(r"\1", chanlist_target).split(" ")

    global _shared_channels
    comparison = compare_channels(chanlist, chanlist_target)
    _shared_channels["shared"] += comparison["shared"]
    _shared_channels["not_shared"] += comparison["not_shared"]

    return w.WEECHAT_RC_OK


def whois_callback_afterchan(data, signal, signal_data):
    """When the WHOIS server info numeric comes by"""

    server = signal.split(",")[0]
    if not should_compare_channels(server):
        return w.WEECHAT_RC_OK

    nick = w.info_get_hashtable("irc_message_parse", {"message": signal_data})["arguments"].split(" ")[1]
    print_shared_list(server, nick)

    global _force_comparison
    if _force_comparison:
        # This was a forced comparison request.
        _force_comparison = False

    return w.WEECHAT_RC_OK


# Utility functions
def compare_channels(chanlist, chanlist_target):
    """Return a list of channels that are in both lists"""

    shared_channels = []
    not_shared_channels = []

    for chan in chanlist:
        if chan in chanlist_target:
            shared_channels.append(chan)
        else:
            not_shared_channels.append(chan)

    return {"shared": shared_channels, "not_shared": not_shared_channels}


def format_shared_channels(channels, current_channels):
    """Take a list of channels and format it into a displayable string"""

    count_shared = len(channels["shared"])
    count_total = len(current_channels)
    verbose = w.config_get_plugin("verbose_output") in ["true", "on"]
    output_priority = w.config_get_plugin("output_priority")

    if count_total == count_shared:
        if verbose:
            return "All channels are shared"
        return None

    if not count_shared:
        if verbose:
            return "No channels are shared"
        return None

    if output_priority == "not_shared" or (output_priority == "smart" and count_shared > count_total / 2):
        output = ", ".join(sort_output(channels["not_shared"]))
        append = ", not sharing"
    else:
        output = ", ".join(sort_output(channels["shared"]))
        append = ""

    return "Sharing {}/{} channels{}: {}".format(count_shared, count_total, append, output)


def sort_output(data):
    """Sort WHOIS output by user specification, default is no sorting at all"""

    sorting = w.config_get_plugin("sorting")
    sortings = ["alpha", "alpha_ignore_case"]

    if sorting in sortings:
        if sorting == "alpha":
            data = sorted(data)
        if sorting == "alpha_ignore_case":
            data = sorted(data, key=str.lower)

    return data


def filter_channels_by_server(channels, server):
    """Remove channels that are on the designated server"""

    chans = []

    for channel in channels:
        sv, chan = channel.split(".", 1)

        if sv == server:
            chans.append(chan)

    return chans


def retrieve_channels(server):
    """Get a list of the channels the user is in"""

    isupport_chantypes = w.info_get("irc_server_isupport_value", "{},CHANTYPES".format(server))
    ischan_regex = re.compile("^{}\.[{}]".format(re.escape(server), re.escape(isupport_chantypes)))

    chans = []
    infolist = w.infolist_get("buffer", "", "")

    while w.infolist_next(infolist):
        bname = w.infolist_string(infolist, "name")

        if ischan_regex.match(bname):
            chans.append(bname)

    w.infolist_free(infolist)
    return chans


def find_target_buffer(server, nick):
    """Return the buffer the user most likely wants their data printed to"""

    targets = {
        "current": w.current_buffer(),
        "weechat": w.buffer_search_main(),
        "server": w.buffer_search("irc", "server.{}".format(server)),
        "private": w.buffer_search("irc", "{}.{}".format(server, nick))
    }

    opt = w.config_string(w.config_get("irc.msgbuffer.whois"))
    if not opt:
        opt = w.config_string(w.config_get("irc.look.msgbuffer_fallback"))

    target = ""

    if opt.lower() in targets:
        target = targets[opt]

    return target


def print_shared_list(server, nick):
    """Format and print the shared channel list"""

    global _shared_channels
    if _shared_channels:
        result = format_shared_channels(_shared_channels, filter_channels_by_server(retrieve_channels(server), server))

        if result:
            w.prnt(find_target_buffer(server, nick), fmt_nick(nick) + " " + result)

    _shared_channels = {"shared": [], "not_shared": []}


def should_compare_channels(server):
    """Determine if we should compare the channels"""

    if server in w.config_get_plugin("ignored_servers").replace(" ", "").split(","):
        return False

    if w.config_get_plugin("compare_only_on_command") in ["true", "on"] and not _force_comparison:
        return False

    return True


def create_whois_regex_from_isupport(server):
    """Look into server ISUPPORT to create the ideal regex for removing channel modes from WHOIS output"""

    isupport_prefix = w.info_get("irc_server_isupport_value", "{},PREFIX".format(server)).split(")")[1]
    isupport_chantypes = w.info_get("irc_server_isupport_value", "{},CHANTYPES".format(server))

    # Strip modes from WHOIS output.
    whois_regex = re.compile(r"(?:[{}]{})?(([{}])[^ ]+)".format(
        re.escape(isupport_prefix),
        "{1," + str(len(isupport_prefix)) + "}",
        re.escape(isupport_chantypes)
    ))

    return whois_regex


# Formatting and colour functions/utilities.
def fmt_nick(nick):
    """Format nick in colours for output colouring"""

    green = w.color("green")
    reset = w.color("reset")
    nick_col = w.color(w.info_get("irc_nick_color_name", nick))

    return "{}[{}{}{}]{}".format(green, nick_col, nick, green, reset)


if import_ok and w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    settings = {
        "compare_only_on_command": ["off", "Specifically require {} for comparisons?".format(SCRIPT_COMMAND)],
        "ignored_servers": ["", "Servers to ignore comparisons with, comma separated."],
        "output_priority": ["shared", "How to display output? smart, shared, not_shared"],
        "sorting": ["none", "Ensure sorting shared channel WHOIS output? none, alpha, alpha_ignore_case"],
        "verbose_output": ["on", "Also show output when all or none channels are shared"]
    }

    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value[0])
            w.config_set_desc_plugin(option, default_value[1])

    w.hook_command(
        SCRIPT_COMMAND,
        ("Compare channels you share with <nick> on the current network.\n"
         "Hooks into WHOIS output and can be triggered manually via a command."),
        "<nick>", "Nickname to issue a WHOIS on and compare channels with.",
        "", "cmd_chancomp", ""
    )

    w.hook_signal("*,irc_in_319", "whois_callback_chan", "")
    w.hook_signal("*,irc_in_312", "whois_callback_afterchan", "")
