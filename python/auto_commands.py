# Copyright (c) 2025 by Kamil Wiśniewski <tomteipl@gmail.com>
#
# This script sends auto commands on start
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
#
#[Change Log]
#
# 0.3   : Implemented the hook_completion_cb to provide autocompletion for stored commands.
#       : Added Guides.
#       : Added <del> by Index or String values.
#       : Added "time" command to set timer for sending commands after start.
#
# 0.2   : added list, add, delete, clear commands
#       : added save and load commands functions
#
# 0.1   : Initial release

import weechat


SCRIPT_NAME = "auto_commands"
SCRIPT_AUTHOR = "Tomteipl"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Send auto commands on start"

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")


#   Guides
help = """
    Usage:\n

    IMPORTANT: Commands are sent on client start only once !
    /autocommands add <command> - adds command to the list. You can use spaces and special signs.
    /autocommands del <number/string> - deletes command from the list. You can use /autocommands list to see the numbers or tap TAB for auto completion.
    /autocommands list - shows the list of commands with index.
    /autocommands clear - clears the list of commands.
    /autocommands time <miliseconds> - 1sec = 1000ms, sets the timer for hook in miliseconds. Default value 10000ms = 10 sec.
    """



commands = []   # Commands are stored here

def load_commands():
    global commands
    saved_commands = weechat.config_get_plugin("commands")
    commands = saved_commands.split(",") if saved_commands else []

def save_commands():
    weechat.config_set_plugin("commands", ",".join(commands))

# adds commands to the list
def add_command(data, buffer, args):
    commands.append(args)
    save_commands()
    weechat.prnt(buffer, f"Command '{args}' added!")
    return weechat.WEECHAT_RC_OK

def send_auto_commands(data, buffer):
    for command in commands:
        weechat.command("", command)
        weechat.prnt("", f"Command '{command}' sent!")
    return weechat.WEECHAT_RC_OK


# [ ---COMMANDS--- ]
def commands_cb(data, buffer, args):
    if args.startswith("list"):
        weechat.prnt(buffer, "Current commands: \n")
        for i, command in enumerate(commands):
            weechat.prnt(buffer, f"{i + 1}. {command}")
        return weechat.WEECHAT_RC_OK

    elif args.startswith("add"):
        add_command(data, buffer, args[len("add "):])
        return weechat.WEECHAT_RC_OK

    elif args.startswith("del"):
        try:
            arg_value = " ".join(args.split()[1:])

            if arg_value.isdigit():         # delete command by index (example: /autocommands del 1)
                index = int(args.split()[1]) -1

                if 0 <= index < len(commands):
                    del_command = commands.pop(index)
                    save_commands()
                    weechat.prnt(buffer, f"Command '{del_command}' deleted!")
                    return weechat.WEECHAT_RC_OK

                else:
                    weechat.prnt(buffer, "Invalid command number!")
                    return weechat.WEECHAT_RC_OK

            elif arg_value in commands:          # delete command by string, you can use autocomplete (example: /autocommands del /join #channel)
                commands.remove(arg_value)
                save_commands()
                weechat.prnt(buffer, f"Command '{arg_value}' deleted!")
                return weechat.WEECHAT_RC_OK
            
            else:
                weechat.prnt(buffer, "Invalid command number or string!")
                return weechat.WEECHAT_RC_OK

        except (ValueError, IndexError):
                weechat.prnt(buffer, "Invalid command number!")
                return weechat.WEECHAT_RC_OK

    elif args.startswith("time"):           # set timer for hook
        try:
            new_time = int(args.split()[1])
            weechat.config_set_plugin("timer", str(new_time))
            weechat.prnt(buffer, f"Timer set to {new_time} ms!")

        except (ValueError, IndexError):
            weechat.prnt(buffer, "Invalid time value! /autocommands time <miliseconds>")

        return weechat.WEECHAT_RC_OK

    elif args.startswith("clear"):
        commands.clear()
        weechat.prnt(buffer, "Commands cleared!")
        return weechat.WEECHAT_RC_OK

    else:
        weechat.prnt(buffer, f"{help}")
        return weechat.WEECHAT_RC_OK



# Commands completion when using <del>
def hook_completion_cb(data, completion, buffer, completion_item):
    for command in commands:
        weechat.completion_list_add(completion_item, command, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK



load_commands()

weechat.hook_completion("autocommands_cmds", "List auto commands", "hook_completion_cb", "")
weechat.hook_command(
    "autocommands",
    "List auto commands",
    "",
    "",
    "list || add  || del %(autocommands_cmds) || clear || time",
    "commands_cb",
    "",
)

timer = int(weechat.config_get_plugin("timer") or 10000)
weechat.hook_timer(timer, 0, 1, "send_auto_commands", "")
