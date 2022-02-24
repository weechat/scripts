# -*- coding: utf-8 -*-
#
# Script Name: aesthetic.py
# Script Author: Wojciech Siewierski
# Script License: GPL3
# Contact: vifon @ irc.freenode.net

SCRIPT_NAME = 'aesthetic'
SCRIPT_AUTHOR = 'Wojciech Siewierski'
SCRIPT_VERSION = '1.0.6'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Make messages more A E S T H E T I C A L L Y pleasing.'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat')
    print('You can obtain a copy of WeeChat, for free, at https://weechat.org')
    import_ok = False

weechat_version = 0

import shlex
import sys

def aesthetic_(args):
    for arg in args:
        try:
            arg = arg.decode('utf8')
        except AttributeError:
            pass
        yield " ".join(arg.upper())
        for n, char in enumerate(arg[1:]):
            yield " ".join(" "*(n+1)).join(char.upper()*2)

def aesthetic(args):
    if sys.version_info < (3,):
        return (x.encode('utf8') for x in aesthetic_(args))
    else:
        return aesthetic_(args)

def aesthetic_cb(data, buffer, args):
    for x in aesthetic(shlex.split(args)):
        weechat.command(buffer, x)
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat_version = weechat.info_get("version_number", "") or 0
        weechat.hook_command(
            "aesthetic",
            """Format a message like this:

E X A M P L E
X X
A   A
M     M
P       P
L         L
E           E

Each argument is formatted separately, use sh-like quotes for grouping.  For example '/aesthetic foo bar' will send two such blocks while '/aesthetic "foo bar"' would send one larger one.

Use with care to not cause undesirable message spam.""",
            "message", "",
            "",
            "aesthetic_cb", ""
        )
