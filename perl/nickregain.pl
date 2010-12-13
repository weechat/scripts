#
# nickregain.pl - Automatically regain your nick when avaiable, for weechat 0.3.0
# Version 1.1.1
#
# Automatically checks every x mins to see if your prefered nicks are available
# and issues either /nick or a custom nickserv command
#
# Usage:
# /nickregain on|off|now|all
# Set regain on or off for a server
# 'now' runs a one time test on current server
# 'all' runs a one time test on all servers
#
# /set plugins.var.perl.nickregain.<servername>_enabled
# This sets whether the nickregain is will run on a server
#
# /set plugins.var.perl.nickregain.<servername>_command
# Setting this will make nickregain issue this command instead of just "/nick <nick>" and override all other methods
# You WILL need to add the '/nick' command to this
# Use $nick to mark the nick, Commands can be separated using ;
# e.g /msg nickserv ghost $nick;/nick $nick;/msg nickserv identify password
# See '/msg nickserv help' for exact syntax
#
# /set plugins.var.perl.nickregain.<servername>_command_delay
# This sets the delay between the server connection and the command being triggered
# Default: 0
#
# /set plugins.var.perl.nickregain.<servername>_delay
# This sets the delay between each /ison check
# Used incase you can't see the old nick quit or nick change
# Default: 60
#
# History:
# 2010-12-13, idl0r:
#	v1.1.1:	-fix: corner case where $config{$name} didn't exist for a disconnecting server
# 2009-04-24, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.1	-feature: Add server_command_delay option to add a delay to server_command
#		-fix: Broken quit/nick change detection
#		-fix: Close off leaking infolists
#		-fix: Hooks unhook properly now
# 2009-10-27, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0.2	-fix: Make ison nicks check quote better, didn't always work
#			Give /nickregain now it's own sub, to trigger ison
#			Let /nickregain work out the server name, rather than assume it was on a server buffer
# 2009-10-22, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0.1	-fix: make infolist loop $name's local vars, so they don't overwrite existing
# 2009-10-19, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0:	Public Release
#		-fix: /ison command was sending /ison /ison nicks
#			Quote the ison nicks check to protect regexp
#			Update settings on connect, fixes initial connected being set off
#		-code: Make creating the $isonnicks var less silly
#
# 2009-10-18, KenjiE20 <longbow@longbowslair.co.uk>:
#	v1.0RC:	Initial Public Release Candidate
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

$helpstr = "  on: Enables regain for current server
 off: Disables regain for current server
 now: Runs regain once for current server
 all: Runs regain once for all servers\n
 ".weechat::color("bold")."/set plugins.var.perl.nickregain.<servername>_command".weechat::color("-bold")."
 Setting this will make nickregain issue this command instead of just \"/nick <nick>\" and override all other methods
 You ".weechat::color("bold")."WILL".weechat::color("-bold")." need to add the '/nick' command to this
 Use \$nick to mark the nick, Commands can be separated using ;
 e.g /msg nickserv ghost \$nick;/nick \$nick;/msg nickserv identify password
 See '/msg nickserv help' for exact syntax\n
 ".weechat::color("bold")."/set plugins.var.perl.nickregain.<servername>_command_delay".weechat::color("-bold")."
 This sets the delay between the server connection and the command being triggered
 Default: ".weechat::color("bold")."0".weechat::color("-bold")."\n
 ".weechat::color("bold")."/set plugins.var.perl.nickregain.<servername>_enabled".weechat::color("-bold")."
 This sets whether the nickregain is will run on a server\n
 ".weechat::color("bold")."/set plugins.var.perl.nickregain.<servername>_delay".weechat::color("-bold")."
 This sets the delay between each /ison check
 Used incase you can't see the old nick quit or nick change
 Default: ".weechat::color("bold")."60".weechat::color("-bold");

weechat::register("nickregain", "KenjiE20", "1.1.1", "GPL3", "Auto Nick Regaining", "", "");

