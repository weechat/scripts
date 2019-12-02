#
# Copyright (c) 2010-2019 by Nils Görs <weechatter@arcor.de>
# Copyleft (ɔ) 2013 by oakkitten
#
# colors the channel text with nick color and also highlight the whole line
# colorize_nicks.py script will be supported
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

# history:
# 3.8: new option custom_action_text (https://github.com/weechat/scripts/issues/313) (idea by 3v1n0)
# 3.7: new option "alternate_color" (https://github.com/weechat/scripts/issues/333) (idea by snuffkins)
# 3.6: new option "own_lines_color" (idea by Linkandzelda)
#    : add help about "localvar" to option
# 3.5: new options "highlight_words" and "highlight_words_color" (idea by jokrebel)
# 3.4: new options "tags" and "ignore_tags"
# 3.3: use localvar "colorize_lines" for buffer related color (idea by tomoe-mami)
# 3.2: minor logic fix
# 3.1: fix: line wasn't colored with nick color, when highlight option was "off" (reported by rivarun)
# 3.0: large part of script rewritten
#      fix: works nicely with colors
#      improved: highlight_regex and highlight_words work in a natural way
#      removed: /colorize_lines
#      removed: shuffle
# 2.2: fix: regex with [tab] in message (patch by sqrrl)
# 2.1: fix: changing highlight color did not apply messages already displayed (reported by rafi_)
# 2.0: fix: debugging weechat::print() removed (thanks demure)
# 1.9: fix: display bug with nick_mode
# 1.8  add: option "use_irc_colors" (requested by Zertap)
#      fix: empty char for nick_mode was used, even when "irc.look.nick_mode_empty" was OFF (reported by FlashCode)
# 1.7: fix: broken lines in dcc chat (reported by equatorping)
# 1.6: improved: wildcard "*" can be used for server and/or nick. (requested by ldvx)
#    : add: new value, "only", for option "own_lines" (read help!)
# 1.5: sync: option weechat.look.nickmode changed in 0.3.9 to "irc.look.nick_mode"
# 1.4: fix: whole ctcp message was display in prefix (reported by : Mkaysi)
# 1.3: fix: now using weechat::buffer_get_string() instead of regex to prevent problems with dots inside server-/channelnames (reported by surfhai)
# 1.2: add: hook_modifier("colorize_lines") to use colorize_lines with another script.
#    : fix: regex was too greedy and also hit tag "prefix_nick_ccc"
# 1.1: fix:  problems with temporary server (reported by nand`)
#    : improved: using weechat_string_has_highlight()
# 1.0: fix: irc.look.nick_prefix wasn't supported
# 0.9: added: option "own_nick" (idea by travkin)
#    : new value (always) for option highlight
#    : clean up code
# 0.8.1: fix: regex()
# 0.8: added: option "avail_buffer" and "nicks" (please read help-page) (suggested by ldvx)
#    : fix: blacklist_buffers wasn't load at start
#    : fix: nick_modes wasn't displayed since v0.7
#    : rewrote init() routine
#    : thanks to stfn for hint with unescaped variables in regex.
# 0.7: fix: bug when irc.look.nick_suffix was set (reported and beta-testing by: hw2) (>= weechat 0.3.4)
#      blacklist_buffers option supports servername
#      clean up code
# 0.6: code optimazations.
#      rename of script (rainbow_text.pl -> colorize_lines.pl) (suggested by xt and flashcode)
# 0.5: support of hotlist_max_level_nicks_add and weechat.color.chat_nick_colors (>= weechat 0.3.4)
# 0.4: support of weechat.look.highlight_regex option (>= weechat 0.3.4)
#    : support of weechat.look.highlight option
#    : highlighted line did not work with "." inside servername
#    ; internal "autoset" function fixed
# 0.3: support of colorize_nicks.py implemented.
#    : /me text displayed wrong nick colour (colour from suffix was used)
#    : highlight messages will be checked case insensitiv
# 0.2: supports highlight_words_add from buffer_autoset.py script (suggested: Emralegna)
#    : correct look_nickmode colour will be used (bug reported by: Emralegna)
#    : /me text will be coloured, too
# 0.1: initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#

#use Data::Dumper
#$Data::Dumper::Useqq=1;

use strict;
my $PRGNAME     = "colorize_lines";
my $VERSION     = "3.8";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENCE     = "GPL3";
my $DESCR       = "Colorize users' text in chat area with their nick color, including highlights";

