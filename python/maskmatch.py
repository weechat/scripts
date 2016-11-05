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
# Whenever a mode with a hostmask argument is set (like a ban, or a quiet), this
# script compares the mask to anyone in the current channel to see if it matches
# anyone, and lists them accordingly.
#
# This script comes with a command (/maskmatch <hostname>) to perform a match
# before you perform a ban or quiet on anyone, and as well has partial extban support
# in the form of recognizing account names with $a:accountname and $~a
#
# Script options:
#   whitelist, blacklist (default: "", options: see description)
#     The whitelist supports multiple types of arguments. Primarily a server,
#     channel, or combination of the two.
#
#     examples:
#       freenode will match all channels on freenode
#       #freenode will match the channel #freenode on all networks
#       freenode.#freenode will match the channel #freenode on freenode
#
#     Matching objects on the whitelist will only match on these targets.
#     Matching objects on the blacklist will never match on these targets.
#     When both options are set, the whitelist takes precedence over the blacklist.
#     When neither option is set, everything matches.
#
#   disabled (default: false, options: true, false)
#     Relatively straightforward, if you want to disable the listing of users
#     when someone sets a ban, and are just interested in the /modematch command,
#     set this to true.
#
#   ignore_masks (default: *!*@*, options: comma separated string of hostmasks)
#     Some masks (in particular *!*@*) match a large array of users. Hostmasks in
#     this list should never match.
#
#   limit (default: 4, options: integer)
#     The limit indicates how many matches to print before aborting. This is to
#     prevent flood on larger matches. The limit cannot be turned off (it will always
#     be at least 1), but can be set to arbitrarily high numbers.
#
#     When the limit is reached, you will see "... and x more matches".
#
#   match_set, match_unset (default: true, options: true, false)
#     Configure if you want to match only when a mode is set or unset.
#
#     The script will not show matches when both options are set to false.
#
#   matching_modes (default: beIq, options: list of mode characters)
#     List of modes that have a hostmask parameter. In version 1.0, maskmatch does
#     not read the server's isupport to see which modes have parameters to them.
#
#     Because it does not do this, problems may occur if you are on a network that, for example,
#     supports +q as "channel owner" as opposed to quiet. You could either mark the network as
#     blacklisted, or use this option to negate all q matches. In addition to that, you may simply
#     not wish to see matches for invite exceptions or quiets.
#
#   prefix (default: [_script_name_], options: see description)
#     The prefix is the name the script assumes in front of the printing message.
#     This option can be any type of string, inherit from network_prefix, or more.
#     Multiple special options can be in place.
#
#     In addition to this, if the prefix is surrounded in [] brackets, the prefix_color
#     will be assumed upon the brackets, rather than the prefix itself.
#
#     Special options:
#       _script_name_    - Gets converted into SCRIPT_NAME, which would be maskmatch
#       _prefix_network_ - The option you have set in weechat.look.prefix_network
#       _setter_         - The person whom set the mode
#       _target_         - The person whom the mode was set on. This is their nick, not the hostmask
#
#     The _setter_ and _target_ options do not honor prefix_color, and will always have their own
#     weechat color.
#
#   prefix_color (default: green, options: any weechat supported color)
#     The prefix color is the color the prefix (or the brackets surrounding the prefix)
#     will have. This can be any weechat supported color.
#
#   print_as_list (default: false, options: true, false)
#     Instead of printing a newline per message, print it as a large list instead.
#     This formatting is more compact, and will consume less space. But may as direct
#     result be less readable for larger limits.
#
#   sorting (default: alpha_ignore_case, options: none, alpha, alpha_ignore_case)
#     Sort matches by their name - either alphabetically, alphabetically with case insensitivity,
#     or none at all.
#
#   verbose (default: false, options: true, false)
#     When verbose is on, you will be informed when there aren't any matches found.
#
# This script functions on WeeChat 1.3 and above, supporting both Python 2 and Python 3.
# It probably runs on earlier versions of WeeChat, but has not been tested.
#
# History:
#  version 1.0 - 2015-12-19
#    Script creation
#  version 1.1 - 2015-12-19
#    cmd_maskmatch: Validate if existing buffer is a channel
#    match_against_nicklist:
#      Fix wrong comparison.
#      Optimize iterating through the nicklist by not constantly reperforming some
#        calculations, and instead storing them into boolean values.
#    Code formatting fixes
#  version 1.2 - 2015-12-31
#    bug fix: Add missing parenthesis to ensure proper .format() calls.
#  version 1.3 - 2016-09-21
#    consistency: honour weechat.look.prefix_same_nick in print_as_list(), also now
#      use the name in both messages of print_as_list(). This change is slightly
#      backwards-incompatible. You will need to edit either
#      weechat.look.prefix_same_nick with a space (" ") to get the old behaviour,
#      or set the script option prefix to a space (also not ideal.)
#
#      Feel free to provide feedback on this change if you liked the old behaviour
#      and don't find the alternate solutions acceptable. Considering the size of
#      this change you could easily revert back to 1.2. Future releases will provide
#      a solution if the old behaviour was liked.
#  version 1.4 - 2016-10-11
#    bug fix: works around a problem where modes with arguments are not being filtered out,
#      and instead maskmatch starts matching against the wrong argument.
#      This is a bit of a cheesy hack. Anyone is welcome to improve the logic on this.
#      relevant: https://github.com/Zarthus/weechat-scripts/issues/3

