# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Hairo R. Carela <hairocr8@gmail.com>
#
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
# DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
# TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
# 0. You just DO WHAT THE FUCK YOU WANT TO.
#
# Alternate way of text formatting, useful for relays without text formatting
# features (Glowingbear, WeechatAndroid, etc)
#
# Usage:
# /aformat *text* for bold text
# /aformat /text/ for italic text
# /aformat _text_ for underlined text
# /aformat |text| for reversed (black on white) text
#
# History:
#   2016-09-24:
#       v0.1: Initial release
#
# TODO:
# - Colors support

import sys

try:
    import weechat
    from weechat import WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

SCRIPT_NAME = "aformat"
SCRIPT_AUTHOR = "Hairo R. Carela <hairocr8@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "WTFPL"
SCRIPT_DESC = ("Alternate way of text formatting, see /help for instructions")

PY3 = sys.version > '3'

class format:
    # Special byte sequences, using weechat.color("stuff") had some unwanted
    # results, i'll look into it if needed. Colors are unused for now
   # PURPLE = '\x0306'
   # BLUE = '\x0302'
   # GREEN = '\x0303'
   # YELLOW = '\x0308'
   # RED = '\x0304'
   BOLD = '\x02'
   ITALIC = '\x1D'
   UNDERLINE = '\x1F'
   REVERSE = '\x16'
   END = '\x0F'

if PY3:
    unichr = chr
    def send(buf, text):
        weechat.command(buf, "/input send {}".format(text))
else:
    def send(buf, text):
        weechat.command(buf, "/input send {}".format(text.encode("utf-8")))

def cb_aformat_cmd(data, buf, args):
    if not PY3:
        args = args.decode("utf-8")

    # Get the indexes of the separators (*/_|) in the string
    bolds = [i for i, ltr in enumerate(args) if ltr == "*"]
    italics = [i for i, ltr in enumerate(args) if ltr == "/"]
    underlines = [i for i, ltr in enumerate(args) if ltr == "_"]
    reverses = [i for i, ltr in enumerate(args) if ltr == "|"]

    if len(bolds) != 0:
        for i, v in enumerate(bolds):
            if i%2 == 0:
                args = args[:v] + format.BOLD + args[v+1:]
            else:
                args = args[:v] + format.END + args[v+1:]

    if len(italics) != 0:
        for i, v in enumerate(italics):
            if i%2 == 0:
                args = args[:v] + format.ITALIC + args[v+1:]
            else:
                args = args[:v] + format.END + args[v+1:]

    if len(underlines) != 0:
        for i, v in enumerate(underlines):
            if i%2 == 0:
                args = args[:v] + format.UNDERLINE + args[v+1:]
            else:
                args = args[:v] + format.END + args[v+1:]

    if len(reverses) != 0:
        for i, v in enumerate(reverses):
            if i%2 == 0:
                args = args[:v] + format.REVERSE + args[v+1:]
            else:
                args = args[:v] + format.END + args[v+1:]

    send(buf, args)
    return weechat.WEECHAT_RC_OK


if import_ok and __name__ == "__main__":
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                     SCRIPT_LICENSE, SCRIPT_DESC, '', '')
    weechat.hook_command("aformat", "Alternate way of text formatting, useful for relays without text formatting features (Glowingbear, WeechatAndroid, etc)",
                         "text <*/_|> text <*/_|> more text",
                         "    *: bold text\n"
                         "    /: italic text\n"
                         "    _: underlined text\n"
                         "    |: reversed (black on white) text\n\n"
                         "    eg.: typing: /aformat This /must/ be the *work* of an _enemy_ |stand|\n"
                         "    will output: This {0}must{4} be the {1}work{4} of an {2}enemy{4} {3}stand{4}".format(weechat.color("italic"), weechat.color("bold"), weechat.color("underline"), weechat.color("reverse"), weechat.color("reset")),
                         "", "cb_aformat_cmd", "")
