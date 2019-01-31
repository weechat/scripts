# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2017-2019 Matthias Adamczyk
# Copyright (c) 2019 Marco Trevisan
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
Automatically hide read buffers and unhide them on new activity.

Requires WeeChat version 1.0 or higher.

Configuration:
    plugins.var.python.buffer_autohide.hide_inactive: Hide inactive buffers (default: "off")
    plugins.var.python.buffer_autohide.hide_private: Hide private buffers (default: "off")
    plugins.var.python.buffer_autohide.unhide_low: Unhide a buffer when a low priority message (like JOIN,
        PART, etc.) has been received (default: "off"),
    plugins.var.python.buffer_autohide.exemptions: An enumeration of buffers that should not become hidden (default: "")
    plugins.var.python.buffer_autohide.keep_open: Keep a buffer open for a short amount of time (default: "off")
    plugins.var.python.buffer_autohide.keep_open_timeout: Timeout in milliseconds for how long a selected buffer should be kept around (default: "60 * 1000")

History:
2017-03-19: Matthias Adamczyk <mail@notmatti.me>
    version 0.1: Initial release
2018-06-28: yeled <yeled@github.com>
    version 0.2: Only skip irc.servers
2018-12-07: Matthias Adamczyk <mail@notmatti.me>
    version 0.3: Add a functionality to define exemptions for certain buffers
2018-12-07: Marco Trevisan <mail@3v1n0.net>
    version 0.4: Keep buffers active for a given time before hide them again if they should
2019-01-31: Trygve Aaberge <trygveaa@gmail.com>
    version 0.5: Support buffers from plugins other than IRC as well

