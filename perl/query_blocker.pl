# -----------------------------------------------------------------------------
#
# query_blocker.pl - Simple blocker for private messages (i.e. spam).
#
# -----------------------------------------------------------------------------
# Copyright (c) 2009-2014 by rettub <rettub@gmx.net>
# Copyright (c) 2011-2018 by nils_2 <weechatter@arcor.de>
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
# -----------------------------------------------------------------------------
#
# Simple IRC query blocker.
# - requires WeeChat 0.4.2 or newer
# - suggests perl script newsbar
#
# Got inspiration from (xchat script):
# GodOfGTA's Query-Blocker (eng) 1.2.3
#   http://home.arcor.de/godofgta/xchat/queryblocker-eng.pl
#
#
# Newest version available at:
#   git://github.com/rettub/weechat-plugins.git
#
## Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# -----------------------------------------------------------------------------
# History:
# 2018-07-30, usefulz & nils_2:
#     version 1.2:
#     FIX: undefine subroutine
#     ADD: eval_expression() for options
#     FIX: Warnung: Use of uninitialized value using highmon as a bar
#     FIX: Warnung: Use of uninitialized value using newsbar
#
# 2017-04-14, nils_2:
#     version 1.1:
#       ADD: function to ignore server (https://github.com/weechat/scripts/issues/79)
#
# 2016-12-11, mumixam:
#     version 1.0:
#     FIX: message starting with color not caught
#
# 2014-05-22, nils_2:
#     version 0.9:
#     IMPROVED: use NOTICE instead of PRIVMSG for auto-response (suggested by Mkaysi)
#
# 2013-05-01, nils_2:
#     version 0.8:
#     ADD: option ignore_auto_message (suggested by bpeak)
#
# 2013-02-24, nils_2:
#     version 0.7:
#     FIX: case insensitive comparison for "nickserv" and "chanserv"
#     ADD: option 'show_first_message_only' (suggested by gry)
#
# 2012-08-16, nils_2:
#     version 0.6.1:
#     IMPROVED: help text to allow a temporary query
#
# 2012-06-12, nils_2:
#     version 0.6:
#     FIX: allow own queries without 'mynick' in query whitelist
#     ADD: option 'temporary_mode'.
#     ADD: whitelist is now using format: server.nickname (please update your qb-whitelist!)
#     ADD: tab completion for all commands
#
# 2012-05-03, nils_2:
#     version 0.5:
#     FIX: invalid pointer for function infolist_get()
#     FIX: problem with case-sensitive nicks
#     FIX: work-around for [bug #27936] removed. (weechat ≥ 0.3.2)
#     ADD: option msgbuffer (idea by pmo)
#     ADD: option open_on_startup (idea by pmo)
#     ADD: option show_nick_only and show_deny_message
#     ADD: nick completion for add/del
#
# 2011-09-17, nils_2:
#     version 0.4:
#     FIX:         infolist() not freed
#
# 2010-12-20, nils_2:
#     version 0.3:
#     FIX:         find_color_nick(), now using API function weechat::info_get("irc_nick_color")
#
# 2010-01-10, rettub:
#     version 0.2:
#     new options: quiet, show_hint
#                  auto_message, auto_message_prefix
#
# 2009-11-03, rettub:
#     version 0.1: initial release
#
# -----------------------------------------------------------------------------
# TODO
#   - make Auto-Messages configurable

use Data::Dumper;
use warnings;
use strict;

