#
# Copyright (c) 2008-2009 by FlashCode <flashcode@flashtux.org>
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

#
# Display sidebar with list of buffers.
#
# History:
# 2009-01-04, FlashCode <flashcode@flashtux.org>:
#     v0.8: update syntax for command /set (comments)
# 2008-10-20, Jiri Golembiovsky <golemj@gmail.com>:
#     v0.7: add indenting option
# 2008-10-01, FlashCode <flashcode@flashtux.org>:
#     v0.6: add default color for buffers, and color for current active buffer
# 2008-09-18, FlashCode <flashcode@flashtux.org>:
#     v0.5: fix color for "low" level entry in hotlist
# 2008-09-18, FlashCode <flashcode@flashtux.org>:
#     v0.4: rename option "show_category" to "short_names",
#           remove option "color_slash"
# 2008-09-15, FlashCode <flashcode@flashtux.org>:
#     v0.3: fix bug with priority in hotlist (var not defined)
# 2008-09-02, FlashCode <flashcode@flashtux.org>:
#     v0.2: add color for buffers with activity and config options for
#           colors, add config option to display/hide categories
# 2008-03-15, FlashCode <flashcode@flashtux.org>:
#     v0.1: script creation
#
# Help about settings:
#   display short names (remove text before first "." in buffer name):
#      /set plugins.var.perl.buffers.short_names on
#   use indenting for some buffers like IRC channels:
#      /set plugins.var.perl.buffers.indenting on
#   change colors:
#      /set plugins.var.perl.buffers.color_number color
#      /set plugins.var.perl.buffers.color_default color
#      /set plugins.var.perl.buffers.color_hotlist_low color
#      /set plugins.var.perl.buffers.color_hotlist_message color
#      /set plugins.var.perl.buffers.color_hotlist_private color
#      /set plugins.var.perl.buffers.color_hotlist_highlight color
#      /set plugins.var.perl.buffers.color_current color
#   (replace "color" by your color, which may be "fg" or "fg,bg")
#

use strict;

my $version = "0.8";

# -------------------------------[ config ]-------------------------------------

my $default_short_names = "off";
my $default_indenting   = "off";

my %hotlist_level = (0 => "low", 1 => "message", 2 => "private", 3 => "highlight");
my %default_color_hotlist = ("low"       => "white",
                             "message"   => "yellow",
                             "private"   => "lightgreen",
                             "highlight" => "magenta");
my $default_color_number = "lightgreen";

# --------------------------------[ init ]--------------------------------------

weechat::register("buffers", "FlashCode <flashcode\@flashtux.org>", $version,
                  "GPL3", "Sidebar with list of buffers", "", "");
if (weechat::config_get_plugin("short_names") eq "")
{
    weechat::config_set_plugin("short_names", $default_short_names);
}
if (weechat::config_get_plugin("indenting") eq "")
{
    weechat::config_set_plugin("indenting", $default_indenting);
}
if (weechat::config_get_plugin("color_number") eq "")
{
    weechat::config_set_plugin("color_number", $default_color_number);
}
if (weechat::config_get_plugin("color_default") eq "")
{
    weechat::config_set_plugin("color_default", "default");
}
foreach my $level (values %hotlist_level)
{
    if (weechat::config_get_plugin("color_hotlist_".$level) eq "")
    {
        weechat::config_set_plugin("color_hotlist_".$level,
                                   $default_color_hotlist{$level});
    }
}
if (weechat::config_get_plugin("color_current") eq "")
{
    weechat::config_set_plugin("color_current", "lightcyan,red");
}
weechat::bar_item_new("buffers", "build_buffers");
weechat::bar_new("buffers", "0", "0", "root", "", "left", "horizontal",
                 "vertical", "0", "0", "default", "default", "default", "1",
                 "buffers");
weechat::hook_signal("buffer_*", "buffers_signal_buffer");
weechat::hook_signal("hotlist_*", "buffers_signal_hotlist");
weechat::hook_config("plugins.var.perl.buffers.*", "buffers_signal_config");
weechat::hook_timer(1, 0, 1, "buffers_timer_one_time");

# ------------------------------------------------------------------------------

sub build_buffers
{
    my $str = "";
    
    # read hotlist
    my %hotlist;
    my $infolist = weechat::infolist_get("hotlist", "", "");
    while (weechat::infolist_next($infolist))
    {
        $hotlist{weechat::infolist_integer($infolist, "buffer_number")} =
            weechat::infolist_integer($infolist, "priority");
    }
    weechat::infolist_free($infolist);
    
    # read buffers list
    $infolist = weechat::infolist_get("buffer", "", "");
    while (weechat::infolist_next($infolist))
    {
        my $color = weechat::config_get_plugin("color_default");
        $color = "default" if ($color eq "");
        my $bg = "";
        my $number = weechat::infolist_integer($infolist, "number");
        if (exists $hotlist{$number})
        {
            $color = weechat::config_get_plugin("color_hotlist_"
                                                .$hotlist_level{$hotlist{$number}});
        }
        if (weechat::infolist_integer($infolist, "current_buffer") == 1)
        {
            $color = weechat::config_get_plugin("color_current");
            $bg = $1 if ($color =~ /.*,(.*)/);
        }
        my $color_bg = "";
        $color_bg = weechat::color(",".$bg) if ($bg ne "");
        $str .= weechat::color(weechat::config_get_plugin("color_number"))
            .$color_bg
            .weechat::infolist_integer($infolist, "number")
            .weechat::color("default")
            .$color_bg
            ."."
            .weechat::color($color);
        if (weechat::config_get_plugin("indenting") eq "on")
        {
            if ((weechat::infolist_string($infolist, "plugin_name") eq "irc")
                && (weechat::info_get("irc_is_channel",
                                      weechat::infolist_string($infolist, "short_name")) eq "1"))
            {
                $str .= "  ";
            }
        }
        if (weechat::config_get_plugin("short_names") eq "on")
        {
            $str .= weechat::infolist_string($infolist, "short_name");
        }
        else
        {
            $str .= weechat::infolist_string($infolist, "name");
        }
        $str .= "\n";
    }
    weechat::infolist_free($infolist);
    
    return $str;
}

sub buffers_signal_buffer
{
    weechat::bar_item_update("buffers");
    return weechat::WEECHAT_RC_OK;
}

sub buffers_signal_hotlist
{
    weechat::bar_item_update("buffers");
    return weechat::WEECHAT_RC_OK;
}

sub buffers_signal_config
{
    weechat::bar_item_update("buffers");
    return weechat::WEECHAT_RC_OK;
}

sub buffers_timer_one_time
{
    weechat::bar_item_update("buffers");
    return weechat::WEECHAT_RC_OK;
}
