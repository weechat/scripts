#
# rslap.pl - Random slap strings for weechat 0.3.0
#
# Let's you /slap a nick but with a random string
# Customisable via the 'rslap' file in your config dir
# The rslap file is plain text, with one message per line
# Use '$nick' to denote where a nick should go
#
# Usage:
# /rslap <nick> [<entry]>
#  Slaps <nick> with a random slap, entry will use that entry
#  number instead of a random one
#
# /rslap_info
#  This tells you how many messages there are, and prints them
#
# /rslap_add <string to add>
# /rslap_remove <entry id>
#  Adds / removes string/id from the available list and attempts
#  to update the rslap file
#
# /set plugins.var.perl.rslap.slapback
#  Sets the slapback, takes "off", "on/random", or "n" where n
#  is a valid entry number

# History:
# 2021-05-05, Sébastien Helleu <flashcode@flashtux.org>:
#       v1.4: add compatibility with XDG directories (WeeChat >= 3.2)
# 2010-12-30, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.3.1	-fix: uninitialised variable error
# 2010-04-25, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.3	-feature: Ability to add/remove entries
#		-feature: Can specify which string /rslap will use
#		-feature: Slapback with specified/random string
# 2009-08-10, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.2:	Correct /help format to match weechat base
# 2009-07-28, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.1:	-fix: Make file loading more robust
#		and strip out comments/blank lines
# 2009-07-09, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0:	Initial Public Release

# Copyright (c) 2009-2010 by KenjiE20 <longbow@longbowslair.co.uk>
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

weechat::register("rslap", "KenjiE20", "1.4", "GPL3", "Slap Randomiser", "", "");

my $weechat_dir = weechat::info_get("weechat_data_dir", "");
$weechat_dir = weechat::info_get("weechat_dir", "") if (!$weechat_dir);
$file = $weechat_dir."/rslap";
my @lines;
$lastrun = 0;
$rslap_slapback_hook = 0;
rslap_start();
rslap_slapback_toggle("","",weechat::config_get_plugin ("slapback"));

