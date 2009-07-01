#
# chanmon.pl - Channel Monitoring for weechat 0.3.0
# Version 1.3
#
# Add 'Channel Monitor' buffer that you can position to show IRC channel
# messages in a single location without constantly switching buffers
# i.e. In a seperate window beneath the main channel buffer
#
# Usage:
# /monitor is used to toggle a channel monitoring on and off, this needs
# to be used in the channel buffer for the channel you wish to toggle
#
# /dynmon is used to toggle 'Dynamic Channel Monitoring' on and off, this
# will automagically stop monitoring the current active buffer, without
# affecting regular settings (Default is off)
#
# /set plugins.var.perl.chanmon.alignment "channel"
# The config setting "alignment" can be changed to;
# "channel", "schannel", "channel,nick", "schannel,nick"
# to change how the monitor appears
# The 'schannel' value will only show the buffer number as opposed to
# 'server#channel'
#
# Ideal set up:
# Split the layout 70/30 (or there abouts) horizontally and load
# Optionally, make the status and input lines only show on active windows
#
# /window splith 70 --> open the chanmon buffer
# /set weechat.bar.status.conditions "active"
# /set weechat.bar.input.conditions "active"
#
# History:
# 2009-07-01, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.3	-feature(tte): Mimic buffers.pl 'short_names'
# 2009-06-29, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.2.1	-fix: let the /monitor message respect the alignment setting
# 2009-06-19, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.2	-feature(tte): Customisable alignment
#			Thanks to 'FreakGaurd' for the idea
# 2009-06-14, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.1.2	-fix: don't assume chanmon buffer needs creating
#			fixes crashing with /upgrade
# 2009-06-13, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.1.1	-code: change from True/False to on/off for weechat consistency
#			Settings WILL NEED to be changed manually from previous versions
# 2009-06-13, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.1:	-feature(tte): Dynamic Channel Monitoring,
#			don't display messages from active channel buffer
#			defaults to Disabled
#			Thanks to 'sjohnson' for the idea
#		-fix: don't set config entries for non-channels
#		-fix: don't assume all channels are #
# 2009-06-12, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0.1:	-fix: glitch with tabs in IRC messages
# 2009-06-10, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0:	Initial Public Release
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
	my $curbuf = "";
	my $dyncheck = "0";

