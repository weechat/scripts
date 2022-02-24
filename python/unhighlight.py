#
# Copyright (C) 2016 Andrew Rodgers-Schatz <me@andrew.rs>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

try:
    import weechat
except Exception:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://weechat.org/')
    import_ok = False

import time
import re

SCRIPT_NAME     = 'unhighlight'
SCRIPT_AUTHOR   = 'xiagu'
SCRIPT_VERSION  = '0.1.3'
SCRIPT_LICENSE  = 'GPL3'
SCRIPT_DESC     = 'Allows per-buffer specification of a regex that prevents highlights.'


def matches_unhighlight_strings(msg, regex):
    return weechat.string_has_highlight_regex(msg, regex)


def unhighlight_cb(data, modifier, modifier_data, message):
    """Check if the line matches the unhighlight regular expression, and if it does, clear the message and reprint it with the no_highlight tag added."""

    if modifier_data.startswith('0x'):
        # WeeChat >= 2.9
        buffer, tags = modifier_data.split(';', 1)
    else:
        # WeeChat <= 2.8
        plugin, buffer_name, tags = modifier_data.split(';', 2)
        buffer = weechat.buffer_search(plugin, buffer_name)

    if 'no_highlight' in tags or 'notify_none' in tags:
        return message

    unhighlight_regex = weechat.buffer_get_string(buffer, 'localvar_unhighlight_regex')
    if not matches_unhighlight_strings(message, unhighlight_regex):
        return message

    # inspired by https://weechat.org/scripts/source/mass_hl_blocker.pl.html/
    # this is terrible and gross but afaik there is no way to change the
    # highlight message once it's set and no way to interact with a message's
    # tags before highlights are checked.
    weechat.prnt_date_tags(buffer, 0, "%s,no_highlight" % tags, message)
    return ''


def command_cb(data, buffer, args):
    args = args.strip().lower().split(' ')

    if args[0] == 'list':
        weechat.command('', '/set *.localvar_set_unhighlight_regex')
    else:
        weechat.command('', '/help %s' % SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK


def main():
    hook = weechat.hook_modifier('weechat_print', 'unhighlight_cb', '')

    description = """
{script_name} lets you set up a regex for things to never highlight.

To use this, set the localvar 'unhighlight_regex' on a buffer. Lines in
that buffer which match will never be highlighted, even if they have
your nick or match highlight_words or highlight_regex.

You will need the script 'buffer_autoset.py' installed to make local
variables persistent; see the examples below.

Examples:
 Temporarily block highlights in the current buffer for lines matching 'banana':
   /buffer set localvar_set_unhighlight_regex banana
 Unhighlight SASL authentication messages for double logins:
   /buffer weechat
   /buffer set localvar_set_unhighlight_regex SaslServ
   /buffer_autoset add core.weechat localvar_set_unhighlight_regex SaslServ
 List buffers with autoset unhighlights:
   /{script_name} list
 Show this help:
   /{script_name}
 Display local variables for current buffer:
   /buffer localvar
""".format(script_name = SCRIPT_NAME)

    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'list', description, 'list %-', 'command_cb', '')


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    main()
