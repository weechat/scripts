#
# Copyright (c) 2009 by Stravy <stravy@gmail.com>
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
use IO::Socket::INET;
use WWW::Curl::Easy;
use URI::Escape;

use strict;
use vars qw( %cmode $strmon_buffer $command_buffer $strmon_help $version $daemon_file $strmon_tag );

$version = "0.5.4";
weechat::register( "strmon", "Stravy", $version, "GPL",
  "Messages monitoring and notifications", "", "" );

%cmode = ( 'silent' => 3,
            'normal' => 0,
            'nosound' => 1,
            'novisual' => 2);

$strmon_tag='strmon_message';

$daemon_file=<<'AFP';
#!/usr/bin/perl
#
# Copyright (c) 2009 by Stravy <stravy@gmail.com>
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
# This is a notify daemon associated with weechat script strmon,
# it uses mplayer (http://www.mplayerhq.hu) for sound notifications
# and notify-send for osd notifications.
#
# It has to be run on the local machine, default port is 9867, but can
# be changed using --localport=xxxx on the command line
#
# Default directory to look for images is $HOME/.config/strmon_daemon/pics
# Default directory to look for sounds is $HOME/.config/strmon_daemon/sounds
# these directories can be manually changed in this script by modifying
# variables $picdir and $sounddir
#
  use strict;

  require Net::Daemon;

  package strmon_daemon;
  use vars qw($VERSION @ISA $picdir $sounddir);
  $VERSION = '0.2';
  @ISA = qw(Net::Daemon); # to inherit from Net::Daemon

  $picdir=$ENV{'HOME'}."/.config/strmon_daemon/pics";
  $sounddir=$ENV{'HOME'}."/.config/strmon_daemon/sounds";

  sub Version ($) { "strmon daemon,$VERSION"; }


  sub new
    {
    my($class, $attr, $args) = @_;
    my($self) = $class->SUPER::new($attr, $args);
    return $self;
    }

  sub Run {
      my($self) = @_;
      my($line, $sock);
      $sock = $self->{'socket'};
      my $pe = $sock->peerhost();
      #print("Name : $pe\n");
      # limit access to 127.X.X.X
      return unless($pe=~/^127\./);
      while (1) {
          if (!defined($line = $sock->getline())) {
              if ($sock->error()) {
                  $self->Error("Client connection error %s",
                               $sock->error());
              }
              $sock->close();
              return;
          }
          $line =~ s/\s+$//; # Remove CRLF
          my($rc);
          my $message=do_the_work($line);
          $rc = printf $sock ("$message\n");
          if (!$rc) {
              $self->Error("Client connection error %s",
                           $sock->error());
              $sock->close();
              return;
          }
      }
  }

  sub do_the_work
    {
    my $ligne=shift @_;
    my ($mod,$pic,$sound,$bgcolor,$fgcolor,$chancolor,$nickcolor,$nchan,$chan,$nick,$ret);
    my $unformated=1;
    if ($ligne=~/^[\s\t]*(\d+)[\s\t]+"(.+)"[\s\t]+"(.+)"[\s\t]+(\S+)[\s\t]+(\S+)[\s\t]+(\S+)[\s\t]+(\S+)[\s\t]+(\d+)[\s\t]+(\S+)[\s\t]+(\S+)[\s\t]*:(.*)$/)
        {
        $unformated=0;
        $mod=$1;
        $pic=$2;
        $sound=$3;
        $bgcolor=$4;
        $fgcolor=$5;
        $chancolor=$6;
        $nickcolor=$7;
        $nchan=$8;
        $chan=$9;
        $nick=$10;
        $ligne=$11;
        }
    if ($unformated)
        {
        $ret=do_unformated($ligne);
        } else
        {
        $ret=do_message($mod,$pic,$sound,$bgcolor,$fgcolor,$chancolor,$nickcolor,$nchan,$chan,$nick,$ligne);
        }
    return $ret;
    }

  sub format_text
    {
    my $line=shift @_;
    my $text="";
    my $ind=0;
    my $tt;
    while ( ($tt=substr $line,$ind,40) && ($ind<200) )
       {
       $text.=$tt."<br>";
       $ind+=40;
       }
    $text=~/(.*)<br>$/;
    $text=$1;
    $text=~s/"/\\"/g;
    return $text;
    }

  sub do_message
    {
    (my $mod, my $pic, my $sound, my $bgcolor, my $fgcolor, my $chancolor, my $nickcolor, my $nchan, my $chan, my $nick, my $text)= @_;
    my $ret;
    # is the nick silent?
    if ($mod==3 )
      {
      $ret="Let's be silent";
      return $ret;
      } else
      {
      $text=format_text($text);

      my $message="";
      $message="<b><font size=3 color='$chancolor'>$chan  </font></b>";
      $message.="<b><font size=3 color='$nickcolor'>$nick </font></b>";
      $pic=$picdir."/".$pic unless ($pic=~/^\//);
      $message.="<img src='$pic'><br>";
      $message.="<font size=3>$text</font>";

      unless ($mod==2)
        {
        my $command="notify-send \"$message\" ";
        system($command);
        }
      unless ($mod==1)
        {
        $sound=$sounddir."/".$sound unless ($sound=~/^\//);
        my $command="mplayer -ao alsa $sound 1 > /dev/null 2> /dev/null &";
        system($command);
        }
      $ret="Notification done";
      return $ret;
      }
    }

  sub do_unformated
    {
    my $ligne = shift @_;
    my $ret;
    if ($ligne=~/^daemon piclist/)
        {
        my @list=`ls $picdir`;
        chop @list;
        $ret=join(",",@list);
        } elsif ($ligne=~/^daemon soundlist/)
        {
        my @list=`ls $sounddir`;
        chop @list;
        $ret=join(",",@list);
        } elsif ($ligne=~/^daemon show "(.*)"/)
        {
        my $pic=$1;
        $pic=$picdir."/".$pic unless ($pic=~/^\//);
        my $command="notify-send \"<img src='$pic'>\" &";
        system($command);
        $ret="done";
        } elsif ($ligne=~/^daemon play "(.*)"/)
        {
        my $sound=$1;
        $sound=$sounddir."/".$sound unless ($sound=~/^\//);
        my $command="mplayer -ao alsa $sound 1 > /dev/null 2> /dev/null &";
        system($command);
        $ret="done";
        } else
        {
        $ret="Unformated message";
        }
    return $ret;
    }


  package main;

  # let's go
  my $server = strmon_daemon->new({'pidfile' => 'none',
                                'localport' => 9867}, \@ARGV);

  $server->Bind();

AFP



$strmon_help=<<"AFP";

strmon version $version

Basically, strmon creates a buffer which monitor messages based on highlights,
tags (so can be private messages), buffers or specific nicknames.

Although it can be run by itself, full advantage of strmon is achieved using
companion script strmon_daemon.pl which allow sound and osd notifications, it
is embedded in this script and can be generated with command :
    /strmon daemon write
that will write script strmon_daemon.pl into \$HOME.
By default use of this daemon is deactivated, you can print current state,
enable or disable it with command:
    /strmon daemon [on|off]

The script strmon_daemon.pl uses programs mplayer (http://www.mplayerhq.hu/)
and notify-send, which must be installed on local machine.
strmon_daemon.pl also needs the following files to exist on local machine :
    \$HOME/.config/strmon_daemon/pics/default.png
    \$HOME/.config/strmon_daemon/sounds/default.ogg

Principle of operation :
1) start notification daemon strmon_daemon.pl on local machine.
2) If you run weechat on the local machine, just load strmon.pl script into
weechat and that's it.
If weechat runs on a distant machine on which you connect by ssh, use the
following command for connecting :
     ssh distant.machine.org -R 9867:localhost:9867
this will redirect localhost:9867 on the remote machine to
localhost:9867 on the local machine thus allowing strmon.pl weechat script
to access the notification daemon on local machine.

In this version, notifo support (smartphone notification) has been replaced
by 'Notify My Android' as notifo no longer exist.
See https://www.notifymyandroid.com to get an account, unfortunately you will
only have 5 notifications per day for the free version.

strmon is configured by entering commands either with
     /strmon command
  in any buffer, either with
     command
  in the strmon buffer.
command outputs are printed in the core buffer.



Note :
When specifying a picture (res. sound) file, unless the name begin with a / it
is considered to be relative to \$HOME/.config/strmon_daemon/pics (res. /sounds)

  help
   display this help

  open
    open a new monitoring buffer if it does not already exist. It is created
    on startup but can be closed by /buffer close, in that case monitoring
    is directed to core buffer.

  mode
  mode {normal|silent|nosound|novisual}
    without argument : print current default mode of operation
    with argument : set the specified mode as default

        normal   : both osd and sound notifications
        silent   : no notification at all, only monitoring
        nosound  : only osd notification
        novisual : only sound notification

  color
  color {bgcolor|fgcolor|chanelcolor|nickcolor} color
    without argument : print default colors used for osd notifications
    with argument : set the specified color to be used as :

        bgcolor     : color used as background
        fgcolor     : text color used for the content of the message
        chanelcolor : text color used for chanel name
        nickcolor   : text color used for nick name

        color can be specified either with an X11 color name (without space),
        either by a RGB hexadecimal value.

            ex : color fgcolor #ffffff
                 color fgcolor black

  nma [on|off]
  nma test
  nma apikey [APIKEY]
    without arguments : print current status of nma (Notify My Android) use.
    test : try to send a test notification
    on|off : set use of nma notifications
    apikey [APIKEY] : print or set the apikey for nma account

  daemon [on|off]
  daemon write
  daemon test
  daemon port [port]
  daemon {piclist|soundlist}
  daemon show picturefile
  daemon play soundfile
    without arguments : print current status of daemon use. Note that if it
                        is 'off' the only other possible commands are on|off,
                        port and write.
    on|off : set use of notification daemon
    write : will write file \$HOME/strmon_daemon.pl
    test : try to contact the server with a test notification
                        (bypassing default operation mode)
    port [port] : print daemon port number or set it to the given value
    piclist : ask the daemon the list of pictures available on its side
                (in \$HOME/.config/strmon_daemon/pics )
    soundlist : ask the daemon the list of sounds available on its side
                (in \$HOME/.config/strmon_daemon/sounds )
    show picturefile : ask the daemon to display the specified image file
    play soundfile : ask the daemon to play the specified sound file

  picture
  picture picturefile
    without arguments : print current default picture
    with argument : set the specified file as default picture

  sound
  sound soundfile
    without arguments : print current default sound
    with argument : set the specified sound as default sound

  nick nickname
  nick nickname test
  nick nickname mode {normal|silent|nosound|novisual}
  nick nickname pic picfile
  nick nickname sound soundfile
  nick nickname {bgcolor|fgcolor|chanelcolor|nickcolor} color
    without arguments : show options specific to one nickname
    with argument : set option specific to one nickname, or make
    a test notification from nickname.

  filtertags
  filtertags list [givenlist]
    without arguments : show current list of filtered tags (messages
                        with these tags will not be monitored)
    list [givenlist] : set the tag list to be filtered given as a
                        comma separated list of tag, or no arguments
                        to erase it.

  filternicks
  filternicks list [givenlist]
    without arguments : show current list of filtered nicks (messages
                        from these nicks will not be monitored)
    list [givenlist] : set the nick list to be filtered given as a
                        comma separated list of nicks, or no arguments
                        to erase it.

  monitor
  monitor {tag|buf|nick} number del
  monitor {tag|buf|nick} number {normal|silent|nosound|novisual}
  monitor hl {on|off} [normal|silent|nosound|novisual]
  monitor tag add tagname [normal|silent|nosound|novisual]
  monitor buf add regex [normal|silent|nosound|novisual]
  monitor nick add nickname [normal|silent|nosound|novisual]
    without arguments : print a numbered list of current monitors
    number del : remove monitor identified by its number (given with
                 previous command). Note that all monitors will be
                 renumbered after that.
    number {normal|silent|nosound|novisual} : set the notification mode
                 for the monitor given by its number
    hl {on|off} [normal|silent|nosound|novisual] : activate/deactivate
                 monitoring of highlights and optionally set notification
                 mode.
    tag add tagname [normal|silent|nosound|novisual] : monitor messages
                 with tag tagname, optionally set notification mode
    buf add regex [normal|silent|nosound|novisual] : monitor messages printed
                 in buffer with name given by the given regex, optionally
                 set notification mode.
    nick add nickname [normal|silent|nosound|novisual] : monitor messages
                 from the specified nickname

AFP

$strmon_buffer = "";
$command_buffer = "";
weechat::hook_command("strmon", "Message monitoring and notification", "command", $strmon_help, "", "strmon_command", "");
weechat::hook_print("", "", "", 0, "strmon_event", "");
strmon_default_settings();
strmon_buffer_open();


###############################
# Subs

sub strmon_command
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    strmon_buffer_input($data,$buffer,$args);
    return weechat::WEECHAT_RC_OK;
}

sub strmon_buffer_input
{
    my $cb_buffer=$_[1];
    my $cb_data=$_[2];

    #weechat::print($cb_buffer, $cb_data);
    $cb_data=~s/\s*$//;
    $cb_data=~s/^\s*//;
    $cb_data=~/^(\S*)\s*(.*)$/;
    my $main=$1;
    my $args=$2;
    #weechat::print_date_tags($strmon_buffer,time,$strmon_tag,$main);
    if ( ($main eq 'help') || ($main eq '') )
        {
        # help
        weechat::command("", "/help strmon");
        } elsif ($main eq 'open')
        {
        strmon_buffer_open();
        } elsif ($main eq 'mode')
        {
        # mode
        strmon_mode_command($args);
        } elsif ($main eq 'color')
        {
        # color
        strmon_color_command($args);
        } elsif ($main eq 'nma')
        {
        # nma
        strmon_nma_command($args);
        } elsif ($main eq 'daemon')
        {
        # daemon
        strmon_daemon_command($args);
        } elsif ($main eq 'picture')
        {
        # picture
        strmon_picture_command($args);
        } elsif ($main eq 'sound')
        {
        # sound
        strmon_sound_command($args);
        } elsif ($main eq 'nick')
        {
        # nick
        strmon_nick_command($args);
        } elsif ($main eq 'filtertags')
        {
        # filtertags
        strmon_filtertags_command($args);
        } elsif ($main eq 'filternicks')
        {
        strmon_filternicks_command($args);
        } elsif ($main eq 'monitor')
        {
        # monitor
        strmon_monitor_command($args);
        } else
        {
        # unknown
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Unrecognized strmon command");
        }
    return weechat::WEECHAT_RC_OK;
}


sub strmon_mode_command
{
    my $args=shift @_;
    my $mode;
    $args=~s/ //g;
    if ($args eq '')
        {
        $mode=weechat::config_get_plugin('globalmode');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Current mode is : $mode");
        } elsif ( ($args eq 'normal') || ($args eq 'silent') || ($args eq 'nosound') || ($args eq 'novisual') )
        {
        weechat::config_set_plugin('globalmode',$args);
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Mode set to $args");
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Wrong argument, must be : normal,silent,nosound,novisual");
        }
    return weechat::WEECHAT_RC_OK;
}

sub strmon_color_command
{
    my $args=shift @_;
    $args=~s/  / /g;
    my @args=split(" ",$args);
    if (scalar(@args)==0)
        {
        my $bgcolor=weechat::config_get_plugin('default_bg_color');
        my $fgcolor=weechat::config_get_plugin('default_fg_color');
        my $nickcolor=weechat::config_get_plugin('default_nick_color');
        my $chanelcolor=weechat::config_get_plugin('default_chanel_color');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Colors used for osd notifications :\n".
                                      "    Background (bgcolor)     : $bgcolor\n".
                                      "    Text       (fgcolor)     : $fgcolor\n".
                                      "    Chanel     (chanelcolor) : $chanelcolor\n".
                                      "    Nick       (nickcolor)   : $nickcolor");
        } elsif (scalar(@args)==2)
        {
        my %coptions = ( 'bgcolor' => 'default_bg_color',
                         'fgcolor' => 'default_fg_color',
                         'chanelcolor' => 'default_chanel_color',
                         'nickcolor' => 'default_nick_color' );
        if (defined($coptions{$args[0]}))
            {
            weechat::config_set_plugin($coptions{$args[0]},$args[1]);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Color ".$args[0]." set to : ".$args[1]);
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Wrong first argument for command color, must be one of\n    bgcolor,fgcolor,chanelcolor,nickcolor");
            }
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Wrong number of arguments for command color");
        }
    return weechat::WEECHAT_RC_OK;
}


sub strmon_nma_command
{
    my $args=shift @_;
    my $usenma=weechat::config_get_plugin("usenma");
    my $apikey=weechat::config_get_plugin("nma_apikey");
    $args=~/^(\S*)\s*(.*)$/;
    my $first=$1;
    my $second=$2;
    if ($first eq '')
        {
        # print usage
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Use of nma is currently : $usenma");
        } elsif (($first eq 'on') || ($first eq 'off'))
        {
        weechat::config_set_plugin('usenma',$first);
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Use of nma set to : $first");
        } elsif ($first eq 'apikey')
        {
        if ($second eq '')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma apikey is : $apikey");
            } else
            {
            weechat::config_set_plugin('nma_apikey',$second);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma apikey set to : $second");
            }
        } elsif ($first eq 'test')
        {
            # test nma
            my $testdata='1 irc.#test Nickname : This is a test message';
            strmon_nma_execute($testdata);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma test done");
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Wrong argument for nma command.");
        }

    return weechat::WEECHAT_RC_OK;
}


