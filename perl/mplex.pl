#
# Copyright (c) 2010 by rettub <rettub <at> gmx <dot> net>
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
# ----------------------------------------------------------------------------
#
# I have written it in perl, cause I like perl and don't like python :)
#
# - Simple remote control of multiplexer,
# - Checking of detach/attach (TMUX, GNU screen)
# - Optional: setting of the appropriate away status,
#   executing of 3rd party script commands,
#   emitting Signals ('mplex_detached', 'mplex_attached')
#   if multiplexer state has changed.
#
# * Based on idea of the script screen_away.pl for irssi written by
#   Andreas 'ads' Scherbaum
# * Idea for "Don't touch away stats for servers which have user defined 'away'"
#   shamelessly stolen from Xt's script screen_away.py for weechat.
# 
# * This script extends those scripts mentioned above by various errorchecks,
#   emitting Signals, command queue executed on attach/detach, and a simple command
#   to interact with Gnu Screen itself.
#
# ----------------------------------------------------------------------------
#
# TODO  - switch2window for TMUX
#       - paste from GNU screen into weechat (nearly done in dev)
#
# Changelog
#
# Version v0.03 04.02.2010
#
#   * enable arg 'switch2window' for tmux
#
# Version v0.02 04.02.2010
#
#   * FIX: use '-S' to check for TMUX socket
#   * added 'Known issues' for two TMUX sessions impossible to get detached state
#   * whitespace fixes,typo
#
# Version v0.01 02.02.2010
#
#   * initial version 

use 5.006;


use strict;
use warnings;
use Data::Dumper;

my $Version   = '0.03';
my $SCRIPT    = 'mplex';
my $AUTHOR    = 'rettub';
my $LICENSE   = "GPL3";
my $COMMAND   = $SCRIPT;
my $ARGS_HELP = "[switch2window <window>]";

sub version {
    $Version;
}

# {{{ helpers
my $DEBUG=0;
sub DEBUG {
    weechat::print( '', "***\t" . "[" . weechat::color('reset') . "$SCRIPT:" . weechat::color('green') . "]" . weechat::color('reset') . " $_[0]" )
      if $DEBUG or $_[1];
}

sub _info {
    weechat::print( '',
        weechat::color('green') . "[" . weechat::color('reset') . "$SCRIPT:" . weechat::color('green') . "]" . weechat::color('reset') . " $_[0]" )
      if weechat::config_get_plugin('verbose') eq 'on' or $_[1];
}

sub _error {
    weechat::print( '',
          weechat::prefix("error")
       	. weechat::color('green') . "[" . weechat::color('reset') . "$SCRIPT:" . weechat::color('green') . "]" . weechat::color('reset') . " $_[0]" );
}
#}}}

# settings / global vars {{{
my %Hooks  = ();

# script options
my %Settings = (
    'change_away_stat' => 'on',
    'away_msg'         => 'Detached head',
    'interval'         => '60',              # check multiplexer status in sec
    'verbose'          => 'on',
    'emit_signals'     => 'off',
    'exec_script_cmds' => 'off',
);

# }}}

# help {{{
my $info = "Simple remote control of multiplexer,"
." checking of detach/attach (TMUX, GNU screen)."
." Optional: setting of the appropriate away status, executing of 3rd party script commands, emitting Signals if multiplexer state has changed.";

sub _cur_default {
    my $a = $_[0];
    weechat::config_get_plugin($a) ne $Settings{$a}
      ? "'" . weechat::config_get_plugin($a) . "' (default:  \'" . $Settings{$a} . "\')"
      : "\'$Settings{$a}\'";
}

sub help {
   return 
     "\n"
    ."config vars:\n"
    ."  change_away_stat:  Enable/disable changing of away status on detach/attach.\n"
    ."                     current: " . _cur_default('change_away_stat') . "\n"
    ."  away_msg:          Away message used if deteached\n"
    ."                     current: " . _cur_default('away_msg') . "\n"
    ."  interval:          Interval in seconds for checking detach/attach.\n"
    ."                     current: " . _cur_default('interval') . "\n"
    ."  emit_signals:      Emit signals on detach/attach. (on/off)\n"
    ."                     The signals can be used by other scripts to act on detach/attach.\n"
    ."                     Signals:  mplex_detached, mplex_attached.\n"
    ."                     current: " . _cur_default('emit_signals') . "\n"
    ."  verbose:           Be a little noisy. (on/off)\n"
    ."                     current: " . _cur_default('verbose') . "\n"
    ."  exec_script_cmds:  Exec 3rd party script commands. (on/off)\n"
    ."                     current: " . _cur_default('exec_script_cmds') . "\n"
    ."  on_detachN:        \n"
    ."  on_attachN:        3rd party script commands to be executed on detach/attach (N is an integer (0, 1 ... n).\n"
    ."                     Values for the interger 'N' must be continuous without prefixed zero(s)!\n"
    ."                     Example settings to turn beep on/off depending on multiplexer attached state:\n"
    ."                       on_detach0 '/newsbar nobeep'\n"
    ."                       on_attach0 '/newsbar beep'\n"
    ."\n"
    ."\n"
    ."The script command 'switch2window' is intended to be used by other scripts or via key bindings\n"
    ."  Example key binding (I'm using newsbar :) :\n"
    ."      This will clear lines from newsbar matching '[RSS]', hide it  and switch directly to screens newsbeuter window\n"
    ."      /key bind meta-Oo => /newsbar clear \[RSS\]; /newsbar hide; /mplex switch2window newsbeuter\n" 
    ."\n"
    ."If a user has set the status 'away' for a server, this status wll not be touched! (Idea stolen from XTs screen_away) \n"
    ."\n"
    ."\n"
    ."Known issues:\n"
    ."  Don't know TMUX as well, I considered that starting a weechat within a (new and only) tmux session, then starting an \n"
    ."  second session in an other xterminal, detaching the first one (running weechat) - then there's no way to get the detached state \n"
    ."  for the 'weechat' session. The socket file /var/run//tmux/tmux-UID/default keeps its executable state. Sorry don't have any clue for\n"
    ."  a workaround. If any TMUX user can help - please tell me\n"
    ."\n"
    ."have fun...\n"
    ;
}

