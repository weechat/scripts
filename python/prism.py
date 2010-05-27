# Copyright (c) 2010 Alex Barrett <al.barrett@gmail.com>
#
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
# DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
# TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
# 0. You just DO WHAT THE FUCK YOU WANT TO.


import weechat as w
import random
import re


SCRIPT_NAME    = "prism"
SCRIPT_AUTHOR  = "Alex Barrett <al.barrett@gmail.com>"
SCRIPT_VERSION = "0.2.1"
SCRIPT_LICENSE = "WTFPL"
SCRIPT_DESC    = "Taste the rainbow."


# red, lightred, brown, yellow, green, lightgreen, cyan,
# lightcyan, blue, lightblue, magenta, lightmagenta
colors = [5, 4, 7, 8, 3, 9, 10, 11, 2, 12, 6, 13]
color_count = len(colors)

# keeping a global index means the coloring will pick up where it left off
color_index = 0

# spaces don't need to be colored and commas cannot be because mIRC is dumb
chars_neutral = " ,"
chars_control = "\x01-\x1f\x7f-\x9f"

regex_chars = "[^%(n)s%(s)s][%(n)s%(s)s]*" % { 'n': chars_neutral, 's': chars_control }
regex_words = "[^%(n)s]+[%(n)s%(s)s]*" % { 'n': chars_neutral, 's': chars_control }


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
              SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    w.hook_command("prism",
                   SCRIPT_DESC,
                   "[-rw] text",
                   "    -r: randomizes the order of the color sequence\n"
                   "    -w: color entire words instead of individual characters\n"
                   "  text: text to be colored",
                   "", "prism_cmd_cb", "")


def prism_cmd_cb(data, buffer, args):
    global color_index

    input = args.decode("UTF-8")

    # select a tokenizer and increment mode
    regex = regex_chars
    inc = 1

    m = re.match('-[rw]* ', input)
    if m:
        opts = m.group(0)
        input = input[len(opts):]
        if 'w' in opts:
            regex = regex_words
        if 'r' in opts:
            inc = 0

    output = u""
    tokens = re.findall(regex, input)
    for token in tokens:
        # prefix each token with a color code
        color_code = unicode(colors[color_index % color_count]).rjust(2, "0")
        output += u"\x03" + color_code  + token

        # select the next color or another color at
        # random depending on the options specified
        if inc == 0:
            color_index += random.randint(1, color_count - 1)
        else:
            color_index += inc 

    # output starting with a / will be executed as a
    # command unless we escape it with a preceding /
    if len(output) > 0 and output[0] == "/":
        output = "/" + output

    w.command(w.current_buffer(), output.encode("UTF-8"))
    return w.WEECHAT_RC_OK
