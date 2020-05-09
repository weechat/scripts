#
# Copyright (c) 2010-2013 by Nils Görs <weechatter@arcor.de>
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
# v0.4  : add compatibility with new weechat_print modifier data (WeeChat >= 2.9)
# v0.3  : add: option cloaked_text_reply (suggested by dAnjou)
#       : add: option rapid_fire
#       : add: description for options
# v0.2  : error with uninitialized channel removed
#       : /me text will be cloaked, too
#
# TODO saving the cloaked text to log-file.

use strict;
use POSIX qw(strftime);

my $SCRIPT_NAME         = "curiousignore";
my $SCRIPT_VERSION      = "0.4";
my $SCRIPT_DESC         = "suppresses messages from specified nick and only prints his nickname in channel";

my $save_to_log = "on";
my $nick_mode = "";
my %nick_structure = ();
#$VAR1 = {
#		'server.channel' => nick
#	}

my %options_default = ('blacklist'              => ['','comma separated list of nicks to be cloaked. format: server.#channel.nick'],
                       'cloaked_text'           => ['text cloaked','text that will be displayed in buffer. if no text is given, the message will be discard'],
                       'cloaked_text_reply'     => ['reply to cloaked text','text that will be displayed in buffer for an reply of a cloaked nick. if no text is given, the message will be discard. Own written messages will be displayed'],
                       'rapid_fire'             => ['on','displays cloaked text only once, even nick sends several messages'],
);

my %options = ();

# program starts here
sub colorize_cb {
    my ( $data, $modifier, $modifier_data, $string ) = @_;

    $string =~ m/^(.*)\t(.*)/;                                                                          # get the nick & message: nick[tab]message
    my $nick = $1;
    my $message = $2;

    if (not defined $nick) {return $string;}                                                            # no nickname
    my $server = "";
    my $channel = "";
    if ($modifier_data =~ /0x/)
    {
        # WeeChat >= 2.9
        $modifier_data =~ (m/([^;]*);/);
        my $buf_ptr = $1;
        $server = weechat::buffer_get_string($buf_ptr, "localvar_server");
        $channel = weechat::buffer_get_string($buf_ptr, "localvar_channel");
    }
    else
    {
        # WeeChat <= 2.8
        #irc;freenode.#weechat;
        $modifier_data =~ (m/irc;(.+?)\.(.+?)\;/);
        $server = $1;
        $channel = $2;
    }
    if ($server eq "" or $channel eq "") {return $string;}                                              # no channel
    my $server_chan = $server . "." . $channel;

    $nick = weechat::string_remove_color($nick,"");                                                     # remove colour-codes from nick
    my $nick_color = weechat::info_get('irc_nick_color', $nick);                                        # get nick-colour

    my $last_nick = "";
    if ($nick =~ m/^\@|^\%|^\+|^\~|^\*|^\&|^\!|^\-/)                                                    # check for nick modes (@%+~*&!-)
    {
        $nick_mode = substr($nick,0,1);
        $last_nick = substr($nick,1,length($nick)-1);
    }
    else
    {
        $last_nick = $nick;
    }

    my $blacklist2 = $options{blacklist};
    $blacklist2 =~ tr/,/ /;                                                                             # replace "," with space
    if ( index( $blacklist2, $server_chan.".".$last_nick ) >= 0 )                                           # check blacklist
    {
        return "" if ( lc($options{rapid_fire}) eq "on"  && defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $last_nick) );
        #get_logfile_name( weechat::buffer_search("",$server_chan),$string );                       # find the buffer pointer

        return $string if (get_current_nick() eq $nick);
        $string = $last_nick . "\t" . $options{cloaked_text};
        $nick_structure{$server_chan} = $last_nick;                                                         # store last nick
        return "" if ( $options{cloaked_text} eq "" );
        return $string;
    }

