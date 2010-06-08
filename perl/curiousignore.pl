#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# ignore message and only print nick-name from specified users
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
# idea by darrob
#
# settings:
# /set plugins.var.perl.curiousignore.blacklist server.channel.nick
# /set plugins.var.perl.curiousignore.cloaked_text "text cloaked"
#
# this scripts needs weechat 0.3.2 or higher
#
# v0.2	: error with uninitialized channel removed
#	: /me text will be cloaked, too
#
# TODO saving the cloaked text to log-file.

use strict;
use POSIX qw(strftime);

my $prgname	= "curiousignore";
my $version	= "0.2";
my $description	= "suppresses messages from specified nick and only prints his nickname in channel";

my $blacklist = "";
my $cloaked_text = "text cloaked";
my $save_to_log = "on";
my $nick_mode = "";
my %nick_structure = ();
#$VAR1 = {
#		'server.channel' => nick
#	}

# program starts here
sub colorize_cb {
	my ( $data, $modifier, $modifier_data, $string ) = @_;

	$string =~ m/^(.*)\t/;											# get the nick name: nick[tab]string
		my $nick = $1;

	if (not defined $nick) {return $string;}								# no nickname
#irc;freenode.#weechat;
		$modifier_data =~ (m/irc;(.+?)\.(.+?)\;/);
	my $server = $1;
	my $channel = $2;
	if (not defined $channel) {return $string;}								# no channel
		my $server_chan = $server . "." . $channel;

	$nick = weechat::string_remove_color($nick,"");								# remove colour-codes from nick
		my $nick_color = weechat::info_get('irc_nick_color', $nick);						# get nick-colour

#    $blacklist = weechat::config_get_plugin("blacklist");
		my $blacklist2 = $blacklist;
	$blacklist2 =~ tr/,/ /;

	my $nick2 = "";
	if ($nick =~ m/^\@|^\%|^\+|^\~|^\*|^\&|^\!|^\-/) {						# check for nick modes (@%+~*&!-)
		$nick_mode = substr($nick,0,1);
		$nick2 = substr($nick,1,length($nick)-1);
	} else{
		$nick2 = $nick;
	}

	if ( index( $blacklist2, $server_chan.".".$nick2 ) >= 0 ) {						# check blacklist

		if ( defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $nick2 or $cloaked_text eq "") ){
#	get_logfile_name( weechat::buffer_search("",$server_chan),$string );				# find the buffer pointer
			return "";											# kill line
		}


#	if ($cloaked_text eq ""){									# no output text given!
#	    get_logfile_name( weechat::buffer_search("",$server_chan),$string );			# find the buffer pointer
#	    return "";											# kill line
#	}

#	get_logfile_name( weechat::buffer_search("",$server_chan),$string );				# find the buffer pointer
		$string = $nick2 . "\t" . $cloaked_text;
		$nick_structure{$server_chan} = $nick2;								# add nick from latest message
			return $string;
	}

# curious nick made a /me ?
	if (weechat::config_string(weechat::config_get("weechat.look.prefix_action")) eq $nick2){ 		# get prefix_action
		my @array=split(/,/,$blacklist);
		foreach (@array){
			$_ =~ (/(.+?)\.(.+?)\.(.*)/);
			my $string_w_color = weechat::string_remove_color($string,"");
			$nick = $3;
			my $nick_w_prefix = weechat::config_string(weechat::config_get("weechat.look.prefix_action")) . "\t" . $3;
			if (  $string_w_color =~ m/^$nick_w_prefix/ ){
				if ( defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $nick or $cloaked_text eq "") ){
					return "";											# kill line
				}
				$string = $nick . "\t" . $cloaked_text;
				$nick_structure{$server_chan} = $nick;								# add nick from latest message
					return $string;
			}
		}

	}

	$nick_structure{$server_chan} = $nick2;								# add nick from latest message
		return $string;
}

# using this "hack" weechat will crash on start
sub get_logfile_name{											# get name of log-file
	my ($buffer, $string) = @_;										# buffer pointer
		my $logfilename = "";
	my $log_enabled = "";
	my $log_level = "";
	my $bpointer = "";

	if ($save_to_log eq "on"){										# save to log on?
		my $linfolist = weechat::infolist_get("logger_buffer", "", "");

		while(weechat::infolist_next($linfolist)){
			$bpointer = weechat::infolist_pointer($linfolist, "buffer");
			if($bpointer eq $buffer){
				$logfilename = weechat::infolist_string($linfolist, "log_filename");
				$log_enabled = weechat::infolist_integer($linfolist, "log_enabled");
				$log_level = weechat::infolist_integer($linfolist, "log_level");
				if ($log_level == 0 ){									# logging disabled
					last;
				}
# get time format and convert it
				my $time_format = weechat::config_string( weechat::config_get("logger.file.time_format") );
				$time_format = strftime $time_format, localtime;
# remove colour-codes from string and create output for log
				$string = $time_format . "\t" . weechat::string_remove_color($string,"");


				weechat::command($buffer, "/mute logger disable");						# disable file logging
					system("echo \'" . $string . "\' >>".$logfilename);						# write output to logfile
					weechat::command($buffer,"/mute logger set " . $log_level);					# start file logging again
					last;
			}
		}
		weechat::infolist_free($linfolist);
	}
	return weechat::WEECHAT_RC_OK;
}

sub toggle_config_by_set{
	my ( $pointer, $name, $value ) = @_;

	if ($name eq "plugins.var.perl.$prgname.blacklist"){
		$blacklist = $value;
		return weechat::WEECHAT_RC_OK;
	}
	if ($name eq "plugins.var.perl.$prgname.cloaked_text"){
		$cloaked_text = $value;
		return weechat::WEECHAT_RC_OK;
	}
	if ($name eq "plugins.var.perl.$prgname.save_to_log"){
		$save_to_log = $value;
		return weechat::WEECHAT_RC_OK;
	}
	return weechat::WEECHAT_RC_OK;
}

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
		"GPL3", $description, "", "");

if (!weechat::config_is_set_plugin("blacklist")){
	weechat::config_set_plugin("blacklist", $blacklist);
}else{
	$blacklist = weechat::config_get_plugin("blacklist");
}
if (!weechat::config_is_set_plugin("cloaked_text")){
	weechat::config_set_plugin("cloaked_text", $cloaked_text);
}else{
	$cloaked_text = weechat::config_get_plugin("cloaked_text");
}

#  if (!weechat::config_is_set_plugin("save_to_log")){
#    weechat::config_set_plugin("save_to_log", $save_to_log);
#  }else{
#    $save_to_log = weechat::config_get_plugin("save_to_log");
#  }

weechat::hook_modifier("weechat_print","colorize_cb", "");

weechat::hook_config( "plugins.var.perl.$prgname.*", "toggle_config_by_set", "" );
