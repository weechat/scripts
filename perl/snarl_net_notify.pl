#
# Copyright (c) 2010 by Eric Harmon (http://eharmon.net)
# Copyright (c) 2009 by kinabalu (andrew AT mysticcoders DOT com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

#
# Snarl Notification script over network
#
# Based on growl-net-notify.pl by kinabalu
# Code and README availible at: http://github.com/eharmon/snarl-net-notify
#
# History:
#
# 2010-02-12, eharmon
#	version 0.6.1, switched to new weechat naming standards
#
# 2010-02-08, eharmon
#       version 0.6, ported from Growl to Snarl, added a few features
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#       version 0.5, sync with last API changes
#
# 2009-04-25, kinabalu <andrew AT mysticcoders DOT com>
#       version 0.4, version upgrade, minor cleanup of source
#
# 2009-04-18, kinabalu <andrew AT mysticcoders DOT com>
#	version 0.3, version upgraded to support weechat 0.3.0+
#
# 2009-04-16, kinabalu <andrew AT mysticcoders DOT com>
#	version 0.2, removed need for Parse::IRC
#
# 2009-04-10, kinabalu <andrew AT mysticcoders DOT com>
#	version 0.1, initial version rewritten from growl-notify
#   - original inspiration from growl-notify.pl author Zak Elep
#
# /snarl can be used in combination with these actions
#
# /snarl on
# /snarl off
# /snarl setup [host] [port]
# /snarl inactive [time_in_seconds]
# /snarl status
# /snarl test [message]
# /help snarl
#
# The script can be loaded into WeeChat by executing:
#
# /perl load snarl_net_notify.pl
#
# The script may also be auto-loaded by WeeChat.  See the
# WeeChat manual for instructions about how to do this.
#
# This script was tested with WeeChat version 0.3.0.
#

use IO::Socket::INET;
use integer;

my $snarl_app = "WeeChat";				# name given to Snarl for configuration
my $snarl_active = 1;

# SNP response codes
use constant SNP_SUCCESS 			=> 0;
use constant SNP_ERROR_FAILED			=> 101;
use constant SNP_ERROR_UNKNOWN_COMMAND 		=> 102;
use constant SNP_ERROR_TIMED_OUT		=> 103;
use constant SNP_ERROR_BAD_PACKET		=> 107;
use constant SNP_ERROR_NOT_RUNNING		=> 201;
use constant SNP_ERROR_NOT_REGISTERED		=> 202;
use constant SNP_ERROR_ALREADY_REGISTERED	=> 203;
use constant SNP_ERROR_CLASS_ALREADY_EXISTS	=> 204;

sub message_process_init {

    weechat::hook_signal("weechat_pv", "highlight_privmsg", "");
    weechat::hook_print( "", "", "", 1, "highlight_public", "");
    weechat::hook_signal("quit", "snarl_unregister", "");
    weechat::hook_signal("irc_server_connected", "server_connection_change", "");
    weechat::hook_signal("irc_server_disconnected", "server_connection_change", "");

}

#
# 0.3.0 clean version of highlighting for private messages
#
sub highlight_privmsg {
    my ( $nick, $message ) = ( $_[2] =~ /(.*?)\t(.*)/ );
		
	send_message("IRC query from $nick", $message);				
	return weechat::WEECHAT_RC_OK;	
}

#
# 0.3.0 clean version of highlighting for public messages
#
sub highlight_public {
    my ( $data, $bufferp, undef, undef, undef, $ishilight, $nick, $message ) = @_;
		
	if( $ishilight == 1 ) {
				
        $channel = weechat::buffer_get_string( $bufferp, "localvar_channel" ) || 'UNDEF';

		send_message("IRC highlight from $nick", $message . ($channel ne 'UNDEF' ? ' in ' . $channel : ''));
	}
	return weechat::WEECHAT_RC_OK;	
}

#
# Send a notification when the connection status changes
#
sub server_connection_change {
	my ($data, $signal, $name) = @_;
	if($signal eq "irc_server_connected") {
		$state = "Connected to";
	} else {
		$state = "Disconnected from";
	}
	send_message("IRC Connection", "$state $name", 4);
	return weechat::WEECHAT_RC_OK;
}

