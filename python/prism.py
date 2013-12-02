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
# 2013-11-26, Seganku <seganku@zenu.net>
#    v0.2.7: add -c switch for the option to pass output to a command
# 2013-07-19, Sebastien Helleu <flashcode@flashtux.org>
#    v0.2.6: use buffer received in command callback instead of current buffer
# 2013-05-04, Rylai
#    v0.2.5: add -e switch for the option to destroy the eyes of all
#            who have the misfortune of seeing your text
# 2013-04-26, Biohazard
#   v0.2.4: add support for using the command through keybindings
# 2013-03-12, R1cochet
#   v0.2.3: add -b switch for backwards/reverse text
# 2013-01-29, SuperT1R:
#   v0.2.2: add -m switch to append /me to the beginning of the output


import weechat as w
import random
import re


SCRIPT_NAME    = "prism"
SCRIPT_AUTHOR  = "Alex Barrett <al.barrett@gmail.com>"
SCRIPT_VERSION = "0.2.7"
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
                   "[-rwmbe] text|-c[wbe] <sep> <command> <sep>text",
                   "    -r: randomizes the order of the color sequence\n"
                   "    -w: color entire words instead of individual characters\n"
                   "    -m: append /me to beginning of output\n"
                   "    -b: backwards text (entire string is reversed)\n"
                   "    -e: eye-destroying colors (randomized background colors)\n"
                   "    -c: specify a separator to turn on colorization\n"
                   "        eg. -c : /topic :howdy howdy howdy\n"
                   "  text: text to be colored",
                   "-r|-w|-m|-b|-e|-c", "prism_cmd_cb", "")
def find_another_color(colorCode):
    otherColor = (unicode(colors[random.randint(1, color_count - 1) % color_count]).rjust(2, "0"))
    while (otherColor == colorCode):
        otherColor = (unicode(colors[random.randint(1, color_count - 1) % color_count]).rjust(2, "0"))
    return otherColor

def prism_cmd_cb(data, buffer, args):
    global color_index

    input = args.decode("UTF-8")
    input_method = "command"

    if not input:
        input = w.buffer_get_string(buffer, "input")
        input = input.decode("UTF-8")
        input_method = "keybinding"

    # select a tokenizer and increment mode
    regex = regex_chars
    inc   = 1
    bs    = 0
    cmd   = ""
    m = re.match(r'(-[rwmbec]+)\s+(?:([^ ]+)\s+(.+?)\s*\2)?(.*)', input)
    if m and input_method == "command":
        opts = m.group(1)
        input = m.group(4)
        if 'c' in opts:
            cmd = m.group(3)
        if 'w' in opts:
            regex = regex_words
        if 'r' in opts:
            inc = 0
        if 'm' in opts:
            cmd = "/me"
        if 'b' in opts:
            input = input[::-1]
        if 'e' in opts:
             bs = 1

    output = u""
    tokens = re.findall(regex, input)
    for token in tokens:
        # prefix each token with a color code
        color_code = unicode(colors[color_index % color_count]).rjust(2, "0")
        if bs == 1:
            output += u'\x03' + color_code + ',' + find_another_color(color_code) + token
        else:
            output += u"\x03" + color_code  + token

        # select the next color or another color at
        # random depending on the options specified
        if inc == 0:
            color_index += random.randint(1, color_count - 1)
        else:
            color_index += inc

    # output starting with a / will be executed as a
    # command unless we escape it with a preceding /
    # Commands should use the -c flag
    if len(output) > 0 and output[0] == "/":
        output = "/" + output
    if len(cmd) > 0:
        output = cmd + ' ' + output
    if input_method == "keybinding":
        w.buffer_set(buffer, "input", output.encode("UTF-8"))
    else:
        w.command(buffer, output.encode("UTF-8"))
    return w.WEECHAT_RC_OK
