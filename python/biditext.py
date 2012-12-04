# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 by Oscar Morante <oscar@morante.eu>
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

# This script uses fribidi library to display rtl text properly

import weechat
from pyfribidi import *

SCRIPT_NAME    = "biditext"
SCRIPT_AUTHOR  = "Oscar Morante <oscar@morante.eu>"
SCRIPT_VERSION = "1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Use fribidi to handle RTL text"


def biditext_cb(data, modifier, modifier_data, line):
    return log2vis(line, LTR)


if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME,
                        SCRIPT_AUTHOR,
                        SCRIPT_VERSION,
                        SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        weechat.hook_modifier('weechat_print', 'biditext_cb', '')

