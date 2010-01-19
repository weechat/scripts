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
# 2010-01-14, xt
#   version 0.3: steal more chars from m4v
# 2010-01-06, xt <xt@bash.no>
#   version 0.2: fix idiotic programming
# 2009-11-12, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re

SCRIPT_NAME    = "upside_down"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Replaces text you write with upside down text"

settings = {}

replacements = {
# Upper case
    u'A' : u'\N{FOR ALL}',
    u'B' : u'\N{GREEK SMALL LETTER XI}',
    u'C' : u'\N{ROMAN NUMERAL REVERSED ONE HUNDRED}',
    u'D' : u'\N{LEFT HALF BLACK CIRCLE}',
    u'E' : u'\N{LATIN CAPITAL LETTER REVERSED E}',
    u'F' : u'\N{TURNED CAPITAL F}',
    u'G' : u'\N{TURNED SANS-SERIF CAPITAL G}',
    u'J' : u'\N{LATIN SMALL LETTER LONG S}',
    u'K' : u'\N{RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT}',
    u'L' : u'\ua780',
    u'M' : u'W',
    u'N' : u'\N{LATIN LETTER SMALL CAPITAL REVERSED N}',
    u'P' : u'\N{CYRILLIC CAPITAL LETTER KOMI DE}',
    u'Q' : u'\N{GREEK CAPITAL LETTER OMICRON WITH TONOS}',
    u'R' : u'\N{LATIN LETTER SMALL CAPITAL TURNED R}',
    u'T' : u'\N{UP TACK}',
    u'U' : u'\N{INTERSECTION}',
    u'V' : u'\u0245',
    u'Y' : u'\N{TURNED SANS-SERIF CAPITAL Y}',
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
