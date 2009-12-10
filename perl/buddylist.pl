#
# Copyright (c) 2009 by Nils Görs <weechatter@arcor.de>
#
# just a simple buddylist using the nicklist from channels you are in.
# it also works if nicklist is hidden.
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
# settings:
# /set plugins.var.perl.buddylist.color.offline
# /set plugins.var.perl.buddylist.color.online
# /set plugins.var.perl.buddylist.color.away
# /set plugins.var.perl.buddylist.color.default
# /set plugins.var.perl.buddylist.sort ("default" = sorted by nickname or "status" = sorted by status (online, away, offline)
#
# v0.4: added option "sort"
# v0.3: remove spaces for indenting when bar position is top/bottom
#     : hook_config when settings changed.
# v0.2: removed the work-around for crash when searching nick in buffer without nicklist (function nicklist_search_nick)  
# v0.1: initial release


use strict;
my $prgname	= "buddylist";
my $version	= "0.4";
my $description	= "A simple buddylist to show if your buddies are online/away/offline.";

my $buffer	= "";
my $bar_name	= "buddylist";
my $default_buddylist = "buddylist.txt";
my %buddies = ();					# to store the buddylist

my %buddylist_level = (0 => "online", 1 => "away", 2 => "offline");
my %default_color_buddylist = ("online" => "yellow",
                             "away"    => "cyan",
                             "offline"    => "blue");
my $color_default = "lightcyan";
my $position = "top";

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");
init();
buddylist_read();

weechat::bar_item_new($bar_name, "build_buffer", "");

weechat::bar_new($bar_name, "0", "0", "root", "", "left", "horizontal",
                 "vertical", "0", "0", "default", "default", "default", "1",
                 $bar_name);

#weechat::hook_signal("*,irc_in2_366", "check_nick", "");		# 366 waits, till nicklist is fully readed (join does not work!)
#weechat::hook_signal("*,irc_in2_part", "check_nick", "");
weechat::hook_signal("nicklist_changed", "check_nick", "");
weechat::hook_config("*.$prgname.*", "config_signal", "");

weechat::hook_command($prgname, $description,

	"<add>[nick_1 [... nick_n]] | <del>[nick_1 [... nick_n]]", 

	"<add> [nick(s)] add nick(s) to the buddylist\n".
	"<del> [nick(s)] delete nick(s) from the buffylist\n".
	"\n".
	"Options:\n".
	"'buddylist'    : path/file-name to store your buddies.\n".
	"'color.offline': color for offline buddies.\n".
	"'color.online' : color for online buddies.\n".
	"'color.away'   : color for online buddies that are away.\n".
	"\n".
	"Examples:\n".
	"Add buddy to buddylist:\n".
	"/$prgname add buddyname\n".
	"Delete buddy from buddylist:\n".
	"/$prgname del buddyname\n",
	"add|del", "settings", "");

check_nick();

return weechat::WEECHAT_RC_OK;

sub config_signal{
  weechat::bar_item_update($bar_name);
  return weechat::WEECHAT_RC_OK;
}

my $str = "";
sub build_buffer{
$str = "";
    # get bar position (left/right/top/bottom) and sort (default/status)
    my $option = weechat::config_get("weechat.bar.$prgname.position");
    if ($option ne ""){
        $position = weechat::config_string($option);
    }
    my $sort = weechat::config_get_plugin("sort");

    if ($sort eq "status"){							# use sort option "status"
      foreach (sort {$buddies{$a} <=> $buddies{$b}} (sort keys(%buddies))){	# sorted by value
	createoutput();
      }
    } else {									# use "default" for sort
      foreach ( sort { "\L$a" cmp "\L$b" } keys %buddies ){
	createoutput();
      }
    }
    return $str;
}
sub createoutput{
    my $cr = "\n";
        my $color = weechat::config_get_plugin("color.default");
        $color = "default" if ($color eq "");
	    my $status = $buddies{$_};						# get buddy status
            $color = weechat::config_get_plugin("color.".$buddylist_level{$status});
### visual settings for left, right or top and bottom
            my $visual = " ";
            $visual  = $cr if (($position eq "left") || ($position eq "right"));
       $str .= weechat::color($color). "$_" . $visual;
}

