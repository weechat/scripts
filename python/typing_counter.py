# Copyright (c) 2010-2013 by fauno <fauno@kiwwwi.com.ar>
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
# 0.4 <nils_2@freenode>:
#       fix display bug with more than one window
# 0.5 <nils_2@freenode>:
#       add description for options
#       add tweet and sms counter for bitlbee and gtalksms (suggested by ahuemer@freenode)
# 0.6 <nils_2@freenode>:
#       add support for gtalksms "reply" (suggested by ahuemer@freenode)
# 0.7 <nils_2@freenode>:
#       fix bug with root bar (reported by fours_)
# 0.8 <nils_2@freenode>:
#       fix regex bug with ":" in sms text (reported by ahuemer)
#
# 0.9 <nils_2@freenode>:
#       add option 'start_cursor_pos_at_zero' (idea by nesthib)
#
# Note: As of version 0.2 this script requires a version of weechat
#       from git 2010-01-25 or newer, or at least 0.3.2 stable.
#
# usage:
# add [tc] to your weechat.bar.status.items
#
# config:
# %P = cursor position
# %L = input length
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
SCRIPT_VERSION = "0.9"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item showing typing count and cursor position. Add 'tc' to a bar."

try:
  import weechat as w

except Exception:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()
try:
    import os, sys, re

except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

tc_input_text   = ''
length          = 0
cursor_pos      = 1
count_over      = '0'

tc_default_options = {
    'format'            : ('[%P|%L|<%R|%C>]','item name to add in a bar is "tc". item format is: %P = cursor position, %L = input length, %R = reverse counting from max_chars, %C = displays how many chars are count over max_chars'),
    'warn'              : ('140','turns indicator to "warn_colour" when position is reached'),
    'warn_colour'       : ('red','color for warn after specified number of chars'),
    'max_chars'         : ('200','max number of chars to count reverse'),
    'warn_command'      : ('', 'to activate a display beep use: $beep'),
    'tweet_buffer'      : ('bitlbee.#tweet','name of tweet buffer. This is a comma separated list'),
    'sms_buffer'        : ('bitlbee.sms','name of sms buffer (using gtalksms). This is a comma separated list'),
    'start_cursor_pos_at_zero': ('off','if option on, cursor position will start counting from zero instead of one'),
}
tc_options = {}

def command_run_cb (data, signal, signal_data):
    if tc_options['warn_command'] == '':
        return w.WEECHAT_RC_OK
    global length, cursor_pos, tc_input_text
    current_buffer = w.current_buffer()
    start_pos = int(tc_options['start_cursor_pos_at_zero'].lower() == 'off')
    cursor_pos = w.buffer_get_integer(current_buffer,'input_pos') + start_pos
    if (cursor_pos -1) == 0:
        tc_action_cb()
    return w.WEECHAT_RC_OK

def tc_bar_item_update (data=None, signal=None, signal_data=None):
    '''Updates bar item'''
    '''May be used as a callback or standalone call.'''
    global length, cursor_pos, tc_input_text

    w.bar_item_update('tc')
    return w.WEECHAT_RC_OK

def tc_bar_item (data, item, window):
    '''Item constructor'''
    # window empty? root bar!
    if not window:
        window = w.current_window()

    global length, cursor_pos, tc_input_text, count_over,tc_options
    count_over = '0'
    sms = ''
    tweet = ''
    reverse_chars = 0

    ptr_buffer = w.window_get_pointer(window,"buffer")
    if ptr_buffer == "":
        return ""

    length = w.buffer_get_integer(ptr_buffer,'input_length')
    start_pos = int(tc_options['start_cursor_pos_at_zero'].lower() == 'off')
    cursor_pos = w.buffer_get_integer(ptr_buffer,'input_pos') + start_pos

    plugin = w.buffer_get_string(ptr_buffer, 'plugin')

    host = ''
    if plugin == 'irc':
        servername = w.buffer_get_string(ptr_buffer, 'localvar_server')
        channelname = w.buffer_get_string(ptr_buffer, 'localvar_channel')
        channel_type = w.buffer_get_string(ptr_buffer, 'localvar_type')
        name = w.buffer_get_string(ptr_buffer, 'localvar_name')
        input_line = w.buffer_get_string(ptr_buffer, 'input')
        mynick = w.info_get('irc_nick', servername)
        nick_ptr = w.nicklist_search_nick(ptr_buffer, '', mynick)

        # check for a sms message
        if channel_type == 'private' and name in tc_options['sms_buffer'].split(","):
            # 160 chars for a sms
            # 'sms:name:text'
            get_sms_text = re.match(r'(s|sms):(.*?:)(.*)', input_line)
            if get_sms_text:
#            if get_sms_text.group(2):
                sms_len = len(get_sms_text.group(3))
#                input_length = len(input_line)
#                sms_prefix = input_length - sms_len
                sms = 160-sms_len
                reverse_chars = sms
            else:
                get_sms_text = re.match(r'(r|reply):(.*)', input_line)
                if get_sms_text:
                    sms_len = len(get_sms_text.group(2))
                    sms = 160-sms_len
                    reverse_chars = sms

        # check for a tweet buffer
        elif name in tc_options['tweet_buffer'].split(","):
            # 140 chars for a tweet! prefix "post " = 5 chars

            # check out if length >= 5 and matches "post "
            if length >= 5 and re.match(r'post (.*)', input_line):
                tweet = 145 - length
                reverse_chars = tweet

        # get host and length from host
        elif servername != channelname:
            infolist = w.infolist_get('irc_nick', '', '%s,%s,%s' % (servername,channelname,mynick))
#            w.prnt("","%s.%s.%s.%s" % (servername,channelname,mynick,nick_ptr))
            while w.infolist_next(infolist):
                host = w.infolist_string(infolist, 'host')
            w.infolist_free(infolist)
            if host != '':
                host = ':%s!%s PRIVMSG %s :' % (mynick,host,channelname)
                host_length = len(host)
#        w.prnt("","%d" % host_length)
                reverse_chars = (475 - int(host_length) - length -1)    # -1 = return
            else:
                reverse_chars = (int(tc_options['max_chars']) - length)
        else:
            reverse_chars = (int(tc_options['max_chars']) - length)
    else:
        # reverse check for max_chars
        reverse_chars = (int(tc_options['max_chars']) - length)

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
    if tc_options['warn']:
        if length >= int(tc_options['warn']):
            length_warn = "%s%s%s" % (w.color(tc_options['warn_colour']), str(length), w.color('default'))
            out_format = out_format.replace('%L', length_warn)
        else:
            out_format = out_format.replace('%L', str(length))
    else:
            out_format = out_format.replace('%L', str(length))

    out_format = out_format.replace('%P', str(cursor_pos))
    if sms:
        out_format = out_format.replace('%R', "s:" + reverse_chars)
    elif tweet:
        out_format = out_format.replace('%R', "t:" + reverse_chars)
    else:
        out_format = out_format.replace('%R', reverse_chars)
    out_format = out_format.replace('%C', count_over)
#    out_format = out_format.replace('%T', str(tweet))
#    out_format = out_format.replace('%S', str(sms))
    tc_input_text = out_format

    return tc_input_text

def init_config():
    global tc_default_options, tc_options

    for option,value in list(tc_default_options.items()):
        w.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, value[0])
            tc_options[option] = value[0]
        else:
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