sub strmon_daemon_command
{
    my $args=shift @_;
    my $port = weechat::config_get_plugin("notifyport");
    my $usedaemon=weechat::config_get_plugin('usedaemon');
    $args=~/^(\S*)\s*(.*)$/;
    my $first=$1;
    my $second=$2;
    if (($first eq 'piclist') || ($first eq 'soundlist'))
        {
        if ($usedaemon ne 'on')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"This command is only available when use of daemon is on");
            return weechat::WEECHAT_RC_OK;
            }
        if (my $sock = IO::Socket::INET->new(PeerAddr => 'localhost',
                                 PeerPort => $port+0,
                                 Proto => 'tcp'))
            {
            print $sock "daemon $first\n";
            my $answer=$sock->getline();
            $sock->shutdown(2);
            my @liste=split(',',$answer);
            foreach (@liste)
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,$_);
                }
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Problem contacting daemon");
            }

        } elsif (($first eq 'play') || ($first eq 'show'))
        {
        if ($usedaemon ne 'on')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"This command is only available when use of daemon is on");
            return weechat::WEECHAT_RC_OK;
            }
        if (my $sock = IO::Socket::INET->new(PeerAddr => 'localhost',
                                 PeerPort => $port+0,
                                 Proto => 'tcp'))
            {
            print $sock "daemon $first \"$second\"\n";
            $sock->shutdown(2);
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Problem contacting daemon");
            }
        } elsif ($first eq 'test')
        {
        if ($usedaemon ne 'on')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"This command is only available when use of daemon is on");
            return weechat::WEECHAT_RC_OK;
            }
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Testing daemon connection");
        my $bg=weechat::config_get_plugin('default_bg_color');
        my $fg=weechat::config_get_plugin('default_fg_color');
        my $cc=weechat::config_get_plugin('default_chanel_color');
        my $nc=weechat::config_get_plugin('default_nick_color');
        my $pi=weechat::config_get_plugin('default_picture');
        my $so=weechat::config_get_plugin('default_sound');

        if (my $sock = IO::Socket::INET->new(PeerAddr => 'localhost',
                                 PeerPort => $port+0,
                                 Proto => 'tcp'))
            {
            my $out = "0 \"$pi\" \"$so\" $bg $fg $cc $nc 1 irc.#test Nickname : This is a test message\n";
            print $sock $out;
            $sock->shutdown(2);
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Problem contacting daemon");
            }
        } elsif ($first eq 'port')
        {
        if ($second eq '')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Daemon port number : $port");
            } elsif ($second=~/^\d+$/)
            {
            weechat::config_set_plugin('notifyport',$second);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Daemon port set to $second");
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Argument should be an integer");
            }

        } elsif ( ($first eq '') || ($first eq 'on') || ($first eq 'off') )
        {
        if ($first eq '')
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Use of daemon is currently : $usedaemon");
            } else
            {
            weechat::config_set_plugin('usedaemon',$first);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Use of daemon set to : $first");
            }
        } elsif ($first eq 'write')
        {
        my $fich=$ENV{'HOME'}."/strmon_daemon.pl";
        unless ( open(FICH,">$fich") )
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Cannot open $fich for writing ...");
            return weechat::WEECHAT_RC_OK;
            }
        print FICH $daemon_file;
        close(FICH);
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"File $fich has been written. Refer to help for the rest ...");
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Wrong argument for daemon command.");
        }

    return weechat::WEECHAT_RC_OK;
}

