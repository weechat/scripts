#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# just prints the beat time in Bar-Item.
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
# Config:
# Add [beat] to your weechat.bar.status.items
# 
# refresh rate in seconds:
# /set plugins.var.perl.beat.refresh <sec>
# history:
# 0.2 wrong string was set to config

use strict;
my $prgname	= "beat";
my $version	= "0.2";
my $description	= "Shows you the Beat-Internet-Time in Bar-Item";
# default values
my $refresh	= "60";	#seconds
my %Hooks	= ();

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

if (!weechat::config_is_set_plugin("refresh")){
  weechat::config_set_plugin("refresh", $refresh);
}else{
  $refresh = weechat::config_get_plugin("refresh");
}

weechat::hook_config( "plugins.var.perl.$prgname.refresh", 'toggle_refresh', "" );
hook_timer() if ($refresh ne "0");

sub item_update{
      weechat::bar_item_update('beat');
        return weechat::WEECHAT_RC_OK
}

sub show_beat {
    my $time = shift || time();

    unless ( $time =~ /^\d+$/ ) {
        weechat::print("","$prgname: time() format is wrong.");
    }

    return sprintf "@%d", ( ( $time+3600 ) % 86400 ) / 86.4;
}

# check out config settings
sub toggle_refresh{
	$refresh = $_[2];

	if (!weechat::config_is_set_plugin("refresh")){
	  $refresh = 60 ;
	  weechat::config_set_plugin("refresh", $refresh);
	}

	if ($refresh ne "0"){
		if (defined $Hooks{timer}) {
			unhook_timer();
			hook_timer();
			return weechat::WEECHAT_RC_OK;
		}
	}
	if ($refresh eq "0"){
		if (defined $Hooks{timer}) {
			unhook_timer();
		}
	}else{
		if (not defined $Hooks{timer}){
			weechat::config_set_plugin("refresh", "0") unless hook_timer();		# fall back to '0', if hook fails
		}
	}
return weechat::WEECHAT_RC_OK;
}
my $bar_item = "";
sub hook_timer{
	$Hooks{timer} = weechat::hook_timer($refresh * 1000, 60, 0, "item_update", "");
		if ($Hooks{timer} eq '')
		{
			weechat::print("","ERROR: can't enable $prgname, hook failed");
			return 0;
		}
	$bar_item = weechat::bar_item_new($prgname, "show_beat","");
	weechat::bar_item_update('beat');
	return 1;
}
sub unhook_timer{
	weechat::bar_item_remove($bar_item);
	weechat::unhook($Hooks{timer}) if %Hooks;
	%Hooks = ();
}
