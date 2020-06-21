# -----------------------------------------------------------------------------
#
# TONS OF THANKS TO FlashCode FOR HIS IRC CLIENT AND HIS SUPPORT ON #weechat
#
# -----------------------------------------------------------------------------
# Copyright (c) 2009-2014 by rettub <rettub@gmx.net>
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
# newsbar for weechat version 0.3.0 or later
#
# Listening for highlights and sends them to a bar.
#
#
# Usage:
#     see /help newsbar
#
# -----------------------------------------------------------------------------
# Download:
# http://github.com/rettub/weechat-plugins/raw/master/perl/newsbar.pl
# https://github.com/weechatter/weechat-scripts
# http://www.weechat.org/scripts/
# -----------------------------------------------------------------------------
# XXX Known bugs:
#     Bar must be redrawed if terminal size has changed (wrapping)
#     Wrapping starts to early if some locale/utf chars contained in message string
#
# More bugs? Would be surprised if not, please tell me!
#
# -----------------------------------------------------------------------------
# TODO Optional execute an external user cmd with args:
#        nick, channel, server, message, ... (date/time?)
#      Or write a special script for it.
#      Can be uesed for scripts using libnotify, make weechat speaking to you
#      (I use festival for it)
# TODO exclude nicks, channels, servers, ... by eg. user defined whitelists
#      and/or blacklists
# -----------------------------------------------------------------------------
#
# Changelog:
# Version 0.19 2020-06-21, Sébastien Helleu
#   * FIX: make call to bar_new compatible with WeeChat >= 2.9
#
# Version 0.18 2014-10-26, nils_2
#   * IMPROVED: use hook_print() instead of hook_signal() for private messages
#   * ADD: option "blacklist_buffers" (idea by Pixelz)
#   * ADD: option "highlights_current_channel" (idea by sjoshi)
#
# Version 0.17 2014-06-08, nils_2
#   * FIX: update bar when option weechat.bar.newsbar_title.color_fg changed (reported by: bpeak)
#   * IMPROVED: use weechat_string_eval_expression() for weechat.look.buffer_time_format
#
# Version 0.16 2014-04-10, nils_2
#   * ADD: own color settings
#   * FIX: update bar when script options changed
#
# Version 0.15 2013-12-03, nils_2
#   * FIX: display error with ${color:nnn} in weechat.look.buffer_time_format
#
# Version 0.14 2013-01-13, nils_2
#   * IMPROVED: new option "most_recent" (idea by swimmer)
#   * FIX: typo in help text
#
# Version 0.13 2012-02-13, nils_2
#   * FIX: display error with weechat.look.buffer_time_format (WeeChat >= 0.3.5)
#
# Version 0.12 2011-10-03, nils_2
#
#   * FIX: ACTION highlight (/me) did not work if flood_protection() was enabled.
#   * IMPROVED: flood_protection() will act if ’n’ nicks are mentioned in whole message and not only at beginning of message
#
# Version 0.11 2010-12-20, nils_2
#
#   * FIX function called before weechat::register()
#   * FIX find_color_nick, now using API function weechat::info_get("irc_nick_color")
#
# Version 0.10 2010-01-20
#
#   * FIX warning about undefined var
#   * examples for key bindings
#     - add 'bind'
#     - typo,
#     - new example
#   * remove usage in comments (not in sync)
#
# Version 0.09 2010-01-19
#
#   * FIX remove old debug code creating files in /tmp
#
# Version 0.08 2010-01-19
#
#   * protection for 'nick-flood'
#     new options: nick_flood_protection, nick_flood_max_nicks
#
#     It's annoying if bots enter channels printing all nicks.
#     newsbar can ignore those bots, for that
#      set nick_flood_protection 'on'
#
#   * added direkt download url
#   * newsbar: update TODO
#
# Version 0.07 2010-01-18
#
#   * newsbar: ignore private highlights if current buffer is private buffer for
#     nick sending message
#
# Version 0.06 2010-01-14
#   * fixes
#     - missing use of option 'beep_duration'
#
#   * new options
#     - ssh_key
#     - add arg '--beep' for '/newsbar add'
#
#   * others
#     - renamed option beep_ssh_host into ssh_host
#     - changed default values for beep_freq* to 1000
#     - more use of user configs for colors
#     - update script example for newsbeuter
#     - lowercase beep status
#     - colorize DEBUG, print script-name too
#     - set beep frequence of highlights in server buffer to option 'beep_freq_msg'
#     - newsbar: beautify local/remote state for 'beep'
#
# Version 0.05 2009-11-11
#   * new options:
#     - beep_duration: beep duration in milliseconds
#     - beep_cmd:      command to be executed on 'beeps' (can be any cmd)
#     - beep_ssh_host: host (and optional user) where remote beeps should be
#                      executed
#     - beep_remote:   beep on a remote host
#     - beep_duration: duration of beep
#     - beep_freq_channel,
#       beep_freq_private,
#       beep_freq_msg: beep frequences
#
#   * new commands:
#     - beep_local:    execute beep cmd on localhost
#     - beep_remote:   execute beep cmd on remote host using ssh
#     - beep, nobeep:  toggle beeps
#
#   - show state of config var: away_only
#   - use of global weechat-options for colors
#   - use same color for nicks as Weechat does
#
# Version 0.04 2009-09-07
#   - different beeps on highlights, can be turned on/off
#
# Version 0.03 2009-09-07
#   - fix: new api arguments (arg1 data-pointer)
#
# Version 0.02 2009-09-01
#   - quickfix for new api
#
# Version 0.01 2009-03-20
#   - hilights.pl partly rewritten and renamed it to newsbar.pl
#     (use a bar instead of a buffer)
#     newest version available at:
#     git://github.com/rettub/weechat-plugins.git
#   - based on an idea of Brandon Hartshorn (Sharn) to write highlights into an
#     extra buffer
#     Original script:
#     http: http://github.com/sharn/weechat-scripts/tree/master
#     git:  git://github.com/sharn/weechat-scripts.git

use Data::Dumper;
use Text::Wrap;
use POSIX qw(strftime);
use strict;
use warnings;

