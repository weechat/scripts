# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by FlashCode <flashcode@flashtux.org>
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
# Quick jump to buffers.
# (this script requires WeeChat 0.2.7 or newer)
#
# History:
#
# 2009-02-18, FlashCode <flashcode@flashtux.org>:
#     version 0.4: do not hook command and init options if register failed
# 2009-02-08, FlashCode <flashcode@flashtux.org>:
#     version 0.3: case insensitive search for buffers names
# 2009-02-08, FlashCode <flashcode@flashtux.org>:
#     version 0.2: add help about Tab key
# 2009-02-08, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release
#

import weechat

SCRIPT_NAME    = "go"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Quick jump to buffers"

# script options
settings = {
    "color_number"                 : "yellow,magenta",
    "color_number_selected"        : "yellow,red",
    "color_name"                   : "black,cyan",
    "color_name_selected"          : "black,brown",
    "color_name_highlight"         : "red,cyan",
    "color_name_highlight_selected": "red,brown",
    "message"                      : "Go to: ",
}

# hooks management
hook_command_run = {
    "input" : ("/input *",  "command_run_input"),
    "buffer": ("/buffer *", "command_run_buffer"),
    "window": ("/window *", "command_run_window"),
}
hooks = {}

# input before command /go (we'll restore it later)
saved_input = ""

# last user input (if changed, we'll update list of matching buffers)
old_input = None

# matching buffers
buffers = []
buffers_pos = 0

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "go_unload_script", ""):
    weechat.hook_command("go", "Quick jump to buffers", "",
                         "You can bind command to a key, for example:\n  /key meta-g /go\n\n" +
                         "You can use completion key (commonly Tab and shift-Tab) to select " +
                         "next/previous buffer in list.",
                         "", "go_cmd")
    for option, default_value in settings.iteritems():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value)

def unhook_one(hook):
    """ Unhook something hooked by this script """
    global hooks
    if hook in hooks:
        weechat.unhook(hooks[hook])
        del hooks[hook]

def unhook_all():
    """ Unhook all """
    global hook_command_run
    unhook_one("modifier")
    map(unhook_one, hook_command_run.keys())

def hook_all():
    """ Hook command_run and modifier """
    global hook_command_run, hooks
    for hook, value in hook_command_run.iteritems():
        if hook not in hooks:
            hooks[hook] = weechat.hook_command_run(value[0], value[1])
    if "modifier" not in hooks:
        hooks["modifier"] = weechat.hook_modifier(
            "weechat_input_text_display_with_cursor", "input_modifier")

def go_start(buffer):
    """ Start go on buffer """
    global saved_input, old_input, buffers_pos
    hook_all()
    saved_input = weechat.buffer_get_string(buffer, "input")
    weechat.buffer_set(buffer, "input", "")
    old_input = None
    buffers_pos = 0

def go_end(buffer):
    """ End go on buffer """
    global saved_input, old_input
    unhook_all()
    weechat.buffer_set(buffer, "input", saved_input)
    old_input = None

def go_cmd(buffer, args):
    """ Command "/go": just hook what we need """
    global hooks
    if "modifier" in hooks:
        go_end(buffer)
    else:
        go_start(buffer)
    return weechat.WEECHAT_RC_OK

def get_matching_buffers(input):
    """ Return list with buffers matching user input """
    global buffers_pos
    list = []
    if len(input) == 0:
        buffers_pos = 0
    input = input.lower()
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        name = weechat.infolist_string(infolist, "name")
        if len(input) == 0 or name.lower().find(input) >= 0:
            number = weechat.infolist_integer(infolist, "number")
            list.append((number, name))
            if len(input) == 0 and weechat.infolist_pointer(infolist, "pointer") == weechat.current_buffer():
                buffers_pos = len(list) - 1
    weechat.infolist_free(infolist)
    return list

def buffers_to_string(buffers, pos, input):
    """ Return string built using list of buffers found (matching user input) """
    global settings
    string = ""
    colors = {}
    input = input.lower()
    for option in settings:
        colors[option] = weechat.config_get_plugin(option)
    for i in range(len(buffers)):
        index = buffers[i][1].lower().find(input)
        if index >= 0:
            index2 = index + len(input)
            selected = ""
            if i == pos:
                selected = "_selected"
            string += " " + \
                weechat.color(colors["color_number" + selected]) + str(buffers[i][0]) + \
                weechat.color(colors["color_name" + selected]) + buffers[i][1][:index] + \
                weechat.color(colors["color_name_highlight" + selected]) + buffers[i][1][index:index2] + \
                weechat.color(colors["color_name" + selected]) + buffers[i][1][index2:] + \
                weechat.color("reset")
    if string != "":
        string = "  " + string
    return string

def input_modifier(modifier, modifier_data, string):
    """ This modifier is called when input text item is built by WeeChat
    (commonly after changes in input or cursor move), it builds new input with
    prefix ("Go to:"), and suffix (list of buffers found) """
    global old_input, buffers, buffers_pos
    names = ""
    input = weechat.string_remove_color(string)
    input = input.strip()
    if old_input == None or input != old_input:
        old_buffers = buffers
        buffers = get_matching_buffers(input)
        if buffers != old_buffers and len(input) > 0:
            buffers_pos = 0
        old_input = input
    names = buffers_to_string(buffers, buffers_pos, input)
    return weechat.config_get_plugin("message") + string + names

def command_run_input(buffer, command):
    """ Function called when a command "/input xxxx" is run """
    global buffers, buffers_pos
    if command == "/input search_text" or command.find("/input jump") == 0:
        # search text or jump to another buffer is forbidden now
        return weechat.WEECHAT_RC_OK_EAT
    elif command == "/input complete_next":
        # choose next buffer in list
        buffers_pos += 1
        if buffers_pos >= len(buffers):
            buffers_pos = 0
    elif command == "/input complete_previous":
        # choose previous buffer in list
        buffers_pos -= 1
        if buffers_pos < 0:
            buffers_pos = len(buffers) - 1
    elif command == "/input return":
        # switch to selected buffer (if any)
        go_end(buffer)
        if len(buffers) > 0:
            weechat.command(buffer, "/buffer " + str(buffers[buffers_pos][0]))
        return weechat.WEECHAT_RC_OK_EAT
    return weechat.WEECHAT_RC_OK

def command_run_buffer(buffer, command):
    """ Function called when a command "/buffer xxxx" is run """
    return weechat.WEECHAT_RC_OK_EAT

def command_run_window(buffer, command):
    """ Function called when a command "/buffer xxxx" is run """
    return weechat.WEECHAT_RC_OK_EAT

def go_unload_script():
    """ Function called when script is unloaded """
    unhook_all()
    return weechat.WEECHAT_RC_OK