sub check_nick{
my $nick_name = "";
my $nick_color = "";
my $nicktest = ();
   my $bufferlist = weechat::infolist_get("buffer","","");			# get list of buffers

  foreach ( keys %buddies ){
  $buddies{$_} = 2;								# set buddy to offline

      while (weechat::infolist_next($bufferlist)){
      $buffer = weechat::infolist_pointer($bufferlist,"pointer");		# get buffer pointer
      my $name = weechat::infolist_string($bufferlist,"plugin_name");		# get name of plugin

	if ($name eq "irc" and $buffer ne 0){					# irc buffer and not 0?
	  my $found = 0;
	  $found = weechat::nicklist_search_nick($buffer,"",$_);		# is nick in nicklist? 0 if nick not found
	    unless ($found eq ""){
		$buddies{$_} = 0;						# buddy is online
		$nicktest = weechat::infolist_get("nicklist",$buffer,"");	# get list of nick

		while (weechat::infolist_next($nicktest)){
		  $nick_name = weechat::infolist_string($nicktest,"name");	# get nick
		  $nick_color = weechat::infolist_string($nicktest,"color");	# get color for nick.
		  $buddies{$_} = 1 if ($_ eq $nick_name and $nick_color eq "weechat.color.nicklist_away");#buddy is away.
		}
		weechat::infolist_free($nicktest);
	    }
	}
      }
    }
  weechat::infolist_free($bufferlist);
  weechat::bar_item_update($bar_name);
return weechat::WEECHAT_RC_OK;
}

sub settings{
	my ($getargs) = ($_[2]);
	my ( $cmd, $args ) = ( $getargs =~ /(.*?)\s+(.*)/ );		# get parameters and cut cmd from nicks
	$cmd = $getargs unless $cmd;

    if (defined $args) {						# buddy name choosed?
       foreach ( split( / +/, $args ) ) {
	  if ($cmd eq "add"){
	      $buddies{$_} = 2;
	      buddylist_save();
	  }
	  if ($cmd eq "del" and exists $buddies{$_}){
	      delete $buddies{$_};
	      buddylist_save();
	  }
       }
    }else{
        weechat::print("", "$prgname : Please tell me the buddy name.");
    }
check_nick();
return weechat::WEECHAT_RC_OK;
}

### read the buddylist
sub buddylist_read {
    my $buddylist = weechat::config_get_plugin("buddylist");
    return unless -e $buddylist;
    open (WL, "<", $buddylist) || DEBUG("$buddylist: $!");
	while (<WL>) {
		chomp;
		$buddies{$_} = 2 if length $_;			# offline
	}
	close WL;
}
sub buddylist_save {
    my $buddylist = weechat::config_get_plugin( "buddylist" );
    open (WL, ">", $buddylist) || DEBUG("write buddylist: $!");
    print WL "$_\n" foreach ( sort { "\L$a" cmp "\L$b" } keys %buddies );
    close WL;
}

sub DEBUG {weechat::print('', "***\t" . $_[0]);}

# init the settings
sub init{
    if ( weechat::config_get_plugin("buddylist") eq '' ) {
        my $wd = weechat::info_get( "weechat_dir", "" );
        $wd =~ s/\/$//;
        weechat::config_set_plugin("buddylist", $wd . "/" . $default_buddylist );
    }
if (weechat::config_get_plugin("color.default") eq "")
{
    weechat::config_set_plugin("color.default", "default");
}
if (weechat::config_get_plugin("sort") eq "")
{
    weechat::config_set_plugin("sort", "default");
}
# get color settings.
  foreach my $level (values %buddylist_level){
    if (weechat::config_get_plugin("color.".$level) eq ""){
        weechat::config_set_plugin("color.".$level,
                                   $default_color_buddylist{$level});
    }
  }
}
