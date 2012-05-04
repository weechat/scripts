# -----------------------------------------------------------------------------
#
# query_blocker.pl - Simple blocker for private messages (i.e. spam).
#
# -----------------------------------------------------------------------------
# Copyright (c) 2009-2012 by rettub <rettub@gmx.net>
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
# - requires WeeChat 0.3.2 or newer
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
# -----------------------------------------------------------------------------
# History:
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
# FIXME
#   - add 'mynick' to list - needed?
#
# TODO
#   - make Auto-Messages configurable

use Data::Dumper;
use warnings;
use strict;

my $SCRIPT      = 'query_blocker';
my $AUTHOR      = 'rettub <rettub@gmx.net>';
my $VERSION     = '0.5';
my $LICENSE     = 'GPL3';
my $DESCRIPTION = 'Simple blocker for private message (i.e. spam)';
my $COMMAND     = "query_blocker";             # new command name
my $ARGS_HELP   = "<on> | <off> | <status> | <list [last]> | <add [nick_1 [... [nick_n]]]> | <del nick_1 [... [nick_n]]> | <reload> | <blocked [clear]>";
my %help_desc = ( "block_queries"       => "to enable or disable $COMMAND (default: 'off')",
                  "quiet"               => "will send auto reply about blocking, but don't send any notice to you. (default: 'off')",
                  "show_deny_message"   => "show you the deny message, sent to user. (default: 'off')",
                  "show_hint"           => "show hint how to allow queries for nick. (default: 'on')",
                  "show_nick_only"      => "only show nick and server. (default: 'off')",
                  "whitelist"           => "path/file-name to store/read nicks not to be blocked (default: qb-whitelist.txt)",
                  "auto_message"        => "messages to inform user that you don't like to get private messages without asking first. '%N' will be replaced with users nick.",
                  "auto_message_prefix" => "Prefix for auto message, may not be empty!",
                  "msgbuffer"           => "buffer used to display $SCRIPT messages (current = current buffer, private = private buffer, weechat = weechat core buffer, server = server buffer, buffer = $SCRIPT buffer, highmon = highmon buffer)",
                  "logger"              => "logger status for $SCRIPT buffer (default: 'off')",
                  "hotlist_show"        => "$SCRIPT buffer appear in hotlists (status bar/buffer.pl) (default: 'off')",
                  "open_on_startup"     => "open $SCRIPT buffer on startup. option msgbuffer has to be set to 'buffer' (default: 'off')",
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

By default all private messages (/query, /msg) from nicks not in the whitelist will be blocked.
 - to allow all private message, $SCRIPT can be disabled, type '/$COMMAND off'.
 - to allow private messages from certain nicks, put them into the whitelist, type '/$COMMAND add nick' (you can use nick-completion).
 - to remove a nick from the whitelist, type '/$COMMAND del nick' (you can use nick-completion).

NOTE: If you load $SCRIPT the first time, blocking of private messages is disabled, you have to enable blocking, type '/$COMMAND on'.
EO_HELP

my $COMPLETITION  = "on %-||off %-||status %-||list %-||add %(perl_query_blocker_add) %-||del %(perl_query_blocker_del) %-||reload %-||blocked %-";
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
    "whitelist"     => "qb-whitelist.txt",
    "auto_message"  => "I'm using a query blocking script, please wait while i whitelist you!",
    "auto_message_prefix" => "Auto-Message: ",
    "msgbuffer"     => "server", # current, private, weechat, buffer, highmon
    "logger"        => "off",
    "hotlist_show"  => "off",
    "open_on_startup"  => "off",
);

# FIXME store server too?
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

sub nick_allowed { return exists $Allowed{ $_[0] }; }

sub whitelist_read {
    my $whitelist = weechat::config_get_plugin( "whitelist" );
    return unless -e $whitelist;
    open (WL, "<", $whitelist) || DEBUG("$whitelist: $!");
	while (<WL>) {
		chomp;
		$Allowed{$_} = 1  if length $_;
	}
	close WL;
}