# }}}



# Terminal multiplexer stuff {{{
my %Server = ();
my %Socket = ();
use constant {
    DETACHED  => 0,
    ATTACHED  => 1,
};

sub mp_attached {
    get_mp_socket() unless defined $Socket{'socket'};
    return undef unless defined $Socket{'socket'};

    my (undef,undef,$stat) = stat($Socket{'socket'});
    return (($stat & 00100) != 0);
}

sub mp_switch2window {
    my $w = shift;

    return undef unless get_mp_socket();

    if ( $Socket{mp} eq 'screen' ) {
        `screen -S $Socket{session} -X select $w`;
    } else {
        my $err = `tmux selectw -t $Socket{'session_id'}:$w`;
        chomp $err;
        if ( length($err) ) {
            _error("Sorry, Dave I can't do that, $Socket{mp} throws an error: '" . weechat::color('red') . $err . weechat::color('reset') . "'");
        }
    }
}

{
my $mp_stat_old = undef;

sub remove_timer {
    if ( $_[0] ) {
        _error( $_[0] );
        _error( "check for " . ( defined $Socket{mp} ? $Socket{mp} : 'multiplexer' ) . " detach/attach disabled" );
    }

    if ( $Hooks{timer} ) {
        weechat::unhook( $Hooks{timer} );
        delete $Hooks{timer};
    }
}

sub init_timer {
    remove_timer();

    if ( get_mp_socket() ) {
        _info( "check for $Socket{mp} detach/attach activated (every " . weechat::config_get_plugin('interval') . " seconds)" ) if not defined $mp_stat_old;
        $Hooks{timer} = weechat::hook_timer( weechat::config_get_plugin('interval') * 1000, 0, 0, 'mp_timer', '' );

        $mp_stat_old = mp_attached();
    } else {
        DEBUG("weechat is not running inside a multiplexer, $SCRIPT is disabled");
    }
}

sub mp_timer {
    my $mp_stat = mp_attached();

    DEBUG( "##### mp_stat NOT DEFINED ####")  unless defined $mp_stat;

    return eval "weechat::WEECHAT_RC_OK" unless defined $mp_stat;

    if ( $mp_stat == ATTACHED and $mp_stat_old != ATTACHED ) {         # mp attached, unset away stat
        get_server();

	weechat::hook_signal_send("mplex_attached", weechat::WEECHAT_HOOK_SIGNAL_STRING, $Socket{mp}) if weechat::config_get_plugin('emit_signals') eq 'on';
        for my $server ( keys %Server ) {
            if ( $Server{$server}{user_away} ) {		       # away stat set by user? Don't touch!
                delete $Server{$server}{user_away};		       # delete user_away stat.
            } else {
                _info( "$Socket{mp} attached. Unsetting away status for server: $server" );
                weechat::command( $Server{$server}{buffer}, "/away" ) if weechat::config_get_plugin('change_away_stat') eq 'on';
            }
        }
	do_on_attach();
	init_timer();
    } elsif ( $mp_stat == DETACHED and $mp_stat_old != DETACHED ) {    # mp detached, set away stat
        get_server();

	weechat::hook_signal_send("mplex_detached", weechat::WEECHAT_HOOK_SIGNAL_STRING, $Socket{mp}) if weechat::config_get_plugin('emit_signals') eq 'on';
        for my $server ( keys %Server ) {
            if ( $Server{$server}{away} ) {			       # away stat set by user? Don't touch!
                $Server{$server}{user_away} = 1;		       # mark server
            } else {
                my $msg = weechat::config_get_plugin('away_msg');
                $msg = "not here..." unless length($msg);	       # we do need an away msg
                _info( "$Socket{mp} detached. Setting away status for server: $server" );
                weechat::command( $Server{$server}{buffer}, "/away $msg" ) if weechat::config_get_plugin('change_away_stat') eq 'on';
            }
        }
	do_on_detach();
	init_timer();
    }
    return eval "weechat::WEECHAT_RC_OK";
}
}