sub strmon_picture_command
{
    my $args=shift @_;
    if ($args eq '')
        {
        my $pic=weechat::config_get_plugin('default_picture');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Default picture is currently : $pic");
        } else
        {
        weechat::config_set_plugin('default_picture',$args);
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Default picture set to $args");
        }
    return weechat::WEECHAT_RC_OK;
}

sub strmon_sound_command
{
    my $args=shift @_;
    if ($args eq '')
        {
        my $sound=weechat::config_get_plugin('default_sound');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Default sound is currently : $sound");
        } else
        {
        weechat::config_set_plugin('default_sound',$args);
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Default sound set to $args");
        }
    return weechat::WEECHAT_RC_OK;
}

sub strmon_nick_command
{
    my $args=shift @_;
    $args=~/^(\S*)\s*(.*)$/;
    my $nickname=$1;
    $args=$2;
    if ($nickname eq "")
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Must give a nickname");
        } else
        {
        if ($args eq '')
            {
            unless (weechat::config_is_set_plugin("nick_$nickname") || weechat::config_is_set_plugin("nick_color_$nickname"))
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"No configuration for nickname $nickname");
                } else
                {
                if (weechat::config_is_set_plugin("nick_$nickname"))
                    {
                    my ($mo,$pi,$so)=split(",",weechat::config_get_plugin("nick_$nickname"));
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"$nickname mode : $mo\n$nickname picture : $pi\n$nickname sound : $so");
                    }
                if (weechat::config_is_set_plugin("nick_color_$nickname"))
                    {
                    my ($bc,$fc,$cc,$nc)=split(",",weechat::config_get_plugin("nick_color_$nickname"));
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"$nickname bgcolor : $bc\n$nickname fgcolor : $fc\n$nickname chanelcolor : $cc\n$nickname nickcolor : $nc");
                    }
                }

            } else
            {
            #
            $args=~/^(\S+)\s*(.*)$/;
            my $first=$1;
            my $args=$2;
            # preparing settings
            my $mo;
            my $pi;
            my $so;
            if (weechat::config_is_set_plugin("nick_$nickname"))
                {
                ($mo,$pi,$so)=split(",",weechat::config_get_plugin("nick_$nickname"));
                } else
                {
                $mo=weechat::config_get_plugin('globalmode');
                $pi=weechat::config_get_plugin('default_picture');
                $so=weechat::config_get_plugin('default_sound');
                }
            my $bc;
            my $fc;
            my $cc;
            my $nc;
            if (weechat::config_is_set_plugin("nick_color_$nickname"))
                {
                ($bc,$fc,$cc,$nc)=split(",",weechat::config_get_plugin("nick_color_$nickname"));
                } else
                {
                $bc=weechat::config_get_plugin('default_bg_color');
                $fc=weechat::config_get_plugin('default_fg_color');
                $cc=weechat::config_get_plugin('default_chanel_color');
                $nc=weechat::config_get_plugin('default_nick_color');
                }
            if ($first eq 'test')
                {
                strmon_notify($cmode{$mo},$pi,$so,$bc,$fc,$cc,$nc,"1 irc.#test $nickname : This is a test message from $nickname");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Test notification from $nickname done");
                }
                elsif ( ($first eq 'mode') && ($args ne '') )
                {
                if (($args ne 'normal') && ($args ne 'silent') && ($args ne 'nosound') && ($args ne 'novisual'))
                    {
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"Argument for nick $nickname mode should be one of normal,silent,nosound,novisual");
                    } else
                    {
                    weechat::config_set_plugin("nick_$nickname","$args,$pi,$so");
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"Mode for $nickname set to $args");
                    }
                } elsif ( ($first eq 'picture') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_$nickname","$mo,$args,$so");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Picture for $nickname set to $args");
                } elsif ( ($first eq 'sound') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_$nickname","$mo,$pi,$args");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Sound for $nickname set to $args");
                } elsif ( ($first eq 'bgcolor') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_color_$nickname","$args,$fc,$cc,$nc");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Background color fot $nickname set to $args");
                } elsif ( ($first eq 'fgcolor') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_color_$nickname","$bc,$args,$cc,$nc");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Text color for $nickname set to $args");
                } elsif ( ($first eq 'chanelcolor') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_color_$nickname","$bc,$fc,$args,$nc");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Chanel color for $nickname set to $args");
                } elsif ( ($first eq 'nickcolor') && ($args ne '') )
                {
                weechat::config_set_plugin("nick_color_$nickname","$bc,$fc,$cc,$args");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Nickname color for $nickname set to $args");
                } else
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"bad arguments for nick $nickname command");
                }
            }
        }
    return weechat::WEECHAT_RC_OK;
}