my $SCRIPT      = 'query_blocker';
my $AUTHOR      = 'rettub <rettub@gmx.net>';
my $VERSION     = '1.2';
my $LICENSE     = 'GPL3';
my $DESCRIPTION = 'Simple blocker for private message (i.e. spam)';
my $COMMAND     = "query_blocker";             # new command name
my $ARGS_HELP   = "<on> | <off> | <status> | <list [last]> | <add [nick_1 [... [nick_n]]]> | <del nick_1 [... [nick_n]]> | <reload> | <blocked [clear]>";
my %help_desc = ( "block_queries"       => "to enable or disable $COMMAND (default: 'off')",
                  "quiet"               => "will send auto reply about blocking, but don't send any notice to you. (default: 'off')",
                  "show_deny_message"   => "show you the deny message, sent to user. (default: 'off')",
                  "show_hint"           => "show hint how to allow queries for nick. (default: 'on')",
                  "show_nick_only"      => "only show nick and server. (default: 'off')",
                  "show_first_message_only"=> "Show only first message sent by blocked queries (default: 'on')",
                  "whitelist"           => "path/file-name to store/read nicks not to be blocked (default: qb-whitelist.txt)",
                  "auto_message"        => "messages to inform user that you don't like to get private messages without asking first. '%N' will be replaced with users nick (note: content is evaluated, see /help eval).",
                  "auto_message_prefix" => "Prefix for auto message, may not be empty! (note: content is evaluated, see /help eval)",
                  "msgbuffer"           => "buffer used to display $SCRIPT messages (current = current buffer, private = private buffer, weechat = weechat core buffer, server = server buffer, buffer = $SCRIPT buffer, highmon = highmon buffer, newsbar = newsbar-bar)",
                  "logger"              => "logger status for $SCRIPT buffer (default: 'off')",
                  "hotlist_show"        => "$SCRIPT buffer appear in hotlists (status bar/buflist) (default: 'off')",
                  "open_on_startup"     => "open $SCRIPT buffer on startup. option msgbuffer has to be set to 'buffer' (default: 'off')",
                  "temporary_mode"      => "if 'on' you have to manually add a nick to whitelist. otherwise a conversation will be temporary only and after closing query buffer the nick will be discard (default: 'off')",
                  "ignore_auto_message" => "path/file-name to store/read nicks to not send an auto message (default: qb-ignore_auto_message.txt)",
);

my $CMD_HELP    = <<EO_HELP;
If a not allowed (blocked) nick sends you a private message, you will see a notice about nick, server and the message, but no buffer will be created. Then the nick gets a 'blocked' state, which will prevent you from seeing his queries again till you restart WeeChat, reload the script or you put the nick into the whitelist (if newsbar.pl is running notices will be printed there). In addition the user will be informed about blocking by an auto responce message when he gains the blocked state. So he can ask you in the public channel to allow his private messages.
If you send a private message to a user, his nick will be added to the whitelist.

Arguments:
              on/off: toggle blocking of queries.
              status: show blocking status.
         list [last]: show whitelist, use last to show the nick blocked last.
     add/del [nicks]: add/delete nick(s) to/from whitelist. (if no nick is given, 'add' will use the last blocked one).
                      ('nicks' is a list of nicks seperated by spaces).
              reload: reload whitelist (useful if you changed the file-location i.e. to use a common file).
     blocked [clear]: list blocked nicks. If arg 'clear' is given all blocked nicks will be removed.

Script Options:
 ignore_auto_message: $help_desc{ignore_auto_message}
           whitelist: $help_desc{whitelist}
       block_queries: $help_desc{block_queries}
        auto_message: $help_desc{auto_message}
 auto_message_prefix: $help_desc{auto_message_prefix}
               quiet: $help_desc{quiet}
   show_deny_message: $help_desc{show_deny_message}
           show_hint: $help_desc{show_hint}
      show_nick_only: $help_desc{show_nick_only}
           msgbuffer: $help_desc{msgbuffer}
              logger: $help_desc{logger}
        hotlist_show: $help_desc{hotlist_show}
     open_on_startup: $help_desc{open_on_startup}
      temporary_mode: $help_desc{temporary_mode}

By default all private messages (/query, /msg) from nicks not in the whitelist will be blocked.
 - to allow all private message, $SCRIPT can be disabled, type '/$COMMAND off'.
 - to allow private messages from certain nicks, put them into the whitelist, type '/$COMMAND add nick' (you can use nick-completion).
   if you start a query, the nick will be added as a temporary nick. the nick will be removed when you close query
 - to remove a nick from the whitelist, type '/$COMMAND del nick' (you can use nick-completion).
 - you can add a localvar for a specific server to disable $COMMAND for this server: /buffer set localvar_set_query_blocker 1

NOTE: If you load $SCRIPT the first time, blocking of private messages is disabled, you have to enable blocking, type '/$COMMAND on'.
EO_HELP

my $COMPLETITION  = "on %-".
                    "||off %-".
                    "||status %-".
                    "||list last %-".
                    "||add %(perl_query_blocker_add)| %(nick)|%*".
                    "||del %(perl_query_blocker_del)| %(nick)|%*".
                    "||reload %-".
                    "||blocked clear %-";
my $CALLBACK      = $COMMAND;
my $CALLBACK_DATA = undef;
my $weechat_version;

