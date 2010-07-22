#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# display the status of your buddies in a buddylist bar
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
# 0.9.2 : server wasn't hidden for "default" settings
#	  server will be hidden if all buddies are offline for this server (option: hide.server.if.buddies.offline (requested by TenOfTen))
#	  buddies will be hidden when offline (option: hide.buddy.if.offline (requested by TenOfTen))
#	  new function added: "list"
#	  the buddylist will be saved in a new format : servername.nickname (old format will be recognized, too)
#	  and other internal changes
# 0.9.1	: bar could not be hidden (detrate-)
#	: error message for old datafile (bazerka)
# 0.9: servername without nicks will not be displayed in buddylist
#	servername will be displayed in different colour or will be hidden if not connected (option "color.server.offline")
#	buddylist bar will be hidden if you are not connected to a server (option "hide.bar")
# 0.8: - major changes - (buddylist file changed!!!)
#	buddylist uses now server / nick structure
#       change entries in buddylist to : servername,nickname (e.g.: freenode,nils_2)
#	or add your buddies again with the add function.
# 0.7: nick change will be recognize
# 0.6: nick wasn't set to offline, if buddy leave channel
# 0.5: server information will be used now instead of nicklist
#	reduction of cpu load (reported by ArcAngel and tigrmesh)
#	bar will be removed if you unload the script. (requested by bazerka)
#	help page will be displayed when you call buddylist without arguments
# 0.4: added option "sort"
# 0.3: remove spaces for indenting when bar position is top/bottom
#     : hook_config when settings changed.
# 0.2: work-around for crash when searching nick in buffer without nicklist (function nicklist_search_nick) removed 
# 0.1: initial release
#
# TODO: waiting for redirection ;-)

use strict;

my $prgname		= "buddylist";
my $version		= "0.9.2";
my $description		= "Simple buddylist that shows the status of your buddies.";

my $buffer		= "";
# default settings
my $default_buddylist	= "buddylist.txt";
my %buddylist_level = (0 => "online", 1 => "away", 2 => "offline");
my %default_color_buddylist = ("online" => "yellow",
			       "away"    => "cyan",
			       "offline"    => "blue");
my $position		= "top";
my $hide_bar		= "on";					# hide buddylist bar when all servers are offline
my $hide_server		= "off";				# hide server if no buddy is online on this server
my $hide_buddy		= "off";				# hide buddies when they are offline
my $sort		= "default";				# sort method
my $color_default	= "default";
my $color_server_online	= "white";
my $color_server_offline= "hide";

my %buddies		= ();					# to store the buddylist with status for each nick
my %nick_structure	= ();					# to store servername, nickname and status
#$VAR1 = {
#	'freenode' =>	{
#				'nils_2' => 'online',
#				'nick2' => 'offline',
#				'nick3' => 'online'
#			},                       
#	'fu-berlin' =>	{
#				'nils_2' => 'away'    
#			}
#	};

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
		"GPL3", $description, "shutdown", "");

init();
buddylist_read();

weechat::bar_item_new($prgname, "build_buddylist", "");
weechat::bar_new($prgname, "0", "0", "root", "", "left", "horizontal",
		"vertical", "0", "0", "default", "default", "default", "1",
		$prgname);
weechat::command("", "/bar show " . $prgname);

weechat::hook_signal("*,irc_in2_352", "from_hook_who","");			# RFC command with use,channel,status etc..
weechat::hook_signal("*,irc_in_part", "remove_nick", "");
weechat::hook_signal("*,irc_in_quit", "remove_nick", "");
weechat::hook_signal("*,irc_in_nick", "nick_changed", "");
weechat::hook_config("plugins.var.perl.$prgname.*", "toggled_by_set", "");	# buddylist options changed?
weechat::hook_signal("irc_server_connected", "server_connected", "");
weechat::hook_signal("irc_server_disconnected", "server_disconnected", "");

