# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <tor@bash.no>
# Copyright (c) 2012-2021 by Sebastien Helleu <flashcode@flashtux.org>
# Based on bufsave.pl for 0.2.x by FlashCode
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
# Save content of current buffer in a file.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2021-05-02, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.5: add compatibility with WeeChat >= 3.2 (XDG directories)
# 2017-12-02, Benjamin Roberts <benjamin@bgroberts.id.au>:
#     version 0.4: added support for home path expansion
# 2012-08-28, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.3: compatibility with WeeChat >= 0.3.9 (hdata_time is now long
#                  instead of string)
# 2012-08-23, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.2: use hdata for WeeChat >= 0.3.6 (improve performance)
# 2009-06-10, xt <tor@bash.no>
#     version 0.1: initial release
#

"""Buffer saver."""

import weechat as w
from os.path import exists
import time

SCRIPT_NAME = "bufsave"
SCRIPT_AUTHOR = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Save buffer to a file"
SCRIPT_COMMAND = SCRIPT_NAME


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
              SCRIPT_DESC, "", ""):
    w.hook_command(
        SCRIPT_COMMAND,
        "save current buffer to a file",
        "[filename]",
        "  filename: target file (must not exist)\n",
        "%f",
        "bufsave_cmd",
        '',
    )


def cstrip(text):
    """Use weechat color strip on text."""
    return w.string_remove_color(text, '')


def bufsave_cmd(data, buffer, args):
    """Callback for /bufsave command."""

    filename_raw = args

    if not filename_raw:
        w.command('', '/help %s' % SCRIPT_COMMAND)
        return w.WEECHAT_RC_OK

    options = {
        'directory': 'data',
    }
    filename = w.string_eval_path_home(filename_raw, {}, {}, options)

    if exists(filename):
        w.prnt('', 'Error: target file already exists!')
        return w.WEECHAT_RC_OK

    try:
        fp = open(filename, 'w')
    except Exception:
        w.prnt('', 'Error writing to target file!')
        return w.WEECHAT_RC_OK

    version = w.info_get('version_number', '') or 0
    if int(version) >= 0x00030600:
        # use hdata with WeeChat >= 0.3.6 (direct access to data, very fast)
        own_lines = w.hdata_pointer(w.hdata_get('buffer'), buffer, 'own_lines')
        if own_lines:
            line = w.hdata_pointer(w.hdata_get('lines'),
                                   own_lines, 'first_line')
            hdata_line = w.hdata_get('line')
            hdata_line_data = w.hdata_get('line_data')
            while line:
                data = w.hdata_pointer(hdata_line, line, 'data')
                if data:
                    date = w.hdata_time(hdata_line_data, data, 'date')
                    # since WeeChat 0.3.9, hdata_time returns long instead of
                    # string
                    if not isinstance(date, str):
                        date = time.strftime('%F %T',
                                             time.localtime(int(date)))
                    fp.write('%s %s %s\n' % (
                        date,
                        cstrip(w.hdata_string(hdata_line_data,
                                              data, 'prefix')),
                        cstrip(w.hdata_string(hdata_line_data,
                                              data, 'message')),
                    ))
                line = w.hdata_move(hdata_line, line, 1)
    else:
        # use infolist with WeeChat <= 0.3.5 (full duplication of lines,
        # slow and uses memory)
        infolist = w.infolist_get('buffer_lines', buffer, '')
        while w.infolist_next(infolist):
            fp.write('%s %s %s\n' % (
                w.infolist_time(infolist, 'date'),
                cstrip(w.infolist_string(infolist, 'prefix')),
                cstrip(w.infolist_string(infolist, 'message')),
            ))
        w.infolist_free(infolist)

    fp.close()

    return w.WEECHAT_RC_OK
