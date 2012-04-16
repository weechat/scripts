#
# Copyright (c) 2010-2012 by Nils Görs <weechatter@arcor.de>
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
# 1.1: fix:  invalid pointer for function infolist_get()
# 1.0: added: allow internal WeeChat command(s)
# v0.9: fixed: mem leak, infolist not removed with infolist_free()
# v0.8: get_color() is now using API function weechat::info_get("irc_nick_color")
# v0.7: quakenet uses different JOIN format (JOIN #channelname instead of JOIN :#channelname)
# v0.6: newsbar support
#     : internal changes (thanks to rettub)
#     : added option 'block_all_buffers'
# v0.5: unhook notify_me() (by rettub)
#     : option for external command (by rettub)
#     : standard command is now only display beep (by rettub)
#     : external command does not freeze weechat anymore
#     : using %N and %C for nick and channel-name
#     : added %S for internal server-name
#     : added whitelist and blacklist (suggested and code used from rettub)
#     : added "block_current_buffer" option
# v0.4: auto completion
# v0.3: $extern_command better readable and typo "toogle" instead of "toggle" removed
# v0.2: variable bug removed
# v0.1: first step (in perl)
#
# This script starts an external progam when a user JOIN a chat you are in.
# possible arguments you can give to the external program:
# %N : for the nick-name
# %C : for the channel-name
# %S : for the internal server-name
#
# /set plugins.var.perl.jnotify.blacklist = "jn-blacklist.txt"
# /set plugins.var.perl.jnotify.whitelist = "jn-whitelist.txt"
# /set plugins.var.perl.jnotify.block_current_buffer = "on"
# /set plugins.var.perl.jnotify.cmd = "echo -en "\a"" 
# /set plugins.var.perl.jnotify.status = "on"
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

use strict;
#### Use your own external command here (do not forget the ";" at the end of line):
my $extern_command = qq(echo -en "\a");

# examples:
# playing a sound
# my $extern_command = qq(play -q $HOME/sounds/hello.wav);
# write to an output file.
# my $extern_command = qq('echo "\"%C\" \"neuer User: %N\"">>/tmp/jnotify-`date +"%Y%m%d"`.log');
# this is my favorite. Displays weechat-logo + channel + nick using system-notification.
# my $extern_command = qq(notify-send -t 9000 -i $HOME/.weechat/120px-Weechat_logo.png "\"%C\" \"neuer User: %N\");

# example to run an internal command:
# /echo -b %C -level 3 %N joined channel


# default values in setup file (~/.weechat/plugins.conf)
my $version		= "1.1";
my $prgname 		= "jnotify";
my $description 	= "starts an internal command or external program if a user or one of your buddies JOIN a channel you are in";
my $status		= "status";
my $default_status	= "on";
my $block_current_buffer= "off";
my $whitelist		= "whitelist";
my $default_whitelist	= "jn-whitelist.txt";
my $blacklist		= "blacklist";
my $default_blacklist	= "jn-blacklist.txt";
my $command_chars       = "/";
my %Hooks               = ();
my %Allowed = ();
my %Disallowed = ();

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

