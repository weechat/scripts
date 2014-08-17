#
# chanmon.pl - Channel Monitoring for weechat 0.3.0
# Version 2.5
#
# Add 'Channel Monitor' buffer/bar that you can position to show IRC channel
# messages in a single location without constantly switching buffers
# i.e. In a seperate window beneath the main channel buffer
#
# Usage:
# /chanmon [help] | [monitor [channel [server]]] | [dynmon] | [clean default|orphan|all] | clearbar
#  Command wrapper for chanmon commands
#
# /chmonitor [channel] [server] is used to toggle a channel monitoring on and off, this
#  can be used in the channel buffer for the channel you wish to toggle, or be given
#  with arguments e.g. /monitor #weechat freenode
#
# /dynmon is used to toggle 'Dynamic Channel Monitoring' on and off, this
#  will automagically stop monitoring the current active buffer, without
#  affecting regular settings (Default is off)
#
# /chanclean default|orphan|all will clean the config section of default 'on' entries,
#  channels you are no longer joined, or both
#
# /chanmon clearbar will clear the contents of chanmon's bar output
#
# /set plugins.var.perl.chanmon.alignment
#  The config setting "alignment" can be changed to;
#  "channel", "schannel", "nchannel", "channel,nick", "schannel,nick", "nchannel,nick"
#  to change how the monitor appears
#  The 'channel'  value will show: "#weechat"
#  The 'schannel' value will show: "6"
#  The 'nchannel' value will show: "6:#weechat"
#
# /set plugins.var.perl.chanmon.short_names
#  Setting this to 'on' will trim the network name from chanmon, ala buffers.pl
#
# /set plugins.var.perl.chanmon.merge_private
#  Setting this to 'on' will merge private messages to chanmon's display
#
# /set plugins.var.perl.chanmon.color_buf
#  This turns colored buffer names on or off, you can also set a single fixed color by using a weechat color name.
#  This *must* be a valid color name, or weechat will likely do unexpected things :)
#
# /set plugins.var.perl.chanmon.show_aways
#  Toggles showing the Weechat away messages
#
# /set plugins.var.perl.chanmon.logging
#  Toggles logging status for chanmon buffer (default: off)
#
# /set plugins.var.perl.chanmon.output
#  Changes where output method of chanmon; takes either "bar" or "buffer" (default; buffer)
# /set plugins.var.perl.chanmon.bar_lines
#  Changes the amount of lines the output bar will hold.
#  (Only appears once output has been set to bar, defaults to 10)
#
# /set plugins.var.perl.chanmon.nick_prefix
# /set plugins.var.perl.chanmon.nick_suffix
#  Sets the prefix and suffix chars in the chanmon buffer
#  (Defaults to <> if nothing set, and blank if there is)
#
# servername.#channel
#  servername is the internal name for the server (set when you use /server add)
#  #channel is the channel name, (where # is whatever channel type that channel happens to be)
#
# Example set up:
# Split the layout 70/30 (or there abouts) horizontally and load
# Optionally, hide the status and input lines on chanmon
#
# /window splith 70 --> change to chanmon buffer
# /set weechat.bar.status.conditions "${window.buffer.full_name} != perl.chanmon"
# /set weechat.bar.input.conditions "${window.buffer.full_name} != perl.chanmon"
#

# Bugs and feature requests at: https://github.com/KenjiE20/chanmon

