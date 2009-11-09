#
# Copyright (c) 2009 by jnbek <jnbek@yahoo.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
# Changelog:
#  0.1: first version
#  0.2: Added the player controls.
#  0.5: Major changes, made the rb accept args, added lart feature, made
#  volume unmute the player if muted upon volume changes.
# TODO: Check if Rhythmbox is actually loaded or not..

my $version  = '0.5';
my @greeting = (
    "With extreme prejuduce, I choose to hear:",
    "Without a second thought, I\'m listening to:",
    "Rhythmbox is being forced at gunpoint to play:",
    "Just for Kicks and Giggles, I\'m jamming to:",
    "For some reason known only to God, I\'m playing:",
    "Guess What!!!, I\'m headbanging to:",
    "Hmmm, I seem to be listening to:",
    "You know what?? I'll just listen to:",
    "Some d00d decided to make Rhythmbox play:",
    "Sam Fisher snuck into my house and hacked Rhythmbox into playing:",
    "If you know what\'s good for ya, you\'ll also listen to:",
    "Why are you looking at me like that, it\'s just:",
    "....And then there was this time at band camp, ...and ...and, we were listening to:",
    "Yea, that\'s right, I\'m listening to:",
    "MMmmMMmmMmmmMmmmm, Chocolate.... OOooo and:",
    "Hey some dude wanted me to tell you to listen to:",
    "Rhythmbox decided to thrash out to:",
    "Yea so what if my mama dresses me funny, at least I\'m listening to:",
    "Tommy Vercetti jacked my car and all I have left is:",
    "Carl Johnson told me that I better listen to:",
    "I visited Carlsbad Caverns and all I got was:",
    "Look !!! Up in the sky, it\'s a bird, it\'s a plane, it\'s:",
    "Vinnie and Guido said they\'d break my legs if I didn\'t play:",
    "Suprise !!! You're Fred, Guess What... Barney\'s Dead, Huh?? Oh Wait:",
    "Only cool people are allowed to listen to:",
    "Vic Vance beat up his brother Lance, just so I could devastate you all with:",
    "Tony Cipriani convinced me it was in my best interest to listen to:",
    "Real men don't eat quiche, but they sure as heck listen to:",
    "Music to destroy all mankind to, it\'s:",
    "You know you\'re cool when your theme song becomes: ",
    "Run Away, RUN AWAY!!! It\'s..:",
);

my $help         = q{
        The following commands are available:
            rb:                          Displays current song in the current channel
            rb lart   | rb-lart:         Displays current song in the current channel with a random flavor.
            rb toggle | rb-toggle:       Toggles Play/Pause State
            rb next   | rb-next:         Skip to Next Track
            rb prev   | rb-prev:         Skip to the Pervious Played Track
            rb up     | rb-up:           Raise The Player Volume
            rb down   | rb-down:         Lower The Player Volume
            rb mute   | rb-mute:         Mute The Player
            rb unmute | rb-unmute:       Unmute The Player
};
my $description  = "Rhythmbox-Weechat: General Purpose Notification and Control Tool.";
my $cmd_args     = "[lart | toggle | next | prev | up | down | mute | unmute]";
my $status       = "loaded";

# See <rhythmbox_src_dir>/remote/dbus/rb-client.c in the parse_pattern
# function for a complete list of available properties.
my $album        = '%at';
my $year         = '%ay';
my $disc_number  = '%an';
my $genre        = '%ag';
my $title        = '%tt';
my $artist       = '%ta';
my $track_number = '%tN';
my $duration     = '%td';
my $elapsed      = '%te';
my $bitrate      = '%tb';

my $format = "$title by $artist on $album (Track: $track_number)($elapsed/$duration)($genre)($bitrate bps)";
weechat::register( "rhythmbox", "jnbek", $version, "GPL", $description, "", "" );
weechat::hook_command( "rb", $description, $cmd_args, $help, "", "rb", "" );
weechat::hook_command( "rb-lart", "Display Track Info with Flair", "", "", "", "rb_lart", "" );
weechat::hook_command( "rb-toggle", "Toggle Play/Pause State", "", "", "", "rb_toggle", "" );
weechat::hook_command( "rb-next", "Play next track", "", "", "", "rb_next", "" );
weechat::hook_command( "rb-prev", "Play previous track", "", "", "", "rb_prev", "" );
weechat::hook_command( "rb-up", "Raise the player volume", "", "", "", "rb_up", "" );
weechat::hook_command( "rb-down", "Lower the player volume", "", "", "", "rb_down", "" );
weechat::hook_command( "rb-mute", "Mute the player volume", "", "", "", "rb_mute", "" );
weechat::hook_command( "rb-unmute", "Unmute the player", "", "", "", "rb_unmute", "" );

