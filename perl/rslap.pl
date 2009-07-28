#
# rslap.pl - Random slap strings for weechat 0.3.0
# Version 1.1
#
# Let's you /slap a nick but with a random string
# Customisable via the 'rslap' file in your config dir
# The rslap file is plain text, with one message per line
# Use '$nick' to denote where a nick should go
#
# Usage:
# /rslap <nick>
# Slaps <nick> with a random slap
# /rslapinfo
# This tells you how many messages there are, and prints them
#
# History:
# 2009-07-28, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.1:	-fix: Make file loading more robust
#		and strip out comments/blank lines
# 2009-07-09, KenjiE20 <longbow@longbowslair.co.uk>:
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

weechat::register("rslap", "KenjiE20", "1.1", "GPL3", "Slap Randomiser", "", "");

$file = weechat::info_get("weechat_dir", "")."/rslap";
my @lines;
rslap_start();

sub rslap_start
{
	if (-r $file)
	{
		weechat::hook_command("rslap", "Slap a nick with a random string", "[nick]", "Nick to slap", "nicks", "rslap", "");
		weechat::hook_command("rslapinfo", "Prints out the current strings /rslap will use", "", "", "", "slap_info", "");

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

sub slap_info
{
	weechat::print ("", "Number of available strings: ".weechat::color("bold").@lines.weechat::color("-bold")."\n");
	foreach (@lines)
	{
		weechat::print ("", "\t  ".$_."\n");
	}
	return weechat::WEECHAT_RC_OK;
}

sub rslap
{
	$buffer = $_[1];
	$nick = $_[2];
	if (weechat::buffer_get_string($buffer, "plugin") eq "irc")
	{
		if ($nick eq "")
		{
			weechat::print ("", weechat::prefix("error")."No nick given");
		}
		else
		{
			$randslap = int(rand(@lines));
			$str = $lines[$randslap];
			$str =~ s/\$nick/$nick/;
			weechat::command ($buffer, "/me ".$str);
		}
	}
	else
	{
		weechat::print ($buffer, weechat::prefix("error")."Must be used on an IRC buffer");
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