try:
    import weechat as w
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False


SCRIPT_NAME = "maskmatch"
SCRIPT_AUTHOR = "Zarthus <zarthus@lovebytes.me>"
SCRIPT_VERSION = "1.4"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Display who got banned (quieted, excepted, etc.) when a mode with a hostmask argument is set"
SCRIPT_COMMAND = "maskmatch"


def cmd_maskmatch(data, buffer, mask):
    """Trigger for /maskmatch <hostmask>"""

    is_channel = False
    try:
        server, channel = w.buffer_get_string(buffer, "name").split(".", 1)
        is_channel = True
    except ValueError:
        is_channel = False
        w.prnt(buffer, "error: Active buffer does not appear to be a channel.")

    if not is_channel:
        return w.WEECHAT_RC_OK

    matches = match_against_nicklist(server, channel, mask)

    print_matches(buffer, matches, {"setter": "maskmatch", "mode": "special", "set": True, "mask": mask})

    return w.WEECHAT_RC_OK

def on_channel_mode(data, signal, signal_data):
    """Whenever a channel mode is set."""

    if w.config_get_plugin("disabled") in ["true", "yes"]:
        return w.WEECHAT_RC_OK

    parsed = w.info_get_hashtable("irc_message_parse", {"message": signal_data})

    server = signal.split(",")[0]
    channel = parsed["channel"]

    if not should_match(server, channel):
        return w.WEECHAT_RC_OK

    chars = w.config_get_plugin("matching_modes")
    modes_set = parsed["text"].split(" ")[0]
    found = False

    for c in chars:
        if c in modes_set:
            found = True
            break

    if not found:
        return w.WEECHAT_RC_OK

    modes = parse_modes(parsed["text"])

    for mode in modes:
        mode["setter"] = parsed["nick"]
        match_mode(server, channel, mode)

    return w.WEECHAT_RC_OK


def match_mode(server, channel, data):
    """When the matching mode should be compared against the userlist."""

    if is_mask_ignored(data["mask"]):
        return False

    if w.config_get_plugin("match_unset") not in ["true", "yes"] and not data["set"]:
        return False

    if w.config_get_plugin("match_set") not in ["true", "yes"] and data["set"]:
        return False

    target = w.buffer_search("irc", "{}.{}".format(server, channel))

    matches = match_against_nicklist(server, channel, data["mask"])
    print_matches(target, matches, data)

    return True


def parse_modes(text):
    """Go through the mode string (+bbb arg1 arg2 arg3) and split them up, discarding unsupported modes"""

    modes, args = text.split(" ", 1)
    masks = args.split(" ")
    chars = w.config_get_plugin("matching_modes")

    toggle = None
    i = 0
    ret = []

    for c in modes:
        if c == "+" or c == "-":
            toggle = c == "+"
            continue

        if c not in chars:
            if c in ["I", "k", "e", "b", "q"] or not is_maskmatch_mask(masks[i]):  # TODO: look in isupport CHANMODES and PREFIX
                del masks[i]
            continue

        ret.append({"set": toggle, "mode": c, "mask": masks[i]})
        i += 1

    return ret


def match_list_item(server, channel, item):
    """Match a list item against a server.channel, channel, or server combination."""

    if "." in item:
        if "{}.{}".format(server, channel) == item:
            return True
    else:
        if channel == item or server == item:
            return True

    return False


def should_match(server, channel):
    """Validate if the server.channel combination is in any of the white or blacklist items."""

    whitelist = w.config_get_plugin("whitelist")
    blacklist = w.config_get_plugin("blacklist")

    if not whitelist and not blacklist:
        return True

    if whitelist:
        wl = whitelist.split(",")
        for item in wl:
            if match_list_item(server, channel, item):
                return True
        return False
    else:
        bl = blacklist.split(",")
        for item in bl:
            if match_list_item(server, channel, item):
                return False
        return True

