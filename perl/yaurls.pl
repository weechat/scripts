# Copyright (c) 2012 by R1cochet R1cochet@hushmail.com
# All rights reserved
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
# yaURLs, version 1.9, for weechat version 0.3.7 or later
# will shorten URL's in channels
#
# Shorten URL's using any of the following services:
# durl.me, is.gd, ln-s.net, lytn.it, metamark.net, sapo.pt, safe.mn, tinyURL.com
#
# Default color theme in 256color terminal
# header: 46
# prefix/suffix: *200
# url: *190
# domain: 196
#
#
# Changelog:
# 2012-09-21, R1cochet
#     version 1.9: Added more shortening services
# 2012-03-09, Sebastien Helleu <flashcode@flashtux.org>
#     version 1.8: Fix reload of config file
# 2012-03-08, R1cochet
#     version 1.7: Removed need for Regexp::Common and URI::Escape modules. Cleaned up some code
# 2012-03-04, R1cochet
#     version 1.6: Fixed error with twitter links not being recognized. Added module URI::Escape to properly format URL's before shortening
# 2012-02-28, R1cochet
#     version 1.5: Initial release

use strict;
use warnings;

my $SCRIPT_NAME = "yaurls";
my $SCRIPT_AUTHOR = "R1cochet";
my $VERSION = "1.9";
my $SCRIPT_LICENSE = "GPL3";
my $SCRIPT_DESC = "yes, another URL shortener";

# initialize global variables
my $config_file;        # config pointer
my %config_section;     # config section pointer
my %config_options;     # init config options
my $incoming_nick = "";

my %Unsafe = (RFC3986 => qr/[^A-Za-z0-9\-\._~]/,);
my %escapes;
for (0..255) {
    $escapes{chr($_)} = sprintf("%%%02X", $_);
}

weechat::register($SCRIPT_NAME, $SCRIPT_AUTHOR, $VERSION, $SCRIPT_LICENSE, $SCRIPT_DESC, "", "");

### initial config
sub init_config {
    $config_file = weechat::config_new("yaurls", "config_reload_cb", "");
    return if (!$config_file);

    # create new section in config file
    $config_section{'blacklists'} = weechat::config_new_section($config_file, "blacklists", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'blacklists'}) {
        weechat::config_free($config_file);
        return;
    }
    # add the options to the section
    $config_options{'channel_blacklist'} = weechat::config_new_option($config_file, $config_section{'blacklists'}, "channel_blacklist", "string",
                                                                       "Comma seperated list of Channels to ignore", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'nick_blacklist'} = weechat::config_new_option($config_file, $config_section{'blacklists'}, "nick_blacklist", "string",
                                                                       "Comma seperated list of Nicks to ignore", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'server_blacklist'} = weechat::config_new_option($config_file, $config_section{'blacklists'}, "server_blacklist", "string",
                                                                       "Comma seperated list of Servers to ignore", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'string_blacklist'} = weechat::config_new_option($config_file, $config_section{'blacklists'}, "string_blacklist", "string",
                                                                       "Comma seperated list of Strings to ignore", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'url_blacklist'} = weechat::config_new_option($config_file, $config_section{'blacklists'}, "url_blacklist", "string",
                                                                       "Comma seperated list of URL's to ignore", "", 0, 0, "youtube.com", "youtube.com", 1, "", "", "", "", "", "",);

    $config_section{'colors'} = weechat::config_new_section($config_file, "colors", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'colors'}) {
        weechat::config_free($config_file);
        return;
    }
    $config_options{'header_color'} = weechat::config_new_option($config_file, $config_section{'colors'}, "header_color", "color",
                                                                       "Set the color of the header", "", 0, 0, "green", "green", 0, "", "", "", "", "", "",);
    $config_options{'prefix_color'} = weechat::config_new_option($config_file, $config_section{'colors'}, "prefix_suffix_color", "color",
                                                                       "Set the color of the prefix and suffix", "", 0, 0, "magenta", "magenta", 0, "", "", "", "", "", "",);
    $config_options{'url_color'} = weechat::config_new_option($config_file, $config_section{'colors'}, "url_color", "color",
                                                                       "Set the color of the tinyURL link", "", 0, 0, "yellow", "yellow", 0, "", "", "", "", "", "",);
    $config_options{'domain_color'} = weechat::config_new_option($config_file, $config_section{'colors'}, "domain_color", "color",
                                                                       "Set the color of the domain name", "", 0, 0, "blue", "blue", 0, "", "", "", "", "", "",);

    $config_section{'engine'} = weechat::config_new_section($config_file, "engine", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'engine'}) {
        weechat::config_free($config_file);
        return;
    }
    $config_options{'service'} = weechat::config_new_option($config_file, $config_section{'engine'}, "service", "integer",
                                                                       "Set which shortener service to use (durl = durl.me, is.gd = is.gd, ln-s = ln-s.net, lytn = lytn.it, ".
                                                                       "metamark = metamark.net, punyURL = sapo.pt, safe = safe.mn, tinyURL = tinyURL.com)",
                                                                       "durl|is.gd|ln-s|lytn|metamark|punyURL|safe|tinyURL", 0, 0, "tinyURL", "tinyURL", 0, "", "", "", "", "", "");
    $config_options{'convert_own'} = weechat::config_new_option($config_file, $config_section{'engine'}, "convert_own", "boolean",
                                                                       "Convert own links sent to buffer", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);
    $config_options{'maximum_length'} = weechat::config_new_option($config_file, $config_section{'engine'}, "maximum_length", "integer",
                                                                       "Set the maximum length of URL's to be converted (anything equal to or larger will be converted)", "", 20, 500, "35", "35", 0, "", "", "", "", "", "");
    $config_options{'timeout'} = weechat::config_new_option($config_file, $config_section{'engine'}, "timeout", "integer",
                                                                       "Set the maximum time limit for fetching the short URL (time in seconds)", "", 10, 120, "20", "20", 0, "", "", "", "", "", "");

    $config_section{'look'} = weechat::config_new_section($config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'look'}) {
        weechat::config_free($config_file);
        return;
    }
    $config_options{'header'} = weechat::config_new_option($config_file, $config_section{'look'}, "header", "string",
                                                                       "Set the header string", "", 0, 0, "yaURLs", "yaURLs", 1, "", "", "", "", "", "",);
    $config_options{'header_prefix'} = weechat::config_new_option($config_file, $config_section{'look'}, "header_prefix", "string",
                                                                       "Set the header prefix", "", 0, 0, "{", "{", 1, "", "", "", "", "", "",);
    $config_options{'header_suffix'} = weechat::config_new_option($config_file, $config_section{'look'}, "header_suffix", "string",
                                                                       "Set the header suffix", "", 0, 0, "}~>", "}~>", 1, "", "", "", "", "", "",);
    $config_options{'format'} = weechat::config_new_option($config_file, $config_section{'look'}, "format", "string",
                                                                       "Set the print format (%H = Header, %U = tinyURL, %D = Domain)", "", 0, 0, "%H %U %D", "%H %U %D", 0, "", "", "", "", "", "",);
}
# intit callbacks
sub config_reload_cb {      # reload config file
    return weechat::config_reload($config_file);
}

