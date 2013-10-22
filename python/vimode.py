# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Germain Z. <germanosz@gmail.com>
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
# Description:
# An attempt to add a vi-like mode to WeeChat, which provides some common vi
# key bindings and commands, as well as normal/insert modes.
#
# Usage:
# To switch to Normal mode, press Ctrl + Space. The Escape key can be used as
# well, though it's still a bit flaky (it's also been reported it's even more
# flaky on older versions, so update your WeeChat to 0.4.2+).
#
# To switch back to Insert mode, you can use i/a/A (or cw/ce/...).
# To execute a command, simply precede it with a ':' while in normal mode,
# for example: ":h" or ":s/foo/bar".
#
# Current key bindings:
# j                  Scroll buffer up * (scrolls a few lines at a time)
# k                  Scroll buffer down * (same as above)
# w                  Forward to the beginning of word
# e                  Forward to the end of word
# b                  Backward to the beginning of word
# gg                 Go to top of buffer * (no counts)
# G                  Go to bottom of buffer
# h                  Move cursor left
# l                  Move cursor right
# 0                  Go to beginning of line
# ^                  Go to beginning of line * (doesn't take whitespace into
#                    consideration, behaves like '0')
# $                  Go to end of line * (same as above)
# x                  Delete character at cursor
# dw                 Delete word
# db                 Delete previous word
# de                 Delete till end of word
# d^                 Delete till beginning of line
# d$                 Delete till end of line
# dd                 Delete line
# ce                 Delete till end of word, switch to insert mode
# cw                 Delete word, switch to insert mode
# cb                 Delete previous word, switch to insert mode
# c^                 Delete till beginning of line, switch to insert mode
# c$                 Delete till end of line, switch to insert mode
# dd                 Delete line, switch to insert mode
# /                  Launch WeeChat search mode
# Counts (e.g. 'd2w', '2G') are supported. However, key bindings marked with a
# '*' won't perform as intended for the time being. Explanation follows in
# parentheses.
# TODO: yy yw ye yb p, make 'e'/'w'/... return start/end positions to avoid
#       redundancy and make them usable by multiple modifiers (e.g. 'de', 'dw')
# TODO (later): u U C-R r R %
#               better search (/), add: n N ?
# TODO (even later): .
#
# Current commands:
# :h                 Help (/help)
# :set               Set WeeChat config option (/set)
# :q                 Closes current buffer (/close)
# :qall              Exits WeeChat (/exit)
# :w                 Saves settings (/save)
# :s/pattern/repl
# :s/pattern/repl/g  Search/Replace, supports regex (check docs for the Python
#                    re module for more information). '&' in the replacement is
#                    also substituted by the pattern. If the 'g' flag isn't
#                    present, only the first match will be substituted.
#                    Escapes are not interpreted for repl (e.g. '\&'), and '/'
#                    isn't expected to be used/escaped anywhere in the command.
#                    TODO: Improve this.
# TODO: :! (probably using shell.py)
#       :w <file> saves buffer's contents to file
#       :r <file> puts file's content in input line/open in buffer?
# TODO: Display matching commands with (basic) help, like Penta/Vimp do.
#
# History:
#     version 0.1: initial release
#     version 0.2: added esc to switch to normal mode, various key bindings and
#                  commands.
#     version 0.2.1: fixes/refactoring
#

import weechat
import re
import time


SCRIPT_NAME = "vimode"
SCRIPT_AUTHOR = "GermainZ <germanosz@gmail.com>"
SCRIPT_VERSION = "0.2.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = ("An attempt to add a vi-like mode to WeeChat, which adds some"
               " common vi key bindings and commands, as well as normal/insert"
               " modes.")

# Initialize variables:
input_line = '' # used to communicate between functions, when only passing a
                # single string is allowed (e.g. for weechat.hook_timer).
cmd_text = '' # holds the text of the command line.
mode = "INSERT" # mode we start in (INSERT or COMMAND), insert by default.
pressed_keys = '' # holds any pressed keys, regardless of their type.
vi_buffer = '' # holds 'printable' pressed keys (e.g. arrow keys aren't added).
last_time = time.time() # used to check if pressed_keys and vi_buffer need to
                        #be reset.
num = r"[0-9]*" # simple regex to detect number of repeats in keystrokes such
                # as "d2w"

# Some common vi commands.
# Others may be present in exec_cmd:
vi_commands = {'h': "/help", 'qall': "/exit", 'q': "/close", 'w': "/save",
               'set': "/set"}