# script options
my %SETTINGS = (
    "block_queries" => "off",
    "quiet"         => "off",
    "show_deny_message" => "off",
    "show_hint"     => "on",
    "show_nick_only"=> "off",
    "show_first_message_only" => "on",
    "whitelist"     => "qb-whitelist.txt",
    "auto_message"  => "I'm using a query blocking script, please wait while i whitelist you!",
    "auto_message_prefix" => "Auto-Message: ",
    "msgbuffer"     => "server", # current, private, weechat, buffer, highmon
    "logger"        => "off",
    "hotlist_show"  => "off",
    "open_on_startup"  => "off",
    "temporary_mode" => "off",
    "ignore_auto_message" => "qb-ignore_auto_message.txt",
);

my $Last_query_nick = undef;

sub DEBUG {weechat::print('', "***\t" . $_[0]);}

# {{{ helpers
# 
# irc_nick_find_color: find a color for a nick (according to nick letters)
sub irc_nick_find_color
{
    my $nick_name = $_[0];
    return weechat::info_get("irc_nick_color", $nick_name);
}
# }}}

my %Blocked = ();
my %Allowed = ();
my %ignore_auto_message = ();

sub check_ignore_auto_message { return exists $ignore_auto_message{ $_[0] }; }

sub ignore_auto_message_read {
    my $whitelist = weechat::config_get_plugin( "ignore_auto_message" );
    return unless -e $whitelist;
    open (WL, "<", $whitelist) || DEBUG("$whitelist: $!");
        while (<WL>) {
                chomp;
                my ( $server, $nick ) = split /\./,$_;           # servername.nickname
                if (not defined $nick){
                    close WL;
                    weechat::print("",weechat::prefix("error")."$SCRIPT: $whitelist wrong format for entry: $_ (new format: servername.nickname).");
                    return 1;
                }
                $ignore_auto_message{$_} = 1  if length $_;
        }
        close WL;
        return 0;
}

sub nick_allowed { return exists $Allowed{ $_[0] }; }

sub whitelist_read {
    my $whitelist = weechat::config_get_plugin( "whitelist" );
    return unless -e $whitelist;
    open (WL, "<", $whitelist) || DEBUG("$whitelist: $!");
	while (<WL>) {
		chomp;
                my ( $server, $nick ) = split /\./,$_;           # servername.nickname
                if (not defined $nick){
                    close WL;
                    weechat::print("",weechat::prefix("error")."$SCRIPT: $whitelist wrong format for entry: $_ (new format: servername.nickname).");
                    return 1;
                }
                $Allowed{$_} = 1  if length $_;
	}
	close WL;
	return 0;
}

sub whitelist_save {
    my $whitelist = weechat::config_get_plugin( "whitelist" );
    open (WL, ">", $whitelist) || DEBUG("write whitelist: $!");
    foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed ){
        print WL "$_\n" if ($Allowed{$_} == 1);
    }
    close WL;
}

# newsbar api staff {{{
sub info2newsbar {
    my ( $color, $category, $server, $nick, $message ) = @_;
    weechat::command( '',
            "/newsbar  add --color $color $category\t"
          . irc_nick_find_color($nick)
          . $nick
          . weechat::color('reset') . '@'
          . irc_nick_find_color($server)
          . $server
          . weechat::color('reset')
          . weechat::color('bold')
          . " tries to start a query: "
          . weechat::color('reset')
          . $message );
    weechat::command( '',
            "/newsbar  add --color $color $category\t"
          . "To allow the query, type: "
          . "/$COMMAND add $nick" ) unless (weechat::config_get_plugin('show_hint') eq 'off');
}

sub newsbar {
    my $info_list = weechat::infolist_get( "perl_script", "", "newsbar" );
    weechat::infolist_next($info_list);
    my $newsbar = weechat::infolist_string( $info_list, "name" ) eq 'newsbar';
    weechat::infolist_free($info_list);
    return $newsbar if (defined $newsbar);
}
#}}}

