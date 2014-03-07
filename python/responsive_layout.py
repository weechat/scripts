# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Stefan Wold <ratler@stderr.eu>
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
# (This script requires WeeChat 0.4.3 or higher).
#
# WeeChat script for responsive layout based on terminal height and width.
#
#
# Source and changes available on GitHUB: https://github.com/Ratler/ratlers-weechat-scripts
#
# Commands:
#  /rlayout


SCRIPT_NAME    = "responsive_layout"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.7"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Responsive layout will automatically apply layouts based on the terminals current size."
SCRIPT_COMMAND = "rlayout"

SETTINGS = {
    "default_nicklist": ("on", "Global setting to always show nicklist when layout switches."),
               "debug": ("off", "Script debug output"),

}

LAYOUT_LIST = []

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

try:
    import re
    from operator import itemgetter
except ImportError as err:
    print "Missing module(s) for %s: %s" % (SCRIPT_NAME, err)
    import_ok = False


def _print(message, buf=""):
    weechat.prnt(buf, "%s: %s" % (SCRIPT_NAME, message))


def _debug(message, buf=""):
    if weechat.config_get_plugin('debug') == 'on':
        weechat.prnt(buf, "+++ %s (debug): %s" % (SCRIPT_NAME, message))


def responsive_cb(data, signal, signal_data):
    term_height = int(weechat.info_get("term_height", ""))
    term_width = int(weechat.info_get("term_width", ""))

    try:
        apply_layout = None
        for layout, width, height in LAYOUT_LIST:
            if term_height <= int(height) or term_width <= int(width):
                apply_layout = layout
                break

        if apply_layout is None:
            # Always apply the last layout if term width/height is larger than configured layouts
            apply_layout = LAYOUT_LIST[-1][0]

        if layout_exist(apply_layout) and not layout_current(apply_layout):
            _print("Applying layout %s" % apply_layout)
            weechat.command("", "/layout apply %s" % apply_layout)
            toggle_nick_list(apply_layout)

        weechat.bar_item_update("rlayout")
    except ValueError:
        _print("Height or width is not in number form, ignoring.")

    return weechat.WEECHAT_RC_OK


def layout_current(layout):
    infolist = weechat.infolist_get("layout", "", "")
    current = False

    while weechat.infolist_next(infolist):
        if weechat.infolist_integer(infolist, "current_layout") == 1 and \
           weechat.infolist_string(infolist, "name") == layout:
            current = True
            break

    weechat.infolist_free(infolist)
    return current


def layout_exist(layout):
    infolist = weechat.infolist_get("layout", "", "")
    found = False

    while weechat.infolist_next(infolist):
        if layout == weechat.infolist_string(infolist, "name"):
            found = True
            break

    weechat.infolist_free(infolist)
    return found


def toggle_nick_list(layout):
    """
    Check configuration whether nick list bar should be on or off for the provided layout.
    """
    value = weechat.config_get_plugin("layout.%s.nicklist" % layout)
    if value == "":
        value = weechat.config_get_plugin("default_nicklist")

    if value == "on":
        weechat.command("", "/bar show nicklist")
    elif value == "off":
        weechat.command("", "/bar hide nicklist")


def rlayouts_list():
    """
    Return a list of configured rlayouts.
    """
    layouts = []
    pattern = re.compile(r"^plugins\.var\.python\.%s\.layout\.(.+)\." % SCRIPT_NAME)
    infolist = weechat.infolist_get("option", "", "plugins.var.python.%s.layout.*" % SCRIPT_NAME)

    while weechat.infolist_next(infolist):
        layout = re.search(pattern, weechat.infolist_string(infolist, "full_name")).groups()
        if layout[0] not in layouts:
            layouts.append(layout[0])

    weechat.infolist_free(infolist)

    return layouts


def update_layout_list():
    """
    Updates global LAYOUT_LIST with a sorted array containing layout tuples, ie (layout_name, width, height)
    """
    global LAYOUT_LIST

    layout_tuples = []

    for layout in rlayouts_list():
        width = weechat.config_get_plugin("layout.%s.width" % layout)
        height = weechat.config_get_plugin("layout.%s.height" % layout)

        if width is not "" and height is not "":
            layout_tuples.append((layout, int(width), int(height)))

    layout_tuples.sort(key=itemgetter(1, 2))
    _debug("update_layout_list(%s)" % layout_tuples)
    LAYOUT_LIST = layout_tuples


