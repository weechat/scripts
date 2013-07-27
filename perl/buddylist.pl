#
# Copyright (c) 2010-2013 by Nils Görs <weechatter@arcor.de>
#
# display the status and visited buffers of your buddies in a buddylist bar
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
# 1.8   : fixed: problem with temporary server
#       : added: %h variable for filename
# 1.7   : fixed: perl error when adding and removing nick
#       : fixed: perl error: Use of uninitialized value $bitlbee_service_separator (reported by gtmanfred)
#       : improved: a warning will be displayed if no filename for the buddylist is given.
# 1.6   : added: support for new option "irc.network.whois_double_nick"
# 1.5   : fixed: wrong pointer in bar_item_remove()
#       : fixed: perl error: Use of uninitialized value $nickname
# 1.4   : added: option hide.servername.in.buddylist (suggested by Cubox)
# 1.3.1 : fixed: perl error: Use of uninitialized value in string comparison (reported by ArcAngel)
# 1.3   : added: mouse support (weechat >= v0.3.6)
#       : added: nick completion for add/del
#       : improved: hide_bar function (for example after /upgrade).
#       : fixed: did action on bar in the build callback => crashed latest git
#       : fixed: typo with option "hide.bar" and "social.net.color" removed.
# 1.2.1 : fixed: bitlbee_service was not set, for new added buddy
# v1.2  : added: function "hide_bar = always" (requested by: Emralegna)
#       : added: buddies will be separated by protocol (msn/jabber etc.pp.) on bitlbee server (requested by: ArcAngel)
#       : added: options "text.online", "text.away", "text.offline" (maybe usefull for color-blind people:-) 
#       : added: function weechat_config_set_desc_plugin() (only for weechat >= v0.3.5)
# v1.1  : fixed: offline users on bitlbee were shown as away. (reported and beta-testing by javuchi)
# v1.0  : redirection implemented (needs weechat >= 0.3.4). Now, its a real buddylist
#	: new options: "check.buddies", "callback.timeout", "use.redirection", "display.original.nick"
#	: buffer-number will be displayed behind nickname (option: "color.number")
#	: buddylist will be build instandly when switching bar-position.
#	: thanks to shariebeth for beta-testing
# 0.9.4 : now using irc.server_default.away_check_max_nicks and irc.server_default.away_check
# 0.9.3 : check for JOIN signal (requested by Rupp)
# 0.9.2 : server wasn't hidden for "default" settings
#	  server will be hidden if all buddies are offline for this server (option: hide.server.if.buddies.offline (requested by TenOfTen))
#	  buddies will be hidden when offline (option: hide.buddy.if.offline (requested by TenOfTen))
#	  new function added: "list"
#	  the buddylist will be saved in a new format : servername.nickname (old format will be recognized, too)
#	  and other internal changes
# 0.9.1	: bar could not be hidden (detrate-)
#	: error message for old datafile (bazerka)
# 0.9   : servername without nicks will not be displayed in buddylist
#	  servername will be displayed in different color or will be hidden if not connected (option "color.server.offline")
#	  buddylist bar will be hidden if you are not connected to a server (option "hide.bar")
# 0.8   : - major changes - (buddylist file changed!!!)
#	  buddylist uses now server / nick structure
#         change entries in buddylist to : servername,nickname (e.g.: freenode,nils_2)
#	  or add your buddies again with the add function.
# 0.7   : nick change will be recognize
# 0.6   : nick wasn't set to offline, if buddy leave channel
# 0.5   : server information will be used now instead of nicklist
#	  reduction of cpu load (reported by ArcAngel and tigrmesh)
#	  bar will be removed if you unload the script. (requested by bazerka)
#	  help page will be displayed when you call buddylist without arguments
# 0.4   : added option "sort"
# 0.3   : remove spaces for indenting when bar position is top/bottom
#	  hook_config when settings changed.
# 0.2   : work-around for crash when searching nick in buffer without nicklist (function nicklist_search_nick) removed 
# 0.1   : initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# TODO:
# /monitor function:
# :holmes.freenode.net 730 * :weechatter!~nils@mue-99-999-999-999.dsl.xxxxx.de

use strict;

my $prgname		= "buddylist";
my $version		= "1.8";
my $description		= "display status from your buddies a bar-item.";

# -------------------------------[ config ]-------------------------------------
my $default_buddylist	= "%h/buddylist.txt";
my %buddylist_level = (0 => "online", 1 => "away", 2 => "offline");
my %default_color_buddylist = ("online" => "yellow",
			       "away"    => "cyan",
			       "offline"    => "blue");

my %default_options = (	"position"		=>	"top",
                        "hide_bar"		=>	"on",		# hide buddylist bar when all servers are offline
                        "hide_server"		=>	"off",		# hide server if no buddy is online on this server
                        "hide_buddy"		=>	"off",		# hide buddy when offline
                        "buddy_on_server"	=>	"on",		# show connected buddy (on server and not channel)
                        "buddy_on_server_color"	=>	"lightgreen",	# color for buddy who is connected to server
                        "sort"			=>	"default",	# sort method
                        "color_default"		=>	"default",
                        "color_server_online"	=>	"white",
                        "color_server_offline"	=>	"hide",
                        "color_number"		=>	"lightred",
                        "show_query"		=>	"on",
                        "check_buddies"		=>	"20",		# delay (in seconds)
                        "callback_timeout"	=>	"60",		# delay (in seconds)
                        "use_redirection"	=>	"on",
                        "display_original_nick"	=>	"off",
                        "display_social_net"    =>      "on",
                        "display_social_net_color"=>    "yellow",
                        "text_online"           =>      "",
                        "text_away"             =>      "",
                        "text_offline"          =>      "",
                        "text_color"            =>      "white",
                        "hide_servername_in_buddylist"       =>      "off",

);
my %mouse_keys = ("\@item(buddylist):button1*"                                  => "hsignal:buddylist_mouse",
                  "\@item(buffer_nicklist)>item(buddylist):button1-gesture-*"   => "hsignal:buddylist_mouse",
                  "\@chat(*)>item(buddylist):button1-gesture-*"                 => "hsignal:buddylist_mouse",
                  "\@item(buddylist):button1-gesture-*"                         => "hsignal:buddylist_mouse");

my $debug_redir_out	= "off";

# ------------------------------[ internal ]-----------------------------------
my %Hooks		= ();					# space for my hooks
my %buddies		= ();					# to store the buddylist with status for each nick
my %nick_structure	= ();					# to store servername, nickname and status
my $default_version     = 0;                                    # minimum version (0.3.4)
my $bar_hidden          = "off";                                # status of bar
my $servertest          = 0;                                    # 0 = no server connected
my @buddylist_focus = ();

#$VAR1 = {
#       'freenode' =>   {
#                               'nils_2'        =>      'status'        =>      'online',
#                               'nil2_2'        =>      'buffer'        =>      '1,2,3',
#                               'nil2_2'        =>      'counter'       =>      0 or 1,
#                               'nil2_2'        =>      'buf_name'      =>      "#weechat #weechat-fr",
#                               'nil2_2'        =>      'bitlbee_service'=>       "msn",
#                               'nick_name'     =>      'status'        =>      'offline',
#                               'nick_name'     =>      'buffer'        =>      '',
#                               'nick_name'     =>      'counter'       =>      0 or 1,
#                               'nick_name'     =>      'buf_name'      =>      "#weechat #weechat-fr",
#                               'nick_name'     =>      'bitlbee_service'=>       "jabber",
#                               'nick_name2'    =>      'status'        =>      'online',
#                               'nick_name2'    =>      'buffer'        =>      '3,4',
#                               'nick_name2'    =>      'counter'       =>      0 or 1,
#                               'nick_name2'    =>      'buf_name'      =>      "#weechat #weechat-fr",
#                               'nick_name2'    =>      'bitlbee_service'=>      "facebook",
#                       },
#       'fu-berlin' =>  {
#                               'nils_2'        =>      'status'        =>      'away',
#                               'nils_2'        =>      'buffer'        =>      '4,5',
#                               'nil2_2'        =>      'counter'       =>      0 or 1,
#                               'nil2_2'        =>      'buf_name'      =>      "#amiga #motorrad",
#                               'nils_2'        =>      'bitlbee_service'=>      "",
#                       }
#       };

# -------------------------------[ main ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
		"GPL3", $description, "shutdown", "");
my $weechat_version = "";
init();
buddylist_read();

weechat::bar_item_new($prgname, "build_buddylist", "");
weechat::bar_new($prgname, "1", "0", "root", "", "left", "horizontal",
                 "vertical", "0", "0", "default", "default", "default", "1",
                 $prgname);

weechat::hook_signal("buffer_*", "buddylist_signal_buffer", "");


weechat::hook_signal("*,irc_in2_352", "from_hook_who","");			# RFC command with use,channel,status etc..

weechat::hook_signal("*,irc_in_part", "remove_nick", "");
weechat::hook_signal("*,irc_in_quit", "remove_nick", "");
weechat::hook_signal("*,irc_in_join", "add_nick", "");

weechat::hook_signal("buffer_closing", "buffer_closing", "");
#weechat::hook_signal("buffer_moved", "buffer_moved", "");


weechat::hook_signal("*,irc_in_nick", "nick_changed", "");
weechat::hook_signal("irc_server_connected", "server_connected", "");
weechat::hook_signal("irc_server_disconnected", "server_disconnected", "");
weechat::hook_config("plugins.var.perl.$prgname.*", "toggled_by_set", "");	# buddylist options changed?
weechat::hook_completion("perl_buddylist", "buddylist completion", "buddy_list_completion_cb", "");

