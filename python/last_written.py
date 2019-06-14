# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 by nils_2 <weechatter@arcor.de>
#
# last written: provide item to keep track of last buffer you wrote something
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
# 2019-06-02: nils_2, (freenode.#weechat)
#       0.1 : initial release

try:
    import weechat,re

except Exception:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://www.weechat.org/')
    quit()

SCRIPT_NAME     = 'last_written'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.1'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'keep track of last buffer you wrote something'

item_last_written = 'last_written'
item_last_sent = 'last_sent'
last_written = ''
last_sent = ''
# ==============================[ callback ]=============================
# signal_data = buffer_ptr
def input_text_changed_cb(data, signal, signal_data):
    global last_written
    buffer_name = weechat.buffer_get_string(signal_data, 'name')
    if last_written == buffer_name:
        return weechat.WEECHAT_RC_OK
    last_written = buffer_name
    update_item_cb(data,signal,signal_data,'last_written')
    return weechat.WEECHAT_RC_OK

# signal = buffer_ptr
def input_return_cb(data, signal, signal_data):
    global last_sent
    buffer_name = weechat.buffer_get_string(signal, 'name')
    if last_sent == buffer_name:
        return weechat.WEECHAT_RC_OK
    last_sent = buffer_name
    update_item_cb(data,signal,signal_data,'last_sent')
    return weechat.WEECHAT_RC_OK
# ================================[ item ]===============================
def bar_item_last_written_cb(data, item, window):
    global last_written
    # check for root input bar!
    if not window:
        window = weechat.current_window()

    # get current buffer (for example for split windows!)
    ptr_buffer = weechat.window_get_pointer(window,'buffer')
    if ptr_buffer == '':
        return ''
    return last_written

def bar_item_last_sent_cb(data, item, window):
    global last_written
    # check for root input bar!
    if not window:
        window = weechat.current_window()

    # get current buffer (for example for split windows!)
    ptr_buffer = weechat.window_get_pointer(window,'buffer')
    if ptr_buffer == '':
        return ''
    return last_sent

def update_item_cb(data, signal, signal_data,item_name):
    weechat.bar_item_update(item_name)
    return weechat.WEECHAT_RC_OK

def last_written_info_cb(data, info_name, arguments):
    global last_written
    return last_written

def last_sent_info_cb(data, info_name, arguments):
    global last_sent
    return last_sent

# ================================[ main ]===============================
if __name__ == '__main__':
    global version
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'last_written||last_sent',
                            'script provide two items:\n'
                            '"last_written", will print name of buffer you typed text last time\n'
                            '"last_sent", will print name of buffer you sent text last time\n\n'
                            'You can use both items with /eval or in /key using variable "${info:last_written}" and "${info:last_sent}"\n\n'
                            'Example:\n'
                            'bind key to jump to last buffer you sent text\n'
                            ' /key bind meta-# /eval /buffer ${info:last_sent}\n'
                            'creates an item for text_item.py script (item name ""ti_last_written"\n'
                            ' /set plugins.var.python.text_item.ti_last_written "all|input_text_changed ${info:last_written} ${info:last_sent}"'
                            '',
                            '','','')

        weechat.bar_item_new(item_last_written, 'bar_item_last_written_cb','')
        weechat.bar_item_new(item_last_sent, 'bar_item_last_sent_cb','')
        weechat.hook_info('last_written',
                      'Return name of last buffer text was written',
                      '',
                      'last_written_info_cb', '')
        weechat.hook_info('last_sent',
                      'Return name of last buffer text was sent',
                      '',
                      'last_sent_info_cb', '')

        weechat.hook_command_run('/input return', 'input_return_cb', '')
        weechat.hook_signal ('input_text_changed', 'input_text_changed_cb', '')
