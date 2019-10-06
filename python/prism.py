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
# 2019-08-24, simonpatapon <simon@patapon.lol>
#    v0.2.12: make the script compatible with python 3
# 2017-06-28, Aoede <eevee@posteo.eu>
#    v0.2.11: add -k switch to add black background
# 2015-11-16, wowaname <wowaname@volatile.ch>
#    v0.2.9, 0.2.10: wrote an actual parser rather than regex
# 2014-09-03, Matthew Martin <phy1729@gmail.com>
#    v0.2.8: add color reset to the end of the output
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
import sys


SCRIPT_NAME    = "prism"
SCRIPT_AUTHOR  = "Alex Barrett <al.barrett@gmail.com>"
SCRIPT_VERSION = "0.2.12"
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
                   "[-rwmbek] text|-c[wbe] <sep> <command> <sep>text",
                   "    -r: randomizes the order of the color sequence\n"
                   "    -w: color entire words instead of individual characters\n"
                   "    -m: append /me to beginning of output\n"
                   "    -b: backwards text (entire string is reversed)\n"
                   "    -e: eye-destroying colors (randomized background colors)\n"
                   "    -k: add black background (note: -e overrides this)\n"
                   "    -c: specify a separator to turn on colorization\n"
                   "        eg. -c : /topic :howdy howdy howdy\n"
                   "  text: text to be colored",
                   "-r|-w|-m|-b|-e|-c", "prism_cmd_cb", "")


def find_another_color(colorCode):
    otherColor = (str(colors[random.randint(1, color_count - 1) % color_count]).rjust(2, "0"))
    try:
        otherColor = otherColor.decode('utf-8')
    except AttributeError:
        pass
    while (otherColor == colorCode):
        otherColor = (str(colors[random.randint(1, color_count - 1) % color_count]).rjust(2, "0"))
        try:
            otherColor = otherColor.decode('utf-8')
        except AttributeError:
            pass
    return otherColor


def prism_cmd_cb(data, buffer, args):
    global color_index

    try:
        input = args.decode('utf-8')
    except AttributeError:
        input = args

    input_method = "command"

    if not input or (input[0] == '-' and input.find(' ') == -1):
        input = (input + ' ' if input else '') + w.buffer_get_string(buffer, "input")
        try:
            input = input.decode('utf-8')
        except AttributeError:
            pass
        input_method = "keybinding"

    if not input:
        return w.WEECHAT_RC_OK

    optstop = input and input[0] == '-' and input.find(' ')
    opts = input[1:optstop] if optstop else ''
    cmdstop = 'c' in opts and input.find(' ', optstop+1)
    cmd = ''
    if 'm' in opts:
        cmd = '/me '
    if 'c' in opts:
        find = input[optstop+1:cmdstop]
        where = input.find(find, cmdstop+1)
        cmd = input[cmdstop+1:where]
        input = input[where+len(find):]
    else:
        input = input[optstop+bool(optstop):]
    regex = regex_words if 'w' in opts else regex_chars
    inc = 'r' not in opts
    bs = 'e' in opts
    k = 'k' in opts
    input = input[::-1] if 'b' in opts else input

    output = ""
    tokens = re.findall(regex, input)
    for token in tokens:
        # prefix each token with a color code
        color_code = str(colors[color_index % color_count]).rjust(2, "0")
        try:
            color_code = color_code.decode('utf-8')
        except AttributeError:
            pass
        if bs == 1:
            output += '\x03' + color_code + ',' + find_another_color(color_code) + token
        elif k == 1:
            output += '\x03' + color_code + ',' + '1'.rjust(2, "0") + token
        else:
            output += "\x03" + color_code  + token

        # select the next color or another color at
        # random depending on the options specified
        if inc == 0:
            color_index += random.randint(1, color_count - 1)
        else:
            color_index += inc
    output += '\x0f'

    # output starting with a / will be executed as a
    # command unless we escape it with a preceding /
    # Commands should use the -c flag
    if len(output) > 0 and output[0] == "/":
        output = "/" + output
    if len(cmd) > 0:
        output = cmd + output
    if sys.version_info < (3, ):
        output = output.encode('utf-8')
    if input_method == "keybinding":
        w.buffer_set(buffer, "input", output)
    else:
        w.command(buffer, output)
    return w.WEECHAT_RC_OK