sub whitelist_save {
    my $whitelist = weechat::config_get_plugin( "whitelist" );
    open (WL, ">", $whitelist) || DEBUG("write whitelist: $!");
    print WL "$_\n" foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed );
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
    if ( $buf_pointer eq "" ){
        if ( $server eq "" ){
            $buf_pointer = weechat::buffer_search_main();
        }else{
            $buf_pointer = fallback($server);
        }
    }
    return $buf_pointer if (lc(weechat::config_get_plugin('quiet') eq "on"));

    if (weechat::config_get_plugin('show_nick_only') eq 'off') {
        $message = ": $message";
    }else{
        $message = "";
    }
    weechat::print($buf_pointer,"$prefix_network\t"
                                .irc_nick_find_color($nick).$nick
                                .weechat::color('reset')
                                ." tries to start a query on "
                                .irc_nick_find_color($server).$server
                                .weechat::color('reset')
                                .$message );
    
    weechat::print($buf_pointer,"$prefix_network\t"
                                ."to allow query: /$COMMAND add "
                                .irc_nick_find_color($nick).$nick
                                .weechat::color('reset') ) unless (weechat::config_get_plugin('show_hint') eq 'off');
    return $buf_pointer;
}

sub fallback_buffer{
    my $server = @_;
    my $fallback = weechat::config_string( weechat::config_get("irc.look.msgbuffer_fallback") );
    my $buf_pointer;
    if ( $fallback eq "current" )
    {
        my $buf_pointer = weechat::current_buffer();
    }elsif ( $fallback eq "server" )
    {
        $buf_pointer = weechat::buffer_search("irc","server".".".$server);
    }
    return $buf_pointer;
}