# commands used by jnotify. Type: /help jnotify
weechat::hook_command($prgname, $description,

        "<toggle> | <status> | <block> | <wl> | <wl> | <wl_add> / <wl_del> / <bl_add> / <bl_del> [nick_1 [... nick_n]]", 

        "<toggle>           $prgname between on and off\n".
        "<status>           tells you if $prgname is on or off\n".
        "<block>            toggle the 'block current channel' option on/off\n".
        "<wl>               shows entries in whitelist\n".
        "<bl>               shows entries in blacklist\n".
        "<wl_add> [nick(s)] add nick(s) to the whitelist\n".
        "<wl_del> [nick(s)] delete nick(s) from the whitelist\n".
        "<bl_add> [nick(s)] add nick(s) to the blacklist\n".
        "<bl_del> [nick(s)] delete nick(s) from the blacklist\n".
        "\n".
        "Options:\n".
        "'status'   : status of $prgname (on/off)\n".
        "'whitelist': path/file-name to store a list of nicks, channels and servers you would like to be inform if someone joins.\n".
        "'blacklist': path/file-name to store a list of nicks, channels and servers you would like to ignore.\n".
        "'cmd'      : command that should be executed if a user joins a channel you are in.\n".
        "             '%N' will be replaced with users nick\n".
        "             '%C' will be replaced with name of channel\n".
        "             '%S' will be replaced with the internal server name (use '/server' to see the internal server names)\n".
        "to execute internal weechat command(s) you have to initiate the command line with a weechat command_char (\"/\" or weechat.look.command_chars)\n".
        "'block_current_buffer': if option is 'on', notices will be blocked if user joins the channel you are currently in. Other channels will be displayed.\n".
        "'block_all_buffers'   : if option is 'on', all channels will be blocked and notification will be shown for whitelist entries only.\n".
        "'use_newsbar'         : if option is 'on' and newsbar.pl is running notices will be printed there.\n".
        "\n".
        "Examples:\n".
        "Show entries in whitelist:\n".
        "  /$prgname wl\n".
        "Add entries to blacklist (nick, server, channel):\n".
        "  /$prgname bl_add nickname freenode #weechat\n".
        "Delete entries from whitelist (channel, nick, server):\n".
        "  /$prgname wl_del #weechat nickname freenode\n".
        "Toggle option block_current_buffer (on|off):\n".
        "  /$prgname block\n".
        "Set the variable for the external command (i recommend to use /iset script):\n".
        "  /set plugins.var.perl.$prgname.cmd \"notify-send -t 9000 -i ~/.weechat/some_pic.png \"Channel: %C on Server: %S\" \"new User: %N\"\n".
        "Set the variable for an internal command (script /echo):\n".
        "  /set plugins.var.perl.$prgname.cmd \"/echo -b %C -level 3 %N joined channel\"",
        "toggle|status|block|wl|bl|wl_add|wl_del|bl_add|bl_del", "switch", "");

init();
weechat::hook_config( "plugins.var.perl.$prgname.$status", 'toggled_by_set', "" );

# create hook_signal for IRC command JOIN 
hook() if (weechat::config_get_plugin($status) eq "on");

# return 0 on error
sub hook{
	$Hooks{notify_me} = weechat::hook_signal("*,irc_in_join", "notify_me", ""); # (servername, signal, script command, arguments)
		if ($Hooks{notify_me} eq '')
		{
			weechat::print("","ERROR: can't enable $prgname, hook failed ");
			return 0;
		}

	return 1;
}
sub unhook{
	weechat::unhook($Hooks{notify_me}) if %Hooks;
	%Hooks = ();
}

sub _notify {
    my ( $server_name, $newnick, $channelname ) = @_;

    if ( weechat::config_get_plugin("use_newsbar") eq "on" and newsbar() ) {	# option "use_newsbar" is on and newsbar is running!
        info2newsbar( 'lightgreen', '[JNOTIFY]', $server_name, $newnick, $channelname );
    } else {
        my $external_command = weechat::config_get_plugin('cmd');		# get external command (user settings)
        $external_command =~ s/%C/$channelname/;				# replace string '%C' with $channelname
        $external_command =~ s/%N/$newnick/;					# replace string '%N' with $newnick
        $external_command =~ s/%S/$server_name/;				# replace string '%S' with $server_name

        my $command_char = substr($external_command,0,1);                       # get first char of external command.

        if ( index($command_chars,$command_char) == -1) {
          system( $external_command . "&" );                                    # start external program
        }else{
          weechat::command("",$external_command);                               # start internalt command
        }
    }
}

sub notify_me {
    my ( undef, $buffer, $args ) = @_;						# save callback from hook_signal

    my $mynick = weechat::info_get( "irc_nick", split( /,/, $buffer ) );	# get current nick on a server
    my $newnick = weechat::info_get( "irc_nick_from_host", $args );		# get nickname from new user
    my ($channelname) = ( $args =~ m!.*JOIN (.*)! );				# extract channel name from hook_signal
    ($channelname)  = ($channelname =~ m!.*:(.*)!) if ($channelname =~ m!.*:(.*)!); # ":" in channelname?
    my ($server_name) = split( /,/, $buffer );					# extract internal server name from hook_signal

    return weechat::WEECHAT_RC_OK if ( $mynick eq $newnick );			# did i join the channel?

    # If user setting "block_current_buffer" is "on"
    if ( weechat::config_get_plugin("block_current_buffer") eq "on" ) {
        return weechat::WEECHAT_RC_OK if ( weechat::buffer_get_string( weechat::current_buffer(), "short_name" ) eq $channelname );
    }

    if ( exists $Allowed{$newnick} or exists $Allowed{$channelname} or exists $Allowed{$server_name} ) {          # User or Channel or Buffer in Whitelist?
        _notify( $server_name, $newnick, $channelname );
        return weechat::WEECHAT_RC_OK;
    } elsif (
        ( scalar keys %Allowed ) == 0                                                                             # whitelist empty?
        or exists $Disallowed{$newnick} or exists $Disallowed{$channelname} or exists $Disallowed{$server_name}   # User, Channel or Server in Blacklist?
      )
    {
        return weechat::WEECHAT_RC_OK;
    }

    if ( weechat::config_get_plugin("block_all_buffers") eq "off" ) {
      _notify( $server_name, $newnick, $channelname );
    }

    return weechat::WEECHAT_RC_OK;
}

