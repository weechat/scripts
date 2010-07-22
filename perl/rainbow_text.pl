#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
#
# colours the channel text with nick colour and also highlight the whole text
# now colorize_nicks.py script will be supported
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
# history:
# 0.3: support of colorize_nicks.py implemented.
#    : /me text displayed wrong nick colour (colour from suffix was used)
#    : highlight messages will be checked case insensitiv
# 0.2: supports highlight_words_add from buffer_autoset.py script (suggested: Emralegna)
#    : correct look_nickmode colour will be used (bug reported by: Emralegna)
#    : /me text will be coloured, too
# 0.1: initial release
#
# requirements: sunglasses ;-)

use strict;
my $prgname	= "rainbow_text";
my $version	= "0.3";
my $description	= "colours the channel text with according nick colour. Highlight messages will be fully highlighted";
# default values
my $var_highlight = "on";
my $var_chat = "on";
my $var_shuffle = "off";
my $var_buffer_autoset = "off";
my $prefix_action = "";
my $blacklist_channels = "";
my %colours = (0 => "darkgray", 1 => "red", 2 => "lightred", 3 => "green",
		  4 => "lightgreen", 5 => "brown", 6 => "yellow", 7 => "blue",
		  8 => "lightblue", 9 => "magenta", 10 => "lightmagenta", 11 => "cyan",
		  12 => "lightcyan", 13 => "white");

my $zahl = 0;
my $nick_mode = "";

