''' History searcher '''
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
#
#   Based on go.py by FlashCode
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
# Set screen title
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2010-01-19, xt <xt@bash.no>
#     version 0.2: return max 9 commands
# 2009-06-10, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w
import re
weechat = w

SCRIPT_NAME    = "histsearch"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Quick search in command history (think ctrl-r in bash)"
SCRIPT_COMMAND = 'histsearch'

# script options
settings = {
    "color_number"                 : "yellow,magenta",
    "color_number_selected"        : "yellow,red",
    "color_name"                   : "black,cyan",
    "color_name_selected"          : "black,brown",
    "color_name_highlight"         : "red,cyan",
    "color_name_highlight_selected": "red,brown",
    "message"                      : "Command: ",
}


# hooks management
hook_command_run = {
    "input" : ("/input *",  "command_run_input"),
    "buffer": ("/buffer *", "command_run_buffer"),
    "window": ("/window *", "command_run_window"),
}
hooks = {}

# input before command (we'll restore it later)
saved_input = ""

# last user input (if changed, we'll update list of matching commands)
old_input = None

# matching buffers
commands = []
command_pos = 0

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command(SCRIPT_COMMAND, "Quick search in command history", "",
                         "You can bind command to a key, for example:\n  /key bind meta-e /histsearch\n\n" +
                         "You can use completion key (commonly Tab and shift-Tab) to select " +
                         "next/previous command in list.",
                         "", "histsearch_cmd", "")
    for option, default_value in settings.iteritems():
        if w.config_get_plugin(option) == "":
            w.config_set_plugin(option, default_value)


def unhook_one(hook):
    """ Unhook something hooked by this script """
    global hooks
    if hook in hooks:
        w.unhook(hooks[hook])
        del hooks[hook]

def unhook_all():
    """ Unhook all """
    global hook_command_run
    unhook_one("modifier")
    map(unhook_one, hook_command_run.keys())
    return w.WEECHAT_RC_OK

def hook_all():
    """ Hook command_run and modifier """
    global hook_command_run, hooks
    for hook, value in hook_command_run.iteritems():
        if hook not in hooks:
            hooks[hook] = w.hook_command_run(value[0], value[1], "")
    if "modifier" not in hooks:
        hooks["modifier"] = w.hook_modifier(
            "input_text_display_with_cursor", "input_modifier", "")

def histsearch_start(buffer):
    """ Start histsearch on buffer """
    global saved_input, old_input, commands_pos
    hook_all()
    saved_input = w.buffer_get_string(buffer, "input")
    w.buffer_set(buffer, "input", "")
    old_input = None
    commands_pos = 0

def histsearch_end(buffer):
    """ End histsearch on buffer """
    global saved_input, old_input
    unhook_all()
    w.buffer_set(buffer, "input", saved_input)
    old_input = None

def get_matching_commands(input):
    """ Return list with commands matching user input """
    global commands_pos
    clist = []
    if len(input) == 0:
        commands_pos = 0
        return []
    input = input.lower()
    infolist = w.infolist_get("history", "", "")
    while w.infolist_next(infolist):
        text = w.infolist_string(infolist, "text")
        matching = input in text
        #if not matching and input.isdigit():
        #    matching = str(number).startswith(input)
        if len(clist) > 9:
           # Return max 10 commands
            break
        if len(input) == 0 or matching:
            if not text in clist:
                clist.append(text)
    w.infolist_free(infolist)
    return clist

def get_command_string(commands, pos, input):
    ''' Build the string that is displayed on input bar '''

    global settings

    colors = {}
    returnstr = ''

    for option in settings:
        colors[option] = weechat.config_get_plugin(option)

    for i, command in enumerate(commands):
        selected = ''
        if i == pos:
            selected = "_selected"
        index = command.find(input)
        index2 = index + len(input)
        returnstr += ' ' + \
                weechat.color(colors["color_number" + selected]) + str(i) + \
                weechat.color(colors["color_name" + selected]) + command[:index] + \
                weechat.color(colors["color_name_highlight" + selected]) + command[index:index2] + \
                weechat.color(colors["color_name" + selected]) + command[index2:] + \
                weechat.color("reset")

        if i > 10:
            # Display max 10 commands
            break

    return returnstr

def input_modifier(data, modifier, modifier_data, string):
    """ This modifier is called when input text item is built by WeeChat
    (commonly after changes in input or cursor move), it builds new input with
    prefix ("Commands:"), and suffix (list of commands found) """
    global old_input, commands, commands_pos
    if modifier_data != w.current_buffer():
        return ""
    input = w.string_remove_color(string, "")
    input = input.strip()
    if old_input == None or input != old_input:
        old_commands = commands
        commands = get_matching_commands(input)
        if commands != old_commands and len(input) > 0:
            commands_pos = 0
        old_input = input
    commandstr = get_command_string(commands, commands_pos, input)
    return w.config_get_plugin("message") + string + commandstr

def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    global commands, commands_pos
    if command == "/input search_text" or command.find("/input jump") == 0:
        # search text or jump to another buffer is forbidden now
        return w.WEECHAT_RC_OK_EAT
    elif command == "/input complete_next":
        # choose next buffer in list
        commands_pos += 1
        if commands_pos >= len(commands):
            commands_pos = 0
        w.hook_signal_send("input_text_changed",
                                 w.WEECHAT_HOOK_SIGNAL_STRING, "")
        return w.WEECHAT_RC_OK_EAT
    elif command == "/input complete_previous":
        # choose previous buffer in list
        commands_pos -= 1
        if commands_pos < 0:
            commands_pos = len(commands) - 1
        w.hook_signal_send("input_text_changed",
                                 w.WEECHAT_HOOK_SIGNAL_STRING, "")
        return w.WEECHAT_RC_OK_EAT
    elif command == "/input return":
        # As in enter was pressed.
        # Put the current command on the input bar
        histsearch_end(buffer)
        if len(commands) > 0:
            w.command(buffer, "/input insert " + commands[commands_pos])
        return w.WEECHAT_RC_OK_EAT
    return w.WEECHAT_RC_OK

def command_run_buffer(data, buffer, command):
    """ Function called when a command "/buffer xxxx" is run """
    return w.WEECHAT_RC_OK_EAT

def command_run_window(data, buffer, command):
    """ Function called when a command "/buffer xxxx" is run """
    return w.WEECHAT_RC_OK_EAT

def histsearch_cmd(data, buffer, args):
    """ Command "/histsearch": just hook what we need """
    global hooks

    if "modifier" in hooks:
        histsearch_end(buffer)
    else:
        histsearch_start(buffer)
    return w.WEECHAT_RC_OK

def histsearch_unload_script():
    """ Function called when script is unloaded """
    unhook_all()
    return w.WEECHAT_RC_OK
