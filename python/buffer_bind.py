# -*- coding: utf-8 -*-
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

import weechat as w

SCRIPT_NAME = "buffer_bind"
SCRIPT_AUTHOR = "Trevor 'tee' Slocum <tslocum@gmail.com>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Bind meta-<key> to the current buffer"
SCRIPT_NOTE = """Case sensitivity is controlled via plugins.var.python.%s.case_sensitive (default: off)

%s is a port of irssi's window_alias written by veli@piipiip.net""" % (SCRIPT_NAME, SCRIPT_NAME)

SETTINGS = {
    "case_sensitive": "off"
}


def command_buffer_bind(data, buffer, args):
    if len(args) == 1 and args[0] != "":
        bindkey = args[0]
        buffername = w.buffer_get_string(buffer, "name")

        bind_keys = [bindkey]
        if w.config_get_plugin("case_sensitive") == "off" and bindkey.isalpha():
            bind_keys.append(bindkey.swapcase())
        for bind_keys_i in bind_keys:
            w.command(buffer, "/key bind meta-%s /buffer %s" % (bind_keys_i, buffername))

        w.prnt(buffer, "Buffer %s is now accessible with meta-%s" % (buffername, bindkey))
    else:
        w.command(buffer, "/help %s" % SCRIPT_NAME)

    return w.WEECHAT_RC_OK_EAT


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
              SCRIPT_DESC, "", ""):
    for option, value in SETTINGS.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, value)

    w.hook_command(SCRIPT_NAME, SCRIPT_DESC, "<key>", SCRIPT_NOTE, "key", "command_buffer_bind", "")
