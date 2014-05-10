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
# This script generates a file containing a formatted list of highlights to be
# used by an external program like conky.
#
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#        0.2: change hook_print callback argument type of displayed/highlight
#             (WeeChat >= 1.0)
# 2012-03-07: nesthib <nesthib@gmail.com>
#        0.1: initial release

try:
    import weechat as w
except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

import re, os
from collections import Counter

name = "hl2file"
author = "nesthib <nesthib@gmail.com>"
version = "0.2"
license = "GPL"
description = "Generates a file with highlights for external programs like conky"
shutdown_function = "shutdown"
charset = ""

w.register(name, author, version, license, description, shutdown_function, charset)

settings = {
        'output_file': '%h/highlights.txt',
        'output_active_buffer': '%h/active_buffer.txt',
        #'ignore_chans': 'server',
        'output_format': '%{buffer}: %{nick} (%{message})',
        'summarize_by_buffer': 'off',
        'short_buffer_names': 'on',
        'clear_visited_buffers': 'on',
        }

for opt, val in settings.iteritems():
    if not w.config_is_set_plugin(opt):
        w.config_set_plugin(opt, val)

highlights = []
regex_tags = re.compile('%\{[^\{\}]+\}')

def bufname(buffer):
    buffer_name = w.buffer_get_string(buffer , 'name')
    if w.config_get_plugin('short_buffer_names') == 'on':
        buffer_name = buffer_name.partition('.')[2]
    return buffer_name

def write(my_file, content):
    if my_file == "":
        return
    my_file = os.path.expanduser(my_file.replace("%h", w.info_get("weechat_dir", "")))
    try:
        f = open(my_file, 'w')
    except IOError:
        w.prnt('', 'Error: %s is unable to open "%s", please select an appropriate location' % (name, my_file))
    else:
        f.writelines(content)
        f.close()

def my_print_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    global highlights
    if w.config_get_plugin('clear_visited_buffers') == 'on':
        if buffer == w.window_get_pointer(w.current_window(), 'buffer'):
            return w.WEECHAT_RC_OK
    if int(highlight):
        infos = {'buffer'   : buffer,
                 'date'     : date,
                 'tags'     : str.split(tags, ','),
                 'nick'   : prefix,
                 'message'  : message,
                 }
        highlights.append(infos)
        write_file()
    return w.WEECHAT_RC_OK

def write_file():
    global highlights
    filename = w.config_get_plugin('output_file')
    if w.config_get_plugin('summarize_by_buffer') == 'on':
        items = Counter([ bufname(item['buffer']) for item in highlights ])
        output_lines = [ '%s (%s)\n' % (item, items[item]) for item in items ]
    else:
        output_regex = w.config_get_plugin('output_format')
        tags = regex_tags.findall(output_regex)
        output_lines = []
        for infos in highlights:
            output_string = output_regex+'\n'
            for tag in tags:
                item = tag.lstrip('%{').rstrip('}')
                if item in infos.keys():
                    if item == 'buffer':
                        new_string = bufname(infos[item])
                    else:
                        new_string = infos[item]
                    output_string = output_string.replace(tag, new_string)
            output_lines.append(output_string)
    write(filename, output_lines)

def clear_file_cb(data, buffer, args):
    global highlights
    highlights = []
    write_file()
    return w.WEECHAT_RC_OK

def buffer_switch_cb(data, signal, signal_data):
    global highlights
    if w.config_get_plugin('clear_visited_buffers') == 'on':
        buffer = w.window_get_pointer(w.current_window(), 'buffer')
        write(w.config_get_plugin('output_active_buffer'), bufname(buffer))
        highlights = [ item for item in highlights if item['buffer'] != buffer ]
        write_file()
    return w.WEECHAT_RC_OK

def shutdown():
    for my_file in ['output_file', 'output_active_buffer']:
        filename = w.config_get_plugin(my_file).replace("%h", w.info_get("weechat_dir", ""))
        if os.path.exists(filename):
            os.remove(filename)
    return w.WEECHAT_RC_OK

### OPTIONS ###

invertdict = lambda d: dict(zip(d.itervalues(), d.keys()))
booleans = {'on': True, 'off': False}
boolean_options = ['summarize_by_buffer', 'short_buffer_name', 'clear_visited_buffers']

options = {}
for option in settings.keys():
    if option in boolean_options :
        options[option] = booleans[w.config_get_plugin(option)]
    else:
        options[option] = w.config_get_plugin(option)

def my_config_cb(data, option, value):
    global options

    for boolean_option in boolean_options :
        if option.endswith(boolean_option):
            if value in booleans.keys():
                options[boolean_option] = booleans[w.config_get_plugin(boolean_option)]
            else:
                w.prnt('', 'Error: "%s" is not a boolean, please use "on" or "off"' % w.config_get_plugin(boolean_option))
                w.config_set_plugin(boolean_option, invertdict(booleans)[options[boolean_option]])
    write_file()
    return w.WEECHAT_RC_OK

for option in settings.keys():
    w.hook_config("plugins.var.python.%s.%s" % (name, option), "my_config_cb", "")

###  HOOKS  ###

w.hook_command("hl2file_clear", "", "", "", "", "clear_file_cb", "")
w.hook_signal("buffer_switch","buffer_switch_cb","")
w.hook_signal("window_switch","buffer_switch_cb","")
w.hook_print("", "", "", 1, "my_print_cb", "")
