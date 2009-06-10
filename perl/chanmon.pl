#
# chanmon.pl - Channel Monitoring for weechat 0.3.0 
#
# Add 'Channel Monitor' buffer that you can position to show IRC channel
# messages in a single location without constantly switching buffers
# i.e. In a seperate window beneath the main channel buffer
#
# Usage:
# /monitor is used to toggle a channel monitoring on and off, this needs
# to be used in the channel buffer for the channel you wish to toggle
#
# Ideal set up:
# Split the layout 70/30 (or there abouts) horizontally and load
# Optionally, make the status and input lines only show on active windows
#
# /window splith 70 --> open the chanmon buffer
# /set weechat.bar.status.conditions "active"
# /set weechat.bar.input.conditions "active"
#

#
# Copyright (c) 2009 by KenjiE20 <longbow@longbowslair.co.uk>
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

my $chanmon_buffer = "";

sub chanmon_new_message
{
	my $net = "";
	my $chan = "";
	my $nick = "";
	my $outstr = "";

#	DEBUG point
#	$string = "0: ".$_[0]." 1: ".$_[1]." 2: ".$_[2]." 3: ".$_[3]." 4: ".$_[4]." 5: ".$_[5]." 6: ".$_[6]." 7: ".$_[7];
#	weechat::print("", $string);

	if ($_[3] =~ /irc_privmsg/ || $_[3] =~ /irc_topic/)
	{
		$bufname = weechat::buffer_get_string($_[1], 'name');
		if (weechat::config_get_plugin($bufname) eq "" && $bufname =~ /(.*)\.#(.*)/)
		{
			weechat::config_set_plugin($bufname, "True");
		}
		if (weechat::config_get_plugin($bufname) eq "True" && $_[4] eq "1")
		{
			if ($bufname =~ /(.*)\.#(.*)/) {
				$bufname = $1."#".$2;
				if (!($_[6] =~ / \*/) && !($_[6] =~ /--/)) {
					if ($_[5] eq "1")
					{
						$uncolnick = weechat::string_remove_color($_[6], "");
						$nick = " <".weechat::color("chat_highlight").$uncolnick.weechat::color("reset").">";
					}
					else
					{
						$nick = " <".$_[6].weechat::color("reset").">";
					}
				}
				elsif ($_[6] =~ /--/) {
					$nick = " ".$_[6].weechat::color("reset");
				}
				else {
					$nick = $_[6].weechat::color("reset");
				}
				$outstr = $bufname.":".$nick." ".$_[7];

				weechat::print($chanmon_buffer, $outstr);
			}
		}
	}
	# Special outgoing ACTION catcher
	elsif ($_[3] eq "")
	{
		$bufname = weechat::buffer_get_string($_[1], 'name');
		if (weechat::config_get_plugin($bufname) eq "" && $bufname =~ /(.*)\.#(.*)/)
		{
			weechat::config_set_plugin($bufname, "True");
		}
		if (weechat::config_get_plugin($bufname) eq "True" && $_[4] eq "1")
		{
			if ($bufname =~ /(.*)\.#(.*)/) {
				$bufname = $1."#".$2;
				$net = $1;
				$mynick = weechat::info_get("irc_nick", $net);
				if ($_[7] =~ $mynick)
				{
					$nick = weechat::color("white")." *".$nick.weechat::color("reset");
					$outstr = $bufname.":".$nick." ".$_[7];
					
					weechat::print($chanmon_buffer, $outstr);

				}
				
			}
		}
	}

	return weechat::WEECHAT_RC_OK;
}

sub chanmon_toggle
{
	$bufname = weechat::buffer_get_string(weechat::current_buffer(), 'name');
	$str = "";
	if (weechat::config_get_plugin($bufname) eq "False")
	{
		weechat::config_set_plugin($bufname, "True");
		$nicename = $bufname;
		$nicename =~ s/(.*)\.#(.*)/$1#$2/;
		$str = $nicename.": Channel Monitoring Enabled";
		weechat::print($chanmon_buffer, $str);
		return weechat::WEECHAT_RC_OK;
	}
	elsif (weechat::config_get_plugin($bufname) eq "True" || weechat::config_get_plugin($bufname) eq "")
	{
		weechat::config_set_plugin($bufname, "False");
		$nicename = $bufname;
		$nicename =~ s/(.*)\.#(.*)/$1#$2/;
		$str = $nicename.": Channel Monitoring Disabled";
		weechat::print($chanmon_buffer, $str);
		return weechat::WEECHAT_RC_OK;
	}
}

sub chanmon_buffer_close
{
	weechat::buffer_close($chanmon_buffer);
	$chanmon_buffer = "";
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_setup
{
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_open
{
	$chanmon_buffer = weechat::buffer_new("chanmon", "chanmon_buffer_setup", "", "", "chanmon_buffer_close", "");
	weechat::buffer_set($chanmon_buffer, "notify", "0");
	weechat::buffer_set($chanmon_buffer, "title", "Channel Monitor");
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_input
{
	return weechat::WEECHAT_RC_OK;
}

weechat::register("chanmon", "KenjiE20", "1.0", "GPL3", "Channel Monitor", "", "");
weechat::hook_print("", "", "", 0, "chanmon_new_message", "");
weechat::hook_command("monitor", "Toggles monitoring for a channel (must be used in the channel buffer itself)", "", "", "", "chanmon_toggle", "");
weechat::hook_config("plugins.var.perl.chanmon.*", "", "");
chanmon_buffer_open();