# program starts here
sub colorize_cb {
my ( $data, $modifier, $modifier_data, $string ) = @_;

if (index($modifier_data,"irc_privmsg") == -1){								# its neither a channel nor a query buffer
  return $string;
}
if ($var_highlight eq "off" and $var_chat eq "off"){							# all options OFF
  return $string;
}

$modifier_data =~ (m/irc;(.+?)\.(.+?)\;/);
my $servername = $1;
my $channel_name = $2;
if (index($blacklist_channels,$channel_name) >= 0) {							# check blacklist_channels
  return $string;
}

my $my_nick = weechat::info_get( 'irc_nick', $servername );						# get nick with servername (;freenode.)

$string =~ m/^(.*)\t(.*)/;										# get the nick name: nick[tab]string
my $nick = $1;
my $line = $2;												# get written text

# i wrote the message
    if ($nick =~ m/(\w.*$my_nick.*)/){									# i wrote the message
      if ($var_chat eq "on"){
	  my $nick_color = weechat::config_color(weechat::config_get("weechat.color.chat_nick_self"));	# get my nick colour
	  $nick_color = weechat::color($nick_color);
	  $line = colorize_nicks($nick_color,$modifier_data,$line);
	  $line = $nick . "\t" . $nick_color . $line . weechat::color('reset');
	  return $line;
      }else{
	  return $string;
      }
    }

# check if look.nickmode is ON and no prefix and no query buffer
my $nick_mode = "";
if ( weechat::config_boolean(weechat::config_get("weechat.look.nickmode")) ==  1 and (weechat::string_remove_color($nick,"") ne $prefix_action) and (index($modifier_data,"notify_private")) == -1){
   if (weechat::string_remove_color($nick,"") =~ m/^\@|^\%|^\+|^\~|^\*|^\&|^\!|^\-/) {			# check for nick modes (@%+~*&!-) without colour
      $nick_mode = substr($nick,0,5);									# get nick_mode with colour codes
      $nick = substr($nick,5,length($nick)-1);								# get nick name
  }
}

# get nick colour
$nick = weechat::string_remove_color($nick,"");								# remove colour-codes from nick
my $nick_color = weechat::info_get('irc_nick_color', $nick);						# get nick-colour

# check for /me text
if ($prefix_action eq $nick){										# nick is a prefix!!!
    $line = weechat::string_remove_color($line,"");							# remove colour-codes from line
	$nick_color = weechat::info_get('irc_nick_color', $line =~ (m/(.+?) /));			# and get real nick-colour from line
}

# highlight message received?
    if ($var_highlight eq "on"){									# highlight_mode on?
      if ($var_buffer_autoset eq "on"){									# buffer_autoset "on"?
	  my $highlight_words_add = weechat::config_string(weechat::config_get("buffer_autoset.buffer.irc.".$servername.".".$channel_name.".highlight_words_add"));
	      foreach ( split( /,+/, $highlight_words_add ) ) {						# check for highlight_words_add
		  if ($_ eq ""){next;}									# ignore empty string
		    my $search_string = shell2regex($_);

		  if ($string =~ m/\b$search_string\b/gi){						# i (ignorecase)
		    my $color_highlight = weechat::config_color(weechat::config_get("weechat.color.chat_highlight"));
		    my $color_highlight_bg = weechat::config_color(weechat::config_get("weechat.color.chat_highlight_bg"));
		    my $high_color = weechat::color("$color_highlight,$color_highlight_bg");
			  if ($prefix_action eq $nick){							# highlight in /me text?
#			    $line = weechat::string_remove_color($line,"");				# remove colour-codes from line
			    $line = colorize_nicks($nick_color,$modifier_data,$line);
			    $line = $nick_mode . $high_color . $nick . "\t" . $high_color . $line . weechat::color('reset');
			    return $line;
			  }
		    $line = colorize_nicks($high_color,$modifier_data,$line);
		    $line = $nick_mode . $high_color . $nick . "\t" . $high_color . $line . weechat::color('reset');
		    return $line;
		  }
	      }
      }
	# buffer_autoset is off.
	if (lc($string) =~ m/(\w.*$my_nick.*)/){							# my name called in string (case insensitiv)?
	    my $color_highlight = weechat::config_color(weechat::config_get("weechat.color.chat_highlight"));
	    my $color_highlight_bg = weechat::config_color(weechat::config_get("weechat.color.chat_highlight_bg"));
	    my $high_color = weechat::color("$color_highlight,$color_highlight_bg");

	      if ($prefix_action eq $nick){								# prefix used (for example using /me)

		    if (weechat::string_remove_color($line,"") =~ m/^$my_nick/) {			# check for own nick
			$nick_color = weechat::config_color(weechat::config_get("weechat.color.chat_nick_self"));# get my nick colour
			$nick_color = weechat::color($nick_color);
			$line = colorize_nicks($nick_color,$modifier_data,$line);
			$line = $nick_mode . $nick . "\t" . $nick_color . $line . weechat::color('reset');# print line
			return $line;
		    }
		# $prefix_action ne $nick
		$line = colorize_nicks($high_color,$modifier_data,$line);
		$line = $nick_mode . $nick . "\t" . $high_color . $line . weechat::color('reset');
		return $line;
	      }

# highlight whole line
	      $line = colorize_nicks($high_color,$modifier_data,$line);
	      $line = $nick_mode . $high_color . $nick . "\t" . $high_color . $line . weechat::color('reset');
	      return $line;
	}
    } # highlight area finished

# simple channel message
    if ($var_chat eq "on"){										# chat_mode on?
	if ($var_shuffle eq "on"){									# colour_shuffle on?
	  my $zahl2 = 0;
	  my $my_color = weechat::config_color(weechat::config_get("weechat.color.chat_nick_self"));	# get my own nick colour
	    for (1){											# get a random colour but don't use
	      redo if ( $zahl ==  ($zahl2 = int(rand(14))) or ($colours{$zahl2} eq $my_color) );	# latest colour nor own nick colour
	      $zahl = $zahl2;
	    }
	  $nick_color = weechat::color($colours{$zahl});						# get new random colour
	}
	  if ($prefix_action eq $nick){									# prefix used (for example using /me)
		$line = colorize_nicks($nick_color,$modifier_data,$line);
		$line = $nick_mode . $nick . "\t" . $nick_color . $line . weechat::color('reset');
		return $line;
	  }

      $line = colorize_nicks($nick_color,$modifier_data,$line);
      $line = $nick_mode . $nick_color . $nick . "\t" . $nick_color . $line . weechat::color('reset');	# create new line nick_color+nick+separator+text
      return $line;
    }else{
      return $string;											# return original string
    }

} # end of sub colorize_cb{}

# converts shell wildcard characters to regex
sub shell2regex {
    my $globstr = shift;
    my %patmap = (
        '*' => '.*',
        '?' => '.',
        '[' => '[',
        ']' => ']',
    );
    $globstr =~ s{(.)} { $patmap{$1} || "\Q$1" }ge;
    return $globstr;
}

