# Copyright (c) 2010-2012 by fauno <fauno@kiwwwi.com.ar>
#
# Bar item showing typing count. Add 'tc' to a bar.
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
# 0.1:  initial release
# 0.2 <nils_2@freenode>:
#       fixed display bug when buffer changes
#       added cursor position
#       colour of number changes if a specified number of chars is reached
#       added reverse counting
# 0.2.2 <nils_2@freenode>:
#       update settings instantly when changed
#       fix display bug when loading the script first time
# 0.2.3 <nils_2@freenode>:
#       fix display bug with count_over. Wasn't set to 0
# 0.3 <nils_2@freenode>:
#       added sound-alarm when cursor position is -1 or higher than 'max_chars'
#       improved option-handling
#
# Note: As of version 0.2 this script requires a version of weechat
#       from git 2010-01-25 or newer, or at least 0.3.2 stable.
#
# usage:
# add [tc] to your weechat.bar.status.items
#
# config:
# %P = cursor position
# %L = input lenght
# %R = reverse counting from max_chars
# %C = displays how many chars are count over max_chars
# /set plugins.var.python.typing_counter.format "[%P|%L|<%R|%C>]"
#
# color for warn after specified number of chars
# /set plugins.var.python.typing_counter.warn_colour "red"
#
# turns indicator to "warn_colour" when position is reached
# /set plugins.var.python.typing_counter.warn "150"
#
# max number of chars to count reverse
# /set plugins.var.python.typing_counter.max_chars "200"
#
# to activate a display beep use.
# /set plugins.var.python.typing_counter.warn_command "$bell"
#
## TODO:
# - buffer whitelist/blacklist
# - max chars per buffer (ie, bar item will turn red when count > 140 for identica buffer)

SCRIPT_NAME    = "typing_counter"
SCRIPT_AUTHOR  = "fauno <fauno@kiwwwi.com.ar>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item showing typing count and cursor position. Add 'tc' to a bar."

try:
  import weechat as w

except Exception:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()
try:
    import os, sys

except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

tc_input_text   = ''
length          = 0
cursor_pos      = 1
count_over      = '0'

tc_default_options = {
    'format'            : '[%P|%L|<%R|%C>]',
    'warn'              : '140',
    'warn_colour'       : 'red',
    'max_chars'         : '200',
    'warn_command'      : '',
}
tc_options = {}

def command_run_cb (data, signal, signal_data):
    if tc_options['warn_command'] == '':
        return w.WEECHAT_RC_OK
    global length, cursor_pos, tc_input_text
    current_buffer = w.current_buffer()
    cursor_pos = w.buffer_get_integer(current_buffer,'input_pos') + 1
    if (cursor_pos -1) == 0:
        tc_action_cb()
    return w.WEECHAT_RC_OK

def tc_bar_item_update (data=None, signal=None, signal_data=None):
    '''Updates bar item'''
    '''May be used as a callback or standalone call.'''
    global length, cursor_pos, tc_input_text

    current_buffer = w.current_buffer()
    length = w.buffer_get_integer(current_buffer,'input_length')
    cursor_pos = w.buffer_get_integer(current_buffer,'input_pos') + 1
    w.bar_item_update('tc')
    return w.WEECHAT_RC_OK

def tc_bar_item (data, item, window):
    '''Item constructor'''
    global length, cursor_pos, tc_input_text, count_over,tc_options
    count_over = '0'

    # reverse check for max_chars
    reverse_chars = (int(tc_options['max_chars']) - length)
#    reverse_chars = (int(max_chars) - length)
    if reverse_chars == 0:
        reverse_chars = "%s" % ("0")
    else:
        if reverse_chars < 0:
            count_over = "%s%s%s" % (w.color(tc_options['warn_colour']),str(reverse_chars*-1), w.color('default'))
            reverse_chars = "%s" % ("0")
            tc_action_cb()
        else:
            reverse_chars = str(reverse_chars)
    out_format = tc_options['format']
    if length >= int(tc_options['warn']):
        length_warn = "%s%s%s" % (w.color(tc_options['warn_colour']), str(length), w.color('default'))
        out_format = out_format.replace('%L', length_warn)
    else:
        out_format = out_format.replace('%L', str(length))

    out_format = out_format.replace('%P', str(cursor_pos))
    out_format = out_format.replace('%R', reverse_chars)
    out_format = out_format.replace('%C', count_over)
    tc_input_text = out_format

    return tc_input_text

def init_config():
    global tc_default_options, tc_options
    for option, default_value in tc_default_options.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
        tc_options[option] = w.config_get_plugin(option)

def config_changed(data, option, value):
    init_config()
    return w.WEECHAT_RC_OK

def tc_action_cb():
    global tc_options
    if tc_options['warn_command']:
        if tc_options['warn_command'] == '$bell':
            f = open('/dev/tty', 'w')
            f.write('\a')
            f.close()
        else:
            os.system(tc_options['warn_command'])
    return w.WEECHAT_RC_OK

if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                  SCRIPT_LICENSE, SCRIPT_DESC,
                  "", ""):
        init_config() # read configuration
        tc_bar_item_update() # update status bar display

        w.hook_signal('input_text_changed', 'tc_bar_item_update', '')
        w.hook_signal('input_text_cursor_moved','tc_bar_item_update','')
        w.hook_command_run('/input move_previous_char','command_run_cb','')
        w.hook_command_run('/input delete_previous_char','command_run_cb','')
        w.hook_signal('buffer_switch','tc_bar_item_update','')
        w.hook_config('plugins.var.python.' + SCRIPT_NAME + ".*", "config_changed", "")
        w.bar_item_new('tc', 'tc_bar_item', '')