sub print_info {
    my ( $buffer, $server, $my_nick, $nick, $message ) = @_;
    my $prefix_network = weechat::config_string( weechat::config_get("weechat.look.prefix_network"));
    my $buf_pointer = "";
    my $bar_pointer = "";
    my $orig_message = $message;

    if     ( $buffer eq "current" ){
        $buf_pointer = weechat::current_buffer();
    }elsif ( $buffer eq "weechat" ){
        $buf_pointer = weechat::buffer_search("core","weechat");
    }elsif ( $buffer eq "server" ){
        $buf_pointer = weechat::buffer_search("irc","server".".".$server);
    }elsif ( $buffer eq "private" ){
        $buf_pointer = weechat::buffer_search("irc",$server.".".$my_nick);
    }elsif ( $buffer eq "buffer" ){
        $buf_pointer = weechat::buffer_search("perl",$SCRIPT);
        $buf_pointer = query_blocker_buffer_open() if ( $buf_pointer eq "" );
    }elsif ( $buffer eq "highmon" ){
        $buf_pointer = weechat::buffer_search("perl","highmon");
    }else{
        $buf_pointer = weechat::buffer_search("",$buffer);
        $server = weechat::buffer_get_string($buf_pointer, "localvar_server");
    }

    # no buffer found, use weechat fallback buffer
    if ( $buf_pointer eq "" or not defined $buf_pointer ){
        if ( $server eq "" ){
            $buf_pointer = weechat::buffer_search_main();
        }else{
            $buf_pointer = fallback_buffer($server);
        }
    }
    return $buf_pointer if (lc(weechat::config_get_plugin('quiet') eq "on"));

    if (lc(weechat::config_get_plugin('show_nick_only') eq 'off')) {
        $message = ": $message";
    }else{
        $message = "";
    }
    unless ( exists $Blocked{$server.".".$nick} and lc(weechat::config_get_plugin('show_first_message_only') eq 'off') ) {
        weechat::print($buf_pointer,"$prefix_network\t"
                                    .irc_nick_find_color($nick).$nick
                                    .weechat::color('reset')
                                    ." tries to start a query on "
                                    .irc_nick_find_color($server).$server
                                    .weechat::color('reset')
                                    .$message );
        weechat::print($buf_pointer,"$prefix_network\t"
                                    ."to allow query: /$COMMAND add "
                                    .irc_nick_find_color($server).$server
                                    .weechat::color('reset')
                                    ."."
                                    .irc_nick_find_color($nick).$nick
                                    .weechat::color('reset')."\n"
                                    ."or to allow temporary query: /query -server "
                                    .irc_nick_find_color($server).$server
                                    .weechat::color('reset')
                                    ." "
                                    .irc_nick_find_color($nick).$nick
                                    .weechat::color('reset')) unless (weechat::config_get_plugin('show_hint') eq 'off');
    }else{
        weechat::print($buf_pointer,irc_nick_find_color($server).$server."."
                                    .irc_nick_find_color($nick).$nick."\t"
                                    .weechat::color('reset')
                                    .$orig_message );
    }
    return $buf_pointer;
}

sub eval_expression{
    my ($string) = @_;
    return weechat::string_eval_expression($string, {}, {},{});
}

# get value from msgbuffer_fallback option
sub fallback_buffer{
    my ($server) = @_;
    my $fallback = weechat::config_string( weechat::config_get("irc.look.msgbuffer_fallback") );
    my $buf_pointer;
    $buf_pointer = weechat::current_buffer() if ( $fallback eq "current" );
    $buf_pointer = weechat::buffer_search("irc","server".".".$server) if ( $fallback eq "server" );
    return $buf_pointer;
}