# constants
#
# script default options
my %SETTINGS = (
    "bar_name"               => "newsbar",
    "beeps"                  => "off",
    "beep_freq_channel"      => "1000",
    "beep_freq_private"      => "1000",
    "beep_freq_msg"          => "1000",
    "beep_duration"          => "20",
    "beep_cmd"               => "beep -f %F -l %L",
    "ssh_host"               => "",
    "ssh_key"                => "",
    "beep_remote"            => "off",
    "show_highlights"        => "on",
    "away_only"              => "off",
    "format_public"          => '%N.%C@%s',
    "show_priv_msg"          => "on",
    "format_private"         => '%N@%s',
    "show_priv_server_msg"   => "on",
    "remove_bar_on_unload"   => "on",
    "memo_tag_color"         => 'yellow',
    "bar_hidden_on_start"    => "1",
    "bar_auto_hide"          => "on",
    "bar_visible_lines"      => "4",
    "bar_seperator"          => "off",
    "bar_title"              => "Highlights",
    "colored_help"           => "on",
    "nick_flood_protection"  => 'off',
    "nick_flood_max_nicks"   => '4',
    "most_recent"            => "first",
    "debug"                  => "on",
    "color_status_name"      => 'white',
    "color_status_number"    => 'yellow',
    "color_server_msg_tag"   => 'magenta',
    "color_privmsg_tag"      => 'red',
    "color_info_msg_tag"     => 'cyan',
    "highlights_current_channel" => "on",
    "blacklist_buffers"      => "",
);

my $weechat_version;
my $SCRIPT              = "newsbar";
my $SCRIPT_VERSION      = "0.19";
my $SCRIPT_AUTHOR       = "rettub";
my $SCRIPT_LICENCE      = "GPL3";
my $SCRIPT_DESCRIPTION  = "Print highlights or text given by commands into bar 'NewsBar'. Auto popup on top of weechat if needed. 'beeps' can be executed local or remote";
my $COMMAND     = "newsbar";             # new command name
my $ARGS_HELP   = "<always> | <away_only> | <beep> | <nobeep> | <beep_local> | <beep_remote> | <clear [regexp]>"
                 ."| <memo [text]> | <add [--color color] text>"
                 ."| <toggle> | <hide> | <show>"
                 ."| <scroll_home> | <scroll_page_up> | <scroll_page_down> | <scroll_up> | <scroll_down> | <scroll_end>";
