# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 by Ferus Castor <ferus+weechat@airmail.cc>
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


# Select a buffer from dmenu or rofi
# To call externally (IE: from i3), enable weechat fifo and run:
#  $ echo "core.weechat */buffer_dmenu" >> $(find ~/.weechat -type p)
#
# Optionally requires i3-py [py2] (or i3ipc [py3]) to focus weechat in i3
#
# History:
# 2020-06-08, Ferus
#     version 0.2: drop support of py2 and fix error when closing
#                  dmenu/rofi with no choice selected
# 2020-02024, Seirdy
#     version 0.1.2: py3-ok
# 2017-05-03, Ferus
#     version 0.1.1: fix argument error for config_set_plugin
# 2016-05-01, Ferus
#     version 0.1: initial release - requires WeeChat ≥ 0.3.7

# TODO:
#   Option to remove certain buffer types
#   Implement `focus` for other window managers
#   if buffer == currentbuffer: switch to previous buffer

# pylint: disable=I0011,W0603,W1401

SCRIPT_NAME = "buffer_dmenu"
SCRIPT_AUTHOR = "Ferus <ferus+weechat@airmail.cc>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = (
    "List buffers in dmenu (or rofi), changes active window to selected buffer"
)
SCRIPT_COMMAND = "buffer_dmenu"

import os
import subprocess

try:
    import weechat as w
except ImportError as e:
    print("This script must be run under WeeChat.")
    exit(1)

try:
    import i3ipc as i3

    have_i3 = True
except ImportError as e:
    have_i3 = False

settings = {
    "launcher": ("dmenu", "launcher to use (supported: dmenu/rofi)"),
    "focus": (
        "false",
        "whether to immediately focus the terminal after selecting buffer",
    ),
    "focus.wm": ("i3", "wm focus logic to use (supported: i3)"),
    "dmenu.command": ("dmenu -b -i -l 20", "command used to call dmenu"),
    "rofi.command": (
        "rofi -p '# ' -dmenu -lines 10 -columns 8 -auto-select -mesg '<big>Pick a <b>buffer</b> to jump to:</big>'",
        "command used to call rofi",
    ),
    "title.regex": ("WeeChat \d+\.\d+", "regex used to match weechat's title window"),
}


def check_dmenu():
    devnull = open(os.devnull)
    retcode = subprocess.call(["which", "dmenu"], stdout=devnull, stderr=devnull)
    return True if retcode == 0 else False


def check_rofi():
    devnull = open(os.devnull)
    retcode = subprocess.call(["which", "rofi"], stdout=devnull, stderr=devnull)
    return True if retcode == 0 else False


def get_launcher():
    launcher = w.config_get_plugin("launcher")
    command = None
    if launcher == "dmenu":
        if check_dmenu():
            command = w.config_get_plugin("dmenu.command")
    elif launcher == "rofi":
        if check_rofi():
            command = w.config_get_plugin("rofi.command")
    return command


def launch(options):
    launcher = get_launcher()
    if launcher:
        call(launcher, options)
    return True


def focus():
    if w.config_string_to_boolean(w.config_get_plugin("focus")):
        if w.config_get_plugin("focus.wm") == "i3":
            focus_i3()


def focus_i3():
    if have_i3:
        regex = w.config_get_plugin("title.regex")

        i3conn = i3.Connection()
        weechat = i3conn.get_tree().find_named(regex)[0]
        weechat.command("focus")


def call(command, options):
    options = "\n".join(options)

    w.hook_process_hashtable(
        "sh",
        {"arg1": "-c", "arg2": 'echo "{0}" | {1}'.format(options, command)},
        10 * 1000,
        "launch_process_cb",
        "",
    )


process_output = ""


def launch_process_cb(data, command, rc, out, err):
    global process_output
    if out == "" or ":" not in out:
        return w.WEECHAT_RC_ERROR
    process_output += out
    if int(rc) >= 0:
        selected = process_output.strip("\n")
        name = selected.split(":")
        process_output = ""
        switch_to_buffer(name)
        focus()
    return w.WEECHAT_RC_OK


def get_open_buffers():
    buffers = []
    infolist = w.infolist_get("buffer", "", "")
    if infolist:
        while w.infolist_next(infolist):
            name = w.infolist_string(infolist, "name")
            number = w.infolist_integer(infolist, "number")
            _ = "{0}:{1}".format(number, name)
            buffers.append(_)
        w.infolist_free(infolist)
    return buffers


def get_hotlist_buffers():
    buffers = []
    infolist = w.infolist_get("hotlist", "", "")
    if infolist:
        while w.infolist_next(infolist):
            number = w.infolist_integer(infolist, "buffer_number")
            buffer = w.infolist_pointer(infolist, "buffer_pointer")
            name = w.buffer_get_string(buffer, "name")
            _ = "{0}:{1}".format(number, name)
            buffers.append(_)
        w.infolist_free(infolist)
    return buffers


def switch_to_buffer(buffer_name):
    w.command("", "/buffer {0}".format(buffer_name))


def dmenu_cmd_cb(data, buffer, args):
    """ Command /buffers_dmenu """
    if args == "hotlist":
        buffers = get_hotlist_buffers()
    else:
        buffers = get_open_buffers()

    if not launch(buffers):
        return w.WEECHAT_RC_ERROR
    return w.WEECHAT_RC_OK


if w.register(
    SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
):
    version = w.info_get("version_number", "") or 0
    for option, value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, value[0])
        if int(version) >= 0x00030500:
            w.config_set_desc_plugin(
                option, '{0} (default: "{1}")'.format(value[1], value[0])
            )

    w.hook_command(
        SCRIPT_COMMAND,
        "Show a list of all buffers in dmenu",
        "[hotlist]",
        "  hotlist: shows hotlist buffers only\n"
        "\n"
        "To call externally (IE: from i3), enable weechat fifo and run:\n"
        "  $ echo 'core.weechat */buffer_dmenu' >> $(find ~/.weechat -type p)\n"
        "\n"
        "To focus the terminal containing WeeChat for the following WM:\n"
        "  i3: requires i3ipc from pip3\n",
        "",
        "dmenu_cmd_cb",
        "",
    )