sub rslap_start
{
	if (-r $file)
	{
		weechat::hook_command("rslap", "Slap a nick with a random string", "nickname [entry]", "nickname: Nick to slap\n   entry: which entry number to use (/rslap_info for the list)\n\n /set plugins.var.perl.rslap.slapback\n  Sets the slapback, takes \"off\", \"on/random\", or \"n\" where n is a valid entry number", "%(nicks)", "rslap", "");
		weechat::hook_command("rslap_info", "Prints out the current strings /rslap will use", "", "", "", "rslap_info", "");
		weechat::hook_command("rslap_add", "Add a new slap entry", "[slap string]", "", "", "rslap_add", "");
		weechat::hook_command("rslap_remove", "Remove a slap entry", "[entry number]", "", "", "rslap_remove", "");

		weechat::hook_config("plugins.var.perl.rslap.slapback", "rslap_slapback_toggle", "");

		if (!(weechat::config_is_set_plugin ("slapback")))
		{
			weechat::config_set_plugin("slapback", "off");
		}

		open FILE, $file;
		@lines = <FILE>;
		close (FILE);

		foreach (@lines)
		{
			s/^#.*$//;
			chomp;
		}
		@lines = grep /\S/, @lines;
	}
	else
	{
		rslap_make_file();
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap_info
{
	weechat::print ("", "Number of available strings: ".weechat::color("bold").@lines.weechat::color("-bold")."\n");
	$max_align = length(@lines);
	$count = 1;
	foreach (@lines)
	{
		weechat::print ("","\t ".(" " x ($max_align - length($count))).$count.": ".$_."\n");
		$count++;
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap_add
{
	my $text = $_[2] if ($_[2]);
	if ($text)
	{
		push (@lines, $text);
		weechat::print("", "Added entry ".@lines." as: \"".$text."\"");
		rslap_update_file();
		return weechat::WEECHAT_RC_OK;
	}
	else
	{
		return weechat::WEECHAT_RC_OK;
	}
}

sub rslap_remove
{
	my $entry = $_[2] if ($_[2]);
	if ($entry =~ m/^\d+/)
	{
		$entry--;
		if ($lines[$entry])
		{
			$removed = $lines[$entry];
			$lines[$entry] = '';
			@lines = grep /\S/, @lines;
			weechat::print("", "Removed entry ".weechat::color("bold").($entry + 1).weechat::color("-bold")." (".$removed.")");
			rslap_update_file();
			return weechat::WEECHAT_RC_OK;
		}
		else
		{
			weechat::print ("", weechat::prefix("error")."Not a valid entry");
		}
	}
	else
	{
		return weechat::WEECHAT_RC_OK;
	}
}

sub rslap_slapback_toggle
{
	$point = $_[0];
	$name = $_[1];
	$value = $_[2];
	
	if ($value eq "off")
	{
		if ($rslap_slapback_hook)
		{
			weechat::unhook($rslap_slapback_hook);
			$rslap_slapback_hook = 0;
		}
	}
	elsif ($value ne "off")
	{
		if (!$rslap_slapback_hook)
		{
			$rslap_slapback_hook = weechat::hook_print("", "", "", 1, "rslap_slapback_cb", "");
		}
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap
{
	$buffer = $_[1];
	$args = $_[2];
	if (weechat::buffer_get_string($buffer, "plugin") eq "irc")
	{
		($nick, $number) = split(/ /,$args);
		if ($nick eq "")
		{
			weechat::print ("", weechat::prefix("error")."No nick given");
		}
		else
		{
			if (defined $number && $number =~ m/^\d+$/)
			{
				$number--;
				if (!$lines[$number])
				{
					weechat::print ($buffer, weechat::prefix("error")."Not a valid entry");
					return weechat::WEECHAT_RC_OK;
				}
			}
			else
			{
				$number = int(rand(@lines));
			}
			$str = $lines[$number];
			$str =~ s/\$nick/$nick/;
			$lastrun = time;
			weechat::command ($buffer, "/me ".$str);
		}
	}
	else
	{
		weechat::print ($buffer, weechat::prefix("error")."Must be used on an IRC buffer");
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap_slapback_cb
{
	$cb_datap = $_[0];
	$cb_bufferp = $_[1];
	$cb_date = $_[2];
	$cb_tags = $_[3];
	$cb_disp = $_[4];
	$cb_high = $_[5];
	$cb_prefix = $_[6];
	$cb_msg = $_[7];
	
	$bufname = weechat::buffer_get_string($cb_bufferp, 'name');
	# Only do something if a) IRC message b) is an action c) displayed and d) is a channel
	if ($cb_tags =~ /irc_privmsg/ && $cb_tags =~ /irc_action/ && $cb_disp eq "1" && $bufname =~ /.*\.[#&\+!].*/)
	{
		# Anti-recursive
		if ((time - $lastrun) < 10)
		{
			return weechat::WEECHAT_RC_OK;
		}
		# Strip colour
		$cb_msg = weechat::string_remove_color($cb_msg, "");
		# Snip sender from message
		$from_nick = substr($cb_msg, 0, index($cb_msg, " "));
		$cb_msg = substr($cb_msg, length($from_nick));
		# check for our nick and slap in message
		$cur_nick = weechat::buffer_get_string($cb_bufferp, "localvar_nick");
		if ($from_nick ne $cur_nick && $cb_msg =~ /slap/ && $cb_msg =~ /\s$cur_nick(\s|$)/)
		{
			if (weechat::config_get_plugin("slapback") =~ m/^\d+$/)
			{
				rslap("", $cb_bufferp, $from_nick." ".weechat::config_get_plugin("slapback"));
			}
			else
			{
				rslap("", $cb_bufferp, $from_nick);
			}
		}
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap_make_file
{
	weechat::print ("", "Attempting to create default file at: $file");

	open FILE, ">", $file;
 	$defs = "slaps \$nick around a bit with a large trout\n".
 		"gives \$nick a clout round the head with a fresh copy of WeeChat\n".
 		"slaps \$nick with a large smelly trout\n".
 		"breaks out the slapping rod and looks sternly at \$nick\n".
 		"slaps \$nick's bottom and grins cheekily\n".
 		"slaps \$nick a few times\n".
		"slaps \$nick and starts getting carried away\n".
		"would slap \$nick, but is not being violent today\n".
		"gives \$nick a hearty slap\n".
		"finds the closest large object and gives \$nick a slap with it\n".
		"likes slapping people and randomly picks \$nick to slap\n".
		"dusts off a kitchen towel and slaps it at \$nick";
	print FILE $defs;
	close (FILE);
	if (!(-r $file))
	{
		weechat::print ("", weechat::prefix("error")."Problem creating file: $file\n".
		weechat::prefix("error")."Make sure you can write to the location.");
		return weechat::WEECHAT_RC_ERROR;
	}
	else
	{
		weechat::print ("", "File created at: $file successfully");
		rslap_start();
		return weechat::WEECHAT_RC_OK;
	}
}

sub rslap_update_file
{
	$defs = '';
	foreach (@lines)
	{
		$defs = $defs."\n".$_;
	}
	unless(open (FILE, ">", $file))
	{
		weechat::print ("", weechat::prefix("error")."Cannot write to file: $file");
		return weechat::WEECHAT_RC_ERROR;
	}
	print FILE $defs;
	close (FILE);
	return weechat::WEECHAT_RC_OK;
}
