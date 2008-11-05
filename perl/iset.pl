#
# Copyright (c) 2008 by FlashCode <flashcode@flashtux.org>
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

# Set WeeChat and plugins options interactively.
#
# History:
# 2008-11-05, FlashCode <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-04-19, FlashCode <flashcode@flashtux.org>:
#     script creation

use strict;

my $version = "0.1";

my $buffer = "";
my @options_names = ();
my @options_types = ();
my @options_values = ();
my $option_max_length = 0;
my $current_line = 0;
my $filter = "*";

sub iset_title
{
    if ($buffer ne "")
    {
        weechat::buffer_set($buffer, "title", "Interactive set (iset.pl v$version)  |  Filter: $filter");
    }
}

sub iset_filter
{
    $filter = $_[0];
    $filter = "$1.*" if ($filter =~ /f (.*)/);
    $filter = "*.$1.*" if ($filter =~ /s (.*)/);
    if ((substr($filter, 0, 1) ne "*") && (substr($filter, -1, 1) ne "*"))
    {
        $filter = "*".$filter."*";
    }
}

sub iset_buffer_input
{
    iset_filter($_[1]);
    iset_get_options();
    weechat::buffer_clear($_[0]);
    iset_title();
    $current_line = 0;
    iset_refresh();
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_buffer_close
{
    $buffer = "";
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_init
{
    $current_line = 0;
    $buffer = weechat::buffer_new("iset", "iset_buffer_input", "iset_buffer_close");
    if ($buffer ne "")
    {
        weechat::buffer_set($buffer, "type", "free");
        iset_title();
        weechat::buffer_set($buffer, "key_bind_ctrl-L", "/iset **refresh");
        weechat::buffer_set($buffer, "key_bind_meta2-A", "/iset **up");
        weechat::buffer_set($buffer, "key_bind_meta2-B", "/iset **down");
        weechat::buffer_set($buffer, "key_bind_meta- ", "/iset **toggle");
        weechat::buffer_set($buffer, "key_bind_meta-+", "/iset **incr");
        weechat::buffer_set($buffer, "key_bind_meta--", "/iset **decr");
        weechat::buffer_set($buffer, "key_bind_meta-r", "/iset **reset");
        weechat::buffer_set($buffer, "key_bind_meta-u", "/iset **unset");
        weechat::buffer_set($buffer, "key_bind_meta-ctrl-J", "/iset **set");
        weechat::buffer_set($buffer, "key_bind_meta-ctrl-M", "/iset **set");
        weechat::buffer_set($buffer, "key_bind_meta-meta2-1~", "/iset **scroll_top");
        weechat::buffer_set($buffer, "key_bind_meta-meta2-4~", "/iset **scroll_bottom");
    }
}

sub iset_get_options
{
    @options_names = ();
    @options_types = ();
    @options_values = ();
    $option_max_length = 0;
    my $i = 0;
    my $infolist = weechat::infolist_get("option", "", $filter);
    while (weechat::infolist_next($infolist))
    {
        my $name = weechat::infolist_string($infolist, "full_name");
        my $type = weechat::infolist_string($infolist, "type");
        my $value = weechat::infolist_string($infolist, "value");
        push(@options_names, $name);
        push(@options_types, $type);
        push(@options_values, $value);
        $option_max_length = length($name) if (length($name) > $option_max_length);
        $i++;
    }
    weechat::infolist_free($infolist);
}

sub iset_refresh_line
{
    if ($buffer ne "")
    {
        my $y = $_[0];
        my $format = sprintf("%%s%%-%ds %%s %%-7s %%s %%s%%s%%s", $option_max_length);
        my $around = "";
        $around = "\"" if ($options_types[$y] eq "string");
        my $color1 = "";
        my $color2 = "";
        my $color3 = "";
        if ($y == $current_line)
        {
            $color1 = weechat::color("white,magenta");
            $color2 = weechat::color("lightcyan,magenta");
            $color3 = weechat::color("lightgreen,red");
        }
        my $strline = sprintf($format,
                              $color1, $options_names[$y],
                              $color2, $options_types[$y],
                              $color3, $around, $options_values[$y], $around);
        weechat::print_y($buffer, $y, $strline);
    }
}

sub iset_refresh
{
    if (($buffer ne "") && ($#options_names >= 0))
    {
        foreach my $y (0 .. $#options_names)
        {
            iset_refresh_line($y);
        }
    }
}

sub iset_signal_window_scrolled
{
    if ($buffer ne "")
    {
        my $infolist = weechat::infolist_get("window", $_[1], "");
        if (weechat::infolist_next($infolist))
        {
            if (weechat::infolist_pointer($infolist, "buffer") eq $buffer)
            {
                my $old_current_line = $current_line;
                my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
                my $chat_height = weechat::infolist_integer($infolist, "chat_height");
                $current_line += $chat_height if ($current_line < $start_line_y);
                $current_line -= $chat_height if ($current_line >= $start_line_y + $chat_height);
                $current_line = $start_line_y if ($current_line < $start_line_y);
                $current_line = $start_line_y + $chat_height - 1 if ($current_line >= $start_line_y + $chat_height);
                $current_line = $#options_names if ($current_line > $#options_names);
                if ($old_current_line != $current_line)
                {
                    iset_refresh_line($old_current_line);
                    iset_refresh_line($current_line);
                }
            }
        }
        weechat::infolist_free($infolist);
    }
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_check_line_outside_window
{
    if ($buffer ne "")
    {
        my $infolist = weechat::infolist_get("window", "", "current");
        if (weechat::infolist_next($infolist))
        {
            my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
            my $chat_height = weechat::infolist_integer($infolist, "chat_height");
            if ($start_line_y > $current_line)
            {
                weechat::command($buffer, "/window scroll -".($start_line_y - $current_line));
            }
            else
            {
                if ($start_line_y <= $current_line - $chat_height)
                {
                    weechat::command($buffer, "/window scroll +".($current_line - $start_line_y - $chat_height + 1));
                }
            }
        }
        weechat::infolist_free($infolist);
    }
}

sub iset_config
{
    if ($buffer ne "")
    {
        iset_get_options();
        iset_refresh_line($current_line);
    }
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_set_option
{
    my $option = weechat::config_get($_[0]);
    weechat::config_option_set($option, $_[1], 1) if ($option ne "");
}

sub iset_reset_option
{
    my $option = weechat::config_get($_[0]);
    weechat::config_option_reset($option, 1) if ($option ne "");
}

sub iset_unset_option
{
    my $option = weechat::config_get($_[0]);
    weechat::config_option_unset($option) if ($option ne "");
    weechat::buffer_clear($buffer);
    iset_refresh();
}

sub iset
{
    if ($_[1] ne "")
    {
        iset_filter($_[1]) if (substr($_[1], 0, 2) ne "**");
    }
    
    if ($buffer eq "")
    {
        iset_init();
        iset_get_options();
        iset_refresh();
    }
    
    if ($_[1] eq "")
    {
        weechat::buffer_set($buffer, "display", "1");
    }
    else
    {
        if ($_[1] eq "**refresh")
        {
            weechat::buffer_clear($buffer);
            iset_get_options();
            iset_refresh();
            weechat::command($buffer, "/window refresh");
        }
        if ($_[1] eq "**up")
        {
            if ($current_line > 0)
            {
                $current_line--;
                iset_refresh_line($current_line + 1);
                iset_refresh_line($current_line);
                iset_check_line_outside_window();
            }
        }
        if ($_[1] eq "**down")
        {
            if ($current_line < $#options_names)
            {
                $current_line++;
                iset_refresh_line($current_line - 1);
                iset_refresh_line($current_line);
                iset_check_line_outside_window();
            }
        }
        if ($_[1] eq "**scroll_top")
        {
            my $old_current_line = $current_line;
            $current_line = 0;
            iset_refresh_line ($old_current_line);
            iset_refresh_line ($current_line);
            weechat::command($buffer, "/window scroll_top");
        }
        if ($_[1] eq "**scroll_bottom")
        {
            my $old_current_line = $current_line;
            $current_line = $#options_names;
            iset_refresh_line ($old_current_line);
            iset_refresh_line ($current_line);
            weechat::command($buffer, "/window scroll_bottom");
        }
        if ($_[1] eq "**toggle")
        {
            if ($options_types[$current_line] eq "boolean")
            {
                iset_set_option($options_names[$current_line], "toggle");
            }
        }
        if ($_[1] eq "**incr")
        {
            if (($options_types[$current_line] eq "integer")
                || ($options_types[$current_line] eq "color"))
            {
                iset_set_option($options_names[$current_line], "++1");
            }
        }
        if ($_[1] eq "**decr")
        {
            if (($options_types[$current_line] eq "integer")
                || ($options_types[$current_line] eq "color"))
            {
                iset_set_option($options_names[$current_line], "--1");
            }
        }
        if ($_[1] eq "**reset")
        {
            iset_reset_option($options_names[$current_line]);
        }
        if ($_[1] eq "**unset")
        {
            iset_unset_option($options_names[$current_line]);
        }
        if ($_[1] eq "**set")
        {
            my $quote = "";
            $quote = "\"" if ($options_types[$current_line] eq "string");
            weechat::buffer_set($buffer, "input", "/set ".$options_names[$current_line]." = ".$quote.$options_values[$current_line].$quote);
        }
    }
    
    return weechat::WEECHAT_RC_OK;
}

weechat::register("iset", "FlashCode <flashcode\@flashtux.org>", $version, "GPL3", "Interactive Set for configuration options", "", "");
weechat::hook_command("iset", "Interactive set", "[f file] [s section] [text]",
                      "f file    : show options for a file (for example: 'f weechat' or 'f irc')\n".
                      "s section : show options for a section (for example: 's look')\n".
                      "text      : show options with 'text' in name (for example: 'nicklist')\n\n".
                      "Keys for iset buffer:\n".
                      "up,down   : move one option up/down\n".
                      "pgup,pdwn : move one page up/down\n".
                      "ctrl + 'L': refresh options and screen\n".
                      "alt-space : toggle boolean on/off\n".
                      "alt + '+' : increase value (for integer or color)\n".
                      "alt + '-' : decrease value (for integer or color)\n".
                      "alt + 'R' : reset value of option\n".
                      "alt + 'U' : unset option\n".
                      "alt-enter : set new value for option (edit it with command line)\n".
                      "text,enter: set a new filter using command line (use '*' to see all options)",
                      "", "iset");
weechat::hook_signal("window_scrolled", "iset_signal_window_scrolled");
weechat::hook_config("*", "iset_config");
