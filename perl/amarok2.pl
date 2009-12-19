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
# v0.4	: ssh support added
#	: some options added
#	: internal changes
# v0.3	: added option "channel" and made internal changes
# v0.2	: auto completion is now possible
# v0.1	: first release
#
# This script needs Amarok2 and KDE4 (qdbus)
# qdbus is part of libqt4-dbus
#
# /set plugins.var.perl.amarok2.ssh_status
# /set plugins.var.perl.amarok2.ssh_host
# /set plugins.var.perl.amarok2.ssh_port
# /set plugins.var.perl.amarok2.ssh_user
# /set plugins.var.perl.amarok2.color_artist
# /set plugins.var.perl.amarok2.color_title
# /set plugins.var.perl.amarok2.color_album

use strict;
# since KDE4 dcop doesn't work anymore. We have to use qdbus or dbus-send instead
my $cmd = "qdbus";
#my $cmd = "dbus-send --type=method_call --dest=";
my $amarokcheck = qq(ps -e | grep "amarok");
my $version = "0.4";
my $description = "Amarok 2 control and now playing script.";
my $program_name = "amarok2";
my @array = "";
my $anzahl_array = "";
my $buffer = "";
my $title_name = "";
my %ssh = (status => "enabled", host => "localhost", port => "22", user => "user");

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
	"album|artist|title|all|play|stop|next|prev|channel", "checkargs", "");
init();
return weechat::WEECHAT_RC_OK;

my $amarok_result = "";
## my routine to figure out which argument the user selected
sub checkargs{
  my ($buffer, $args) = ($_[1], $_[2]);				# get argument 
  $args = lc($args);						# switch argument to lower-case

    get_user_settings();

  if (check_amarok() eq 0){					# check out if qdbus and Amarok2 exists.
      @array=split(/ /,$args);
      $anzahl_array=@array;
      return weechat::WEECHAT_RC_OK if ($anzahl_array == 0);	# no arguments are given

    my @paramlist = ("album", "artist", "title");
    if (grep(m/$array[0]/, @paramlist)){
      amarok_get_info($array[0]);				# call subroutine with selected argument
      print_in_channel($amarok_result);
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
    my $artist = amarok_get_info("artist");
    my $album = amarok_get_info("album");
    my $title = amarok_get_info("title");
    my $print_string = "$title from $album by $artist";
    $print_string = "" if ($title eq "0" and $album eq "0" and $artist eq "0");
  print_in_channel($print_string);
}

sub print_in_channel{
  my $print_string = ($_[0]);					# get argument
  $print_string = "Amarok2: Not playing",$array[1] = "" if ($print_string eq ""); # string empty? only print in buffer!
  $buffer = weechat::current_buffer;				# get current buffer
	if ($anzahl_array == 2){				# does a second argument exists?
	  if ($array[1] eq "channel"){				# does the second argument is "channel"?
	    weechat::command($buffer, "/me listening to: " . $print_string);	# print in current channel
	  }
	else{
	  weechat::print($buffer,$print_string);		# print in current buffer only
	}
	 }
	else{
	  weechat::print($buffer,$print_string);		# print in current buffer only
	}
}
my $color = "";
# routines to control Amarok
sub amarok_get_info{
  my $arg = ($_[0]);
    $amarok_result = "";
	if ($ssh{status} eq "enabled"){
	  my $cmd2 = sprintf("ssh -p %d %s@%s %s %s %s:",$ssh{port},$ssh{user},$ssh{host},$cmd, $amarok_remote, $arg);	# make it ssh
	  $amarok_result = `$cmd2`;
	}else{
         $amarok_result = `$cmd  $amarok_remote $arg":"`;
	}
      return weechat::WEECHAT_RC_OK if ($amarok_result eq "");
      if ($amarok_result eq ($arg . ": \n")){			# check result, if its empty
	$amarok_result = ($arg . ": unknown");			# than print "unknown"
      }
    $amarok_result =~ s/\n//g;					# remove line-feeds

# remove prefix
    if ($arg eq "artist"){
      $amarok_result =~ s/artist: //g;
      $color = get_color("artist");
      $amarok_result = $color . $amarok_result . weechat::color("reset");
    } 
    if ($arg eq "title"){
      $amarok_result =~ s/title: //g;
      $color = get_color("title");
      $amarok_result = $color . $amarok_result . weechat::color("reset");
    } 
    if ($arg eq "album"){
      $amarok_result =~ s/album: //g;
      $color = get_color("album");
      $amarok_result = $color . $amarok_result . weechat::color("reset");
    } 

return $amarok_result;
}
sub amarok_pannel{
  my $arg = ($_[0]);
   if ($ssh{status} eq "enabled"){
      my $cmd2 = sprintf("ssh -p %d %s@%s %s %s%s",$ssh{port},$ssh{user},$ssh{host},$cmd, $amarok_com, $arg);	# make it ssh
      system("$cmd2 2>/dev/null 1>&2 &");
   }else{
    my $amarok_rc = (`$cmd $amarok_com"$arg"`);		# remote command + arg (Play/Pause/Stop/Prev/Next)
   }
}

### check for qdbus and amarok...
sub check_amarok{
$buffer = weechat::current_buffer;
if (!`$cmd`){							# check for qdbus
	weechat::print($buffer,"Could not find $cmd. Make sure $cmd is in your PATH or edit $cmd-variable in the script ($cmd is part of libqt4-dbus)");
	return weechat::WEECHAT_RC_ERROR;
}
return weechat::WEECHAT_RC_OK if ($ssh{status} eq "enabled");
if (!`$amarokcheck`){						# is Amarok running?
	weechat::print($buffer,"Amarok2 is not running. Please start Amarok2");
	return weechat::WEECHAT_RC_ERROR;
}
return weechat::WEECHAT_RC_OK;
}
sub get_color{
  my $arg = ($_[0]);
        $color = weechat::color(weechat::config_get_plugin("color_$arg"));
return $color;
}
sub init{
  if (weechat::config_get_plugin("ssh_status") eq ""){
    weechat::config_set_plugin("ssh_status", $ssh{status});
  }
  if (weechat::config_get_plugin("ssh_host") eq ""){
    weechat::config_set_plugin("ssh_host", $ssh{host});
  }
  if (weechat::config_get_plugin("ssh_port") eq ""){
    weechat::config_set_plugin("ssh_port", $ssh{port});
  }
  if (weechat::config_get_plugin("ssh_user") eq ""){
    weechat::config_set_plugin("ssh_user", $ssh{user});
  }
  if (weechat::config_get_plugin("color_title") eq ""){
    weechat::config_set_plugin("color_title", "white");
  }
  if (weechat::config_get_plugin("color_album") eq ""){
    weechat::config_set_plugin("color_album", "white");
  }
  if (weechat::config_get_plugin("color_artist") eq ""){
    weechat::config_set_plugin("color_artist", "white");
  }

}
sub get_user_settings{
  $ssh{status} = weechat::config_get_plugin("ssh_status");
  $ssh{host} = weechat::config_get_plugin("ssh_host");
  $ssh{user} = weechat::config_get_plugin("ssh_user");
  $ssh{port} = weechat::config_get_plugin("ssh_port");
}