weechat::hook_command($prgname, $description,
		"<add>[nick_1 [... nick_n]] | <del>[nick_1 [... nick_n]]", 

		"<add> [nick(s)] add nick(s) to the buddylist\n".
		"<del> [nick(s)] delete nick(s) from the buddylist\n".
		"<list> show buddylist\n".
		"\n".
		"Options:\n".
		"'plugins.var.perl.buddylist.buddylist'           : path/file-name to store your buddies.\n".
		"'plugins.var.perl.buddylist.color.away'          : colour for away buddies.\n".
		"'plugins.var.perl.buddylist.color.default        : fall back colour. (default: standard weechat colour)\n".
		"'plugins.var.perl.buddylist.color.offline'       : colour for offline buddies.\n".
		"'plugins.var.perl.buddylist.color.online'        : colour for online buddies.\n".
		"'plugins.var.perl.buddylist.color.server'        : colour for servername.\n".
		"'plugins.var.perl.buddylist.color.server.offline : colour for disconnected server (default: hide).\n".
		"'plugins.var.perl.buddylist.hide.server.if.buddies.offline: hides server when all buddies are offline for this server (default: off).\n".
		"'plugins.var.perl.buddylist.hide.buddy.if.offline: hide buddy if offline (default: off).\n".

		"'plugins.var.perl.buddylist.hide.bar             : hide buddylist-bar when all servers with buddies are offline (default: on).\n".
		"                                                   using this option you can not manually hide the buddylist bar.\n".
		"'plugins.var.perl.buddylist.sort'                : sort method for buddylist (default or status).\n".
		"                                         default : $prgname will be sort by nickname\n".
		"                                         status  : $prgname will be sort by status (online, away, offline)\n\n".
		"If $prgname don't refresh buddylist, check the following WeeChat options:\n".
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
	"add|del|list", "settings", "");
server_check();
return weechat::WEECHAT_RC_OK;

# weechat connected to a server (irc_server_connected)
sub server_connected{
	server_check();
	weechat::bar_item_update($prgname);
	return weechat::WEECHAT_RC_OK;
}

# weechat disconnected from server (irc_server_disconnected)
sub server_disconnected{
	server_check();
	weechat::bar_item_update($prgname);
	return weechat::WEECHAT_RC_OK;
}

my $str = "";
sub build_buddylist{
	$str = "";
	if ($hide_bar eq "on"){
		return $str;										# and print it.
	}
# get bar position (left/right/top/bottom) and sort (default/status)
	my $option = weechat::config_get("weechat.bar.$prgname.position");
	if ($option ne ""){
		$position = weechat::config_string($option);
	}

	if ($sort eq "status"){										# use sort option "status"
		foreach my $s ( sort keys %nick_structure ) {
			if (keys (%{$nick_structure{$s}}) eq "0"){					# check out if nicks exists for server
				next;									# no nick for server. jump to next server
			}
		# sort list by status (from online, away, offline)
		my ($n) = (sort { $nick_structure{$s}{$a} <=> $nick_structure{$s}{$b}}  keys (%{$nick_structure{$s}} ));
		if ($nick_structure{$s}{$n} eq "2" and $hide_server eq "on"){				# status from first buddy in list!
		  next;											# first sorted buddy is offline (2)
		}
			my $visual = " ";								# placeholder after servername
				my $cr = "\n";
			$visual  = $cr if (($position eq "left") || ($position eq "right"));

			my $color_server = get_server_status($s);					# get server colour
			if ($color_server eq "1"){
			  next;										# hide server if result = 1
			}
			$str .= weechat::color($color_server) . $s . ":" . $visual;			# add servername ($s ;) to buddylist

# sorted by status first and nick case insensitiv as second
			      foreach my $n (sort { $nick_structure{$s}{$a} cmp $nick_structure{$s}{$b}} (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}})))){
				createoutput($s,$n);
			      }
		}

	} elsif ($sort ne "status") {									# use sort option "default"
		foreach my $s ( sort keys %nick_structure ) {						# sort server alphabetically
			if (keys (%{$nick_structure{$s}}) eq "0"){					# check out if nicks exists for server
				next;									# no nick for server. jump to next server
			}
		# sort list by status (from online, away, offline)
		my ($n) = (sort { $nick_structure{$s}{$a} <=> $nick_structure{$s}{$b}}  keys (%{$nick_structure{$s}} ));
		if ($nick_structure{$s}{$n} eq "2" and $hide_server eq "on"){				# status from first buddy in list!
		  next;											# first sorted buddy is offline (2)
		}
			my $visual = " ";								# placeholder after servername
				my $cr = "\n";
			$visual  = $cr if (($position eq "left") || ($position eq "right"));

			my $color_server = get_server_status($s);					# get server colour
			if ($color_server eq "1"){
			  next;										# hide server if result = 1
			}
			$str .= weechat::color($color_server) . $s . ":" . $visual;			# add servername ($s ;) to buddylist

				foreach my $n (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}} ))){ # sort by name case insensitiv
					createoutput($s,$n);
				}
		}
	}
	if ($str eq ""){
		$str = "Please wait... no buddies in your buddylist for connected server, or you are not connected to a server, or your buddies are all offline";
	}
	return $str;
}
# get status from server and color the servername (or hide)
sub get_server_status{
my $server = $_[0];
	my $infolist_server = weechat::infolist_get("irc_server","",$server);			# get pointer for server %s
	weechat::infolist_next($infolist_server);
	my $is_connected = weechat::infolist_integer($infolist_server,"is_connected");		# get status of connection for server (1 = connected | 0 = disconnected)
	weechat::infolist_free($infolist_server);						# don't forget to free infolist ;-)
		if ($is_connected == 0){							# 0 = not connected
				if ($color_server_offline eq "hide"){				# hide offline servers?
					return 1;						# yes!
				}
		$color_server_offline = $color_default if ($color_server_offline eq "");
		return $color_server_offline;							# colour for server offline
		}
$color_server_online = $color_default if ($color_server_online eq "");				# fall back colour if color_server = ""
return $color_server_online;									# colour for server online
}

