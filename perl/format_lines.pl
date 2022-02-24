# Copyright (c) 2013 by R1cochet DeltaXrho@gmail.com
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

# Changelog:
# 2020-05-09, FlashCode
#     version 1.6: add compatibility with new weechat_print modifier data (WeeChat >= 2.9)
# 2013-01-16, R1cochet
#     version 1.5: Fixed error where filtered lines would still show blank lines (found by Nei). Added option to hide prefix on formatted lines (suggested by Nei).
# 2013-01-15, R1cochet
#     version 1.4: Initial release


use strict;
use warnings;
use Text::Format;

my $VERSION = "1.6";
my $SCRIPT_DESC = "format the output of each line.";

weechat::register("format_lines", "R1cochet", $VERSION, "GPL3", $SCRIPT_DESC, "", "");

# initialize global variables
my $config_file;        # config pointer
my %config_section;     # config section pointer
my %config_options;     # init config options

sub init_config {
    $config_file = weechat::config_new("format_lines", "config_reload_cb", "");
    return if (!$config_file);

    $config_section{'lists'} = weechat::config_new_section($config_file, "lists", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'lists'}) {
        weechat::config_free($config_file);
        return;
    }
    $config_options{'blacklist_buffer'} = weechat::config_new_option($config_file, $config_section{'lists'}, "blacklist_buffer", "string",
                                                                       "Comma separated list of buffers to ignore.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'blacklist_nick'} = weechat::config_new_option($config_file, $config_section{'lists'}, "blacklist_nick", "string",
                                                                       "Comma separated list of nicks to ignore.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'blacklist_plugin'} = weechat::config_new_option($config_file, $config_section{'lists'}, "blacklist_plugin", "string",
                                                                       "Comma separated list of plugins to ignore.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'blacklist_server'} = weechat::config_new_option($config_file, $config_section{'lists'}, "blacklist_server", "string",
                                                                       "Comma separated list of servers to ignore.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'blacklist_tags'} = weechat::config_new_option($config_file, $config_section{'lists'}, "blacklist_tags", "string",
                                                                       "Comma separated list of tags to ignore.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'whitelist_buffer'} = weechat::config_new_option($config_file, $config_section{'lists'}, "whitelist_buffer", "string",
                                                                       "Comma separated list of buffers to always format.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);
    $config_options{'whitelist_nick'} = weechat::config_new_option($config_file, $config_section{'lists'}, "whitelist_nick", "string",
                                                                       "Comma separated list of nicks to always format.", "", 0, 0, "", "", 1, "", "", "", "", "", "",);

    $config_section{'look'} = weechat::config_new_section($config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config_section{'look'}) {
        weechat::config_free($config_file);
        return;
    }
    $config_options{'ignore_empty_lines'} = weechat::config_new_option($config_file, $config_section{'look'}, "ignore_empty_lines", "boolean",
                                                                       "Ignore lines with no text. (will not insert blank lines if there is no text)", "", 0, 0, "on", "on", 0, "", "", "", "", "", "",);
    $config_options{'print_blank_lines'} = weechat::config_new_option($config_file, $config_section{'look'}, "print_blank_lines", "boolean",
                                                                       "Print blank lines between each line of text.", "", 0, 0, "on", "on", 0, "", "", "", "", "", "",);
    $config_options{'number_of_lines'} = weechat::config_new_option($config_file, $config_section{'look'}, "number_of_lines", "integer",
                                                                       "Number of blank lines to print after each line of text.", "", 1, 4, "1", "1", 0, "", "", "", "", "", "",);
    $config_options{'hide_formatted_prefix'} = weechat::config_new_option($config_file, $config_section{'look'}, "hide_formatted_prefix", "boolean",
                                                                        "Prevent prefix from showing on formatted lines.", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);
    $config_options{'hide_timestamp'} = weechat::config_new_option($config_file, $config_section{'look'}, "hide_timestamp", "boolean",
                                                                       "Prevent timestamp from showing on inserted blank lines.", "", 0, 0, "on", "on", 0, "", "", "", "", "", "",);
    $config_options{'max_line_length'} = weechat::config_new_option($config_file, $config_section{'look'}, "max_line_length", "integer",
                                                                       "Maximum length of line before it is split. (Split occurs at max length or before)", "", 0, 256, "72", "72", 0, "", "", "", "", "", "",);
    $config_options{'indent_width'} = weechat::config_new_option($config_file, $config_section{'look'}, "indent_width", "integer",
                                                                       "Number of spaces to insert in front of first split line. (Paragraph style formatting)", "", 0, 16, "4", "4", 0, "", "", "", "", "", "",);
}

