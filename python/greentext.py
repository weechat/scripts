# # Weechat-Greentext
# Version:          v1
# Min WeeChat
#  version tested:  3.8
# Author:           AGVXOV
# Contact:          agvxov@gmail.com
# Project Home:     https://github.com/agvxov/weechat-greentext
# This script is Public Domain.
#
# Weechat script for applying imageboard formatting to messages. The following are supported:
#  + greentext
#  + purpletext
#  + redtext
# 
# Both inbound and outbound messages are colored.
# Since the coloring uses IRC color codes,
# outbound greentexting will be visible to both you and your friends.
#
import weechat
import re

SCRIPT_NAME    = "greentext"
SCRIPT_AUTHOR  = "AGVXOV"
SCRIPT_VERSION = "1"
SCRIPT_LICENSE = "PD"
SCRIPT_DESC    = "Colorize imageboard-style text formatting."

greentext_re  = re.compile("^\s*>.*$")
purpletext_re = re.compile("^\s*<.*$")
redtext_re    = re.compile("^.*(==.*==).*$")

COLOR_GREEN  = chr(3) + str(3)
COLOR_PURPLE = chr(3) + str(6)
COLOR_RED    = chr(3) + str(4) + chr(2)
COLOR_END    = chr(3) + str(0)

def hi_greentext(modifier, s):
	if greentext_re.search(s):
		if modifier == 'irc_out1_PRIVMSG':
			s = COLOR_GREEN + s
		else:
			s = weechat.color("green") + s
	return s

def hi_purpletext(modifier, s):
	if purpletext_re.search(s):
		if modifier == 'irc_out1_PRIVMSG':
			s = COLOR_PURPLE + s
		else:
			s = weechat.color("magenta") + s
	return s

def hi_redtext(modifier, s):
	if redtext_re.search(s):
		if modifier == 'irc_out1_PRIVMSG':
			m = redtext_re.search(s)
			s = s[:m.start(1)] + COLOR_RED + m.group(1) + COLOR_END + s[m.end(1):]
		else:
			s = weechat.color("red") + s
	return s

def hi(data, modifier, modifier_data, s):
	msg = weechat.info_get_hashtable('irc_message_parse', {'message': s})
	r = msg["text"]
	r = hi_greentext(modifier, r)
	r = hi_purpletext(modifier, r)
	r = hi_redtext(modifier, r)
	r = s[:-len(msg["text"])] + r
	return r
	
def main():
	if not weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
		return
	weechat.hook_modifier('irc_in2_privmsg', 'hi', '')
	weechat.hook_modifier('irc_out1_privmsg', 'hi', '')
	
if __name__ == "__main__":
	main()