sub strmon_filtertags_command
{
    my $args=shift @_;
    if ($args eq '')
        {
        my $tags=weechat::config_get_plugin('filtertags');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Currently filtered tags : $tags");
        } elsif ($args=~/^list\s*(.*)$/)
        {
        $args=$1;
        if ($args eq '')
            {
            # reset list
            weechat::config_set_plugin('filtertags',"");
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"List of filtered tags reseted");
            } elsif ($args=~/^([^,\s]+,)*[^,\s]+$/)
            {
            weechat::config_set_plugin('filtertags',$args);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"List of filtered tags set to : $args");
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"must enter a comma separated list of tags");
            }
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad argument to filtertags command");
        }

    return weechat::WEECHAT_RC_OK;
}

sub strmon_filternicks_command
{
    my $args=shift @_;
    if ($args eq '')
        {
        my $nicks=weechat::config_get_plugin('filternicks');
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Currently filtered nicks : $nicks");
        } elsif ($args=~/^list\s*(.*)$/)
        {
        $args=$1;
        if ($args eq '')
            {
            # reset list
            weechat::config_set_plugin('filternicks',"");
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"List of filtered nicks reseted");
            } elsif ($args=~/^([^,\s]+,)*[^,\s]+$/)
            {
            weechat::config_set_plugin('filternicks',$args);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"List of filtered nicks set to : $args");
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"must enter a comma separated list of nicks");
            }
        } else
        {
        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad argument to filternicks command");
        }

    return weechat::WEECHAT_RC_OK;
}