sub get_nick_mode{
my ( $word ) = @_;

  if ($word =~ m/^\@|^\%|^\+|^\~|^\*|^\&|^\!|^\-/) {							# check for nick modes (@%+~*&!-)
    $nick_mode = substr($word,0,1);
    my $nick = substr($word,1,length($word)-1);
    return $nick;
  }else{
    return "",$word;
  }
}

# check for colorize_nicks script an set colour before and after nick name 
sub colorize_nicks{
my ( $nick_color, $mf_data, $line ) = @_;

my $pyth_ptn = weechat::infolist_get("python_script","","colorize_nicks");
weechat::infolist_next($pyth_ptn);

if ( "colorize_nicks" eq weechat::infolist_string($pyth_ptn,"name") ){				# does colorize_nicks is installed?
	$line = weechat::string_remove_color($line,"");						# remove colour-codes from line first
	$line = weechat::hook_modifier_exec( "colorize_nicks",$mf_data,$line);			# call colorize_nicks function and color the nick
	my @array = "";
	my $color_code_reset = weechat::color('reset');
	@array=split(/$color_code_reset/,$line);
	my $new_line = "";
	foreach (@array){
	  $new_line .=  $nick_color . $_ . weechat::color('reset');
	}
	$new_line =~ s/\s+$//g;						# remove space at end
	$line = $new_line;

}
weechat::infolist_free($pyth_ptn);
return $line;
}

# changes in settings?
sub toggle_config_by_set{
my ( $pointer, $name, $value ) = @_;

  if ($name eq "plugins.var.perl.$prgname.highlight"){
    $var_highlight = $value;
    return weechat::WEECHAT_RC_OK;
  }
  if ($name eq "plugins.var.perl.$prgname.buffer_autoset"){
    $var_buffer_autoset = $value;
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

# toggle functions on/off manually
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

  if ($getarg eq "buffer_autoset"){
    if ($var_buffer_autoset eq "on"){
      weechat::config_set_plugin("buffer_autoset", "off");
    } else{
      weechat::config_set_plugin("buffer_autoset", "on");
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


# main routine
# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

  if (!weechat::config_is_set_plugin("highlight")){
    weechat::config_set_plugin("highlight", $var_highlight);
  }else{
    $var_highlight = weechat::config_get_plugin("highlight");
  }
  if (!weechat::config_is_set_plugin("buffer_autoset")){
    weechat::config_set_plugin("buffer_autoset", $var_buffer_autoset);
  }else{
    $var_buffer_autoset = weechat::config_get_plugin("buffer_autoset");
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
#weechat::hook_modifier("colorize_text","colorize_cb", "");

weechat::hook_command($prgname, $description,

	"<highlight> <chat> <shuffle> <autoset>", 

	"<highlight>    toggle highlight colour text on/off\n".
	"<chat>         toggle chat colour text on/off\n".
	"<shuffle>      toggle shuffle colour mode on/off\n".
	"<autoset>      toggle highlight colour mode for buffer_autoset on/off\n\n".
	"Options (script):\n".
	"'plugins.var.perl.$prgname.highlight'           : toggle highlight colour in text on/off\n".
	"'plugins.var.perl.$prgname.buffer_autoset'      : toggle highlight colour in text for buffer_autoset on/off\n".
	"'plugins.var.perl.$prgname.chat'                : toggle coloured text for chats on/off\n".
	"'plugins.var.perl.$prgname.shuffle'             : toggle shuffle colour mode for chats on/off\n".
	"'plugins.var.perl.$prgname.blacklist_channels'  : comma separated list with channelname (e.g.: #weechat,#weechat-fr)\n\n".
	"Options (global):\n".
	"'weechat.color.chat_highlight'                      : highlight colour\n".
	"'weechat.color.chat_highlight_bg'                   : highlight background colour\n".
	"'weechat.color.chat_nick*'                          : colours for nicks\n\n".
	"To use the autoset highlight option install buffer_autoset script from: http://www.weechat.org/scripts/\n",
	"highlight|chat|shuffle|autoset", "change_settings", "");

weechat::hook_config( "plugins.var.perl.$prgname.*", "toggle_config_by_set", "" );
