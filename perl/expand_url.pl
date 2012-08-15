#
# Copyright (c) 2011-2012 by Nils Görs <weechatter@arcor.de>
#
# Get information on a short URL. Find out where it goes.
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
# 0.4  : some code optimizations
# 0.3  : fixed: script won't worked if more than one URL per message exists.
#      : fixed: output buffer wasn't correctly set for each message.
#      : fixed: missing return in callback for hook_config()
#      : added: if an URI exists twice in a message script will only print URI once.
#      : added: option "expand_own" (default: off).
#      : added: only private and public messages with string "://" will be caught
# 0.2  : add "://" in call to hook_print() (thanks to xt)
# 0.1  : internal release
#
# requirements:
# - URI::Find

use strict;
use URI::Find;

my $prgname	= "expand_url";
my $version	= "0.4";
my $description	= "Get information on a short URL. Find out where it goes.";
# default values
my %options = (	"shortener"             =>      "goo.gl|tiny.cc|bit.ly|is.gd|tinyurl.com",
                "expander"              =>      "http://expandurl.com/api/v1/?url=",
#                                               "http://api.longurl.org/v1/expand?url=";
                "color"                 =>      "blue",
                "expand_own"            =>      "off",
);

my %uris;
my $uri_only;

sub hook_print_cb{
my ( $data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message ) = @_;
my $tags2 = ",$tags,";
#return weechat::WEECHAT_RC_OK if ( not $tags2 =~ /,notify_[^,]+,/ ); # return if message is not from a nick.
#weechat::print("",$tags);

if ( $options{expand_own} eq "off" ){
  # get servername from buffer
  my $infolist = weechat::infolist_get("buffer",$buffer,"");
  weechat::infolist_next($infolist);
  my ($servername, undef) = split( /\./, weechat::infolist_string($infolist,"name") );
  weechat::infolist_free($infolist);

  my $my_nick = weechat::info_get( "irc_nick", $servername );		# get own nick
  if ( $tags2 =~ /,nick_[$my_nick,]+,/ ){
    return weechat::WEECHAT_RC_OK;
  }
}

  %uris = ();
  my $finder = URI::Find->new( \&uri_find_cb );
  my $how_many_found = $finder->find(\$message);		# search uri in message. result in $uri_only

  if ( $how_many_found >= 1 ){					# does message contains an url?
    my @uris = keys %uris;
    foreach my $uri (@uris) {
      if ($uri =~ m/$options{shortener}/) {		# shortener used?
	my $get_homepage = $options{expander} . $uri;	# add API + URL
	my $homepage = qq(perl -e 'use LWP::Simple; print get(\"$get_homepage\");');
	weechat::hook_process($homepage, 10000 ,"hook_process_cb",$buffer);
      }
    }
  }
return weechat::WEECHAT_RC_OK;
}

# callback from hook_process()
sub hook_process_cb {
my ($data, $command, $return_code, $out, $err) = @_;
  return weechat::WEECHAT_RC_OK if ( $return_code > 0 );

  my $buffer = $data;
  my @array = split(/\n/,$out);
  foreach ( @array ){
    $uri_only = "";
    my $finder = URI::Find->new( \&uri_find_one_cb );
    my $how_many_found = $finder->find(\$_);
      if ( $how_many_found >= 1 ){				# does message contains an url?
	  weechat::print($buffer, "[url]\t". weechat::color($options{color}) . $uri_only);
	last;
      }
}
  return weechat::WEECHAT_RC_OK;
}

# callback from URI::Find
sub uri_find_cb {
my ( $uri_url, $uri ) = @_;
  $uris{$uri}++;
return "";
}

sub uri_find_one_cb {
my ( $uri_url, $uri ) = @_;
  $uri_only = $uri;
return "";
}

# get settings or set them if they do not exists.
sub init_config{
    foreach my $option (keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option});
        }
        else{
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}
# changes in settings hooked by hook_config()?
sub toggle_config_by_set{
my ( $pointer, $name, $value ) = @_;
    $name = substr($name,length("plugins.var.perl.$prgname."),length($name));
    $options{$name} = $value;
return weechat::WEECHAT_RC_OK ;
}

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

init_config();

#weechat::hook_print("", "", "://", 1, "hook_print_cb", "");       # only public messages with string "://" will be caught!
weechat::hook_print("", "notify_message", "://", 1, "hook_print_cb", "");	# only public messages with string "://" will be caught!
weechat::hook_print("", "notify_private", "://", 1, "hook_print_cb", "");	# only private messages with string "://" will be caught!
weechat::hook_print("", "notify_highlight", "://", 1, "hook_print_cb", "");	# only highlight messages with string "://" will be caught!
weechat::hook_config("plugins.var.perl.$prgname.*", "toggle_config_by_set", "");# options changed?