my %config = ("buffers"                 => "all",       # all, channel, query
              "blacklist_buffers"       => "",          # "a,b,c"
              "lines"                   => "on",
              "highlight"               => "on",        # on, off, nicks
              "nicks"                   => "",          # "d,e,f", "/file"
              "own_lines"               => "on",        # on, off, only
              "own_lines_color"         => "",          # empty means, use color from option "chat_nick_self"
              "tags"                    => "irc_privmsg",
              "ignore_tags"             => "irc_ctcp",
              "highlight_words"         => "off",       # on, off
              "highlight_words_color"   => "black,darkgray",
              "alternate_color"         => "",
              "custom_action_text"      => "",
);

my %help_desc = ("buffers"                  => "Buffer type affected by the script (all/channel/query, default: all)",
                 "blacklist_buffers"        => "Comma-separated list of channels to be ignored (e.g. freenode.#weechat,*.#python)",
                 "lines"                    => "Apply nickname color to the lines (off/on/nicks). The latter will limit highlighting to nicknames in option 'nicks'. You can use a localvar to color all lines with a given color (eg: /buffer set localvar_set_colorize_lines *yellow). You'll have enable this option to use alternate_color.",
                 "highlight"                => "Apply highlight color to the highlighted lines (off/on/nicks). The latter will limit highlighting to nicknames in option 'nicks'. Options 'weechat.color.chat_highlight' and 'weechat.color.chat_highlight_bg' will be used as colors.",
                 "nicks"                    => "Comma-separater list of nicks (e.g. freenode.cat,*.dog) OR file name starting with '/' (e.g. /file.txt). In the latter case, nicknames will get loaded from that file inside weechat folder (e.g. from ~/.weechat/file.txt). Nicknames in file are newline-separated (e.g. freenode.dog\\n*.cat)",
                 "own_lines"                => "Apply nickname color to own lines (off/on/only). The latter turns off all other kinds of coloring altogether. This option has an higher priority than alternate_color option.",
                 "own_lines_color"          => "this color will be used for own messages. Set an empty value to use weechat.color.chat_nick_self option",
                 "tags"                     => "Comma-separated list of tags to accept (see /debug tags)",
                 "ignore_tags"              => "Comma-separated list of tags to ignore (see /debug tags)",
                 "highlight_words"          => "highlight word(s) in text, matching word(s) in weechat.look.highlight",
                 "highlight_words_color"    => "color for highlight word in text (format: fg,bg)",
                 "alternate_color"          => "alternate between two colors for messages (format: fg,bg:fg,bg)",
                 "custom_action_text"       => "customise the text attributes of ACTION message (note: content is evaluated, see /help eval)",
);

my @ignore_tags_array;
my @tags_array;

#################################################################################################### config