sub toggled_by_set{
	my $value = $_[2];

        $command_chars = weechat::config_string( weechat::config_get("weechat.look.command_chars") ) . "/";

	if ($value ne 'on')
	{
		weechat::config_set_plugin($status, "off")	unless ($value eq 'off') ;
		if (defined $Hooks{notify_me}) {
			weechat::print('',"$prgname disabled value: $value");
			unhook();
		}
	}
	else
	{
		if (not defined $Hooks{notify_me}) {
			weechat::print("","$prgname enabled");
			weechat::config_set_plugin($status, "off")
				unless  hook();									# fall back to 'off' if hook fails
						}
						}
						return weechat::WEECHAT_RC_OK;
						}

sub switch{
						my ($getargs) = ($_[2]);
						my $jnotify = weechat::config_get_plugin($status);		# get value from jnotify
						my $block_current_stat = weechat::config_get_plugin("block_current_buffer");

						if ($getargs eq $status or "")
						{
						weechat::print("","Status of $prgname is         : $jnotify");	# print status of jnotify
						weechat::print("","blocking of current buffer is: $block_current_stat");
						return weechat::WEECHAT_RC_OK;
						}

						if ($getargs eq "toggle"){
						if ($jnotify eq "on")
						{
							weechat::config_set_plugin($status, "off");
						}
						else
						{
							weechat::config_set_plugin($status, "on");
						}
						return weechat::WEECHAT_RC_OK;
						}

						if ($getargs eq "block"){
							if ($block_current_stat eq "on")
							{
								weechat::config_set_plugin("block_current_buffer", "off");
							}
							else
							{
								weechat::config_set_plugin("block_current_buffer", "on");
							}
							return weechat::WEECHAT_RC_OK;
						}

						if ($getargs eq "wl")
						{
							list_show( "whitelist", \%Allowed);
							return weechat::WEECHAT_RC_OK;
						}
						if ($getargs eq "bl")
						{
							list_show( "blacklist", \%Disallowed);
							return weechat::WEECHAT_RC_OK;
						}
						else
						{
							my ( $cmd, $arg ) = ( $getargs =~ /(.*?)\s+(.*)/ );			# cut cmd from nicks
								$cmd = $getargs unless $cmd;
# check cmd "whitelist add/del" and "blacklist add/del"
							if ($cmd eq "wl_add")
							{
								_add("wl_add",$arg);
							}
							if ($cmd eq "wl_del")
							{
								_del("wl_del",$arg);
							}
							if ($cmd eq "bl_add")
							{
								_add("bl_add",$arg);
							}
							if ($cmd eq "bl_del")
							{
								_del("bl_del",$arg);
							}
						}
}

