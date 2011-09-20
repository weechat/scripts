#
# Copyright (C) 2008-2011 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2010-2011 Nils Görs <weechatter@arcor.de>
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
# 2011-09-20, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.9: add mouse support, fix iset buffer, fix errors on first load under FreeBSD
# 2011-07-21, nils_2 <weechatter@arcor.de>:
#     version 1.8: added: option "show_plugin_description" (alt+p)
#                  fixed: typos in /help iset (lower case for alt+'x' keys)
# 2011-05-29, nils_2 <weechatter@arcor.de>:
#     version 1.7: added: version check for future needs
#                  added: new option (scroll_horiz) and usage of scroll_horiz function (weechat >= 0.3.6 required)
#                  fixed: help_bar did not pop up immediately using key-shortcut
# 2011-02-19, nils_2 <weechatter@arcor.de>:
#     version 1.6: added: display of all possible values in help bar (show_help_extra_info)
#                  fixed: external user options never loaded when starting iset first time
# 2011-02-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.5: use new help format for command arguments
# 2011-02-03, nils_2 <weechatter@arcor.de>:
#     version 1.4: fixed: restore value filter after /upgrade using buffer local variable.
# 2011-01-14, nils_2 <weechatter@arcor.de>:
#     version 1.3: added function to search for values (option value_search_char).
#                  code optimization.
# 2010-12-26, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.2: improve speed of /upgrade when iset buffer is open,
#                  restore filter used after /upgrade using buffer local variable,
#                  use /iset filter argument if buffer is open.
# 2010-11-21, drubin <drubin+weechat@smartcube.co.za>:
#     version 1.1.1: fix bugs with cursor position
# 2010-11-20, nils_2 <weechatter@arcor.de>:
#     version 1.1: cursor position set to value
# 2010-08-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.0: move misplaced call to infolist_free()
# 2010-02-02, rettub <rettub@gmx.net>:
#     version 0.9: turn all the help stuff off if option 'show_help_bar' is 'off',
#                  new key binding <alt>-<v> to toggle help_bar and help stuff on/off
# 2010-01-30, nils_2 <weechatter@arcor.de>:
#     version 0.8: fix error when option does not exist
# 2010-01-24, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: display iset bar only on iset buffer
# 2010-01-22, nils_2 <weechatter@arcor.de> and drubin:
#     version 0.6: add description in a bar, fix singular/plural bug in title bar,
#                  fix selected line when switching buffer
# 2009-06-21, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: fix bug with iset buffer after /upgrade
# 2009-05-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: sync with last API changes
# 2009-01-04, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: open iset buffer when /iset command is executed
# 2009-01-04, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: use null values for options, add colors, fix refresh bugs,
#                  use new keys to reset/unset options, sort options by name,
#                  display number of options in buffer's title
# 2008-11-05, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-04-19, Sebastien Helleu <flashcode@flashtux.org>:
#     script creation

use strict;

my $PRGNAME = "iset";
my $VERSION = "1.9";
my $DESCR   = "Interactive Set for configuration options";
my $AUTHOR  = "Sebastien Helleu <flashcode\@flashtux.org>";
my $LICENSE = "GPL3";

my $iset_buffer = "";
my $wee_version_number = 0;
my @iset_focus = ();
my @options_names = ();
my @options_types = ();
my @options_values = ();
my @options_is_null = ();
my $option_max_length = 0;
my $current_line = 0;
my $filter = "*";
my $description = "";
my $options_name_copy = "";
my $iset_filter_title = "";
my %options = ("show_help_bar"              => "on",
               "show_help_extra_info"       => "on",
               "show_plugin_description"    => "on",
               "scroll_horiz"               => "10%",
               "color_option"               => "default",
               "color_option_selected"      => "white",
               "color_type"                 => "brown",
               "color_type_selected"        => "yellow",
               "color_value"                => "cyan",
               "color_value_selected"       => "lightcyan",
               "color_value_undef"          => "green",
               "color_value_undef_selected" => "lightgreen",
               "color_bg_selected"          => "red",
               "color_help_option_name"     => "white",
               "color_help_text"            => "default",
               "color_help_default_value"   => "green",
               "value_search_char"          => "=",
    );
