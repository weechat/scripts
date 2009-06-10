''' Buffer saver '''
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <tor@bash.no>
#  Based on bufsave.pl for 0.2.x by FlashCode
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
# Set screen title
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-10, xt <tor@bash.no>
#     version 0.1: initial release
#
import weechat as w
from os.path import exists

SCRIPT_NAME    = "bufsave"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Save buffer to a file"
SCRIPT_COMMAND  = SCRIPT_NAME


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    w.hook_command(SCRIPT_COMMAND,
            "save current buffer to a file",
            "[filename]",
            "  filename: target file (must not exist)\n",
            "%f",
            "bufsave_cmd",
            '')

def cstrip(text):
    ''' Use weechat color strip on text'''

    return w.string_remove_color(text, '')

def bufsave_cmd(data, buffer, args):
    ''' Callback for /bufsave command '''

    filename = args

    if not filename:
        w.command('', '/help %s' %SCRIPT_COMMAND)
        return w.WEECHAT_RC_OK

    if exists(filename):
        w.prnt('', "Error: target file already exists!")
        return w.WEECHAT_RC_OK
        
    infolist = w.infolist_get('buffer_lines', buffer, '')
    channel =  w.buffer_get_string(buffer, 'name')
    try:
        fp = file(filename, 'w')
    except:
        w.prnt('', "Error writing to target file!")
        return w.WEECHAT_RC_OK

    while w.infolist_next(infolist):
        fp.write('%s %s %s\n' %(\
                w.infolist_time(infolist, 'date'),
                cstrip(w.infolist_string(infolist, 'prefix')),
                cstrip(w.infolist_string(infolist, 'message')),
                ))

    w.infolist_free(infolist)

    return w.WEECHAT_RC_OK