sub strmon_monitor_command
{
    my $args=shift @_;
    my ($hl,$hlm)=split(':',weechat::config_get_plugin('highlights'));
    my @taglist=split(',',weechat::config_get_plugin('monitortags'));
    my @buflist=split(',',weechat::config_get_plugin('monitorbuf'));
    my @nicklist=split(',',weechat::config_get_plugin('monitornicks'));
    if ($args eq '')
        {
        # no arguments, just print the list
        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Monitor highlights is ".weechat::color('magenta').$hl.weechat::color('chat').", with notification mode ".weechat::color('green').$hlm.weechat::color("reset"));
        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."There are ".weechat::color('yellow').scalar(@taglist).weechat::color('chat')." tags monitored :".weechat::color("reset"));
        my $ntags=0;
        foreach (@taglist)
            {
            $ntags++;
            my ($t,$m)=split(':',$_);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"    ".weechat::color('yellow').$ntags.weechat::color('chat').": ".
                            weechat::color('magenta').$t.weechat::color('chat')." with notification mode ".weechat::color('green').$m.weechat::color("reset"));
            }
        my $nbufs=0;
        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."There are ".weechat::color('yellow').scalar(@buflist).weechat::color('chat')." buffers monitored :".weechat::color("reset"));
        foreach (@buflist)
            {
            $nbufs++;
            my ($b,$m)=split(':',$_);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"    ".weechat::color('yellow').$nbufs.weechat::color('chat').": ".
                            weechat::color('magenta').$b.weechat::color('chat')." with notification mode ".weechat::color('green').$m.weechat::color("reset"));
            }
        my $nnicks=0;
        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."There are ".weechat::color('yellow').scalar(@nicklist).weechat::color('chat')." nicks monitored :".weechat::color("reset"));
        foreach (@nicklist)
            {
            $nnicks++;
            my ($n,$m)=split(':',$_);
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"    ".weechat::color('yellow').$nnicks.weechat::color('chat').": ".
                            weechat::color('magenta').$n.weechat::color('chat')." with notification mode ".weechat::color('green').$m.weechat::color("reset"));
            }
        } else
        {
        $args=~/^(\S+)\s*(.*)$/;
        my $first=$1;
        $args=$2;
        if ($first eq 'hl')
            {
            if ($args=~/^(on|off)\s*(normal|silent|nosound|novisual)?$/)
                {
                my $shl=$1;
                my $shlm;
                ($2)?($shlm=$2):($shlm=$hlm);
                weechat::config_set_plugin('highlights',"$shl:$shlm");
                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Monitor highlights set to ".weechat::color('magenta').$shl.weechat::color('chat')." with notify mode ".weechat::color('green').$shlm.weechat::color('reset'));
                } else
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor hl command");
                }
            } elsif ($first eq 'tag')
            {
            if ($args eq '')
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor tag command");
                } else
                {
                $args=~/^(\S+)\s*(.*)$/;
                my $second=$1;
                $args=$2;
                if ($second eq 'add')
                    {
                    if ($args=~/^(\S+)\s*(normal|silent|nosound|novisual)?$/)
                        {
                        my $stag=$1;
                        my $stmod;
                        ($2)?($stmod=$2):($stmod='normal');
                        push @taglist, "$stag:$stmod";
                        weechat::config_set_plugin('monitortags',join(',',@taglist));
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Added monitoring of tag ".weechat::color('magenta').$stag.weechat::color('chat')." with notify mode ".weechat::color('green').$stmod.weechat::color('reset'));
                        } else
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor tag add command");
                        }
                    } elsif ($second=~/\d+/)
                    {
                    #
                    if ( ($second > scalar(@taglist)) || ($second <= 0) )
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Given number does not match an existing tag");
                        } else
                        {
                        if ($args=~/^(del|normal|silent|nosound|novisual)$/)
                            {
                            my ($t,$m)=split(':',$taglist[$second-1]);
                            if ($args eq 'del')
                                {
                                splice @taglist,($second-1),1;
                                weechat::config_set_plugin('monitortags',join(',',@taglist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Monitoring of tag ".weechat::color('magenta').$t.weechat::color('chat')." removed".weechat::color('reset'));
                                } else
                                {
                                $taglist[$second-1]="$t:$args";
                                weechat::config_set_plugin('monitortags',join(',',@taglist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Notification mode set to ".weechat::color('green').$m.weechat::color('chat')." for tag ".weechat::color('magenta').$t.weechat::color('reset'));
                                }
                            } else
                            {
                            weechat::print_date_tags($command_buffer,time,$strmon_tag,"last argument should be one of del,normal,silent,nosound,novisual");
                            }
                        }
                    } else
                    {
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor tag command");
                    }
                }
            } elsif ($first eq 'nick')
            {
            if ($args eq '')
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor nick command");
                } else
                {
                $args=~/^(\S+)\s*(.*)$/;
                my $second=$1;
                $args=$2;
                if ($second eq 'add')
                    {
                    if ($args=~/^(\S+)\s*(normal|silent|nosound|novisual)?$/)
                        {
                        my $snick=$1;
                        my $snmod;
                        ($2)?($snmod=$2):($snmod='normal');
                        push @nicklist, "$snick:$snmod";
                        weechat::config_set_plugin('monitornicks',join(',',@nicklist));
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Added monitoring of nick ".weechat::color('magenta').$snick.weechat::color('chat')." with notify mode ".weechat::color('green').$snmod.weechat::color('reset'));
                        } else
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor nick add command");
                        }
                    } elsif ($second=~/\d+/)
                    {
                    #
                    if ( ($second > scalar(@nicklist)) || ($second <= 0) )
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Given number does not match an existing nick");
                        } else
                        {
                        if ($args=~/^(del|normal|silent|nosound|novisual)$/)
                            {
                            my ($n,$m)=split(':',$nicklist[$second-1]);
                            if ($args eq 'del')
                                {
                                splice @nicklist,($second-1),1;
                                weechat::config_set_plugin('monitornicks',join(',',@nicklist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Monitoring of nick ".weechat::color('magenta').$n.weechat::color('chat')." removed".weechat::color('reset'));
                                } else
                                {
                                $nicklist[$second-1]="$n:$args";
                                weechat::config_set_plugin('monitornicks',join(',',@nicklist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Notification mode set to ".weechat::color('green').$m.weechat::color('chat')." for nick ".weechat::color('magenta').$n.weechat::color('reset'));
                                }
                            } else
                            {
                            weechat::print_date_tags($command_buffer,time,$strmon_tag,"last argument should be one of del,normal,silent,nosound,novisual");
                            }
                        }
                    } else
                    {
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor nick command");
                    }
                }
            } elsif ($first eq 'buf')
            {
            if ($args eq '')
                {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor buf command");
                } else
                {
                $args=~/^(\S+)\s*(.*)$/;
                my $second=$1;
                $args=$2;
                if ($second eq 'add')
                    {
                    if ($args=~/^(\S+)\s*(normal|silent|nosound|novisual)?$/)
                        {
                        my $sbuf=$1;
                        my $sbmod;
                        ($2)?($sbmod=$2):($sbmod='normal');
                        push @buflist, "$sbuf:$sbmod";
                        weechat::config_set_plugin('monitorbuf',join(',',@buflist));
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Added monitoring of buffer ".weechat::color('magenta').$sbuf.weechat::color('chat')." with notify mode ".weechat::color('green').$sbmod.weechat::color('reset'));
                        } else
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor buf add command");
                        }
                    } elsif ($second=~/\d+/)
                    {
                    #
                    if ( ($second > scalar(@buflist)) || ($second <= 0) )
                        {
                        weechat::print_date_tags($command_buffer,time,$strmon_tag,"Given number does not match an existing monitored buffer");
                        } else
                        {
                        if ($args=~/^(del|normal|silent|nosound|novisual)$/)
                            {
                            my ($b,$m)=split(':',$buflist[$second-1]);
                            if ($args eq 'del')
                                {
                                splice @buflist,($second-1),1;
                                weechat::config_set_plugin('monitorbuf',join(',',@buflist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Monitoring of buffer ".weechat::color('magenta').$b.weechat::color('chat')." removed".weechat::color('reset'));
                                } else
                                {
                                $buflist[$second-1]="$b:$args";
                                weechat::config_set_plugin('monitorbuf',join(',',@buflist));
                                weechat::print_date_tags($command_buffer,time,$strmon_tag,weechat::color('chat')."Notification mode changed to ".weechat::color('green').$args.weechat::color('chat')." for ".weechat::color('magenta').$b.weechat::color('reset'));
                                }
                            } else
                            {
                            weechat::print_date_tags($command_buffer,time,$strmon_tag,"last argument should be one of del,normal,silent,nosound,novisual");
                            }
                        }
                    } else
                    {
                    weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad arguments for monitor buf command");
                    }
                }
            } else
            {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"Bad argument for monitor command");
            }
        }
    return weechat::WEECHAT_RC_OK;
}

