# coding: utf-8
#
# Copyright (c) 2012-2018 by nesthib <nesthib@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# This script checks every message before it is sent and blocks messages which
# correspond to misformatted commands (e.g. " /msg NickServ…") to avoid the
# unfortunate discosure of personnal informations.
#
# 2022-11-11: Kevin Morris <kevr@cost.org>
#        0.3: remove leading whitespaces in all situations
# 2018-06-07: nils_2@freenode.#weechat
#        0.2: make script compatible with Python 3.x
# 2012-03-07: nesthib <nesthib@gmail.com>
#        0.1: initial release

try:
    import weechat
except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org")
    quit()

import re

name = "unwanted_msg"
author = "nesthib <nesthib@gmail.com>"
version = "0.3"
license = "GPL"
description = "Avoid sending misformatted messages"
shutdown_function = ""
charset = ""

config = {
    "left_delimiter": "[",
    "right_delimiter": "]"
}

weechat.register(name, author, version, license,
                 description, shutdown_function, charset)


def raw_command_cb(data, buffer, args):
    """ Implementation of the /raw command.

    /raw sends arguments given as verbatim as possible to the buffer.
    Commands themselves remove whitespace found between the command and
    any arguments, and so, a special delimiter is required to decipher
    what the user intends when formatting inputs with included
    whitespace: [ some message].


    Example output:
        /raw  hello
            "hello"
        /raw [ hello]
            " hello"
    """
    left = weechat.config_get_plugin("left_delimiter")
    right = weechat.config_get_plugin("right_delimiter")
    weechat.command(buffer, args.lstrip(left).rstrip(right))
    return weechat.WEECHAT_RC_OK


def my_modifier_cb(buf, modifier, modifier_data, string):
    if re.match(r'^\s.+$', string):
        # In the case where there actually is whitespace and we need to
        # deal with it, reset the input position to 0. We are only
        # dealing with the beginning of the string, so this has no
        # negative side affects. Without this, space causes the cursor
        # position to increment when attempting to type a whitespace
        # at the beginning of an otherwise-not-lead-with-whitespace string.
        weechat.buffer_set(modifier_data, "input_pos", "0")
    return string.lstrip()  # Remove _any_ whitespace at the start.


def get_left_delimiter():
    return weechat.config_get_plugin("left_delimiter")


def get_right_delimiter():
    return weechat.config_get_plugin("right_delimiter")


def get_usage():
    """ A dynamic function that produces usage based on the plugin's
    left_delimiter and right_delimiter options. """
    return get_left_delimiter() + " raw-text" + get_right_delimiter()


if __name__ == "__main__":
    for option, default_value in config.items():
        is_set = weechat.config_is_set_plugin(option)
        if not is_set:
            weechat.config_set_plugin(option, default_value)

    desc = f"""Send raw input (including whitespace in enclosed configured \
delimiters) to the current buffer.

Optional whitespace delimiters can be configured:

    plugins.var.python.{name}.left_delimiter
        - default: [
        - configured: {get_left_delimiter()}

    plugins.var.python.{name}.right_delimiter
        - default: ]
        - configured: {get_right_delimiter()}

Execute '/python reload unwanted_msg' to reflect configuration changes.
"""

    weechat.hook_modifier("input_text_content", "my_modifier_cb", str())
    weechat.hook_command("raw", desc, get_usage(), "", str(),
                         "raw_command_cb", str())
