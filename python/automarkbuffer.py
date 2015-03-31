# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by nils_2 <weechatter@arcor.de>
#
# mark buffers as read if there is no new message in a specific time range
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
# idea by bascht
#
# 2015-01-25: nils_2, (freenode.#weechat)
#       1.0 : initial release

try:
    import weechat
    import time

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "automarkbuffer"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "1.0"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "mark buffers as read if there is no new message in a specific time range"
TIMER           = None
WEECHAT_VERSION = ""
whitelist       = []

OPTIONS         = { 'whitelist'                         : ('','comma separated list of buffer to ignore, e.g. freenode.#weechat,freenode.#weechat-de (check name of buffer with : /buffer localvar)'),
                    'time'                              : ('3600','time in seconds to mark buffer as read, if there are no new messages'),
                    'interval'                          : ('60','how often in seconds to check for messages'),
                    'clear'                             : ('all','hotlist = remove buffer from hotlist, unread = set unread marker, all = hotlist & unread'),
                    'ignore_hidden'                     : ('on','hidden messages will be ignored (for example "irc_smart_filter" ones)'),
                    'ignore_query'                      : ('on','query buffer(s) will be ignored'),
                   }

def check_buffer_timer_cb(data, remaining_calls):
    global WEECHAT_VERSION,whitelist

    # search for buffers in hotlist
    ptr_infolist = weechat.infolist_get("hotlist", "", "")
    while weechat.infolist_next(ptr_infolist):
        ptr_buffer = weechat.infolist_pointer(ptr_infolist, "buffer_pointer")
        localvar_name = weechat.buffer_get_string(ptr_buffer, 'localvar_name')
        # buffer in whitelist? go to next buffer
        buf_type = weechat.buffer_get_string(ptr_buffer,'localvar_type')
        # buffer is a query buffer?
        if OPTIONS['ignore_query'].lower() == 'on' and buf_type == 'private':
            continue
        # buffer in whitelist?
        if localvar_name in whitelist:
            continue
        if ptr_buffer:
            if get_time_from_line(ptr_buffer):
                if OPTIONS['clear'].lower() == 'hotlist' or OPTIONS['clear'].lower() == 'all':
                    weechat.buffer_set(ptr_buffer, "hotlist", '-1')
                if OPTIONS['clear'].lower() == 'unread' or OPTIONS['clear'].lower() == 'all':
                    weechat.command(ptr_buffer,"/input set_unread_current_buffer")

    weechat.infolist_free(ptr_infolist)
    return weechat.WEECHAT_RC_OK

def get_time_from_line(ptr_buffer):
    lines = weechat.hdata_pointer(weechat.hdata_get('buffer'), ptr_buffer, 'own_lines')

    if lines:
        line = weechat.hdata_pointer(weechat.hdata_get('lines'), lines, 'last_line')
        last_read_line = weechat.hdata_pointer(weechat.hdata_get('lines'), lines, 'last_read_line')
        # last line already read?
        while line != last_read_line:
            hdata_line = weechat.hdata_get('line')
            hdata_line_data = weechat.hdata_get('line_data')

            data = weechat.hdata_pointer(hdata_line, line, 'data')

            date_last_line = weechat.hdata_time(hdata_line_data, data, 'date')
            displayed = weechat.hdata_char(hdata_line_data, data, 'displayed')
            # message hidden?
            if not displayed and OPTIONS['ignore_hidden'].lower() == 'on':
                prev_line = weechat.hdata_pointer(hdata_line, line, 'prev_line')
                line = prev_line
                continue

            # buffer empty?
            if not date_last_line:
                return 0

            get_current_ticks = time.time()

            time_gone = get_current_ticks - date_last_line
            if int(OPTIONS['time']) < time_gone:
                return 1
            else:
                return 0
    return 0
# ================================[ weechat options and description ]===============================
def set_timer():
    global TIMER
    if TIMER:
        weechat.unhook(TIMER)
    if int(OPTIONS['interval']) == 0:
        return
    TIMER = weechat.hook_timer(int(OPTIONS['interval']) * 1000,
            0, 0, 'check_buffer_timer_cb', '')

def init_options():
    for option,value in OPTIONS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, "%s (default: '%s')" % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS,whitelist
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    if name.endswith('.interval'):                                        # timer value changed?
        set_timer()

    if name.endswith('.whitelist'):                                       # whitelist changed?
        whitelist = OPTIONS['whitelist'].split(',')
    return weechat.WEECHAT_RC_OK
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        WEECHAT_VERSION = weechat.info_get("version_number", "") or 0

        if int(WEECHAT_VERSION) >= 0x01000000:
            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
            init_options()
            set_timer()
            whitelist = OPTIONS['whitelist'].split(',')
        else:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 1.0 or higher'))
