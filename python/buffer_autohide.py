# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2017-2018 Matthias Adamczyk
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
"""
Automatically hide read IRC buffers and unhide them on new activity.

Requires WeeChat version 1.0 or higher.

Configuration:
    plugins.var.python.buffer_autohide.hide_inactive: Hide inactive buffers (default: "off")
    plugins.var.python.buffer_autohide.hide_private: Hide private buffers (default: "off")
    plugins.var.python.buffer_autohide.unhide_low: Unhide a buffer when a low priority message (like JOIN,
        PART, etc.) has been received (default: "off"),
    plugins.var.python.buffer_autohide.excemptions: An enumeration of buffers that should not become hidden (default: "")

History:
2017-03-19: Matthias Adamczyk <mail@notmatti.me>
    version 0.1: Initial release
2018-06-28: yeled <yeled@github.com>
    version 0.2: Only skip irc.servers
2018-12-07: Matthias Adamczyk <mail@notmatti.me>
    version 0.3: Add a functionality to define excemptions for certain buffers

https://github.com/notmatti/buffer_autohide
"""
import_ok = True
try:
    import weechat
    from weechat import WEECHAT_RC_OK
except ImportError:
    print("Script must be run under weechat. https://weechat.org")
    import_ok = False


SCRIPT_NAME = "buffer_autohide"
SCRIPT_AUTHOR = "Matthias Adamczyk <mail@notmatti.me>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Automatically hide read IRC buffers and unhide them on new activity"
SCRIPT_COMMAND = SCRIPT_NAME

DELIMITER = "|@|"
CURRENT_BUFFER = "0x0" # pointer string representation


def config_init():
    """Add configuration options to weechat."""
    config = {
        "hide_inactive": ("off", "Hide inactive buffers"),
        "hide_private": ("off", "Hide private buffers"),
        "unhide_low": ("off",
            "Unhide a buffer when a low priority message (like JOIN, PART, etc.) has been received"),
        "excemptions": ("", "An enumeration of buffers that should not get hidden"),
    }
    for option, default_value in config.items():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value[0])
        weechat.config_set_desc_plugin(
            option, '{} (default: "{}")'.format(default_value[1], default_value[0]))


def hotlist_dict():
    """Return the contents of the hotlist as a dictionary.

    The returned dictionary has the following structure:
    >>> hotlist = {
    ...     "0x0": {                    # string representation of the buffer pointer
    ...         "count_low": 0,
    ...         "count_message": 0,
    ...         "count_private": 0,
    ...         "count_highlight": 0,
    ...     }
    ... }
    """
    hotlist = {}
    infolist = weechat.infolist_get("hotlist", "", "")
    while weechat.infolist_next(infolist):
        buffer_pointer = weechat.infolist_pointer(infolist, "buffer_pointer")
        hotlist[buffer_pointer] = {}
        hotlist[buffer_pointer]["count_low"] = weechat.infolist_integer(
            infolist, "count_00")
        hotlist[buffer_pointer]["count_message"] = weechat.infolist_integer(
            infolist, "count_01")
        hotlist[buffer_pointer]["count_private"] = weechat.infolist_integer(
            infolist, "count_02")
        hotlist[buffer_pointer]["count_highlight"] = weechat.infolist_integer(
            infolist, "count_03")
    weechat.infolist_free(infolist)
    return hotlist


def hide_buffer_cb(data, signal, signal_data):
    """Hide the previous IRC buffer when switching buffers.

    If configuration option ``hide_private`` is enabled,
    private buffers will become hidden as well.

    If the previous buffer name matches any of the excemptions defined in ``excemptions``,
    it will not become hidden.

    :param data: Pointer
    :param signal: Signal sent by Weechat
    :param signal_data: Data sent with signal
    :returns: callback return value expected by Weechat.
    """
    global CURRENT_BUFFER

    previous_buffer = CURRENT_BUFFER
    CURRENT_BUFFER = weechat.current_buffer()

    plugin = weechat.buffer_get_string(previous_buffer, "plugin")
    full_name = weechat.buffer_get_string(previous_buffer, "full_name")
    server = weechat.buffer_get_string(previous_buffer, "localvar_server")
    channel = weechat.buffer_get_string(previous_buffer, "localvar_channel")

    if full_name.startswith("irc.server"):
        return WEECHAT_RC_OK

    buffer_type = weechat.buffer_get_string(
        weechat.info_get("irc_buffer", "{},{}".format(server, channel)),
        "localvar_type")

    if (buffer_type == "private"
            and weechat.config_get_plugin("hide_private") == "off"):
        return WEECHAT_RC_OK

    if weechat.config_get_plugin("hide_inactive") == "off":
        nicks_count = 0
        infolist = weechat.infolist_get(
            "irc_channel", "", "{},{}".format(server, channel))
        if infolist:
            weechat.infolist_next(infolist)
            nicks_count = weechat.infolist_integer(infolist, "nicks_count")
        weechat.infolist_free(infolist)
        if nicks_count == 0:
            return WEECHAT_RC_OK

    for entry in list_excemptions():
        if entry in full_name:
            return WEECHAT_RC_OK

    weechat.buffer_set(previous_buffer, "hidden", "1")
    return WEECHAT_RC_OK