sub createoutput{
my ($server,$nick) = ($_[0],$_[1]);
my $status = $nick_structure{$server}{$nick};							# get buddy status
	if ($status eq "2" and $hide_buddy eq "on"){						# buddy is offline
	  $str .= "";
	}else{											# get colour for away/online
	  my $cr = "\n";
	  my $color = $color_default;
	  $color = "default" if ($color eq "");
		  $color = $default_color_buddylist{$buddylist_level{$status}};
	  ### visual settings for left, right or top and bottom
	  my $visual = " ";									# placeholder
	  my $mover = "";									# move it to right
		  if (($position eq "left") || ($position eq "right")){
			  $visual  = $cr;
			  $mover  = "  ";
		  }
	  $str .= weechat::color($color) . $mover . "$nick" . $visual;
	}

}

# buddy changed his nick (irc_in_nick)
sub nick_changed{
	my ($blank, $servername, $args) = @_;
	my ($server) = split(/,/, $servername);					# get name from server
		$args =~ /\:(.*)\!(.*)\:(.*)/;
	my $old_nickname = $1;
	my $new_nickname = $3;

	if (defined $nick_structure{$server}{$old_nickname}){
	  if (exists $nick_structure{$server}{$old_nickname}){			# nick in buddylist?
		my $status = $nick_structure{$server}{$old_nickname};		# get old buddy status
			$nick_structure{$server}{$new_nickname} = $status;	# add changed buddyname with old status
			delete $nick_structure{$server}{$old_nickname};		# delete old buddyname
			weechat::bar_item_update($prgname);
	  }
	}
}
# buddy leaves channel (irc_in_part / irc_in_quit)
sub remove_nick{
#($nick,$name,$ip,$action,$channel) = ($args =~ /\:(.*)\!n=(.*)@(.*?)\s(.*)\s(.*)/); # maybe for future use
	my ( $data, $servername, $args ) = @_;
	my ($server) = split(/,/, $servername);					# get name from server
		my ($nickname) = ($args =~ /\:(.*)\!/);
	if (exists $nick_structure{$server}{$nickname}){			# nick in buddylist?
		$nick_structure{$server}{$nickname} = 2;			# yes. but he went offline
			weechat::bar_item_update($prgname);
	}
}
# get information from who command (irc_in2_352)
sub from_hook_who{
	my ( $data, $servername, $args ) = @_;

	my @words= split(" ",$args);						# [7] = nick
		($servername) = split(/,/, $servername);			# get name from server
		my $nickname = $words[7];
	if (exists $nick_structure{$servername}{$nickname}){			# nick in buddylist?
		my $status = 0;
		$status = 1 if (substr($words[8],0,1) eq "G");			# buddy is away
			add_to_nicktable($servername, $nickname, $status);
		weechat::bar_item_update($prgname);
	}
}
# add buddy to my structure
sub add_to_nicktable{
	my ($servername, $nickname, $status) = @_;
	$nick_structure{$servername}{$nickname} = $status;			# create structure
}
# user commands
sub settings{
	my ($getargs) = ($_[2]);
	my $servername = current_buffer_test();

	my ( $cmd, $args ) = ( $getargs =~ /(.*?)\s+(.*)/ );					# get parameters and cut cmd from nicks
		$cmd = $getargs unless $cmd;

	if ($cmd eq "list"){									# print buddylist (with status) in core buffer
	  weechat::print("",weechat::color("white")."Buddylist (" . weechat::color("green"). "Servername" . weechat::color("reset") . "." . weechat::color("lightgreen") . "Nickname" . weechat::color("reset") . weechat::color("lightred") . " (status)" . weechat::color("reset") . weechat::color("white") . "):");
	  foreach my $s ( sort keys %nick_structure ) {						# sort server (a-z)
		foreach my $n ( sort keys %{$nick_structure{$s}} ) {				# sort nicks (a-z)
		  weechat::print( ""," " . weechat::color("green") . $s . weechat::color("reset") . "." . weechat::color("lightgreen") . $n . weechat::color("reset") . weechat::color("lightred") . " (" . weechat::color($default_color_buddylist{$buddylist_level{$nick_structure{$s}{$n}}}) . $buddylist_level{$nick_structure{$s}{$n}} . weechat::color("lightred") .")");
		}
	  }
	  return weechat::WEECHAT_RC_OK;
	}

	if ($servername eq "0") {
		weechat::print("",weechat::prefix("error")."$prgname: You can't add nor del buddies in core buffer.");
		return weechat::WEECHAT_RC_OK;
	}

	if (defined $args and current_buffer_test() ne "0") {					# buddy choosed?
		foreach ( split( / +/, $args ) ) {
			if ($cmd eq "add"){
				$nick_structure{$servername}{$_} = 2;
				buddylist_save();
			}
			if ($cmd eq "del" and exists $nick_structure{$servername}{$_}){
				delete $nick_structure{$servername}{$_};
# delete servername from structure, if last nick from server was deleted
				delete $nick_structure{$servername} if (keys (%{$nick_structure{$servername}}) == 0);
				buddylist_save();
			}
		}
	}else{
		weechat::command("", "/help $prgname");						# no arguments given. Print help
	}
	weechat::bar_item_update($prgname);
	return weechat::WEECHAT_RC_OK;
}