sub rb {
    my ( $self, $buffer, $args ) = @_;
    if (length($args) == 0) {
        if ( $status eq "paused" ) {
            weechat::command( $buffer, "Rhythmbox is currently paused. type /rb toggle to continue" );
        }
        else {
            chomp( my $cs = (`rhythmbox-client --print-playing-format "$format"`));    #Dbl Quotes required
            weechat::command($buffer, "/say Now Playing: $cs");
        }
    }
    else {
        my $method = "rb_$args";
        &$method;
    }
    return weechat::WEECHAT_RC_OK;
}

sub rb_lart {
    my ( $self, $buffer, $args ) = @_;
    if ( $status eq "paused" ) {
        weechat::command( $buffer, "Rhythmbox is currently paused. type /rb toggle to continue" );
    }
    else {
        my $index   = rand @greeting;
        my $playing_string = $greeting[$index];
        chomp( my $cs = (`rhythmbox-client --print-playing-format "$format"`));    #Dbl Quotes required
        weechat::command($buffer, "/say $playing_string $cs");
    }
    return weechat::WEECHAT_RC_OK;
}

sub rb_toggle {
    my ( $self, $buffer, $args ) = @_;
    if ( $status ne "paused" ) {
        chomp( my $pp = (`rhythmbox-client --pause`));
        $status = "paused";
        weechat::print( $buffer, "Rhythmbox has paused. type /rb-toggle to continue" );
    }
    else {
        chomp( my $pp = (`rhythmbox-client --play`));
        $status = "playing";
        chomp( my $cs = (`rhythmbox-client --print-playing-format "$format"`));    #Dbl Quotes required
        weechat::print( $buffer, "Now Playing: $cs" );
    }
    return weechat::WEECHAT_RC_OK;

}

sub rb_next {
    my ( $self, $buffer, $args ) = @_;
    chomp( my $next = (`rhythmbox-client --next`));
    chomp( my $cs   = (`rhythmbox-client --print-playing-format "$format"`));        #Dbl Quotes required
    weechat::print( $buffer, "Now Playing: $cs" );

    return weechat::WEECHAT_RC_OK;
}

sub rb_prev {
    my ( $self, $buffer, $args ) = @_;
    chomp( my $prev = (`rhythmbox-client --previous`));
    chomp( my $cs   = (`rhythmbox-client --print-playing-format "$format"`));        #Dbl Quotes required
    weechat::print( $buffer, "Now Playing: $cs" );

    return weechat::WEECHAT_RC_OK;
}

sub rb_up {
    my ( $self, $buffer, $args ) = @_;
    if($status eq "muted") {
        chomp (my $unmute = (`rhythmbox-client --unmute`));
        $status = "unmuted";
    }
    chomp( my $up  = (`rhythmbox-client --volume-up`));
    chomp( my $vol = (`rhythmbox-client --print-volume`));
    weechat::print( $buffer, $vol );

    return weechat::WEECHAT_RC_OK;
}

sub rb_down {
    my ( $self, $buffer, $args ) = @_;
    if($status eq "muted") {
        chomp (my $unmute = (`rhythmbox-client --unmute`));
        $status = "unmuted";
    }
    chomp( my $down = (`rhythmbox-client --volume-down`));
    chomp( my $vol  = (`rhythmbox-client --print-volume`));
    weechat::print( $buffer, $vol );

    return weechat::WEECHAT_RC_OK;
}

sub rb_mute {
    my ( $self, $buffer, $args ) = @_;
    chomp( my $mute = (`rhythmbox-client --mute`) );
    chomp( my $vol  = (`rhythmbox-client --print-volume`));
    weechat::print( $buffer, $vol );
    $status = "muted";
    return weechat::WEECHAT_RC_OK;
}

sub rb_unmute {
    my ( $self, $buffer, $args ) = @_;
    chomp( my $unmute = (`rhythmbox-client --unmute`));
    chomp( my $vol    = (`rhythmbox-client --print-volume`));
    $status = "unmuted";
    weechat::print( $buffer, $vol );

    return weechat::WEECHAT_RC_OK;
}
