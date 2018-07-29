# This script requires weechat 0.3.0 or newer
# It will probably ONLY work on linux and only
# if the user can access the /proc filesystem
#
# History:
#
# 2018-05-14, CrazyCat <crazycat@c-p-f.org>
#   version 1.2 : added check for no swap
# 2009-10-13, wishbone <djwishbone@gmail.com>
#   version 1: initial release
#
# This script is a machine statistics bar project.
# Currently it has three different stat options that
# can be added to any bar.
# 'inf_stat'  : interface throughput statistics
# 'load_stat' : cpu load information
# 'mem_Stat'  : machine memory free percentages
#
# In addition there are two new variables you
# may want to set.
#
# stats_interface : eg. eth1, en0, etc..
# /set plugins.var.perl.interface_stats.stats_interface "eth1"
# eth1 is the default
#
# stats_refresh : refresh time in sections
# It's default is set to 10 seconds.
#
#
# I usually make a new bar for this script
# eg.
# /bar add mystats window bottom 1 0 [inf_stats],[load_stats],[mem_stats]
#
# The plugin iset will make things MUCH easier for you.
# Consider getting that if you haven't already.
#
# I've tried to make this script as extensible as
# possible.  It should be very simple for most
# people familar with perl to add a new monitor
# for whatever they like.  If you get stuck just
# email me.
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
# TODO:
# Create stats_bar command to get details printed to screen or channel
# Add more monitors?  (email me if you have suggestions)


   
###########################################################
# initialization
#

use strict;

my $VERSION = "1.2";
weechat::register("stats_bar","wishbone",$VERSION,"GPL3","statistics bar", "", "");

my ($refresh,$old_refresh) = (10,0);
my ($refresh_hook, $config_hook1, $config_hook2) = ("","","");
my ($last_in, $last_out) = (0.0,0.0);
my ($cur_in, $cur_out) = (0.0,0.0);
my %stats_data =(
	inf_stats => "0",
	load_stats => "0",
	mem_stats => "0",
	temp_stats => "0",
	);
my $stats_interface = "";



if (!weechat::config_is_set_plugin('stats_refresh')) {
	weechat::config_set_plugin('stats_refresh',$refresh);
} else {
	$refresh = weechat::config_get_plugin('stats_refresh');
	$old_refresh = $refresh;

}

if (!weechat::config_is_set_plugin('stats_interface')) {
# Do not edit this value.  Set it in the weechat config
# options with /set.
	weechat::config_set_plugin('stats_interface',"eth1");
} else {
	$stats_interface = weechat::config_get_plugin('stats_interface');

}


weechat::bar_item_new('inf_stats','stats_cb',"inf_stats");
weechat::bar_item_new('load_stats','stats_cb',"load_stats");
weechat::bar_item_new('mem_stats','stats_cb',"mem_stats");
weechat::bar_item_new('temp_stats','stats_cb',"temp_stats");
refresh_stats_cb();
$refresh_hook = weechat::hook_timer($refresh*1000, 0,0,'refresh_stats_cb', "");



######################################################
# subs
#


sub stats_cb {
  my $item = shift;
  my $get_sub_s = "get_".$item;
  my $get_sub = \&$get_sub_s;
#  weechat::print("","$get_sub_s");
  &{ $get_sub }();
#  weechat::print("","$stats_data{$item}");
  return "$stats_data{$item}";
}

sub refresh_stats_cb {
  weechat::bar_item_update('inf_stats');
  weechat::bar_item_update('load_stats');
  weechat::bar_item_update('mem_stats');
  weechat::bar_item_update('temp_stats');
  return weechat::WEECHAT_RC_OK;
}

sub read_settings {
  $refresh = weechat::config_get_plugin('stats_refresh');
  $stats_interface = weechat::config_get_plugin('stats_interface');
  $refresh = 1 if $refresh < 1;
  if ($refresh != $old_refresh) {
  	$old_refresh = $refresh;
	weechat::unhook($refresh_hook);
	$refresh_hook = weechat::hook_timer($refresh*1000, 0,0,'refresh_stats_cb', "");
  }


  return weechat::WEECHAT_RC_OK;

}