sub modifier_irc_in_privmsg {
    my ( $data, $signal, $server, $arg ) = @_;
    my $my_nick = weechat::info_get( 'irc_nick', $server );

    # by default, blocking is enabled for all server. except the one with a localvar
    return $arg if (weechat::buffer_get_string(weechat::buffer_search("irc", "server.".$server), 'localvar_query_blocker'));

    # check for query message
    if ( $arg =~ m/:(.+?)!.+? PRIVMSG $my_nick :(.*)/i ) {
        my $query_nick = $1;
        my $query_msg  = $2;

        # always allow own queries
        return $arg if ($query_nick eq $my_nick);

        # if nick is allowed to send queries, let WeeChat handle the query
        return $arg if nick_allowed($server . "." . $query_nick);

        # if nick is in ignore_auto_message list, ignore it.
        return '' if check_ignore_auto_message($server . "." . $query_nick);

        $Last_query_nick = $server . "." . $query_nick;
        my $buf_pointer;
        unless ( exists $Blocked{$server.".".$query_nick} and lc(weechat::config_get_plugin('show_first_message_only') eq 'on') )
        {
            unless (lc(weechat::config_get_plugin('quiet') eq 'on'))
            {
                # print messages to.... newsbar, current, private, server, weechat, buffer, highmon
                if ( newsbar() eq "1" and lc(weechat::config_get_plugin('msgbuffer')) eq 'newsbar' ) {
                    info2newsbar( 'lightred', '[QUERY-WARN]', $server, $query_nick, $query_msg );
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'current' ) {
                    $buf_pointer = print_info("current", $server, $my_nick, $query_nick, $query_msg);
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'server' ) {
                    $buf_pointer = print_info("server", $server, $my_nick, $query_nick, $query_msg);
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'private' ) {
                    $buf_pointer = print_info("private", $server, $my_nick, $query_nick, $query_msg);
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'weechat' ) {
                    $buf_pointer = print_info("weechat", $server, $my_nick, $query_nick, $query_msg);
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'buffer' ) {
                    $buf_pointer = print_info("buffer", $server, $my_nick, $query_nick, $query_msg);
                } elsif ( lc(weechat::config_get_plugin('msgbuffer')) eq 'highmon' ) {
                    $buf_pointer = print_info("highmon", $server, $my_nick, $query_nick, $query_msg);
                } else {
                    $buf_pointer = print_info(weechat::config_get_plugin('msgbuffer'), $server, $my_nick, $query_nick, $query_msg);
                }
            }
            #elsif (lc(weechat::config_get_plugin('quiet') eq 'on')){
            #    $buf_pointer = print_info(lc(weechat::config_get_plugin('msgbuffer')), $server, $my_nick, $query_nick, $query_msg);
            #}

            # auto responce msg to query_nick (deny_message)
            my $msg = weechat::config_get_plugin('auto_message_prefix') . weechat::config_get_plugin('auto_message');
            $msg =~ s/%N/$query_nick/g;     # keep this for historical reasons
            $msg = eval_expression($msg);

            if (lc(weechat::config_get_plugin('show_deny_message')) eq 'off' or lc(weechat::config_get_plugin('quiet') eq 'on'))
            {
                # According to the RFC 1459, automatic messages must not be sent as response to NOTICEs and currently it might be possible to get in loop of automatic away messages or something similar.
#                weechat::command( '', "/mute -all /msg -server $server $query_nick $msg " );
                weechat::command( '', "/mute -all /notice -server $server $query_nick $msg " );
            }
            else        # show deny message!
            {
#                weechat::command( '', "/mute -all /msg -server $server $query_nick $msg " );
                weechat::command( '', "/mute -all /notice -server $server $query_nick $msg " );
                if ( newsbar() eq "1" and lc(weechat::config_get_plugin('msgbuffer')) eq 'newsbar' ) {
                    weechat::command( '',
                    "/newsbar  add --color lightred [QUERY-WARN]\t"     # $color $category
                    . irc_nick_find_color($query_nick)
                    . $query_nick
                    . weechat::color('reset') . '@'
                    . irc_nick_find_color($server)
                    . $server
                    . weechat::color('reset')
                    . ": "
                    . weechat::color('bold')
                    . "$msg");
                }
                else {
                    weechat::print($buf_pointer,"$SCRIPT\t"."$query_nick"."@"."$server: $msg");
                }
            }
            # counter for how many blocked messages
            $Blocked{$server.".".$query_nick} = 0;
        }
            $Blocked{$server.".".$query_nick}++;
    }
    else
    {
        return $arg;
    }

    # return empty string - don't create a new buffer
    return '';
}

# add nick to whitelist
sub _add {
    my $arg = shift;
    my $temporary_mode = shift;
    my $temporary_txt = "";

    if ( defined $arg ) {
        foreach ( split( / +/, $arg ) ) {
            my ($server,$nick);
            ($server,$nick) = split(/\./,$_);
            if (not defined $nick){
                $nick = $server;
                $server = weechat::buffer_get_string(weechat::current_buffer(),"localvar_server");
                if ($server eq ""){
                    weechat::print( '', "Server missing for: '".
                                        irc_nick_find_color($nick).
                                        $nick . weechat::color('reset') . "'");
                    return;
                }
            }
            $Last_query_nick = undef if ( defined $Last_query_nick and $server.".".$nick eq $Last_query_nick );
            $Allowed{$server.".".$nick} = $temporary_mode;
            delete $Blocked{$server.".".$nick};
            $temporary_txt = " (temporary)" if ($temporary_mode == 2);
            weechat::print( '', "Allow" . $temporary_txt ." queries for: '".
                                weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                weechat::color('reset') . "." .
                                irc_nick_find_color($nick).
                                $nick . weechat::color('reset') . "'");
        }
        whitelist_save();
    } elsif ( defined $Last_query_nick and not exists $Allowed{$Last_query_nick} ) {
        $Allowed{$Last_query_nick} = $temporary_mode;
        my ($server,$nick) = split(/\./,$Last_query_nick);
        delete $Blocked{$Last_query_nick};
        weechat::print( '', "Allow" . $temporary_txt . " queries for: '".
                            weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                            weechat::color('reset') . "." .
                            irc_nick_find_color($nick).
                            $nick . weechat::color('reset') . "'");
        $Last_query_nick = undef;
        whitelist_save();
        # FIXME: open query window
    } else {
        weechat::print( '', "There is no nick to be added to the whitelist");
    }
}