# program starts here
sub colorize_cb
{
    my ( $data, $modifier, $modifier_data, $string ) = @_;

    # quit if a ignore_tag was found
    if (@ignore_tags_array)
    {
        my $combined_search = join("|",@ignore_tags_array);
        my @ignore_tags_found = ($modifier_data =~ /($combined_search)/);
        return $string if (@ignore_tags_found);
    }

    if (@tags_array)
    {
        my $combined_search = join("|",@tags_array);
        my @tags_found = ($modifier_data =~ /($combined_search)/);
        return $string unless (@tags_found);
    }

# find buffer pointer
    $modifier_data =~ m/([^;]*);([^;]*);/;
    my $buf_ptr = weechat::buffer_search($1, $2);
    return $string if ($buf_ptr eq "");

    # find buffer name, server name
    # return if buffer is in a blacklist
    my $buffername = weechat::buffer_get_string($buf_ptr, "name");
    return $string if weechat::string_has_highlight($buffername, $config{blacklist_buffers});
    my $servername = weechat::buffer_get_string($buf_ptr, "localvar_server");

    # find stuff between \t
    $string =~ m/^([^\t]*)\t(.*)/;
    my $left = $1;
    my $right = $2;

    # find nick of the sender
    # find out if we are doing an action
    my $nick = ($modifier_data =~ m/(^|,)nick_([^,]*)/) ? $2 : weechat::string_remove_color($left, "");
    my $action = ($modifier_data =~ m/\birc_action\b/) ? 1 : 0;

    ######################################## get color

    my $color = "";
    my $my_nick = weechat::buffer_get_string($buf_ptr, "localvar_nick");
    my $channel_color = weechat::color( get_localvar($buf_ptr,"localvar_colorize_lines") );
    my $alternate_last = get_localvar($buf_ptr,"localvar_colorize_lines_alternate");
    my ($alternate_color1,$alternate_color2) = split(/:/,$config{alternate_color},2) if ( $config{alternate_color} ne "");

#    weechat::print("","a: $alternate_color1");
#    weechat::print("","b: $alternate_color2");

    if ($my_nick eq $nick)
    {
        # it's our own line
        # process only if own_lines is "on" or "only" (i.e. not "off")
        return $string if ($config{own_lines} eq "off") && not ($channel_color) && ( $config{alternate_color} eq "" );

        $color = weechat::color($config{own_lines_color});
        $color = weechat::color("chat_nick_self") if ($config{own_lines_color} eq "");
        $color = $channel_color if ($channel_color) && ($config{own_lines} eq "off");

        $color = get_alternate_color($buf_ptr,$alternate_last,$alternate_color1,$alternate_color2) if ( $config{alternate_color} ne "" ) &&
        ( $config{own_lines} eq "off" );

    } else {
        # it's someone else's line
        # don't process is own_lines are "only"
        # in order to get correct matching, remove colors from the string
        return $string if ($config{own_lines} eq "only");
        my $right_nocolor = weechat::string_remove_color($right, "");
        if ((
            # if configuration wants us to highlight
            $config{highlight} eq "on" ||
            ($config{highlight} eq "nicks" && weechat::string_has_highlight("$servername.$nick", $config{nicks}))
           ) && (
            # ..and if we have anything to highlight
            weechat::string_has_highlight($right_nocolor, weechat::buffer_string_replace_local_var($buf_ptr, weechat::buffer_get_string($buf_ptr, "highlight_words"))) ||
            weechat::string_has_highlight($right_nocolor, weechat::config_string(weechat::config_get("weechat.look.highlight"))) ||
            weechat::string_has_highlight_regex($right_nocolor, weechat::config_string(weechat::config_get("weechat.look.highlight_regex"))) ||
            weechat::string_has_highlight_regex($right_nocolor, weechat::buffer_get_string($buf_ptr, "highlight_regex"))
           )) {
            # that's definitely a highlight! get a highlight color
            # and replace the first occurance of coloring, that'd be nick color
            $color = weechat::color('chat_highlight');
            $right =~ s/\31[^\31 ]+?\Q$nick/$color$nick/ if ($action);
        } elsif (
            # now that's not a highlight OR highlight is off OR current nick is not in the list
            # let's see if configuration wants us to highlight lines
            $config{lines} eq "on" ||
            ($config{lines} eq "nicks" && weechat::string_has_highlight("$servername.$nick", $config{nicks}))
           ) {
            $color = weechat::info_get('irc_nick_color', $nick);
            $color = $channel_color if ($channel_color); 

            $color = get_alternate_color($buf_ptr,$alternate_last,$alternate_color1,$alternate_color2) if ( $config{alternate_color} ne "");
        } else {
            # oh well
            return $string if ($config{highlight_words} ne "on");
        }
    }
    my $right_nocolor = weechat::string_remove_color($right, "");
    if ((
            $config{highlight_words} eq "on"
            ) && ($my_nick ne $nick) && (
            weechat::string_has_highlight($right_nocolor, weechat::config_string(weechat::config_get("weechat.look.highlight")))
            ))
            {
            my $high_word_color = weechat::color(weechat::config_get_plugin("highlight_words_color"));
            my $reset = weechat::color('reset');
            my @highlight_array = split(/,/,weechat::config_string(weechat::config_get("weechat.look.highlight")));
            my @line_array = split(/ /,$right);

            foreach my $l (@line_array) {
                foreach my $h (@highlight_array) {
                    my $i = $h;
                    # check word case insensitiv || check if word matches without "(?-i)" at beginning
                    if ( lc($l) eq lc($h) || (index($h,"(?-i)") != -1 && ($l eq substr($i,5,length($i)-5,""))) ) {
                        $right =~ s/\Q$l\E/$high_word_color$l$reset/;
                    # word starts with (?-i) and has a wildcard ?
                    } elsif ((index($h,"(?-i)") != -1) && (index($h,"*") != -1) ){
                        my $i = $h;
                        my $t = substr($i,5,length($i)-5,"");
                        my $regex = weechat::string_mask_to_regex($t);
                        $right =~ s/\Q$l\E/$high_word_color$l$reset/ if ($l =~ /^$regex$/i);    # use * without sensitive
                      }elsif ((index($h,"*") == 0 || index($h,"*") == length($h)-1)){# wildcard at beginning or end ?
                        my $regex = weechat::string_mask_to_regex($h);
                        $right =~ s/\Q$l\E/$high_word_color$l$reset/ if ($l =~ /^$regex$/i);
                      }
                }
            }
            }
    ######################################## inject colors and go!

    my $out = "";
    if ($action) {
        # remove the first color reset - after * nick
        # make other resets reset to our color
        $right =~ s/\34//;
        $color = weechat::string_eval_expression($config{custom_action_text}, {}, {}, {}) if ( $config{custom_action_text} ne "");
        $right =~ s/\34/\34$color/g;
        $out = $left . "\t" . $right . "\34"
    } else {
        # make other resets reset to our color
        $right =~ s/\34/\34$color/g;
        $out = $left . "\t" . $color . $right . "\34"
    }
    #weechat::print("", ""); weechat::print("", "\$str " . Dumper($string)); weechat::print("", "\$out " . Dumper($out));
    return $out;
}