my $CMD_HELP    = <<EO_HELP;
Arguments:

    always:         enable highlights to bar always       (set config <c>away_only</c> = 'off').
    away_only:      enable highlights to bar if away only (set config <c>away_only</c> = 'on').
    beep:           enable beeps on highlights (set config <c>beeps</c> = 'on').
    nobeep:         disable beeps on highlights (set config <c>beeps</c> = 'off').
    beep_local:     execute beep cmd on localhost (set config <c>beeps_remote</c> = 'off').
    beep_remote:    execute beep cmd on remote host using ssh (set config <c>beeps_remote</c> = 'on').
    <c>clear [regexp]</c>: Clear bar '$SETTINGS{bar_name}'. Clear all messages.
                    If a perl regular expression is given, clear matched lines only.
    <c>memo [text]</c>:    Print a memo into bar '$SETTINGS{bar_name}'.
                    If text is not given, an empty line will be printed.

    <c>add [--color color] text</c>:
                    Print text formatted into bar '$SETTINGS{bar_name}'.
                    Useful to display text using the FIFO pipe of WeeChat (same
                    as weechat does for buffers).
                    Text given before an optional tab will be printed left to the
                    delemeter, all other text will be printed right to the
                    delemeter. If <c>--color weechat-color-name</c> is given, text
                    infront of a tab will be colored.
                    If text is not given, an empty line will be printed.
                    The best way to use this command is in a script called by e.g.
                    cron or newsbeuter (maybe using ssh from an other host).

                    Example (commandline):
                    \$ echo -e \\
                        "*/newsbar add --color lightred [WARN]\\tgit updated! Do: git fetch, rebuild weechat" \\
                        > ~/.weechat/weechat_fifo_$$
                    \$ echo "*/newsbar add simple message" > ~/.weechat/weechat_fifo_$$

                    Example (script for newsbeuter's 'notify-program'):
                    #/bin/sh
                    # file /bin/nb2newsbar.sh
                    # clear old lines containing [RSS], print newsbeuters notify
                    # XXX This script assumes that only one weechat-client is runnig on that host
                    # XXX depends on pgrep
                    #
                    # Example key binding to delete lines containing [RSS] and to
                    # hide newsbar at once:
                    #   key: </> on numeric keypad (check it for you with meta-k)
                    #   meta-Oo => /newsbar clear \[RSS\]; /newsbar hide
                    #
                    # related example settings in ~/.newsbeuter/config
                    # notify-format  "%d new articles (%n unread articles, %f unread feeds)"
                    # notify-program "~/bin/nb2newsbar.sh"
                    WPID=`pgrep weechat-curses
                    [ "x\$WPID" != "x" ] && echo -e "*/newsbar clear \\[RSS\\]\\n*/newsbar add --color brown [RSS]\\t\$@" \\
                                             > "\$HOME/.weechat/weechat_fifo_\$WPID"

    toggle,
    hide,           show,
    scroll_home,    scroll_end,
    scroll_page_up, scroll_page_down,
    scroll_up,      scroll_down:
                    Useful simple key bindings.

                    Example key bindings (all on numeric keypad, NUMLOCK := off):
                    <Return> /key bind meta-OM /newsbar <c>toggle</c>
                    <7>      /key bind meta-OU /newsbar <c>scroll_home</c>
                    <1>      /key bind meta-O\\ /newsbar <c>scroll_end</c>
                    <9>      /key bind meta-OZ /newsbar <c>scroll_page_up</c>
                    <3>      /key bind meta-O[ /newsbar <c>scroll_page_down</c>
                    <8>      /key bind meta-OW /newsbar <c>scroll_up</c>
                    <2>      /key bind meta-OY /newsbar <c>scroll_down</c>
                    <Alt><Return> /key bind meta-OM => /newsbar <c>clear</c>  (clear and hide)

                    Check for your keys with <alt>-k (meta-k)!

Config settings:

    beeps:                  Beep on highlights. ('on'/'off')
    beep_freq_channel:      frequence of beep (highlighted on a public channel).
                            default: '$SETTINGS{beep_freq_channel}'
    beep_freq_private:      frequence of beep (message on a private).
                            default: '$SETTINGS{beep_freq_private}'
    beep_freq_msg:          frequence of beep (highlighted on a private channel).
                            default: '$SETTINGS{beep_freq_msg}'
    beep_duration:          beep duration in milliseconds
                            default: '$SETTINGS{beep_duration}'
    beep_cmd:               command to be executed on 'beeps'
                            default: '$SETTINGS{beep_cmd}'
    beep_remote:            beep on a remote host (see: option <c>ssh_host</c>)
                            default: '$SETTINGS{beep_remote}'
    ssh_host:               host (and optional user) where remote beeps should
                            be executed
                            default: '$SETTINGS{ssh_host}'
    ssh_key:                ssh key (identity_file) for remote commands
                            (you can use ssh-agent instead, then there's no need for
                            this option)
                            default: '$SETTINGS{ssh_key}'
    away_only:              Collect highlights only if you're away.
                            default: '$SETTINGS{away_only}'
    highlights_current_channel:
                            handle highlight for current channel. ('on'/'off'/'away')
                            default: '$SETTINGS{highlights_current_channel}'
    show_highlights:        Enable/disable handling of public messages. ('on'/'off')
                            default: '$SETTINGS{show_highlights}'
    show_priv_msg:          Enable/disable handling of private messages. ('on'/'off')
                            default: '$SETTINGS{show_priv_msg}'
    show_priv_server_msg:   Enable/disable handling of private server messages. ('on'/'off')
                            (server responses to server commands including your nick
                             (i.e.: '/msg nickserv info'))
                            default: '$SETTINGS{show_priv_server_msg}'
    format_public:          Format-string for public highlights.
    format_private:         Format-string for private highlights.

                            Format-string:
                            %n : nick,    %N : colored nick
                            %c : channel, %C : colored channel  (public only)
                            %s : server
                            default public format:  '$SETTINGS{format_public}'
                            default private format: '$SETTINGS{format_private}'

    memo_tag_color:         Color of '[memo]' e.g.: 'black,cyan' fg: black, bg: cyan
                            default: '$SETTINGS{memo_tag_color}'
    remove_bar_on_unload:   Remove bar when script will be unloaded.
    bar_auto_hide:          Hide bar if empty ('on'/'off')
                            default: '$SETTINGS{bar_auto_hide}'
    bar_hidden_on_start:    Start with a hidden bar ('1'/'0')
                            default: '$SETTINGS{bar_hidden_on_start}'
    bar_visible_lines:      lines visible if bar is shown
                            default: '$SETTINGS{bar_visible_lines}'
    bar_seperator:          Show bar separator line ('on'/'off')
                            default: '$SETTINGS{bar_seperator}'
    bar_title:              Title of info bar
                            default: '$SETTINGS{bar_title}'

    colored_help:           Display colored help. If you don't like it, do:
                              /set plugins.var.perl.newsbar.colored_help off
                            then reload the script.
                            default: '$SETTINGS{colored_help}'
    nick_flood_protection:  Don't act on messages starting with mutiple nicks.
                            It's annoying if bots enter channels printing all
                            nicks.
                            default: '$SETTINGS{nick_flood_protection}'
    nick_flood_max_nicks:   If messages starts with #nick_flood_max_nicks or
                            more nicks, then it's assumed as nick_flood
                            default: '$SETTINGS{nick_flood_max_nicks}'
    most_recent:            display a new message in bar ('first'/'last')
                            default: '$SETTINGS{most_recent}'
    blacklist_buffers:      comma-separated list of channels to be ignored (e.g. freenode.#weechat,irc_dcc.*)
    debug:                  Show some debug/warning messages on failure. ('on'/'off').
                            default: '$SETTINGS{debug}'

EO_HELP

my $COMPLETITION  =
"always|away_only|beep|nobeep|beep_local|beep_remote|clear|memo|add|toggle|hide|show|scroll_down|scroll_up|scroll_page_down|scroll_page_up|scroll_home|scroll_end";
my $CALLBACK      = $COMMAND;
my $CALLBACK_DATA = undef;

# global vars
my $Bar;
my $Bar_title;
my $Bar_title_name = 'newsbar_title';
my @Bstr=();
my $Baway="";
my $Bar_hidden=undef;
my $Beeps="";
my $Beep_freq_ch = 1000;
my $Beep_freq_pr = 1000;
my $Beep_freq_msg = 1000;
my $Beep_remote = '';
my $Nick_flood_protection;
my $Nick_flood_max_nicks;

# helper functions {{{
# XXX track changes for irc_nick_find_color(),  be ready for 256 colors
{

sub DEBUG {weechat::print('', _color_str('yellow', "***") . "\t$SCRIPT: $_[0]");}

sub _beep {
    my $arg = weechat::config_get_plugin('beep_cmd');
    $arg =~ s/%F/$_[0]/;
    $arg =~ s/%L/$_[1]/;
    my $ssh_host = weechat::config_get_plugin('ssh_host');
    my $ssh_key  = weechat::config_get_plugin('ssh_key');
    $ssh_key = "-i $ssh_key " if $ssh_key;
    my $ssh_cmd  = "ssh $ssh_key $ssh_host";

    if ( weechat::config_get_plugin('beeps') eq 'on' ) {
        if ( $ssh_host ne ''
            and weechat::config_get_plugin('beep_remote') eq 'on' )
        {
            system("$ssh_cmd $arg 2>/dev/null 1>&2 &");
        } else {
            system("$arg 2>/dev/null 1>&2 &");
        }
    }
}

# 
# irc_nick_find_color: find a color for a nick (according to nick letters)
sub irc_nick_find_color
{
    my $nick_name = $_[0];
    return weechat::info_get("irc_nick_color", $nick_name);
}

sub _colored {
    my $a = shift;
    my $np ='[\@+^]';
    my ($b) = ($a =~ /^$np?(.*)/);

    return weechat::color('lightgreen') . '@' . irc_nick_find_color($b) . $b . weechat::color('reset') if $a =~ /^\@/;
    return weechat::color('yellow') . '+' . irc_nick_find_color($b) . $b . weechat::color('reset') if $a =~ /^\+/;
    return irc_nick_find_color($b) . $a . weechat::color('reset')
}

sub _get_prefix_mode_with_color
{
    my $test = weechat::config_string( weechat::config_get('irc.color.nick_prefixes') );
#       irc.color.nick_prefixes
#       modes    = 'qaohv'
#       prefixes = '~&@%+'

}

sub _color_str {
    my ($color_name, $str) = @_;
    weechat::color($color_name) . $str  . weechat::color('reset');
}

sub _bar_toggle {
    my $cmd = shift;

    if ( $cmd eq 'show' ) {
        $Bar_hidden = 0;
    } elsif ( $cmd eq 'hide' ) {
        $Bar_hidden = 1;
    } elsif ( $cmd eq 'toggle' ) {
        $Bar_hidden = $Bar_hidden ? 0 : 1;
    }

    if ($Bar_hidden) {
        my ( $bar, $bar_title ) = _bar_get();
        weechat::bar_set($bar_title, 'hidden', $Bar_hidden); # XXX bar must be visible before bar_item_update() is called!
        weechat::bar_set($bar, 'hidden', $Bar_hidden); # XXX bar must be visible before bar_item_update() is called!
    } else {
        _bar_show();
    }
}

sub _bar_hide {
    weechat::bar_item_update($Bar_title_name);
    weechat::bar_item_update(weechat::config_get_plugin('bar_name'));

    if (weechat::config_get_plugin('bar_auto_hide') eq 'on' and not @Bstr) {
        $Bar_hidden = 1;
        my ( $bar, $bar_title ) = _bar_get();

        if ($bar and $bar_title) {
            weechat::command('', "/bar hide " . $Bar_title_name);
            weechat::command('', "/bar hide " . weechat::config_get_plugin('bar_name'));
        } else {
            ( $bar, $bar_title ) = _bar_recreate();
        }
    }
}

sub _bar_clear
{
    my $arg = shift;

    return unless @Bstr;

    if (defined $arg)
    {
        $arg = ".*" if ($arg eq "*");
    }
    @Bstr = $arg ? grep { not $_->[1] =~ /$arg/} @Bstr : ();

    _bar_hide();
}

sub _bar_date_time
{
    my $dt = strftime( weechat::config_string (weechat::config_get('weechat.look.buffer_time_format')), localtime);
    return weechat::string_eval_expression($dt, {}, {},{}) if ($weechat_version >= 0x00040200);

    my $dt_bak = $dt;
    my $dt_marker = 0;
#    while ( $dt_bak ~~ /\$\{(?:color:)?[^\{\}]+\}/ )
    while ( $dt_bak =~ /\$\{(?:color:)?[^\{\}]+\}/ )
    {
        $dt_bak =~ /\$\{(?:color:)?(.*?)\}/;
        my $col = weechat::color($1);
        $dt_bak =~ s/\$\{(?:color:)?(.*?)\}/$col/;
        $dt_marker = 1;
    }
    my $dc     = weechat::color(
        weechat::config_string(weechat::config_get('weechat.color.chat_time_delimiters')));
    my $tdelim = $dc . ":" . weechat::color ("reset");
    my $ddelim = $dc . "-" . weechat::color ("reset");
    
    $dt =~ s/:/$tdelim/g;
    $dt =~ s/-/$ddelim/g;

    $dt = $dt_bak if ($dt_marker == 1);

    return $dt;
}

sub _bar_show {
    my ( $bar, $bar_title ) = _bar_get();

    unless ($bar and $bar_title) {
        ( $bar, $bar_title ) = _bar_recreate();
    }
    if ( $bar and $bar_title ) {
        $Bar_hidden = 0;
        weechat::bar_set($bar_title, 'hidden', '0');    # XXX bars must be visible before
        weechat::bar_set($bar, 'hidden', '0');          #     bar_item_update() is called!

        weechat::bar_item_update($Bar_title_name);
        weechat::bar_item_update( weechat::config_get_plugin('bar_name'));

        # scroll bar, after(!) update
        if (lc(weechat::config_get_plugin('most_recent')) eq "last"
        and weechat::bar_search( weechat::config_get_plugin('bar_name')) ne ""){
            my $bar_name = weechat::config_get_plugin('bar_name');
            weechat::command("","/bar scroll " . $bar_name . " * ye");
        }

    } else {
        weechat::print('', "$SCRIPT: ERROR: missing bar, please reload $SCRIPT");
    }
}

sub _bar_print {
    my $str = shift;

    if (lc(weechat::config_get_plugin('most_recent')) eq "last"){
        push(@Bstr , [_bar_date_time() . " ",  $str]); # insert msg to bottom
    }
    else{
        unshift(@Bstr , [_bar_date_time() . " ",  $str]); # insert msg to top
    }

    _bar_show();
}

sub _print_formatted {
    my ( $fmt, $message, @id ) = @_;

    my @f = qw(N C S);
    my $t;
    my $i = 0;
    foreach (@f)
    {
        if ( $fmt =~ /%($_)/i )
        {
            # $1 = "nN cC sS" from option format_private, format_public
            $t = $1 eq $_ ? _colored( $id[$i] ) : $id[$i];
            $fmt =~ s/%$1/$t/;
        }
        $i++;
    }

    _bar_print( $fmt . "\t" . $message); # insert msg to top
}
}
# }}}

# weechat stuff {{{

sub check_nick_flood {
    my ( $bufferp, $message ) = @_;

    $message =~ s/\,|\.|\;|\://g;                               # remove special chars first ( for example: nickname, or nickname: )
    my @n = split( '\s+', $message);
    @n = &del_double(@n);                                       # remove double nicks
    my $is_nick = 0;
    for ( my $i = 0 ; $i < @n ; $i++ ) {
        $is_nick++ if weechat::nicklist_search_nick( $bufferp, '', $n[$i] );
    }

    if ( defined $is_nick and $is_nick >= $Nick_flood_max_nicks ){
      return defined $is_nick;
    }elsif ( defined $is_nick and $is_nick < $Nick_flood_max_nicks ){
      return;
    }
    return $is_nick = 1 if ( not defined $is_nick );
    return;
}

sub del_double{
  my %all=();
  @all{@_}=1;
  return (keys %all);
}
# colored output of hilighted text to bar
sub highlights_public
{
    my ( $data, $bufferp, $date, $tags, $displayed, $ishilight, $nick, $message ) = @_;
    # with 1.0 displayed and highlight changed from "string" to "integer"
    $displayed = int($displayed);
    $ishilight = int($ishilight);

    # find buffer name, server name
    # return if buffer is in a blacklist
    my $buffername = weechat::buffer_get_string($bufferp, "name");
    return weechat::WEECHAT_RC_OK if weechat::string_has_highlight($buffername, weechat::config_get_plugin('blacklist_buffers'));

    if ( $ishilight == 1
        and weechat::config_get_plugin('show_highlights') eq 'on' )
    {
        if ( weechat::config_get_plugin('away_only') eq 'on' ) {
            return weechat::WEECHAT_RC_OK
              unless weechat::buffer_get_string( $bufferp, "localvar_away" );
        }

        my $btype = weechat::buffer_get_string( $bufferp, "localvar_type" );
        my ( $server, $channel, $fmt ) = (
            weechat::buffer_get_string( $bufferp, "localvar_server" ),
            weechat::buffer_get_string( $bufferp, "localvar_channel" ),
            undef
        );

        # check current buffer for hightlight and away status
        my $current_buffer = weechat::current_buffer();
        return weechat::WEECHAT_RC_OK if ( $bufferp eq $current_buffer and weechat::config_get_plugin('highlights_current_channel') eq 'off' );

        # away status is set?
        if ( $bufferp eq $current_buffer and weechat::config_get_plugin('highlights_current_channel') eq 'away' )
        {       # nick is not away
                return weechat::WEECHAT_RC_OK unless weechat::buffer_get_string( $bufferp, "localvar_away" );
        }

        if ( $btype eq 'channel' ) {
            return weechat::WEECHAT_RC_OK
              if $Nick_flood_protection eq 'on'
                  and check_nick_flood( $bufferp, $message );

            $fmt = weechat::config_get_plugin('format_public');
            _beep( $Beep_freq_ch, weechat::config_get_plugin('beep_duration') );
        } elsif ( $btype eq 'private' ) {
            $channel = '';
            $fmt     = weechat::config_get_plugin('format_private');
            _beep( $Beep_freq_pr, weechat::config_get_plugin('beep_duration') );
        } elsif ( $btype eq 'server' ) {
            if ( weechat::config_get_plugin('show_priv_server_msg') eq 'on' ) {
                #TODO check for #channel == $server FIXME needed?
                $fmt     = '%N%c';
                $nick    = $server;
                $channel = weechat::color( weechat::config_get_plugin('color_server_msg_tag') ) . "[SERVER-MSG]";
                _beep($Beep_freq_msg, weechat::config_get_plugin('beep_duration') );
            }
        }
        _print_formatted( $fmt, $message, $nick, $channel, $server ) if $fmt;
    }

    return weechat::WEECHAT_RC_OK;
}

# colored output of private messages to bar
# server messages aren't shown in the bar
# format: 'nick[privmsg] | message' (/msg)
sub highlights_private
{
    my ( $data, $bufferp, $date, $tags, $displayed, $ishilight, $nick, $message ) = @_;
    # find buffer name, server name
    # return if buffer is in a blacklist
    my $buffername = weechat::buffer_get_string($bufferp, "name");
    return weechat::WEECHAT_RC_OK if weechat::string_has_highlight( $buffername, weechat::config_get_plugin('blacklist_buffers') );

    if ( weechat::config_get_plugin('show_priv_msg') eq "on"
        and $nick ne '--' )
    {
        my $buffer_name = weechat::buffer_get_string( $bufferp, "short_name" );
        my $plugin = weechat::buffer_get_string( $bufferp, "plugin" );
        my $server = weechat::buffer_get_string( $bufferp, "localvar_server" ) if ($plugin eq "irc");

        my $current_buffer_name = weechat::buffer_get_string( weechat::current_buffer(), "short_name" );
        unless ( $current_buffer_name eq $nick )
        {
            _beep( $Beep_freq_msg, weechat::config_get_plugin('beep_duration') );
            my $fmt = '%N@%s%c';
            my $channel = weechat::color( weechat::config_get_plugin('color_privmsg_tag') ) . " [privmsg]";
            $server = $plugin if ($plugin eq "xfer");
            _print_formatted( $fmt, $message, $nick, $channel, $server );
        }
    }

    return weechat::WEECHAT_RC_OK;
}
# obsolete sub-routine

sub highlights_private2
{
    my ( $signal, $callback, $callback_data ) = @_;
    my ( $nick, $message ) = ( $_[2] =~ /(.*?)\t(.*)/ );

    my $fmt = '%N%c';

    if ( weechat::config_get_plugin('show_priv_msg') eq "on"
        and $nick ne '--' )
    {
        my ( $bufferp, $buffer_name );
        $bufferp     = weechat::current_buffer();
        $buffer_name = weechat::buffer_get_string( $bufferp, "short_name" )
          if $bufferp;

        # find buffer name, server name
        # return if buffer is in a blacklist
        my $buffername = weechat::buffer_get_string($bufferp, "name");
        return weechat::WEECHAT_RC_OK if weechat::string_has_highlight( $buffername, weechat::config_get_plugin('blacklist_buffers') );

        unless ( $buffer_name and $buffer_name eq $nick) {
            _beep( $Beep_freq_msg, weechat::config_get_plugin('beep_duration') );
            my $channel = weechat::color( weechat::config_get_plugin('color_privmsg_tag') ) . "[privmsg]";
            my $server = undef;
            _print_formatted( $fmt, $message, $nick, $channel, $server );
        }
    }
    return weechat::WEECHAT_RC_OK;
}

# Arguments in function:
# arg0 = data,
# arg1 = string with pointer to buffer,
# arg2 = user arguments for command 
sub newsbar {

    return weechat::WEECHAT_RC_OK if $_[1] =~ /^scroll_/ and $Bar_hidden;

    my $_cmd = $_[2];
    if ( $_cmd eq 'always' ) {
            weechat::config_set_plugin( 'away_only', 'off' );
    } elsif ( $_cmd eq 'away_only' ) {
            weechat::config_set_plugin( 'away_only', 'on' );
    } elsif ( $_cmd eq 'beep' ) {
            weechat::config_set_plugin( 'beeps', 'on' );
    } elsif ( $_cmd eq 'nobeep' ) {
            weechat::config_set_plugin( 'beeps', 'off' );
    } elsif ( $_cmd eq 'beep_remote' ) {
            weechat::config_set_plugin( 'beep_remote', 'on' );
    } elsif ( $_cmd eq 'beep_local' ) {
            weechat::config_set_plugin( 'beep_remote', 'off' );
    } elsif ( $_cmd eq 'show' or $_cmd eq 'hide' or $_cmd eq 'toggle' ) {
            _bar_toggle( $_cmd );
    } elsif ( $_cmd eq 'scroll_home' ) {
            weechat::command('', "/bar scroll " . weechat::config_get_plugin('bar_name') . " * yb" );
    } elsif ( $_cmd eq 'scroll_end' ) {
            weechat::command('', "/bar scroll " . weechat::config_get_plugin('bar_name') . " * ye" );
    } elsif ( $_cmd eq 'scroll_page_up' ) {
            weechat::command('', "/bar scroll " .
                weechat::config_get_plugin('bar_name') . " * y-" . weechat::config_get_plugin('bar_visible_lines'));
    } elsif ( $_cmd eq 'scroll_page_down' ) {
            weechat::command('', "/bar scroll " .
                weechat::config_get_plugin('bar_name') . " * y+" . weechat::config_get_plugin('bar_visible_lines'));
    } elsif ( $_cmd eq 'scroll_up' ) {
            weechat::command('', "/bar scroll " . weechat::config_get_plugin('bar_name') . " * y-1");
    } elsif ( $_cmd eq 'scroll_down' ) {
            weechat::command('', "/bar scroll " . weechat::config_get_plugin('bar_name') . " * y+1");
    } else {
        my ( $cmd, $arg ) = ( $_cmd =~ /(.*?)\s+(.*)/ );
        $cmd = $_cmd unless $cmd;
        if ( $cmd eq 'memo' ) {
            _bar_print(
                weechat::color( weechat::config_get_plugin('memo_tag_color') )
                  . "[memo]"
                  . weechat::color('reset') . "\t"
                  . ( defined $arg ? $arg : '' ) );
        } elsif ( $cmd eq 'clear' ) {
            _bar_clear($arg);
        } elsif ( $cmd eq 'add' ) {
            my $beep = $arg =~ s/--beep//;
            my ($add_cmd, $value) = ($arg =~ /^\s*?(--color)\s+(.*?)(\s+|\$)/);

            if ( defined $add_cmd and $add_cmd eq '--color' ) {
                $arg =~ s/^\s*?--color\s+$value\s*//;
                if ( $arg =~ /\t/ ) {
                    $arg =~ s/\s*\t\s*(.*)/\t$1/;
                    my $color_code = weechat::color($value);
                    $color_code = '' if $color_code =~ /F-1/;    # XXX ^Y must be literal ctrl-v,ctrl-Y
                    $arg = $color_code . $arg;
                } else {
                    $arg =~ s/^\s+//;
                    $arg = weechat::color( weechat::config_get_plugin('color_info_msg_tag') ) . "[INFO]\t" . $arg;
                }
            } else {
                if ( $arg =~ /\t/ ) {
                    $arg =~ s/\s*\t\s*(.*)/\t$1/;
                } else {
                    $arg =~ s/^\s+//;
                    $arg = weechat::color( weechat::config_get_plugin('color_info_msg_tag') ) . "[INFO]\t" . $arg unless $arg =~ /\t/;
               }
            }

            _beep($Beep_freq_pr, weechat::config_get_plugin('beep_duration') ) if $beep;
            _bar_print($arg);
        }
    }

    return weechat::WEECHAT_RC_OK;
}

sub init_config {

    while ( my ( $option, $default_value ) = each(%SETTINGS) ) {
        weechat::config_set_plugin( $option, $default_value )
          if weechat::config_get_plugin($option) eq "";
    }

    $Beep_freq_ch  = weechat::config_get_plugin('beep_freq_channel');
    $Beep_freq_pr  = weechat::config_get_plugin('beep_freq_private');
    $Beep_freq_msg = weechat::config_get_plugin('beep_freq_msg');
    $Beeps         = weechat::config_get_plugin('beeps');
    $Nick_flood_protection = weechat::config_get_plugin('nick_flood_protection');
    $Nick_flood_max_nicks  = weechat::config_get_plugin('nick_flood_max_nicks');
}

sub beepfreq_config_changed {
    my $datap  = shift;
    my $option = shift;
    my $value  = shift;

    if ( $option =~ /\.beep_freq_channel$/ ) {
        $Beep_freq_ch = $value;
    } elsif ( $option =~ /\.beep_freq_private$/ ) {
        $Beep_freq_pr = $value;
    } elsif ( $option =~ /\.beep_freq_msg$/ ) {
        $Beep_freq_msg = $value;
    }

    return weechat::WEECHAT_RC_OK;
}

sub beeps_config_changed {
    my $datap = shift;
    my $option = shift;
    my $value = shift;

    if ( $value eq 'on' ) {
        $Beeps = " on";
    } else {
        if( $value ne 'off' ) {
            weechat::print('',  weechat::color('lightred') . "=!=\t" . "$SCRIPT: "
                . _color_str( 'lightred', "ERROR" )
                . ": wrong value: '"
                . _color_str( 'red', $value ) . "' "
                . "for config var 'away_only'. Must be one of '"
                . _color_str('cyan', "on" ) . "', '"
                . _color_str('cyan', "off" ) . "'. I'm using: '"
                . _color_str('cyan', "off" ) . "'."
            );

            weechat::config_set_plugin( 'beeps', 'off' );
        }
        $Beeps = "off";
    }

    weechat::bar_item_update($Bar_title_name);
    return weechat::WEECHAT_RC_OK;
}

sub beep_remote_config_changed {
#    my $datap = shift;
#    my $option = shift;
#    my $value = shift;

    my $c = $_[2];
    if ( $c eq 'on' and weechat::config_get_plugin('ssh_host') eq '') {
        DEBUG("cant beep on remote, 'ssh_host' not set");
    } else {
        $Beep_remote = $c eq 'on' ? weechat::config_get_plugin('ssh_host') : 'local';
        weechat::bar_item_update($Bar_title_name);
    }

    return weechat::WEECHAT_RC_OK;
}
sub config_changed_nick_flood {
    my $datap  = shift;
    my $option = shift;
    my $value  = shift;

    $Nick_flood_protection = $value if $option =~ /protection/;
    $Nick_flood_max_nicks  = $value if $option =~ /max_nicks/;

    return weechat::WEECHAT_RC_OK;
}

sub highlights_config_changed {
    my $datap = shift;
    my $option = shift;
    my $value = shift;

    if ( $value eq 'on' ) {
        $Baway = "if away";
    } else {
        if( $value ne 'off' ) {
            weechat::print('',  weechat::color('lightred') . "=!=\t" . "$SCRIPT: "
                . _color_str( 'lightred', "ERROR" )
                . ": wrong value: '"
                . _color_str( 'red', $value ) . "' "
                . "for config var 'away_only'. Must be one of '"
                . _color_str('cyan', "on" ) . "', '"
                . _color_str('cyan', "off" ) . "'. I'm using: '"
                . _color_str('cyan', "off" ) . "'."
            );

            weechat::config_set_plugin( 'away_only', 'off' );
        }
        $Baway = " always";
    }

    weechat::bar_item_update($Bar_title_name);
    return weechat::WEECHAT_RC_OK;
}

sub _bar_item_update
{
    weechat::bar_item_update($Bar_title_name);
    weechat::bar_item_update(weechat::config_get_plugin('bar_name'));
   return weechat::WEECHAT_RC_OK;
}

sub _bar_get {
    return ( weechat::bar_search( weechat::config_get_plugin('bar_name') ),
        weechat::bar_search($Bar_title_name) );
}

sub _bar_recreate {
    my ( $bar, $bar_title ) = _bar_get();

    weechat::print('', _color_str('yellow', '=!=') . "\t$SCRIPT: recreating missing bars (deleted by user?)");
    weechat::command('', "/bar del " . weechat::config_get_plugin('bar_name')) if $bar;
    weechat::command('', "/bar del " . $Bar_title_name )                       if $bar_title;
    
    init_bar();

    return _bar_get();
}

# Make new bar if needed
sub init_bar {
    my $bar_name = weechat::config_get_plugin('bar_name');
    $bar_name = $SCRIPT if ($bar_name eq "");

    $Bar_hidden = weechat::config_get_plugin('bar_hidden_on_start')
      unless defined $Bar_hidden;

    $Beep_remote = weechat::config_get_plugin('beep_remote') eq 'on' ?  weechat::config_get_plugin('ssh_host') : 'local';
    $Beeps = weechat::config_get_plugin('beeps');
    $Beeps = ' ' . $Beeps if $Beeps eq 'on';

    unless (defined $Bar) {
        highlights_config_changed(
            undef,
            "plugins.var.perl." . $SCRIPT . ".away_only",
            weechat::config_get_plugin('away_only')
        );
        weechat::bar_item_new( $bar_name, "build_bar", "" );
        if ($weechat_version >= 0x02090000) {
            weechat::bar_new(
                $bar_name,                              $Bar_hidden,
                "1000",                                 "root",
                "",                                     "top",
                "vertical",                             "vertical",
                "0",
                weechat::config_get_plugin('bar_visible_lines'),
                "default",                              "default",
                weechat::config_string(weechat::config_get('weechat.bar.newsbar.color_bg')),
                weechat::config_string(weechat::config_get('weechat.bar.newsbar.color_bg')),
                weechat::config_get_plugin('bar_seperator'),
                $bar_name
            );
        } else {
            weechat::bar_new(
                $bar_name,                              $Bar_hidden,
                "1000",                                 "root",
                "",                                     "top",
                "vertical",                             "vertical",
                "0",
                weechat::config_get_plugin('bar_visible_lines'),
                "default",                              "default",
                weechat::config_string(weechat::config_get('weechat.bar.newsbar.color_bg')),
                weechat::config_get_plugin('bar_seperator'),
                $bar_name
            );
        }
    }

    my $c;
    if ( $c = weechat::config_string( weechat::config_get('weechat.bar.newsbar.color_bg') ) )
    {
        $c = weechat::config_string(weechat::config_get('weechat.bar.title.color_bg'));
    }

    unless (defined $Bar_title) {
        weechat::bar_item_new( $Bar_title_name, "build_bar_title", "" );
        if ($weechat_version >= 0x02090000) {
            weechat::bar_new(
                $Bar_title_name,                        $Bar_hidden,
                "1010",                                 "root",
                "",                                     "top",
                "vertical",                             "vertical",
                "0",                                    '1',
                "default",                              "default",
                $c, $c,
                'off',
                $Bar_title_name
            );
        } else {
            weechat::bar_new(
                $Bar_title_name,                        $Bar_hidden,
                "1010",                                 "root",
                "",                                     "top",
                "vertical",                             "vertical",
                "0",                                    '1',
                "default",                              "default",
                $c,
                'off',
                $Bar_title_name
            );
        }
    }

    weechat::bar_item_update($Bar_title_name);
    weechat::bar_item_update($bar_name);
}

# FIXME look for FlashCode's ' Force refresh of bars using a bar item when it is destroyed'
# needed for reload too, to be sure to display title before the text bar if e.g.
# text bar was deleted by user
sub unload {
    $Bar = weechat::bar_search( weechat::config_get_plugin('bar_name') );
#    my ( $bar, $bar_title ) = _bar_get();

#    if ($Bar and weechat::config_get_plugin('remove_bar_on_unload') eq 'on') {
        weechat::bar_remove(weechat::bar_search( $Bar_title_name));
        weechat::bar_remove($Bar);
#    }

    return weechat::WEECHAT_RC_OK;
}
# }}}

sub build_bar_title {

    my $most_recent = lc(weechat::config_get_plugin('most_recent'));
    $most_recent = "first" if (($most_recent ne "last") and ($most_recent ne "first"));

    my $cfg =
    weechat::color(weechat::config_string(weechat::config_get('weechat.bar.newsbar_title.color_fg')));
    my $cdelm =
    weechat::color(weechat::config_string(weechat::config_get('weechat.bar.newsbar_title.color_delim')));
    my $cst_num = 
    weechat::color( weechat::config_get_plugin('color_status_number') );
    my $cst_name = 
    weechat::color( weechat::config_get_plugin('color_status_name') );
    my $title =
        $cfg . weechat::config_get_plugin('bar_title') . ": "
      . $cdelm . "[" . $cst_num . "%I"
      . $cdelm . "] [" . $cfg . "active:" . $cst_name . "%A"
      . $cdelm . "] [" . $cfg . "beep: "
      . $cst_name . "%B" . $cdelm . "(" . $cst_name . "%R" . $cdelm . ")"
      . $cdelm . "] [" . $cfg. "most recent: " . $cst_name . $most_recent . $cdelm . "]";

    my $i = @Bstr;
    $i ||= 0;

    $title =~ s/%A/$Baway/;
    $title =~ s/%I/$i/;
    $title =~ s/%B/$Beeps/;
    $title =~ s/%R/$Beep_remote/;

    return $title;
}

use constant {
    TIME     => 0,
    TIME_CCL => 1,    #    TIME_COLOR_CODE_LEN
    NICK     => 2,
    NICK_CCL => 3,    #    NICK_COLOR_CODE_LEN
    MSG      => 4,
};

# FIXME use columns (width in chars) of bar if possible
sub _terminal_columns { my $c = `tput cols`; chomp $c; return $c; }

sub build_bar {
    my $str = "";
    my @f;
    my $i        = 0;
    my $nlen_max = 0;
    my $tlen_max = 0;    # max lenght of date/time

    # get lengths
    foreach (@Bstr) {
        ($f[$i][NICK], $f[$i][MSG]) = split(/\t/, $_->[1]);
        $f[$i][TIME]                = $_->[0];                          # [date ] time

        my $tlen_c       = length(weechat::string_remove_color($f[$i][TIME], ""));    # length without color codes
        $f[$i][TIME_CCL] = length($f[$i][TIME]) - $tlen_c;               # length of color codes
        $tlen_max        = $tlen_c if $tlen_c > $tlen_max;              # new max length

        my $nlen_c       = length(weechat::string_remove_color($f[$i][NICK], ""));
        $f[$i][NICK_CCL] = length($f[$i][NICK]) - $nlen_c;
        $nlen_max        = $nlen_c if $nlen_c > $nlen_max;
        $i++;
    }

    # FIXME rebuild bar if user config changed
    my $c_cps = weechat::color(
        weechat::config_string(weechat::config_get('weechat.color.chat_prefix_suffix')));
    my $l_ps  = weechat::config_string(weechat::config_get('weechat.look.prefix_suffix'));
    # FIXME use user config color
    my $delim     = " " . $c_cps . $l_ps . weechat::color ("reset") . " ";
    #my $delim     = " " . $c_cps . weechat::color ("default") . " ";
    my $l_d  = length(weechat::string_remove_color($delim, ""));

    $Text::Wrap::columns  = _terminal_columns() - ($nlen_max + $tlen_max + $l_d);
    $Text::Wrap::unexpand = 0;   # don't turn spaces into tabs

    foreach (@f) {
        if ( length(@$_[MSG]) > $Text::Wrap::columns ) {
            my @a = split( /\n/, wrap( '', '', @$_[MSG] ) );
            $str .= sprintf( "%*s%*s$delim%s\n", $tlen_max, @$_[TIME], $nlen_max  + @$_[NICK_CCL], @$_[NICK], shift @a );
            foreach (@a) {
                $str .= sprintf( "%*s%*s$delim%s\n", $tlen_max, " ", $nlen_max , " ", $_ );
            }
        } else {
            $str .= sprintf( "%*s%*s$delim%s\n", $tlen_max, @$_[TIME], $nlen_max + @$_[NICK_CCL], @$_[NICK], @$_[MSG] );
        }
    }

    return $str;
}

# color/uncolor help {{{
sub color_help
{
  if (weechat::config_string (weechat::config_get('plugins.var.perl.newsbar.colored_help')) eq 'off' )
  {
    $CMD_HELP =~ s/<c>|<\/c>//g;
  }
  else
  {
    my $cc_cyan    = weechat::color('cyan');
    my $cc_white   = weechat::color('white');
    my $cc_brown   = weechat::color('brown');
    my $cc_default = weechat::color('default');
    $CMD_HELP =~ s/default: '(.*)?'/default: '$cc_cyan$1$cc_default'/g;
    $CMD_HELP =~ s/'(on|off|0|1)?'/'$cc_cyan$1$cc_default'/g;
    $CMD_HELP =~ s/(\/newsbar)/$cc_white$1$cc_default/g;
    foreach ( split( /\|/, $COMPLETITION ), keys %SETTINGS )
    {
        $CMD_HELP =~
          s/(?|^(\s+)($_)([:,])|(\s+)($_)([:,])$)/$1$cc_brown$2$cc_default$3/gm;
    }
    $CMD_HELP =~ s/<c>(.*)?<\/c>/$cc_brown$1$cc_default/g;
    $CMD_HELP =~ s/(%[nNcCs])/$cc_cyan$1$cc_default/g;
  } # }}}
}

# ------------------------------------------------------------------------------
# here we go...
# init script
# XXX If you don't check weechat::register() for succsess, %SETTINGS will be set
# XXX by init_config() into the namespace of other perl scripts.
if ( weechat::register(  $SCRIPT,  $SCRIPT_AUTHOR, $SCRIPT_VERSION, $SCRIPT_LICENCE, $SCRIPT_DESCRIPTION, "unload", "" ) )
{
    $weechat_version = weechat::info_get('version_number', '');

    color_help();
    weechat::hook_command( $COMMAND,  $SCRIPT_DESCRIPTION,  $ARGS_HELP, $CMD_HELP, $COMPLETITION, $CALLBACK, "" );
    weechat::hook_print( "", "notify_message", "", 1, "highlights_public", "" );
    weechat::hook_print( "", "notify_private", "", 1, "highlights_private", "" );

# obsolete
#    weechat::hook_signal( "weechat_pv",    "highlights_private2", "" );

    init_config();
    init_bar();
    weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".away_only", 'highlights_config_changed', "" );
    weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".beep_freq_*", 'beepfreq_config_changed', "" );
    weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".beeps", 'beeps_config_changed', "" );
    weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".beep_remote", 'beep_remote_config_changed', "" );
    weechat::hook_config( "plugins.var.perl." . $SCRIPT . ".nick_flood*", 'config_changed_nick_flood', "" );

    weechat::hook_config( "plugins.var.perl." . $SCRIPT . "*", '_bar_item_update', "" );
    weechat::hook_config( "weechat.bar.newsbar_title.color_*", '_bar_item_update', "" );

}
# vim: ai ts=4 sts=4 et sw=4 foldmethod=marker :