sub config_read {           # read my config file
    return weechat::config_read($config_file);
}

sub config_write {          # write to my config file
    return weechat::config_write($config_file);
}

init_config();              # load config
config_read();              # get options if already in config file

weechat::hook_print( "", "irc_privmsg", "://", 1, "print_hook_cb", "");         # Hook into print

sub build_header {
    my $header = weechat::color(weechat::config_color($config_options{'header_color'})) . weechat::config_string($config_options{'header'}) . weechat::color("reset");
    $header = weechat::color(weechat::config_color($config_options{'prefix_color'})) . weechat::config_string($config_options{'header_prefix'}) . weechat::color("reset") . $header;
    $header = $header . weechat::color(weechat::config_color($config_options{'prefix_color'})) . weechat::config_string($config_options{'header_suffix'}) . weechat::color("reset");
    return $header;
}

sub black_list1 {       # match url, string
    my ($string, $black_list) = @_;
    my @black_list = split ",", $black_list;
    foreach(@black_list) {
        return 1 if $string =~ /\Q$_\E/i;
    }
    return 0;
}

sub black_list2 {       # match nick, server, channel; front to end
    my ($string, $black_list) = @_;
    my @black_list = split ",", $black_list;
    foreach(@black_list) {
        return 1 if $string =~ /^\Q$_\E\z/;
    }
    return 0;
}

sub uri_escape {
    my $url = shift;
    utf8::encode($url);
    $url =~ s/($Unsafe{RFC3986})/$escapes{$1}/ge;
    return $url;
}

sub service_url {
    my $url = shift;
    $url = uri_escape($url);

    if (weechat::config_string($config_options{'service'}) eq "durl") {
        $url = "http://durl.me/api/Create.do?longurl=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "is.gd") {
        $url = "http://is.gd/create.php?format=simple&url=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "ln-s") {
        $url = "http://ln-s.net/home/api.jsp?url=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "lytn") {
        $url = "http://lytn.it/api.php?rel=2&link=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "metamark") {
        $url = "http://metamark.net/api/rest/simple?long_url=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "punyURL") {
        $url = "http://services.sapo.pt/PunyURL/GetCompressedURLByURL?url=$url";
    }
    elsif (weechat::config_string($config_options{'service'}) eq "safe") {
        $url = "http://safe.mn/api/?format=text&url=$url";
    }
    else {
        $url = "http://tinyurl.com/api-create.php?url=$url";
    }

    return $url;
}