# handle hooks {{{
{
my %Hooks;

sub qb_hooked { %Hooks };

sub qb_hook {
    return 1 if qb_hooked();

    $Hooks{query}          = weechat::hook_command_run( '/query *', 'qb_query', "" );
    $Hooks{msg}            = weechat::hook_command_run( '/msg *',   'qb_msg',   "" );
    $Hooks{modifier_in}    = weechat::hook_modifier( "irc_in_privmsg", "modifier_irc_in_privmsg", "" );
    $Hooks{completion_del} = weechat::hook_completion("perl_query_blocker_del", "query blocker completion_del", "query_blocker_completion_del_cb", "");
    $Hooks{completion_add} = weechat::hook_completion("perl_query_blocker_add", "query blocker completion_add", "query_blocker_completion_add_cb", "");

    # FIXME handle hook errors (hook_ returns NULL := '')
    DEBUG("cant hook completion for del argument")      if $Hooks{completion_del}    eq '';
    DEBUG("cant hook completion for add argument")      if $Hooks{completion_add}    eq '';
    DEBUG("cant hook command '/query'")                 if $Hooks{query}    eq '';
    DEBUG("cant hook command '/msg'")                   if $Hooks{msg}      eq '';
    DEBUG("cant hook modifier 'irc_in_privmsg'")        if $Hooks{modifier_in} eq '';

    return 0;
}

sub qb_unhook {
    return 1 unless qb_hooked();

    # FIXME handle hook errors (hook_ returns NULL := '')
    weechat::unhook( $Hooks{query} );
    weechat::unhook( $Hooks{msg} );
    weechat::unhook( $Hooks{modifier_in} );
    weechat::unhook( $Hooks{completion_del} );
    weechat::unhook( $Hooks{completion_add} );
    undef %Hooks;

    return 0;
}
} # }}}

sub query_blocker_completion_del_cb{
    my ($data, $completion_item, $buffer, $completion) = @_;
    foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed ) {
        weechat::hook_completion_list_add($completion, $_,1, weechat::WEECHAT_LIST_POS_SORT);
    }
return weechat::WEECHAT_RC_OK;
}
sub query_blocker_completion_add_cb{
    my ($data, $completion_item, $buffer, $completion) = @_;
    foreach (reverse keys %Blocked) {
        weechat::hook_completion_list_add($completion, $_,1, weechat::WEECHAT_LIST_POS_SORT);
    }
return weechat::WEECHAT_RC_OK;
}


sub toggled_by_set {
    my ( $script, $option, $value ) = @_;

    if ( $value ne 'on' ) { # all values different to 'on' will disable blocking
        if ( $value ne 'off' ) {
            weechat::config_set_plugin( $option, "off" );
            DEBUG("wrong value for option '$option', falling back to 'off'");
        }
        if ( qb_hooked() ) {    # enabled?
            qb_unhook();
            weechat::print( '', "$COMMAND: disabled" );
        } else {
            weechat::print( '', "$COMMAND: already disabled" );
        }
    } else {    # enable blocking
        unless ( qb_hooked() ) {
            qb_hook();
            weechat::print( '', "$COMMAND: private messages will be blocked" );
        } else {
            weechat::print( '', "$COMMAND: private messages already blocked" );
        }
    }

    return weechat::WEECHAT_RC_OK;
}