# History:
# 2014-08-16, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.5:	-add: clearbar command to clear bar output
#			-add: firstrun output prompt to check the help text for set up hints as they were being missed
#			and update hint for conditions to use eval
#			-change: Make all outputs use the date callback for more accurate timestamps (thanks Germainz)
# 2013-12-04, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.4:	-add: Support for eval style colour codes in time format used for bar output
# 2013-10-10, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.3.3.1:	-fix: Typo in closed buffer warning
# 2013-10-07, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.3.3:	-add: Warning and fixer for accidental buffer closes
# 2013-01-15, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.3.2:	-fix: Let bar output use the string set in weechat's config option
#			-add: github info
#			-change: Ideal set up -> Example set up
# 2012-04-15, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.3.1:	-fix: Colour tags in bar timestamp string, bar error fixes from highmon
# 2012-02-28, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.3:	-feature: Added merge_private option to display private messages (default: off)
# 2010-12-22, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.2:	-change: Use API instead of config to find channel colours, ready for 0.3.4 and 256 colours
# 2010-12-05, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.1.3: -change: /monitor is now /chmonitor to avoid command conflicts (thanks m4v)
#		(/chanmon monitor remains the same)
#		-fix: Add command list to inbuilt help
# 2010-09-30, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.1.2:	-fix: logging config was not correctly toggling back on (thanks to sleo for noticing)
# 2010-09-20, m4v <lambdae2@gmail.com>:
#	v2.1.1:	-fix: chanmon wasn't detecting buffers displayed on more than one window
# 2010-08-27, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.1: -feature: Add 'nchannel' option to alignment to display buffer and name
# 2010-04-25, KenjiE20 <longbow@longbowslair.co.uk>:
#	v2.0:	Release as version 2.0
# 2010-04-24, KenjiE20 <longbow@longbowslair.co.uk>:
#		-fix: No longer using hard-coded detection for ACTION and
#			TOPIC messages. Use config settings for ACTION printing
# 2010-04-15, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.9:	Rewrite for v2.0
#		-feature: /monitor takes arguments
#		-feature: Added /chanclean for config cleanup
#		-feature: Buffer logging option (default: off)
#		-feature: Selectable output (Bar/Buffer (default))
#		-feature: /chanmon is now a command wrapper for all commands
#			/help chanmon gives command help
#			/chanmon help gives config help
#		-code change: Made more subs to shrink the code down in places
#		-fix: Stop chanmon attempting to double load/hook
# 2010-02-10, m4v <lambdae2@gmail.com>:
#	v1.7.1:	-fix: chanmon was leaking infolists, changed how chanmon
#			detects if the buffer is displayed or not.
# 2010-01-25, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.7:	-fixture: Let chanmon be aware of nick_prefix/suffix
#			and allow custom prefix/suffix for chanmon buffer
#			(Defaults to <> if nothing set, and blank if there is)
#		-fix: Make dynamic monitoring aware of multiple windows
#			rather than just the active buffer
#		(Thanks to m4v for these)
# 2009-09-07, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.6:	-feature: colored buffer names
#		-change: chanmon version sync
# 2009-09-05, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.5:	-fix: disable buffer highlight
# 2009-09-02, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.4.1	-change: Stop unsightly text block on '/help'
# 2009-08-10, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.4:	-feature: In-client help added
#		-fix: Added missing help entries
#			Fix remaining ugly vars
# 2009-07-09, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.3.3	-fix: highlight on the channel monitor when someone /me highlights
# 2009-07-04, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.3.2	-fix: use new away_info tag instead of ugly regexp for away detection
#		-code: cleanup old raw callback arguement variables to nice neat named ones
# 2009-07-04, KenjiE20 <longbow@longbowslair.co.uk>:
#	v.1.3.1	-feature(tte): Hide /away messages by default, change 'show_aways' to get them back
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
#	v1.1:	-feature: Dynamic Channel Monitoring,
#			don't display messages from active channel buffer
#			defaults to Disabled
#			Thanks to 'sjohnson' for the idea
#		-fix: don't set config entries for non-channels
#		-fix: don't assume all channels are #
# 2009-06-12, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0.1:	-fix: glitch with tabs in IRC messages
# 2009-06-10, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0:	Initial Public Release

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

@bar_lines = ();
@bar_lines_time = ();
# Replicate info earlier for in-client help
$chanmonhelp = weechat::color("bold")."/chanmon [help] | [monitor [channel [server]]] | [dynmon] | [clean default|orphan|all] | clearbar".weechat::color("-bold")."
Command wrapper for chanmon commands

".weechat::color("bold")."/chmonitor [channel] [server]".weechat::color("-bold")." is used to toggle a channel monitoring on and off, this
 can be used in the channel buffer for the channel you wish to toggle, or be given with arguments e.g. /monitor #weechat freenode

".weechat::color("bold")."/dynmon".weechat::color("-bold")." is used to toggle 'Dynamic Channel Monitoring' on and off, this will automagically stop monitoring the current active buffer, without affecting regular settings (Default is off)

".weechat::color("bold")."/chanclean".weechat::color("-bold")." default|orphan|all will clean the config section of default 'on' entries, channels you are no longer joined, or both

".weechat::color("bold")."/chanmon clearbar".weechat::color("-bold")." will clear the contents of chanmon's bar output

".weechat::color("bold")."/set plugins.var.perl.chanmon.alignment".weechat::color("-bold")."
 The config setting \"alignment\" can be changed to;
 \"channel\", \"schannel\", \"nchannel\", \"channel,nick\", \"schannel,nick\", \"nchannel,nick\"
 to change how the monitor appears
 The 'channel'  value will show: \"#weechat\"
 The 'schannel' value will show: \"6\"
 The 'nchannel' value will show: \"6:#weechat\"

".weechat::color("bold")."/set plugins.var.perl.chanmon.short_names".weechat::color("-bold")."
 Setting this to 'on' will trim the network name from chanmon, ala buffers.pl

".weechat::color("bold")."/set plugins.var.perl.chanmon.merge_private".weechat::color("-bold")."
 Setting this to 'on' will merge private messages to chanmon's display

".weechat::color("bold")."/set plugins.var.perl.chanmon.color_buf".weechat::color("-bold")."
 This turns colored buffer names on or off, you can also set a single fixed color by using a weechat color name.
 This ".weechat::color("bold")."must".weechat::color("-bold")." be a valid color name, or weechat will likely do unexpected things :)

".weechat::color("bold")."/set plugins.var.perl.chanmon.show_aways".weechat::color("-bold")."
 Toggles showing the Weechat away messages

".weechat::color("bold")."/set plugins.var.perl.chanmon.logging".weechat::color("-bold")."
 Toggles logging status for chanmon buffer (default: off)

".weechat::color("bold")."/set plugins.var.perl.chanmon.output".weechat::color("-bold")."
 Changes where output method of chanmon; takes either \"bar\" or \"buffer\" (default; buffer)
".weechat::color("bold")."/set plugins.var.perl.chanmon.bar_lines".weechat::color("-bold")."
 Changes the amount of lines the output bar will hold.
 (Only appears once output has been set to bar, defaults to 10)

