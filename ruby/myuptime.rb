# ==================================================================================================
#  myuptime.rb (c) April 2006 by David DEMONCHY (fusco) <fusco.spv@gmail.com>
#
#  port to WeeChat 0.3.0 by Benjamin Neff (SuperTux88) <info@benjaminneff.ch>
#
#  Licence     : GPL v2
#  Description : Sends machine uptime to current channel
#  Syntax      : /myuptime
#    => uptime  <hostname> :  00:16:58 up 11:09,  4 users,  load average: 0.05, 0.21, 0.29 
#
# ==================================================================================================

def weechat_init
	Weechat.register('myuptime', 'David DEMONCHY (fusco) <fusco.spv@gmail.com>', '0.2', 'GPL2', 'Sends machine uptime to current channel', '', '')
	Weechat.hook_command('myuptime', 'Sends machine uptime to current channel', '', '', '', 'myuptime', '')
	return Weechat::WEECHAT_RC_OK
end

def myuptime(data, buffer, args)
	Weechat.command(buffer, "uptime "+ `hostname`.chomp + ":"  + `uptime`.chomp)
	return Weechat::WEECHAT_RC_OK
end
