# Copyright (c) 2008 Ben <dumbtech@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# TODO: Clean up code and add UTF-8 support.

import weechat as wc
import re

wc.register("wildcard", "0.1", "", "Adds wildcard support to nick completions.")
wc.add_keyboard_handler("wildcard")

if wc.get_plugin_config("max") == "": wc.set_plugin_config("max", "9")
max = wc.get_plugin_config("max")
warned = False

def wildcard(key, input, input_after):
    global warned
    if input != "":
        pos = int(wc.get_info("input_pos"))
        end = input.find(" ", pos)
        if end == -1: end = None
        word = input[input.rfind(" ", 0, pos) + 1 : end]
        if key == "tab" and word.find("*") != -1:
            all_nicks = wc.get_nick_info(wc.get_info("server"), wc.get_info("channel"))
            regex = re.compile(re.escape(word).replace(r"\*", ".*"), re.I)
            matching_nicks = filter(regex.match, all_nicks)
            if len(matching_nicks) > int(max) and warned == False:
                wc.prnt("Warning: you are about to expand over " + max + " nicks." \
                        + " Press <tab> again if you're sure you want to continue.")
                warned = True
            else:
                for i in range(0, len(word)): wc.command("/key call backspace")
                wc.command("/key call insert " + ' '.join(matching_nicks))
                warned = False
    return wc.PLUGIN_RC_OK
