# -*- coding: utf-8 -*-
#
# Copyright (c) 2019-2021 by eyJhb (eyjhbb@gmail.com)
#
# replaces incoming emojis with ascii text, and can replace outgoing
# messages with emojis, if the same syntax is followed.
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
# This script deletes weechatlog-files by age or size
# YOU ARE USING THIS SCRIPT AT YOUR OWN RISK!
#
# 2021-04-15: eyJhb
#       0.2 : added this text + error if unable to import emoji package
#
# 2019-09-16: eyJhb
#       0.1 : initial release
#
# Development is currently hosted at
# https://github.com/eyJhb/weechat-emoji2ascii

SCRIPT_NAME    = "emoji2ascii"
SCRIPT_AUTHOR  = "eyJhb <eyjhbb@gmail.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPLv3"
SCRIPT_DESC    = "Replaces emoji characters with ascii text and vice versa"

import_ok = True

try:
   import weechat as w
except:
   print("Script must be run under weechat. http://www.weechat.org")
   import_ok = False

try:
    import emoji
except ImportError:
    print("Failed to import emoji, please install it")
    import_ok = False

import re

def convert_emoji_to_aliases(data, modifier, modifier_data, string):
    return emoji.demojize(string)

def convert_aliases_to_emoji(data, modifier, modifier_data, string):
    return emoji.emojize(string)

if __name__ == "__main__" and import_ok:
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                  SCRIPT_DESC, "", "utf-8"):

        w.hook_modifier("irc_in2_away", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_cnotice", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_cprivmsg", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_kick", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_knock", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_notice", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_part", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_privmsg", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_quit", "convert_emoji_to_aliases", "")
        w.hook_modifier("irc_in2_wallops", "convert_emoji_to_aliases", "")

        w.hook_modifier("irc_out1_cprivmsg", "convert_aliases_to_emoji", "")
        w.hook_modifier("irc_out1_privmsg", "convert_aliases_to_emoji", "")