sub get_localvar
{
    my ( $buf_ptr,$localvar ) = @_;
    return weechat::buffer_get_string($buf_ptr, "$localvar");
}

sub set_localvar
{
    my ( $buf_ptr,$value ) = @_;
    weechat::buffer_set($buf_ptr, "localvar_set_colorize_lines_alternate", "$value");
}

sub get_alternate_color
{
    my ( $buf_ptr, $alternate_last,$alternate_color1,$alternate_color2 ) = @_;
    my $color;
    if (($alternate_last eq "") or ($alternate_last eq "0"))
    {
        $color = weechat::color($alternate_color1);
        set_localvar($buf_ptr,"1");
    } else {
        $color = weechat::color($alternate_color2);
        set_localvar($buf_ptr,"0");
    }
    return $color;
}
#################################################################################################### config

# read nicknames if $conf{nisks} starts with /
# after this, $conf{nisks} is of form a,b,c,d
# if it doesnt start with /, assume it's already a,b,c,d
sub nicklist_read
{
    return if (substr($config{nicks}, 0, 1) ne "/");
    my $file = weechat::info_get("weechat_dir", "") . $config{nicks};
    return unless -e $file;
    my $nili = "";
    open (WL, "<", $file) || DEBUG("$file: $!");
    while (<WL>)
    {
        chomp;                                                         # kill LF
        $nili .= $_ . ",";
    }
    close WL;
    chop $nili;                                                        # remove last ","
    $config{nicks} = $nili;
}

sub ignore_tags
{
    @ignore_tags_array = split(",",$config{ignore_tags});
}

sub use_of_tags
{
    @tags_array = split(",",$config{tags});
}

# called when a config option ha been changed
# $name = plugins.var.perl.$prgname.nicks etc
sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name,length("plugins.var.perl.$PRGNAME."),length($name));
    $config{$name} = lc($value);
    nicklist_read() if ($name eq "nicks");
    ignore_tags() if ($name eq "ignore_tags");
    use_of_tags() if ($name eq "tags");
}

# read configuration from weechat OR
#   set default options and
#   set dectription if weechat >= 0.3.5
# after done, read nicklist from file if needed
sub init_config
{
    my $weechat_version = weechat::info_get('version_number', '') || 0;
    foreach my $option (keys %config){
        if (!weechat::config_is_set_plugin($option)) {
            weechat::config_set_plugin($option, $config{$option});
            weechat::config_set_desc_plugin($option, $help_desc{$option}) if ($weechat_version >= 0x00030500); # v0.3.5
        } else {
            $config{$option} = lc(weechat::config_get_plugin($option));
        }
    }
    nicklist_read();
    ignore_tags();
    use_of_tags();
}

#################################################################################################### start

weechat::register($PRGNAME, "Nils Görs <weechatter\@arcor.de>", $VERSION, $LICENCE, $DESCR, "", "") || return;

weechat::hook_modifier("500|weechat_print","colorize_cb", "");
init_config();
weechat::hook_config("plugins.var.perl.$PRGNAME.*", "toggle_config_by_set", "");
