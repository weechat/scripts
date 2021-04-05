# -*- coding: utf-8 -*-
#
# Copyright (C) 2019  Cole Helbling <cole.e.helbling@outlook.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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

# Changelog:
# 2019-12-14, Cole Helbling <cole.e.helbling@outlook.com>
#   version 1.0: initial release

SCRIPT_NAME = "styurl"
SCRIPT_AUTHOR = "Cole Helbling <cole.e.helbling@outlook.com>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Style URLs with a Python regex"

import_ok = True
try:
    import weechat as w
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org")
    import_ok = False

try:
    import re
except ImportError as message:
    print("Missing package for %s: %s" % (SCRIPT_NAME, message))
    import_ok = False

# https://mathiasbynens.be/demo/url-regex
# If you don't want to create your own regex, see the above link for options or
# ideas on creating your own

styurl_settings = {
    "buffer_type": (
        "formatted",
        "the type of buffers to run on (options are \"formatted\", \"free\", "
        "or \"*\" for both)"
    ),
    "format": (
        "${color:*_32}",
        "the style that should be applied to the URL"
        "(evaluated, see /help eval)"
    ),
    "ignored_buffers": (
        "core.weechat,python.grep",
        "comma-separated list of buffers to ignore URLs in "
        "(full name like \"irc.freenode.#alacritty\")"
    ),
    "ignored_tags": (
        "irc_quit,irc_join",
        "comma-separated list of tags to ignore URLs from"
    ),
    "regex": (
        r"((?:https?|ftp)://[^\s/$.?#].\S*)",
        "the URL-parsing regex using Python syntax "
        "(make sure capturing group 1 is the full URL)"
    ),
}

line_hook = None


def styurl_line_cb(data, line):
    """
    Callback called when a line is displayed.
    This parses the message for any URLs and styles them according to
    styurl_settings["format"].
    """
    global styurl_settings

    # Don't style the line if it's not going to be displayed... duh
    if line["displayed"] != "1":
        return line

    tags = line["tags"].split(',')
    ignored_tags = styurl_settings["ignored_tags"]

    # Ignore specified message tags
    if ignored_tags:
        if any(tag in tags for tag in ignored_tags.split(',')):
            return line

    bufname = line["buffer_name"]
    ignored_buffers = styurl_settings["ignored_buffers"]

    # Ignore specified buffers
    if ignored_buffers and bufname in ignored_buffers.split(','):
        return line

    message = line["message"]

    # TODO: enforce presence of a properly-formatted color object at
    # styurl_settings["format"] (eval object would also be valid, if it eval'd
    # to a color)

    regex = re.compile(styurl_settings["regex"])
    url_style = w.string_eval_expression(styurl_settings["format"], {}, {}, {})
    reset = w.color("reset")

    # Search for URLs and surround them with the defined URL styling
    formatted = regex.sub(r"%s\1%s" % (url_style, reset), message)
    line["message"] = line["message"].replace(message, formatted)

    return line


def styurl_config_cb(data, option, value):
    """Callback called when a script option is changed."""
    global styurl_settings, line_hook

    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in styurl_settings:
            # Changing the buffer target requires us to re-hook to prevent
            # obsolete buffer types from getting styled
            if name == "buffer_type":
                if value in ("free", "formatted", "*"):
                    w.unhook(line_hook)
                    line_hook = w.hook_line(value, "", "", "styurl_line_cb",
                                            "")
                else:
                    # Don't change buffer type if it is invalid
                    w.prnt("", SCRIPT_NAME + ": Invalid buffer type: '%s', "
                           "not changing." % value)
                    w.config_set_plugin(name, styurl_settings[name])
                    return w.WEECHAT_RC_ERROR

            styurl_settings[name] = value

    return w.WEECHAT_RC_OK


def styurl_unload_cb():
    """Callback called when the script is unloaded."""
    global line_hook

    w.unhook(line_hook)
    del line_hook
    return w.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                  SCRIPT_DESC, "styurl_unload_cb", ""):

        version = w.info_get("version_number", "") or 0

        for option, value in styurl_settings.items():
            if w.config_is_set_plugin(option):
                styurl_settings[option] = w.config_get_plugin(option)
            else:
                w.config_set_plugin(option, value[0])
                styurl_settings[option] = value[0]
            if int(version) >= 0x00030500:
                w.config_set_desc_plugin(option, "%s (default: \"%s\")"
                                         % (value[1], value[0]))

        w.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
                      "styurl_config_cb", "")

        # Style URLs
        line_hook = w.hook_line(styurl_settings["buffer_type"], "", "",
                                "styurl_line_cb", "")