sub strmon_buffer_open
{
    $strmon_buffer = weechat::buffer_search("perl", "strmon");

    if ($strmon_buffer eq "")
    {
        $strmon_buffer = weechat::buffer_new("strmon", "strmon_buffer_input", "", "strmon_buffer_close", "");
        weechat::buffer_set($strmon_buffer, "highlight_words", "-");
        weechat::buffer_set($strmon_buffer, "title", "strmon Message Monitoring");

    }

    return weechat::WEECHAT_RC_OK;
}

sub strmon_default_settings
{
# set default values
# use nma
if (! weechat::config_is_set_plugin("usenma"))
    {
    weechat::config_set_plugin("usenma","off");
    }

# nma apikey
if (! weechat::config_is_set_plugin("nma_apikey"))
    {
    weechat::config_set_plugin("nma_apikey","nokey");
    }

# use daemon
if (! weechat::config_is_set_plugin("usedaemon"))
    {
    weechat::config_set_plugin("usedaemon","off");
    }

# port number
if (! weechat::config_is_set_plugin("notifyport"))
    {
    weechat::config_set_plugin("notifyport","9867");
    }

# filter tags
if (! weechat::config_is_set_plugin("filtertags"))
    {
    weechat::config_set_plugin("filtertags","irc_join,irc_part,irc_quit,away_info");
    }

# filter nicks
if (! weechat::config_is_set_plugin("filternicks"))
    {
    weechat::config_set_plugin("filternicks","");
    }

# global mode
if (! weechat::config_is_set_plugin("globalmode"))
    {
    weechat::config_set_plugin("globalmode","normal");
    }

# highlights
if (! weechat::config_is_set_plugin("highlights"))
    {
    weechat::config_set_plugin("highlights","on:normal");
    }

# monitor tags
if (! weechat::config_is_set_plugin("monitortags"))
    {
    weechat::config_set_plugin("monitortags","notify_private:normal");
    }

# monitor buffers
if (! weechat::config_is_set_plugin("monitorbuf"))
    {
    weechat::config_set_plugin("monitorbuf","");
    }

# monitor nicks
if (! weechat::config_is_set_plugin("monitornicks"))
    {
    weechat::config_set_plugin("monitornicks","");
    }

# default picture
if (! weechat::config_is_set_plugin("default_picture"))
    {
    weechat::config_set_plugin("default_picture","default.png");
    }

# default sound
if (! weechat::config_is_set_plugin("default_sound"))
    {
    weechat::config_set_plugin("default_sound","default.ogg");
    }

# default background color
if (! weechat::config_is_set_plugin("default_bg_color"))
    {
    weechat::config_set_plugin("default_bg_color","#fff0d7");
    }

# default message color
if (! weechat::config_is_set_plugin("default_fg_color"))
    {
    weechat::config_set_plugin("default_fg_color","black");
    }

# default chanel color
if (! weechat::config_is_set_plugin("default_chanel_color"))
    {
    weechat::config_set_plugin("default_chanel_color","brown");
    }

# default nick color
if (! weechat::config_is_set_plugin("default_nick_color"))
    {
    weechat::config_set_plugin("default_nick_color","blue");
    }

}


