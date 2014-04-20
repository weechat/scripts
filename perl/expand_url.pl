#
# Copyright (c) 2011-2014 by Nils Görs <weechatter@arcor.de>
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
# 0.6  : fix regex for tag "nick_xxx"
# 0.5  : fix expand_own() tag "prefix_nick_ccc" (thanks roughnecks)
#      : add item "%nick" for prefix (idea by roughnecks)
#      : improved option "expander". Now more than one expander can be used (Thanks FiXato for some information about URLs)
#      : add new options: "prefix" and "color_prefix"
#      : add help text for options
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
# - apt-get install liburi-find-perl
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# This Script needs WeeChat 0.3.7 or higher
#
# You will find version 0.4:
# http://git.savannah.gnu.org/gitweb/?p=weechat/scripts.git;a=snapshot;h=7bb8ac448c25cf50829ff88d554765a4ff9470cd;sf=tgz

use strict;
use URI::Find;

my $PRGNAME	= "expand_url";
my $version	= "0.6";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENSE     = "GPL3";
my $DESC	= "Get information on a short URL. Find out where it goes.";
# default values
my %options = ( "shortener"             =>      "t.co/|goo.gl|tiny.cc|bit.ly|is.gd|tinyurl.com|ur1.ca",
                "expander"              =>      "http://untiny.me/api/1.0/extract?url= http://api.longurl.org/v1/expand?url= http://expandurl.com/api/v1/?url=",
                "color"                 =>      "blue",
                "prefix"                =>      "[url]",
                "color_prefix"          =>      "blue",
                "expand_own"            =>      "off",
);

my %option_desc = ( "shortener"         =>      "list of know shortener. \"|\" separated list",
                    "expander"          =>      "list of expander to use in script. Please use a space \" \" to separate expander",
                    "color"             =>      "color to use for expanded url in buffer",
                    "color_prefix"      =>      "color for prefix",
                    "prefix"            =>      "displayed prefix. You can use item \"\%nick\" to display nick in prefix (default: [url])",
                    "expand_own"        =>      "own shortened urls will be expanded (on|off)",
);

my %uris;
my @url_expander;                       # used expander
my $url_expander_number = 0;            # store number of expander
my $weechat_version;

sub hook_print_cb
{
    my ( $data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message ) = @_;
    my $tags2 = ",$tags,";
    #return weechat::WEECHAT_RC_OK if ( not $tags2 =~ /,notify_[^,]+,/ ); # return if message is not from a nick.
    #weechat::print("",$tags);

    if ( lc($options{expand_own}) eq "off" )
    {
        # get servername from buffer
        my $infolist = weechat::infolist_get("buffer",$buffer,"");
        weechat::infolist_next($infolist);
        my ($servername, undef) = split( /\./, weechat::infolist_string($infolist,"name") );
        weechat::infolist_free($infolist);

        my $my_nick = weechat::info_get( "irc_nick", $servername );   # get own nick
    }

#  if ( $tags2 =~ /,nick_[$my_nick,]+,/ ){
#  if ( $tags2 =~ m/(^|,)nick_[$my_nick,]+,/ ){
#      return weechat::WEECHAT_RC_OK;
#  }
#}

    my $nick_wo_suffix = ($tags2 =~ m/(^|,)nick_([^,]*)/) ? $2 : "";
    return weechat::WEECHAT_RC_OK if ($nick_wo_suffix eq "");

#    $tags =~ m/(^|,)nick_(.*),/;
#    my $nick_wo_suffix = $2;                                                                        # nickname without nick_suffix
  # search uri in message. result in %uris
  %uris = ();
  my $finder = URI::Find->new( \&uri_find_cb );
  my $how_many_found = $finder->find(\$message);

  if ( $how_many_found >= 1 ){                                  # does message contains an url?
    my @uris = keys %uris;
    foreach my $uri (@uris) {
        if ($uri =~ m/$options{shortener}/) {                   # known shortener used?
            if ( $url_expander_number > 0 ){                    # one expander exists?
                my $expand_counter = 0;
                weechat::hook_process("url:".$url_expander[$expand_counter].$uri, 10000 ,"hook_process_cb","$buffer $uri $expand_counter $nick_wo_suffix");
            }
        }
    }
  }
return weechat::WEECHAT_RC_OK;
}