".weechat::color("bold")."/set plugins.var.perl.chanmon.nick_prefix".weechat::color("-bold")."
".weechat::color("bold")."/set plugins.var.perl.chanmon.nick_suffix".weechat::color("-bold")."
 Sets the prefix and suffix chars in the chanmon buffer
 (Defaults to <> if nothing set, and blank if there is)

".weechat::color("bold")."servername.#channel".weechat::color("-bold")."
 servername is the internal name for the server (set when you use /server add)
 #channel is the channel name, (where # is whatever channel type that channel happens to be)

".weechat::color("bold")."Example set up:".weechat::color("-bold")."
Split the layout 70/30 (or there abouts) horizontally and load
Optionally, hide the status and input lines on chanmon

".weechat::color("bold")."/window splith 70".weechat::color("-bold")." --> change to chanmon buffer
".weechat::color("bold")."/set weechat.bar.status.conditions \"\${window.buffer.full_name} != perl.chanmon\"".weechat::color("-bold")."
".weechat::color("bold")."/set weechat.bar.input.conditions \"\${window.buffer.full_name} != perl.chanmon\"".weechat::color("-bold");
# Print verbose help
sub print_help
{
	weechat::print("", "\t".weechat::color("bold")."Chanmon Help".weechat::color("-bold")."\n\n");
	weechat::print("", "\t".$chanmonhelp);
	return weechat::WEECHAT_RC_OK;
}

