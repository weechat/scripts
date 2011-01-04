# -*- coding: utf-8 -*-
#
###
# Copyright (c) 2011, Andy Pilate (Lenoob <andypilate at gmail dot com> )
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###


# Just do /leet to convert text to leet ("/help leet" for help)

# Changelog
# 0.1
# First version

import weechat as w
import re

SCRIPT_NAME    = "leet"
SCRIPT_AUTHOR  = "Lenoob"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Convert text to leet"

settings = {}

replacements = {
# Upper case
    u'A' : u'4',
    u'B' : u')3',
    u'C' : u'©',
    u'D' : u'|)',
    u'E' : u'3',
    u'F' : u'|=',
    u'G' : u'6',
    u'J' : u'(/',
    u'K' : u'|<',
    u'L' : u'£',
    u'M' : u'|\\/|',
    u'N' : u'|\\|',
    u'P' : u'|*',
    u'Q' : u'(_,)',
    u'R' : u'|2',
    u'T' : u'7',
    u'U' : u'|_|',
    u'V' : u'\\/',
    u'Y' : u'\'/',
    u'Z' : u'%',
    u'O' : u'0',
    u'S' : u'5',

    'a' : u'4',
    'b' : u')3',
    'c' : u'©',
    'd' : u'|)',
    'e' : u'3',
    'f' : u'|=',
    'g' : u'6',
    'j' : u'(/',
    'k' : u'|<',
    'l' : u'£',
    'm' : u'|\\/|',
    'n' : u'|\\|',
    'p' : u'|*',
    'q' : u'(_,)',
    'r' : u'|2',
    't' : u'7',
    'u' : u'|_|',
    'v' : u'\\/',
    'y' : u'\'/',
    'z' : u'%',
    'o' : u'0',
    's' : u'5',


}



if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    w.hook_command("leet",
                         SCRIPT_DESC,
                         "[text]",
                         "text: text to be in leet\n"
                         "",
                         "", "leet_cmd_cb", "")


def leet_cmd_cb(data, buffer, args):
    ''' Command /leet '''
    translate_input = args
    if not translate_input:
        translate_input = w.buffer_get_string(buffer, "input")
    outstring = ''
    for char  in translate_input:
        if char in replacements:
            char = replacements[char]
        outstring += char
    outstring = outstring.encode('UTF-8')
    w.buffer_set(buffer, 'input', outstring)
    w.buffer_set(buffer, 'input_pos', '%d' % len(outstring))
    return w.WEECHAT_RC_OK