def is_maskmatch_mask(mask):
    """Validate if a mask is a valid IRC mask we support"""

    # author comment: if we ever need regex for more than just
    # this, this statement could be replaced with a regex
    # that is more accurate. /\$~a|\$a:[^ ]+|[^! ]+![^@ ]+@/ or the likes.

    return "$~a" in mask or "$a:" in mask or ("!" in mask and "@" in mask)


def is_mask_ignored(mask):
    """Validate if banmask is in the ignored banmask list."""

    ignored = w.config_get_plugin("ignore_masks").split(",")

    for banmask in ignored:
        if mask == banmask:
            return True
    return False


def match_against_nicklist(server, channel, hostmask):
    """Compare the hostmask against all users in the channel"""

    infolist = w.infolist_get("irc_nick", "", "{},{}".format(server, channel))

    if "$a:" in hostmask or "$~a" in hostmask:
        field = "account"
        hostmask = hostmask.replace("$a:", "")
        hostfield = False
    else:
        field = "host"
        hostfield = True

    extban_unreg = hostmask == "$~a"
    matches = []

    while w.infolist_next(infolist):
        name = w.infolist_string(infolist, "name")

        if hostfield:
            host = name + "!" + w.infolist_string(infolist, field)
        else:
            host = w.infolist_string(infolist, field)

        if ((extban_unreg and host == "*") or
            (not extban_unreg and w.string_match(host, hostmask, 0))):
            matches.append(name)

    w.infolist_free(infolist)
    return matches


def print_matches(target, matches, data):
    """Print all matching masks to the target channel"""

    verbose = w.config_get_plugin("verbose") in ["true", "yes"]
    limit = int(w.config_get_plugin("limit"))

    if limit < 1:
        limit = 1

    total = len(matches)
    if total == 0:
        if verbose or data["mode"] == "special":
            w.prnt(target, "{}\tNo matches for {}".format(fmt_prefix(data).replace("_target_", ""), fmt_banmask(data["mask"])))
        return

    sorting = w.config_get_plugin("sorting")
    if sorting == "alpha":
       matches = sorted(matches)
    elif sorting == "alpha_ignore_case":
       matches = sorted(matches, key=str.lower)

    if w.config_get_plugin("print_as_list") in ["true", "yes"]:
        print_as_list(target, matches, data, limit, total)
    else:
        print_as_lines(target, matches, data, limit, total)

def print_as_list(target, matches, data, limit, total):
    """Prints the output as a comma-separated list of nicks."""

    col = w.color(w.info_get("irc_nick_color_name", data["setter"]))
    pf = fmt_prefix(data).replace("_target_", "")

    s = "{}\tThe following {} {}"
    if data["mode"] == "special":
        w.prnt(target, s.format(pf, "nick matches" if total == 1 else "nicks match", fmt_banmask(data["mask"])))
    else:
        w.prnt(target, (s + ", {} by {}{}{}").format(
           pf, "nick matches" if total == 1 else "nicks match",
           fmt_banmask(data["mask"]), fmt_mode_char(data["mode"]), col,
           data["setter"], w.color("reset")
        ))

    nicks = []
    remainder = len(matches) - limit
    i = 0
    for name in matches:
       nicks.append("{}{}{}".format(w.color(w.info_get("irc_nick_color_name", name)), name, w.color("reset")))
       i += 1

       if i >= limit:
           break

    if w.config_string(w.config_get("weechat.look.prefix_same_nick")):
        pf = (w.color(w.config_get_plugin("prefix_color")) +
          w.config_string(w.config_get("weechat.look.prefix_same_nick")) +
          w.color("reset"))

    printstr = "{}\t{}".format(pf, ", ".join(nicks))
    if remainder > 0:
        printstr += ", and {} more..".format(remainder)
    w.prnt(target, printstr)


