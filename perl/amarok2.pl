# Copyright (c) 2010-2012 by Nils Görs <weechatter@arcor.de>
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
# v0.7  : display bug removed (done by linopolus)
# v0.6  : added text_output option (%Z = current play time, %M (max play time, %S = sample rate)
# v0.5	: external color code will be used to avoid character missmatch
#	: added text_output option (%T = title, %C = album, %A = artist) 
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
#
# TODO add an item-bar

use strict;
# since KDE4 dcop doesn't work anymore. We have to use qdbus or dbus-send instead
my $cmd = "qdbus";
#my $cmd = "dbus-send --type=method_call --dest=";
my $amarokcheck = qq(ps -e | grep "amarok");
my $version = "0.7";
my $description = "Amarok 2 control and now playing script with ssh support";
my $program_name = "amarok2";
my @array = "";
my $anzahl_array = "";
my $buffer = "";
my $title_name = "";
my %ssh = (status => "disabled", host => "localhost", port => "22", user => "user");
my %ext_colors = (white => "00", black => "01", darkblue => "02", darkgreen => "03", lightred => "04",
		  darkred => "05", magenta => "06", orange => "07", yellow => "08", lightgreen => "09",
		  cyan => "10", lightcyan => "11", lightblue => "12", lightmagenta => "13", gray => "14",
		  lightgray => "15");
my $ext_color = "";
my $text_output = "listening to: ♬  \%T from \%C by \%A [\%Z of \%M @ \%S kbps] ♬";

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
	"The option 'text_output' uses the following place holder:\n".
	"      '%T' will be replaced with the title name\n".
	"      '%C' will be replaced with the album name\n".
	"      '%A' will be replaced with the artist name\n".
	"      '%Z' will be replaced with current play time\n".
	"      '%M' will be replaced with time of song\n".
	"      '%S' will be replaced with sample rate\n\n".
	"If you want to use the ssh remote control you have to enable the ssh options:\n".
	"       /set plugins.var.perl.amarok2.ssh_status enabled (default: disabled)\n".
	"       /set plugins.var.perl.amarok2.ssh_host <hostname> (default: localhost)\n".
	"       /set plugins.var.perl.amarok2.ssh_user <username> (default: user)\n".
	"       /set plugins.var.perl.amarok2.ssh_port <port> (default: 22)\n\n".
	"Examples:\n".
	"/amarok2 play        => play / pause current song\n".
	"/amarok2 all         => displays artist album and title in current buffer\n".
	"/amarok2 all channel => displays artist album and title in current channel\n\n".
	"This script is very funny to play internet-radio. Most stations sending informations that can be displayed\n",
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

    my @paramlist = ("album", "artist", "title", "time", "mtime", "bitrate");
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
# command "all" used. Create output
sub cmd_all{
    my $artist = amarok_get_info("artist");
    my $album = amarok_get_info("album");
    my $title = amarok_get_info("title");
    my $sample_rate = amarok_get_info("audio-bitrate");
    my $mtime = amarok_get_info("mtime");

     my $time = millisecs_to_time( `$cmd  org.kde.amarok /Player PositionGet` );
     $mtime = millisecs_to_time($mtime);			# max. time

    my $print_string = weechat::config_get_plugin("text_output");
    $print_string = "%T from %C by %A" if ($print_string eq "");
    $print_string =~ s/%A/$artist/;
    $print_string =~ s/%C/$album/;
    $print_string =~ s/%T/$title/;
    $print_string =~ s/%Z/$time/;
    $print_string =~ s/%M/$mtime/;
    $print_string =~ s/%S/$sample_rate/;

    $print_string = "" if ($title eq "0" and $album eq "0" and $artist eq "0");

  print_in_channel($print_string);
}

sub print_in_channel{
  my $print_string = ($_[0]);					# get argument
  $print_string = "Amarok2: Not playing",$array[1] = "" if ($print_string eq ""); # string empty? only print in buffer!
  $buffer = weechat::current_buffer;				# get current buffer
	if ($anzahl_array == 2){				# does a second argument exists?
	  if ($array[1] eq "channel"){				# does the second argument is "channel"?
	    weechat::command($buffer, "/me " . $print_string);	# print in current channel
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
# routines to control Amarok. Also via ssh, if enabled
sub amarok_get_info{
  my $arg = ($_[0]);
    $amarok_result = "";
	if ($ssh{status} eq "enabled"){
	  my $cmd2 = sprintf("ssh -p %d %s@%s %s %s %s:",$ssh{port},$ssh{user},$ssh{host},$cmd, $amarok_remote, $arg);	# make it ssh
	  $amarok_result = `$cmd2`;
	}else{
         $amarok_result = `$cmd  $amarok_remote "\"^"$arg":\""`;
	}
      return weechat::WEECHAT_RC_OK if ($amarok_result eq "");
      if ($amarok_result eq ($arg . ": \n")){			# check result, if its empty
	$amarok_result = ($arg . ": unknown");			# than print "unknown"
      }
    $amarok_result =~ s/\n//g;					# remove line-feeds

# remove prefix
if ($anzahl_array == 2){				# does a second argument exists?
  if ($array[1] eq "channel"){				# does the second argument is "channel"?
    if ($arg eq "artist"){
      $amarok_result =~ s/artist: //g;
      $color = get_ext_color("artist");
      $amarok_result = "\cC" . $color . $amarok_result . "\cC";
    }
    if ($arg eq "title"){
      $amarok_result =~ s/title: //g;
      $color = get_ext_color("title");
      $amarok_result = "\cC" . $color . $amarok_result . "\cC";
    }
    if ($arg eq "album"){
      $amarok_result =~ s/album: //g;
      $color = get_ext_color("album");
      $amarok_result = "\cC" . $color . $amarok_result . "\cC";
    }
  }
}else{
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
}
    if ($arg eq "audio-bitrate"){
      $amarok_result =~ s/audio-bitrate: //g;
    }
    if ($arg eq "mtime"){
      $amarok_result =~ s/mtime: //g;
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

# get colour name and transform it for external use.
sub get_ext_color{
  my $arg = ($_[0]);
  $ext_color = "";
  $ext_color = $ext_colors{weechat::config_get_plugin("color_$arg")};		# get colour-code from color_name
    if (not defined $ext_color){
      $ext_color = $ext_colors{white};						# use standard colour if something went wrong
    }
return $ext_color;
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
  if (weechat::config_get_plugin("text_output") eq ""){
    weechat::config_set_plugin("text_output", $text_output);
  }
}
sub get_user_settings{
  $ssh{status} = weechat::config_get_plugin("ssh_status");
  $ssh{host} = weechat::config_get_plugin("ssh_host");
  $ssh{user} = weechat::config_get_plugin("ssh_user");
  $ssh{port} = weechat::config_get_plugin("ssh_port");
}

sub millisecs_to_time{
  my $sec = ($_[0]);

  my $s = int $sec / 1000;
  $sec = sprintf("%0.2f", $s);
  my $m = int $sec / 60;
  $s = $sec - ($m * 60);
  my $h = int $m / 60;
  $m = $m - ($h * 60);

  $h="0$h" if (length($h) == 1);
  $m="0$m" if (length($m) == 1);
  $s="0$s" if (length($s) == 1);
  my $timestring = "";
  if ($h eq "00"){
    $timestring = sprintf("%02d:%02d", $m, $s);
  }else {
    $timestring = sprintf("%03d:%02d:%02d", $h, $m, $s);
  }
return $timestring;
}
