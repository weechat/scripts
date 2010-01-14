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
#
# USAGE: Bind a key to command /flip . Then write some text at input line 
# press your key to transform it to upside down.

#
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2010-01-06, xt <xt@bash.no>
#   version 0.2: fix idiotic programming
# 2009-11-12, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "upside_down"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Replaces text you write with upside down text"

settings = {}

replacements = {
     'a' : u"\u0250",
     'b' : u'q',
     'c' : u"\u0254",
     'd' : u'p',
     'e' : u"\u01DD",
     'f' : u"\u025F",
     'g' : u"\u0183",
     'h' : u'\u0265',
     'i' : u'\u0131',
     'j' : u'\u027E',
     'k' : u'\u029E',
     'm' : u'\u026F',
     'n' : u'u',
     'r' : u'\u0279',
     't' : u'\u0287',
     'p' : u'd',
     'u' : u'n',
     'q' : u'b',
     'v' : u'\u028C',
     'w' : u'\u028D',
     'y' : u'\u028E',
     '.' : u'\u02D9',
     '[' : u']',
     '(' : u')',
     '{' : u'}',
     '?' : u'\u00BF',
     '!' : u'\u00A1',
     "\'" :u',',
     '>' : u'<',
     '<' : u'>',
     '_' : u'\u203E',
     ';' : u'\u061B',
     '\u203F' : u'\u2040',
     '\u2045' : u'\u2046',
     '\u2234' : u'\u2235',
}



if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    w.hook_command("flip",
                         SCRIPT_DESC,
                         "[text]",
                         "text: text to be flipped\n"
                         "",
                         "", "flip_cmd_cb", "")


def flip_cmd_cb(data, buffer, args):
    ''' Command /flip '''
    translate_input = args
    if not translate_input:
        translate_input = w.buffer_get_string(w.current_buffer(), "input")
    outstring = ''
    for char  in translate_input:
        if char in replacements:
            char = replacements[char]
        outstring += char
    outstring = outstring.encode('UTF-8')
    w.buffer_set(w.current_buffer(), 'input', outstring)
    return w.WEECHAT_RC_OK
