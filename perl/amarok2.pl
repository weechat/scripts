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
# v0.3: added option "channel" and made internal changes
# v0.2: auto completion is now possible
# v0.1: first release
#
# This script needs Amarok2 and KDE4 (qdbus)
#

use strict;
# since KDE4 dcop doesn't work anymore. We have to use qdbus instead
my $qdbus = "qdbus";
my $amarokcheck = qq($qdbus | grep "amarok");

my $version = "0.3";
my $description = "Amarok 2 control and now playing script.";
my $program_name = "amarok2";
my @array = "";
my $anzahl_array = "";
my $buffer = "";
my $title_name = "";
my $amarok_remote = "org.kde.amarok /Player org.freedesktop.MediaPlayer.GetMetadata | grep";
my $amarok_com = "org.kde.amarok /Player org.freedesktop.MediaPlayer.";

# first function called by a WeeChat-script
weechat::register($program_name, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

# commands used by amarok2. Type: /help amarok2
weechat::hook_command($program_name, $description,
	"[album [<channel>] | artist [<channel>] | title [<channel>] | all [<channel>] | stop | play | next | prev]", 
	"album  : display album\n".
	"artist : display artist\n".
	"title  : display current playing title\n".
	"all    : display artist, album and title\n".
	"stop   : stop current playing song\n".
	"play   : Play/Pause current song\n".
	"next   : play next song\n".
	"prev   : play previous song\n\n".
	"Examples:\n".
	"/amarok2 play        => play / pause current song\n".
	"/amarok2 all         => displays artist album and title in current buffer\n".
	"/amarok2 all channel => displays artist album and title in current channel\n".
	"This script is very funny using with internet-radio. Most stations sending informations\n",
	"album|artist|title|all|play|stop|next|prev", "checkargs", "");
return weechat::WEECHAT_RC_OK;

## my routine to figure out which argument the user selected
sub checkargs{
  my ($buffer, $args) = ($_[1], $_[2]);				# get argument 
  $args = lc($args);						# switch argument to lower-case

  if (check_amarok() eq 0){					# check out if qdbus and Amarok2 exists.
      @array=split(/ /,$args);
      $anzahl_array=@array;
      return weechat::WEECHAT_RC_OK if ($anzahl_array == 0);	# no arguments are given

    my @paramlist = ("album", "artist", "title");
    if (grep(m/$array[0]/, @paramlist)){
      amarok_get_info($array[0])				# call subroutine with selected argument
    }

    if ($array[0] eq "all"){
      cmd_all();
    }
    if ($array[0] eq "play"){
      amarok_pannel("PlayPause");
    }
    if ($array[0] eq "stop"){
      amarok_pannel("Stop");
    }
    if ($array[0] eq "next"){
      amarok_pannel("Next");
    }
    if ($array[0] eq "prev"){
      amarok_pannel("Prev");
    }

  }
return weechat::WEECHAT_RC_OK;
}

sub cmd_all{
    amarok_get_info("artist");
    amarok_get_info("album");
    amarok_get_info("title");
}
sub print_in_channel{
  my ($print_string) = ($_[0]);					# get argument
  $buffer = weechat::current_buffer;				# get current buffer
	if ($anzahl_array == 2){				# does a second argument exists?
	  if ($array[1] eq "channel"){				# does the second argument is "channel"?
	    weechat::command($buffer, $print_string);		# print in current channel
	  }
	else{
	  weechat::print($buffer,$print_string);		# print in current buffer only
	}
	 }
	else{
	  weechat::print($buffer,$print_string);		# print in current buffer only
	}
}
# routines to control Amarok
sub amarok_get_info{
  my ($arg) = ($_[0]);
    my $amarok_result = (`$qdbus $amarok_remote "$arg":`);	# remote command + arg (album, artist or title)
#      return weechat::WEECHAT_RC_OK if ($amarok_result eq "");
      if ($amarok_result eq ($arg . ": \n")){			# check result, if its empty
	$amarok_result = ($arg . ": unknown");			# than print "unknown"
      }
  print_in_channel($amarok_result);
}

sub amarok_pannel{
  my ($arg) = ($_[0]);
    my $amarok_rc = (`$qdbus $amarok_com"$arg"`);		# remote command + arg (Play/Pause/Stop/Prev/Next)
}

### check for qdbus and amarok...
sub check_amarok{
$buffer = weechat::current_buffer;
if (!`$qdbus`){							# check for qdbus
	weechat::print($buffer,"Could not find qdbus. Make sure qdbus is in your PATH or edit qdbus-variable in the script");
	return weechat::WEECHAT_RC_ERROR;
}
if (!`$amarokcheck`){						# is Amarok running?
	weechat::print($buffer,"Amarok2 ist not running...");
	return weechat::WEECHAT_RC_ERROR;
}
return weechat::WEECHAT_RC_OK;
}
