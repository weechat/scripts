#
# Copyright (c) 2010, Chris Branch <x@chrisbranch.co.uk>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# History:
# 2010-07-26
#   revision 1.0
#

import weechat
import time

SCRIPT_NAME    = "ichatts"
SCRIPT_AUTHOR  = "Chris Branch <x@chrisbranch.co.uk>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "BSD"
SCRIPT_DESC    = "iChat-style timestamps"

settings = {
    "minutes_until_timestamp" : '5',    # print when no message occurs for this long
    "remind_every"            : '15',   # print a new timestamp every X minutes if there is activity
}

buffer_dates = {}

def prnt_timestamp(buffer, timestamp):
    weechat.prnt(buffer, '%s[%s%s%s:%s%s%s]' %
	(weechat.color("chat_delimiters"),
	 weechat.color("chat_time"),
	 time.strftime('%H', time.localtime(timestamp)),
	 weechat.color("chat_time_delimiters"),
	 weechat.color("chat_time"),
	 time.strftime('%M', time.localtime(timestamp)),
	 weechat.color("chat_delimiters")))

def timer_cb(data, remaining_calls):
    global buffer_dates
    current_time = int(time.time())
    timestamp_secs = int(weechat.config_get_plugin('minutes_until_timestamp')) * 60
    # Which buffers need a timestamp printing?
    for (buffer, (last_message, last_printed)) in buffer_dates.items():
        # If X minutes have elapsed since the last message, and we haven't printed anything since then.
        if last_printed < last_message and current_time - last_message >= timestamp_secs:
            buffer_dates[buffer] = (last_message, current_time)
            prnt_timestamp(buffer, last_message)
    return weechat.WEECHAT_RC_OK

def print_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    # Update buffer with date of last message
    global buffer_dates
    current_time = int(date)
    last_printed = buffer_dates.get(buffer, (0, 0))[1]
    remind_secs = int(weechat.config_get_plugin('remind_every')) * 60
    # Has it been X minutes since we last printed a timestamp?
    if current_time - last_printed >= remind_secs:
        last_printed = current_time
        prnt_timestamp(buffer, current_time)
        
    buffer_dates[buffer] = (current_time, last_printed)
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        # Set default settings
        for option, default_value in settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

	weechat.hook_timer(60000, 60, 0, 'timer_cb', '')
        weechat.hook_print('', '', '', 0, 'print_cb', '')

