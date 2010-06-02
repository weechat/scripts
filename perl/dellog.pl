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
# v0.2: /mute function added (needs weechat v0.3.2 and higher!)
# v0.1: first release
#
# This script DELETES the log file for the current buffer
#
# You are using this script at your risk.
#

use strict;
my $version = "0.2";
my $description = "delete log file";
my $program_name = "dellog";

# first function called by a WeeChat-script
weechat::register($program_name, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

weechat::hook_command($program_name, $description,
	"[delete]", 
	"delete: delete log file from current buffer\n",
	"delete","getargs", "");
return weechat::WEECHAT_RC_OK;


sub getargs{
  my ($buffer, $args) = ($_[1], $_[2]);				# get argument 
  $args = lc($args);						# switch argument to lower-case
    if ($args eq "delete"){
	get_logfile_name();
    }
return weechat::WEECHAT_RC_OK;
}


sub get_logfile_name{						# get name of current name of log-file

  my $buffer = weechat::current_buffer;				# get current buffer name
    my $linfolist = weechat::infolist_get("logger_buffer", "", "");

    while(weechat::infolist_next($linfolist)){
      my $bpointer = weechat::infolist_pointer($linfolist, "buffer");
        if($bpointer eq $buffer){
	  my $logfilename = weechat::infolist_string($linfolist, "log_filename");
	  my $log_enabled = weechat::infolist_integer($linfolist, "log_enabled");
	  my $log_level = weechat::infolist_integer($linfolist, "log_level");
	  weechat::command($buffer, "/mute logger disable");	# disable file logging
	  unlink($logfilename);					# DELETE Log-file
	  weechat::command($buffer,"/mute logger set " . $log_level);# start file logging again
	  last;
	}
    }
      weechat::infolist_free($linfolist);
}
