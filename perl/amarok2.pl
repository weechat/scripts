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
# v0.1: first release.
#
# This script needs Amarok2 and KDE4 (qdbus)
#

use strict;
my $version = "0.1";
my $description = "remote control for Amarok2";
my $program_name = "amarok2";

# since KDE4 dcop doesn't work anymore. We have to use qdbus instead
my $qdbusbin = "qdbus";
my $amarokcheck = qq(qdbus | grep "amarok");

# first function called by a WeeChat-script
weechat::register($program_name, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

# commands used by amarok2. Type: /help amarok2
weechat::hook_command($program_name, $description,
	"[album] [artist] [title] [all] [stop] [play] [next] [prev]", 
	"album  : display album\n".
	"artist : display artist\n".
	"title  : display current playing title\n".
	"all    : display artist, album and title\n".
	"stop   : stop current playing song\n".
	"play   : Play/Pause current song\n".
	"next   : play next song\n".
	"prev   : play previous song\n",
	"", "checkargs", "");
return weechat::WEECHAT_RC_OK;					# Return_Code OK

### my subroutines
sub checkargs{							# check out which command to use.
  my ($buffer, $args) = ($_[1], $_[2]);				# get argument 
  $args = lc($args);						# switch argument to lower-case
  if (check_amarok() eq 0){					# check out if qdbus and Amarok2 exists.

    if ($args eq "album"){
      cmd_album()
    }
    if ($args eq "artist"){
      cmd_artist()
    }
    if ($args eq "title"){
      cmd_title()
    }
    if ($args eq "all"){
      cmd_all()
    }
    if ($args eq "stop"){
      cmd_stopsong()
    }
    if ($args eq "play"){
      cmd_playsong()
    }
    if ($args eq "next"){
      cmd_nextsong()
    }
    if ($args eq "prev"){
      cmd_prevsong()
    }
  }
}

sub cmd_album{
    my $buffer = weechat::current_buffer;
    my $album_name = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.GetMetadata | grep "album:"`;
    if ($album_name ne ""){
      weechat::print($buffer, $album_name);
  }
}

sub cmd_artist{
    my $buffer = weechat::current_buffer;
    my $artist_name = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.GetMetadata | grep "artist:"`;
    if ($artist_name ne ""){
      weechat::print($buffer,$artist_name);
    }
}

sub cmd_title{
    my $buffer = weechat::current_buffer;
    my $title_name = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.GetMetadata | grep "title:"`;
    if ($title_name ne ""){
      weechat::print($buffer,$title_name);
    }
}

sub cmd_all{
    cmd_artist();
    cmd_album();
    cmd_title();
}

sub cmd_stopsong{
  my $stop_rc = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.Stop`;
}

sub cmd_playsong{
  my $play_rc = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.PlayPause`;
}

sub cmd_nextsong{
  my $next_rc = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.Next`;
}

sub cmd_prevsong{
  my $prev_rc = `qdbus org.kde.amarok /Player org.freedesktop.MediaPlayer.Prev`;
return weechat::WEECHAT_RC_OK;					# Return_Code OK
}

### check for qdbus and amarok...
sub check_amarok{
if (!`$qdbusbin`){						# check for qdbus
	weechat::print("","Could not find qdbus. Make sure qdbus is in your PATH or edit qdbusbin in the script");
	return weechat::WEECHAT_RC_ERROR;			# Return_Code ERROR
}
if (!`$amarokcheck`){						# is Amarok running?
	weechat::print("","Please start Amarok2 first...");
	return weechat::WEECHAT_RC_ERROR;			# Return_Code ERROR
}
return weechat::WEECHAT_RC_OK;					# Return_Code OK
}