regain_setup();

weechat::hook_signal("irc_server_disconnected", "regain_disconn", "");
weechat::hook_signal("irc_server_connected", "regain_conn", "");

weechat::hook_command("nickregain", "Nickregain script handler", "on|off|now|all", $helpstr, "on|off|now|all", "regain_command", "");
weechat::hook_config("plugins.var.perl.nickregain.*", "regain_setup", "");

# Initialise config variables, and load / update them
sub regain_setup
{
	# Loop through defined servers
	$infolist = weechat::infolist_get("irc_server", "", "");
	while (weechat::infolist_next($infolist))
	{
		# Get server internal name
		my $name = weechat::infolist_string($infolist, "name");
#DEBUG		weechat::print ("", "Checking and creating config entries for $name");

		# If no configs exist, populate
		if (!weechat::config_is_set_plugin($name."_delay"))
		{
			weechat::config_set_plugin($name."_delay", "60");
		}
		if (!weechat::config_is_set_plugin($name."_command"))
		{
			weechat::config_set_plugin($name."_command", "");
		}
		if (!weechat::config_is_set_plugin($name."_command_delay"))
		{
			weechat::config_set_plugin($name."_command_delay", "0");
		}
		if (!weechat::config_is_set_plugin($name."_enabled"))
		{
			weechat::config_set_plugin($name."_enabled", "off");
		}

		# Set / update internal vars
		$config{$name}{'enabled'} = weechat::config_get_plugin($name."_enabled");
		$config{$name}{'command'} = weechat::config_get_plugin($name."_command");
		$config{$name}{'command_delay'} = weechat::config_get_plugin($name."_command_delay");
		$config{$name}{'delay'} = weechat::config_get_plugin($name."_delay");
		$config{$name}{'curnick'} = weechat::infolist_string($infolist, "nick");
		$config{$name}{'nicks'} = weechat::infolist_string($infolist, "nicks");
		$config{$name}{'connected'} = weechat::infolist_integer($infolist, "is_connected");
		# If being ran as update, need to be careful of active var
		# If var isn't already set, then initialise
		if (!exists $config{$name}{'active'})
		{
			$config{$name}{'active'} = 0;
			# Init hook vars
			$nhook{$name} = 0;
			$qhook{$name} = 0;
			$thook{$name} = 0;
			$ihook{$name} = 0;
		}
	}
	weechat::infolist_free($infolist);
}

# Turn timers off when disconnected
sub regain_disconn
{
	$data = $_[0];
	$signal = $_[1];
	$name = $_[2];

	# Are we configured to run on this server
	if ($config{$name} && ($config{$name}{'enabled'} ne 'off'))
	{
		# Unhook any hooks, as they can't do anything now
		if ($nhook{$name})
		{
			weechat::unhook($nhook{$name});
			$nhook{$name} = 0;
		}
		if ($qhook{$name})
		{
			weechat::unhook($qhook{$name});
			$qhook{$name} = 0;
		}
		if ($thook{$name})
		{
			weechat::unhook($thook{$name});
			$thook{$name} = 0;
		}
		if ($ihook{$name})
		{
			weechat::unhook($ihook{$name});
			$ihook{$name} = 0;
		}
	}
#DEBUG	regain_info();
	return weechat::WEECHAT_RC_OK;
}

