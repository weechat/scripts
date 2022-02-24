# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
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
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2020-06-05, Normen Hansen <normen667@gmail.com>
#   version 0.7: add option to change prefix of entered text
# 2019-06-17, Brad Hubbard <bhubbard@redhat.com>
#   version 0.6: replace iteritems with items for python3 compatability
# 2011-07-17, Sébastien Helleu <flashcode@flashtux.org>
#   version 0.5: allow empty value for pairs or words
# 2011-02-01, xt
#   version 0.4: improve regexp for word replacement
# 2010-11-26, xt <xt@bash.no>
#   version 0.3: don't replace in /set commands
# 2009-10-27, xt <xt@bash.no>
#   version 0.2: also replace on words
# 2009-10-22, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "text_replace"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.7"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Replaces text you write with replacement text"

# script options
settings = {
        'replacement_pairs': '(:=:),):=:(',   # pairs separated by , orig text and replacement separated by =
        'replacement_words': 'hhe=heh',       # words separated by , orig text and replacement separated by =
        'replacement_prefixes': ':=/',       # strings separated by , orig prefix and replacement separated by =
}



if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    # Hooks we want to hook
    hook_command_run = {
        "input" : ("/input return",  "command_run_input"),
    }
    # Hook all hooks !
    for hook, value in hook_command_run.items():
        w.hook_command_run(value[0], value[1], "")


def command_run_input(data, buffer, command):
    """ Function called when a command "/input xxxx" is run """
    if command == "/input return": # As in enter was pressed.

        # Get input contents
        input_s = w.buffer_get_string(buffer, 'input')

        # Skip modification of settings
        if input_s.startswith('/set '):
            return w.WEECHAT_RC_OK

        # Iterate transformation pairs
        for replace_item in w.config_get_plugin('replacement_pairs').split(','):
            if replace_item:
                orig, replaced = replace_item.split('=')
                input_s = input_s.replace(orig, replaced)
        # Iterate words
        for replace_item in w.config_get_plugin('replacement_words').split(','):
            if replace_item:
                orig, replaced = replace_item.split('=')
                # Search for whitespace+word+whitespace and replace the word
                input_s = re.sub('(\s+|^)%s(\s+|$)' %orig, '\\1%s\\2' %replaced, input_s)
        # Iterate prefixes
        for replace_item in w.config_get_plugin('replacement_prefixes').split(','):
            if replace_item:
                orig, replaced = replace_item.split('=')
                if input_s.startswith(orig):
                    input_s = input_s.replace(orig, replaced, 1)

        # Spit it out
        w.buffer_set(buffer, 'input', input_s)
    return w.WEECHAT_RC_OK