sub config_reload_cb {
    return weechat::config_reload($config_file);
}

sub config_read {
    return weechat::config_read($config_file);
}

sub config_write {
    return weechat::config_write($config_file);
}

### initialize config
init_config();
config_read();

my $text = Text::Format->new;
$text->columns(weechat::config_integer($config_options{'max_line_length'}));
$text->firstIndent(weechat::config_integer($config_options{'indent_width'}));

weechat::hook_config("format_lines.look.*", "config_cb", "");
sub config_cb {
    my ($data, $option, $value) = @_;
    return weechat::WEECHAT_RC_OK if ($option !~ /^format_lines\.look\./);
    if ($option =~ /^format_lines\.look\.max_line_length$/) {
        $text->columns($value);
    }
    if ($option =~ /^format_lines\.look\.indent_width$/) {
        $text->firstIndent($value);
    }
    return weechat::WEECHAT_RC_OK;
}


weechat::hook_modifier("weechat_print", "format_lines_cb", "");

sub nick_wl {
    my ($tags, $nick_list) = (shift, weechat::config_string($config_options{'whitelist_nick'}));
    my @nick_list = split ",", $nick_list;
    foreach(@nick_list) {
        return 1 if $tags =~ /.*,nick_\Q$_\E,/i;
    }
    return 0;
}
sub buffer_wl {
    my ($buffer_name, $buffer_list) = (shift, weechat::config_string($config_options{'whitelist_buffer'}));
    my @buffer_list = split ",", $buffer_list;
    foreach(@buffer_list) {
        return 1 if $buffer_name =~ /^\Q$_\E\z/i;
    }
    return 0;
}

sub buffer_bl {
    my ($buffer, $buffer_list) = (shift, weechat::config_string($config_options{'blacklist_buffer'}));
    my @buffer_list = split ",", $buffer_list;
    foreach(@buffer_list) {
        return 1 if $buffer =~ /^\Q$_\E\z/i;
    }
    return 0;
}
sub nick_bl {
    my ($tags, $nick_list) = (shift, weechat::config_string($config_options{'blacklist_nick'}));
    my @nick_list = split ",", $nick_list;
    foreach(@nick_list) {
        return 1 if $tags =~ /.*,nick_\Q$_\E,/i;
    }
    return 0;
}
sub plugin_bl {
    my ($plugin, $plugin_list) = (shift, weechat::config_string($config_options{'blacklist_plugin'}));
    my @plugin_list = split ",", $plugin_list;
    foreach(@plugin_list) {
        return 1 if $plugin =~ /^\Q$_\E\z/;
    }
    return 0;
}
sub server_bl {
    my ($server, $server_list) = (shift, weechat::config_string($config_options{'blacklist_server'}));
    my @server_list = split ",", $server_list;
    foreach(@server_list) {
        return 1 if $server =~ /^\Q$_\E\z/;
    }
    return 0;
}
sub tags_bl {
    my ($tags, $tags_list) = (shift, weechat::config_string($config_options{'blacklist_tags'}));
    my @tags_list = split ",", $tags_list;
    foreach(@tags_list) {
        return 1 if $tags =~ /\Q$_\E/i;
    }
    return 0;
}

