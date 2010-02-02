#   Copyright [2010] [Sebastian Köhler]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#===============================================================================
#
#         FILE:  weerock.pl
#
#  DESCRIPTION:  WeeChat Pluging to show others youre good taste in music
#                
#                Supported Players:
#                   mpc
#                   ncmpcpp
#                   moc
#                   rhytmbox(requires Net::DBus)
#                   audacious
#                   exaile
#                   pytone
#                   quod libet
#
#      OPTIONS:  ---
# REQUIREMENTS:  weechat 3.1,one of the above players
#         BUGS:  ---
#        NOTES:  ---
#       AUTHOR:  Sebastian Köhler (sk), sebkoehler@whoami.org.uk
#      WEBSITE:  http://hg.whoami.org.uk/weerock
#      VERSION:  0.2
#      CREATED:  31.01.2010 04:17:41
#     REVISION:  ---
#===============================================================================

use strict;

my $description = "Rock this chat!";
my $helptext = "Use this command to show your current song in the channel\n\n";

weechat::register('weerock','Sebstian Köhler','0.2','Apache 2.0',$description,'','');


weechat::hook_command('mpc',$description,
                      "",
                      "$helptext".
                      "SETTINGS\n".
                      "    /set plugins.var.perl.weerock.mpc_host PASSWORD\@IP\n".
                      "        Default: localhost\n".
                      "    /set plugins.var.perl.weerock.mpc_port PORT\n".
                      "        Default: 6600\n",
                      "",
                      "mpc",
                      "");

weechat::hook_command('ncmpcpp',$description,
                      "",
                      "$helptext".
                      "SETTINGS".
                      "    /set plugins.var.perl.weerock.ncmpcpp_host PASSWORD\@IP\n".
                      "        Default: localhost\n".
                      "    /set plugins.var.perl.weerock.ncmpcpp_port PORT\n".
                      "        Default: 6600\n",
                      "",
                      "ncmpcpp",
                      "");

weechat::hook_command('moc',$description,
                      "",
                      "$helptext",
                      "",
                      "moc",
                      "");

weechat::hook_command('rhythmbox',$description,
                      "",
                      "$helptext",
                      "",
                      "rhythmbox",
                      "");

weechat::hook_command('audacious',$description,
                      "",
                      "$helptext",
                      "",
                      "audacious",
                      "");

weechat::hook_command('weerock',$description,
                      "",
                      "Show Help for weeRock",
                      "",
                      "weerock",
                      "");

weechat::hook_command('exaile',$description,
                      "",
                      "$helptext",
                      "",
                      "exaile",
                      "");

weechat::hook_command('pytone',$description,
                      "",
                      "$helptext",
                      "",
                      "pytone",
                      "");

weechat::hook_command('quodlibet',$description,
                      "",
                      "$helptext",
                      "",
                      "quodlibet",
                      "");

return weechat::WEECHAT_RC_OK;

sub quodlibet {
    loadDefaults();
    my $artist = (`quodlibet --print-playing \"<artist>\"`);
    my $album  = `quodlibet --print-playing \"<album>\"`;
    my $title  = `quodlibet --print-playing \"<title>\"`;
    
    echoToChannel(buildMessage($artist,$album,$title,"",""));
}

sub pytone {
    loadDefaults();
    my $string = `pytonectl getplayerinfo`;
    if($string =~ /(.*) - (.*) \( (\d?\d:\d\d)\/ (\d?\d:\d\d)\)/) {
        echoToChannel(buildMessage($1,"",$2,$3,$4));     
    }
}

sub weerock {
    my $bold   = weechat::color("bold");
    my $unbold = weechat::color("-bold");
    
    my $help = "%bold%NAME%unbold%\n".
               "    weeRock - $description\n".
               "%bold%COMMANDS%unbold%\n".
               "    /mpc\n".
               "    /moc\n".
               "    /ncmpcpp\n".
               "    /rhythmbox\n\n".
               "    For more information do:\n".
               "    /help command\n\n".
               "%bold%GLOBAL SETTINGS%unbold%\n".
               "    /set plugins.var.perl.weerock.format STRING\n".
               "        STRING will be send to the Channel\n".
               "        Following Variables are available:\n".
               "            %artist% - Artist\n".
               "            %album%  - Album\n".
               "            %title%  - Title\n".
               "            %ct%     - Current Time\n".
               "            %tt%     - Total Time\n".
               "        Default: \"%artist%(%album%) - %title% [%ct%/%tt%]\"\n".
               "    /set plugins.var.perl.weerock.left_string STRING\n".
               "        STRING is printed before the song information\n".
               "        Default: \"/me np\"\n".
               "    /set plugins.var.perl.weerock.right_string STRING\n".
               "        STRING is printed after the song information\n".
               "        Default: \"\"";
    
    $help =~ s/%bold%/$bold/g;
    $help =~ s/%unbold%/$unbold/g;
    echoToBuffer($help);
}

sub audacious {
    loadDefaults();
    my $artist = `audtool2 current-song-tuple-data artist`;
    my $album  = `audtool2 current-song-tuple-data album`;
    my $title  = `audtool2 current-song-tuple-data title`;
    my $ct     = `audtool2 current-song-output-length-seconds`;
    my $tt     = `audtool2 current-song-length-seconds`;

    if($ct) {
       $ct = secToMin($ct); 
    }
    if($tt) {
        $tt = secToMin($tt);
    }
    
    echoToChannel(buildMessage($artist,$album,$title,$ct,$tt));
}