# check for buffer. add/del function can not be used in core buffer
sub current_buffer_test{
  my $buffer_name = weechat::buffer_get_string(weechat::current_buffer(),"name");	# get current buffer name
  if ($buffer_name =~ /\./){							# format?
      my ($servername, $channelname) = split (/\./,$buffer_name);		# split
      if ($servername eq "server"){						# user in server buffer?
	return $channelname;							# yes
	}
      return $servername;							# user in channel buffer!
      }
return 0;									# in core buffer!!!
}

# check server status
sub server_check{
	if (weechat::config_get_plugin("hide.bar") eq "off"){					# get user settings
		$hide_bar = "off";								# don't hide bar
#  weechat::command("", "/bar show " . $prgname);
			return;
	}

	foreach my $s ( sort keys %nick_structure ) {						# sort server alphabetically
		my $infolist_server = weechat::infolist_get("irc_server","",$s);		# get pointer for server %s
			weechat::infolist_next($infolist_server);
		my $is_connected = weechat::infolist_integer($infolist_server,"is_connected");	# get status of connection for server (1 = connected | 0 = disconnected)
			weechat::infolist_free($infolist_server);				# don't forget to free infolist ;-)
			if ($is_connected == 1){						# one server is at least online!
				$hide_bar = "off";						# show bar
					weechat::command("", "/bar show " . $prgname);
				last;
			} else {
				$hide_bar = "on";						# hide bar
					weechat::command("", "/bar hide " . $prgname);
			}
	}
}

