#Author: Pawel Pogorzelski <pawelpogorzelski AT gmail DOT com>
#What it does: This script shows when Your nick is highlighted via libnotify 
#Released under GNU GPL v2 or newer

#/usr/bin/python
#coding: utf-8

import weechat,string 
from os import popen

weechat.register ('weenotify', '0.02', '', """Remember to replace ******** in plugins.rc with your nickname""")
weechat.add_message_handler("privmsg", "show_it_to_them")

default = {
##Remember to replace ******** in plugins.rc with your nickname
  "nick_check": "********",
  "time": "3",
  "icon": "/usr/share/pixmaps/gnome-irc.png"
}

for k, v in default.items():
	if not weechat.get_plugin_config(k):
    		weechat.set_plugin_config(k, v)

def show_it_to_them(server, args):
	nick_check = weechat.get_plugin_config("nick_check")
	time = str(int(weechat.get_plugin_config("time")) * 1000)
	icon = weechat.get_plugin_config("icon")
#	weechat.prnt( args )
	split_first = args.split('!')
	sender = split_first[0].replace(':','')
	split_second = split_first[1].split('PRIVMSG')
#	weechat.prnt('second' + split_second[1])
	channel_temp = split_second[1].split(':')
	channel = channel_temp[0].strip()
#	weechat.prnt('channel' + channel)
	message_split = args.split(channel + ' :')
	if message_split[0] != ' ':
#		weechat.prnt('message' + message_split[1])
		message = message_split[1].replace('"',"'")
#		message.replace('"','\ ')
#		message = "a"
#		weechat.prnt('message' + message)
		if args.find(nick_check) != -1:
			popen ("notify-send " + sender + "@" + channel + ' "' + message +'" -t '+time + " -i " +icon)	
  	return 0