sub get_server {
    my $infolist = weechat::infolist_get( 'irc_server', '', '' );

    while ( weechat::infolist_next($infolist) ) {
        my $server = weechat::infolist_string( $infolist, 'name' );

        unless ( weechat::infolist_integer( $infolist, 'is_connected' ) == 1 ) {
            delete $Server{$server};
            next;
        }

        $Server{$server}{buffer} = weechat::infolist_pointer( $infolist, 'buffer' );
        $Server{$server}{away}   = weechat::infolist_integer( $infolist, 'is_away' );
    }
    weechat::infolist_free($infolist);
}

# FIXME improve checking for nested multiplexer eg. screen in screen
sub get_mp_socket {

    my $ret = undef;

    if ( $ENV{'STY'} and $ENV{'TMUX'} ) {
        remove_timer("can't handle nested multiplexer (e.g. tmux in GNU screen or via versa)");
        return $ret;
    } elsif ( $ENV{'STY'} ) {

        my $chk_cmd = `LC_ALL="C" screen -ls`;

        if ( $chk_cmd !~ /^No Sockets found/s ) {

            $Socket{mp}      = 'screen';
            $Socket{session} = $ENV{'STY'};
            $Socket{path}    = $chk_cmd;
            $Socket{path} =~ s/^.+\d+ Sockets? in ([^\n]+)\.\n.+$/$1/s;
            $Socket{'socket'} = $Socket{path} . '/' . $Socket{session};

            # GNU screen uses a named pipe
            if ( -p $Socket{'socket'} ) {

                $ret = 1;
            } else {
                chomp $chk_cmd;
                $chk_cmd =~ s/\s+/ /gm;

                #		$chk_cmd =~ s/\n/ -- /gm;
                remove_timer( "error accessing screen socket from: '" . weechat::color('cyan') . $chk_cmd . weechat::color('reset') . "'" );
            }
        }
    } elsif ( $ENV{'TMUX'} ) {
        $Socket{mp} = 'tmux';
        ( $Socket{'socket'}, $Socket{'server_pid'}, $Socket{'session_id'} ) = $ENV{'TMUX'} =~ /(.*?),(\d+?),(.*)/; # XXX session_id: contains digits only?
        ( $Socket{'path'}, $Socket{'session'} ) = ( $Socket{'socket'} =~ /(.*)\/(.*)/ );

        # TMUX uses a socket
        if ( -S $Socket{'socket'} ) {
            $ret = 1;
        } else {
            remove_timer("error accessing TMUX socket");
        }
    }
    return $ret;
}

# }}}

# weechat stuff {{{

sub mplex {
    my ($cmd, $arg) = split(' ', $_[2]);

    if ( $cmd eq 'switch2window' ) {
        mp_switch2window($arg);
	
    }

    # make perl happy if executed as a script within a shell
    return eval "weechat::WEECHAT_RC_OK";
}

my @On_detach=();
my @On_attach=();
sub init_on_mplex_arrays {
    my $i;

    @On_detach = ();
    for ( $i = 0 ; ; $i++ ) {
        last unless weechat::config_is_set_plugin("on_detach$i");
        push @On_detach, weechat::config_get_plugin("on_detach$i");
    }

    @On_attach = ();
    for ( $i = 0 ; ; $i++ ) {
        last unless weechat::config_is_set_plugin("on_attach$i");
        push @On_attach, weechat::config_get_plugin("on_attach$i");
    }

    return eval "weechat::WEECHAT_RC_OK";
}

sub do_on_attach {
    foreach(@On_attach) {DEBUG("On_attach: $_"); weechat::command('', $_);}
}

sub do_on_detach {
    foreach(@On_detach) {DEBUG( "On_attach: $_");weechat::command('', $_);}
}

sub init_config {
    while ( my ( $option, $default_value ) = each(%Settings) ) {
        weechat::config_set_plugin( $option, $default_value )
          if weechat::config_get_plugin($option) eq "";
    }
    init_on_mplex_arrays();
}

sub init_plugin {

    if ( weechat::register( $SCRIPT, $AUTHOR, $Version, $LICENSE, $info, "", "" ) ) {

        # Hooks
        $Hooks{cmd} = weechat::hook_command(
            $COMMAND, $info,, $ARGS_HELP,

            "switch2window <window>: switch to a certain multiplexer window. (Useful for key bindings)\n"
              . "                          <window> can be a window-name or a window-number\n"

              . help(),
            "switch2window", $COMMAND, ""
        );

        init_config();
        $Hooks{config} = weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".on_*", 'init_on_mplex_arrays', "" );
        init_timer();
    }
}
# }}}

# ----------------------------------------------------------------------------
# here we go...
    init_plugin();

# setlocal equalprg=perltidy\ -q\ -l=160
# # vim: tw=160 ai ts=4 sts=4 et sw=4  foldmethod=marker :