#	DEBUG point
#	$string = "\t"."0: ".$_[0]." 1: ".$_[1]." 2: ".$_[2]." 3: ".$_[3]." 4: ".$_[4]." 5: ".$_[5]." 6: ".$_[6]." 7: ".$_[7];
#	weechat::print("", "\t".$string);

	if ($_[3] =~ /irc_privmsg/ || $_[3] =~ /irc_topic/)
	{
		$bufname = weechat::buffer_get_string($_[1], 'name');
		if (weechat::config_get_plugin($bufname) eq "" && $bufname =~ /(.*)\.([#&\+!])(.*)/)
		{
			weechat::config_set_plugin($bufname, "on");
		}
		if (weechat::config_get_plugin($bufname) eq "on" && $_[4] eq "1")
		{
			if ($bufname =~ /(.*)\.([#&\+!])(.*)/)
			{
				if (weechat::config_get_plugin("dynamic") eq "on")
				{
					$curbuf = weechat::buffer_get_string(weechat::current_buffer(), 'name');
					if ($bufname ne $curbuf)
					{
						$dyncheck = "1";
					}
				}

				$bufname = $1.$2.$3;
				if (!($_[6] =~ / \*/) && !($_[6] =~ /--/))
				{
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
				elsif ($_[6] =~ /--/)
				{
					$nick = " ".$_[6].weechat::color("reset");
				}
				else
				{
					$nick = $_[6].weechat::color("reset");
				}
				
				if (weechat::config_get_plugin("short_names") eq "on")
				{
					$bufname =~ s/.*([#&\+!])(.*)/$1$2/;
				}

				if (weechat::config_get_plugin("alignment") eq "channel")
				{
					$nick =~ s/\s(.*)/$1/;
					$outstr = $bufname."\t".$nick." ".$_[7];
				}
				elsif (weechat::config_get_plugin("alignment") eq "schannel")
				{
					$nick =~ s/\s(.*)/$1/;
					$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($_[1], 'number').weechat::color("reset");
					$outstr = $bufname."\t".$nick." ".$_[7];
				}
				elsif (weechat::config_get_plugin("alignment") eq "channel,nick")
				{
					$outstr = $bufname.":".$nick."\t".$_[7];
				}
				elsif (weechat::config_get_plugin("alignment") eq "schannel,nick")
				{
					$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($_[1], 'number').weechat::color("reset");
					$outstr = $bufname.":".$nick."\t".$_[7];
				}
				else
				{
					$outstr = "\t".$bufname.":".$nick." ".$_[7];
				}

				if (weechat::config_get_plugin("dynamic") eq "on")
				{
					if ($dyncheck)
					{
						weechat::print($chanmon_buffer, $outstr);
					}
				}
				else
				{
					weechat::print($chanmon_buffer, $outstr);
				}
			}
		}
	}
	# Special outgoing ACTION catcher
	elsif ($_[3] eq "")
	{
		$bufname = weechat::buffer_get_string($_[1], 'name');
		if (weechat::config_get_plugin($bufname) eq "" && $bufname =~ /(.*)\.([#&\+!])(.*)/)
		{
			weechat::config_set_plugin($bufname, "on");
		}
		if (weechat::config_get_plugin($bufname) eq "on" && $_[4] eq "1")
		{
			if ($bufname =~ /(.*)\.([#&\+!])(.*)/)
			{
				if (weechat::config_get_plugin("dynamic") eq "on")
				{
					$curbuf = weechat::buffer_get_string(weechat::current_buffer(), 'name');
					if ($bufname ne $curbuf)
					{
						$dyncheck = "1";
					}
				}

				$bufname = $1.$2.$3;
				$net = $1;
				$mynick = weechat::info_get("irc_nick", $net);
				if ($_[7] =~ $mynick)
				{
					$nick = weechat::color("white")." *".$nick.weechat::color("reset");

					if (weechat::config_get_plugin("short_names") eq "on")
					{
						$bufname =~ s/.*([#&\+!])(.*)/$1$2/;
					}

					if (weechat::config_get_plugin("alignment") eq "channel")
					{
						$nick =~ s/\s(.*)/$1/;
						$outstr = $bufname."\t".$nick." ".$_[7];
					}
					elsif (weechat::config_get_plugin("alignment") eq "schannel")
					{
						$nick =~ s/\s(.*)/$1/;
						$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($_[1], 'number').weechat::color("reset");
						$outstr = $bufname."\t".$nick." ".$_[7];
					}
					elsif (weechat::config_get_plugin("alignment") eq "channel,nick")
					{
						$outstr = $bufname.":".$nick."\t".$_[7];
					}
					elsif (weechat::config_get_plugin("alignment") eq "schannel,nick")
					{
						$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($_[1], 'number').weechat::color("reset");
						$outstr = $bufname.":".$nick."\t".$_[7];
					}
					else
					{
						$outstr = "\t".$bufname.":".$nick." ".$_[7];
					}

					if (weechat::config_get_plugin("dynamic") eq "on")
					{
						if ($dyncheck)
						{
							weechat::print($chanmon_buffer, $outstr);
						}
					}
					else
					{
						weechat::print($chanmon_buffer, $outstr);
					}
				}
			}
		}
	}
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_toggle
{
	$bufname = weechat::buffer_get_string(weechat::current_buffer(), 'name');
	if ($bufname =~ /(.*)\.([#&\+!])(.*)/)
	{
		$sbuf = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer(weechat::current_buffer(), 'number').weechat::color("reset");
		$str = "";
		if (weechat::config_get_plugin($bufname) eq "off")
		{
			weechat::config_set_plugin($bufname, "on");
			$nicename = $bufname;
			$nicename =~ s/(.*)\.([#&\+!])(.*)/$1$2$3/;

			if (weechat::config_get_plugin("short_names") eq "on")
			{
				$nicename =~ s/.*([#&\+!])(.*)/$1$2/;
			}

			if (weechat::config_get_plugin("alignment") =~ /channel/)
			{
				if (weechat::config_get_plugin("alignment") =~ /schannel/)
				{
					$str = $sbuf."\tChannel Monitoring Enabled";
				}
				else
				{
					$str = $nicename."\tChannel Monitoring Enabled";
				}
			}
			else
			{
				$str = $nicename.": Channel Monitoring Enabled";
			}
			weechat::print($chanmon_buffer, $str);
			return weechat::WEECHAT_RC_OK;
		}
		elsif (weechat::config_get_plugin($bufname) eq "on" || weechat::config_get_plugin($bufname) eq "")
		{
			weechat::config_set_plugin($bufname, "off");
			$nicename = $bufname;
			$nicename =~ s/(.*)\.([#&\+!])(.*)/$1$2$3/;
			
			if (weechat::config_get_plugin("short_names") eq "on")
			{
				$nicename =~ s/.*([#&\+!])(.*)/$1$2/;
			}

			if (weechat::config_get_plugin("alignment") =~ /channel/)
			{
				if (weechat::config_get_plugin("alignment") =~ /schannel/)
				{
					$str = $sbuf."\tChannel Monitoring Disabled";
				}
				else
				{
					$str = $nicename."\tChannel Monitoring Disabled";
				}
			}
			else
			{
				$str = $nicename.": Channel Monitoring Disabled";
			}
			weechat::print($chanmon_buffer, $str);
			return weechat::WEECHAT_RC_OK;
		}
	}
}

sub chanmon_dyn_toggle
{
	$str = "";
	if (weechat::config_get_plugin("dynamic") eq "off")
	{
		weechat::config_set_plugin("dynamic", "on");
		$str = "Dynamic Channel Monitoring Enabled";
		weechat::print($chanmon_buffer, $str);
		return weechat::WEECHAT_RC_OK;
	}
	elsif (weechat::config_get_plugin("dynamic") eq "on")
	{
		weechat::config_set_plugin("dynamic", "off");
		$str = "Dynamic Channel Monitoring Disabled";
		weechat::print($chanmon_buffer, $str);
		return weechat::WEECHAT_RC_OK;
	}
}

sub chanmon_buffer_close
{
	$chanmon_buffer = "";
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_setup
{
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_open
{
	$chanmon_buffer = weechat::buffer_search("perl", "chanmon");

	if ($chanmon_buffer eq "")
	{
		$chanmon_buffer = weechat::buffer_new("chanmon", "chanmon_buffer_setup", "", "", "chanmon_buffer_close", "");
	}

	if ($chanmon_buffer ne "")
	{
		weechat::buffer_set($chanmon_buffer, "notify", "0");
		weechat::buffer_set($chanmon_buffer, "title", "Channel Monitor");
	}
	return weechat::WEECHAT_RC_OK;
}

sub chanmon_buffer_input
{
	return weechat::WEECHAT_RC_OK;
}

weechat::register("chanmon", "KenjiE20", "1.3", "GPL3", "Channel Monitor", "", "");
weechat::hook_print("", "", "", 0, "chanmon_new_message", "");
weechat::hook_command("monitor", "Toggles monitoring for a channel (must be used in the channel buffer itself)", "", "", "", "chanmon_toggle", "");
weechat::hook_command("dynmon", "Toggles 'dynamic' monitoring (auto-disable monitoring for current channel)", "", "", "", "chanmon_dyn_toggle", "");
weechat::hook_config("plugins.var.perl.chanmon.*", "", "");
if (!(weechat::config_is_set_plugin ("alignment")))
{
	weechat::config_set_plugin("alignment", "channel");
}
if (weechat::config_get_plugin("alignment") eq "")
{
	weechat::config_set_plugin("alignment", "none");
}
if (weechat::config_get_plugin("dynamic") eq "")
{
	weechat::config_set_plugin("dynamic", "off");
}
if (!(weechat::config_is_set_plugin ("short_names")))
{
	weechat::config_set_plugin("short_names", "off");
}
chanmon_buffer_open();
