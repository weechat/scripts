# -*- coding: utf-8 -*-
# (this script requires WeeChat 0.3.0 or newer)
#
# Copyright 2018 tx <trqx@goat.si>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# self-censor stuff you were going to say
#
# configuration examples:
#
# set comma separated words:
# /set plugins.var.python.selfcensor.censors "shit,fuck"
# /set plugins.var.python.selfcensor.censors "://reddit.com,://youtube.com"
# /set plugins.var.python.selfcensor.censors ""
#
# set warning message:
# /set plugins.var.python.selfcensor.warning "NOPE!"
#
# set tourette message (automatically sent instead of your message):
# /set plugins.var.python.selfcensor.tourette "FUCK"
#
# disable tourette:
# /set plugins.var.python.selfcensor.tourette ""
#
# History:
#
# 2018-09-20, tx <trqx@goat.si>
#    v0.1: initial release

import weechat as w
import re

SCRIPT_NAME = "selfcensor"
SCRIPT_AUTHOR = "tx <trqx@goat.si"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "self-censor stuff you were going to say"

# script options
settings = {"censors": "", "warning": "🔥", "tourette": ""}


if w.register(
    SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    # Hooks we want to hook
    hook_command_run = {"input": ("/input return", "command_run_input")}
    # Hook all hooks !
    for hook, value in hook_command_run.items():
        w.hook_command_run(value[0], value[1], "")


def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    if command == "/input return":  # As in enter was pressed.

        # Get input contents
        input_s = w.buffer_get_string(buffer, "input")

        # Skip modification of settings
        if input_s.startswith("/set "):
            return w.WEECHAT_RC_OK

        # Iterate censored stuff
        for censor in w.config_get_plugin("censors").split(","):
            if censor:
                if censor in input_s:
                    warning = "{} ({})".format(w.config_get_plugin("warning"), censor)
                    input_s = w.config_get_plugin("tourette")
                    w.command("", "/print " + warning)
                    break

        # Spit it out
        w.buffer_set(buffer, "input", input_s)
    return w.WEECHAT_RC_OK