sub strmon_buffer_close
{
    $strmon_buffer = "";
    return weechat::WEECHAT_RC_OK;
}

sub strmon_nma_execute
{
    (my $data) =  @_;
    my $nout=weechat::string_remove_color($data,"");
    # do not notify unformatted messages (such as channel messages when monitoring
    # a buffer)
    return unless($nout=~/^(\d+)\s(\S+)\s(\S+)\s:\s(.*)$/);
    my $nchan=$1;
    my $chan=$2;
    my $nick=$3;
    my $msg=$4;

    my $curl = new WWW::Curl::Easy;
    my @fields;

    # Try to find an url in the message to send with the notification
    my $url="";
    if ($msg=~/(https?:\/\/\S+)/)
        {
        $url=$1;
        }

    my $apikey=weechat::config_get_plugin("nma_apikey");
    push @fields,"apikey=$apikey";
    push @fields,"application=Weechat";
    push @fields,"event=".uri_escape("Chan:$chan Nick:$nick");
    push @fields,"description=".uri_escape($msg);
    if ($url ne "")
        {
        push @fields,"url=".uri_escape($url);
        }

    my $pdata=join("&",@fields);

    $curl->setopt(CURLOPT_POSTFIELDS, $pdata);
    $curl->setopt(CURLOPT_URL, 'https://www.notifymyandroid.com/publicapi/notify');
    $curl->setopt(CURLOPT_SSL_VERIFYPEER,0);

    # redirect response into variable $response_body
    my $response_body;
    open (my $fileid,">",\$response_body);
    $curl->setopt(CURLOPT_WRITEDATA,$fileid);

    # Starts the actual request
    my $retcode = $curl->perform;

    # Write an output in case of problems
    if ($retcode == 0) {
        # parse result
        $response_body=~/^.+code=\"(\d+)\"/;
        my $rcode=$1;

        if ($rcode==200) {
           # Message sent do not write anything

           } elsif ($rcode==400) {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma error 400 : The data supplied is in the wrong format, invalid length or null");
           } elsif ($rcode==401) {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma error 401 : None of the API keys provided were valid.");
           } elsif ($rcode==402) {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma error 402 : Maximum number of API calls per hour exceeded.");
           } elsif ($rcode==500) {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"nma error 500 : Internal server error. Please contact our support if the problem persists.");
           } else {
                weechat::print_date_tags($command_buffer,time,$strmon_tag,"Unknown nma error code : $rcode");
           }


        } else {
            weechat::print_date_tags($command_buffer,time,$strmon_tag,"A curl error happened : ".$curl->strerror($retcode)." ($retcode)");
        }
    # free data
    undef(@fields);
    close($fileid);
}

sub strmon_notify
{
    (my $mode, my $pic, my $sound, my $bg_color, my $fg_color, my $chan_color, my $nick_color, my $data) = @_;
    my $ret=0;
    my $usedaemon=weechat::config_get_plugin('usedaemon');
    my $usenma=weechat::config_get_plugin('usenma');

    # Daemon notification
    if ($usedaemon eq 'on')
        {
        my $port = weechat::config_get_plugin("notifyport");
        if (my $sock = IO::Socket::INET->new(PeerAddr => 'localhost',
                                        PeerPort => $port+0,
                                        Proto => 'tcp'))
            {
            my $out="$mode \"$pic\" \"$sound\" $bg_color $fg_color $chan_color $nick_color ".weechat::string_remove_color($data,"")."\n";
            print $sock $out;
            $sock->shutdown(2);
            $ret=1;
            }
        }

    # nma notification
    if ($usenma eq 'on')
        {
        strmon_nma_execute($data);
        $ret=1;
        }
    return $ret;
}