my %mouse_keys = ("\@chat(perl.$PRGNAME):button2*" => "hsignal:iset_mouse",
                  "\@chat(perl.$PRGNAME):wheelup" => "/repeat 5 /iset **up",
                  "\@chat(perl.$PRGNAME):wheeldown" => "/repeat 5 /iset **down");

sub iset_init_config
{
    foreach my $option (keys %options)
    {
        if (!weechat::config_is_set_plugin($option))
        {
            weechat::config_set_plugin($option, $options{$option});
        }
        else
        {
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}

sub iset_title
{
    if ($iset_buffer ne "")
    {
        $iset_filter_title = "Filter: " if ($iset_filter_title eq "");
        $filter = "*" if ($filter eq "");
        my $postfix = "s";
        my $option_txt  = " option";
        my $opt_txt = $option_txt;
        $opt_txt = $option_txt.$postfix if (@options_names > 1);
        my $show_plugin_descr_txt = "";
        $show_plugin_descr_txt = " (plugins description hidden)" if ($options{show_plugin_description} eq "off");
        weechat::buffer_set($iset_buffer, "title",
                            "Interactive set (iset.pl v$VERSION)  |  "
                            .$iset_filter_title.weechat::color("yellow").$filter.weechat::color("default")."  |  "
                            .@options_names.$opt_txt . $show_plugin_descr_txt);
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
    if ($iset_buffer ne "")
    {
        weechat::buffer_set($iset_buffer, "localvar_set_iset_filter", $filter);
    }
}

sub iset_buffer_input
{
    my ($data, $buffer, $string) = ($_[0], $_[1], $_[2]);

    my $string2 = substr( $string,0,1 );
    if ( $string2 eq $options{value_search_char} ){
      $filter = substr( $string, 1 );
      iset_get_values($filter);
      $iset_filter_title = "Filter (by value): ";
      if ($iset_buffer ne "")
      {
          weechat::buffer_set($iset_buffer, "localvar_set_iset_filter", $filter);
      }
    }else{
      $iset_filter_title = "";
      iset_filter($string);
      iset_get_options();
    }
    weechat::buffer_clear($buffer);
    iset_title($iset_filter_title);
    $current_line = 0;
    iset_refresh();
    return weechat::WEECHAT_RC_OK;
}

sub iset_buffer_close
{
    $iset_buffer = "";
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_init
{
    $current_line = 0;
    $iset_buffer = weechat::buffer_search("perl", $PRGNAME);
    if ($iset_buffer eq "")
    {
        $iset_buffer = weechat::buffer_new($PRGNAME, "iset_buffer_input", "", "iset_buffer_close", "");
    }
    else
    {
        my $new_filter = weechat::buffer_get_string($iset_buffer, "localvar_iset_filter");
        $filter = $new_filter if ($new_filter ne "");
    }
    if ($iset_buffer ne "")
    {
        weechat::buffer_set($iset_buffer, "type", "free");
        iset_title();
        weechat::buffer_set($iset_buffer, "key_bind_ctrl-L",        "/iset **refresh");
        weechat::buffer_set($iset_buffer, "key_bind_meta2-A",       "/iset **up");
        weechat::buffer_set($iset_buffer, "key_bind_meta2-B",       "/iset **down");
        weechat::buffer_set($iset_buffer, "key_bind_meta2-23~",     "/iset **left");
        weechat::buffer_set($iset_buffer, "key_bind_meta2-24~" ,    "/iset **right");
        weechat::buffer_set($iset_buffer, "key_bind_meta- ",        "/iset **toggle");
        weechat::buffer_set($iset_buffer, "key_bind_meta-+",        "/iset **incr");
        weechat::buffer_set($iset_buffer, "key_bind_meta--",        "/iset **decr");
        weechat::buffer_set($iset_buffer, "key_bind_meta-imeta-r",  "/iset **reset");
        weechat::buffer_set($iset_buffer, "key_bind_meta-imeta-u",  "/iset **unset");
        weechat::buffer_set($iset_buffer, "key_bind_meta-ctrl-J",   "/iset **set");
        weechat::buffer_set($iset_buffer, "key_bind_meta-ctrl-M",   "/iset **set");
        weechat::buffer_set($iset_buffer, "key_bind_meta-meta2-1~", "/iset **scroll_top");
        weechat::buffer_set($iset_buffer, "key_bind_meta-meta2-4~", "/iset **scroll_bottom");
        weechat::buffer_set($iset_buffer, "key_bind_meta-v",        "/iset **toggle_help");
        weechat::buffer_set($iset_buffer, "key_bind_meta-p",        "/iset **toggle_show_plugin_desc");
        weechat::buffer_set($iset_buffer, "localvar_set_iset_filter", $filter);
    }
}

sub iset_get_options
{
    @iset_focus = ();

    @options_names = ();
    @options_types = ();
    @options_values = ();
    @options_is_null = ();
    $option_max_length = 0;
    my %options_internal = ();
    my $i = 0;
    my $key;
    my $iset_struct;
    my %iset_struct;

    my $infolist = weechat::infolist_get("option", "", $filter);
    while (weechat::infolist_next($infolist))
    {
        $key = sprintf("%08d", $i);
        my $name = weechat::infolist_string($infolist, "full_name");
          next if ( $options{show_plugin_description} eq 'off' and index ($name, "plugins.desc.") != -1 );
        my $type = weechat::infolist_string($infolist, "type");
        my $value = weechat::infolist_string($infolist, "value");
        my $is_null = weechat::infolist_integer($infolist, "value_is_null");

        $options_internal{$name}{"type"} = $type;
        $options_internal{$name}{"value"} = $value;
        $options_internal{$name}{"is_null"} = $is_null;
        $option_max_length = length($name) if (length($name) > $option_max_length);

        $iset_struct{$key} = $options_internal{$name};
        push(@iset_focus, $iset_struct{$key});
        $i++;
    }
    weechat::infolist_free($infolist);


    foreach my $name (sort keys %options_internal)
    {
        push(@options_names, $name);
        push(@options_types, $options_internal{$name}{"type"});
        push(@options_values, $options_internal{$name}{"value"});
        push(@options_is_null, $options_internal{$name}{"is_null"});
    }
}

sub iset_get_values
{
    my $var_value = $_[0];
    @options_names = ();
    @options_types = ();
    @options_values = ();
    @options_is_null = ();
    $option_max_length = 0;
    my %options_internal = ();
    my $i = 0;
    my $infolist = weechat::infolist_get("option", "", "*");
    $var_value =~ tr/[a-z][0-9].=-_!//cd;  # kill meta chars
    $var_value = lc($var_value);
    while (weechat::infolist_next($infolist))
    {
        my $name = weechat::infolist_string($infolist, "full_name");
          next if ( $options{show_plugin_description} eq 'off' and index ($name, "plugins.desc.") != -1 );
        my $type = weechat::infolist_string($infolist, "type");
        my $value = weechat::infolist_string($infolist, "value");
        my $is_null = weechat::infolist_integer($infolist, "value_is_null");
        if (lc($value) =~ m/$var_value/)
        { 
            $options_internal{$name}{"type"} = $type;
            $options_internal{$name}{"value"} = $value;
            $options_internal{$name}{"is_null"} = $is_null;
            $option_max_length = length($name) if (length($name) > $option_max_length);
        }
        $i++;
    }
    weechat::infolist_free($infolist);
    foreach my $name (sort keys %options_internal)
    {
        push(@options_names, $name);
        push(@options_types, $options_internal{$name}{"type"});
        push(@options_values, $options_internal{$name}{"value"});
        push(@options_is_null, $options_internal{$name}{"is_null"});
    }
        weechat::buffer_set($iset_buffer, "localvar_set_iset_filter", $var_value);
}

sub iset_refresh_line
{
    if ($iset_buffer ne "")
    {
        my $y = $_[0];
        if ($y <= $#options_names)
        {
            return if (! defined($options_types[$y]));
            my $format = sprintf("%%s%%-%ds %%s %%-7s %%s %%s%%s%%s", $option_max_length);
            my $around = "";
            $around = "\"" if ((!$options_is_null[$y]) && ($options_types[$y] eq "string"));
            my $color1 = weechat::color($options{color_option});
            my $color2 = weechat::color($options{color_type});
            my $color3 = "";
            if ($options_is_null[$y])
            {
                $color3 = weechat::color($options{color_value_undef});
            }
            else
            {
                $color3 = weechat::color($options{color_value});
            }
            if ($y == $current_line)
            {
                $color1 = weechat::color($options{color_option_selected}.",".$options{color_bg_selected});
                $color2 = weechat::color($options{color_type_selected}.",".$options{color_bg_selected});
                if ($options_is_null[$y])
                {
                    $color3 = weechat::color($options{color_value_undef_selected}.",".$options{color_bg_selected});
                }
                else
                {
                    $color3 = weechat::color($options{color_value_selected}.",".$options{color_bg_selected});
                }
            }
            my $value = $options_values[$y];
            $value = "(undef)" if ($options_is_null[$y]);
            my $strline = sprintf($format,
                                  $color1, $options_names[$y],
                                  $color2, $options_types[$y],
                                  $color3, $around, $value, $around);
            weechat::print_y($iset_buffer, $y, $strline);
        }
    }
}

sub iset_refresh
{
    iset_title();
    if (($iset_buffer ne "") && ($#options_names >= 0))
    {
        foreach my $y (0 .. $#options_names)
        {
            iset_refresh_line($y);
        }
    }
    weechat::bar_item_update("isetbar_help") if $options{show_help_bar}  eq 'on';
}

sub iset_full_refresh
{
    if ($iset_buffer ne "")
    {
        weechat::buffer_clear($iset_buffer);
        # search for "*" in $filter.
        if ($filter =~ m/\*/)
        {
            iset_get_options();
        }
        else
        {
            iset_get_values($filter);
            $iset_filter_title = "Filter (by value): ";
        }
        iset_set_current_line($current_line);
        iset_refresh();
        weechat::command($iset_buffer, "/window refresh");
    }
}

sub iset_set_current_line
{
    my $new_current_line = $_[0];
    my $old_current_line = $current_line;
    $current_line = $new_current_line;
    $current_line = $#options_names if ($current_line > $#options_names);
    if ($old_current_line != $current_line)
    {
        iset_refresh_line($old_current_line);
        iset_refresh_line($current_line);
        weechat::bar_item_update("isetbar_help") if $options{show_help_bar} eq 'on';
    }
}

sub iset_signal_window_scrolled_cb
{
    my ($data, $signal, $signal_data) = ($_[0], $_[1], $_[2]);
    if ($iset_buffer ne "")
    {
        my $infolist = weechat::infolist_get("window", $signal_data, "");
        if (weechat::infolist_next($infolist))
        {
            if (weechat::infolist_pointer($infolist, "buffer") eq $iset_buffer)
            {
                my $old_current_line = $current_line;
                my $new_current_line = $current_line;
                my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
                my $chat_height = weechat::infolist_integer($infolist, "chat_height");
                $new_current_line += $chat_height if ($new_current_line < $start_line_y);
                $new_current_line -= $chat_height if ($new_current_line >= $start_line_y + $chat_height);
                $new_current_line = $start_line_y if ($new_current_line < $start_line_y);
                $new_current_line = $start_line_y + $chat_height - 1 if ($new_current_line >= $start_line_y + $chat_height);
                iset_set_current_line($new_current_line);
            }
        }
        weechat::infolist_free($infolist);
    }
    
    return weechat::WEECHAT_RC_OK;
}

sub iset_get_window_number
{
    if ($iset_buffer ne "")
    {
        my $window = weechat::window_search_with_buffer($iset_buffer);
        return "-window ".weechat::window_get_integer ($window, "number")." " if ($window ne "");
    }
    return "";
}

sub iset_check_line_outside_window
{
    if ($iset_buffer ne "")
    {
        undef my $infolist;
        if ($wee_version_number >= 0x00030500)
        {
            my $window = weechat::window_search_with_buffer($iset_buffer);
            $infolist = weechat::infolist_get("window", $window, "") if $window;
        }
        else
        {
            $infolist = weechat::infolist_get("window", "", "current");
        }
        if ($infolist)
        {
            if (weechat::infolist_next($infolist))
            {
                my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
                my $chat_height = weechat::infolist_integer($infolist, "chat_height");
                my $window_number = "";
                if ($wee_version_number >= 0x00030500)
                {
                    $window_number = "-window ".weechat::infolist_integer($infolist, "number")." ";
                }
                if ($start_line_y > $current_line)
                {
                    weechat::command($iset_buffer, "/window scroll ".$window_number."-".($start_line_y - $current_line));
                }
                else
                {
                    if ($start_line_y <= $current_line - $chat_height)
                    {
                        weechat::command($iset_buffer, "/window scroll ".$window_number."+".($current_line - $start_line_y - $chat_height + 1));
                    }
                }
            }
            weechat::infolist_free($infolist);
        }
    }
}

sub iset_get_option_name_index
{
    my $option_name = $_[0];
    my $index = 0;
    while ($index <= $#options_names)
    {
        return -1 if ($options_names[$index] gt $option_name);
        return $index if ($options_names[$index] eq $option_name);
        $index++;
    }
    return -1;
}

sub iset_config_cb
{
    my ($data, $option_name, $value) = ($_[0], $_[1], $_[2]);
    
    if ($iset_buffer ne "")
    {
        return weechat::WEECHAT_RC_OK if (weechat::info_get("weechat_upgrading", "") eq "1");
        
        my $index = iset_get_option_name_index($option_name);
        if ($index >= 0)
        {
            # refresh info about changed option
            my $infolist = weechat::infolist_get("option", "", $option_name);
            if ($infolist)
            {
                weechat::infolist_next($infolist);
                if (weechat::infolist_fields($infolist))
                {
                    $options_types[$index] = weechat::infolist_string($infolist, "type");
                    $options_values[$index] = weechat::infolist_string($infolist, "value");
                    $options_is_null[$index] = weechat::infolist_integer($infolist, "value_is_null");
                    iset_refresh_line($index);
                }
                else
                {
                    iset_full_refresh();
                }
                weechat::infolist_free($infolist);
            }
        }
        else
        {
            iset_full_refresh() if ($option_name ne "weechat.bar.isetbar.hidden");
        }
        if ($option_name eq "plugins.var.perl.iset.show_help_bar")
        {
            my $show = 1;
            $show = 0 if ($value eq "off");
            iset_show_bar($show);
        }
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
    weechat::buffer_clear($iset_buffer);
    iset_refresh();
}


sub iset_cmd_cb
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    my $filter_set = 0;
    if (($args ne "") && (substr($args, 0, 2) ne "**"))
    {
        if ( substr( $args,0,1 ) eq $options{value_search_char} )
        {
            my $var_value = substr( $args, 1 );  # cut value_search_char
            if ($iset_buffer ne "")
            {
                weechat::buffer_clear($iset_buffer);
                weechat::command($iset_buffer, "/window refresh");
            }
            iset_init();
            iset_get_values($var_value);
            iset_refresh();
            weechat::buffer_set($iset_buffer, "display", "1");
            $iset_filter_title = "Filter (by value): ";
            $filter = $var_value;
            iset_title($iset_filter_title);
            return weechat::WEECHAT_RC_OK;
        }
        else
        {
            iset_filter($args);
            $filter_set = 1;
            my $ptrbuf = weechat::buffer_search("perl",$PRGNAME);
            if ($ptrbuf eq "")
            {
                iset_init();
                iset_get_options();
                iset_full_refresh();
                weechat::buffer_set(weechat::buffer_search("perl",$PRGNAME), "display", "1");
                return weechat::WEECHAT_RC_OK;
            }
        }
    }
    
    if ($iset_buffer eq "")
    {
        iset_init();
        iset_get_options();
        iset_refresh();
    }
    else
    {
        iset_full_refresh() if ($filter_set);
    }
    
    if ($args eq "")
    {
        weechat::buffer_set($iset_buffer, "display", "1");
    }
    else
    {
        if ($args eq "**refresh")
        {
            iset_full_refresh();
        }
        if ($args eq "**up")
        {
            if ($current_line > 0)
            {
                $current_line--;
                iset_refresh_line($current_line + 1);
                iset_refresh_line($current_line);
                iset_check_line_outside_window();
            }
        }
        if ($args eq "**down")
        {
            if ($current_line < $#options_names)
            {
                $current_line++;
                iset_refresh_line($current_line - 1);
                iset_refresh_line($current_line);
                iset_check_line_outside_window();
            }
        }
        if ($args eq "**left" && $wee_version_number >= 0x00030600)
        {
            weechat::command($iset_buffer, "/window scroll_horiz ".iset_get_window_number()."-".$options{scroll_horiz});
        }
        if ($args eq "**right" && $wee_version_number >= 0x00030600)
        {
            weechat::command($iset_buffer, "/window scroll_horiz ".iset_get_window_number().$options{scroll_horiz});
        }
        if ($args eq "**scroll_top")
        {
            my $old_current_line = $current_line;
            $current_line = 0;
            iset_refresh_line ($old_current_line);
            iset_refresh_line ($current_line);
            weechat::command($iset_buffer, "/window scroll_top ".iset_get_window_number());
        }
        if ($args eq "**scroll_bottom")
        {
            my $old_current_line = $current_line;
            $current_line = $#options_names;
            iset_refresh_line ($old_current_line);
            iset_refresh_line ($current_line);
            weechat::command($iset_buffer, "/window scroll_bottom ".iset_get_window_number());
        }
        if ($args eq "**toggle")
        {
            if ($options_types[$current_line] eq "boolean")
            {
                iset_set_option($options_names[$current_line], "toggle");
            }
        }
        if ($args eq "**incr")
        {
            if (($options_types[$current_line] eq "integer")
                || ($options_types[$current_line] eq "color"))
            {
                iset_set_option($options_names[$current_line], "++1");
            }
        }
        if ($args eq "**decr")
        {
            if (($options_types[$current_line] eq "integer")
                || ($options_types[$current_line] eq "color"))
            {
                iset_set_option($options_names[$current_line], "--1");
            }
        }
        if ($args eq "**reset")
        {
            iset_reset_option($options_names[$current_line]);
        }
        if ($args eq "**unset")
        {
            iset_unset_option($options_names[$current_line]);
        }
        if ($args eq "**toggle_help")
        {
            if ($options{show_help_bar} eq "on")
            {
                weechat::config_set_plugin("show_help_bar", "off");
            }
            else
            {
                weechat::config_set_plugin("show_help_bar", "on");
                iset_show_bar(1);
            }
        }
        if ($args eq "**toggle_show_plugin_desc")
        {
            if ($options{show_plugin_description} eq "on")
            {
                weechat::config_set_plugin("show_plugin_description", "off");
                iset_full_refresh();
            }
            else
            {
                weechat::config_set_plugin("show_plugin_description", "on");
                iset_full_refresh();
            }
        }
        if ($args eq "**set")
        {
            my $quote = "";
            my $value = $options_values[$current_line];
            if ($options_is_null[$current_line])
            {
                $value = "null";
            }
            else
            {
                $quote = "\"" if ($options_types[$current_line] eq "string");
            }
            weechat::buffer_set($iset_buffer, "input", "/set ".$options_names[$current_line]." ".$quote.$value.$quote);
            weechat::command($iset_buffer, "/input move_beginning_of_line");
            weechat::command($iset_buffer, "/input move_next_word");
            weechat::command($iset_buffer, "/input move_next_word");
            weechat::command($iset_buffer, "/input move_next_char");
            weechat::command($iset_buffer, "/input move_next_char") if ($quote ne "");
        }
    }
    weechat::bar_item_update("isetbar_help") if $options{show_help_bar} eq 'on';
    return weechat::WEECHAT_RC_OK;
}

sub iset_get_help
{
    return '' unless $options{show_help_bar} eq 'on';

    if (not defined $options_names[$current_line])
    {
        return "No option selected. Set a new filter using command line (use '*' to see all options)";
    }
    if ($options_name_copy eq $options_names[$current_line])
    {
        return $description;
    }
    $options_name_copy = $options_names[$current_line];
    my $optionlist ="";
    $optionlist = weechat::infolist_get("option", "", $options_names[$current_line]);
    weechat::infolist_next($optionlist);
    my $full_name = weechat::infolist_string($optionlist,"full_name");
    my $option_desc = "";
    my $option_default_value = "";
    my $option_range = "";
    my $possible_values = "";
    my $re = qq(\Q$full_name);
    if (grep (/^$re$/,$options_names[$current_line]))
    {
        $option_desc = weechat::infolist_string($optionlist, "description_nls");
        $option_desc = weechat::infolist_string($optionlist, "description") if ($option_desc eq "");
        $option_desc = "No help found" if ($option_desc eq "");
        $option_default_value = weechat::infolist_string($optionlist, "default_value");
        $possible_values = weechat::infolist_string($optionlist, "string_values") if (weechat::infolist_string($optionlist, "string_values") ne "" );
        if ((weechat::infolist_string($optionlist, "type") eq "integer") && ($possible_values eq ""))
        {
            $option_range = weechat::infolist_integer($optionlist, "min")
                ." .. ".weechat::infolist_integer($optionlist, "max");
        }
    }
    weechat::infolist_free($optionlist);
    iset_title();
    
    $description = weechat::color($options{color_help_option_name}).$options_names[$current_line]
        .weechat::color("bar_fg").": "
        .weechat::color($options{color_help_text}).$option_desc;
    
    # show additional infos like default value and possible values
    if ($options{show_help_extra_info} eq "on")
    {
        $description .=
            weechat::color("bar_delim")." ["
            .weechat::color("bar_fg")."default: "
            .weechat::color("bar_delim")."\""
            .weechat::color($options{color_help_default_value}).$option_default_value
            .weechat::color("bar_delim")."\"";
        if ($option_range ne "")
        {
            $description .= weechat::color("bar_fg").", values: ".$option_range;
        }
        if ($possible_values ne "")
        {
            $possible_values =~ s/\|/", "/g;      # replace '|' to '", "'
            $description .= weechat::color("bar_fg").", values: ". "\"" . $possible_values . "\"";

        }
        $description .= weechat::color("bar_delim")."]";
    }
    return $description;
}

sub iset_check_condition_isetbar_cb
{
    my ($data, $modifier, $modifier_data, $string) = ($_[0], $_[1], $_[2], $_[3]);
    my $buffer = weechat::window_get_pointer($modifier_data, "buffer");
    if ($buffer ne "")
    {
        if ((weechat::buffer_get_string($buffer, "plugin") eq "perl")
            && (weechat::buffer_get_string($buffer, "name") eq $PRGNAME))
        {
            return "1";
        }
    }
    return "0";
}

sub iset_show_bar
{
    my $show = $_[0];
    my $barhidden = weechat::config_get("weechat.bar.isetbar.hidden");
    if ($barhidden)
    {
        if ($show)
        {
            if ($options{show_help_bar} eq "on")
            {
                if (weechat::config_boolean($barhidden))
                {
                    weechat::config_option_set($barhidden, 0, 1);
                }
            }
        }
        else
        {
            if (!weechat::config_boolean($barhidden))
            {
                weechat::config_option_set($barhidden, 1, 1);
            }
        }
    }
}

sub iset_signal_buffer_switch_cb
{
    my $buffer_pointer = $_[2];
    my $show_bar = 0;
    $show_bar = 1 if (weechat::buffer_get_integer($iset_buffer, "num_displayed") > 0);
    iset_show_bar($show_bar);
    iset_check_line_outside_window() if ($buffer_pointer eq $iset_buffer);
    return weechat::WEECHAT_RC_OK;
}

sub iset_item_cb
{
    return iset_get_help();
}

sub iset_upgrade_ended
{
    iset_full_refresh();
}

sub iset_end
{
    # when script is unloaded, we hide bar
    iset_show_bar(0);
}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.iset."), length($name));
    $options{$name} = $value;
    iset_full_refresh();
    return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ mouse support ]-------------------------------------
sub hook_focus_iset_cb
{
    my %info = %{$_[1]};
    my $bar_item_line = int($info{"_bar_item_line"});
    undef my $hash;
    if (($info{"_buffer_name"} eq $PRGNAME) && $info{"_buffer_plugin"} eq "perl" && ($bar_item_line >= 0) && ($bar_item_line <= $#iset_focus))
    {
        $hash = $iset_focus[$bar_item_line];
    }
    else
    {
        $hash = {};
        my $hash_focus = $iset_focus[0];
        foreach my $key (keys %$hash_focus)
        {
            $hash->{$key} = "?";
        }
    }
    return $hash;
}

# _chat_line_y contains selected line
sub iset_hsignal_mouse_cb
{
    my ($data, $signal, %hash) = ($_[0], $_[1], %{$_[2]});
 
    if ($hash{"_buffer_name"} eq $PRGNAME && ($hash{"_buffer_plugin"} eq "perl"))
    {
        if ($hash{"_key"} eq "button2")
        {
            if ($options_types[$hash{"_chat_line_y"}] eq "boolean")
            {
                iset_set_option($options_names[$hash{"_chat_line_y"}], "toggle");
                $current_line = $hash{"_chat_line_y"};
                iset_refresh_line($current_line);
                iset_refresh();
            }
            elsif ($options_types[$hash{"_chat_line_y"}] eq "string")
            {
                $current_line = $hash{"_chat_line_y"};
                iset_refresh_line($current_line);
                iset_refresh();
                weechat::command("", "/$PRGNAME **set");
            }
        }
        elsif ($hash{"_key"} eq "button2-gesture-left")
        {
            if ($options_types[$hash{"_chat_line_y"}] eq "integer" or ($options_types[$hash{"_chat_line_y"}] eq "color"))
            {
                $current_line = $hash{"_chat_line_y"};
                iset_refresh_line($current_line);
                iset_refresh();
                weechat::command("", "/$PRGNAME **decr");
            }
        }
        elsif ($hash{"_key"} eq "button2-gesture-right")
        {
            if ($options_types[$hash{"_chat_line_y"}] eq "integer"  or ($options_types[$hash{"_chat_line_y"}] eq "color"))
            {
                $current_line = $hash{"_chat_line_y"};
                iset_refresh_line($current_line);
                iset_refresh();
                weechat::command("", "/$PRGNAME **incr");
            }
        }
    }
}
# -----------------------------------[ main ]-----------------------------------------
weechat::register($PRGNAME, $AUTHOR, $VERSION, $LICENSE,
                  $DESCR, "iset_end", "");

$wee_version_number = weechat::info_get("version_number", "") || 0;

weechat::hook_command($PRGNAME, "Interactive set", "f <file> || s <section> || [=]<text>",
                      "f file     : show options for a file\n".
                      "s section  : show options for a section\n".
                      "text       : show options with 'text' in name\n".
                      weechat::config_get_plugin("value_search_char")."text      : show options with 'text' in value\n\n".
                      "Keys for iset buffer:\n".
                      "f11,f12        : move iset content left/right\n".
                      "up,down        : move one option up/down\n".
                      "pgup,pdwn      : move one page up/down\n".
                      "home,end       : move to first/last option\n".
                      "ctrl+'L'       : refresh options and screen\n".
                      "alt+space      : toggle boolean on/off\n".
                      "alt+'+'        : increase value (for integer or color)\n".
                      "alt+'-'        : decrease value (for integer or color)\n".
                      "alt+'i',alt+'r': reset value of option\n".
                      "alt+'i',alt+'u': unset option\n".
                      "alt+enter      : set new value for option (edit it with command line)\n".
                      "text,enter     : set a new filter using command line (use '*' to see all options)\n".
                      "alt+'v'        : toggle help bar on/off\n".
                      "alt+'p'        : toggle option \"show_plugin_description\" on/off\n\n".
                      "Examples:\n".
                      "  show options for file 'weechat'\n".
                      "    /iset f weechat\n".
                      "  show options for file 'irc'\n".
                      "    /iset f irc\n".
                      "  show options for section 'look'\n".
                      "    /iset s look\n".
                      "  show all options with text 'nicklist' in name\n".
                      "    /iset nicklist\n".
                      "  show all values which contain 'red'. '" . weechat::config_get_plugin("value_search_char"). "' is a trigger char.\n".
                      "    /iset ".weechat::config_get_plugin("value_search_char")."red\n",
                      "", "iset_cmd_cb", "");
weechat::hook_signal("upgrade_ended", "iset_upgrade_ended", "");
weechat::hook_signal("window_scrolled", "iset_signal_window_scrolled_cb", "");
weechat::hook_signal("buffer_switch", "iset_signal_buffer_switch_cb","");
weechat::bar_item_new("isetbar_help", "iset_item_cb", "");
weechat::bar_new("isetbar", "on", "0", "window", "", "top", "horizontal",
                 "vertical", "3", "3", "default", "cyan", "default", "1",
                 "isetbar_help");
weechat::hook_modifier("bar_condition_isetbar", "iset_check_condition_isetbar_cb", "");
iset_init_config();
weechat::hook_config("*", "iset_config_cb", "");
weechat::hook_config( "plugins.var.perl.iset.*", "toggle_config_by_set", "" );
$iset_buffer = weechat::buffer_search("perl", $PRGNAME);
iset_init() if ($iset_buffer ne "");

if ($wee_version_number >= 0x00030600)
{
    weechat::hook_focus("chat", "hook_focus_iset_cb", "");
    weechat::hook_hsignal($PRGNAME."_mouse", "iset_hsignal_mouse_cb", "");
    weechat::key_bind("mouse", \%mouse_keys);
}
