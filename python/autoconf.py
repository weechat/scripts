# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Manu Koell <manu@koell.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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
# 2017-11-03: fix script/issue #236
#       v0.2: add "%h" variable in option 'file'
# 2018-10-23: fix script/issue #297
#       v0.3: make script python 3 compatible

from __future__ import print_function

import os
import re

from fnmatch import fnmatch

try:
    import weechat as w

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

NAME        = "autoconf"
AUTHOR      = "Manu Koell <manu@koell.li>"
VERSION     = "0.3"
LICENSE     = "GPL3"
DESCRIPTION = "auto save/load changed options in a ~/.weerc file, useful to share dotfiles with"

EXCLUDES = [
    '*.nicks',
    '*.username', '*.sasl_username',
    '*.password', '*.sasl_password',
    'irc.server.*.autoconnect',
    'irc.server.*.autojoin'
]

SETTINGS = {
    'autosave': ('on', 'auto save config on quit'),
    'autoload': ('on', 'auto load config on start'),
    'ignore': (
        ','.join(EXCLUDES),
        'comma separated list of patterns to exclude'),
    'file': ('%h/.weerc', 'config file location ("%h" will be replaced by WeeChat home, "~/.weechat" by default)')
}

def cstrip(text):
    """strip color codes"""

    return w.string_remove_color(text, '')

def get_config(args):
    """get path to config file"""

    try:
        conf = args[1]
    except Exception:
        conf = w.config_get_plugin('file').replace("%h",w.info_get("weechat_dir", ""))
    return os.path.expanduser(conf)

def load_conf(args):
    """send config to fifo pipe"""

    fifo = w.info_get('fifo_filename', '')
    conf = get_config(args)

    if os.path.isfile(conf):
        w.command('', '/exec -sh -norc cat | grep */set %s > %s' % (conf, fifo))

def save_conf(args):
    """match options and save to config file"""

    try:
        f = open(get_config(args), 'w+')

    except Exception as e:
        w.prnt('', '%sError: %s' % (w.prefix('error'), e))

        return w.WEECHAT_RC_ERROR

    header = [
        '#',
        '# WeeChat %s (compiled on %s)' % (w.info_get('version', ''), w.info_get('date', '')),
        '#',
        '# Use /autoconf load or cat this file to the FIFO pipe.',
        '#',
        '# For more info, see https://weechat.org/scripts/source/autoconf.py.html',
        '#',
        ''
    ]

    for ln in header:
        f.write('%s\n' % ln)

    w.command('', '/buffer clear')
    w.command('', '/set diff')

    infolist = w.infolist_get('buffer_lines', '', '')

    while w.infolist_next(infolist):
        message = cstrip(w.infolist_string(infolist, 'message'))
        ignore = w.config_get_plugin('ignore').split(',')
        option = re.match(RE['option'], message)

        if option:
            if not any(fnmatch(option.group(1), p.strip()) for p in ignore):
                f.write('*/set %s %s\n' % (option.group(1), option.group(2)))

    f.close()

    w.infolist_free(infolist)

def autoconf_cb(data, buffer, args):
    """the /autoconf command"""

    args = args.split()

    if 'save' in args:
        save_conf(args)

    elif 'load' in args:
        load_conf(args)

    else:
        # show help message
        w.command('', '/help ' + NAME)

    return w.WEECHAT_RC_OK

def quit_cb(data, signal, signal_data):
    """save config on quit"""

    save_conf(None)

    return w.WEECHAT_RC_OK

if __name__ == '__main__':
    if w.register(NAME, AUTHOR, VERSION, LICENSE, DESCRIPTION, "", ""):
        w.hook_command(NAME, DESCRIPTION, 'save [path] || load [path]', '', 'save || load', 'autoconf_cb', '')
        default_txt = w.gettext("default: ")            # check if string is translated
        RE = {
            'option': re.compile('\s*(.*) = (.*)  \(%s' % default_txt)
        }

        # set default config
        for option, value in SETTINGS.items():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, value[0])
                w.config_set_desc_plugin(option, '%s  (default: "%s")' % (value[1], value[0]))

        if 'on' in w.config_get_plugin('autoload'):
            load_conf(None)

        if 'on' in w.config_get_plugin('autosave'):
            w.hook_signal('quit', 'quit_cb', '')