# When connected, test if nick is primary, regain if command is set or setup regain hooks
sub regain_conn
{
	$data = $_[0];
	$signal = $_[1];
	$name = $_[2];
	
	# Update all settings
	regain_setup();

	# Are we configured to run on this server & check we are connected for manual commands
	if ($config{$name}{'enabled'} ne 'off' && $config{$name}{'connected'})
	{
		# Run nick check, and get primary nick, for command servers
		$nick = regain_nick_prim($name);
		
		# Are we activated for this server
		if ($config{$name}{'active'})
		{
			# Where to print messages
			$bufferp = weechat::info_get("irc_buffer", $name);
#DEBUG			weechat::print($bufferp, "nickregain.pl: Regain active");

			# Does this server have a regain command set
			if ($config{$name}{'command'} ne "")
			{
#DEBUG				weechat::print($bufferp, "nickregain.pl: Server has command, using");
				if ($config{$name}{'command_delay'} ne "0")
				{
					weechat::hook_timer( $config{$name}{'command_delay'} * 1000, 0, 1, "regain_conn_command", $name);
				}
				else
				{
					regain_conn_command($name);
				}
				return weechat::WEECHAT_RC_OK;
			}
			# If not, hook quit catcher, and timer
			else
			{
				weechat::print($bufferp, "nickregain.pl: Server has no regain command set, hooking QUIT, NICK and timer");
				if (!$qhook{$name})
				{
					$qhook{$name} = weechat::hook_signal("$name,irc_in_quit", "regain_quit_nick_cb", "");
				}
				if (!$nhook{$name})
				{
					$nhook{$name} = weechat::hook_signal("$name,irc_in_nick", "regain_quit_nick_cb", "");
				}
				if (!$thook{$name})
				{
					$thook{$name} = weechat::hook_timer( $config{$name}{'delay'} * 1000, 0, 0, "regain_timer_handle", $name);
				}
				if (!$ihook{$name})
				{
					$ihook{$name} = weechat::hook_signal("$name,irc_in_303", "regain_isoncb", "");
				}
			}
		}
	}
	return weechat::WEECHAT_RC_OK;
}

sub regain_conn_command
{
	$name = $_[0];
	$bufferp = weechat::info_get("irc_buffer", $name);
#DEBUG	weechat::print($bufferp, "nickregain.pl: Sending commands");
	#Split command by ;
	undef @cmds;
	@cmds = split(/;/, $config{$name}{'command'});
	
	# Run commands
	foreach (@cmds)
	{
		# Sub config nick
		$_ =~ s/\$nick/$nick/;
		# Send commands
		weechat::command($bufferp, $_);
	}
	# Deactivate and stop
	$config{$name}{'active'} = 0;
	return weechat::WEECHAT_RC_OK;
}

# Sets active variable depending on if nick is primary, and return primary nick for command servers
sub regain_nick_prim
{
	# Get server name
	$name = $_[0];
	
	# Where to print messages
	$bufferp = weechat::info_get("irc_buffer", $name);

	# Update all settings
	regain_setup();
#DEBUG	regain_info();

	# Build a nick array
	undef @nicks;
	@nicks = split(/,/, $config{$name}{'nicks'});

	# Check if we are primary nick
	if ($config{$name}{'curnick'} eq $nicks[0])
	{
#DEBUG		weechat::print($bufferp, "nickregain.pl: Nick primary, setting active to 0");

		# Deactivate
		$config{$name}{'active'} = 0;
		return "";
	}
	else
	{
#DEBUG		weechat::print($bufferp, "nickregain.pl: Nick not primary, entering regain cycle");

		# Activate and return primary nick, for command servers
		$config{$name}{'active'} = 1;
		return $nicks[0];
	}
}

