#
# Copyright (c) 2009 by Nils Görs <weechatter@arcor.de>
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

# v0.4: auto completion
# v0.3: $extern_command better readable and typo "toogle" instead of "toggle" removed
# v0.2: variable bug removed
# v0.1: first step (in perl)
#
# This script starts an external progam if a user JOIN the chat.
# possible arguments you can give to the external program:
# jnotify_nick : for the nick-name
# jnotify_channel : for the channel-name
#

use strict;
#### Use your own external command here (do not forget the ";" at the end of line):
my $extern_command = qq(notify-send -t 9000 -i /home/nils/.weechat/120px-Weechat_logo.png "jnotify_channel" "neuer User: jnotify_nick");

# example: playing a sound
# my $extern_command = qq(play -q /home/nils/sounds/hello.wav);

###########################
### program starts here ###
###########################
my $version = "0.4";
my $description = "starts an external program if a user JOIN the same channel";
# default values in setup file (~/.weechat/plugins.conf)
my $status		= "status";
my $default_status	= "on";

# first function called by a WeeChat-script.
weechat::register("jnotify", "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

# commands used by jnotify. Type: /help jnotify
weechat::hook_command("jnotify", $description,

	"[toggle | status]", 

	"<toggle> jnotify between on and off\n".
	"<status> tells you if jnotify is on or off\n",
	"toggle|status", "switch", "");


# set value of script (for example starting script the first time)
weechat::config_set_plugin($status, $default_status) if (weechat::config_get_plugin($status) eq "");

# create hook_signal for IRC command JOIN 
weechat::hook_signal("*,irc_in_join", "notify_me", "");			# (servername, signal, script command, arguments)

sub notify_me
{
	my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);		# save callback from hook_signal

	my $mynick = weechat::info_get("irc_nick", split(/,/,$buffer));	# get internal servername: /server
	my $newnick = weechat::info_get("irc_nick_from_host", $args);	# get nickname from new user
	my ($channelname) = ($args =~ m!.*:(.*)!);			# extract channel name from hook_signal


	return weechat::WEECHAT_RC_OK if ($mynick eq $newnick);		# if mynick equal newnick. Its me!!!
	my $external_command = $extern_command;				# save command
	$external_command =~ s/jnotify_channel/$channelname/;		# replace string "jnotify_channel" with $channelname
	$external_command =~ s/jnotify_nick/$newnick/;			# replace string "jnotify_nick" with $newnick

	my $notify = weechat::config_get_plugin($status);		# get status-value from jnotify
	system($external_command) if ($notify eq "on");			# start external program, when jnotify is ON

	return weechat::WEECHAT_RC_OK;					# Return_Code OK
}

sub switch
{
	my ($getargs) = ($_[2]);
	my $jnotify = weechat::config_get_plugin($status);		# get value from jnotify

	if ($getargs eq $status or "")
		{
			weechat::print("","jnotify is: $jnotify");	# print status of jnotify
			return weechat::WEECHAT_RC_OK;			# Return_Code OK
		}

	if ($getargs eq "toggle")
		{

		if ($jnotify eq "off")
			{
				weechat::config_set_plugin($status, "on");
			}

		else
			{
				weechat::config_set_plugin($status, "off");
			}
		return weechat::WEECHAT_RC_OK;					# Return_Code OK
		}

}