sub strmon_event
{

    my $cb_bufferp = $_[1];
    my $cb_date = $_[2];
    my $cb_tags = $_[3];
    my $cb_disp = $_[4];
    my $cb_high = $_[5];
    my $cb_prefix = $_[6];
    my $cb_msg = $_[7];


    # exit immediately if buffer is $strmon_buffer or tag is $strmon_tag
    if ( ($cb_bufferp eq  $strmon_buffer) || ($cb_tags=~/$strmon_tag/) )
        {
        return weechat::WEECHAT_RC_OK;
        }

    # debug
    # weechat::print_date_tags($strmon_buffer,time,$strmon_tag, "Tags : $cb_tags");

    # is the tag filtered? then exit.
    my @ftags=split(",",weechat::config_get_plugin("filtertags"));
    foreach (@ftags)
        {
        if ($cb_tags=~/$_/)
            {
            return weechat::WEECHAT_RC_OK;
            }
        }

    # get a "clean" buffer name
    my $bufname = weechat::string_remove_color(weechat::buffer_get_string($cb_bufferp, 'name') ,"");

    # get a "clean" nick name
    my $nickname = weechat::string_remove_color($cb_prefix,"");
    # Remove @ and + from nickname
    $nickname=~/^[@\+]?(.*)$/;
    $nickname=$1;

    # is the nick filtered?
    my @fnicks=split(",",weechat::config_get_plugin("filternicks"));
    foreach (@fnicks)
        {
        if (lc($nickname) eq lc($_))
            {
            return weechat::WEECHAT_RC_OK;
            }
        }

    # initialize pic
    my $picture=weechat::config_get_plugin("default_picture");

    # initialize sound
    my $sound=weechat::config_get_plugin("default_sound");

    # initialize mode
    my $mode=0;

    # initialize background color
    my $bg_color=weechat::config_get_plugin("default_bg_color");

    # initialize foreground color
    my $fg_color=weechat::config_get_plugin("default_fg_color");

    # initialize chanel color
    my $chan_color=weechat::config_get_plugin("default_chanel_color");

    #initialize nick color
    my $nick_color=weechat::config_get_plugin("default_nick_color");

    # Is there a specific configuration for this nick?
    if (weechat::config_is_set_plugin("nick_$nickname"))
        {
        (my $mo, my $pi, my $so) = split(",",weechat::config_get_plugin("nick_$nickname"));
        $mode=$cmode{$mo};
        $picture=$pi;
        $sound=$so;
        }

    # Is there a specific color configuration for this nick?
    if(weechat::config_is_set_plugin("nick_color_$nickname"))
        {
        ($bg_color,$fg_color,$chan_color,$nick_color)=split(",",weechat::config_get_plugin("nick_color_$nickname"));
        }

    # create the output message
    my $outstr= weechat::color("chat_prefix_buffer").
             weechat::buffer_get_integer($cb_bufferp, 'number').
             " ".
             weechat::buffer_get_string($cb_bufferp, 'name').
             weechat::color("reset").
             " ".
             $cb_prefix.weechat::color("reset").
             " : ".
             $cb_msg;


    # highlight and monitor highlights
    (my $hl, my $hlm) = split(":",weechat::config_get_plugin("highlights"));
    if ( ($cb_high==1) && ($hl eq 'on') )
        {
        weechat::print_date_tags($strmon_buffer,time,$strmon_tag, $outstr);
        $mode = $mode | $cmode{weechat::config_get_plugin("globalmode")} | $cmode{$hlm};
        strmon_notify($mode,$picture,$sound,$bg_color,$fg_color,$chan_color,$nick_color,$outstr);
        return weechat::WEECHAT_RC_OK;
        }


    # get monitored tag list
    my @ctaglist=split(",",weechat::config_get_plugin("monitortags"));
    foreach (@ctaglist)
        {
        (my $tag, my $tagm) = split(":",$_);
        if ($cb_tags=~/$tag/)
            {
            weechat::print_date_tags($strmon_buffer,time,$strmon_tag, $outstr);
            $mode = $mode | $cmode{weechat::config_get_plugin("globalmode")} | $cmode{$tagm};
            strmon_notify($mode,$picture,$sound,$bg_color,$fg_color,$chan_color,$nick_color,$outstr);
            return weechat::WEECHAT_RC_OK;
            }
        }

    # get monitored buffer list
    my @cbuflist=split(",",weechat::config_get_plugin("monitorbuf"));
    foreach (@cbuflist)
        {
        (my $buf, my $bufm) = split(":",$_);
        if ($bufname =~/$buf/)
            {
            weechat::print_date_tags($strmon_buffer,time,$strmon_tag, $outstr);
            $mode = $mode | $cmode{weechat::config_get_plugin("globalmode")} | $cmode{$bufm};
            strmon_notify($mode,$picture,$sound,$bg_color,$fg_color,$chan_color,$nick_color,$outstr);
            return weechat::WEECHAT_RC_OK;
            }
        }

    # get monitored nick list
    my @cnicklist=split(",",weechat::config_get_plugin("monitornicks"));
    foreach (@cnicklist)
        {
        (my $nick, my $nickm) = split(":",$_);
        if (lc($nick) eq lc($nickname))
            {
            weechat::print_date_tags($strmon_buffer,time,$strmon_tag, $outstr);
            $mode = $mode | $cmode{weechat::config_get_plugin("globalmode")} | $cmode{$nickm};
            strmon_notify($mode,$picture,$sound,$bg_color,$fg_color,$chan_color,$nick_color,$outstr);
            return weechat::WEECHAT_RC_OK;
            }
        }

    return weechat::WEECHAT_RC_OK;
}
