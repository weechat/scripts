#
# Copyright (C) 2010 by Guido Berhoerster <guido+weechat@berhoerster.name>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import re
import string
from collections import Mapping
import weechat

SCRIPT_NAME = 'terminal-title'
VERSION = '1'
AUTHOR = 'Guido Berhoerster'
DESCRIPTION = 'Displays user defined information in the terminal title'
DEFAULT_SETTINGS = {
    'title': ('WeeChat %version [%buffer_count] %buffer_number: '
            '%buffer_name{%buffer_nicklist_count} [%hotlist]',
            'items displayed in the terminal title')
}
TERM_TEMPLATES = [
    ('xterm', "\033]0;%s\007"),
    ('screen', "\033_%s\033\\")
]
TERM_TEMPLATE = None


class TermTitleMapping(Mapping):
    substitutions = {
        'buffer_title':
                lambda : weechat.buffer_get_string(weechat.current_buffer(),
                "title"),
        'buffer_name':
                lambda : weechat.buffer_get_string(weechat.current_buffer(),
                "name"),
        'buffer_plugin':
                lambda : weechat.buffer_get_string(weechat.current_buffer(),
                "plugin"),
        'buffer_number':
                lambda : weechat.buffer_get_integer(weechat.current_buffer(),
                "number"),
        'buffer_nicklist_count':
                lambda : weechat.buffer_get_integer(weechat.current_buffer(),
                "nicklist_visible_count"),
        'buffer_count': lambda : buffer_count(),
        'hotlist': lambda : hotlist(),
        'version': lambda : weechat.info_get("version", "")
    }

    def __getitem__(self, key):
        return self.substitutions[key]()

    def __iter__(self):
        return self.substitutions.iterkeys()

    def __len__(self):
        return len(self.substitutions)


class TermTitleTemplate(string.Template):
    delimiter = '%'


def buffer_count():
    buffer_count = 0
    buffer = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(buffer):
        buffer_count += 1
    weechat.infolist_free(buffer)
    return buffer_count

def hotlist():
    hotlist_items = []
    hotlist = weechat.infolist_get("hotlist", "", "")
    while weechat.infolist_next(hotlist):
        buffer_number = weechat.infolist_integer(hotlist, "buffer_number")
        buffer = weechat.infolist_pointer(hotlist, "buffer_pointer")
        short_name = weechat.buffer_get_string(buffer, "short_name")
        hotlist_items.append("%s:%s" % (buffer_number, short_name))
    weechat.infolist_free(hotlist)
    return ",".join(hotlist_items)

def set_term_title_hook(data, signal, signal_data):
    title_template_str = weechat.config_get_plugin('title')
    title_template = TermTitleTemplate(title_template_str)
    title_str = title_template.safe_substitute(TermTitleMapping())
    sys.__stdout__.write(TERM_TEMPLATE % title_str)
    sys.__stdout__.flush()

    return weechat.WEECHAT_RC_OK

def config_hook(data, option, value):
    set_term_title_hook("", "", "")

    return weechat.WEECHAT_RC_OK

if __name__ == '__main__':
    weechat.register(SCRIPT_NAME, AUTHOR, VERSION, 'GPL3', DESCRIPTION, '', '')

    for option, (value, description) in DEFAULT_SETTINGS.iteritems():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' %
                (description, value))

    term = os.environ.get("TERM", None)
    if term:
        for term_name, term_template in TERM_TEMPLATES:
            if term.startswith(term_name):
                TERM_TEMPLATE = term_template
                for hook in ['buffer_switch', 'buffer_title_changed',
                        'hotlist_changed', 'upgrade_ended']:
                    weechat.hook_signal(hook, 'set_term_title_hook', '')
                weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                        'config_hook', '')
                set_term_title_hook('', '', '')
                break