# Callback for NICK or QUIT signals, and test if nick is better
sub regain_quit_nick_cb
{
#	DEBUG point
#	$string = "\t"."0: ".$_[0]." 1: ".$_[1]." 2: ".$_[2];
#	weechat::print("", "\t".$string);
#	0:  1: server,irc_in_QUIT 2: :nick!user@host QUIT :QuitMessage
#	0:  1: server,irc_in_NICK 2: :nick!user@host NICK :NewNick

	$cb_datap = $_[0];
	$cb_signal = $_[1];
	$cb_data = $_[2];
	
	# Update all settings
	regain_setup();

	# Get internal server name from signal
	if ($cb_signal =~ /(.*),irc_in_QUIT/ || $cb_signal =~ /(.*),irc_in_NICK/)
	{
		$server = $1;
	}

	# Double check we are active
	if ($config{$server}{'enabled'} ne 'off' && $config{$server}{'active'})
	{
		# Where to print messages
		$bufferp = weechat::info_get("irc_buffer", $server);

		# Get newly freed nick and nickchange nick
		if ($cb_data =~ /:(.*) QUIT :?(.*)/ || $cb_data =~ /:(.*) NICK :?(.*)/)
		{
			$freenick = weechat::info_get("irc_nick_from_host", $1);
			$nickchanged = weechat::info_get("irc_nick_from_host", $2);

		}

		# Lower casing
		$lcfreenick = $freenick;
		$lcfreenick =~ tr/A-Z/a-z/;
		$lcnickchanged = $nickchanged;
		$lcnickchanged =~ tr/A-Z/a-z/;

		# If nick change was just case changing, then ignore
		if($lcfreenick ne $lcnickchanged)
		{
			# Send nick to tester
			regain_better_nick($server,$freenick);
		}
	}
	return weechat::WEECHAT_RC_OK;
}

# Test a nick to see if it's a more wanted one than current, and regain
sub regain_better_nick
{
	# Get server name
	$name = $_[0];
	# Get nick to test from args (for QUIT/NICK)
	$newnick = $_[1];

	# Where to print messages
	$bufferp = weechat::info_get("irc_buffer", $name);

	# Build a nick array
	undef @nicks;
	@nicks = split(/,/, $config{$name}{'nicks'});

	# Set up lowercase test strings
	$lcnewnick = $newnick;
	$lcnewnick =~ tr/A-Z/a-z/;
	$lccurnick = $config{$name}{'curnick'};
	$lccurnick =~ tr/A-Z/a-z/;
	$lcnicks0 = $nicks[0];
	$lcnicks0 =~ tr/A-Z/a-z/;

	# Loop through desired nicks
	foreach (@nicks)
	{
		# Set up lowercase test string
		$lc_ = $_;
		$lc_ =~ tr/A-Z/a-z/;
		# Check if we've reached the current in use nick and stop
		if ($lc_ eq $lccurnick)
		{
#DEBUG			weechat::print($bufferp, "nickregain.pl: Nick ($newnick) wasn't relevant, or lower than current nick, doing nothing");
			return weechat::WEECHAT_RC_OK;
		}
               	# The nick is one we want
		if ($lcnewnick eq $lc_)
		{
			weechat::print($bufferp, "nickregain.pl: A desired nick ($newnick) quit, regaining");
			weechat::command($bufferp, "/nick $_");
			if ($lcnicks0 eq $lc_)
			{
				weechat::print($bufferp, "nickregain.pl: Regaining primary nick, stopping regain");
				weechat::unhook($nhook{$name});
				$nhook{$name} = 0;
				weechat::unhook($qhook{$name});
				$qhook{$name} = 0;
				weechat::unhook($thook{$name});
				$thook{$name} = 0;
				weechat::unhook($ihook{$name});
				$ihook{$name} = 0;
				$config{$name}{'active'} = 0;
			}
			# No need to test further
			return weechat::WEECHAT_RC_OK;
		}
	}
}

# Each timer cycle, fire off an /ison
sub regain_timer_handle
{
	# Get server name from arg
	$name = $_[0];

	# Where to print messages
	$bufferp = weechat::info_get("irc_buffer", $name);

	# Build a nick array
	undef @nicks;
	@nicks = split(/,/, $config{$name}{'nicks'});

	# Build /ison command
	$isonstr = "/ison";
	foreach (@nicks)
	{
		$isonstr .= " ".$_;
	}

	weechat::print ($bufferp, "nickregain.pl: Issuing $isonstr");
	# Check if nicks are on
	weechat::command ($bufferp, $isonstr);
}