### read the buddylist
sub buddylist_read {
	my $buddylist = weechat::config_get_plugin("buddylist");
	return unless -e $buddylist;
	open (WL, "<", $buddylist) || DEBUG("$buddylist: $!");
	while (<WL>) {
		chomp;								# kill LF
			my ( $servername, $nickname ) = split /,|\./;		# servername,nickname (seperator could be "," or ".")
			if (not defined $nickname){
				close WL;
				weechat::print("",weechat::prefix("error")."$prgname: $buddylist is not valid or uses old format (new format: servername.nickname).");
				return;
			}
		$nick_structure{$servername}{$nickname} = 2  if length $_;	# status offline
	}
	close WL;
}
sub buddylist_save {
	my $buddylist = weechat::config_get_plugin( "buddylist" );
	open (WL, ">", $buddylist) || DEBUG("write buddylist: $!");
	foreach my $s ( sort keys %nick_structure ) {				# sortiert die Server alphabetisch
		foreach my $n ( sort keys %{$nick_structure{$s}} ) {		# sortiert die Nicks alphabetisch
			print WL "$s.$n\n";					# save as servername.nickname
		}
	}
	close WL;
}
# options changed during runntime
sub toggled_by_set{
	my ( $pointer, $option, $value ) = @_;

	if ($option eq "plugins.var.perl.$prgname.hide.server.if.buddies.offline"){
		$hide_server = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.hide.buddy.if.offline"){
		$hide_buddy = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.sort"){
		$sort = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.hide_bar"){
		$hide_bar = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.default"){
		$color_default = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.server"){
		$color_server_online = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.server.offline"){
		$color_server_offline = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.away"){
		$default_color_buddylist{"away"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.offline"){
		$default_color_buddylist{"offline"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.online"){
		$default_color_buddylist{"online"} = $value;
	}
	weechat::bar_item_update($prgname);
return weechat::WEECHAT_RC_OK;

}

# init the settings
sub init{
	if ( weechat::config_get_plugin("buddylist") eq "" ) {
		my $wd = weechat::info_get( "weechat_dir", "" );
		$wd =~ s/\/$//;
		weechat::config_set_plugin("buddylist", $wd . "/" . $default_buddylist );
	}

	if (!weechat::config_is_set_plugin("color.default")){
	  weechat::config_set_plugin("color.default", $color_default);
	}else{
	  $color_default = weechat::config_get_plugin("color.default");
	}
	if (!weechat::config_is_set_plugin("color.server")){
	  weechat::config_set_plugin("color.server", $color_server_online);
	}else{
	  $color_server_online = weechat::config_get_plugin("color.server");
	}
	if (!weechat::config_is_set_plugin("color.server.offline")){
	  weechat::config_set_plugin("color.server.offline", $color_server_offline);
	}else{
	  $color_server_offline = weechat::config_get_plugin("color.server.offline");
	}
	if (!weechat::config_is_set_plugin("hide.bar")){
	  weechat::config_set_plugin("hide.bar", $hide_bar);
	}else{
	  $hide_bar = weechat::config_get_plugin("hide.bar");
	}
	if (!weechat::config_is_set_plugin("sort")){
	  weechat::config_set_plugin("sort", $sort);
	}else{
	  $sort = weechat::config_get_plugin("sort");
	}
	if (!weechat::config_is_set_plugin("hide.server.if.buddies.offline")){
	  weechat::config_set_plugin("hide.server.if.buddies.offline", $hide_server);
	}else{
	  $hide_server = weechat::config_get_plugin("hide.server.if.buddies.offline");
	}
	if (!weechat::config_is_set_plugin("hide.buddy.if.offline")){
	  weechat::config_set_plugin("hide.buddy.if.offline", $hide_buddy);
	}else{
	  $hide_buddy = weechat::config_get_plugin("hide.buddy.if.offline");
	}
# get color settings.
	foreach my $level (values %buddylist_level){
		if (weechat::config_get_plugin("color.".$level) eq ""){
			weechat::config_set_plugin("color.".$level,
					$default_color_buddylist{$level});
		}else{
		    $default_color_buddylist{$level} = weechat::config_get_plugin("color.".$level);
		}
	}
}


# hide bar when buddylist was closed
sub shutdown{
	weechat::command("", "/bar hide " . $prgname);
}
sub DEBUG {weechat::print('', "***\t" . $_[0]);}
