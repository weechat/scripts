# -*- coding: utf-8 -*-
# Copyright (c) 2010 by hokkaido & tmr <hokzerj@ymail.com>
#
# History:
#
# 2010-02-26, hokkaido
#   version 0.2: * Removes re module and fixes the issue with regex
#                  characters (like '^') as command character.
#                * Added support for utf-8 command characters.
# 2010-02-25, hokkaido
#   version 0.1: Initial release.
#
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
''' Add more command characters. Especially handy for mobile phone users 
if '/' is hard to reach.

Usage: Load cmdchars.py and set plugins.var.python.cmdchars.characters.

If you want to use '-', ',' and '§' as supplemental command characters:

    /set plugins.var.python.cmdchars.characters ,-§

In case you want to say something starting with ',', '-' or '§' you have 
to type the character twice. Like: ",,Hello world!". This will result 
string ",Hello world!" to be output.

'''

import weechat as w

SCRIPT_NAME    = "cmdchars"
SCRIPT_AUTHOR  = "hokkaido & tmr"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Adds supplemental command characters"

settings = {
    'characters': '',
}

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if w.config_get_plugin(option) == "":
            w.config_set_plugin(option, default_value)

    # Hooks we want to hook
    hook_command_run = {
        "input" : ("/input return",  "command_run_input"),
    }

    # Hook all hooks !
    for hook, value in hook_command_run.iteritems():
        w.hook_command_run(value[0], value[1], "")


def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    if command == "/input return": # As in enter was pressed.

        # Get input contents
        input_s = unicode(w.buffer_get_string(buffer, 'input'), 'utf-8')

        characters = unicode(w.config_get_plugin('characters'), 'utf-8')

        for char in characters:
            if input_s.startswith(char) and not input_s.startswith(char * 2):
                input_s = input_s[1:]
                w.command(buffer, '/%s' % (input_s.encode('utf-8')))

                # Don't output the command just found into the buffer
                w.buffer_set(buffer, 'input', '')

                return w.WEECHAT_RC_OK

            elif input_s.startswith(char * 2):
                # If command character is written twice then remove 
                # the first character and output string as normal input.
                input_s = input_s[1:]
                break

        # Not a command. Spit it out normally.
        w.buffer_set(buffer, 'input', input_s.encode('utf-8'))

    return w.WEECHAT_RC_OK