sub query_blocker {
    my ( $data, $buffer, $args ) = ( $_[0], $_[1], $_[2] );

    if ( $args =~ /^o(n|ff)$/ ) {
        weechat::config_set_plugin( 'block_queries', $args );
    } elsif ( $args eq 'status' ) {
        if ( weechat::config_get_plugin( 'block_queries') eq 'on' ) {
            weechat::print( '', "$COMMAND: private messages will be blocked");
        } else {
            weechat::print( '', "$COMMAND: disabled");
        }
    } elsif ( $args eq 'reload' ) {
        whitelist_read();
    } else {
        my ( $cmd, $arg ) = ( $args =~ /(.*?)\s+(.*)/ );
        $cmd = $args unless $cmd;
        if ( $cmd eq 'list' ) {
            if ( defined $arg and $arg eq 'last' ) {
                if (defined $Last_query_nick) {
                    my ($server,$nick) = split(/\./,$Last_query_nick);
                    weechat::print( '', "Last blocked nick: '".
                                        weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                        weechat::color('reset') . "." .
                                        irc_nick_find_color($nick).
                                        $nick . weechat::color('reset') . "'");
                } else {
                    weechat::print( '', "No blocked nicks");
                }
            } else {
                my $n = keys %Allowed;
                weechat::print( '', "Allowed nicks for queries ($n):" );
                foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed ) {
                    my ($server,$nick) = split(/\./,$_);
                    my $temporary_txt = "";
                    $temporary_txt = "  (temporary)" if ( $Allowed{$server.".".$nick} == 2);
                    weechat::print( '', "   ".
                                        weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                        weechat::color('reset') . "." .
                                        irc_nick_find_color($nick).
                                        $nick . weechat::color('reset').
                                        $temporary_txt);
                }
            }
        } elsif ( $cmd eq 'blocked' ) {
            if ( keys %Blocked ) {
                if ( defined $arg and $arg eq 'clear' ) {
                    weechat::print( '', "Removing blocked state from:");
                    foreach ( sort { "\L$a" cmp "\L$b" } keys %Blocked ) {
                        my ($server,$nick) = split(/\./,$_);
                        weechat::print( '', "   " .
                                            weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                            weechat::color('reset') . "." .
                                            irc_nick_find_color($nick) . $nick .
                                            weechat::color('reset') . " (#$Blocked{$_})");
                        delete $Blocked{$_};
                    }
                } else {
                    weechat::print( '', "Queries of this nicks have been blocked:" );
                    foreach ( sort { "\L$a" cmp "\L$b" } keys %Blocked ) {
                        my ($server,$nick) = split(/\./,$_);
                        weechat::print( '', "   " .
                                            weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                            weechat::color('reset') . "." .
                                            irc_nick_find_color($nick) . $nick .
                                            weechat::color('reset') . " (#$Blocked{$_})");
                    }
                }
            } else {
                weechat::print( '', "No nicks have been blocked" );
            }
        } elsif ( $cmd eq 'add' ) {
            _add($arg,1);
        }elsif ( $cmd eq 'del' and defined $arg ) {
            foreach ( split( / +/, $arg ) ) {
                if (exists $Allowed{$_} ) {
                    delete $Allowed{$_};
                    my ($server,$nick) = split(/\./,$_);
                    weechat::print( '', "Nick removed from whitelist: '".
                                        weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).$server .
                                        weechat::color('reset') . "." .
                                        irc_nick_find_color($nick) . $nick .
                                        weechat::color('reset') . "'");
                } else {
                    weechat::print( '', "Can't remove nick, not in whitelist: '" . irc_nick_find_color($_) . $_ . weechat::color('reset') . "'");
                }
            }
            whitelist_save();
        }
    }
    return weechat::WEECHAT_RC_OK;
}

sub _get_nick {
    my ($l) = shift;
    $l =~ s/\/(query|msg) +//;

    if ($l =~ /-server/ ) {
        $l =~ s/-server \w+ //;
    }
    
    $l =~ s/ .*$//;

    return $l;
}

# /query
sub qb_query {
    my ($data, $buffer, $command) = @_;
    my $server = weechat::buffer_get_string($buffer,"localvar_server");
    return weechat::WEECHAT_RC_OK if ($server eq "");

    my $n = _get_nick($command);
    return weechat::WEECHAT_RC_OK if (lc($n) eq "nickserv" or lc($n) eq "chanserv");
    my $temporary_mode = 1;
    $temporary_mode = 2 if (weechat::config_get_plugin('temporary_mode') eq "on");
    _add($server.".".$n,$temporary_mode) unless nick_allowed($server.".".$n);

    return weechat::WEECHAT_RC_OK;
}

# add nick as allowed if responce isn't auto reply
sub qb_msg {
    my ($data, $buffer, $command) = @_;
    my $server = weechat::buffer_get_string($buffer,"localvar_server");
    return weechat::WEECHAT_RC_OK if ($server eq "");

    my ($msg) = $command =~ /^\/msg -server .*?\s.*?\s(.*)/;
    return weechat::WEECHAT_RC_OK if (not defined $msg);
    my $n = _get_nick($_[2]);
    return weechat::WEECHAT_RC_OK if (lc($n) eq "nickserv" or lc($n) eq "chanserv");
    my $prefix = weechat::config_get_plugin('auto_message_prefix');

    my $temporary_mode = 1;
    $temporary_mode = 2 if (weechat::config_get_plugin('temporary_mode') eq "on");
    _add($server.".".$n,$temporary_mode) unless nick_allowed($server.".".$n) or $msg =~ /^$prefix/;

    return weechat::WEECHAT_RC_OK;
}

