# Copyright (C) 2011 Fabien Dupont <seeks@kafe-in.net>
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
# (this script requires WeeChat 0.3.6 or newer)
#
# Changelog :
#
# 2012-01-29, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: fix parsing of IRC message (now requires WeeChat >= 0.3.6)
# 2011-04-27: First working version !

use strict;
use URI::Escape;
use JSON;
use utf8;

my $SCRIPT_NAME = "seeks";
my $VERSION = "0.3";

# default values in setup file (~/.weechat/plugins.conf)
my %options = ( 'node'          => 'http://seeks.kafe-in.net',
                'nb_results'    => '3',
                'lang'          => 'en',
                'channels'      => '#seeks,#debian',
                'timeout'       => 60
);

weechat::register($SCRIPT_NAME, "Fabien Dupont <seeks\@kafe-in.net>", $VERSION, "GPL3", "Search terms on seeks node and display results (!seeks)", "", "");
init_config();

# Hooks
weechat::hook_config("plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "");
weechat::hook_signal("*,irc_in2_PRIVMSG", "message_callback", "in");
weechat::hook_command_run("/input return", "message_callback", "out");

# Incoming message
sub message_callback
{
        my ($data, $signal, $signal_data) = @_;
        my ($buffer, $channel, $text);

        # Parameter parsing
        if($data eq "out") {
                $buffer = weechat::buffer_get_string($signal, 'name');
                $channel = $buffer;
                $channel =~ s/^.+\.//;
                $text = weechat::buffer_get_string($signal, 'input');
        } elsif($data eq "in") {
                my $dict = weechat::info_get_hashtable("irc_message_parse", { "message" => $signal_data });
                $buffer = $signal;
                $buffer =~ s/,.*$//;
                $buffer = $buffer.".".$$dict{channel};
                $channel = $$dict{channel};
                $text = $$dict{arguments};
                $text =~ s/^[^:]+ : *//;
        }

        # check if this channel is autorized
        if($options{channels} =~ /(^|,)$channel(,|$)/ && $text =~ s/^!seeks +(.+)$//) {
                my $param = $1;
                weechat::hook_process("curl '".$options{node}.'/search?prs=on&expansion=1&output=json&action=expand&rpp='.$options{nb_results}.'&page=1&lang'.$options{lang}.'=&q='.uri_escape($param)."'", $options{timeout} * 1000, "exec_callback", $buffer);
        }

        return weechat::WEECHAT_RC_OK;
}

# Callback called when curl command is finished
sub exec_callback {
        my ($data, $command, $return_code, $out, $err) = @_;
        if(length $out) {
                my $json = JSON->new->allow_nonref;
                my %results = %{$json->decode($out)};
                my @snippets = @{$results{snippets}};
                my $i = 1;
                for my $snippet (@snippets) {
                        utf8::decode($$snippet{title});
                        weechat::command(weechat::buffer_search("irc", $data), "/say ".$i.": ".$$snippet{title}." ( ".$$snippet{url}." )");
                        $i++;
                }
        }
}

# Someone changed the config
sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".$SCRIPT_NAME."."), length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

# Load the config, saved value or default if unset
sub init_config
{
    foreach my $option (keys %options)
    {
        if (!weechat::config_is_set_plugin($option))
        {
            weechat::config_set_plugin($option, $options{$option});
        }
        else
        {
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}
