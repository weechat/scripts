#
# Copyright (c) 2009 by Nils Görs <weechatter@arcor.de>
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
# waiting for hotlist is changing and then execute a user specified command
# with hotlist entries.
#
# I am using this script to display the hotlist with STDIN plasmoid on
# KDE desktop.
# http://www.kde-look.org/content/show.php/STDIN+Plasmoid?content=92309
#
# Script inspirated by LaoLang_cool
#
#
# hotlist_format uses the following settings:
# %H = use the highlight_char to mark a highligh message in channel
# %N = buffer number: 1 2 3 ....
# %S = short name of channel: #weechat
#
# to export the hotlist_format in your external command.
# %X
#
# Usage:
# following options are used from hotlist2extern:
# /set plugins.var.perl.hotlist2extern.external_command_hotlist = "echo \'WeeChat Aktivität: %X\' >~/.weechat/hotlist_output.txt"
# /set plugins.var.perl.hotlist2extern.external_command_hotlist_empty "echo 'Weechat: keine Aktivität ' >~/.weechat/hotlist_output.txt"
# /set plugins.var.perl.hotlist2extern.highlight_char = "*"
# /set plugins.var.perl.hotlist2extern.hotlist_format = "%H%N:%S"
# /set plugins.var.perl.hotlist2extern.lowest_priority = 0


use strict;
my $hotlist_format		= "%H%N:%S";
my $external_command_hotlist	= "echo \'WeeChat Aktivität: %X\' >~/.weechat/hotlist_output.txt";
my $external_command_hotist_empty	= "echo \'Weechat: keine Aktivität \' >~/.weechat/hotlist_output.txt";
my $highlight_char		= "*";
my $lowest_priority		= 0;

my $prgname	= "Hotlist2Extern";
my $version	= "0.2";
my $description	= "gives the information of hotlist to an external file/program";
my $current_buffer = "";


# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

     init();				# get user settings

     my $hotlist_hook = weechat::hook_signal("hotlist_changed", "hotlist_changed", "");
 
return weechat::WEECHAT_RC_OK;

my $plugin_name		= "";
my $buffer_name		= "";
my $buffer_number	= 0;
my $buffer_pointer	= 0;
my $short_name		= "";
my $res 		= "";
my $res2 		= "";
my $priority		= 0;
my @table		= ();
my $table		= "";

sub hotlist_changed{
my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);			# save callback from hook_signal
@table		= ();
$table		= "";

  $current_buffer = weechat::current_buffer;				# get current buffer
  my $hotlist = weechat::infolist_get("hotlist","","");			# Pointer to Infolist

   while (weechat::infolist_next($hotlist))
    {
        $priority = weechat::infolist_integer($hotlist, "priority");
	  $res = $hotlist_format;							# save hotlist format
	  $res2 = $external_command_hotlist;						# save external_hotlist format

	    $plugin_name = weechat::infolist_string($hotlist,"plugin_name");
	    $buffer_name = weechat::infolist_string($hotlist,"buffer_name");
	    ($buffer_number) = weechat::infolist_integer($hotlist,"buffer_number");	# get number of buffer
	    $buffer_pointer = weechat::infolist_pointer($hotlist, "buffer_pointer");	# Pointer to buffer
	    $short_name = weechat::buffer_get_string($buffer_pointer, "short_name");	# get short_name of buffer

	unless ($priority < $lowest_priority){
	  if ($priority > 0){								# priority high enough (for channel)? 3 for highlight!
	  create_output();
	  }else
	  {
	  create_output();
	  }
	}
    }
  weechat::infolist_free($hotlist);
	    $table = @table;
	    if ($table eq 0){
	      unless ($external_command_hotist_empty eq ""){				# does we have a command for empty string?
		system($external_command_hotist_empty);
	      }
	    }
  return weechat::WEECHAT_RC_OK;
}

sub create_output{
	  $res = $hotlist_format;							# save hotlist format
	  $res2 = $external_command_hotlist;						# save external_hotlist format
	    if ($priority == 3){							# priority is highlight
	      if (grep (/\%H/,$hotlist_format)){					# check with original!!!
		$res =~ s/%H/$highlight_char/;
	      }
	    }else{									# priority != 3
	      $res =~ s/\%H//;								# remove %H
	    }

	    if (grep (/\%S/,$hotlist_format)){						# does %S is in sting? (check with original!!!)
	      $res =~ s/%S/$short_name/;						# add short_name
	    }

	    if (grep (/\%N/,$hotlist_format)){
	      $res =~ s/%N/$buffer_number/;						# add buffer_number
	    }

	    if ($res ne $hotlist_format){						# did $res changed?
	      push (@table, $res);							# add it to @table
	    }

	    $res=qq(\Q$res);								# kill metachars first
	    if (grep /^$res$/, @table){							# does we have added $res to @table?
	      my $export = join(" ", sort(@table));
	      if (grep (/\%X/,$external_command_hotlist)){				# check for %X option.
		$res2 =~ s/%X/$export/;
	    	system($res2);
	      }
	    }
}

sub _extern{
  my ($data) = ($_[0]);
	system($data) unless($data eq "");
  return weechat::WEECHAT_RC_OK;
}

sub init{
# set value of script (for example starting script the first time)
weechat::config_set_plugin('external_command_hotlist', $external_command_hotlist)
	if (weechat::config_get_plugin('external_command_hotlist') eq "");

weechat::config_set_plugin('external_command_hotlist_empty', $external_command_hotist_empty)
	if (weechat::config_get_plugin('external_command_hotlist_empty') eq "");

weechat::config_set_plugin('highlight_char', $highlight_char)
	if (weechat::config_get_plugin('highlight_char') eq "");

weechat::config_set_plugin('lowest_priority', $lowest_priority)
	if (weechat::config_get_plugin('lowest_priority') eq "");

weechat::config_set_plugin('hotlist_format', $hotlist_format)
	if (weechat::config_get_plugin('hotlist_format') eq "");
}