sub process_cb {
    my ($buffer_domain, $command, $return_code, $out, $err) = @_;

    if ($return_code != 0) { # weechat::WEECHAT_HOOK_PROCESS_ERROR
        weechat::print("", "Error with command: $command");
        weechat::print("", "An error occured: $err") if ($err ne "");
        weechat::print("", "ret code: $return_code");
    }
    elsif ($out) {
        my ($buffer, $domain) = split "_:_", $buffer_domain, 2;
        my $header = build_header();
        $domain = weechat::color(weechat::config_color($config_options{'domain_color'})) . "($domain)" . weechat::color("reset");

        if (weechat::config_string($config_options{'service'}) eq "durl") {
            ($out) = $out =~ m/(http:\/\/durl\.me\/\w+)/;
        }
        elsif (weechat::config_string($config_options{'service'}) eq "ln-s") {
            $out =~ s/^(\d{3}\s)|\n*$//g;
        }
        elsif (weechat::config_string($config_options{'service'}) eq "punyURL") {
            weechat::print("", "punyURL called");
            ($out) = $out =~ m/.+\<ascii\>(.+)\<\/ascii\>/;
        }
        elsif (weechat::config_string($config_options{'service'}) eq "safe") {
            $out =~ s/\n*//g;
        }

        my $short_url = weechat::color(weechat::config_color($config_options{'url_color'})) . $out . weechat::color("reset");
        my $tiny_url = weechat::config_string($config_options{'format'});

        $tiny_url =~ s/%H/$header/;
        $tiny_url =~ s/%U/$short_url/;
        $tiny_url =~ s/%D/$domain/;
        weechat::print($buffer, "$tiny_url");
    }
    return weechat::WEECHAT_RC_OK;
}

sub print_hook_cb {
    my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $msg) = @_;
    return weechat::WEECHAT_RC_OK if ($displayed != 1);     # return if initial message wont be shown

    if ((weechat::config_string($config_options{'string_blacklist'})) ne "") {      # check message against "string blacklist"
        return weechat::WEECHAT_RC_OK if (black_list1($msg, weechat::config_string($config_options{'string_blacklist'})));       # return if string is blacklisted
    }

    my $hdata = weechat::hdata_get("buffer");
    my $buffer_name = weechat::hdata_string($hdata, $buffer, "name");
    my ($server, $channel) = split /\./, $buffer_name;  # can be done with a match
    $channel =~ s/#//;

    if ((weechat::config_string($config_options{'server_blacklist'})) ne "") {      # check message against "server blacklist"
        return weechat::WEECHAT_RC_OK if (black_list2($server, weechat::config_string($config_options{'server_blacklist'})));    # return if server is blacklisted
    }

    if ((weechat::config_string($config_options{'channel_blacklist'})) ne "") {     # check message against "channel blacklist"
        return weechat::WEECHAT_RC_OK if (black_list2($channel, weechat::config_string($config_options{'channel_blacklist'})));  # return if nick is blacklisted
    }

    ($incoming_nick = $tags) =~ s/.*nick_//i;
    $incoming_nick =~ s/,.*//i;
    my $own_nick = weechat::info_get("irc_nick", $server);

    if (!weechat::config_boolean($config_options{'convert_own'})) {                 # check if converting own
        return weechat::WEECHAT_RC_OK if $incoming_nick =~ /^\Q$own_nick\E\z/;
    }

    if ((weechat::config_string($config_options{'nick_blacklist'})) ne "") {        # check message against "nick blacklist"
        return weechat::WEECHAT_RC_OK if (black_list2($incoming_nick, weechat::config_string($config_options{'nick_blacklist'})));        # return if nick is blacklisted
    }

    my @msg = split " ", $msg;
    foreach(@msg) {
        if ($_ =~ /^(ht|f)tp/ && $_ =~ m|(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?|) {
            next if (length($_) <= weechat::config_integer($config_options{'maximum_length'}));        # skip if url shorter than max

            if (weechat::config_string($config_options{'url_blacklist'}) ne "") {
                next if (black_list1($_, weechat::config_string($config_options{'url_blacklist'})));     # skip if url is blacklisted
            }
            my $buffer_domain = $buffer."_:_$2";
            my $url = service_url($_);

            weechat::hook_process("url:$url", weechat::config_integer($config_options{'timeout'}) * 1000, "process_cb", $buffer_domain);
        }
    }
    return weechat::WEECHAT_RC_OK;
}