def unhide_buffer_cb(data, signal, signal_data):
    """Unhide a buffer on new activity.

    This callback unhides a buffer in which a new message has been received.
    If configuration option ``unhide_low`` is enabled,
    buffers with only low priority messages (like JOIN, PART, etc.) will be unhidden as well.

    :param data: Pointer
    :param signal: Signal sent by Weechat
    :param signal_data: Data sent with signal
    :returns: Callback return value expected by Weechat.
    """
    server = signal.split(",")[0]
    message = weechat.info_get_hashtable(
        "irc_message_parse",
        {"message": signal_data})
    channel = message["channel"]
    hotlist = hotlist_dict()
    buffer = weechat.info_get("irc_buffer", "{},{}".format(server, channel))

    if not buffer in hotlist.keys():
        # just some background noise
        return WEECHAT_RC_OK

    if (weechat.config_get_plugin("unhide_low") == "on"
            and hotlist[buffer]["count_low"] > 0
            or hotlist[buffer]["count_message"] > 0
            or hotlist[buffer]["count_private"] > 0
            or hotlist[buffer]["count_highlight"] > 0):
        weechat.buffer_set(buffer, "hidden", "0")

    return WEECHAT_RC_OK


def list_excemptions():
    """Return a list of excemption defined in ``excemptions``.

    :returns: A list of defined excemptions.
    """
    return [x for x in weechat.config_get_plugin("excemptions").split(DELIMITER) if x != ""]


def add_to_excemptions(entry):
    """Add an entry to the list of excemptions.

    An entry can be either a #channel or server_name.#channel

    :param entry: The entry to add.
    :returns: the new list of entries. The return value is only used for unit testing.
    """
    entries = list_excemptions()
    entries.append(entry)
    weechat.config_set_plugin("excemptions", DELIMITER.join(entries))
    weechat.prnt("", "[{}] add: {} added to excemptions.".format(SCRIPT_COMMAND, entry))
    return entries


def del_from_excemptions(entry):
    """Remove an entry from the list of defined excemtions.

    :param entry: The entry to delete, which can be specified by the position in the list or by the name itself.
    :returns: the new list of entries. The return value is only used for unit testing.
    """
    entries = list_excemptions()
    try:
        # by index
        try:
            index = int(entry) - 1
            if index < 0:
                raise IndexError
            entry = entries.pop(index)
        except IndexError:
            weechat.prnt("", "[{}] del: Index out of range".format(SCRIPT_COMMAND))
            return entries
    except ValueError:
        try:
            # by name
            entries.remove(entry)
            weechat.config_set_plugin("excemptions", DELIMITER.join(entries))
        except ValueError:
            weechat.prnt("", "[{}] del: Could not find {}".format(SCRIPT_COMMAND, entry))
            return entries

    weechat.config_set_plugin("excemptions", DELIMITER.join(entries))
    weechat.prnt("", "[{}] del: Removed {} from excemptions.".format(SCRIPT_COMMAND, entry))
    return entries


def print_excemptions():
    """Print all excemptions defined in ``excemptions``"""
    entries = list_excemptions()
    if entries:
        count = 1
        for entry in entries:
            weechat.prnt("", "[{}] {}: {}".format(SCRIPT_COMMAND, count, entry))
            count += 1
    else:
        weechat.prnt("", "[{}] list: No excemptions defined so far.".format(SCRIPT_COMMAND))


def command_cb(data, buffer, args):
    """Weechat callback for parsing and executing the given command.

    :returns: Callback return value expected by Weechat.
    """
    list_args = args.split(" ")

    if list_args[0] not in ["add", "del", "list"]:
        weechat.prnt("", "[{0}] bad option while using /{0} command, try '/help {0}' for more info".format(
            SCRIPT_COMMAND))

    elif list_args[0] == "add":
        if len(list_args) == 2:
            add_to_excemptions(list_args[1])

    elif list_args[0] == "del":
        if len(list_args) == 2:
            del_from_excemptions(list_args[1])

    elif list_args[0] == "list":
        print_excemptions()
    else:
        weechat.command("", "/help " + SCRIPT_COMMAND)

    return WEECHAT_RC_OK


if (__name__ == '__main__' and import_ok and weechat.register(
            SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')):
    weechat_version = weechat.info_get("version_number", "") or 0
    if int(weechat_version) >= 0x01000000:
        config_init()
        CURRENT_BUFFER = weechat.current_buffer()
        weechat.hook_signal("buffer_switch", "hide_buffer_cb", "")
        weechat.hook_signal("*,irc_in2_*", "unhide_buffer_cb", "")
        weechat.hook_command(
            SCRIPT_NAME,
            SCRIPT_DESC,
            "add $buffer_name | del { $buffer_name | $list_position } | list",
            "  add    : Add $buffer_name to the list of excemptions\n"
            "           $buffer_name can be either #channel or server_name.#channel"
            "  del    : Delete $buffer_name from the list of excemptions\n"
            "  list   : Return a list of all buffers that should not become hidden.",
            "add|del|list",
            "command_cb",
            ""
        )
    else:
        weechat.prnt("", "{}{} requires WeeChat version 1.0 or higher".format(
            weechat.prefix('error'), SCRIPT_NAME))
