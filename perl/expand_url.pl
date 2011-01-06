#
# Copyright (c) 2010 by Nils Görs <weechatter@arcor.de>
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
# 0.1: internal release
# 0.2: hook_print() changed (thanks to xt)
#
# requirements:
# - URI::Find

use strict;
use URI::Find;

my $prgname	= "expand_url";
my $version	= "0.2";
my $description	= "Get information on a short URL. Find out where it goes.";
# default values
my %default_options = (	"shortener"		=>	"tiny.cc|bit.ly|is.gd|tinyurl.com",
			"expander"		=>	"http://expandurl.com/api/v1/?url=",
#							"http://api.longurl.org/v1/expand?url=";
			"color"			=>	"blue",
);

my $uri_only;
my $orig_buffer;


sub hook_print_cb{
my ( $data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message ) = @_;
my $tags2 = ",$tags,";
return weechat::WEECHAT_RC_OK if ( not $tags2 =~ /,notify_[^,]+,/ ); # message is not from a nick?

  $uri_only = "";
  my $finder = URI::Find->new( \&uri_find_cb );
  my $how_many_found = $finder->find(\$message);		# search uri in message. result in $uri_only

  if ( $how_many_found eq 1 ){					# does message contains an url?
      if ($uri_only =~ m/$default_options{shortener}/) {	# shortener used?
	my $get_homepage = $default_options{expander} . $uri_only;# add API + URL
	my $homepage = qq(perl -e 'use LWP::Simple; print get(\"$get_homepage\");');
	$orig_buffer = $buffer;					# save 
	weechat::hook_process($homepage, 60000 ,"hook_process_cb","");
      }
  }
return weechat::WEECHAT_RC_OK;
}

# callback from hook_process()
sub hook_process_cb {
my ($data, $command, $return_code, $out, $err) = @_;
  return weechat::WEECHAT_RC_OK if ( $return_code > 0 );

  my @array = split(/\n/,$out);
  foreach ( @array ){
    $uri_only = "";
    my $finder = URI::Find->new( \&uri_find_cb );
    my $how_many_found = $finder->find(\$_);
      if ( $how_many_found eq 1 ){					# does message contains an url?
	weechat::print($orig_buffer, "[url]\t". weechat::color($default_options{color}) . $uri_only);
	last;
      }
}
  return weechat::WEECHAT_RC_OK;
}

sub uri_find_cb {
my ( $uri_url, $uri ) = @_;
  $uri_only = $uri;
return "";
}

sub toggled_by_set{
my ( $pointer, $option, $value ) = @_;
	if ($option eq "plugins.var.perl.$prgname.expander"){
		$default_options{expander} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.shortener"){
		$default_options{shortener} = $value;
	}elsif ($option eq "plugins.var.perl.$prgname.color"){
		$default_options{color} = $value;
	}
}

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $version,
                  "GPL3", $description, "", "");

# get settings or set them if they do not exists.
if (!weechat::config_is_set_plugin("shortener")){
  weechat::config_set_plugin("shortener", $default_options{shortener});
}else{
  $default_options{shortener} = weechat::config_get_plugin("shortener");
}
if (!weechat::config_is_set_plugin("expander")){
  weechat::config_set_plugin("expander", $default_options{expander});
}else{
  $default_options{expander} = weechat::config_get_plugin("expander");
}
if (!weechat::config_is_set_plugin("color")){
  weechat::config_set_plugin("color", $default_options{color});
}else{
  $default_options{color} = weechat::config_get_plugin("color");
}

weechat::hook_print("", "", "://", 1, "hook_print_cb", "");
weechat::hook_config("plugins.var.perl.$prgname.*", "toggled_by_set", "");	# options changed?