# Catch /ison's and see if a nick we want if free
sub regain_isoncb
{
#	DEBUG point
#	$string = "\t"."0: ".$_[0]." 1: ".$_[1]." 2: ".$_[2];
#	weechat::print("", "\t".$string);
#	0:  1: server,irc_in_303 2: :server.address 303 nick :nickrequest
#	0:  1: server,irc_in_303 2: :server.address 303 nick :

	$cb_datap = $_[0];
	$cb_signal = $_[1];
	$cb_data = $_[2];
	
	# Update all settings
	regain_setup();

	# Get internal server name from signal
	if ($cb_signal =~ /(.*),irc_in_303/)
	{
		$server = $1;
	}

	# Are we configured to run on this server
	if ($config{$server}{'enabled'} ne 'off' && $config{$server}{'active'})
	{
		# Where to print messages
		$bufferp = weechat::info_get("irc_buffer", $server);

		# Build a nick array
		undef @nicks;
		@nicks = split(/,/, $config{$name}{'nicks'});

		# Get list of /ison nicks online
		if ($cb_data =~ /.* 303 .* :(.*)/)
		{
			$isonnicks = " ".$1." ";
			$isonnicks =~ tr/A-Z/a-z/;
		}

		# Set up lowercase test strings
		$lccurnick = $config{$name}{'curnick'};
		$lccurnick =~ tr/A-Z/a-z/;
		$lcnicks0 = $nicks[0];
		$lcnicks0 =~ tr/A-Z/a-z/;

		# Loop through desired nicks
		foreach (@nicks)
		{
			# Set up lowercase test string
			$lc_ = $_;
			$lc_ =~ tr/A-Z/a-z/;

			# Check if we've reached the current in use nick and stop
			if ($lc_ eq $lccurnick)
			{
#DEBUG				weechat::print($bufferp, "nickregain.pl: Nick ($newnick) wasn't relevant, or lower than current nick, doing nothing");
				return weechat::WEECHAT_RC_OK;
			}

			$check = quotemeta($lc_);
                        # Test if current desired nick is in the /ison hash
			if ($isonnicks =~ / $check /)
			{
				# Nick is online, more on
#DEBUG				weechat::print ($bufferp, "nickregain.pl: Nick $_ is online, cannot regain");
			}
			else
			{
				# Desired nick is free, regain
				weechat::print($bufferp, "nickregain.pl: A desired nick ($_) is free, regaining");
				weechat::command($bufferp, "/nick $_");
				if ($lcnicks0 eq $lc_)
				{
					# Unhook everything
					weechat::print($bufferp, "nickregain.pl: Regaining primary nick, stopping regain");
					weechat::unhook($nhook{$name});
					$nhook{$name} = 0;
					weechat::unhook($qhook{$name});
					$qhook{$name} = 0;
					weechat::unhook($thook{$name});
					$thook{$name} = 0;
					weechat::unhook($ihook{$name});
					$ihook{$name} = 0;
					$config{$name}{'active'} = 0;
				}
				# No need to test further
				return weechat::WEECHAT_RC_OK;
			}
		}
	}
}