# curious nick made a /me ?
    if (weechat::config_string(weechat::config_get("weechat.look.prefix_action")) eq $last_nick)            # get prefix_action
    {
        my @array=split(/,/,$options{blacklist});
        foreach (@array)
        {
            $_ =~ (/(.+?)\.(.+?)\.(.*)/);
            my $string_w_color = weechat::string_remove_color($string,"");
            $nick = $3;
            my $nick_w_prefix = weechat::config_string(weechat::config_get("weechat.look.prefix_action")) . "\t" . $nick;
            if (  $string_w_color =~ m/^$nick_w_prefix/ )
            {
                return "" if ( lc($options{rapid_fire}) eq "on"  && defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $nick) );
                return "" if ( defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $nick) && $options{cloaked_text} eq "" );
                $string = $nick . "\t" . $options{cloaked_text};
                $nick_structure{$server_chan} = $nick;                                                  # store last nick
                return "" if ( $options{cloaked_text} eq "" );
                return $string;
            }
        }

    }

    if ( search_nick_in_message($server,$channel,$message) eq 1 )
    {
        return "" if ( lc($options{rapid_fire}) eq "on"  && defined $nick_structure{$server_chan} && ($nick_structure{$server_chan} eq $last_nick) );

        return $string if (get_current_nick() eq $nick);
        $string = $last_nick . "\t" . $options{cloaked_text_reply};
        $nick_structure{$server_chan} = $last_nick;                                                         # store last nick
        return "" if ( $options{cloaked_text} eq "" );
        return $string;
    }

    $nick_structure{$server_chan} = $last_nick;                                                             # store last nick
    return $string;
}

sub get_current_nick
{
    return weechat::buffer_get_string(weechat::current_buffer(),'localvar_nick');
}

sub search_nick_in_message
{
    my ($server,$channel,$message) = @_;
    my @array=split(/,/,$options{blacklist});
    foreach (@array)
    {
        my ($server_cloaked,$channel_cloaked,$nick_cloaked) = split(/\./,$_);
        next if ($server ne $server_cloaked or $channel ne $channel_cloaked);
        return 1 if ( $message =~ m/$nick_cloaked/i );
    }
return 0;
}

# using this "hack" weechat will crash on start
sub get_logfile_name
{                                                                                                       # get name of log-file
    my ($buffer, $string) = @_;                                                                         # buffer pointer
    my $logfilename = "";
    my $log_enabled = "";
    my $log_level = "";
    my $bpointer = "";

    if ($save_to_log eq "on")                                                                           # save to log on?
    {
        my $linfolist = weechat::infolist_get("logger_buffer", "", "");
        while(weechat::infolist_next($linfolist))
        {
            $bpointer = weechat::infolist_pointer($linfolist, "buffer");
            if($bpointer eq $buffer)
            {
                $logfilename = weechat::infolist_string($linfolist, "log_filename");
                $log_enabled = weechat::infolist_integer($linfolist, "log_enabled");
                $log_level = weechat::infolist_integer($linfolist, "log_level");
                last if ($log_level == 0 );                                                             # logging disabled
                # get time format and convert it
                my $time_format = weechat::config_string( weechat::config_get("logger.file.time_format") );
                $time_format = strftime $time_format, localtime;
                # remove color-codes from string and create output for log
                $string = $time_format . "\t" . weechat::string_remove_color($string,"");
                weechat::command($buffer, "/mute logger disable");                                      # disable file logging
                system("echo \'" . $string . "\' >>".$logfilename);                                     # write output to logfile
                weechat::command($buffer,"/mute logger set " . $log_level);                             # start file logging again
                last;
            }
        }
        weechat::infolist_free($linfolist);
    }
    return weechat::WEECHAT_RC_OK;
}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".$SCRIPT_NAME."."), length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

sub init_config
{
    my $version = weechat::info_get("version_number", "") || 0;
    foreach my $option (keys %options_default)
    {
        if (!weechat::config_is_set_plugin($option))
        {
            weechat::config_set_plugin($option, $options_default{$option}[0]);
            $options{$option} = $options_default{$option}[0];
        }
        else
        {
            $options{$option} = weechat::config_get_plugin($option);
        }
        if ($version >= 0x00030500)
        {
            weechat::config_set_desc_plugin($option, $options_default{$option}[1]." (default: \"".$options_default{$option}[0]."\")");
        }
    }
}

# first function called by a WeeChat-script.
weechat::register($SCRIPT_NAME, "Nils Görs <weechatter\@arcor.de>", $SCRIPT_VERSION, "GPL3", $SCRIPT_DESC, "", "");

init_config();

#  if (!weechat::config_is_set_plugin("save_to_log")){
#    weechat::config_set_plugin("save_to_log", $save_to_log);
#  }else{
#    $save_to_log = weechat::config_get_plugin("save_to_log");
#  }

weechat::hook_modifier("weechat_print","colorize_cb", "");

weechat::hook_config( "plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "" );
