#
# Copyright (c) 2010-2011 by trenki <trechris@gmx.net>
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
# Thinklight blink on highlight/private msg.
# based on beep script  by FlashCode <flashcode@flashtux.org>
#
# Needs /sys/class/leds/tpacpi\:\:thinklight/brightness to be r+w
# as root type:
# chmod 666 /sys/class/leds/tpacpi\:\:thinklight/brightness
# 
# see also http://www.thinkwiki.org/wiki/ThinkLight
# 
#
# CHANGELOG:
# 0.1 
# Initial Release
# 0.2
# add subroutine for both hooks
# add threaded non blocking function
# 0.3
# uses weechat::hook_timer
# 
# 
#use Time::HiRes;
#use threads;
use warnings;
use feature qw/switch/;

my $version = "0.3";
my $blink_command_on = "echo 255 > /sys/class/leds/tpacpi\:\:thinklight/brightness";
my $blink_command_off = "echo 0 > /sys/class/leds/tpacpi\:\:thinklight/brightness";
my $blink_command_stat = "cat /sys/class/leds/tpacpi\:\:thinklight/brightness";

# default values in setup file (~/.weechat/plugins.conf)
my $default_blink_highlight = "on";
my $default_blink_pv        = "on";

weechat::register("thinklight_blink", "trenki <trechris\@gmx.net>", $version,
                  "GPL3", "Thinklight blink on highlight/private message", "", "");
weechat::config_set_plugin("blink_highlight", $default_blink_highlight) if (weechat::config_get_plugin("blink_highlight") eq "");
weechat::config_set_plugin("blink_pv", $default_blink_pv) if (weechat::config_get_plugin("blink_pv") eq "");

weechat::hook_signal("weechat_highlight", "highlight", "");
weechat::hook_signal("irc_pv", "pv", "");


sub highlight
{
    my $blink = weechat::config_get_plugin("blink_highlight");
    weechat::hook_timer( 750, 0, 6, "tpblink", "");
    return weechat::WEECHAT_RC_OK;
}

sub pv
{
    my $blink = weechat::config_get_plugin("blink_pv");
    weechat::hook_timer( 750, 0, 6, "tpblink", "");
    return weechat::WEECHAT_RC_OK;
}

sub tpblink
{
    my $return_value = `cat /sys/class/leds/tpacpi\:\:thinklight/brightness`;
    if($return_value == 255)
    {
        system($blink_command_off);
    }
    else
    {
        system($blink_command_on);
    }
}
