#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
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
# v0.6: nick wasn't set to offline, if user leave channel
# v0.5: server information will be used now instead of nicklist
#	reduction of cpu load (reported by ArcAngel and tigrmesh)
#	bar will be removed if you unload the script. (requested by bazerka)
#	help page will be displayed when you call buddylist without arguments
# v0.4: added option "sort"
# v0.3: remove spaces for indenting when bar position is top/bottom
#     : hook_config when settings changed.
# v0.2: work-around for crash when searching nick in buffer without nicklist (function nicklist_search_nick) removed 
# v0.1: initial release

use strict;
my $prgname	= "buddylist";
my $version	= "0.6";
my $description	= "Simple buddylist that shows the status of your buddies.";

my $buffer	= "";
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
                  "GPL3", $description, "shutdown", "");

init();
buddylist_read();

weechat::bar_item_new($prgname, "build_buffer", "");
weechat::bar_new($prgname, "0", "0", "root", "", "left", "horizontal",
					    "vertical", "0", "0", "default", "default", "default", "1",
					    $prgname);
weechat::command("", "/bar show " . $prgname);

weechat::hook_signal("*,irc_in2_352", "from_hook_who","");			# RFC command with user channel status etc..
weechat::hook_signal("*,irc_in_part", "remove_nick", "");
weechat::hook_signal("*,irc_in_quit", "remove_nick", "");
weechat::hook_config("*.$prgname.*", "config_signal", "");			# settings changed?

weechat::hook_command($prgname, $description,

	"<add>[nick_1 [... nick_n]] | <del>[nick_1 [... nick_n]]", 

	"<add> [nick(s)] add nick(s) to the buddylist\n".
	"<del> [nick(s)] delete nick(s) from the buffylist\n".
	"\n".
	"Options:\n".
	"'plugins.var.perl.buddylist.buddylist'    : path/file-name to store your buddies.\n".
	"'plugins.var.perl.buddylist.color.away'   : colour for away buddies.\n".
	"'plugins.var.perl.buddylist.color.offline': colour for offline buddies.\n".
	"'plugins.var.perl.buddylist.color.online' : colour for online buddies.\n".
	"'plugins.var.perl.buddylist.sort'         : sort method for buddylist.\n".
	"                                  default : $prgname will be sort by nickname\n".
	"                                  status  : $prgname will be sort by status (online, away, offline)\n\n".
	"If $prgname won't refresh, check the following WeeChat options:\n".
	"'irc.network.away_check'          : interval between two checks, in minutes. (has to be >= 1 (default:0)).\n".
	"'irc.network.away_check_max_nicks': channels with high number of nicks will not be checked (default: 25).\n".
	"\n".
	"buddyname has to be written 'case sensitive' (it's recommended to use nick-completion).\n".
	"\n".
	"Examples:\n".
	"Add buddy to buddylist:\n".
	"/$prgname add buddyname\n".
	"Delete buddy from buddylist:\n".
	"/$prgname del buddyname\n",
	"add|del", "settings", "");

return weechat::WEECHAT_RC_OK;


sub config_signal{
  weechat::bar_item_update($prgname);
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
	} else {								# use "default" for sort
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
sub remove_nick{
#($nick,$name,$ip,$action,$channel) = ($args =~ /\:(.*)\!n=(.*)@(.*?)\s(.*)\s(.*)/; # maybe for future use
	my $args = $_[2];							# save callback
	my ($nickname) = ($args =~ /\:(.*)\!/);
	$args =~ /\:(.*)\!/;
	if (exists $buddies{$nickname}){					# nick in buddylist?
		$buddies{$nickname} = 2;					# set buddy to offline
		weechat::bar_item_update($prgname);
	}
}
sub from_hook_who{
	my $args = $_[2];

		my @words= split(" ",$args);
	if (exists $buddies{$words[7]}){					# nick in buddylist?
		$buddies{$words[7]} = 0;					# buddy is online
			$buddies{$words[7]} = 1 if (substr($words[8],0,1) eq "G");# buddy is away
		weechat::bar_item_update($prgname);
	}

}

sub settings{
	my ($getargs) = ($_[2]);
	my ( $cmd, $args ) = ( $getargs =~ /(.*?)\s+(.*)/ );			# get parameters and cut cmd from nicks
		$cmd = $getargs unless $cmd;

	if (defined $args) {							# buddy choosed?
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
		weechat::command("", "/help $prgname");
	}
	weechat::bar_item_update($prgname);
	return weechat::WEECHAT_RC_OK;
}

### read the buddylist
sub buddylist_read {
	my $buddylist = weechat::config_get_plugin("buddylist");
	return unless -e $buddylist;
	open (WL, "<", $buddylist) || DEBUG("$buddylist: $!");
	while (<WL>) {
		chomp;
		$buddies{$_} = 2 if length $_;					# offline
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
sub shutdown{
	weechat::command("", "/bar hide " . $prgname);
}