# Common vi key bindings. A dict holds necessary values further down.
def key_G(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the G key."""
    if repeat > 0:
        # This is necessary to prevent weird scroll jumps.
        weechat.command('', "/window scroll_bottom")
        weechat.command('', "/window scroll %s" % repeat)
    else:
        weechat.command('', "/window scroll_bottom")

def get_pos(data, regex, cur):
    matches = [m.start() for m in re.finditer(regex, data[cur:])]
    if len(matches) > 1 and matches[0] == 0:
        pos = matches[1]
    elif len(matches) > 0 and matches[0] != 0:
        pos = matches[0]
    else:
        pos = len(data)
    return pos

# TODO: separate operators from motions
def key_dw(buf, input_line, cur, repeat):
    """Simulate vi's behavior for dw."""
    pos = get_pos(input_line, r"\b\w", cur)
    input_line = list(input_line)
    del input_line[cur:cur+pos]
    input_line = ''.join(input_line)
    weechat.buffer_set(buf, "input", input_line)

def key_de(buf, input_line, cur, repeat):
    """Simulate vi's behavior for de."""
    pos = get_pos(input_line, r"\w\b", cur)
    input_line = list(input_line)
    del input_line[cur:cur+pos+1]
    input_line = ''.join(input_line)
    weechat.buffer_set(buf, "input", input_line)

def key_w(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the w key."""
    for _ in range(max([1, repeat])):
        weechat.command('', ("/input move_next_word\n/input move_next_word\n"
                             "/input move_previous_word"))
        if len(input_line[cur:].split(' ')) == 1:
            weechat.command('', "/input move_end_of_line")

def key_cw(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the cw key."""
    key_dw(repeat)
    set_mode("INSERT")

def key_ce(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the ce key."""
    """Key ce."""
    key_de(repeat)
    set_mode("INSERT")

def key_cb(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the cb key."""
    for _ in range(max[1, repeat]):
        weechat.command('', "/input move_previous_word")
    set_mode("INSERT")

def key_ccarret(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the c^ key."""
    for _ in range(max[1, repeat]):
        weechat.command('', "/input delete_beginning_of_line")
    set_mode("INSERT")

def key_cdollar(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the c$ key."""
    for _ in range(max[1, repeat]):
        weechat.command('', "/input delete_end_of_line")
    set_mode("INSERT")

def key_cd(buf, input_line, cur, repeat):
    """Simulate vi's behavior for the cd key."""
    weechat.command('', "/input delete_line")
    set_mode("INSERT")

# Common vi key bindings. If the value is a string, it's assumed it's a WeeChat
# command, and a function otherwise.
vi_keys = {'j': "/window scroll_down",
           'k': "/window scroll_up",
           'G': key_G,
           'gg': "/window scroll_top",
           'h': "/input move_previous_char",
           'l': "/input move_next_char",
           'w': key_w,
           'e': ("/input move_next_char\n/input move_next_word\n"
                 "/input move_previous_char"),
           'b': "/input move_previous_word",
           '^': "/input move_beginning_of_line",
           '$': "/input move_end_of_line",
           'x': "/input delete_next_char",
           'dd': "/input delete_line",
           'd$': "/input delete_end_of_line",
           'd^': "/input delete_beginning_of_line",
           'dw': key_dw,
           'db': "/input delete_previous_word",
           'de': key_de,
           'cw': key_cw,
           'ce': key_ce,
           'cb': key_cb,
           'c^': key_ccarret,
           'c$': key_cdollar,
           'cd': key_cd,
           '0': "/input move_beginning_of_line",
           '/': "/input search_text"}


def set_mode(arg):
    """Set the current mode and update the bar mode indicator."""
    global mode
    mode = arg
    weechat.bar_item_update("mode_indicator")

def vi_buffer_cb(data, item, window):
    """Return the content of the vi buffer (pressed keys on hold)."""
    return vi_buffer

def cmd_text_cb(data, item, window):
    """Return the text of the command line."""
    return cmd_text

def mode_indicator_cb(data, item, window):
    """Return the current mode (INSERT/COMMAND)."""
    return mode

def exec_cmd(data, remaining_calls):
    """Translate and execute our custom commands to WeeChat command, with
    any passed arguments.

    input_line is set in key_pressed_cb and is used here to restore its value
    if we want, along with any potential replacements that should be made (e.g.
    for s/foo/bar type commands).

    """
    global input_line
    data = list(data)
    del data[0]
    data = ''.join(data)
    data = data.split(' ', 1)
    cmd = data[0]
    if len(data) == 2:
        args = data[1]
    else:
        args = ''
    if cmd in vi_commands:
        weechat.command('', "%s %s" % (vi_commands[cmd], args))
    # s/foo/bar command
    elif cmd.startswith("s/"):
        pattern = cmd.split('/')[1]
        repl = cmd.split('/')[2].replace('&', pattern)
        flag = None
        count = 1
        if len(cmd.split('/')) > 3:
            flag = cmd.split('/')[3]
        if flag == 'g':
            count = 0
        buf = weechat.current_buffer()
        input_line = re.sub(pattern, repl, input_line, count)
        weechat.buffer_set(buf, "input", input_line)
    else:
        weechat.prnt('', "Command '%s' not found." % cmd)
    return weechat.WEECHAT_RC_OK

def input_set(data, remaining_calls):
    """Set the input line's content."""
    buf = weechat.current_buffer()
    weechat.buffer_set(buf, "input", data)
    # move the cursor back to its position prior to setting the content
    weechat.command('', "/input move_next_char")
    return weechat.WEECHAT_RC_OK

def input_rem_char(data, remaining_calls):
    """Remove one character from the input buffer.

    If data is set to 'cursor', the character at the cursor will be removed.
    Otherwise, data must be an integer and the character at that position will
    be removed instead.

    """
    buf = weechat.current_buffer()
    input_line = weechat.buffer_get_string(buf, 'input')
    if data == "cursor":
        data = weechat.buffer_get_integer(buf, "input_pos")
    input_line = list(input_line)
    try:
        del input_line[int(data - 1)]
    # Not sure why nothing is being detected in some cases from the first time
    except IndexError:
        weechat.hook_timer(1, 0, 1, "input_rem_char", "cursor")
        return weechat.WEECHAT_RC_OK
    input_line = ''.join(input_line)
    weechat.buffer_set(buf, "input", input_line)
    # move the cursor back to its position before removing our character
    weechat.command('', "/input move_previous_char")
    return weechat.WEECHAT_RC_OK

def handle_esc(data, remaining_calls):
    """Esc acts as a modifier and usually waits for another keypress.

    To circumvent that, simulate a keypress then remove what was inserted.

    """
    global cmd_text
    weechat.command('', "/input insert %s" % data)
    weechat.hook_signal_send("key_pressed", weechat.WEECHAT_HOOK_SIGNAL_STRING,
                            data)
    if cmd_text == ":[":
        cmd_text = ':'
    return weechat.WEECHAT_RC_OK

esc_pressed = False
def pressed_keys_check(data, remaining_calls):
    """Check the pressed keys and changes modes or detects bound keys
    accordingly.

    """
    global pressed_keys, mode, vi_buffer, esc_pressed
    # If the last pressed key was Escape, this one will be detected as an arg
    # as Escape acts like a modifier (pressing Esc, then pressing i is detected
    # as pressing meta-i). We'll emulate it being pressed again, so that the
    # user's input is actually processed normally.
    if esc_pressed is True:
        esc_pressed = False
        weechat.hook_timer(50, 0, 1, "handle_esc", pressed_keys[-1])
    if mode == "INSERT":
        # Ctrl + Space, or Escape
        if pressed_keys == "@" or pressed_keys == "[":
            set_mode("NORMAL")
            if pressed_keys == "[":
                esc_pressed = True
    elif mode == "NORMAL":
        # We strip all numbers and check if the the combo is recognized below,
        # then extract the numbers, if any, and pass them as the repeat factor.
        buffer_stripped = re.sub(num, '', vi_buffer)
        if vi_buffer in ['i', 'a', 'A']:
            set_mode("INSERT")
            if vi_buffer == 'a':
                weechat.command('', "/input move_next_char")
            elif vi_buffer == 'A':
                weechat.command('', "/input move_end_of_line")
        # Pressing '0' should not be detected as a repeat count.
        elif vi_buffer == '0':
            weechat.command('', vi_keys['0'])
        # Quick way to detect repeats (e.g. d5w). This isn't perfect, as things
        # like "5d2w1" are detected as "dw" repeated 521 times, but it should
        # be alright as long as the user doesn't try to break it on purpose.
        # Maximum number of repeats performed is 10000.
        elif buffer_stripped in vi_keys:
            repeat = ''.join(re.findall(num, vi_buffer))
            if len(repeat) > 0:
                repeat = min([int(repeat), 10000])
            else:
                repeat = 0
            if isinstance(vi_keys[buffer_stripped], str):
                for _ in range(1 if repeat == 0 else repeat):
                    weechat.command('', vi_keys[re.sub(num, '', vi_buffer)])
            else:
                buf = weechat.current_buffer()
                input_line = weechat.buffer_get_string(buf, 'input')
                cur = weechat.buffer_get_integer(buf, "input_pos")
                vi_keys[buffer_stripped](buf, input_line, cur, repeat)
        else:
            return weechat.WEECHAT_RC_OK
    clear_vi_buffers()
    return weechat.WEECHAT_RC_OK

def clear_vi_buffers(data=None, remaining_calls=None):
    """Clear both pressed_keys and vi_buffer.

    If data is set to 'check_time', they'll only be cleared if enough time has
    gone by since they've been last set.
    This is useful as this function is called using a timer, so other keys
    might've been pressed before the timer is activated.

    """
    global pressed_keys, vi_buffer
    if data == "check_time" and time.time() < last_time + 1.0:
        return weechat.WEECHAT_RC_OK
    pressed_keys = ''
    vi_buffer = ''
    weechat.bar_item_update("vi_buffer")
    return weechat.WEECHAT_RC_OK

def is_printing(current, saved):
    """Is the character a visible, printing character that would normally
    show in the input box?

    Previously saved characters are taken into consideration as well for some
    key combinations, such as the arrows, which are detected as three separate
    events (^A[, [ and A/B/C/D).
    The keys buffers will be cleared if the character isn't visible.

    """
    if current.startswith("") or saved.startswith(""):
        weechat.hook_timer(50, 0, 1, "clear_vi_buffers", '')
        return False
    return True

def key_pressed_cb(data, signal, signal_data):
    """Handle key presses.

    Make sure inputted keys are removed from the input bar and added to the
    appropriate keys buffers or to the command line if it's active, activate it
    when needed, etc.

    """
    global pressed_keys, last_time, cmd_text, input_line, vi_buffer
    if mode == "NORMAL":
        # The character is a printing character, so we'll want to remove it
        # so it doesn't add up to the normal input box.
        if is_printing(signal_data, pressed_keys):
            weechat.hook_timer(1, 0, 1, "input_rem_char", "cursor")
        # It's a command!
        if signal_data == ':':
            cmd_text += ':'
        # Command line is active, so we want to check for some special keys
        # to modify (backspace/normal keys) or submit (Return key) our command.
        elif cmd_text != '':
            # Backspace key
            if signal_data == "?":
                buf = weechat.current_buffer()
                input_line = weechat.buffer_get_string(buf, 'input')
                # Remove the last character from our command line
                cmd_text = list(cmd_text)
                del cmd_text[-1]
                cmd_text = ''.join(cmd_text)
                # We can't actually eat these keystrokes, so simply removing
                # the last character would result in the last two characters
                # being removed (once by the backspace key, once by our script)
                # Instead, we'll just set the input line in a millisecond to
                # its original value, leaving it untouched.
                weechat.hook_timer(1, 0, 1, "input_set", input_line)
            # Return key
            elif signal_data == "M":
                buf = weechat.current_buffer()
                # Clear the input line, therefore nullifying the effect of the
                # Return key, then set it back a millisecond later.
                # This leaves the input box untouched and allows us to execute
                # the command filled in in our command line.
                # We can only pass strings as data using hook_timer, so we'll
                # use the global variable input_line in our exec_cmd function
                # instead to reset the input box's value.
                input_line = weechat.buffer_get_string(buf, 'input')
                weechat.buffer_set(buf, "input", '')
                weechat.hook_timer(1, 0, 1, "exec_cmd", cmd_text)
                cmd_text = ''
            # The key is a normal key, so just append it to our command line.
            elif is_printing(signal_data, pressed_keys):
                cmd_text += signal_data
    # Show the command line when needed, hide it (and update vi_buffer since
    # we'd be looking for keystrokes instead) otherwise.
    if cmd_text != '':
        weechat.command('', "/bar show vi_cmd")
        weechat.bar_item_update("cmd_text")
    else:
        weechat.command('', "/bar hide vi_cmd")
        if is_printing(signal_data, pressed_keys):
            vi_buffer += signal_data
        pressed_keys += signal_data
        # Check for any matching bound keys.
        weechat.hook_timer(1, 0, 1, "pressed_keys_check", '')
        last_time = time.time()
        # Clear the buffers after some time.
        weechat.hook_timer(1000, 0, 1, "clear_vi_buffers", "check_time")
    weechat.bar_item_update("vi_buffer")
    return weechat.WEECHAT_RC_OK


weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                 SCRIPT_DESC, '', '')

weechat.bar_item_new("mode_indicator", "mode_indicator_cb", '')
weechat.bar_item_new("cmd_text", "cmd_text_cb", '')
weechat.bar_item_new("vi_buffer", "vi_buffer_cb", '')
vi_cmd = weechat.bar_new("vi_cmd", "off", "0", "root", '', "bottom",
                         "vertical", "vertical", "0", "0", "default",
                         "default", "default", "0", "cmd_text")
weechat.hook_signal("key_pressed", "key_pressed_cb", '')