weechat::hook_signal("upgrade_ended", "buddylist_upgrade_ended", "");

if ($weechat_version >= 0x00030600){
  weechat::hook_focus($prgname, "hook_focus_buddylist", "");
  weechat::hook_hsignal("buddylist_mouse","buddylist_hsignal_mouse", "");
  weechat::key_bind("mouse", \%mouse_keys);
}


hook_timer_and_redirect() if ($default_options{check_buddies} ne "0" and $default_options{use_redirection} eq "on");

weechat::hook_command($prgname, $description,
                "<add>[nick_1 [... nick_n]] | <del>[nick_1 [... nick_n]]", 

                "<add> [nick(s)] add nick(s) to the buddylist\n".
                "<del> [nick(s)] delete nick(s) from the buddylist\n".
                "<list> show buddylist\n".
                "\n".
                "Options:\n".
                "'plugins.var.perl.buddylist.buddylist'            : path/file-name to store your buddies. \"%h\" will be replaced by WeeChat home (by default: ~/.weechat)\n".
                "\n".
                "'plugins.var.perl.buddylist.color.default         : fall back color. (default: standard weechat color)\n".
                "'plugins.var.perl.buddylist.color.online'         : color for " . weechat::color($default_color_buddylist{online}) . "online " . weechat::color("reset") . "buddies.\n".
                "'plugins.var.perl.buddylist.color.away'           : color for " . weechat::color($default_color_buddylist{away}) . "away " . weechat::color("reset") . "buddies.\n".
                "'plugins.var.perl.buddylist.color.offline'        : color for " . weechat::color($default_color_buddylist{offline}) . "offline " . weechat::color("reset") . "buddies.\n".
                "'plugins.var.perl.buddylist.color.server'         : color for " . weechat::color($default_options{color_server_online}) . "servername" . weechat::color("reset") . ".\n".
                "'plugins.var.perl.buddylist.color.server.offline' : color for disconnected server (default: hide).\n".
                "'plugins.var.perl.buddylist.color.number'         : color for channel number (default: " . weechat::color($default_options{color_number}) . "lightred" . weechat::color("reset") ."). If empty, channel list option is off.\n".
                "\n".
                "'plugins.var.perl.buddylist.show.query'           : displays a query buffer in front of the channel list.\n".
                "\n".
                "'plugins.var.perl.buddylist.hide.server.if.buddies.offline': hides server when all buddies are offline for this server (default: off).\n".
                "'plugins.var.perl.buddylist.hide.buddy.if.offline': hide buddy if offline (default: off).\n".
                "'plugins.var.perl.buddylist.buddy.on.server'      : show buddy who is connected to a server, but not visiting the same channel(s) (default: on).\n".
                "'plugins.var.perl.buddylist.buddy.on.server.color': color for online buddy but not visiting the same channel(s) (default: " . weechat::color($default_options{buddy_on_server_color}) . "lightgreen" . weechat::color("reset") .").\n".
                "'plugins.var.perl.buddylist.hide.bar'             : hides $prgname bar when all servers with added buddies are offline (default: on).\n".
                "                                          always  : $prgname bar will be hidden (for example if you want to add item 'buddylist' to 'weechat.bar.status.items'\n".
                "                                          off     : $prgname bar will not be hidden.\n".
                "\n".
                "'plugins.var.perl.buddylist.check.buddies'        : time in seconds to send a /whois request to server. Be careful not to flood server (default: 20).\n".
                "'plugins.var.perl.buddylist.callback.timeout'     : time in seconds to wait for answer from server. (default: 60).\n".
                "'plugins.var.perl.buddylist.display.original.nick': display original nickname even if buddy changed his /nick (you have to add new nick to buddylist) (default: off).\n".
                "\n".
                "'plugins.var.perl.buddylist.sort'                 : sort method for buddylist (default or status).\n".
                "                                          default : $prgname will be sort by nickname\n".
                "                                          status  : $prgname will be sort by status (online, away, offline)\n".
                "\n".
                "'plugins.var.perl.buddylist.display.social.net'   : using bitlbee, buddies will be sorted in sublists with social-network name (eg. msn/jabber/facebook)(default: on)\n".
                "'plugins.var.perl.buddylist.display.social.net.color': color for social-network name (default: yellow)\n".
                "\n".
                "'plugins.var.perl.buddylist.text.color'           : color for optional online/away/offline-text in buddylist (default: white)\n".
                "'plugins.var.perl.buddylist.text.online'          : optional online text in buddylist (sort method has to be 'status')\n".
                "'plugins.var.perl.buddylist.text.away'            : optional away text in buddylist (sort method has to be 'status')\n".
                "'plugins.var.perl.buddylist.text.offline'         : optional offline text in buddylist (sort method has to be 'status')\n".
                "\n".
                "'plugins.var.perl.buddylist.use.redirection'      : using redirection to get status of buddies (needs weechat >=0.3.4) (default: on).\n".
                "\n\n".
                "Mouse-support (standard key bindings):\n".
                "  click left mouse-button on buddy to open a query buffer.\n".
                "  add a buddy by dragging a nick with left mouse-button from nicklist or chat-area and drop on buddylist.\n".
                "  remove a buddy by dragging a buddy with left mouse-button from buddylist and drop it on any area.\n".
                "\n\n".
                "Troubleshooting:\n".
                "If buddylist will not be refreshed in nicklist-mode, check the following WeeChat options:\n".
                "'irc.server_default.away_check'          : interval between two checks, in minutes. (has to be >= 1 (default:0)).\n".
                "'irc.server_default.away_check_max_nicks': channels with high number of nicks will not be checked (default: 25).\n".
                "\n\n".
                "name of buddy has to be written 'case sensitive' (it's recommended to use nick-completion or to drag'n'drop buddy with mouse).\n".
                "\n\n".
                "Examples:\n".
                "  Add buddy (nils) to buddylist (server of current buffer will be used):\n".
                "    /$prgname add nils\n".
                "  Delete buddy (nils) from buddylist:\n".
                "    /$prgname del nils (server of current buffer will be used)\n",
                "add %(nick)|%*||".
                "del %(perl_buddylist)|%*||".
                "list %-", "settings_cb", "");
server_check();
return weechat::WEECHAT_RC_OK;


sub buddylist_upgrade_ended
{
    server_check();
    return weechat::WEECHAT_RC_OK;
}

# weechat connected to a server (irc_server_connected)
sub server_connected
{
    server_check();
    weechat::bar_item_update($prgname);
    return weechat::WEECHAT_RC_OK;
}

# weechat disconnected from server (irc_server_disconnected)
sub server_disconnected
{
    my $server = $_[2];
    set_nick_status_for_one_server("2",$server);                                                # all nicks off for server
    server_check();
    weechat::bar_item_update($prgname);
    return weechat::WEECHAT_RC_OK;
}


sub set_nick_status_for_one_server
{
    my ($status, $server) = @_;

    foreach my $nickname (%{$nick_structure{$server}} )
    {
        if (exists $nick_structure{$server}{$nickname})                                         # set buddy to offline
        {
            $nick_structure{$server}{$nickname}{status} = $status;
            if ($status eq "2")
            {
                $nick_structure{$server}{$nickname}{buffer} = "";
                $nick_structure{$server}{$nickname}{buf_name} = "";
            }elsif($status eq "0")                                                              # set buddy online
            {
                $nick_structure{$server}{$nickname}{buffer} = "()";
            }
        }
    }
}

sub buffer_closing
{
    my ($signal, $callback, $callback_data) = @_;
    weechat::bar_item_update($prgname);
    return weechat::WEECHAT_RC_OK;
}
#    my $infolist_buf_closing = weechat::infolist_get("buffer",$callback_data,"");		# get pointer from closing buffer
#       weechat::infolist_next($infolist_buf_closing);
#       my $num_closing_buf = weechat::infolist_integer($infolist_buf_closing,"number");	# get number of closing buffer
#       my $server_name = weechat::infolist_string($infolist_buf_closing,"name");
#       my $buffer_name_short = weechat::infolist_string($infolist_buf_closing,"short_name");
#       weechat::infolist_free($infolist_buf_closing);
#       $server_name =~ s/\.$buffer_name_short//;

#	my $buffer_number = "";
#	my $str = "";
#	my $infolist_buffer = weechat::infolist_get("buffer","","*");
#	while ( weechat::infolist_next($infolist_buffer) ){
#	  if ( index (weechat::infolist_string($infolist_buffer,"name"), $server_name) ne "-1" and weechat::infolist_pointer($infolist_buffer,"pointer") ne $callback_data ){
#	      $buffer_number = weechat::infolist_string($infolist_buffer,"short_name");		# get short_name of buffer
#	      $str .= $buffer_number . " ";
#	  }
#	}
#	weechat::infolist_free($infolist_buffer);
#	$str =~ s/^\s+//g;									# delete last space

#    foreach my $nickname ( sort keys %{$nick_structure{$server_name}} ) {			# sortiert die Nicks alphabetisch
#        my $status = $nick_structure{$server_name}{$nickname}{status};
#        next if ( not defined $status or $status eq "2" );
#        my $buf_name = $nick_structure{$server_name}{$nickname}{buf_name};
#        next if ( not defined $buf_name );

#        if ( index($buf_name,$buffer_name_short) ne "-1" or $buf_name ne "" or $buf_name ne "()" ){
#            $buf_name =~ s/$buffer_name_short//;
#            $buf_name =~ s/\s+$//g;								# delete last space
#            if ($buf_name eq ""){								# no more buffer
#                $nick_structure{$server_name}{$nickname}{buf_name} = "";
#                $nick_structure{$server_name}{$nickname}{buffer} = "";
#            }else{
#                $nick_structure{$server_name}{$nickname}{buf_name} = "";
#                $nick_structure{$server_name}{$nickname}{buffer} = "";
#                check_for_channels($server_name, $nickname, $buf_name);
#            }
#        }
#    }
#weechat::bar_item_update($prgname);
#return weechat::WEECHAT_RC_OK;


