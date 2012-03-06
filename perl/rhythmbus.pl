# Copyright (c) 2012 by R1cochet R1cochet@hushmail.com
# All rights reserved
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
# rhythmbus, version 1.0, for weechat version 0.3.6 or later
# control rhytmbox through qdbus, say current song in channel
# similar to amarok2.pl by nils_2 but for rhythmbox. Thank you nils_2
#
# Requires Rhythmbox and qdbus
#
# Format options:
#   %Al = Album, %Ar = Artist, %Ti = Title, %Tr = Track Number, %L = Length, %B = Bitrate
#   default: "np: "%Ti" from %Al by %Ar"
#
# Color options:
#   Can be any IRC color name listed here: http://www.mirc.net/newbie/colors.php
#   exceptions: lightred = red, grey = gray
#   for Bold text use "*", for Underline text use "_"
#   Example: \"_red\" = underlined red text
#

use strict;
use warnings;

my $SCRIPT_NAME = "rhythmbus";
my $SCRIPT_AUTHOR = "R1cochet";
my $VERSION = "1.0";
my $SCRIPT_LICENSE = "GPL3";
my $SCRIPT_DESC = "Control Rhythmbox through qdbus";

# globals
my $state_command = "qdbus org.mpris.MediaPlayer2.rhythmbox /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.";
my $metadata_command = "qdbus org.mpris.MediaPlayer2.rhythmbox /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Metadata | grep";

my %colors = ('white' => "00", 'black' => "01", 'blue' => "02", 'green' => "03", 'red' => "04", 'brown' => "05",
              'purple' => "06", 'orange' => "07", 'yellow' => "08", 'lightgreen' => "09", 'cyan' => "10",
              'lightcyan' => "11",'lightblue' => "12", 'pink' => "13", 'gray' => "14", 'lightgray' => "15",
);

my %options = ( 'format'        => 'Now Playing: "%Ti" off %Al by %Ar',
                'title'         => '',
                'album'         => '_',
                'artist'        => '',
                'trackNumber'   => '',
                'bitrate'       => '',
                'length'        => '',
);

my %help = ( 'format'               => "Set the format of the text to send to current channel\n    %Al = Album, %Ar = Artist, %Ti = Title, %Tr = Track Number, %L = Length, %B = Bitrate\n    default: \"Now Playing: \"%Ti\" from %Al by %Ar\"",
             'color_description'    => "Can be any IRC color name listed here: http://www.mirc.net/newbie/colors.php\n   exceptions: lightred = red, grey = gray (for Bold text use \"*\", for Underline text use \"_\")\n      Example: \"_red\" = underlined red text",
);

weechat::register($SCRIPT_NAME, $SCRIPT_AUTHOR, $VERSION, $SCRIPT_LICENSE, $SCRIPT_DESC, "", "");

sub init_config {
    foreach my $option (keys %options) {
        if (!weechat::config_is_set_plugin($option)) {
            weechat::config_set_plugin($option, $options{$option});
            if ($option =~ /format/) {
                weechat::config_set_desc_plugin($option, $help{$option});
            }
            else {
                weechat::config_set_desc_plugin($option, $help{'color_description'});
            }
        }
        else {
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}
# load config
init_config();

weechat::hook_config("plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "");

sub toggle_config_by_set {
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".$SCRIPT_NAME."."), length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

# commands used by rhythmbus. Type: /help rhythmbus
weechat::hook_command($SCRIPT_NAME, $SCRIPT_DESC,
    "play|pause|stop|next|prev|np",
    "   play:   Toggle play state\n".
    "  pause:   Toggle pause state\n".
    "   stop:   Toggle stop state\n".
    "   next:   Play next track\n".
    "   prev:   Play previous track\n\n".
    "Examples:\n".
    "  skip to next track:\n".
    "    /rhytmbus next\n".
    "  pause currently playing song:\n".
    "    /rhythmbus pause",
    "play|pause|stop|next|prev|np",
    "command_cb", "");

sub command_cb {
    my ($buffer, @args) = ($_[1], split " ", lc($_[2]) );

    return weechat::WEECHAT_RC_OK if (!rhythmbus_check());      # stop if did not pass check

    if ($args[0] =~ /^play/) {
        my $rhythm_rc = `$state_command"Play"`;
    }
    elsif ($args[0] =~ /^pause/) {
        my $rhythm_rc = `$state_command"PlayPause"`;
    }
    elsif ($args[0] =~ /^stop/) {
        my $rhythm_rc = `$state_command"Stop"`;
    }
    elsif ($args[0] =~ /^next/) {
        my $rhythm_rc = `$state_command"Next"`;
    }
    elsif ($args[0] =~ /^prev/) {
        my $rhythm_rc = `$state_command"Previous"`;
    }
    elsif ($args[0] =~ /^np/) {
        now_playing($buffer);
    }

    return weechat::WEECHAT_RC_OK;
}

sub rhythmbus_check {
    my $buffer = weechat::current_buffer;
    if (!`qdbus`) {							# check for qdbus
    	weechat::print($buffer,"Could not find \"qdbus.\" Make sure \"qdbus\" is installed");
	    return 0;
    }
    if (!`ps -e | grep rhythmbox`) {		# is Rhythmbox running?
	    weechat::print($buffer,"Rhythmbox is not running. Please start Rhythmbox");
	    return 0;
    }
    return 1;
}

sub get_color {
    my $option = shift;
    my $color = $colors{weechat::config_get_plugin("$option")};
    return $color;
}

sub color_metadata {
    my ($meta_data, $meta_name) = @_;
    my $color_name = weechat::config_get_plugin("$meta_name");

    $meta_data = "\c_" . $meta_data . "\c_" if $color_name =~ /\_/;
    $meta_data = "\cB" . $meta_data . "\cB" if $color_name =~ /\*/;

    $color_name =~ s/\_|\!|\*//g;
    my $color = $colors{$color_name};

    $meta_data = "\cC" . $color . "$meta_data" . "\cC" if ($color);

    return $meta_data;
}

sub time_length {
    my $time = shift;
    my $seconds = $time / 1000 / 1000;
    my $minutes = int($seconds / 60);
    $seconds = $seconds - ($minutes * 60);
    my $formatted_time = sprintf "%02d:%02d", $minutes, $seconds;
    return $formatted_time;
}

sub get_metadata {
    my $meta_name = shift;
    my $meta_data = `$metadata_command $meta_name:`;
    $meta_data =~ s/.*:\s|\n//g;

    $meta_data = $meta_data / 1024 . "kbs" if $meta_name eq "Bitrate";
    $meta_data = time_length($meta_data) if $meta_name eq "length";
    
    $meta_data = color_metadata($meta_data, $meta_name);

    return $meta_data;
}

sub now_playing {
    my $buffer = $_;

    my $title = get_metadata("title");
    my $artist = get_metadata("artist");
    my $album = get_metadata("album");
    my $bitrate = get_metadata("Bitrate");
    my $track = get_metadata("trackNumber");
    my $length = get_metadata("length");

    my $now_playing = weechat::config_get_plugin("format");
    $now_playing =~ s/%Ti/$title/g;
    $now_playing =~ s/%Al/$album/g;
    $now_playing =~ s/%Ar/$artist/g;
    $now_playing =~ s/%Tr/$track/g;
    $now_playing =~ s/%B/$bitrate/g;
    $now_playing =~ s/%L/$length/g;

    weechat::command($buffer, "/say $now_playing");

    return;
}