# whitelist and blacklist reader and saver (routines from rettubs query_blocker)
sub whitelist_save{
	list_save( "whitelist", \%Allowed, "write whitelist" );
}
sub blacklist_save{
	list_save( "blacklist", \%Disallowed, "write blacklist" );
}
sub list_save {
	my ( $list, $hash_ref, $err_msg ) = @_;
	my $file = weechat::config_get_plugin($list);
	open( LIST, ">", $file ) || DEBUG("$err_msg: $!");
	print LIST "$_\n" foreach ( sort { "\L$a" cmp "\L$b" } keys %$hash_ref );
	close LIST;
}
sub list_read{
	my $list     = shift;
	my $hash_ref = shift;
	my $file    = weechat::config_get_plugin($list);

	return unless -e $file;

	open( LIST, "<", $file ) || DEBUG("$file: $!");
	while (<LIST>) {
		chomp;
		$hash_ref->{$_} = 1 if length $_;
	}
	close LIST;
}
sub list_show{
	my ( $list, $hash_ref ) = @_;

	weechat::print( "", "$prgname: $list" );
	if ( ( my $n = keys %$hash_ref ) eq "0" ) {
		weechat::print( "", "     list is empty" );
		return;
	}

	foreach ( sort { "\L$a" cmp "\L$b" } keys %$hash_ref ) {
		weechat::print( "", "     " . $_ );
	}
}
# add and delete nicks from white and blacklist
sub _add{
	my ($cmd,$args) = ($_[0],$_[1]);

	if (defined $args) {
		foreach ( split( / +/, $args ) ) {
			if ($cmd eq "wl_add")
			{
				$Allowed{$_} = 1;
				whitelist_save();
			}
			elsif ($cmd eq "bl_add")
			{
				$Disallowed{$_} = 1;
				blacklist_save();
			}
		}
	}
	else{
		weechat::print("", "$prgname : There is no nick to be added.");
	}
}
sub _del{
	my ($cmd,$args) = ($_[0],$_[1]);
	if (defined $args) {
		foreach ( split( / +/, $args ) ) {
			if ($cmd eq "wl_del" and exists $Allowed{$_})
			{
				$Allowed{$_} = 1;
				delete $Allowed{$_};
				weechat::print("", "$prgname: Nick ". get_color($_) . $_ . weechat::color("reset") . " removed from whitelist.");
				whitelist_save();
			}elsif ($cmd eq "wl_del") {
				weechat::print("", "$prgname: Nick " . get_color($_) .  $_ . weechat::color("reset") . " not in whitelist. Nothing removed.");
			}

			if ($cmd eq "bl_del" and exists $Disallowed{$_})
			{
				$Disallowed{$_} = 1;
				delete $Disallowed{$_};
				weechat::print("", "$prgname: Nick ". get_color($_) . $_ . weechat::color("reset") . " removed from blacklist.");
				blacklist_save();
			}elsif ($cmd eq "bl_del") {
				weechat::print("", "$prgname: Nick " . get_color($_) .  $_ . weechat::color("reset") . " not in blacklist. Nothing removed.");
			}
		}
	}
	else{
		weechat::print("", "$prgname : There is no nick to be removed.");
	}
}
sub get_color{
    my $nick_name = $_[0];
    return weechat::info_get("irc_nick_color", $nick_name);
}
# newsbar support starts here (code by rettub)
sub info2newsbar{
	my ( $color, $category, $server, $nick, $channelname ) = @_;
	weechat::command( '',
			"/newsbar  add --color $color $category\t"
			. get_color($nick)
			. $nick
			. weechat::color('reset') . '@'
			. get_color($server)
			. $server
			. weechat::color('reset')
			. weechat::color('bold')
			. " joined Channel: "
			. weechat::color('reset')
			. get_color($channelname)
			. $channelname );
}
sub newsbar{
        my $info_list = weechat::infolist_get( "perl_script", "", "newsbar" );
        weechat::infolist_next($info_list);
        my $newsbar = weechat::infolist_string( $info_list, "name" ) eq 'newsbar';
        weechat::infolist_free($info_list);
        return $newsbar if (defined $newsbar);
}
# newsbar support ends here
sub init{
# set value of script (for example starting script the first time)
	weechat::config_set_plugin("cmd", $extern_command)
		if (weechat::config_get_plugin("cmd") eq "");

	weechat::config_set_plugin($status, $default_status)
		if (weechat::config_get_plugin($status) eq "");

	if ( weechat::config_get_plugin($whitelist) eq '' ) {
		my $wd = weechat::info_get( "weechat_dir", "" );
		$wd =~ s/\/$//;
		weechat::config_set_plugin($whitelist, $wd . "/" . $default_whitelist );
	}
	if ( weechat::config_get_plugin($blacklist) eq '' ) {
		my $wd = weechat::info_get( "weechat_dir", "" );
		$wd =~ s/\/$//;
		weechat::config_set_plugin($blacklist, $wd . "/" . $default_blacklist );
	}

	weechat::config_set_plugin("block_current_buffer", $block_current_buffer)
		if (weechat::config_get_plugin("block_current_buffer") eq "");
	weechat::config_set_plugin("use_newsbar", "off")
		if (weechat::config_get_plugin("use_newsbar") eq "");
	weechat::config_set_plugin("block_all_buffers", "off")
		if (weechat::config_get_plugin("block_all_buffers") eq "");


	list_read('whitelist', \%Allowed);
	list_read('blacklist', \%Disallowed);

        $command_chars = weechat::config_string( weechat::config_get("weechat.look.command_chars") ) . "/";
}
sub DEBUG {weechat::print('', "***\t" . $_[0]);}