sub get_load_stats {
        my @lines = ();

        if (!open(DEV, "< /proc/loadavg")) {
                weechat::print("","Failed to open /proc/loadavg!");
                #weechat::unhook($refresh_hook);
        } else {
                @lines = <DEV>;
                close DEV;
                chomp @lines;
             #   @lines = grep(/^\s*($stats_interface)/,@lines);
                if (@lines) {
                if ($lines[0] !~ /^(\d.\d\d) (\d.\d\d) (\d.\d\d) (\d+\/\d+)/) {
			weechat::print("","loadavg did not fit expected pattern");
                        #weechat::unhook($refresh_hook);
			
                } else {
			$stats_data{load_stats} = "l:$1 $2 $3 $4";

                }
                } else {
                        weechat::print("","nothing in /proc/loadavg");

                        #weechat::unhook($refresh_hook);

                }
        }


}

sub get_inf_stats {
	my @lines = ();
	my ($old_in, $old_out) = ($last_in, $last_out);

	if (!open(DEV, "< /proc/net/dev")) {
    		weechat::print("","Failed to open proc/net/dev!");
		#weechat::unhook($refresh_hook);
	} else {
   		@lines = <DEV>;
		close DEV;
		chomp @lines;
		@lines = grep(/^\s*($stats_interface)/,@lines);
		if (@lines) {
		if ($lines[0] !~ /^(\s*)(.*):\s*(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)/) {
		} else {
			$last_in = $3;
			$last_out = $4;
			if ($old_out==0){return;}
			$cur_out=($last_out-$old_out) / ($refresh*1024);
			$cur_in=($last_in-$old_in) / ($refresh*1024);
			$stats_data{inf_stats} = sprintf("i:%.2f o:%.2f",$cur_in, $cur_out);

		}
		} else {
			weechat::print("","$stats_interface interface not found.  Please check stats_bar plugin variable!");
			#weechat::unhook($refresh_hook);

		}
	}
}


sub get_mem_stats {
	my @lines = ();
	my ($memtotal, $memfree, $swaptotal, $swapfree, $mem_percentage, $swap_percentage) = (1,1,1,1,1,1);

	if (!open(DEV, "< /proc/meminfo")) {
    		weechat::print("","Failed to open /proc/meminfo!");
		#weechat::unhook($refresh_hook);
	} else {
   		@lines = <DEV>;
		close DEV;
		chomp @lines;
		@lines = grep(/(MemTotal|MemFree|SwapTotal|SwapFree)/,@lines);
		if (@lines == 4) {
			($memtotal) = ($lines[0] =~ /^MemTotal:\s+(\d+)/);
			($memfree) = ($lines[1] =~ /^MemFree:\s+(\d+)/);
			($swaptotal) = ($lines[2] =~ /^SwapTotal:\s+(\d+)/);
			($swapfree) = ($lines[3] =~ /^SwapFree:\s+(\d+)/);
			$mem_percentage = ($memfree/$memtotal)*100;
			if ($swaptotal == 0) {
				$swap_percentage = 0;
			} else {
				$swap_percentage = ($swapfree/$swaptotal)*100;
			}
			$stats_data{mem_stats} = sprintf("m:%.0f%% s:%.0f%%",$mem_percentage, $swap_percentage);

		} else {
			weechat::print("","Unexpected output from /proc/meminfo.");
			#weechat::unhook($refresh_hook);

		}
	}
}

sub get_temp_stats {
	my @lines = ();
	my ($tempmil,$temp);
	if (!open(DEV, "< /sys/class/thermal/thermal_zone0/temp")) {
		weechat::print("", "Failed to open /sys/class/thermal/thermal_zone0/temp");
	} else {
		@lines = <DEV>;
		close DEV;
		chomp @lines;
		($tempmil) = ($lines[0] =~ /(\d+)/);
		$temp = ($tempmil)/1000;
		$stats_data{temp_stats} = sprintf("CPU:%2.1lf°C", $temp);
	}
}