sub print_blank_lines {
    my ($tag, $buffer, $tab) = (shift, shift, "\t\t");
    $tag =~ s/(^|,)nick_.*?(,|$)// if $tag =~ /irc_privmsg/;
    $tab = "\t" unless (weechat::config_boolean($config_options{'hide_timestamp'}));
    my $blank_lines = weechat::config_integer($config_options{'number_of_lines'});
    for (1..$blank_lines) {
        weechat::print_date_tags($buffer, 0, $tag, $tab);
    }
}

sub print_formatted {
    my ($buffer, $tags, $string) = @_;
    my ($prefix, $msg) = split /\t/, $string;

    if ($msg && length(weechat::string_remove_color($msg, "")) > weechat::config_integer($config_options{'max_line_length'}) ) {
        my @formatted_lines = split /\n/, $text->format($msg);
        for (my $i = 0; $i <= $#formatted_lines; $i++) {
            if ($i > 0 && weechat::config_boolean($config_options{'hide_formatted_prefix'})) {
                weechat::print_date_tags($buffer, 0, $tags, "\t$formatted_lines[$i]");
                print_blank_lines($tags, $buffer) if (weechat::config_boolean($config_options{'print_blank_lines'}));
            }
            else {
                weechat::print_date_tags($buffer, 0, $tags, "$prefix\t$formatted_lines[$i]");
                print_blank_lines($tags, $buffer) if (weechat::config_boolean($config_options{'print_blank_lines'}));
            }
        }
    }
    else {
        weechat::print_date_tags($buffer, 0, $tags, $string);
        print_blank_lines($tags, $buffer) if (weechat::config_boolean($config_options{'print_blank_lines'}));
    }
}

sub format_lines_cb {
    my ($data, $modifier, $modifier_data, $string) = @_;

    if (weechat::config_boolean($config_options{'ignore_empty_lines'})) {
        return $string if ($string eq "");
    }

    my $buffer = "";
    my $tags = "";
    if ($modifier_data =~ /0x/)
    {
        # WeeChat >= 2.9
        $modifier_data =~ m/([^;]*);(.*)/;
        $buffer = $1;
        $tags = $2;
    }
    else {
        # WeeChat <= 2.8
        $modifier_data =~ m/([^;]*);([^;]*);(.*)/;
        $buffer = weechat::buffer_search($1, $2);
        $tags = $3;
    }
    my $plugin = weechat::buffer_get_string($buffer, "plugin");
    my $server = weechat::buffer_get_string($buffer, "localvar_server");
    my $channel = weechat::buffer_get_string($buffer, "localvar_channel");

    my ($prefix, $msg) = split /\t/, $string;

    # whitelists
    if ($channel) {
        if (weechat::config_string($config_options{'whitelist_buffer'}) ne "") {
            if (buffer_wl($channel)) {
                print_formatted($buffer, $tags, $string);
                return "";
            }
        }
    }
    if ($tags =~ /nick_/) {
        if (weechat::config_string($config_options{'whitelist_nick'}) ne "") {
            if (nick_wl($tags)) {
                print_formatted($buffer, $tags, $string);
                return "";
            }
        }
    }
    # blacklists
    if (weechat::config_string($config_options{'blacklist_plugin'}) ne "") {
        if (plugin_bl($plugin)) {
            return $string;
        }
    }
    if (weechat::config_string($config_options{'blacklist_server'}) ne "") {
        if (server_bl($server)) {
            return $string;
        }
    }
    if ($channel) {
        if (weechat::config_string($config_options{'blacklist_buffer'}) ne "") {
            if (buffer_bl($channel)) {
                return $string;
            }
        }
    }
    if (weechat::config_string($config_options{'blacklist_tags'}) ne "") {
        if (tags_bl($tags)) {
            return $string;
        }
    }
    if (weechat::config_string($config_options{'blacklist_nick'}) ne "") {
        if (nick_bl($tags)) {
            return $string;
        }
    }

    print_formatted($buffer, $tags, $string);
    return "";
}
