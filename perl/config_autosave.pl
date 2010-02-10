#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# autosave config-files after a specified time.
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
# usage:
# save all config files:
# /set plugins.var.perl.config_autosave.files "all"
#
# comma separated list of config files you would like to save (without ".conf" suffix!):
# /set plugins.var.perl.config_autosave.files "weechat,plugins,aspell,xfer,alias,irc,jabber,urlgrab,wg,logger,charset"
#
# time in hours to store config file(s) (0 means off):
# /set plugins.var.perl.config_autosave.period <hours>
#
# mute (don't print output when config was saved):
# /set plugins.var.perl.config_autosave.mute <on|off>
#
# v0.3: using the new "version_number" function to get the version number
# v0.2: supports "/mute" command (weechat v0.3.2-dev and higher required!)
# v0.1: initial release


use strict;
my $prgname	= "config_autosave";
my $version	= "0.3";
my $description	= "saves your config after a specified time.";
# default values
my $period	= 1;  			# hours between /save
my $files	= "all";		# /save all config-files
my $mute	= "on";			# hide output?
my %Hooks	= ();
my $min_version = "";

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

check_version();

# check config, if exists
if (!weechat::config_is_set_plugin("period")){
  weechat::config_set_plugin("period", $period);
}else{
  $period = weechat::config_get_plugin("period");
}
if(!weechat::config_is_set_plugin("files")){
   weechat::config_set_plugin("files", $files);
}
if(!weechat::config_is_set_plugin("mute")){
   weechat::config_set_plugin("mute", $mute);
}

weechat::hook_config( "plugins.var.perl.$prgname.period", 'toggle_period', "" );

hook_timer() if ($period ne "0");

sub hook_timer{
	$Hooks{timer} = weechat::hook_timer($period * 1000 * 60 * 60, 0, 0, "save_config", "");	# period * millisec(1000) * second(60) * minutes(60) = hours
		if ($Hooks{timer} eq '')
		{
			weechat::print("","ERROR: can't enable $prgname, hook failed");
			return 0;
		}
	return 1;
}
sub unhook_timer{
	weechat::unhook($Hooks{timer}) if %Hooks;
	%Hooks = ();
}
# unhook timer if $period = 0
sub toggle_period{
	$period = $_[2];

	if (!weechat::config_is_set_plugin("period")){
	  $period = 1 ;
	  weechat::config_set_plugin("period", $period);
	}

	if ($period ne "0"){
		if (defined $Hooks{timer}) {
			unhook_timer();
			hook_timer();
			return weechat::WEECHAT_RC_OK;
		}
	}
	if ($period eq "0"){
		if (defined $Hooks{timer}) {
			weechat::print('',"$prgname disabled.");
			unhook_timer();
		}
	}else{
		if (not defined $Hooks{timer}){
			weechat::print("","$prgname enabled.");
			weechat::config_set_plugin($period, "0") unless hook_timer();		# fall back to '0', if hook fails
		}
	}
return weechat::WEECHAT_RC_OK;
}
sub save_config{
if (!weechat::config_is_set_plugin("files")){
  weechat::print("","ERROR: 'plugins.var.perl.$prgname.files' don't exists.");
  return weechat::WEECHAT_RC_OK;
}

my $cmd_save = "/save";

$mute = weechat::config_get_plugin("mute");
if ($mute eq "on" and $min_version == 0){
    $cmd_save = "/mute " . $cmd_save;
}

$files = weechat::config_get_plugin("files");
  if ($files eq "all"){
	weechat::command("", $cmd_save);
  }else{
      $files =~ tr/\,/ /;
	weechat::command("", $cmd_save . " " . $files);
  }
}
sub check_version{
  my $version_number = weechat::info_get("version_number", "");
  if (($version_number ne "") && ($version_number >= 0x00030200)){	# v0.3.2
	  $min_version = 0;						# current version is same or higher
  }else{
	  $min_version = 1;						# current version is older
  }
}
