# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Arvydas Sidorenko <asido4@gmail.com>
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
# Usage:
#   To show the bar item:
#     /set weechat.bar.nicklist.items "chatters,buffer_nicklist"
#   Config options:
#     /set plugins.var.perl.chatters.frame_color "red"
#     /set plugins.var.perl.chatters.nick_color "yellow"
#     /set plugins.var.perl.chatters.nick_timeout "600"
#
#
# History:
#
#   2012-05-01, Arvydas Sidorenko <asido4@gmail.com>
#       Version 0.1: initial release
#   2012-05-11, Arvydas Sidorenko <asido4@gmail.com>
#       Version 0.2: rewritten script using bar_item to store the chatters
#       instead of nicklist_group
#   2012-05-16, Arvydas Sidorenko <asido4@gmail.com>
#		Version 0.2.1: Bug fix: same channels under different servers share a
#		common chatter list.
#

use strict;
use warnings;

my $version         = "0.2.1";
my $script_name     = "chatters";

# A hash with groups where the chatters are going to be added
#
# Structure:
#   "#channel1" -- "nick1" -- last msg timestamp
#               `- "nick2" -- last msg timestamp
#               `- "nick3" -- last msg timestamp
#   "#channel2" -- "nick1" -- last msg timestamp
#               `- ...
my %chatter_groups          = ();
my $chatters_bar_item_name  = "chatters";

weechat::register($script_name, "Arvydas Sidorenko <asido4\@gmail.com>", $version, "GPL3", "Groups people into chatters and idlers", "", "");

# Check configs
my %default_settings = (frame_color    => "red",
                        nick_color     => "yellow",
                        nick_timeout   => 600);
for (keys %default_settings)
{
    weechat::config_set_plugin($_ => $default_settings{$_}) unless weechat::config_is_set_plugin($_);
}


# Close a channel
weechat::hook_signal("buffer_closing", "buffer_close_cb", "");
# Callback whenever someone leaves the channel
weechat::hook_signal("nicklist_nick_removed", "on_leave_cb", "");
# Callback whenever someone writes something in the channel
weechat::hook_signal("*,irc_in_PRIVMSG", "msg_cb", "");
# Chatter observer callback
weechat::hook_timer(60000, 0, 0, "cleanup_chatters", 0);
# On config change
weechat::hook_config("plugins.var.perl.${script_name}.*", "config_change_cb", "");

weechat::bar_item_new($chatters_bar_item_name, "chatters_bar_cb", "");

###############################################################################
# Buffer update callback
sub chatters_bar_cb
{
    # $_[0] - data
    # $_[1] - bar item
    # $_[2] - window
    my $str     =  "";
    my $buffer  = weechat::window_get_pointer($_[2], "buffer");
    my $channel = buf_to_channel_key($buffer);
    my $frame_color = weechat::color(weechat::config_get_plugin("frame_color"));
    my $nick_color = weechat::color(weechat::config_get_plugin("nick_color"));

    $str = $frame_color . "-- Chatters -----\n";

    if ($channel and $chatter_groups{$channel})
    {
        foreach my $nick (sort {uc($a) cmp uc($b)} keys %{ $chatter_groups{$channel} })
        {
            $str .= $nick_color . $nick . "\n";
        }
    }

    $str .= $frame_color . "-----------------\n";

    return $str;
}

###############################################################################
# Buffer close callback
sub buffer_close_cb
{
    # $_[0] - callback data (3rd hook arg)
    # $_[1] - signal (buffer_closing)
    # $_[2] - buffer pointer
    my $channel = buf_to_channel_key($_[2]);

    if ($chatter_groups{$channel})
    {
        delete $chatter_groups{$channel};
    }
}

###############################################################################
# Gets called when someones writes in a channel
sub msg_cb
{
    # $_[0] - callback data (3rd hook arg)
    # $_[1] - event name
    # $_[2] - the message:
    #    :Asido!~asido@2b600000.rev.myisp.com PRIVMSG #linux :yoo
    my $msg			= weechat::info_get_hashtable("irc_message_parse" => + { "message" => $_[2] });
	my $channel		= "";
	my ($server)	= split ",", $_[1];
	my $key			= "";

    # Ignore private messages
    unless ($msg->{channel} =~ /^#/)
    {
        return weechat::WEECHAT_RC_OK;
    }

	$key = format_key($server, $msg->{channel});

    $chatter_groups{$key}{$msg->{nick}} = time();
    weechat::bar_item_update($chatters_bar_item_name);

    return weechat::WEECHAT_RC_OK;
}

###############################################################################
# Gets called when someones leaves a channel
sub on_leave_cb
{
    # $_[0] - data
    # $_[1] - event name (nicklist_nick_removed)
    # $_[2] - 0x1ffda70,spoty (<buffer_pointer>,<nick>)
    my ($buf, $nick)    = split ",", $_[2];
    my $channel         = buf_to_channel_key($buf);

    if ($chatter_groups{$channel} and $chatter_groups{$channel}{$nick})
    {
        delete $chatter_groups{$channel}{$nick};
        weechat::bar_item_update($chatters_bar_item_name);
    }

    return weechat::WEECHAT_RC_OK;
}

###############################################################################
# Script config edit callback
sub config_change_cb
{
    # $_[0] - data
    # $_[1] - option name
    # $_[2] - new value
    my $opt = $_[1];

    if ($opt =~ /frame_color$/ or $opt =~ /nick_color$/)
    {
        weechat::bar_item_update($chatters_bar_item_name);
    }
    elsif ($opt =~ /nick_timeout$/)
    {
        cleanup_chatters();
    }
}

###############################################################################
# Removes nicks from chatter list who idle for too long
sub cleanup_chatters
{
    my $changed = 0;
    my $nick_timeout = weechat::config_get_plugin("nick_timeout");

    foreach my $channel (keys %chatter_groups)
    {
        foreach my $nick (keys %{ $chatter_groups{$channel} })
        {
            if (time() - $chatter_groups{$channel}{$nick} >= $nick_timeout)
            {
                delete $chatter_groups{$channel}{$nick};
                $changed = 1;
            }
        }
    }

    if ($changed)
    {
        weechat::bar_item_update($chatters_bar_item_name);
    }
}

###############################################################################
# Returns a key for use in chatter_groups
sub buf_to_channel_key
{
    my $buf		= shift;
	my $server	= weechat::buffer_get_string($buf, "localvar_server");
    my $channel	= weechat::buffer_get_string($buf, "localvar_channel");

	return format_key($server, $channel);
}

###############################################################################
# Formats a key out of server and channel to use in chatter_groups
sub format_key
{
	my $server	= shift;
	my $channel	= shift;

	# For unknown reason to me some channels have prepended #, some prepended ##
	# so the best to get rid of them to keep consistency
	$channel =~ /#*(.*)/;
	$channel = $1;

	return $server . "|" . $channel;
}

###############################################################################
#
sub _log
{
    my $msg = shift;

    weechat::print("", "${script_name}: ${msg}\n");
}