#nickregain command handler
sub regain_command
{
	$data = $_[0];
	$buffer = $_[1];
	$args = $_[2];

	if ($args eq 'debug')
	{
		regain_info();
	}

	elsif ($args eq 'all')
	{
		# Update all settings
		regain_setup();

		$infolist = weechat::infolist_get("irc_server", "", "");
		while (weechat::infolist_next($infolist))
		{
			# Get server internal name
			my $name = weechat::infolist_string($infolist, "name");

			# Are we configured to run on this server
			if ($config{$name}{'enabled'} ne 'off')
			{
				# Trigger reconnect script
				regain_conn("","",$name);
			}
		}
		weechat::infolist_free($infolist);
		return weechat::WEECHAT_RC_OK;
	}
	
	$plugin = weechat::buffer_get_string ($buffer, "plugin");
	if ($plugin ne 'irc')
	{
		weechat::print ($buffer, weechat::prefix("error")."Must be used on an IRC buffer");
		return weechat::WEECHAT_RC_OK;
	}

	# Get server command was run on
	$name = weechat::buffer_get_string ($buffer, "name");
	@namearr = split(/\./, $name);
	$name = $namearr[0];
	$name = $namearr[1] if ($name eq "server");
	
	if ($args eq 'on')
	{
		weechat::config_set_plugin($name."_enabled", "on");
		regain_conn("","",$name);
		return weechat::WEECHAT_RC_OK;
	}
	elsif ($args eq 'off')
	{
		weechat::config_set_plugin($name."_enabled", "off");

		if ($nhook{$name})
		{
			weechat::unhook($nhook{$name});
			$nhook{$name} = 0;
		}
		if ($qhook{$name})
		{
			weechat::unhook($qhook{$name});
			$qhook{$name} = 0;
		}
		if ($thook{$name})
		{
			weechat::unhook($thook{$name});
			$thook{$name} = 0;
		}
		if ($ihook{$name})
		{
			weechat::unhook($ihook{$name});
			$ihook{$name} = 0;
		}
		return weechat::WEECHAT_RC_OK;
	}
	elsif ($args eq 'now')
	{
		# Are we configured to run on this server
		if ($config{$name}{'enabled'} ne 'off')
		{
			regain_now($name);
		}
		else
		{
			weechat::print ($buffer, weechat::prefix("error")."nickregain not enabled for this server, try \"/nickregain on\" to enable");
		}
		return weechat::WEECHAT_RC_OK;
	}
}

# Manual run of regain, run command, if somehow failed, and trigger an ison
sub regain_now
{
	$name = $_[0];
	
	# Update all settings
	regain_setup();
	
	# Are we configured to run on this server & check we are connected for manual commands
	if ($config{$name}{'enabled'} ne 'off' && $config{$name}{'connected'})
	{
		# Run nick check, and get primary nick, for command servers
		$nick = regain_nick_prim($name);
		
		# Are we activated for this server
		if ($config{$name}{'active'})
		{
			# Where to print messages
			$bufferp = weechat::info_get("irc_buffer", $name);
#DEBUG			weechat::print($bufferp, "nickregain.pl: Regain active");

			# Does this server have a regain command set
			if ($config{$name}{'command'} ne "")
			{
#DEBUG				weechat::print($bufferp, "nickregain.pl: Server has command, using");

				# Split command by ;
				undef @cmds;
				@cmds = split(/;/, $config{$name}{'command'});
				# Run commands
				foreach (@cmds)
				{
					# Sub config nick
					$_ =~ s/\$nick/$nick/;
					# Send commands
					weechat::command($bufferp, $_);
				}
				# Deactivate and stop
				$config{$name}{'active'} = 0;
				return weechat::WEECHAT_RC_OK;
			}
			# If not, run ison
			else
			{
				regain_timer_handle($name);
			}
		}
	}
}

#DEBUG info
sub regain_info
{
	# Loop through defined servers
	$infolist = weechat::infolist_get("irc_server", "", "");
	while (weechat::infolist_next($infolist))
	{
		# Get server internal name
		my $name = weechat::infolist_string($infolist, "name");

		weechat::print("", $name.": Enabled: ".$config{$name}{'enabled'});
		weechat::print("", $name.": Active: ".$config{$name}{'active'});
		weechat::print("", $name.": Command: ".$config{$name}{'command'});
		weechat::print("", $name.": Delay: ".$config{$name}{'delay'});
		weechat::print("", $name.": Current Nick: ".$config{$name}{'curnick'});
		weechat::print("", $name.": Regain Nicks: ".$config{$name}{'nicks'});
	}
	weechat::infolist_free($infolist);
}
