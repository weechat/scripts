#Author: Martin Pugh
#Contact: mpugh89@gmail.com
#Usage: /rainbow some text here
#Displays text in rainbow colours
#License: WTFPL v2

import weechat
weechat.register('rainbow', '0.5', '', """Print rainbow-colored text. Usage: /rainbow""")
weechat.add_command_handler("rainbow", "rainbow", "print rainbow text")

def rainbow(server, args):
	colors=["9","11","12","13","4"]
	out = ""
	ci = 0
	if args != "":
		for i in range(0,len(args)):
			out += '\x03' + colors[ci] + '\x02' + args[i]
			if ci == len(colors)-1:
				ci = 0
			else:
				ci += 1
		outcommand = '/say ' + out
		weechat.command(outcommand)
	else:
		weechat.prnt("rainbow: no text to output")
	return weechat.PLUGIN_RC_OK
