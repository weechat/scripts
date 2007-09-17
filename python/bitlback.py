"""
  The script is something like timing's bitlbee_join_notice.pl for weechat
  ( http://the-timing.nl/Projects/Irssi-BitlBee/bitlbee_join_notice.pl ).
  It duplicates info about buddy comming back to &bitlbee channel to 
  open query with this buddy (if any).

  The script is in the public domain.
  Leonid Evdokimov (weechat at darkk dot net dot ru)
  http://darkk.net.ru/weechat/bitlback.py

0.1 - initial commit
"""

#######################################################################

import weechat

VERSION = "0.1"
NAME = "bitlback"

def GUI_COLOR(setting):
    color = weechat.get_config(setting)
    if not color:
        raise ValueError("'%s' is not valid color setting" % setting)
    if color == 'default':
        return '\x0f'
    else:
        i = weechat.get_irc_color(color)
        if i < 0:
            raise ValueError("'%s' => '%s' is not valid color" % (setting, color))
        return '\x03%02d' % i

def on_join(servername, args):
    try:
        # :FireEgl!~FireEgl@2001:5c0:84dc:0:211:9ff:feca:b042 JOIN :&bitlbee
        l = args.split(' ', 2)
        if l[2] == ':&bitlbee':
            nick, host = l[0][1:].split("!", 1)
            for b in weechat.get_buffer_info().itervalues():
                if (b['server'] == servername) and (b['channel'] == nick):
                    weechat.prnt('%s--> %s%s %s(%s%s%s)%s has joined %s&bitlbee' %
                            (
                                GUI_COLOR('col_chat_join'),
                                GUI_COLOR('col_chat_nick'),
                                nick,
                                GUI_COLOR('col_chat_dark'),
                                GUI_COLOR('col_chat_host'),
                                host,
                                GUI_COLOR('col_chat_dark'),
                                GUI_COLOR('col_chat'),
                                GUI_COLOR('col_chat_channel'),
                            ),
                            nick,
                            servername)
                    break
    except:
        print args
        raise
    return weechat.PLUGIN_RC_OK

if weechat.register(NAME, VERSION, "", "informs open bitlbee queries when person returns back after going offline"):
    weechat.add_message_handler("join", "on_join")


# vim:set tabstop=4 softtabstop=4 shiftwidth=4: 
# vim:set foldmethod=marker foldlevel=32 foldmarker={{{,}}}: 
# vim:set expandtab: 