sub buffer_moved
{
    my ($signal, $callback, $callback_data) = @_;
    weechat::print("","signal: " . $signal);
    weechat::print("","callback: " . $callback);
    weechat::print("","callback_data: " . $callback_data);
    return weechat::WEECHAT_RC_OK;
}

# build buddylist in bar
my $str = "";
my $number;
my $bitlbee_service_separator = "";
my $bitlbee_service_separator_copy = "";
sub build_buddylist{
        $str = "";
        $number = 0;
        @buddylist_focus = ();

# crashes weechat...
#        if ( $default_options{hide_bar} eq "on" or $default_options{hide_bar} eq "always" ){    # hide buddylist bar?
#          my $servertest = server_check();                                                      # check for server
#          return $str if ( $servertest == 0 );                                                  # no server with buddies online!
#        }

        my $visual = " ";                                                       # placeholder after servername
        my $cr = "\n";
        $visual  = $cr if (($default_options{position} eq "left") || ($default_options{position} eq "right"));

# get bar position (left/right/top/bottom) and sort (default/status)
	my $option = weechat::config_get("weechat.bar.$prgname.position");
	if ($option ne ""){
		$default_options{position} = weechat::config_string($option);
	}

	if ($default_options{sort} eq "status"){						# use sort option "status"
		foreach my $s ( sort keys %nick_structure ) {
                  $bitlbee_service_separator = "";
                  $bitlbee_service_separator_copy = "";
			if (keys (%{$nick_structure{$s}}) eq "0"){				# check out if nicks exists for server in nick_structure
				next;								# no nick for server. jump to next server
			}

                  # sort list by status (online => away => offline) for internal use.
                  my ($n) = ( sort { $nick_structure{$s}{$a}->{status} <=> $nick_structure{$s}{$b}->{status}} keys %{$nick_structure{$s}} );
                  $nick_structure{$s}{$n}{bitlbee_service} = "" if ( not defined $nick_structure{$s}{$n}{bitlbee_service} );
                  if ($nick_structure{$s}{$n}{status} eq "2" and $default_options{hide_server} eq "on"){	# status from first buddy in list!
		      next;									# first sorted buddy is offline (2)
		  }

			my $color_server = get_server_status($s);				# get server color
			if ($color_server eq "1"){
			  next;									# hide server if result = 1
			}
                        if ($default_options{hide_servername_in_buddylist} ne "on"){
                            $str .= weechat::color($color_server) . $s . ":" . $visual;		# add servername ($s ;) to buddylist
                        }
                        add_buddy_focus("","","");                                              # create focus for servername

# sorted by status first, then bitlbee_service and nick case insensitiv at least
#                              foreach my $n (sort { $nick_structure{$s}{$a}->{status} cmp $nick_structure{$s}{$b}->{status}} (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}})))){
                              
                              my $status_output = "";
                              my $status_output_copy = "";
                              foreach my $n (sort { $nick_structure{$s}{$a}->{status} cmp $nick_structure{$s}{$b}->{status}} (sort { $nick_structure{$s}{$a}->{bitlbee_service} cmp $nick_structure{$s}{$b}->{bitlbee_service}} (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}})) ) ) ){
                                # write status to nicklist (optional!!)
                                $status_output = $nick_structure{$s}{$n}{status};
                                if ( $nick_structure{$s}{$n}{status} == 0 and $status_output ne $status_output_copy and $default_options{text_online} ne ""){
                                  $str .= weechat::color($default_options{text_color}) . $default_options{text_online} . weechat::color("reset") .$visual;
                                  add_buddy_focus("","","");
                                }elsif ( $nick_structure{$s}{$n}{status} == 1 and $status_output ne $status_output_copy and $default_options{text_away} ne ""){
                                  $str .= weechat::color($default_options{text_color}) . $default_options{text_away} . weechat::color("reset") .$visual;
                                  add_buddy_focus("","","");
                                }elsif ( $nick_structure{$s}{$n}{status} == 2 and $status_output ne $status_output_copy and $default_options{text_offline} ne "" and $default_options{hide_buddy} eq "off"){
                                  $str .= weechat::color($default_options{text_color}) . $default_options{text_offline} . weechat::color("reset") .$visual;
                                  add_buddy_focus("","","");
                                }
                                  $status_output_copy = $status_output;

                                # write each bitlbee_service only once
                                $nick_structure{$s}{$n}{bitlbee_service} = "" if ( not defined $nick_structure{$s}{$n}{bitlbee_service} );
                                $bitlbee_service_separator = $nick_structure{$s}{$n}{bitlbee_service};
                                if ( $bitlbee_service_separator ne "" and $bitlbee_service_separator_copy ne $bitlbee_service_separator ){
                                  $str .= weechat::color($default_options{display_social_net_color}) . "(" . $bitlbee_service_separator . ") " . $visual;
                                  add_buddy_focus("","","");
                                }
                                createoutput($s,$n);
                                $bitlbee_service_separator_copy = $bitlbee_service_separator;
                              }
                }

	} elsif ($default_options{sort} ne "status") {						# use sort option "default"
		foreach my $s ( sort keys %nick_structure ) {					# sort server alphabetically
                  $bitlbee_service_separator = "";
                  $bitlbee_service_separator_copy = "";
			if (keys (%{$nick_structure{$s}}) eq "0"){				# check out if nicks exists for server
				next;								# no nick for server. jump to next server
			}
		# sort list by status (from online, away, offline)
		my ($n) = ( sort { $nick_structure{$s}{$a}->{status} <=> $nick_structure{$s}{$b}->{status}} keys %{$nick_structure{$s}} );
		if ($nick_structure{$s}{$n}{status} eq "2" and $default_options{hide_server} eq "on"){	# status from first buddy in list!
		  next;										# first sorted buddy is offline (2)
		}
			my $visual = " ";							# placeholder after servername
				my $cr = "\n";
			$visual  = $cr if (($default_options{position} eq "left") || ($default_options{position} eq "right"));

			my $color_server = get_server_status($s);                               # get server color
			if ($color_server eq "1"){
			  next;                                                                 # hide server if result = 1
			}
                        if ($default_options{hide_servername_in_buddylist} ne "on"){
                            $str .= weechat::color($color_server) . $s . ":" . $visual;         # add servername ($s ;) to buddylist
                        }

                        add_buddy_focus("","","");                                              # create focus for servername

#                                foreach my $n (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}} ))){ # sort by name case insensitiv
                                # first sort by bitlbee_service and then name case insensitiv
                                foreach my $n (sort { $nick_structure{$s}{$b}->{bitlbee_service} cmp $nick_structure{$s}{$a}->{bitlbee_service}} (sort {uc($a) cmp uc($b)} (sort keys(%{$nick_structure{$s}})) ) ){
                                  # write each bitlbee_service only once
                                  $nick_structure{$s}{$n}{bitlbee_service} = "" if ( not defined $nick_structure{$s}{$n}{bitlbee_service} );
                                  $bitlbee_service_separator = $nick_structure{$s}{$n}{bitlbee_service};
                                  if ( $bitlbee_service_separator ne "" and $bitlbee_service_separator_copy ne $bitlbee_service_separator ){
                                    $str .= weechat::color($default_options{display_social_net_color}) . "(" . $bitlbee_service_separator . ") " . $visual;
                                    add_buddy_focus("","","");
                                  }
                                  createoutput($s,$n);
                                  $bitlbee_service_separator_copy = $bitlbee_service_separator;
                                }
                }
        }
        if ($str eq ""){
	    my $network_away_check = weechat::config_integer(weechat::config_get("irc.server_default.away_check"));
	    if ($network_away_check == 0 and $default_options{use_redirection} ne "on"){
		$str = "value from option \"irc.server_default.away_check\" is 0.".$visual."It has to be >= 1 or you have to use option".$visual."\"plugins.var.perl.buddylist.use.redirection = on\".";
	    }else{
                return $str = "Not connected to a server..." if ( $servertest == 0 );
		return $str = "Searching for buddies,".$visual."please wait..." if ($network_away_check == 0);
		$str = "Please wait, building buddylist".$visual."(this could take $network_away_check minutes)...".$visual."probably there are no buddies in your".$visual."buddylist for connected server,".$visual."or you are not connected to a server".$visual."or your buddies are all offline";
	    }
	}
	return $str;
}

# get status from server and color the servername (or hide it)
sub get_server_status{
my $server = $_[0];
	my $infolist_server = weechat::infolist_get("irc_server","",$server);			# get pointer for server %s
	weechat::infolist_next($infolist_server);
	my $is_connected = weechat::infolist_integer($infolist_server,"is_connected");		# get status of connection for server (1 = connected | 0 = disconnected)
	weechat::infolist_free($infolist_server);						# don't forget to free infolist ;-)
		if ($is_connected == 0){							# 0 = not connected
				if ($default_options{color_server_offline} eq "hide"){		# hide offline server?
					return 1;						# yes!
				}
		$default_options{color_server_offline} = $default_options{color_default} if ($default_options{color_server_offline} eq "");
		return $default_options{color_server_offline};					# color for server offline
		}
$default_options{color_server_online} = $default_options{color_default} if ($default_options{color_server_online} eq "");# fall back color if color_server = ""
return $default_options{color_server_online};							# color for server online
}