https://github.com/notmatti/buffer_autohide
"""
from __future__ import print_function
import ast
import operator as op
import_ok = True
try:
    import weechat
    from weechat import WEECHAT_RC_OK
except ImportError:
    print("Script must be run under weechat. https://weechat.org")
    import_ok = False


SCRIPT_NAME = "buffer_autohide"
SCRIPT_AUTHOR = "Matthias Adamczyk <mail@notmatti.me>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Automatically hide read buffers and unhide them on new activity"
SCRIPT_COMMAND = SCRIPT_NAME

DELIMITER = "|@|"
MINIMUM_BUFFER_LIFE = 500 # How many ms are enough to consider a buffer valid
KEEP_ALIVE_TIMEOUT = 60 * 1000 # How long a selected buffer should be kept around

CURRENT_BUFFER = "0x0" # pointer string representation
CURRENT_BUFFER_TIMER_HOOK = None # Timeout hook reference
KEEP_ALIVE_BUFFERS = {} # {pointer_string_rep: timeout_hook}


def config_init():
    """Add configuration options to weechat."""
    global KEEP_ALIVE_TIMEOUT

    config = {
        "hide_inactive": ("off", "Hide inactive buffers"),
        "hide_private": ("off", "Hide private buffers"),
        "unhide_low": ("off",
            "Unhide a buffer when a low priority message (like JOIN, PART, etc.) has been received"),
        "exemptions": ("", "An enumeration of buffers that should not get hidden"),
        "keep_open": ("off", "Keep a buffer open for a short amount of time"),
        "keep_open_timeout": ("60 * 1000", "Timeout in milliseconds for how long a selected buffer should be kept around"),
    }
    for option, default_value in config.items():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value[0])
        weechat.config_set_desc_plugin(
            option, '{} (default: "{}")'.format(default_value[1], default_value[0]))

    weechat.hook_config("plugins.var.python.buffer_autohide.keep_open_timeout", "timeout_config_changed_cb", "")
    if weechat.config_is_set_plugin("keep_open_timeout"):
        KEEP_ALIVE_TIMEOUT = eval_expr(weechat.config_get_plugin("keep_open_timeout"))


def eval_expr(expr):
    """Evaluate a mathematical expression.

    >>> eval_expr('2 * 6')
    12
    """
    def evaluate(node):
        # supported operators
        operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                     ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                     ast.USub: op.neg}
        if isinstance(node, ast.Num): # <number>
            return node.n
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return operators[type(node.op)](evaluate(node.left), evaluate(node.right))
        elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
            return operators[type(node.op)](evaluate(node.operand))
        else:
            raise TypeError(node)

    return evaluate(ast.parse(expr, mode='eval').body)


def timeout_config_changed_cb(data, option, value):
    """Set the new keep_alive timeout upon change of the corresponding value in plugins.conf."""
    global KEEP_ALIVE_TIMEOUT
    KEEP_ALIVE_TIMEOUT = eval_expr(value)
    return WEECHAT_RC_OK


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


def on_temporary_active_buffer_timeout(buffer, remaining_calls):
    remove_keep_alive(buffer)
    maybe_hide_buffer(buffer)

    return weechat.WEECHAT_RC_OK


def keep_alive_buffer(buffer):
    remove_keep_alive(buffer)

    if buffer_is_hidable(buffer):
        KEEP_ALIVE_BUFFERS[buffer] = weechat.hook_timer(KEEP_ALIVE_TIMEOUT, 0, 1,
            "on_temporary_active_buffer_timeout", buffer)


def remove_keep_alive(buffer):
    global KEEP_ALIVE_BUFFERS

    if buffer in KEEP_ALIVE_BUFFERS.keys():
        weechat.unhook(KEEP_ALIVE_BUFFERS.pop(buffer))


def switch_current_buffer():
    """Save current buffer and ensure that it's visible, then if the
    buffer is elegible to be hidden, we add it to the list of the buffers
    to be hidden after a delay
    """
    global CURRENT_BUFFER
    global CURRENT_BUFFER_TIMER_HOOK

    previous_buffer = CURRENT_BUFFER
    CURRENT_BUFFER = weechat.current_buffer()

    if previous_buffer == CURRENT_BUFFER:
        return

    if weechat.buffer_get_integer(CURRENT_BUFFER, "hidden") == 1:
        weechat.buffer_set(CURRENT_BUFFER, "hidden", "0")

    if weechat.config_get_plugin("keep_open") != "off":
        if CURRENT_BUFFER_TIMER_HOOK is not None:
            weechat.unhook(CURRENT_BUFFER_TIMER_HOOK)
            CURRENT_BUFFER_TIMER_HOOK = None
            maybe_hide_buffer(previous_buffer)
        else:
            keep_alive_buffer(previous_buffer)

        CURRENT_BUFFER_TIMER_HOOK = weechat.hook_timer(MINIMUM_BUFFER_LIFE, 0, 1,
            "on_current_buffer_is_still_active_timeout", "")
    else:
        maybe_hide_buffer(previous_buffer)


def on_current_buffer_is_still_active_timeout(pointer, remaining_calls):
    global CURRENT_BUFFER_TIMER_HOOK
    global KEEP_ALIVE_BUFFERS

    CURRENT_BUFFER_TIMER_HOOK = None
    remove_keep_alive(CURRENT_BUFFER)

    return weechat.WEECHAT_RC_OK


def switch_buffer_cb(data, signal, signal_data):
    """
    :param data: Pointer
    :param signal: Signal sent by Weechat
    :param signal_data: Data sent with signal
    :returns: callback return value expected by Weechat.
    """
    switch_current_buffer()
    return WEECHAT_RC_OK


def buffer_is_hidable(buffer):
    """Check if passed buffer can be hidden.

    If configuration option ``hide_private`` is enabled,
    private buffers will become hidden as well.

    If the previous buffer name matches any of the exemptions defined in ``exemptions``,
    it will not become hidden.

    :param buffer: Buffer string representation
    """
    if buffer == weechat.current_buffer():
        return False

    if buffer in KEEP_ALIVE_BUFFERS.keys():
        return False

    full_name = weechat.buffer_get_string(buffer, "full_name")

    if full_name.startswith("irc.server"):
        return False

    buffer_type = weechat.buffer_get_string(buffer, 'localvar_type')

    if (buffer_type == "private"
            and weechat.config_get_plugin("hide_private") == "off"):
        return False

    if weechat.config_get_plugin("hide_inactive") == "off":
        nicks_count = weechat.buffer_get_integer(buffer, 'nicklist_nicks_count')
        if nicks_count == 0:
            return False

    for entry in list_exemptions():
        if entry in full_name:
            return False

    return True


def maybe_hide_buffer(buffer):
    """Hide a buffer if all the conditions are met"""
    if buffer_is_hidable(buffer):
        weechat.buffer_set(buffer, "hidden", "1")


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
    hotlist = hotlist_dict()
    line_data = weechat.hdata_pointer(weechat.hdata_get('line'), signal_data, 'data')
    buffer = weechat.hdata_pointer(weechat.hdata_get('line_data'), line_data, 'buffer')

    if not buffer in hotlist.keys():
        # just some background noise
        return WEECHAT_RC_OK

    if (weechat.config_get_plugin("unhide_low") == "on"
            and hotlist[buffer]["count_low"] > 0
            or hotlist[buffer]["count_message"] > 0
            or hotlist[buffer]["count_private"] > 0
            or hotlist[buffer]["count_highlight"] > 0):
        remove_keep_alive(buffer)
        weechat.buffer_set(buffer, "hidden", "0")

    return WEECHAT_RC_OK


def list_exemptions():
    """Return a list of exemption defined in ``exemptions``.

    :returns: A list of defined exemptions.
    """
    return [x for x in weechat.config_get_plugin("exemptions").split(DELIMITER) if x != ""]


def add_to_exemptions(entry):
    """Add an entry to the list of exemptions.

    An entry can be either a #channel or server_name.#channel

    :param entry: The entry to add.
    :returns: the new list of entries. The return value is only used for unit testing.
    """
    entries = list_exemptions()
    entries.append(entry)
    weechat.config_set_plugin("exemptions", DELIMITER.join(entries))
    weechat.prnt("", "[{}] add: {} added to exemptions.".format(SCRIPT_COMMAND, entry))
    return entries


def del_from_exemptions(entry):
    """Remove an entry from the list of defined exemptions.

    :param entry: The entry to delete, which can be specified by the position in the list or by the name itself.
    :returns: the new list of entries. The return value is only used for unit testing.
    """
    entries = list_exemptions()
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
            weechat.config_set_plugin("exemptions", DELIMITER.join(entries))
        except ValueError:
            weechat.prnt("", "[{}] del: Could not find {}".format(SCRIPT_COMMAND, entry))
            return entries

    weechat.config_set_plugin("exemptions", DELIMITER.join(entries))
    weechat.prnt("", "[{}] del: Removed {} from exemptions.".format(SCRIPT_COMMAND, entry))
    return entries


def print_exemptions():
    """Print all exemptions defined in ``exemptions``"""
    entries = list_exemptions()
    if entries:
        count = 1
        for entry in entries:
            weechat.prnt("", "[{}] {}: {}".format(SCRIPT_COMMAND, count, entry))
            count += 1
    else:
        weechat.prnt("", "[{}] list: No exemptions defined so far.".format(SCRIPT_COMMAND))


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
            add_to_exemptions(list_args[1])

    elif list_args[0] == "del":
        if len(list_args) == 2:
            del_from_exemptions(list_args[1])

    elif list_args[0] == "list":
        print_exemptions()
    else:
        weechat.command("", "/help " + SCRIPT_COMMAND)

    return WEECHAT_RC_OK


if (__name__ == '__main__' and import_ok and weechat.register(
            SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')):
    weechat_version = weechat.info_get("version_number", "") or 0
    if int(weechat_version) >= 0x01000000:
        config_init()
        CURRENT_BUFFER = weechat.current_buffer()
        weechat.hook_signal("buffer_switch", "switch_buffer_cb", "")
        weechat.hook_signal("buffer_line_added", "unhide_buffer_cb", "")
        weechat.hook_command(
            SCRIPT_NAME,
            SCRIPT_DESC,
            "add $buffer_name | del { $buffer_name | $list_position } | list",
            "  add    : Add $buffer_name to the list of exemptions\n"
            "           $buffer_name can be either #channel or server_name.#channel\n"
            "  del    : Delete $buffer_name from the list of exemptions\n"
            "  list   : Return a list of all buffers that should not become hidden.",
            "add|del|list",
            "command_cb",
            ""
        )
    else:
        weechat.prnt("", "{}{} requires WeeChat version 1.0 or higher".format(
            weechat.prefix('error'), SCRIPT_NAME))