# Bar item build
sub chanmon_bar_build
{
	# Get max lines
	$max_lines = weechat::config_get_plugin("bar_lines");
	$max_lines = $max_lines ? $max_lines : 10;
	$str = '';
	$align_num = 0;
	$count = 0;
	# Keep lines within max
	while ($#bar_lines > $max_lines)
	{
		shift(@bar_lines);
		shift(@bar_lines_time);
	}
	# So long as we have some lines, build a string
	if (@bar_lines)
	{
		# Build loop
		$sep = " ".weechat::config_string(weechat::config_get("weechat.look.prefix_suffix"))." ";
		foreach(@bar_lines)
		{
			# Find max align needed
			$prefix_num = (index(weechat::string_remove_color($_, ""), $sep));
			$align_num = $prefix_num if ($prefix_num > $align_num);
		}
		foreach(@bar_lines)
		{
			# Get align for this line
			$prefix_num = (index(weechat::string_remove_color($_, ""), $sep));

			# Make string
			$str = $str.$bar_lines_time[$count]." ".(" " x ($align_num - $prefix_num)).$_."\n";
			# Increment count for sync with time list
			$count++;
		}
	}
	return $str;
}

# Make a new bar
sub chanmon_bar_open
{
	# Make the bar item
	weechat::bar_item_new("chanmon", "chanmon_bar_build", "");

	$chanmon_bar = weechat::bar_new ("chanmon", "off", 100, "root", "", "bottom", "vertical", "vertical", 0, 0, "default", "cyan", "default", "on", "chanmon");

	return weechat::WEECHAT_RC_OK;
}
# Close bar
sub chanmon_bar_close
{
	# Find if bar exists
	$chanmon_bar = weechat::bar_search("chanmon");
	# If is does, close it
	if ($chanmon_bar ne "")
	{
		weechat::bar_remove($chanmon_bar);
	}

	# Find if bar item exists
	$chanmon_bar_item = weechat::bar_item_search("chanmon_bar");
	# If is does, close it
	if ($chanmon_bar_item ne "")
	{
		weechat::bar_remove($chanmon_bar_item);
	}

	@bar_lines = ();
	return weechat::WEECHAT_RC_OK;
}

# Make a new buffer
sub chanmon_buffer_open
{
	# Search for pre-existing buffer
	$chanmon_buffer = weechat::buffer_search("perl", "chanmon");

	# Make a new buffer
	if ($chanmon_buffer eq "")
	{
		$chanmon_buffer = weechat::buffer_new("chanmon", "chanmon_buffer_input", "", "chanmon_buffer_close", "");
	}

	# Turn off notify, highlights
	if ($chanmon_buffer ne "")
	{
		weechat::buffer_set($chanmon_buffer, "notify", "0");
		weechat::buffer_set($chanmon_buffer, "highlight_words", "-");
		weechat::buffer_set($chanmon_buffer, "title", "Channel Monitor");
		# Set no_log
		if (weechat::config_get_plugin("logging") eq "off")
		{
			weechat::buffer_set($chanmon_buffer, "localvar_set_no_log", "1");
		}
	}
	return weechat::WEECHAT_RC_OK;
}
# Buffer input has no action
sub chanmon_buffer_input
{
	return weechat::WEECHAT_RC_OK;
}
# Close up
sub chanmon_buffer_close
{
	$chanmon_buffer = "";
	# If user hasn't changed output style warn user
	if (weechat::config_get_plugin("output") eq "buffer")
	{
		weechat::print("", "\tChanmon buffer has been closed but output is still set to buffer, unusual results may occur. To recreate the buffer use ".weechat::color("bold")."/chanmon fix".weechat::color("-bold"));
	}
	return weechat::WEECHAT_RC_OK;
}

# Chanmon command wrapper
sub chanmon_command_cb
{
	$data = $_[0];
	$buffer = $_[1];
	$args = $_[2];
	my $cmd = '';
	my $arg = '';

	if ($args ne "")
	{
		# Split argument up
		@arg_array = split(/ /,$args);
		# Take first as command
		$cmd = shift(@arg_array);
		# Rebuild string to pass to subs
		if (@arg_array)
		{
			$arg = join(" ", @arg_array);
		}
	}

	# Help command
	if ($cmd eq "" || $cmd eq "help")
	{
		print_help();
	}
	# /monitor command
	elsif ($cmd eq "monitor")
	{
		chanmon_toggle($data, $buffer, $arg);
	}
	# /dynmon command
	elsif ($cmd eq "dynmon")
	{
		chanmon_dyn_toggle();
	}
	# /chanclean command
	elsif ($cmd eq "clean")
	{
		chanmon_config_clean($data, $buffer, $arg);
	}
	# clearbar command
	elsif ($cmd eq "clearbar")
	{
		if (weechat::config_get_plugin("output") eq "bar")
		{
			@bar_lines = ();
			weechat::bar_item_update("chanmon");
		}
	}
	# Fix closed buffer
	elsif ($cmd eq "fix")
	{
		if (weechat::config_get_plugin("output") eq "buffer" && $chanmon_buffer eq "")
		{
			chanmon_buffer_open();
		}
	}
	return weechat::WEECHAT_RC_OK;
}

# Clean up config entries
sub chanmon_config_clean
{
	$data = $_[0];
	$buffer = $_[1];
	$args = $_[2];

	# Don't do anything if bad option given
	if ($args ne "default" && $args ne "orphan"  && $args ne "all")
	{
		weechat::print("", "\tchanmon.pl: Unknown option");
		return weechat::WEECHAT_RC_OK;
	}

	@chans = ();
	# Load an infolist of chanmon options
	$infolist = weechat::infolist_get("option", "", "*chanmon*");
	while (weechat::infolist_next($infolist))
	{
		$name = weechat::infolist_string($infolist, "option_name");
		$name =~ s/perl\.chanmon\.(\w*)\.([#&\+!])(.*)/$1.$2$3/;
		if ($name =~ /^(.*)\.([#&\+!])(.*)$/)
		{
			$action = 0;
			# Clean up all 'on's
			if ($args eq "default" || $args eq "all")
			{
				# If value in config is "on"
				if (weechat::config_get_plugin($name) eq "on")
				{
					# Unset and if successful flag as changed
					$rc = weechat::config_unset_plugin($name);
					if ($rc eq weechat::WEECHAT_CONFIG_OPTION_UNSET_OK_REMOVED)
					{
						$action = 1;
					}
				}
			}
			# Clean non joined
			if ($args eq "orphan" || $args eq "all")
			{
				# If we can't find the buffer for this entry
				if (weechat::buffer_search("irc", $name) eq "")
				{
					# Unset and if successful flag as changed
					$rc = weechat::config_unset_plugin($name);
					if ($rc eq weechat::WEECHAT_CONFIG_OPTION_UNSET_OK_REMOVED)
					{
						$action = 1;
					}
				}
			}
			# Add changed entry names to list
			push (@chans, $name) if ($action);
		}
	}
	weechat::infolist_free($infolist);
	# If channels were cleaned from config
	if (@chans)
	{
		# If only one entry
		if (@chans == 1)
		{
			$str = "\tchanmon.pl: Cleaned ".@chans." entry from the config:";
		}
		else
		{
			$str = "\tchanmon.pl: Cleaned ".@chans." entries from the config:";
		}
		# Build a list of channels
		foreach(@chans)
		{
			$str = $str." ".$_;
		}
		# Print what happened
		weechat::print("",$str);
	}
	# Config seemed to be clean
	else
	{
		weechat::print("", "\tchanmon.pl: No entries removed");
	}
	return weechat::WEECHAT_RC_OK;
}

# Check config elements
sub chanmon_config_init
{
	# First run default
	if (!(weechat::config_is_set_plugin ("first_run")))
	{
		if (weechat::config_get_plugin("first_run") ne "true")
		{
			weechat::print("", "\tThis appears to be the first time chanmon has been run. For help and common set up hints see /chanmon help");
			weechat::config_set_plugin("first_run", "true");
		}
	}
	# Alignment default
	if (!(weechat::config_is_set_plugin ("alignment")))
	{
		weechat::config_set_plugin("alignment", "channel");
	}
	if (weechat::config_get_plugin("alignment") eq "")
	{
		weechat::config_set_plugin("alignment", "none");
	}

	# Dynmon default
	if (!(weechat::config_is_set_plugin ("dynamic")))
	{
		weechat::config_set_plugin("dynamic", "off");
	}

	# Short name default
	if (!(weechat::config_is_set_plugin ("short_names")))
	{
		weechat::config_set_plugin("short_names", "off");
	}

	# Coloured names default
	if (!(weechat::config_is_set_plugin ("color_buf")))
	{
		weechat::config_set_plugin("color_buf", "on");
	}

	# Away message default
	if (!(weechat::config_is_set_plugin ("show_aways")))
	{
		weechat::config_set_plugin("show_aways", "off");
	}

	# chanmon log default
	if (!(weechat::config_is_set_plugin ("logging")))
	{
		weechat::config_set_plugin("logging", "off");
	}

	# Output default
	if (!(weechat::config_is_set_plugin ("output")))
	{
		weechat::config_set_plugin("output", "buffer");
	}

	# Private message merging
	if (!(weechat::config_is_set_plugin ("merge_private")))
	{
		weechat::config_set_plugin("merge_private", "off");
	}

	# Check for exisiting prefix/suffix chars, and setup accordingly
	$prefix = weechat::config_get("irc.look.nick_prefix");
	$prefix = weechat::config_string($prefix);
	$suffix = weechat::config_get("irc.look.nick_suffix");
	$suffix = weechat::config_string($suffix);

	if (!(weechat::config_is_set_plugin("nick_prefix")))
	{
		if ($prefix eq "" && $suffix eq "")
		{
			weechat::config_set_plugin("nick_prefix", "<");
		}
		else
		{
			weechat::config_set_plugin("nick_prefix", "");
		}
	}

	if (!(weechat::config_is_set_plugin("nick_suffix")))
	{
		if ($prefix eq "" && $suffix eq "")
		{
			weechat::config_set_plugin("nick_suffix", ">");
		}
		else
		{
			weechat::config_set_plugin("nick_suffix", "");
		}
	}
}

# Get config updates
sub chanmon_config_cb
{
	$point = $_[0];
	$name = $_[1];
	$value = $_[2];

	$name =~ s/^plugins\.var\.perl\.chanmon\.//;

	# Set logging on buffer
	if ($name eq "logging")
	{
		# Search for pre-existing buffer
		$chanmon_buffer = weechat::buffer_search("perl", "chanmon");
		if ($value eq "off")
		{
			weechat::buffer_set($chanmon_buffer, "localvar_set_no_log", "1");
		}
		else
		{
			weechat::buffer_set($chanmon_buffer, "localvar_del_no_log", "");
		}
	}
	# Output changer
	elsif ($name eq "output")
	{
		if ($value eq "bar")
		{
			# Search for pre-existing buffer
			$chanmon_buffer = weechat::buffer_search("perl", "chanmon");
			# Close if it exists
			if ($chanmon_buffer ne "")
			{
				weechat::buffer_close($chanmon_buffer)
			}

			# Output bar lines default
			if (!(weechat::config_is_set_plugin ("bar_lines")))
			{
				weechat::config_set_plugin("bar_lines", "10");
			}
			# Make a bar if doesn't exist
			chanmon_bar_open();
		}
		elsif ($value eq "buffer")
		{
			# If a bar exists, close it
			chanmon_bar_close();
			# Open buffer
			chanmon_buffer_open();
		}

	}
	elsif ($name eq "weechat.look.prefix_suffix")
	{
		if (weechat::config_get_plugin("output") eq "bar")
		{
			@bar_lines = ();
			weechat::print("", "\tchanmon: weechat.look.prefix_suffix changed, clearing chanmon bar");
			weechat::bar_item_update("chanmon");
		}
	}
	return weechat::WEECHAT_RC_OK;
}

# Toggle dynamic monitoring on/off
sub chanmon_dyn_toggle
{
	if (weechat::config_get_plugin("dynamic") eq "off")
	{
		weechat::config_set_plugin("dynamic", "on");
		chanmon_print("Dynamic Channel Monitoring Enabled");
		return weechat::WEECHAT_RC_OK;
	}
	elsif (weechat::config_get_plugin("dynamic") eq "on")
	{
		weechat::config_set_plugin("dynamic", "off");
		chanmon_print("Dynamic Channel Monitoring Disabled");
		return weechat::WEECHAT_RC_OK;
	}
}

# Set up weechat hooks / commands
sub chanmon_hook
{
	weechat::hook_print("", "", "", 0, "chanmon_new_message", "");
	weechat::hook_command("chmonitor", "Toggles monitoring for a channel", "[channel [server]]", " channel: What channel to toggle monitoring for\n  server: Internal server name, if channel is on more than one server", "%(irc_channels) %(irc_servers)", "chanmon_toggle", "");
	weechat::hook_command("dynmon", "Toggles 'dynamic' monitoring (auto-disable monitoring for current channel)", "", "", "", "chanmon_dyn_toggle", "");
	weechat::hook_command("chanclean", "Chanmon config clean up", "default|orphan|all", " default: Cleans all config entries with the default \"on\" value\n  orphan: Cleans all config entries for channels you aren't currently joined\n     all: Does both defaults and orphan", "default|orphan|all", "chanmon_config_clean", "");

	weechat::hook_command("chanmon", "Chanmon help", "[help] | [monitor [channel [server]]] | [dynmon] | [clean default|orphan|all] | clearbar", "    help: Print help for chanmon\n monitor: Toggles monitoring for a channel (/chmonitor)\n  dynmon: Toggles 'dynamic' monitoring (auto-disable monitoring for current channel) (/dynmon)\n   clean: Chanmon config clean up (/chanclean)\nclearbar: Clear Chanmon bar", "help || monitor %(irc_channels) %(irc_servers) || dynmon || clean default|orphan|all || clearbar", "chanmon_command_cb", "");

	weechat::hook_config("plugins.var.perl.chanmon.*", "chanmon_config_cb", "");
	weechat::hook_config("weechat.look.prefix_suffix", "chanmon_config_cb", "");
}

# Main body, Callback for hook_print
sub chanmon_new_message
{
	my $net = "";
	my $chan = "";
	my $nick = "";
	my $outstr = "";
	my $window_displayed = "";
	my $dyncheck = "0";

#	DEBUG point
#	$string = "\t"."0: ".$_[0]." 1: ".$_[1]." 2: ".$_[2]." 3: ".$_[3]." 4: ".$_[4]." 5: ".$_[5]." 6: ".$_[6]." 7: ".$_[7];
#	weechat::print("", "\t".$string);

	$cb_datap = $_[0];
	$cb_bufferp = $_[1];
	$cb_date = $_[2];
	$cb_tags = $_[3];
	$cb_disp = $_[4];
	$cb_high = $_[5];
	$cb_prefix = $_[6];
	$cb_msg = $_[7];

	# Only work on messages and topic notices
	if ($cb_tags =~ /irc_privmsg/ || $cb_tags =~ /irc_topic/)
	{
		# Check buffer name is an IRC channel or private message when enabled
		$bufname = weechat::buffer_get_string($cb_bufferp, 'name');
		if ($bufname =~ /(.*)\.([#&\+!])(.*)/ || (weechat::config_get_plugin("merge_private") eq "on" && $cb_tags =~ /notify_private/))
		{
			# Are we running on this channel
			if (weechat::config_get_plugin($bufname) ne "off" && $cb_disp eq "1")
			{
				# Are we running dynamically
				if (weechat::config_get_plugin("dynamic") eq "on")
				{
					# Check if this buffer is shown in a window somewhere
					$window_displayed = weechat::buffer_get_integer($cb_bufferp, "num_displayed");
					if ($window_displayed ne 0)
					{
						# Stop running
						return weechat::WEECHAT_RC_OK;
					}
				}

				# Format nick
				# Line isn't action or topic notify
				if (!($cb_tags =~ /irc_action/) && !($cb_tags =~ /irc_topic/))
				{
					# Highlight
					if ($cb_high eq "1")
					{
						# Strip nick colour
						$uncolnick = weechat::string_remove_color($cb_prefix, "");
						# Format nick
						$nick = " ".weechat::config_get_plugin("nick_prefix").weechat::color("chat_highlight").$uncolnick.weechat::color("reset").weechat::config_get_plugin("nick_suffix");
					}
					# Normal line
					else
					{
						# Format nick
						$nick = " ".weechat::config_get_plugin("nick_prefix").$cb_prefix.weechat::color("reset").weechat::config_get_plugin("nick_suffix");
					}
				}
				# Topic line
				elsif ($cb_tags =~ /irc_topic/)
				{

					$nick = " ".$cb_prefix.weechat::color("reset");
				}
				# Action line
				else
				{
					# Highlight
					if ($cb_high eq "1")
					{
						$uncolnick = weechat::string_remove_color($cb_prefix, "");
						$nick = weechat::color("chat_highlight").$uncolnick.weechat::color("reset");
					}
					# Normal line
					else
					{
						$nick = $cb_prefix.weechat::color("reset");
					}
				}
				# Send to output
				chanmon_print ($cb_msg, $cb_bufferp, $nick, $cb_date, $cb_tags);
			}
		}
	}
	# Special outgoing ACTION & away_info catcher
	elsif ($cb_tags eq "" || $cb_tags =~ /away_info/ && weechat::config_get_plugin("show_aways") eq "on" )
	{
		# Check buffer name is an IRC channel or private message when enabled
		$bufname = weechat::buffer_get_string($cb_bufferp, 'name');
		if ($bufname =~ /(.*)\.([#&\+!])(.*)/ || (weechat::config_get_plugin("merge_private") eq "on" && $cb_tags =~ /notify_private/))
		{
			# Are we running dynamically
			if (weechat::config_get_plugin("dynamic") eq "on")
			{
				# Check if this buffer is shown in a window somewhere
				$window_displayed = weechat::buffer_get_integer($cb_bufferp, "num_displayed");
				if ($window_displayed eq 1)
				{
					# Stop running
					return weechat::WEECHAT_RC_OK;
				}
			}

			$net = $1;
			$mynick = weechat::info_get("irc_nick", $net);
			if ($cb_msg =~ $mynick)
			{
				$action_colour = weechat::color(weechat::config_string(weechat::config_get("weechat.color.chat_prefix_action")));
				$action_prefix = weechat::config_string(weechat::config_get("weechat.look.prefix_action"));
				$nick_self_colour = weechat::color(weechat::config_string(weechat::config_get("weechat.color.chat_nick_self")));
				$nick = $action_colour.$action_prefix.$nick_self_colour.$nick.weechat::color("reset");
				# Send to output
				chanmon_print ($cb_msg, $cb_bufferp, $nick, $cb_date, $cb_tags);
			}
		}
	}
	return weechat::WEECHAT_RC_OK;
}

# Output formatter and printer takes (msg bufpointer nick)
sub chanmon_print
{
	$cb_msg = $_[0];
	my $cb_bufferp = $_[1] if ($_[1]);
	my $nick = $_[2] if ($_[2]);
	my $cb_date = $_[3] if ($_[3]);
	my $cb_tags = $_[4] if ($_[4]);

	#Normal channel message
	if ($cb_bufferp && $nick)
	{
		# Format buffer name
		$bufname = format_buffer_name($cb_bufferp);

		# If alignment is #channel | nick msg
		if (weechat::config_get_plugin("alignment") eq "channel")
		{
			$nick =~ s/\s(.*)/$1/;
			# Build string
			$outstr = $bufname."\t".$nick." ".$cb_msg;
		}
		# or if it is channel number | nick msg
		elsif (weechat::config_get_plugin("alignment") eq "schannel")
		{
			$nick =~ s/\s(.*)/$1/;
			# Use channel number instead
			$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').weechat::color("reset");
			# Build string
			$outstr = $bufname."\t".$nick." ".$cb_msg;
		}
		# or if it is number:#channel | nick msg
		elsif (weechat::config_get_plugin("alignment") eq "nchannel")
		{
			$nick =~ s/\s(.*)/$1/;
			# Place channel number in front of formatted name
			$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').":".weechat::color("reset").$bufname;
			# Build string
			$outstr = $bufname."\t".$nick." ".$cb_msg;
		}
		# or if it is #channel nick | msg
		elsif (weechat::config_get_plugin("alignment") eq "channel,nick")
		{
			# Build string
			$outstr = $bufname.":".$nick."\t".$cb_msg;
		}
		# or if it is channel number nick | msg
		elsif (weechat::config_get_plugin("alignment") eq "schannel,nick")
		{
			# Use channel number instead
			$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').weechat::color("reset");
			# Build string
			$outstr = $bufname.":".$nick."\t".$cb_msg;
		}
		# or if it is number:#channel nick | msg
		elsif (weechat::config_get_plugin("alignment") eq "nchannel,nick")
		{
			# Place channel number in front of formatted name
			$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').":".weechat::color("reset").$bufname;
			# Build string
			$outstr = $bufname.":".$nick."\t".$cb_msg;
		}
		# or finally | #channel nick msg
		else
		{
			# Build string
			$outstr = "\t".$bufname.":".$nick." ".$cb_msg;
		}
	}
	# chanmon channel toggle message
	elsif ($cb_bufferp && !$nick)
	{
		# Format buffer name
		$bufname = format_buffer_name($cb_bufferp);

		# If alignment is #channel * | *
		if (weechat::config_get_plugin("alignment") =~ /channel/)
		{
			# If it's actually channel number * | *
			if (weechat::config_get_plugin("alignment") =~ /schannel/)
			{
				# Use channel number instead
				$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').weechat::color("reset");
			}
			# Or if it's actually number:#channel * | *
			if (weechat::config_get_plugin("alignment") =~ /nchannel/)
			{
				# Place channel number in front of formatted name
			$bufname = weechat::color("chat_prefix_buffer").weechat::buffer_get_integer($cb_bufferp, 'number').":".weechat::color("reset").$bufname;
			}
			$outstr = $bufname."\t".$cb_msg;
		}
		# or if alignment is | *
		else
		{
			$outstr = $bufname.": ".$cb_msg;
		}
	}
	# chanmon dynmon
	elsif (!$cb_bufferp && !$nick)
	{
		$outstr = "\t".$cb_msg;
	}

	# Send string to buffer
	if (weechat::config_get_plugin("output") eq "buffer")
	{
		# Search for and confirm buffer
		$chanmon_buffer = weechat::buffer_search("perl", "chanmon");
		# Print
		if ($cb_date)
		{
			weechat::print_date_tags($chanmon_buffer, $cb_date, $cb_tags, $outstr);
		}
		else
		{
			weechat::print($chanmon_buffer, $outstr);
		}
	}
	elsif (weechat::config_get_plugin("output") eq "bar")
	{
		# Add time string
		use POSIX qw(strftime);
		if ($cb_date)
		{
			$time = strftime(weechat::config_string(weechat::config_get("weechat.look.buffer_time_format")), localtime($cb_date));
		}
		else
		{
			$time = strftime(weechat::config_string(weechat::config_get("weechat.look.buffer_time_format")), localtime);
		}
		# Colourise
		if ($time =~ /\$\{(?:color:)?[\w,]+\}/) # Coloured string
		{
			while ($time =~ /\$\{(?:color:)?([\w,]+)\}/)
			{
				$color = weechat::color($1);
				$time =~ s/\$\{(?:color:)?[\w,]+\}/$color/;
			}
			$time .= weechat::color("reset");
		}
		else # Default string
		{
			$colour = weechat::color(weechat::config_string(weechat::config_get("weechat.color.chat_time_delimiters")));
			$reset = weechat::color("reset");
			$time =~ s/(\d*)(.)(\d*)/$1$colour$2$reset$3/g;
		}
		# Push updates to bar lists
		push (@bar_lines_time, $time);

		# Change tab char
		$delim = " ".weechat::color(weechat::config_string(weechat::config_get("weechat.color.chat_delimiters"))).weechat::config_string(weechat::config_get("weechat.look.prefix_suffix")).weechat::color("reset")." ";
		$outstr =~ s/\t/$delim/;

		push (@bar_lines, $outstr);
		# Trigger update
		weechat::bar_item_update("chanmon");
	}
}

# Start the output display
sub chanmon_start
{
	if (weechat::config_get_plugin("output") eq "buffer")
	{
		chanmon_buffer_open();
	}
	elsif (weechat::config_get_plugin("output") eq "bar")
	{
		chanmon_bar_open();
	}
}

# Takes two optional args (channel server), toggles monitoring on/off
sub chanmon_toggle
{
	$data = $_[0];
	$buffer = $_[1];
	$args = $_[2];

	# Check if we've been told what channel to act on
	if ($args ne "")
	{
		# Split argument up
		@arg_array = split(/ /,$args);
		# Check if a server was given
		if ($arg_array[1])
		{
			# Find matching
			$bufp = weechat::buffer_search("irc", $arg_array[1].".".$arg_array[0]);
		}
		else
		{
			$found_chans = 0;
			# Loop through defined servers
			$infolist = weechat::infolist_get("buffer", "", "");
			while (weechat::infolist_next($infolist))
			{
				# Only interesting in IRC buffers
				if (weechat::infolist_string($infolist, "plugin_name") eq "irc")
				{
					# Find buffers that maych
					$sname = weechat::infolist_string($infolist, "short_name");
					if ($sname eq $arg_array[0])
					{
						$found_chans++;
						$bufp = weechat::infolist_pointer($infolist, "pointer");
					}
				}
			}
			weechat::infolist_free($infolist);
			# If the infolist found more than one channel, halt as we need to know which one
			if ($found_chans > 1)
			{
				weechat::print("", "Channel name is not unique, please define server");
				return weechat::WEECHAT_RC_OK;
			}
		}
		# Something didn't return right
		if ($bufp eq "")
		{
			weechat::print("", "Could not find buffer");
			return weechat::WEECHAT_RC_OK;
		}
	}
	else
	{
		# Get pointer from where we are
		$bufp = weechat::current_buffer();
	}
	# Get buffer name
	$bufname = weechat::buffer_get_string($bufp, 'name');
	# Test if buffer is an IRC channel
	if ($bufname =~ /(.*)\.([#&\+!])(.*)/)
	{
		if (weechat::config_get_plugin($bufname) eq "off")
		{
			# If currently off, set on
			weechat::config_set_plugin($bufname, "on");

			# Send to output formatter
			chanmon_print("Channel Monitoring Enabled", $bufp);
			return weechat::WEECHAT_RC_OK;
		}
		elsif (weechat::config_get_plugin($bufname) eq "on" || weechat::config_get_plugin($bufname) eq "")
		{
			# If currently on, set off
			weechat::config_set_plugin($bufname, "off");

			# Send to output formatter
			chanmon_print("Channel Monitoring Disabled", $bufp);
			return weechat::WEECHAT_RC_OK;
		}
	}
}

# Takes a buffer pointer and returns a formatted name
sub format_buffer_name
{
	$cb_bufferp = $_[0];
	$bufname = weechat::buffer_get_string($cb_bufferp, 'name');

	# Set colour from buffer name
	if (weechat::config_get_plugin("color_buf") eq "on")
	{
		# Determine what colour to use
		$color = weechat::info_get("irc_nick_color", $bufname);
		if (!$color)
		{
			$color = 0;
			@char_array = split(//,$bufname);
			foreach $char (@char_array)
			{
				$color += ord($char);
			}
			$color %= 10;
			$color = sprintf "weechat.color.chat_nick_color%02d", $color+1;
			$color = weechat::config_get($color);
			$color = weechat::config_string($color);
			$color = weechat::color($color);
		}

		# Private message just show network
		if (weechat::config_get_plugin("merge_private") eq "on" && weechat::buffer_get_string($cb_bufferp, "localvar_type") eq "private")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, "localvar_server");
		}
		# Format name to short or 'nicename'
		elsif (weechat::config_get_plugin("short_names") eq "on")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, 'short_name');
		}
		else
		{
			$bufname =~ s/(.*)\.([#&\+!])(.*)/$1$2$3/;
		}

		# Build a coloured string
		$bufname = $color.$bufname.weechat::color("reset");
	}
	# User set colour name
	elsif (weechat::config_get_plugin("color_buf") ne "off")
	{
		# Private message just show network
		if (weechat::config_get_plugin("merge_private") eq "on" && weechat::buffer_get_string($cb_bufferp, "localvar_type") eq "private")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, "localvar_server");
		}
		# Format name to short or 'nicename'
		elsif (weechat::config_get_plugin("short_names") eq "on")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, 'short_name');
		}
		else
		{
			$bufname =~ s/(.*)\.([#&\+!])(.*)/$1$2$3/;
		}

		$color = weechat::config_get_plugin("color_buf");
		$bufname = weechat::color($color).$bufname.weechat::color("reset");
	}
	# Stick with default colour
	else
	{
		# Private message just show network
		if (weechat::config_get_plugin("merge_private") eq "on" && weechat::buffer_get_string($cb_bufferp, "localvar_type") eq "private")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, "localvar_server");
		}
		# Format name to short or 'nicename'
		elsif (weechat::config_get_plugin("short_names") eq "on")
		{
			$bufname = weechat::buffer_get_string($cb_bufferp, 'short_name');
		}
		else
		{
			$bufname =~ s/(.*)\.([#&\+!])(.*)/$1$2$3/;
		}
	}

	return $bufname;
}

# Check result of register, and attempt to behave in a sane manner
if (!weechat::register("chanmon", "KenjiE20", "2.5", "GPL3", "Channel Monitor", "", ""))
{
	# Double load
	weechat::print ("", "\tChanmon is already loaded");
	return weechat::WEECHAT_RC_OK;
}
else
{
	# Start everything
	chanmon_hook();
	chanmon_config_init();
	chanmon_start();
}