# for mouse support, create a focus list
sub add_buddy_focus{
my ($server,$nick, $status) = ($_[0],$_[1],$_[2]);
          my $buddy_struct;
          my %buddy_struct;
          my $key;

          $key = sprintf("%08d", $number);

          if ($nick ne "" and $server ne ""){                                                   # a legal buddy with server
            $buddy_struct->{"status"} = $status;
            $buddy_struct->{"nick"} = $nick;
            $buddy_struct->{"server"} = $server;
            $buddy_struct{$key} = $buddy_struct;
            push(@buddylist_focus, $buddy_struct{$key});
          }else{                                                                                # create a dummy
           undef $buddy_struct;
           $buddy_struct{$key} = $buddy_struct;
           push(@buddylist_focus, $buddy_struct{$key});
          }
          $number++;
}

sub createoutput{
my ($server,$nick) = ($_[0],$_[1]);
my $status = $nick_structure{$server}{$nick}{status};                                           # get buddy status
$status = 2 if (not defined $status);                                                           # buddy is offline
my $bitlbee_service = $nick_structure{$server}{$nick}{bitlbee_service};                         # get bitlbee_service name or "" if none

my $buffer_number = $nick_structure{$server}{$nick}{buffer};                                    # get buffers, buddy is currently in
$buffer_number = "" if (not defined $buffer_number);                                            # does variable is defined?

        if ($status eq "2" and $default_options{hide_buddy} eq "on"){                           # buddy is offline
                                                                                                # do not create focus, if buddy is not displayed in item!
#          add_buddy_focus($server,$nick,$status);                                               # create focus
          $str .= "";
        }else{                                                                                  # get color for away/online

          add_buddy_focus($server,$nick,$status);                                               # create focus

          my $cr = "\n";
          my $color = $default_options{color_default};
          $color = "default" if ($color eq "" or not defined $color);
          $color = $default_color_buddylist{$buddylist_level{$status}};

          ### visual settings for left/right or top/bottom
          my $visual = " ";                                                                     # placeholder
          my $move_r = "";                                                                      # move it to right
            if (($default_options{position} eq "left") || ($default_options{position} eq "right")){
              $visual  = $cr;
              $move_r  = "  ";
              $move_r  = "" if ($default_options{hide_servername_in_buddylist} eq "on")
            }

          return $str .= weechat::color($color) . $move_r . "$nick" . $visual if ($buffer_number eq "" or $default_options{color_number} eq "");

          # print nick with channel number ( "()" = online without channel, "" = offline )
          return $str .= weechat::color($color) . $move_r . "$nick" .
                          weechat::color("reset") . "(" .
                          weechat::color($default_options{color_number}).
                          $buffer_number .
                          weechat::color("reset") . ")" . $visual if ($buffer_number ne "()");

          if ($default_options{buddy_on_server} eq "on" and $buffer_number eq "()" or $buffer_number eq ""){# option "buddy_on_server" = on ?
            return $str .= weechat::color($default_options{buddy_on_server_color}) . $move_r . "$nick" . weechat::color("reset") . $visual if ($status eq 0);# buddy online?
            return $str .= weechat::color($color) . $move_r . "$nick" . weechat::color("reset") . $visual if ($status eq 1); # buddy away?
          }
        }
}

# buddy changed his nick (irc_in_nick)
sub nick_changed{
	my ($blank, $servername, $args) = @_;

	return weechat::WEECHAT_RC_OK if ( $default_options{use_redirection} eq "on" );		# do not rename nick in redirection_mode!!!


	my ($server) = split(/,/, $servername);							# get name from server
		$args =~ /\:(.*)\!(.*)\:(.*)/;
	my $old_nickname = $1;
	my $new_nickname = $3;

	if (defined $nick_structure{$server}{$old_nickname} and exists $nick_structure{$server}{$old_nickname}){
		my $status = $nick_structure{$server}{$old_nickname}{status};		# get old buddy status
			$nick_structure{$server}{$new_nickname}{status} = $status;	# add /nick buddy with old status
			delete $nick_structure{$server}{$old_nickname};                 # delete old buddyname

			weechat::bar_item_update($prgname);
	}
}

sub add_nick{
    my ( $data, $servername, $args ) = @_;
    my ($server) = split(/,/, $servername);                                 # get name from server
        my ($nickname) = ($args =~ /\:(.*)\!/);

    if (defined $nick_structure{$server}{$nickname} and exists $nick_structure{$server}{$nickname}){                        # nick in buddylist?
        $nick_structure{$server}{$nickname}{status} = 0;                    # create structure
        $nick_structure{$server}{$nickname}{bitlbee_service} = "";
        weechat::bar_item_update($prgname);
    }
}

# buddy leaves channel (irc_in_part / irc_in_quit)
sub remove_nick{
#($nick,$name,$ip,$action,$channel) = ($args =~ /\:(.*)\!n=(.*)@(.*?)\s(.*)\s(.*)/); # maybe for future use
    my ( $data, $servername, $args ) = @_;
    my ($server) = split(/,/, $servername);                                 # get name from server
            my ($nickname) = ($args =~ /\:(.*)\!/);


    if (defined $nick_structure{$server}{$nickname} and exists $nick_structure{$server}{$nickname}){                        # nick in buddylist?
        $nick_structure{$server}{$nickname}{status} = 2;                # yes and he left channel
        $nick_structure{$server}{$nickname}{buf_name} = "";
        $nick_structure{$server}{$nickname}{buffer} = "";
        $nick_structure{$server}{$nickname}{counter} = "";
        $nick_structure{$server}{$nickname}{bitlbee_service} = "";
        weechat::bar_item_update($prgname);
    }
}

# get information from who command (irc_in2_352)
#:anthony.freenode.net 352 nils_2 #channelname debian-tor gateway/tor-sasl/nils2/x-72512466 anthony.freenode.net nils_2 H :0 nils
#1                     2   3      4            5                                            6                    7      8 9  10
#
sub from_hook_who{
    my ( $data, $servername, $args ) = @_;

    my @words = split(" ",$args);                               # [7] = nick
    ($servername) = split(/,/, $servername);                    # get name from server
    my $nickname = $words[7];

    return if (not defined $nickname);

    if (exists $nick_structure{$servername}{$nickname}){        # nick in buddylist?
        my $status = 0;                                         # 0 = offline
        $status = 1 if (substr($words[8],0,1) eq "G");          # buddy is away (1)
        add_to_nicktable($servername, $nickname, $status);
        weechat::bar_item_update($prgname);
    }
}

# add buddy to my structure
sub add_to_nicktable{
	my ($servername, $nickname, $status) = @_;
	$nick_structure{$servername}{$nickname}{status} = $status;		# create structure
}

# user commands
sub settings_cb{
    my ($data, $ptr_buffer, $getargs) = ($_[0], $_[1], $_[2]);

    if ($getargs eq "")
    {
        weechat::command("", "/help $prgname");                                 # no arguments given. print help
        return weechat::WEECHAT_RC_OK;
    }

    my $localvar_name = weechat::buffer_get_string($ptr_buffer, "localvar_name");
    my $localvar_servername = weechat::buffer_get_string($ptr_buffer, "localvar_server");
    my $localvar_channelname = weechat::buffer_get_string($ptr_buffer, "localvar_channel");
    my $localvar_type = weechat::buffer_get_string($ptr_buffer, "localvar_type");
#    my $localvar_plugin = weechat::buffer_get_string($ptr_buffer, "localvar_plugin");

    my ( $cmd, $args ) = ( $getargs =~ /(.*?)\s+(.*)/ );                        # get parameters and cut cmd from nicks
    $cmd = $getargs unless $cmd;

    if ($cmd eq "list")                                                        # print buddylist (with status) in core buffer
    {
        weechat::print("",weechat::color("white")."Buddylist:\n" . weechat::color("green"). "Servername" . weechat::color("reset") . "." . weechat::color("lightgreen") . "Nickname" . weechat::color("lightred") . " (status)" . weechat::color("reset") . " ==> Channelname:");
        foreach my $s ( sort keys %nick_structure )                             # sort server (a-z)
        {
            foreach my $n ( sort keys %{$nick_structure{$s}} )                  # sort nicks (a-z)
            {
                my $show_buffer = "";
                my $show_bitlbee_service = "";
                $show_buffer = "  ==> " . $nick_structure{$s}{$n}{buf_name} if (defined $nick_structure{$s}{$n}{buf_name} and $nick_structure{$s}{$n}{buf_name} ne "");
                $show_bitlbee_service = " (" . $nick_structure{$s}{$n}{bitlbee_service} .")" if (defined $nick_structure{$s}{$n}{bitlbee_service} and $nick_structure{$s}{$n}{bitlbee_service} ne "");
                weechat::print( ""," "
                . weechat::color("green")
                . $s . weechat::color("reset")
                . "."
                . weechat::color("lightgreen")
                . $n
                . weechat::color("reset")
                . $show_bitlbee_service
                # status
                . weechat::color("lightred")
                . " (" . weechat::color($default_color_buddylist{$buddylist_level{$nick_structure{$s}{$n}{status}}})
                . $buddylist_level{$nick_structure{$s}{$n}{status}}
                . weechat::color("lightred") . ")"
                . weechat::color("reset")
                . $show_buffer);
            }
        }
        return weechat::WEECHAT_RC_OK;
    }

    if ( $localvar_type ne "channel" and $localvar_type ne "private" and $localvar_type ne "server" )
    {
        weechat::print("",weechat::prefix("error")."$prgname: You can add/del buddies only in channel/server/private buffers.");
        return weechat::WEECHAT_RC_OK;
    }
    if (defined $args)
    {
        foreach ( split( / +/, $args ) )                                              # more than one nick?
        {
            if ($cmd eq "add")
            {
                $nick_structure{$localvar_servername}{$_}{status} = 2;
                $nick_structure{$localvar_servername}{$_}{bitlbee_service} = "";
                buddylist_save();
            }
            if ($cmd eq "del" and exists $nick_structure{$localvar_servername}{$_})
            {
                delete $nick_structure{$localvar_servername}{$_};
# delete servername from structure, if last nick from server was deleted
                delete $nick_structure{$localvar_servername} if (keys (%{$nick_structure{$localvar_servername}}) == 0);
                buddylist_save();
            }
        }
    }
    else
    {
        weechat::command("", "/help $prgname");                                         # no arguments given. Print help
    }
    weechat::bar_item_update($prgname);
    return weechat::WEECHAT_RC_OK;
}