# callback from hook_process()
sub hook_process_cb {
my ($data, $command, $return_code, $out, $err) = @_;
    my ($buffer, $uri, $expand_counter, $nick_wo_suffix) = split(" ",$data);

    # output not empty. Try to catch long URI
    if ($out ne ""){
        my $how_many_found = 0;
        my @array = split(/\n/,$out);                                   # split output to single raw lines
        foreach ( @array ){
            my $uri_only = "";
            my $finder = URI::Find->new(sub {
                my($uri, $orig_uri) = @_;
                $uri_only = $orig_uri;
                return $orig_uri;});
#            my $finder = URI::Find->new( \&uri_find_one_cb );
            $how_many_found = $finder->find(\$_);

            my $print_suffix = weechat::color($options{color_prefix}).
                                        $options{prefix};

            if ( $how_many_found >= 1 ){                                # does message contains at least one an url?
                if ( grep /$options{prefix}/,"\%nick" ){
                    my $nick_color = weechat::info_get('irc_nick_color', $nick_wo_suffix);# get nick-color
                    $print_suffix = $options{prefix};
                    my $nick_prefix =   $nick_color.
                                        $nick_wo_suffix.
                                        weechat::color($options{color_prefix});
                    $print_suffix =~ s/%nick/$nick_prefix/;
                    $print_suffix = weechat::color($options{color_prefix}).$print_suffix;
                }
                weechat::print($buffer, $print_suffix.
                                        "\t".
                                        weechat::color($options{color}).
                                        $uri_only);
                last;
            }
        }
    return weechat::WEECHAT_RC_OK;
    }elsif ($url_expander_number > 1){
        $expand_counter++;
        return weechat::WEECHAT_RC_OK if ($expand_counter > $url_expander_number - 1);
        weechat::hook_process("url:".$url_expander[$expand_counter].$uri, 10000 ,"hook_process_cb","$buffer $uri $expand_counter $nick_wo_suffix");
        return weechat::WEECHAT_RC_OK;
    }
}

# callback from URI::Find
sub uri_find_cb {
my ( $uri_url, $uri ) = @_;
  $uris{$uri}++;
return "";
}

#sub uri_find_one_cb {
#my ( $uri_url, $uri ) = @_;
#  $uri_only = $uri;
#return "";
#}

# get settings or set them if they do not exists.
sub init_config{
    foreach my $option (keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option});
            if ($option eq "expander"){
                @url_expander = split(/ /,$options{expander});      # split expander
                $url_expander_number = @url_expander;
            }
        }
        else{
            $options{$option} = weechat::config_get_plugin($option);
            if ($option eq "expander"){
                @url_expander = split(/ /,$options{expander});      # split expander
                $url_expander_number = @url_expander;
            }
        }
    }
    # create help text
    foreach my $option (keys %option_desc){
        weechat::config_set_desc_plugin( $option,$option_desc{$option} );
    }
}
# changes in settings hooked by hook_config()?
sub toggle_config_by_set{
my ( $pointer, $name, $value ) = @_;
    $name = substr($name,length("plugins.var.perl.$PRGNAME."),length($name));
    $options{$name} = $value;
    if ($name eq "expander"){
        @url_expander = split(/ /,$options{expander});      # split expander
        $url_expander_number = @url_expander;
    }
return weechat::WEECHAT_RC_OK ;
}

# first function called by a WeeChat-script.
weechat::register($PRGNAME, $AUTHOR, $version,$LICENSE, $DESC, "", "");

$weechat_version = weechat::info_get("version_number", "");
if (( $weechat_version eq "" ) or ( $weechat_version < 0x00030700 )){
    weechat::print("",weechat::prefix("error")."$PRGNAME: needs WeeChat >= 0.3.7. Please upgrade: http://www.weechat.org/");
    weechat::command("","/wait 1ms /perl unload $PRGNAME");
}

init_config();

#weechat::hook_print("", "", "://", 1, "hook_print_cb", "");       # only public messages with string "://" will be caught!
weechat::hook_print("", "notify_message", "://", 1, "hook_print_cb", "");       # only public messages with string "://" will be caught!
weechat::hook_print("", "notify_private", "://", 1, "hook_print_cb", "");       # only private messages with string "://" will be caught!
weechat::hook_print("", "notify_highlight", "://", 1, "hook_print_cb", "");     # only highlight messages with string "://" will be caught!
weechat::hook_print("", "notify_none", "://", 1, "hook_print_cb", "");          # check own messages
weechat::hook_config("plugins.var.perl.$PRGNAME.*", "toggle_config_by_set", "");# options changed?
