# coding: utf-8
#
# Copyright (c) 2012 by nesthib <nesthib@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# This script checks every message before it is sent and blocks messages which
# correspond to misformatted commands (e.g. " /msg NickServ…") to avoid the
# unfortunate discosure of personnal informations.
#
# 2012-03-07: nesthib <nesthib@gmail.com>
#        0.1: initial release

try:
    import weechat as w
except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

import re

name = "unwanted_msg"
author = "nesthib <nesthib@gmail.com>"
version = "0.1"
license = "GPL"
description = "Avoid sending misformatted commands as messages"
shutdown_function = ""
charset = ""

w.register(name, author, version, license, description, shutdown_function, charset)

settings = {
        'regexp'        : ' +/',     # if the pattern matches the beginning of the line, the message will be blocked
        'warning_buffer': 'current', # if set to current/server/weechat will print warning on current/server/weechat buffer. Disable warning if unset
        }
for opt, val in settings.iteritems():
    if not w.config_is_set_plugin(opt):
        w.config_set_plugin(opt, val)

def my_modifier_cb(data, modifier, modifier_data, string):
    if unwanted_pattern.match(string):
        if options['warning_buffer'] == 'current':
            output = w.current_buffer()
        elif options['warning_buffer'] == 'server':
            server = w.buffer_get_string(w.current_buffer(), 'localvar_server')
            plugin = w.buffer_get_string(w.current_buffer(), 'plugin')
            output = w.buffer_search(plugin, 'server.'+server)
        elif options['warning_buffer'] == '':
            output = None
        else:
            output = '' # if invalid option set to weechat buffer
        if not output == None:
            w.prnt_date_tags(output, 0, 'no_log', '%sunwanted message deleted: "%s"' % (w.prefix('error'), string))
        w.buffer_set(w.current_buffer(), 'input', string)
        return ''
    else:
        return string

options = {}
for option in settings.keys():
    options[option] = w.config_get_plugin(option)
unwanted_pattern = re.compile(options['regexp'])

def my_config_cb(data, option, value):
    global options, unwanted_pattern
    for option in settings.keys():
        options[option] = w.config_get_plugin(option)
    unwanted_pattern = re.compile(options['regexp'])
    return w.WEECHAT_RC_OK

for option in settings.keys():
    w.hook_config("plugins.var.python.%s.%s" % (name, option), "my_config_cb", "")

w.hook_modifier('input_text_for_buffer', 'my_modifier_cb', '')