def rlayout_cmd_cb(data, buffer, args):
    """
    Callback for /rlayout command.
    """
    if args == "":
        weechat.command("", "/help %s" % SCRIPT_COMMAND)
        return weechat.WEECHAT_RC_OK

    argv = args.strip().split(" ", 1)
    if len(argv) == 0:
        return weechat.WEECHAT_RC_OK

    short_cmds = ["list", "terminal"]
    if argv[0] not in short_cmds and len(argv) < 2:
        _print("Too few arguments for option '%s'." % argv[0])
        return weechat.WEECHAT_RC_OK

    if argv[0] == "size":
        try:
            layout, width, height = argv[1].split(" ")

            if layout_exist(layout):
                weechat.config_set_plugin("layout.%s.width" % layout, width)
                weechat.config_set_plugin("layout.%s.height" % layout, height)
                update_layout_list()
            else:
                _print("Layout '%s' doesn't exist, see /help layout to create one." % layout)
        except ValueError:
            _print("Too few arguments for option '%s'" % argv[0])
    elif argv[0] == "nicklist":
        try:
            layout, nicklist = argv[1].split(" ")

            if layout_exist(layout):
                if nicklist == "on" or nicklist == "off":
                    weechat.config_set_plugin("layout.%s.nicklist" % layout, nicklist)
                else:
                    _print("Invalid argument '%s' for option '%s'." % (nicklist, argv[0]))
            else:
                _print("Layout '%s' doesn't exist, see /help layout to create one." % layout)
        except ValueError:
            _print("Too few arguments for option '%s'" % argv[0])
    elif argv[0] == "default_nicklist" or argv[0] == "debug":
        if argv[1] == "on" or argv[1] == "off":
            weechat.config_set_plugin(argv[0], argv[1])
        else:
            _print("Invalid argument '%s' for option '%s'" % (argv[1], argv[0]))
    elif argv[0] == "remove":
        if argv[1] in rlayouts_list():
            for option in ["width", "height", "nicklist"]:
                weechat.config_unset_plugin("layout.%s.%s" % (argv[1], option))
            _print("Removed rlayout '%s'" % argv[1])
        else:
            _print("Could not remove '%s', rlayout not found." % argv[1])
    elif argv[0] == "list":
        if len(rlayouts_list()) == 0:
            _print("No configuration set.")
        else:
            for rlayout in rlayouts_list():
                width = weechat.config_get_plugin("layout.%s.width" % rlayout)
                height = weechat.config_get_plugin("layout.%s.height" % rlayout)
                nicklist = weechat.config_get_plugin("layout.%s.nicklist" % rlayout)
                msg = "[%s] width: %s, height: %s" % (rlayout, width, height)
                if nicklist is not "":
                    msg += ", nicklist: %s" % nicklist
                _print(msg)
    elif argv[0] == "terminal":
        term_height = int(weechat.info_get("term_height", ""))
        term_width = int(weechat.info_get("term_width", ""))
        _print("Current terminal width x height is: %s x %s" % (term_width, term_height))

    return weechat.WEECHAT_RC_OK


def rlayout_bar_cb(data, item, window):
    infolist = weechat.infolist_get("layout", "", "")
    layout = None

    while weechat.infolist_next(infolist):
        if weechat.infolist_integer(infolist, "current_layout") == 1:
            layout = weechat.infolist_string(infolist, "name")
            break

    weechat.infolist_free(infolist)

    if layout is None:
        return ""
    else:
        term_height = int(weechat.info_get("term_height", ""))
        term_width = int(weechat.info_get("term_width", ""))

    return "%s (%sx%s)" % (layout, term_width, term_height)


def rlayout_completion_bool_cb(data, completion_item, buffer, completion):
    for bool in ("on", "off"):
        weechat.hook_completion_list_add(completion, bool, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


def rlayout_completion_layout_list_cb(data, completion_item, buffer, completion):
    for rlayout in rlayouts_list():
        weechat.hook_completion_list_add(completion, rlayout, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


def config_cb(data, option, value):
    update_layout_list()
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040300:
            _print("Requires WeeChat >= 0.4.3 for terminal height and width support.")
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND,
                             "WeeChat responsive layout configuration",
                             "size <layout> <width> <height> || nicklist <layout> <on|off> || default_nicklist <on|off>"
                             " || remove <layout> || list || terminal || debug <on|off>",
                             "            size: set max size (width and height) for layout to be automatically applied\n"
                             "        nicklist: show or hide nicklist bar when layout is automatically applied\n"
                             "default_nicklist: default show or hide nicklist bar if not configured per layout\n"
                             "          remove: remove settings for responsive layout\n"
                             "            list: list current configuration\n"
                             "        terminal: list current terminal width and height\n"
                             "           debug: print script debug output\n\n"
                             "To get current layout and terminal dimensions in your bar, use 'rlayout' bar item.",
                             "size %(layouts_names)"
                             " || nicklist %(layouts_names) %(rlayout_bool_value)"
                             " || default_nicklist %(rlayout_bool_value)"
                             " || remove %(rlayouts_names)"
                             " || list"
                             " || terminal"
                             " || debug %(rlayout_bool_value)",
                             "rlayout_cmd_cb",
                             "")

        # Default settings
        for option, default_value in SETTINGS.items():
            if weechat.config_get_plugin(option) == "":
                weechat.config_set_plugin(option, default_value[0])
            weechat.config_set_desc_plugin(option, '%s (default: %s)' % (default_value[1], default_value[0]))

        weechat.hook_completion("rlayout_bool_value", "list of bool values", "rlayout_completion_bool_cb", "")
        weechat.hook_completion("rlayouts_names", "list of rlayouts", "rlayout_completion_layout_list_cb", "")
        weechat.hook_config("plugins.var.python.responsive_layout.layout.*", "config_cb", "")
        weechat.bar_item_new("rlayout", "rlayout_bar_cb", "")
        update_layout_list()
        hook = weechat.hook_signal("signal_sigwinch", "responsive_cb", "")