sub query_blocker_buffer_open
{
    my $query_blocker_buffer = weechat::buffer_new($SCRIPT, "query_blocker_buffer_input", "", "query_blocker_buffer_close", "");

    if ($query_blocker_buffer ne "")
    {
        if (weechat::config_get_plugin("hotlist_show") eq "off"){
            weechat::buffer_set($query_blocker_buffer, "notify", "0");
        }elsif (weechat::config_get_plugin("hotlist_show") eq "on"){
            weechat::buffer_set($query_blocker_buffer, "notify", "3");
        }
        weechat::buffer_set($query_blocker_buffer, "title", $SCRIPT);
        # logger
        weechat::buffer_set($query_blocker_buffer, "localvar_set_no_log", "1") if (weechat::config_get_plugin("logger") eq "off");
    }
    return $query_blocker_buffer;
}
sub query_blocker_buffer_close
{
    return weechat::WEECHAT_RC_OK;
}
sub query_blocker_buffer_input
{
    return weechat::WEECHAT_RC_OK;
}

sub buffer_closing_cb
{
    my ($data, $signal, $signal_data) = @_;
    return weechat::WEECHAT_RC_OK if ( weechat::buffer_get_string($signal_data, "localvar_type" ne "private"));
    my $name = weechat::buffer_get_string($signal_data, "localvar_name");
    foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed )
    {
        my ($server,$nick) = split(/\./,$_);
        delete $Allowed{$_} if ( defined $Allowed{$_} and $Allowed{$server.".".$nick} == 2 and $name eq $server.".".$nick );
    }
    return weechat::WEECHAT_RC_OK;
}

# -----------------------------------------------------------------------------
#
if ( weechat::register( $SCRIPT, $AUTHOR, $VERSION, $LICENSE, $DESCRIPTION, "", "" ) ) {
    weechat::hook_command( $COMMAND, $DESCRIPTION, $ARGS_HELP, $CMD_HELP, $COMPLETITION, $CALLBACK, "" );
    $weechat_version = weechat::info_get("version_number", "");
    if ( ($weechat_version ne "") && (weechat::info_get("version_number", "") < 0x00040200) ) {
        weechat::print("",weechat::prefix("error")."$SCRIPT: needs WeeChat >= 0.4.2. Please upgrade: http://www.weechat.org/");
        weechat::command("","/wait 1ms /perl unload $SCRIPT");
  }

    if ( weechat::config_get_plugin("whitelist") eq '' ) {
        weechat::config_set_plugin( "whitelist", weechat::info_get( "weechat_dir", "" ) . "/" . $SETTINGS{"whitelist"} );
    }
    while ( my ( $option, $default_value ) = each(%SETTINGS) ) {
        weechat::config_set_plugin( $option, $default_value )
          if weechat::config_get_plugin($option) eq "";
    }

    if ( whitelist_read() ){
        weechat::command("","/wait 1ms /perl unload $SCRIPT");
        return;
    }

    weechat::print( '', "$COMMAND: loaded whitelist '" . weechat::config_get_plugin( "whitelist" ) . "'");

    ignore_auto_message_read();

    weechat::hook_signal("buffer_closing","buffer_closing_cb","");
    weechat::hook_config( "plugins.var.perl.$SCRIPT.block_queries", 'toggled_by_set', $SCRIPT );
    if ( ($weechat_version ne "") && (weechat::info_get("version_number", "") >= 0x00030500) ) {    # v0.3.5
        foreach my $option ( keys %help_desc ){
            weechat::config_set_desc_plugin( $option,$help_desc{$option} );
        }
    }

    if ( lc(weechat::config_get_plugin('block_queries') eq "on")) {
        qb_hook();
        weechat::print( '', "$COMMAND: private messages will be blocked");
        if ( lc(weechat::config_get_plugin('open_on_startup')) eq "on" and lc(weechat::config_get_plugin('msgbuffer')) eq "buffer" )
        {
            my $buf_pointer = weechat::buffer_search("perl",$SCRIPT);
            $buf_pointer = query_blocker_buffer_open() if ( $buf_pointer eq "" );
}
    } else {
        weechat::print( '', "$COMMAND: disabled");
    }
}