# check server status for option hide_bar (to hide or show bar)
# TODO infolist fails using /upgrade
sub server_check{
  $servertest = 0;
# check if at least one server is online

	foreach my $s ( sort keys %nick_structure ) {						# sort server alphabetically
                my $infolist_server = weechat::infolist_get("irc_server","",$s);                # get pointer for server %s
		weechat::infolist_next($infolist_server);
		my $is_connected = weechat::infolist_integer($infolist_server,"is_connected");	# get status of connection for server (1 = connected | 0 = disconnected)
                weechat::infolist_free($infolist_server);                                       # don't forget to free infolist ;-)
			if ($is_connected == 1){
			  $servertest = 1;                                                      # one server is at least online!
			  last;
			}
	}
	if ( $servertest == 0 and $default_options{hide_bar} ne "off" ){                         # no server with buddies
          weechat::command("", "/bar hide " . $prgname);
          $bar_hidden = "on";
        }elsif ( $default_options{hide_bar} eq "off" ){
          weechat::command("", "/bar show " . $prgname);
          $bar_hidden = "off";
        }elsif ( $servertest == 1 and $default_options{hide_bar} eq "always" ){
          weechat::command("", "/bar hide " . $prgname);
          $bar_hidden = "on";
        }elsif ($servertest == 1 and $default_options{hide_bar} eq "on" ){
          weechat::command("", "/bar show " . $prgname);
          $bar_hidden = "off";
        }
return $servertest;
}

# /query -server <internal servername> <nick>
sub buddy_completer{
return weechat::WEECHAT_RC_OK;
}

### read the buddylist
sub buddylist_read
{
    my $buddylist = weechat_dir();
    if ($buddylist eq "")
    {
        weechat::print("","Please set a valid filename : /set plugins.var.perl.".$prgname.".buddylist");
        return;
    }
    return unless -e $buddylist;
    open (WL, "<", $buddylist) || DEBUG("$buddylist: $!");
    while (<WL>)
    {
        chomp;                                                              # kill LF
        # search for last "." or "," in buddylist.txt
        # server.nick or irc.temporary.server.nick
        my $cut_here = rindex($_,".");
        $cut_here = rindex($_,",") if ($cut_here == -1);
        if ($cut_here == -1)
        {
            close WL;
            weechat::print("",weechat::prefix("error")."$prgname: $buddylist is not valid or uses old format (new format: servername.nickname).");
            return;
        }
        my $servername = substr( $_, 0, $cut_here);
        my $nickname = substr( $_,$cut_here + 1);
        if (not defined $nickname)
        {
            close WL;
            weechat::print("",weechat::prefix("error")."$prgname: $buddylist is not valid or uses old format (new format: servername.nickname).");
            return;
        }
        $nick_structure{$servername}{$nickname}{status} = 2  if length $_;	# status offline
        $nick_structure{$servername}{$nickname}{bitlbee_service} = "";
    }
    close WL;
}
sub buddylist_save {
	my $buddylist = weechat_dir();
        if ($buddylist eq "")
        {
            weechat::print("","Please set a valid filename : /set plugins.var.perl.buddylist.buddylist");
            return;
        }
	open (WL, ">", $buddylist) || DEBUG("write buddylist: $!");
	foreach my $s ( sort keys %nick_structure ) {				# sortiert die Server alphabetisch
		foreach my $n ( sort keys %{$nick_structure{$s}} ) {		# sortiert die Nicks alphabetisch
			print WL "$s.$n\n";					# save as servername.nickname
		}
	}
	close WL;
}