sub modifier_irc_in_privmsg {
    my ( $data, $signal, $server, $arg ) = @_;
    my $my_nick = weechat::info_get( 'irc_nick', $server );

    # check for query message
    if ( $arg =~ m/:(.+?)\!.+? PRIVMSG $my_nick :(\w.*)/ ) {
        my $query_nick = $1;
        my $query_msg  = $2;

        # if nick is allowed to send queries, let WeeChat handle the query
        return $arg if nick_allowed($query_nick);

        $Last_query_nick = $query_nick;
        my $buf_pointer;
        unless ( exists $Blocked{$query_nick} ) {
            unless (weechat::config_get_plugin('quiet') eq 'on') {
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

            $msg =~ s/%N/$query_nick/g;
            if (lc(weechat::config_get_plugin('show_deny_message')) eq 'off' or lc(weechat::config_get_plugin('quiet') eq 'on'))
            {
                weechat::command( '', "/mute -all /msg -server $server $query_nick $msg " );
            }else
            {
                weechat::command( '', "/mute -all /msg -server $server $query_nick $msg " );
                weechat::print($buf_pointer,"$SCRIPT\t"."$query_nick"."@"."$server: $msg");
            }
            $Blocked{$query_nick} = 0;
        }
            $Blocked{$query_nick}++;
    } else {
        return $arg;
    }

    # return empty string - don't create a new buffer
    return '';
}

sub _add {
    my $arg = shift;

    if ( defined $arg ) {
        foreach ( split( / +/, $arg ) ) {
            $Last_query_nick = undef if ( defined $Last_query_nick and $_ eq $Last_query_nick );
            $Allowed{$_} = 1;
            delete $Blocked{$_};
            weechat::print( '', "Allow queries for: '" . irc_nick_find_color($_) . $_ . weechat::color('reset') . "'");
        }
        whitelist_save();
    } elsif ( defined $Last_query_nick and not exists $Allowed{$Last_query_nick} ) {
        $Allowed{$Last_query_nick} = 1;
        delete $Blocked{$Last_query_nick};
        weechat::print( '', "Allow queries for: '" . irc_nick_find_color($Last_query_nick) . $Last_query_nick . weechat::color('reset') . "'");
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

    $Hooks{query}    = weechat::hook_command_run( '/query *', 'qb_query', "" );
    $Hooks{msg}      = weechat::hook_command_run( '/msg *',   'qb_msg',   "" );
    $Hooks{modifier} = weechat::hook_modifier( "irc_in_privmsg", "modifier_irc_in_privmsg", "" );
    $Hooks{completion_del} = weechat::hook_completion("perl_query_blocker_del", "query blocker completion_del", "query_blocker_completion_del_cb", "");
    $Hooks{completion_add} = weechat::hook_completion("perl_query_blocker_add", "query blocker completion_add", "query_blocker_completion_add_cb", "");

    # FIXME handle hook errors (hook_ returns NULL := '')
    DEBUG("cant hook completion for del argument")      if $Hooks{completion_del}    eq '';
    DEBUG("cant hook completion for add argument")      if $Hooks{completion_add}    eq '';
    DEBUG("cant hook command '/query'")                 if $Hooks{query}    eq '';
    DEBUG("cant hook command '/msg'")                   if $Hooks{msg}      eq '';
    DEBUG("cant hook modifier 'irc_in_privmsg'")        if $Hooks{modifier} eq '';

    return 0;
}

sub qb_unhook {
    return 1 unless qb_hooked();

    # FIXME handle hook errors (hook_ returns NULL := '')
    weechat::unhook( $Hooks{query} );
    weechat::unhook( $Hooks{msg} );
    weechat::unhook( $Hooks{modifier} );
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
                    weechat::print( '', "Last blocked nick: '" . irc_nick_find_color($Last_query_nick) . $Last_query_nick . weechat::color('reset') . "'");
                } else {
                    weechat::print( '', "No blocked nicks");
                }
            } else {
                my $n = keys %Allowed;
                weechat::print( '', "Allowed nicks for queries ($n):" );
                foreach ( sort { "\L$a" cmp "\L$b" } keys %Allowed ) {
                    weechat::print( '', "   " . irc_nick_find_color($_) . $_ );
                }
            }
        } elsif ( $cmd eq 'blocked' ) {
            if ( keys %Blocked ) {
                if ( defined $arg and $arg eq 'clear' ) {
                    foreach ( sort { "\L$a" cmp "\L$b" } keys %Blocked ) {
                        weechat::print( '', "Removing blocked state from" . irc_nick_find_color($_) . $_ );
                        delete $Blocked{$_};
                    }
                } else {
                    weechat::print( '', "Queries of this nicks have been blocked:" );
                    foreach ( sort { "\L$a" cmp "\L$b" } keys %Blocked ) {
                        weechat::print( '', "   " . irc_nick_find_color($_) . $_ . weechat::color('reset') . " (#$Blocked{$_})");
                    }
                }
            } else {
                weechat::print( '', "No nicks have been blocked" );
            }
        } elsif ( $cmd eq 'add' ) {
            _add($arg);
        }elsif ( $cmd eq 'del' and defined $arg ) {
            foreach ( split( / +/, $arg ) ) {
                if (exists $Allowed{$_} ) {
                    delete $Allowed{$_};
                    weechat::print( '', "Nick removed from whitelist: '" . irc_nick_find_color($_) . $_ . weechat::color('reset') . "'");
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

sub qb_query {
    my $n = _get_nick($_[2]);
    _add($n) unless nick_allowed($n);

    return weechat::WEECHAT_RC_OK;
}

# add nick as allowed if responce isn't auto reply
sub qb_msg {
    my ($msg) = $_[2] =~ /^\/msg -server .*?\s.*?\s(.*)/;
    my $n = _get_nick($_[2]);
    my $prefix = weechat::config_get_plugin('auto_message_prefix');

    _add($n) unless nick_allowed($n) or $msg =~ /^$prefix/;

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

# -----------------------------------------------------------------------------
#
if ( weechat::register( $SCRIPT, $AUTHOR, $VERSION, $LICENSE, $DESCRIPTION, "", "" ) ) {
    weechat::hook_command( $COMMAND, $DESCRIPTION, $ARGS_HELP, $CMD_HELP, $COMPLETITION, $CALLBACK, "" );
    $weechat_version = weechat::info_get("version_number", "");
    if ( ($weechat_version ne "") && (weechat::info_get("version_number", "") < 0x00030200) ) {
        weechat::print("",weechat::prefix("error")."$SCRIPT: needs WeeChat >= 0.3.2. Please upgrade: http://www.weechat.org/");
        weechat::command("","/wait 1ms /perl unload $SCRIPT");
  }

    if ( weechat::config_get_plugin("whitelist") eq '' ) {
        weechat::config_set_plugin( "whitelist", weechat::info_get( "weechat_dir", "" ) . "/" . $SETTINGS{"whitelist"} );
    }
    while ( my ( $option, $default_value ) = each(%SETTINGS) ) {
        weechat::config_set_plugin( $option, $default_value )
          if weechat::config_get_plugin($option) eq "";
    }
    whitelist_read();
    weechat::print( '', "$COMMAND: loaded whitelist '" . weechat::config_get_plugin( "whitelist" ) . "'");

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

# vim: ai ts=4 sts=4 et sw=4 tw=0 foldmethod=marker :
