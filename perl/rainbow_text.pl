#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# colours the channel text with nick colour
# and also highlight the whole text
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
# settings see help page
#
# requirements: sun glasses ;-)

use strict;
my $prgname	= "rainbow_text";
my $version	= "0.1";
my $description	= "colours the channel text with nick colour";
# default values
my $var_highlight = "on";
my $var_chat = "on";
my $var_shuffle = "off";
my $prefix_action = "";
my $blacklist_channels = "";
my %colours = (0 => "darkgray", 1 => "red", 2 => "lightred", 3 => "green",
		  4 => "lightgreen", 5 => "brown", 6 => "yellow", 7 => "blue",
		  8 => "lightblue", 9 => "magenta", 10 => "lightmagenta", 11 => "cyan",
		  12 => "lightcyan");

my $zahl = 0;

# program starts here
sub colorize_cb {
my ( $data, $modifier, $modifier_data, $string ) = @_;

if (index($modifier_data,"irc_privmsg") == -1){								# its neither a channel nor a query buffer
  return $string;
}
if ($var_highlight eq "off" and $var_chat eq "off"){							# all options OFF
  return $string;
}
$modifier_data =~ m/\.(.+?);/;
my $channel_name = $1;
if (index($blacklist_channels,$channel_name) >= 0) {							# check blacklist_channels
  return $string;
}

my $my_nick = weechat::info_get( 'irc_nick', $modifier_data =~ m/irc;(.+?)\./ );			# get nick with servername (;freenode.)

$string =~ m/^(.*)\t(.*)/;										# get the nick name: nick[tab]string
my $nick = $1;
my $line = $2;


    if ($nick =~ m/(\w.*$my_nick.*)/){									# i wrote the message
      if ($var_chat eq "on"){
	  my $nick_color = weechat::config_color(weechat::config_get("weechat.color.chat_nick_self"));	# get my nick colour
	  $line = $nick . "\t" . weechat::color($nick_color) . $line . weechat::color('reset');
	  return $line;
      }else{
	  return $string;
      }
    }

$nick = weechat::string_remove_color($nick,"");								# remove colour-codes from nick
my $nick_color = weechat::info_get('irc_nick_color', $nick);						# get nick-colour

    if ($var_highlight eq "on"){
	# highlight message received?
	if ($string =~ m/(\w.*$my_nick.*)/){								# my name called?
	    my $color_highlight = weechat::config_color(weechat::config_get("weechat.color.chat_highlight"));
	    my $color_highlight_bg = weechat::config_color(weechat::config_get("weechat.color.chat_highlight_bg"));
	    my $high_color = weechat::color("$color_highlight,$color_highlight_bg");
	    if ($prefix_action eq $nick){
	      return $string;
	    }
	    $line = $high_color . $nick . "\t" . $high_color . $line . weechat::color('reset');
	    return $line;
	}
    }

    if ($var_chat eq "on"){
      if ($var_shuffle eq "on"){
	my $zahl2 = 0;
	for (1){
	    redo if ($zahl ==  ($zahl2 = int(rand(13))));
	    $zahl = $zahl2;
	}
	$nick_color = weechat::color($colours{$zahl});
      }
	$line = $nick_color . $nick . "\t" . $nick_color . $line . weechat::color('reset');			# create new line nick_color+nick+separator+text
	return $line;
    }else{
	return $string;
    }
}

# changed in settings directly?
sub toggle_config_by_set{
my ( $pointer, $name, $value ) = @_;

  if ($name eq "plugins.var.perl.$prgname.highlight"){
    $var_highlight = $value;
    return weechat::WEECHAT_RC_OK;
  }
  if ($name eq "plugins.var.perl.$prgname.chat"){
    $var_chat = $value;
    return weechat::WEECHAT_RC_OK;
  }
  if ($name eq "plugins.var.perl.$prgname.shuffle"){
    $var_shuffle = $value;
    return weechat::WEECHAT_RC_OK;
  }
  if ($name eq "plugins.var.perl.$prgname.blacklist_channels"){
    $blacklist_channels = $value;
    return weechat::WEECHAT_RC_OK;
  }

return weechat::WEECHAT_RC_OK;
}

# toggle functions on/off
sub change_settings{
my $getarg = lc($_[2]);						# switch to lower-case

  if ($getarg eq "highlight"){
    if ($var_highlight eq "on"){
      weechat::config_set_plugin("highlight", "off");
    } else{
      weechat::config_set_plugin("highlight", "on");
    }
    return weechat::WEECHAT_RC_OK;
  }

  if ($getarg eq "chat"){
    if ($var_chat eq "on"){
      weechat::config_set_plugin("chat", "off");
    } else{
      weechat::config_set_plugin("chat", "on");
    }
  return weechat::WEECHAT_RC_OK;
  }

  if ($getarg eq "shuffle"){
    if ($var_shuffle eq "on"){
      weechat::config_set_plugin("shuffle", "off");
    } else{
      weechat::config_set_plugin("shuffle", "on");
    }
  return weechat::WEECHAT_RC_OK;
  }

weechat::command("", "/help $prgname");			# no arguments given. Print help
return weechat::WEECHAT_RC_OK;
}

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

  if (!weechat::config_is_set_plugin("highlight")){
    weechat::config_set_plugin("highlight", $var_highlight);
  }else{
    $var_highlight = weechat::config_get_plugin("highlight");
  }
  if (!weechat::config_is_set_plugin("chat")){
    weechat::config_set_plugin("chat", $var_chat);
  }else{
    $var_chat = weechat::config_get_plugin("chat");
  }
  if (!weechat::config_is_set_plugin("shuffle")){
    weechat::config_set_plugin("shuffle", $var_shuffle);
  }else{
    $var_shuffle = weechat::config_get_plugin("shuffle");
  }
  if (!weechat::config_is_set_plugin("blacklist_channels")){
    weechat::config_set_plugin("blacklist_channels", $blacklist_channels);
  }else{
    $blacklist_channels = weechat::config_get_plugin("blacklist_channels");
  }

$prefix_action = weechat::config_string(weechat::config_get("weechat.look.prefix_action"));
weechat::hook_modifier("weechat_print","colorize_cb", "");

weechat::hook_command($prgname, $description,

	"<highlight> <chat> <shuffle>", 

	"<highlight> toggle highlight colour text on/off\n".
	"<chat>      toggle chat colour text on/off\n".
	"\n".
	"Options (script):\n".
	"'plugins.var.perl.$prgname.highlight'           : toggle highlight colour in text on/off\n".
	"'plugins.var.perl.$prgname.chat'                : toggle coloured text for chats on/off\n".
	"'plugins.var.perl.$prgname.shuffle'             : toggle shuffle colour mode for chats on/off\n".
	"'plugins.var.perl.$prgname.blacklist_channels'  : comma separated list with channelname (e.g.: #weechat,#weechat-fr)\n\n".
	"Options (global):\n".
	"'weechat.color.chat_highlight'                      : highlight colour\n".
	"'weechat.color.chat_highlight_bg'                   : highlight background colour\n".
	"'weechat.color.chat_nick*'                          : colours for nicks\n",
	"highlight|chat|shuffle", "change_settings", "");

weechat::hook_config( "plugins.var.perl.$prgname.*", "toggle_config_by_set", "" );
