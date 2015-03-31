# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2014 Germain Z. <germanosz@gmail.com>
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
# Convert text to its ｆｕｌｌｗｉｄｔｈ equivalent and send it to buffer.
#


import sys
import weechat


SCRIPT_NAME = "fullwidth"
SCRIPT_AUTHOR = "GermainZ <germanosz@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = ("Convert text to its ｆｕｌｌｗｉｄｔｈ equivalent and send it "
               "to buffer.")

PY3 = sys.version > '3'


if PY3:
    unichr = chr
    def send(buf, text):
        weechat.command(buf, "/input send {}".format(text))
else:
    def send(buf, text):
        weechat.command(buf, "/input send {}".format(text.encode("utf-8")))

def cb_fullwidth_cmd(data, buf, args):
    """Callback for ``/fullwidth``, convert and send the given text."""
    chars = []
    if not PY3:
        args = args.decode("utf-8")
    for char in list(args):
        ord_char = ord(char)
        if ord_char >= 32 and ord_char <= 126:
            char = unichr(ord_char + 65248)
        chars.append(char)
    send(buf, ''.join(chars))
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__":
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                     SCRIPT_LICENSE, SCRIPT_DESC, '', '')
    weechat.hook_command("fullwidth", SCRIPT_DESC, "<text>", '', '',
                         "cb_fullwidth_cmd", '')