def print_as_lines(target, matches, data, limit, total):
    """Prints the output as a line-separated list of nicks."""

    prefix = fmt_prefix(data)
    mstring = "{}{}".format(fmt_mode_char(data["mode"]), "" if data["set"] else " removal")
    mask = fmt_banmask(data["mask"])
    target_in_prefix = "_target_" in prefix
    i = 0

    for name in matches:
        if target_in_prefix:
            pf = prefix.replace("_target_", "{}{}{}".format(
                w.color(w.info_get("irc_nick_color_name", name)),
                name, w.color("reset")))
        else:
            pf = prefix

        if (total - (limit - i) == 1) or (i >= limit):
            left = total - i
            left -= 1 if target_in_prefix else 0

            w.prnt(target, "{}\tand {} more match{}..".format(pf, left, "es" if left != 1 else ""))
            break

        if target_in_prefix:
            w.prnt(target, "{}\tmatches {} {}".format(pf, mstring, mask))
        else:
            w.prnt(target, "{}\t{} {} matches {}".format(pf, mstring, mask, fmt_nick(name)))
        i += 1


def fmt_banmask(mask):
    """Formats a banmask"""

    green = w.color("green")
    reset = w.color("reset")

    return "{}[{}{}{}]{}".format(green, reset, mask, green, reset)


def fmt_mode_char(char):
    """Translate a mode character into a readable string"""

    chars = {
        "b": "ban",
        "e": "ban exception",
        "q": "quiet",
        "I": "invite exception",
        "special": "testing hostmask"
    }

    if char in chars:
        return chars[char]
    return "mode " + char


def fmt_nick(nick):
    """Format nick in colours for output colouring"""

    green = w.color("green")
    reset = w.color("reset")
    nick_col = w.color(w.info_get("irc_nick_color_name", nick))

    return "{}[{}{}{}]{}".format(green, nick_col, nick, green, reset)


def fmt_prefix(data):
    """Read and transform the prefix as per user settings"""

    fmt = w.config_get_plugin("prefix")

    if "_script_name_" in fmt:
        fmt = fmt.replace("_script_name_", SCRIPT_NAME)
    if "_setter_" in fmt:
        fmt = fmt.replace("_setter_", data["setter"])
    if "_prefix_network_" in fmt:
        fmt = fmt.replace("_prefix_network_", w.config_string(w.config_get("weechat.look.prefix_network")))
    col = w.config_get_plugin("prefix_color")


    pfcol = w.color(col)
    reset = w.color("reset")

    if w.string_match(fmt, "[*]", 0):
        fmt = fmt.replace("[", "{}[{}".format(pfcol, reset)).replace("]", "{}]{}".format(pfcol, reset))
    else:
        fmt = "{}{}{}".format(pfcol, fmt, reset)

    return fmt


if import_ok and w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    settings = {
        "blacklist": ["", "List of servers, channels, or server.channel combinations this should not be done for (whitelist takes precedence). Comma separated string"],
        "disabled": ["false", "Set this to true to entirely disable mode matching, and just allow use for the /maskmatch command. Boolean"],
        "ignore_masks": ["*!*@*", "Hostmasks that are too broad that should be ignored. Comma separated string"],
        "limit": ["4", "How many matches should be displayed at maximum? Number"],
        "match_set": ["true", "Match when a mode gets set. Boolean"],
        "match_unset": ["true", "Match when a mode gets unset. Boolean"],
        "matching_modes": ["bIqe", "List of mode characters to match on, every character represents a mode."],
        "prefix": ["_script_name_", "The name the script will have. Special options: _script_name_, _prefix_network_, _setter_, _target_"],
        "prefix_color": ["green", "The colour the prefix will have. If prefix is wrapped in brackets, the brackets will have this color. Any weechat-supported color"],
        "print_as_list": ["false", "Print as one large list, less information - but can fit more names at cost of readability. Boolean"],
        "sorting": ["alpha_ignore_case", "Sort names alphabetically or not. none, alpha, or alpha_ignore_case"],
        "verbose": ["false", "Print also if no matches are found. Boolean"],
        "whitelist": ["", "List of servers, channels, or server.channel combinations this should be done for. Comma separated string"]
   }

    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value[0])
            w.config_set_desc_plugin(option, default_value[1])

    w.hook_command(
        SCRIPT_COMMAND,
        ("Compare a hostmask against the active channel to see how much people it would affect."
         "\n\nA fully qualified hostname should be used in most cases, as it might give unexpected results "
         "when this is not done."
         "\n\nMaskmatch compares against the users in the active channel."
         "\n\nYou can also use account extbans like so: $a:account, $~a."
         " Full extban support is not implemented."),
        "<hostmask>",
        ("The argument <hostmask> is the hostmask to compare against in the active channel, "
         "and should be a fully qualified hostname (*!*@* format), or an account extban."),
        "", "cmd_maskmatch", ""
    )

    w.hook_signal("*,irc_in_MODE", "on_channel_mode", "")

