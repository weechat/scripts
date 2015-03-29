# -*- coding: utf-8 -*-
#
# whoissource.py
# Copyright (c) 2014 by Max Teufel <max@teufelsnetz.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Display source of "End of WHOIS" numerics
# WeeChat port of http://www.stack.nl/~jilles/irc/whoissource.pl.txt

SCRIPT_NAME    = "whoissource"
SCRIPT_AUTHOR  = "Max Teufel"
SCRIPT_VERSION = "0.0.2"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC    = "Display source of \"End of WHOIS\" numerics"

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

def get_buffer(server, nick):
    msgbuffer = weechat.config_string(weechat.config_get('irc.msgbuffer.%s.%s' % (server, 'whois')))
    if msgbuffer == '':
        msgbuffer = weechat.config_string(weechat.config_get('irc.msgbuffer.%s' % 'whois'))

    if msgbuffer == 'private':
        buffer = weechat.buffer_search('irc', '%s.%s' %(server, nick))
        if buffer != '':
            return buffer
        else:
            msgbuffer = weechat.config_string(weechat.config_get('irc.look.msgbuffer_fallback'))

    if msgbuffer == "current":
        return weechat.current_buffer()
    elif msgbuffer == "weechat":
        return weechat.buffer_search_main()
    else:
        return weechat.buffer_search('irc', 'server.%s' % server)

def endofwhois_cb(data, signal, signal_data):
    whois_source = weechat.info_get("irc_nick_from_host", signal_data)
    server = signal.split(",")[0]
    whois_nick = signal_data.split(" ")[3]
    prefix_network = weechat.prefix('network')
    color_delimiter = weechat.color('chat_delimiters')
    buffer = get_buffer(server, whois_nick)
    if whois_nick == weechat.info_get("irc_nick", server):
        color_nick = weechat.color("chat_nick_self")
    elif weechat.info_get("irc_nick_color", whois_nick) != '':
        color_nick = weechat.info_get("irc_nick_color", whois_nick)
    else:
        color_nick = weechat.color('chat_nick')
    color_reset = weechat.color('reset')
    string = "Got /WHOIS reply from %s" % (whois_source)
    weechat.prnt(buffer, '%s%s[%s%s%s]%s %s' % (prefix_network,
                                                color_delimiter,
                                                color_nick,
                                                whois_nick,
                                                color_delimiter,
                                                color_reset,
                                                string))
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    weechat.hook_signal("*,irc_in2_318", "endofwhois_cb", "")

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