# changes in settings hooked by hook_config()?
sub toggled_by_set{
	my ( $pointer, $option, $value ) = @_;

	if ($option eq "plugins.var.perl.$prgname.hide.server.if.buddies.offline"){
		$default_options{hide_server} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.hide.buddy.if.offline"){
		$default_options{hide_buddy} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.sort"){
		$default_options{sort} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.hide.bar"){
		$default_options{hide_bar} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.default"){
		$default_options{color_default} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.server"){
		$default_options{color_server_online} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.server.offline"){
		$default_options{color_server_offline} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.away"){
		$default_color_buddylist{"away"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.offline"){
		$default_color_buddylist{"offline"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.online"){
		$default_color_buddylist{"online"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color.number"){
		$default_options{"color_number"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.show.query"){
		$default_options{"show_query"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.buddy.on.server"){
		$default_options{"buddy_on_server"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.buddy.on.server.color"){
		$default_options{"buddy_on_server_color"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.check.buddies"){
		$default_options{"check_buddies"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.callback.timeout"){
		$default_options{"callback_timeout"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.use.redirection"){
		$default_options{"use_redirection"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.display.original.nick"){
		$default_options{"display_original_nick"} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.display.social.net"){
                $default_options{"display_social_net"} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.display.social.net.color"){
                $default_options{"display_social_net_color"} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.debug.redir.out"){
		$debug_redir_out = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.text.online"){
                $default_options{text_online} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.text.away"){
                $default_options{text_away} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.text.offline"){
                $default_options{text_offline} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.text.color"){
                $default_options{text_color} = $value;
        }elsif ($option eq "plugins.var.perl.$prgname.hide.servername.in.buddylist"){
                $default_options{hide_servername_in_buddylist} = $value;
        }

  server_check();

weechat::bar_item_update($prgname);

# check Hooks()
	if ($default_options{check_buddies} ne "0" and $default_options{use_redirection} eq "on"){
		if (defined $Hooks{timer} and defined $Hooks{redirect}){
			unhook_timer();
			hook_timer_and_redirect();
			return weechat::WEECHAT_RC_OK;
		}
	}

	if ($default_options{check_buddies} eq "0" or $default_options{use_redirection} ne "on"){
		if (defined $Hooks{timer} and defined $Hooks{redirect}){
			unhook_timer();
		}
	}else{
		if (not defined $Hooks{timer} or not defined $Hooks{redirect}){
			weechat::config_set_plugin("check.buddies", "0") unless hook_timer_and_redirect();	# fall back to '0', if hook fails
		}
	}

weechat::bar_item_update($prgname);
return weechat::WEECHAT_RC_OK;
}

sub buddylist_signal_buffer
{
    weechat::bar_item_update($prgname);
    return weechat::WEECHAT_RC_OK;
}

sub weechat_dir
{
    my $dir = weechat::config_get_plugin("buddylist");
    if ( $dir =~ /%h/ )
    {
        my $weechat_dir = weechat::info_get( 'weechat_dir', '');
        $dir =~ s/%h/$weechat_dir/;
    }
    return $dir;
}

# init the settings
sub init{
    $weechat_version = weechat::info_get("version_number", "");
    $default_version = 0;
    if (($weechat_version ne "") && ($weechat_version >= 0x00030400))   # v0.3.4
    {
        $default_version = 1;
    }

    # a filename is defined in option?
    weechat::config_set_plugin("buddylist", $default_buddylist ) if ( weechat::config_get_plugin("buddylist") eq "" );

    if (!weechat::config_is_set_plugin("color.default"))
    {
        weechat::config_set_plugin("color.default", $default_options{color_default});
    }else
    {
        $default_options{color_default} = weechat::config_get_plugin("color.default");
    }
    if (!weechat::config_is_set_plugin("color.server"))
    {
        weechat::config_set_plugin("color.server", $default_options{color_server_online});
    }else
    {
        $default_options{color_server_online} = weechat::config_get_plugin("color.server");
    }
    if (!weechat::config_is_set_plugin("color.server.offline"))
    {
        weechat::config_set_plugin("color.server.offline", $default_options{color_server_offline});
    }else
    {
        $default_options{color_server_offline} = weechat::config_get_plugin("color.server.offline");
    }
    if (!weechat::config_is_set_plugin("buddy.on.server.color"))
    {
        weechat::config_set_plugin("buddy.on.server.color", $default_options{buddy_on_server_color});
    }else
    {
        $default_options{buddy_on_server_color} = weechat::config_get_plugin("buddy.on.server.color");
    }
    if (!weechat::config_is_set_plugin("color.number"))
    {
        weechat::config_set_plugin("color.number", $default_options{color_number});
    }else
    {
        $default_options{color_number} = weechat::config_get_plugin("color.number");
    }
    if (!weechat::config_is_set_plugin("show.query"))
    {
        weechat::config_set_plugin("show.query", $default_options{show_query});
    }else
    {
        $default_options{show_query} = weechat::config_get_plugin("show.query");
    }
    if (!weechat::config_is_set_plugin("hide.bar"))
    {
        weechat::config_set_plugin("hide.bar", $default_options{hide_bar});
    }else
    {
        $default_options{hide_bar} = weechat::config_get_plugin("hide.bar");
    }
    if (!weechat::config_is_set_plugin("sort"))
    {
        weechat::config_set_plugin("sort", $default_options{sort});
    }else
    {
        $default_options{sort} = weechat::config_get_plugin("sort");
    }
    if (!weechat::config_is_set_plugin("hide.server.if.buddies.offline"))
    {
        weechat::config_set_plugin("hide.server.if.buddies.offline", $default_options{hide_server});
    }else
    {
        $default_options{hide_server} = weechat::config_get_plugin("hide.server.if.buddies.offline");
    }
    if (!weechat::config_is_set_plugin("hide.buddy.if.offline"))
    {
        weechat::config_set_plugin("hide.buddy.if.offline", $default_options{hide_buddy});
    }else
    {
        $default_options{hide_buddy} = weechat::config_get_plugin("hide.buddy.if.offline");
    }
    if (!weechat::config_is_set_plugin("buddy.on.server")){
        weechat::config_set_plugin("buddy.on.server", $default_options{buddy_on_server});
    }else{
        $default_options{buddy_on_server} = weechat::config_get_plugin("buddy.on.server");
    }
    if (!weechat::config_is_set_plugin("check.buddies")){
        weechat::config_set_plugin("check.buddies", $default_options{check_buddies});
    }else{
        $default_options{check_buddies} = weechat::config_get_plugin("check.buddies");
    }
    if (!weechat::config_is_set_plugin("callback.timeout")){
        weechat::config_set_plugin("callback.timeout", $default_options{callback_timeout});
    }else{
        $default_options{callback_timeout} = weechat::config_get_plugin("callback.timeout");
    }
    if (!weechat::config_is_set_plugin("use.redirection")){
        weechat::config_set_plugin("use.redirection", $default_options{use_redirection});
    }else{
        $default_options{use_redirection} = weechat::config_get_plugin("use.redirection");
    }
    if (!weechat::config_is_set_plugin("display.original.nick")){
        weechat::config_set_plugin("display.original.nick", $default_options{display_original_nick});
    }else{
        $default_options{display_original_nick} = weechat::config_get_plugin("display.original.nick");
    }
    if (!weechat::config_is_set_plugin("display.social.net")){
        weechat::config_set_plugin("display.social.net", $default_options{display_social_net});
    }else{
        $default_options{display_social_net} = weechat::config_get_plugin("display.social.net");
    }
    if (!weechat::config_is_set_plugin("display.social.net.color")){
        weechat::config_set_plugin("display.social.net.color", $default_options{display_social_net_color});
    }else{
        $default_options{display_social_net_color} = weechat::config_get_plugin("display.social.net.color");
    }
    if (!weechat::config_is_set_plugin("text.online")){
        weechat::config_set_plugin("text.online", $default_options{text_online});
    }else{
        $default_options{text_online} = weechat::config_get_plugin("text.online");
    }
    if (!weechat::config_is_set_plugin("text.away")){
        weechat::config_set_plugin("text.away", $default_options{text_away});
    }else{
        $default_options{text_away} = weechat::config_get_plugin("text.away");
    }
    if (!weechat::config_is_set_plugin("text.offline")){
        weechat::config_set_plugin("text.offline", $default_options{text_offline});
    }else{
        $default_options{text_offline} = weechat::config_get_plugin("text.offline");
    }
    if (!weechat::config_is_set_plugin("text.color")){
        weechat::config_set_plugin("text.color", $default_options{text_color});
    }else{
        $default_options{text_color} = weechat::config_get_plugin("text.color");
    }
    if (!weechat::config_is_set_plugin("hide.servername.in.buddylist")){
        weechat::config_set_plugin("hide.servername.in.buddylist", $default_options{hide_servername_in_buddylist});
    }else{
        $default_options{hide_servername_in_buddylist} = weechat::config_get_plugin("hide.servername.in.buddylist");
    }

    if ( ($weechat_version ne "") && (weechat::info_get("version_number", "") >= 0x00030500) )  # v0.3.5
    {
        weechat::config_set_desc_plugin("buddylist","path/file-name to store your buddies. \"%h\" will be replaced by WeeChat home (by default: ~/.weechat)");
        weechat::config_set_desc_plugin("color.default","fall back color. (default: standard weechat color)");
        weechat::config_set_desc_plugin("color.online","color for online buddies");
        weechat::config_set_desc_plugin("color.away","color for away buddies");
        weechat::config_set_desc_plugin("color.offline","color for offline buddies");
        weechat::config_set_desc_plugin("color.server","color for servername");
        weechat::config_set_desc_plugin("color.server.offline","color for disconnected server (default: hide)");
        weechat::config_set_desc_plugin("color.number","color for channel number (default: lightred). If empty, channel list option is off");

        weechat::config_set_desc_plugin("show.query","displays a query buffer in front of the channel list");

        weechat::config_set_desc_plugin("hide.server.if.buddies.offline","hides server when all buddies are offline for this server (default: off)");
        weechat::config_set_desc_plugin("hide.buddy.if.offline","hide buddy if offline (default: off)");

        weechat::config_set_desc_plugin("buddy.on.server","show buddy who is connected to a server, but not visiting the same channel(s) (default: on)");
        weechat::config_set_desc_plugin("buddy.on.server.color","color for online buddy but not visiting the same channel(s) (default: lightgreen)");

        weechat::config_set_desc_plugin("hide.bar","hides buddylist bar when all servers with added buddies are offline (on = default, always = buddylist bar will be hidden (for example if you want to add item 'buddylist' to 'weechat.bar.status.items', off = buddylist bar will not be hidden))");
        weechat::config_set_desc_plugin("check.buddies","time in seconds to send a /whois request to server. Be careful not to flood server (default: 20)");
        weechat::config_set_desc_plugin("callback.timeout","time in seconds to wait for answer from server. (default: 60)");
        weechat::config_set_desc_plugin("display.original.nick","display original nickname even if buddy changed his /nick (you have to add new nick to buddylist (default: off)");

        weechat::config_set_desc_plugin("sort","sort method for buddylist (default = buddylist will be sort by nickname, status = buddylist will be sort by status (online, away, offline))");

        weechat::config_set_desc_plugin("display.social.net","using bitlbee, buddies will be sorted in sublists with social-network name (eg. msn/jabber/facebook)(default: on)");
        weechat::config_set_desc_plugin("display.social.net.color","color for social-network name (default: yellow)");

        weechat::config_set_desc_plugin("text.color","color for optional online/away/offline-text in buddylist (default: white)");
        weechat::config_set_desc_plugin("text.online","optional online text in buddylist (sort method has to be 'status')");
        weechat::config_set_desc_plugin("text.away","optional away text in buddylist (sort method has to be 'status')");
        weechat::config_set_desc_plugin("text.offline","optional offline text in buddylist (sort method has to be 'status')");

        weechat::config_set_desc_plugin("use.redirection","using redirection to get status of buddies (needs weechat >=0.3.4) (default: on)");
        weechat::config_set_desc_plugin("hide.servername.in.buddylist","hide the servername in buddylist. If \"on\" only nicks will be displayed in buddylist (default: off)");
    }

# only for debugging
    $debug_redir_out = weechat::config_get_plugin("debug.redir.out") if (weechat::config_is_set_plugin("debug.redir.out"));
# get color settings.
    foreach my $level (values %buddylist_level)
    {
        if (weechat::config_get_plugin("color.".$level) eq "")
        {
            weechat::config_set_plugin("color.".$level,
                                       $default_color_buddylist{$level});
        }
        else
        {
            $default_color_buddylist{$level} = weechat::config_get_plugin("color.".$level);
        }
    }
}

# hide bar when buddylist was closed
sub shutdown{
	weechat::command("", "/bar hide " . $prgname);
return weechat::WEECHAT_RC_OK;
}

sub DEBUG {weechat::print('', "***\t" . $_[0]);}

sub hook_timer_and_redirect{

      if ($default_version eq 1){		# if weechat is <= 0.3.4 no hooks() will be installed. Means no redirection!
	$Hooks{redirect} = weechat::hook_hsignal("irc_redirection_buddylist_whois", "redirect_whois", "");	# install hsignal()
		if ($Hooks{redirect} eq '')
		{
			weechat::print("",weechat::prefix("error")."hook failed. can't enable hook_hsignal() for $prgname.");
			return 0;
		}
	$Hooks{timer} = weechat::hook_timer($default_options{check_buddies} * 1000 * 1, 0, 0, "call_whois_all", "");	# period * millisec(1000) * second(1) * minutes(0)
		if ($Hooks{timer} eq '')
		{
			weechat::print("",weechat::prefix("error")."hook failed. can't enable hook_timer() for $prgname.");
			if (defined $Hooks{redirect}){
			  weechat::unhook($Hooks{redirect});
			  delete $Hooks{redirect};
			}
			return 0;
		}
      }
	return 1;
}

sub unhook_timer
{
    if (defined $Hooks{timer})
    {
        weechat::unhook($Hooks{timer});
        delete $Hooks{timer};
    }
    if (defined $Hooks{redirect})
    {
        weechat::unhook($Hooks{redirect});
        delete $Hooks{redirect};
    }
}

sub call_whois_one
{
    my ( $server, $nickname ) = @_;
    my $hash = { "server" => $server, "pattern" => "whois", "signal" => "buddylist",
                "count" => "1", "string" => $nickname, "timeout" => $default_options{callback_timeout}, "cmd_filter" => "" };
    weechat::hook_hsignal_send("irc_redirect_command", $hash);
    weechat::hook_signal_send("irc_input_send", weechat::WEECHAT_HOOK_SIGNAL_STRING, $server.";;2;;/whois ".$nickname); #server;channel;flags;tags;text
}

# -------------------------------[ redirection ]-------------------------------------
# calling /whois all x seconds using hook:timer()
sub call_whois_all{
my $int_count = 0;
my $foreach_count = 0;
	  # sort server and check if server is online
	  foreach my $server ( sort keys %nick_structure ){				# sort server (a-z)
	      my $color_server = get_server_status($server);				# get server status
	      if ($color_server eq $default_options{color_server_offline} or $color_server eq "1"){# server is offline
		next;									# goto next server
	      }
		# sort nick structure and call /whois
		foreach my $nickname ( keys %{$nick_structure{$server}} ) {		# sort nicks (a-z)
		  if (not defined $nick_structure{$server}{$nickname}{counter} or $nick_structure{$server}{$nickname}{counter} eq 0){
		    delete $nick_structure{$server}{$nickname} if ( $nickname eq ":seconds" );	# wrong parsing!?
		    next if ( $nickname eq ":seconds" );					# wrong parsing!?
		    $nick_structure{$server}{$nickname}{counter} = 1;
		    $foreach_count = 1;
		    $int_count = 1;

		    next if ($server eq "" or $nickname eq "");

		    # calling hsignal(redirect)
		    my $hash = { "server" => $server, "pattern" => "whois", "signal" => "buddylist",
				  "count" => "1", "string" => $nickname, "timeout" => $default_options{callback_timeout}, "cmd_filter" => "" };
		    weechat::hook_hsignal_send("irc_redirect_command", $hash);
		    weechat::hook_signal_send("irc_input_send", weechat::WEECHAT_HOOK_SIGNAL_STRING, $server.";;2;;/whois ".$nickname); #server;channel;flags;tags;text

		    last;								# jump to end of list
		  }else{
		    next;
		  }

		}
	  last if ($foreach_count eq 1);
	  }
# set counter for each buddy back to zero to start count from beginning
  if ($int_count eq 0){
  $int_count = 0;
	  foreach my $server ( sort keys %nick_structure ){				# sort server (a-z)
		foreach my $nickname ( sort keys %{$nick_structure{$server}} ) {	# sort nicks (a-z)
		    $nick_structure{$server}{$nickname}{counter} = 0;
		}
	  }
  $foreach_count = 0;
  }
}

# backcall from hook_hsignal()
sub redirect_whois{
    my ($data, $signal, %hashtable) = ($_[0], $_[1], %{$_[2]});

# for testing purpose, to see whats inside of hashtable
    if ( $debug_redir_out eq "on" ){
        while (my($key, $value) = each %hashtable){
            weechat::print("",$key . " is key with value " .$hashtable{$key});
        }
    }

    # get nick from hashtable command: /whois nick
    my (undef, $main_nickname) = split /\s+/, $hashtable{"command"}, 2;
    # weechat >=0.4.0 and "irc.network.whois_double_nick = on", command is: /whois nick nick
    if ($weechat_version >= 0x00040000  and  weechat::config_boolean(weechat::config_get("irc.network.whois_double_nick")) == 1){
        (undef,$main_nickname) = split /\s+/,$main_nickname;
    }

    # timeout error...
    if ($hashtable{"error"} eq "timeout"){
        weechat::print("",weechat::prefix("error").
                    "buddylist: timeout error for server ".
                    weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_server"))).
                    $hashtable{"server"}.
                    weechat::color("reset").
                    ". Increase value \"callback.timeout\" (current value: ".
                    $default_options{callback_timeout} . ")");
        return weechat::WEECHAT_RC_OK;
    }

    # check if buddy is online and look for visiting channels
    my $rfc_319 = "319";							# rfc number containing channels
    my ( $nickname,$channel_name ) = parse_redirect($hashtable{"server"},$rfc_319,$hashtable{"output"});	# check redirection output for channels
    return weechat::WEECHAT_RC_OK if ( $channel_name eq -1 );		# -1 = buddy not online

    if ($channel_name eq -2 and exists $nick_structure{$hashtable{"server"}}{$main_nickname}){
        my $sorted_numbers = check_query_buffer($hashtable{"server"},$main_nickname,"");
        $nick_structure{$hashtable{"server"}}{$main_nickname}{buffer} = "()" if ($sorted_numbers eq "");	# buddy online but not in a channel
        $nick_structure{$hashtable{"server"}}{$main_nickname}{buffer} = $sorted_numbers if ($sorted_numbers ne ""); # /query buffer open
    }else{
        check_for_channels($hashtable{"server"}, $main_nickname, $channel_name);
    }

    weechat::bar_item_update($prgname);
return weechat::WEECHAT_RC_OK;
}

# compare if your buddy is in same channels you are already in. channel-number(s) will be saved in nick_structure(buffer)
sub check_for_channels{
    my ($server, $nickname, $channel_name) = @_;
    return if (not exists $nick_structure{$server}{$nickname}); # does nick exists in nick_structure? NO?

    $nick_structure{$server}{$nickname}{buf_name} = "";         # delete
    $channel_name =~ s/:|@|!|\+//g;                             # kill channel-modes (not needed for channelname)

    $nick_structure{$server}{$nickname}{buf_name} = $channel_name;# save name of visit channels
    my @array=split(/ /,$channel_name);                         # split channelnames into array

    # check out if buddy is in same channels as you are
    my @buf_count;
    $nick_structure{$server}{$nickname}{buffer} = "()";		# delete buffer number in nick_structure{buffer]

    foreach (@array){
        my $buffer_pointer = weechat::buffer_search("irc", $server . "." . $_);
        if ($buffer_pointer ne ""){					# buffer exists?
            my $buffer_number = search_buffer_number($buffer_pointer);# check if buddy is in same channels as you
            if ($buffer_number ne 0){
                push @buf_count,($buffer_number) ;
                # check if option "color.number" has valid entry and write buffer number to nick_structure
                if ($default_options{color_number} ne ""){		# color for color_number set?
                    @buf_count = del_double(@buf_count);
                    my $sorted_numbers = join(",",sort{$a<=>$b}(@buf_count));		# channel numbers (1,2....)
                    $sorted_numbers = check_query_buffer($server,$nickname,$sorted_numbers);
                    $nick_structure{$server}{$nickname}{buffer} = $sorted_numbers;# save buffer number in nick_structure{buffer]
                }
            }
        }elsif ($nick_structure{$server}{$nickname}{buffer} eq "()"){# buddy online but not in a channel you are in
            my $sorted_numbers = check_query_buffer($server,$nickname,"");
            $nick_structure{$server}{$nickname}{buffer} = "()" if ($sorted_numbers eq "");
            $nick_structure{$server}{$nickname}{buffer} = $sorted_numbers if ($sorted_numbers ne "");
        }
    }
}

# delete double entries
sub del_double{
  my %all=();
  @all{@_}=1;
  return (keys %all);
}

# looking for /query buffer
sub check_query_buffer{
my ($server,$nickname,$sorted_numbers) = @_;

return $sorted_numbers if ($default_options{show_query} ne "on");

my $buffer_pointer = weechat::buffer_search("irc", $server . "." . $nickname);
if ($buffer_pointer ne ""){
    my $buffer_number = search_buffer_number($buffer_pointer);
    if ($sorted_numbers ne ""){
        $sorted_numbers = "Q:" . $buffer_number . "," . $sorted_numbers;
    }else{
        $sorted_numbers = "Q:" . $buffer_number;
    }
}

return $sorted_numbers;
}
# search buffer
sub search_buffer_number{
my ( $buffer_name ) = @_;
  my $infolist_buffer = weechat::infolist_get("buffer",$buffer_name,"");	# get infolist_pointer for buffer
  weechat::infolist_next($infolist_buffer);
  my $buffer_number = weechat::infolist_integer($infolist_buffer,"number");	# get buffer_number
  weechat::infolist_free($infolist_buffer);					# don't forget to free infolist ;-)

return $buffer_number;
}

# checks if buddy is connected to server and look for $rfc line from /whois redirection
# :anthony.freenode.net 330 mynick 2nd_nick 1st_nick :is logged in as		# [2nd_nick] is logged in as 1st_nick
sub parse_redirect{
my ( $servername,$rfc,$args ) = @_;

return ("",-1) if (not defined $servername or $servername eq "");
  # nick is not online
  my $rfc_401 = " 401 ";							# No such nick/channel
  $args =~ /($rfc_401)(.*?) (.*?) (.*)\n/;
  if (defined $1 and $1 eq $rfc_401 and defined $3){
	$nick_structure{$servername}{$3}{status} = 2;				# buddy offline
	$nick_structure{$servername}{$3}{buffer} = "";				# clear buffer number
	$nick_structure{$servername}{$3}{buf_name} = "";			# clear name of buffer
    return ("",-1);
  }

  my $rfc_301 = " 301 ";							# nick :away
### part for bitlbee
  # bitlbee offline check
  # :localhost 312 nils_2 nickname mail@gmail.com. :jabber network
  # :localhost 301 nils_2 nickname :User is offline
  my $rfc_312 = " 312 ";							# 312 nick server :info
  my $offline_text = "(:User is offline|:Offline)\n";				# (bitlbee|bitlbee-libpurple)
  my $network = "(:msn|:jabber|:yahoo)";					# possible networks
  my ($a1,$a2,$a3,$a4)  = "";
  ($a1,$a2,$a3,$a4) = ($args =~ /(.*)($rfc_312)(.*)($network)/);
  if ( defined $a4 and $a4 ne ""){
    ($a1,$a2,$a3,$a4) = "";
    ($a1,$a2,$a3,$a4) = ($args =~ /($rfc_301)(.*?) (.*?) ($offline_text)/);
    if ( defined $a4 and $a4 ne ""){
	$nick_structure{$servername}{$a3}{status} = 2;				# buddy offline on bitlbee
	$nick_structure{$servername}{$a3}{buffer} = "";				# clear buffer number
	$nick_structure{$servername}{$a3}{buf_name} = "";			# clear name of buffer
	return ("",-1);
    }
  }

  # bitlbee: add a tag for msn/jabber/facebook to display in buddylist
    ($a1,$a2,$a3,$a4) = "";
  my ($a5,$a6)  = "";
  ($a1,$a2,$a3,$a4,$a5,$a6) = ($args =~ /(.*)($rfc_312)(.*?) (.*?) (.*)($network)/);

if ( $default_options{display_social_net} eq "on" ){
  if ( defined $a6 ){
    my ($string) = split / /,$a6;                                               # get first word from network
    if ( $string eq ":msn" ){
        $nick_structure{$servername}{$a4}{bitlbee_service} = "msn";
    }elsif ( $string eq ":jabber" ){
        $nick_structure{$servername}{$a4}{bitlbee_service} = "jabber";
        $nick_structure{$servername}{$a4}{bitlbee_service} = "facebook" if ( index($args,"chat.facebook.com") ne "-1" );
    }elsif ( $string eq ":yahoo" ){
        $nick_structure{$servername}{$a4}{bitlbee_service} = "yahoo";
    }else{
        $nick_structure{$servername}{$a4}{bitlbee_service} = "";                # no unknown service
    }
  }
}elsif( defined $a6 ){
        $nick_structure{$servername}{$a4}{bitlbee_service} = "";                # no unknown service
}

### bitlbee part end

if ( $default_options{display_original_nick} eq "on" ){
  my $rfc_330 = " 330 ";							# nick :is logged in as
  # check if nick has a different nick name (/nick blafasel)
  $args =~ /($rfc_330)(.*?) (.*?) (.*?) :(.*)\n/;				# non-greedy
    my $nickname_as = $3;
    my $nickname = $4;

    if ( defined $nickname_as and defined $nickname and $nickname_as ne $nickname ){
      if ( exists $nick_structure{$servername}{$nickname} ){
	$args =~ /($rfc_301)/;
	if (defined $1 and $1 eq $rfc_301){					# buddy is away
	  return ($nickname,-1) if (not defined $nickname or not exists $nick_structure{$servername}{$nickname});		# does nick exists in nick_structure? NO?
	  $nick_structure{$servername}{$nickname}{status} = 1;			# buddy away
	  $nick_structure{$servername}{$nickname_as}{status} = 2 if (exists $nick_structure{$servername}{$nickname_as} ); 		# set alias nick to offline
	}else{
	  return ($nickname,-1) if (not defined $nickname or not exists $nick_structure{$servername}{$nickname});		# does nick exists in nick_structure? NO?
	  $nick_structure{$servername}{$nickname}{status} = 0;			# buddy is online
	  $nick_structure{$servername}{$nickname_as}{status} = 2 if (exists $nick_structure{$servername}{$nickname_as} ); 		# set alias nick to offline
	}
      }elsif ( exists $nick_structure{$servername}{$nickname_as} ){
	$args =~ /($rfc_301)/;
	if (defined $1 and $1 eq $rfc_301){					# buddy is away
	  return ($nickname_as,-1) if (not defined $nickname_as or not exists $nick_structure{$servername}{$nickname_as});		# does nick exists in nick_structure? NO?
	  $nick_structure{$servername}{$nickname_as}{status} = 1;		# buddy away
	  $nickname = $nickname_as;
	}else{
	  return ($nickname_as,-1) if (not defined $nickname_as or not exists $nick_structure{$servername}{$nickname_as});		# does nick exists in nick_structure? NO?
	  $nick_structure{$servername}{$nickname_as}{status} = 0;		# buddy is online
	  $nickname = $nickname_as;
	}
      }

	  $rfc = " " . $rfc . " ";						# space at beginning and end of requested rfc

	  if ($args =~ /($rfc)(.*?) (.*?) (.*)\n/){				# non-greedy
	  if (not defined $4){
	    return ($nickname,-2);						# buddy online but not visiting a channel
	  }
	    return ($nickname,$4);						# return data (for example channel names)
	  }else{
	    return ($nickname,-2);						# buddy online but not visiting a channel
	  }
    }
}

  # get nick name 
  my $rfc_311 = " 311 ";							# nick username address * :info
  my (undef, undef, undef, $nickname2, undef) = split /\s+/, $args, 5 if ($args =~ /($rfc_311)/);	# get nickname

  # check nick away....
  $args =~ /($rfc_301)/;
  if (defined $1 and $1 eq $rfc_301){						# buddy is away
	return ($nickname2,-1) if (not defined $nickname2 or not exists $nick_structure{$servername}{$nickname2});		# does nick exists in nick_structure? NO?
	$nick_structure{$servername}{$nickname2}{status} = 1;			# buddy away
  }else{
	return ($nickname2,-1) if (not defined $nickname2 or not exists $nick_structure{$servername}{$nickname2});		# does nick exists in nick_structure? NO?
	$nick_structure{$servername}{$nickname2}{status} = 0;			# buddy is online
  }

  $rfc = " " . $rfc . " ";							# space at beginning and end of requested rfc
  $args =~ /($rfc)(.*?) (.*?) (.*)\n/;						# non-greedy
  if (not defined $4){
    return ($nickname2,-2);							# buddy online but not visiting a channel
  }
return ($nickname2,$4);								# return data (for example channel names)
}

sub buddy_list_completion_cb{
my ($data, $completion_item, $buffer, $completion) = @_;


my $infolist = weechat::infolist_get("buffer",$buffer,"");
weechat::infolist_next($infolist);
my $irc_name = weechat::infolist_string($infolist, "name");
weechat::infolist_free($infolist);

return weechat::WEECHAT_RC_OK if ( $irc_name eq "weechat");                     # core buffer
my ( $server, $channel ) = split(/\./, $irc_name);                              # split server.#channel
return weechat::WEECHAT_RC_OK if ( not defined $channel );                      # iset, infolist buffer etc.
$server = $channel if ( $server eq "server");                                   # are we in server buffer?

  foreach my $nickname ( keys %{$nick_structure{$server}} ) {
    weechat::hook_completion_list_add($completion, $nickname,1, weechat::WEECHAT_LIST_POS_SORT);
  }

return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ mouse support ]-------------------------------------
sub hook_focus_buddylist{
    my %info = %{$_[1]};
    my $bar_item_line = int($info{"_bar_item_line"});
    undef my $hash;
    return if ($#buddylist_focus == -1);

    my $flag = 0;
    # if button1 was pressed on "offline" buddy, do nothing!!!
    if ( ($info{"_bar_item_name"} eq $prgname) && ($bar_item_line >= 0) && ($bar_item_line <= $#buddylist_focus) && ($info{"_key"} eq "button1" ) ){
        $hash = $buddylist_focus[$bar_item_line];
        my $hash_focus = $hash;
        while ( my ($key,$value) = each %$hash_focus ){
          if ( $key eq "status" and $value eq "2" ){
            $flag = 1;
          }
        undef $hash if ($flag == 1);
        }
    return "" if ($flag == 1);
    undef $hash if (not defined $hash);
    return $hash;
    }elsif( ($info{"_bar_item_name"} eq $prgname) && ($bar_item_line >= 0) && ($bar_item_line <= $#buddylist_focus) && (index($info{"_key"},"button1-gesture-") ne -1 ) ){
      $hash = $buddylist_focus[$bar_item_line];
      undef $hash if (not defined $hash);
      return $hash;
    }

}
sub buddylist_hsignal_mouse{
    my ($data, $signal, %hash) = ($_[0], $_[1], %{$_[2]});

      if ( $hash{"_bar_item_name"} eq $hash{"_bar_item_name2"} ){                                 # source and destination is same bar
          return weechat::WEECHAT_RC_OK if (not defined $hash{"server"} or not defined $hash{"nick"});  # no nick or no server defined!
          weechat::command("", "/query -server " . $hash{"server"} . " " . $hash{"nick"});        # open an query
      }elsif ( $hash{"_bar_item_name"} eq $prgname and $hash{"_bar_item_name2"} ne $prgname ){    # drag and drop from buddylist
          return weechat::WEECHAT_RC_OK if (not defined $hash{"server"} or not defined $hash{"nick"});  # no nick or no server defined!
          delete $nick_structure{$hash{"server"}}{$hash{"nick"}};
          delete $nick_structure{$hash{"server"}} if (keys (%{$nick_structure{$hash{"server"}}}) == 0);# delete servername from structure, if last nick from server was deleted
          buddylist_save();
      }elsif ( $hash{"_bar_item_name"} ne $prgname and $hash{"_bar_item_name2"} eq $prgname ){    # drag and drop to buddylist
          if ( $hash{"_chat_line_nick"} ne ""){                                                   # from chat area if ne ""
            $nick_structure{$hash{"_buffer_localvar_server"}}{$hash{"_chat_line_nick"}}{status} = 2;
            $nick_structure{$hash{"_buffer_localvar_server"}}{$hash{"_chat_line_nick"}}{bitlbee_service} = "";
          }elsif ( defined $hash{"nick"} and $hash{"nick"} ne ""){                                # from nicklist!
            $nick_structure{$hash{"_buffer_localvar_server"}}{$hash{"nick"}}{status} = 2;
            $nick_structure{$hash{"_buffer_localvar_server"}}{$hash{"nick"}}{bitlbee_service} = "";
          }
            buddylist_save();
      }

weechat::bar_item_update($prgname);
return weechat::WEECHAT_RC_OK;
}
# this is the end
