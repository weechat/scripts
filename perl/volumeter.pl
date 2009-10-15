# Copyright (c) 2009 by Nils Görs <weechatter@arcor.de>
#
# based on the irssi script by Riku Voipio <riku.voipio@iki.fi>
# and rewritten for weechat after a request from wishbone in irc.freenode.net/#weechat
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
# v0.2:	- settings will be set on startup if not exists (suggested by xt)
#	- TiB (TeraByte) support added (suggested by xt)
#	- /proc/net/dev will be used instead of mrtg-ip-acct (suggested by xt)
# v0.1: first release.

# configuration:
# to make volumeter visible you have to add ",[volumeter]" (without "")
# in your weechat.bar.status.items

# /set plugins.var.perl.volumeter.device_name "wlan0"
# /set plugins.var.perl.volumeter.refresh_rate "1000"
# /set plugins.var.perl.volumeter.display_char "Mb"
# possible display_chars are:
# "TiB" = TeraByte
# "MiB" = MegaByte
# "KiB" = KiloByte
# "Byt" = Byte
# after changing your settings you have to "/perl reload" (without "") the script.

use strict;
my $program_name = "volumeter";
my $version = "0.2";
my $description = "shows volume usage in statusbar";
my $device = "eth0";					# standard device of mrtg-ip-acct
my $device_name = "device_name";			# name for device-setting
my $refresh_rate = "5000";
my $refresh_rate_name = "refresh_rate";			# name for refresh-setting
my $display_char = "MiB";				# TiB (Tera), GiB (Giga), MiB (Mega) KiB (Kilo) and byt (byte)
my $display_char_name = "display_char";			# name for char-setting
my $bar_output = "";
my ($last_in, $last_out) = (0.0,0.0);
my @localstats;
my $procnetdev =  "/proc/net/dev";			# name of file

# first function called by a WeeChat-script
weechat::register($program_name, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

  unless (-e $procnetdev){
    weechat::print("",$procnetdev . "does not exists.");
return weechat::WEECHAT_RC_ERROR;
 
 }
  get_config();

  weechat::bar_item_new($program_name, "refresh_stats","");
  weechat::hook_timer($refresh_rate,1,0,"volumeter_update","");

return weechat::WEECHAT_RC_OK;

### sub-routines
sub get_stats
{
  my $tmp = `cat "$procnetdev" | grep "$device"`;
  $last_out = (($tmp =~ m/(\d+)/g)[9]);			# get last_out
  $last_in = (($tmp =~ m/(\d+)/g)[1]);			# get last_in
  return;
}

sub refresh_stats{
  get_stats();
  calculate_value($last_in,$last_out);
  $bar_output = $device . ": " . $bar_output;
 return $bar_output;
}
sub volumeter_update{
      weechat::bar_item_update('volumeter');
        return weechat::WEECHAT_RC_OK
}
sub calculate_value{
  my ($in_value, $out_value) = ($_[0], $_[1]);				# get argument

  if ($display_char eq "KiB"){
    $in_value = ($in_value / (1024));
    $in_value = sprintf("%.2fKiB" , $in_value);
    $out_value = ($out_value / (1024));
    $out_value = sprintf("%.2fKiB" , $out_value);
    $bar_output = "i:" . $in_value . " o:" . $out_value;
    return;
  }
  if ($display_char eq "MiB"){
    $in_value = ($in_value / (1024*1024));
    $in_value = sprintf("%.2fMiB" , $in_value);
    $out_value = ($out_value / (1024*1024));
    $out_value = sprintf("%.2fMiB" , $out_value);
    $bar_output = "i:" . $in_value . " o:" . $out_value;
    return;
  }
  if ($display_char eq "GiB"){
    $in_value = ($in_value / (1024*1024*1024));
    $in_value = sprintf("%.3fGiB" , $in_value);
    $out_value = ($out_value / (1024*1024*1024));
    $out_value = sprintf("%.3fGiB" , $out_value);
    $bar_output = "i:" . $in_value . " o:" . $out_value;
    return;
  }
  if ($display_char eq "TiB"){
    $in_value = ($in_value / (1024*1024*1024*1024));
    $in_value = sprintf("%.3fTiB" , $in_value);
    $out_value = ($out_value / (1024*1024*1024*1024));
    $out_value = sprintf("%.3fTiB" , $out_value);
    $bar_output = "i:" . $in_value . " o:" . $out_value;
    return;
  }
    $in_value = sprintf("%.0fByt" , $in_value);				# Byte value
    $out_value = sprintf("%.0fByt" , $out_value);
    $bar_output = "i:" . $in_value . " o:" . $out_value;
}

sub get_config{
	my $result_conf = weechat::config_get_plugin($refresh_rate_name);
	  if ($result_conf ne ""){
	      $refresh_rate = $result_conf;
	  }
	  else{
	      weechat::config_set_plugin($refresh_rate_name, $refresh_rate);
	  }
	$result_conf = weechat::config_get_plugin($device_name);
	  if ($result_conf ne ""){
	      $device = $result_conf;
	  }
	  else{
	      weechat::config_set_plugin($device_name, $device);
	  }
	$result_conf = weechat::config_get_plugin($display_char_name);
	  if ($result_conf ne ""){
	      $display_char = $result_conf;
	  }
	  else{
	      weechat::config_set_plugin($display_char_name, $display_char);
	  }
}