sub exaile {
    loadDefaults();
    if(`pgrep exaile`) {
        my $artist = `exaile --get-artist`;
        my $album  = `exaile --get-album`;
        my $title  = `exaile --get-title`;
        my $ct     = `exaile --current-position`;
        my $tt     = secToMin(int(`exaile --get-length`));

        echoToChannel(buildMessage($artist,$album,$title,$ct,$tt));
    }
}

sub rhythmbox {
    loadDefaults();
    require Net::DBus;
    if(`pgrep rhythmbox`) { #check if rbox is running
        my $bus         = Net::DBus->session;
        my $rboxservice = $bus->get_service("org.gnome.Rhythmbox");
        my $rboxplayer  = $rboxservice->get_object("/org/gnome/Rhythmbox/Player");
        my $rboxshell   = $rboxservice->get_object("/org/gnome/Rhythmbox/Shell");
        
        my $artist = "";
        my $album  = "";
        my $title  = "";
        my $ct     = "";
        my $tt     = "";

        if($rboxplayer->getPlaying()) {
            my $song = $rboxshell->getSongProperties($rboxplayer->getPlayingUri());
            my $ct = secToMin($rboxplayer->getElapsed());
            if(exists $song->{'artist'}) {
                $artist = $song->{'artist'};
            }
            if(exists $song->{'title'}) {
                $title = $song->{'title'};
            }
            if(exists $song->{'album'}) {
                $album = $song->{'album'};
            }
            if(exists $song->{'duration'}) {
                $tt = secToMin($song->{'duration'});
            }
            
            echoToChannel(buildMessage($artist,$album,$title,$ct,$tt));
        }
    } 
}


sub moc {
    loadDefaults();
    my $artist = `mocp -Q %artist`;
    my $album  = `mocp -Q %album`;
    my $title  = `mocp -Q %title`;
    my $ct     = `mocp -Q %ct`;
    my $tt     = `mocp -Q %tt`;
    
    echoToChannel(buildMessage($artist,$album,$title,$ct,$tt));
}

sub ncmpcpp {
    loadDefaults();
    my $host = weechat::config_get_plugin("ncmpcpp_host");
    my $port = weechat::config_get_plugin("ncmpcpp_port");
    my $cmd  = "ncmpcpp -h $host -p $port --now-playing";

    my $artist = `$cmd %a`;
    my $album  = `$cmd %b`;
    my $title  = `$cmd %t`;
    my $ct     = "";
    my $tt     = "";

    echoToChannel(buildMessage($artist,$album,$title,$ct,$tt));
}

sub mpc {
    loadDefaults();
        
    my $host    = weechat::config_get_plugin("mpc_host");
    my $port    = weechat::config_get_plugin("mpc_port");
    my $string  = `mpc status -h $host -p $port -f \"%artist% #| %album% #| %title%\"`;
    
    if( $string =~ /(.*) \| (.*) \| (.*)\s\[.*(\d?\d?\d:\d\d)\/(\d?\d?\d:\d\d)/) {
        echoToChannel(buildMessage($1,$2,$3,$4,$5));
    }
}

#
##
### Basic functions
##
#
sub echoToChannel {
    my ($string) = @_;
    my $buffer = weechat::current_buffer;
    my $left_string = weechat::config_get_plugin("left_string");
    my $right_string = weechat::config_get_plugin("right_string" eq "");
    weechat::command($buffer, "$left_string " . $string . " $right_string");
}

sub echoToBuffer {
    my ($string) = @_;
    my $buffer = weechat::current_buffer;
    weechat::print($buffer,$string);
}

sub secToMin {
    my ($sec) = @_;
    return int($sec/60).":".sprintf("%02d",$sec%60);
}

sub buildMessage {
    my ($artist, $album, $title, $ct, $tt) = @_;
    my $message = weechat::config_get_plugin("format");

    $message =~ s/%artist%/$artist/g;
    $message =~ s/%album%/$album/g;
    $message =~ s/%title%/$title/g;
    $message =~ s/%ct%/$ct/g;
    $message =~ s/%tt%/$tt/g;
    $message =~ s/\n//g;

    return $message;
}


sub loadDefaults() {
    if(weechat::config_get_plugin("mpc_host") eq "") {
        weechat::config_set_plugin("mpc_host", "localhost");
    }
    if(weechat::config_get_plugin("mpc_port") eq ""){
        weechat::config_set_plugin("mpc_port", 6600);
    }
    if(weechat::config_get_plugin("ncmpcpp_host") eq ""){
        weechat::config_set_plugin("ncmpcpp_host", "localhost");
    }
    if(weechat::config_get_plugin("ncmpcpp_port") eq ""){
        weechat::config_set_plugin("ncmpcpp_port", "6600"); 
    }
    if(weechat::config_get_plugin("left_string" eq "")) {
        weechat::config_set_plugin("left_string", "/me np");
    }
    if(weechat::config_get_plugin("right_string" eq "")) {
        weechat::config_set_plugin("right_string", "");
    }
    if(weechat::config_get_plugin("format") eq "") {
        weechat::config_set_plugin("format", "%artist%(%album%) - %title% [%ct%/%tt%]");
    }
}