#
#
# Handle the SNP response codes
#
sub get_code {
	my ($response) = @_;
	@split = split(/\//, $response);
	$code = $split[2];
	# If the code is not running then Snarl isn't running network services, alert this error and shut down notifications
	if($code == SNP_ERROR_NOT_RUNNING) {
		prt("Snarl: Error! Snarl isn't accepting network connections, disabling Snarl notifications.");
		$snarl_active = 0;
		# Pretend like everything was fine so we don't handle the error upstream
		return SNP_SUCCESS;
	}
	return $code;
}

#
# Get a connection to Snarl
#
sub get_sock {
	$host = &getc('snarl_net_client');
	$port = &getc('snarl_net_port');
	$sock = new IO::Socket::INET(PeerAddr => $host,
					PeerPort => $port,
					Proto => 'tcp');
	return $sock;
}
	
#
# Send a message over SNP
#
sub send_message {
	my ( $title, $message, $time ) = @_;
	
	my $inactivity = 0;
	
	$inactivity = weechat::info_get("inactivity", "");
		
	if((&getc('snarl_net_inactivity') - $inactivity) <= 0 && $snarl_active) {
		snarl_notify( "$title", "$message", $time );
	}			
}

#
# smaller way to do weechat::get_plugin_config
#
sub getc {
	return weechat::config_get_plugin($_[0]);	
}

#
# smaller way to do weechat::get_plugin_config
#
sub setc {
	return weechat::config_set_plugin($_[0], $_[1]);	
}

#
# print function
# 
sub prt {
	weechat::print("buffer", $_[0]);
}

#
# Send notification through SNP
#
# args: $title, $description, [$length], [$testing]
#
sub snarl_notify {
	$title = $_[0];
	$desc = $_[1];
	$length = $_[2];
	$testing = $_[3];
	if(!$length) {
		$length = 8;
	}

	my $sock = get_sock();
	if($sock) {
		# Loop to try again in case our registration died
		for($n = 0; $n < 2; $n++) {
			print $sock "type=SNP#?version=1.0#?action=notification#?app=$snarl_app#?class=1#?title=$title#?text=$desc#?timeout=$length\r\n";
			$lines = <$sock>;
			$code = get_code($lines);
			# Only handling this error, everything else let's just give up on, as they are hard to handle
			# If our registration has somehow died (remote computer restarted, etc), re-register and try to send again
			if($code == SNP_ERROR_NOT_REGISTERED) {
				snarl_register();
				next;
			# Just so people know what's going on, let's have it show the error if we're testing
			} elsif($code != SNP_SUCCESS && $testing) {
				prt("Snarl: Unhandled error: $code");
				last;
			# If everything worked, break out of the loop
			} else {
				last;
			}
		}
		close($sock);
	} elsif($testing) {
		prt("Snarl: Couldn't connect to Snarl. Check port and Snarl network configuration.");
	}
}

#
# Register your app with Snarl through SNP
#
sub snarl_register {	
	my $sock = get_sock();
	if($sock) {
		print $sock "type=SNP#?version=1.0#?action=register#?app=$snarl_app\r\n";
		$line = <$sock>;
		$code = get_code($line);
		if($code == SNP_SUCCESS || $code == SNP_ERROR_ALREADY_REGISTERED) {
			print $sock "type=SNP#?version=1.0#?action=add_class#?app=$snarl_app#?class=1#?title=IRC Notification\r\n";
			$line = <$sock>;
			$code = get_code($line);
			if($code == SNP_SUCCESS || $code == SNP_CLASS_ALREADY_EXISTS) {
				prt("Snarl registered at $host:$port");
			} else {
				prt("Couldn't register notifcation: $line");
			}
		} else {
			prt("Couldn't register app: $line");
		}
		close($sock);
	} else {
		prt("Connection to $host:$port failed: $@");
	}
}

#
# Unregister application through SNP
#
sub snarl_unregister {
	my $sock = get_sock();
	if($sock) {
		print $sock "type=SNP#?version=1.0#?action=unregister#?app=$snarl_app\r\n";
		close($sock);
	}
}

#
# Handler will process commands
#
# /snarl on
# /snarl off
# /snarl setup [host] [password] [port]
# /snarl inactive [time_in_seconds]
# /snarl status
# /snarl test [message]
# /help snarl
#
sub handler {
	no strict 'refs';	# access symbol table
	
        my $data = shift;
	my $buffer = shift;
	my $argList = shift;

	my @args = split(/ /, $argList);
	my $command = $args[0];	
		
	if(!$command) {
		prt("Rawr! (try /help snarl for help on using this plugin)");
		return weechat::WEECHAT_RC_OK;
	}
	
	if($command eq "off") {
		$snarl_active = 0;
		snarl_unregister();
		prt("Snarl notifications: OFF");
		return weechat::WEECHAT_RC_OK;
	} elsif($command eq "on") {
		$snarl_active = 1;
		snarl_register();
		prt("Snarl notifications: ON");
		return weechat::WEECHAT_RC_OK;
	} elsif($command eq "inactive") {
		if(exists $args[1] && $args[1] >= 0) {
			setc("snarl_net_inactivity", $args[1]);
			prt("Snarl notifications inactivity set to: " . $args[1] . "s");
			return weechat::WEECHAT_RC_OK;
		}
		return weechat::WEECHAT_RC_ERROR;	
	} elsif($command eq "setup") {
		if(exists $args[1] && $args[1] ne "") {
			setc("snarl_net_client", $args[1]);			
		} 
		if(exists $args[2] && $args[2] ne "") {
			setc("snarl_net_port", $args[2]);
		}
		snarl_register();				
		prt("Snarl setup re-registered with: [host: " . &getc('snarl_net_client') . ":"  . &getc('snarl_net_port') . "]"); 
		return weechat::WEECHAT_RC_OK;
	} elsif($command eq "status") {
		prt("Snarl notifications: " . ($snarl_active ? "ON" : "OFF") . ", inactivity timeout: " . &getc("snarl_net_inactivity"));
		return weechat::WEECHAT_RC_OK;
	} elsif($command eq "test") {
		if($snarl_active) {
			my $test_message = "Just testing.";
			if($args[1]) {
				$test_message = substr $argList, 5;
			}
			prt("Sending test message: " . $test_message);
			snarl_notify("Test Message", $test_message, '', 1 );
		} else {
			prt("Snarl isn't active, please active it to send test messages.");
		}
		return weechat::WEECHAT_RC_OK;
	}

    return weechat::WEECHAT_RC_ERROR;
}


#
# setup
#
my $version = '0.6.1';
   
weechat::register("snarl-net-notify", "eharmon, kinabalu <andrew\@mysticcoders.com>", $version, "GPL3", "Send Weechat notifications to Snarl", "", "");
		
weechat::hook_command("snarl", "setup the snarl notify script",

                               "on|off|setup [host] [port]|inactive [time_in_seconds]|status|help",
                               "on: turn on snarl notifications (default)\n".
                               "off: turn off snarl notifications\n".
                               "setup [host] [port]: change the parameters for registration/notification with Snarl\n".
                               "inactive [time_in_seconds]: number of seconds of inactivity before we notify (default: 30)\n".
                               "status: gives info on notification and inactivity settings\n".
                               "test [message]: send a test message\n",

                               "on|off|setup|inactive|status", "handler", "");

my $default_snarl_net_client = "localhost";
my $default_snarl_net_inactivity = 30;
my $default_snarl_net_port = 9887;				# default UDP port used by Snarl

&setc("snarl_net_client", $default_snarl_net_client) if (&getc("snarl_net_client") eq "");
&setc("snarl_net_inactivity", $default_snarl_net_inactivity) if (&getc("snarl_net_inactivity") eq "");
&setc("snarl_net_port", $default_snarl_net_port) if (&getc("snarl_net_port") eq "");
		
# register our app with snarl		
snarl_register();

# register our hooks in WeeChat
message_process_init();
