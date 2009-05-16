#
# Copyright (c) 2006-2009 by FlashCode <flashcode@flashtux.org>
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
# Play a sound for IRC "CTCP SOUND" message.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.7: sync with last API changes
# 2009-02-03, FlashCode <flashcode@flashtux.org>:
#     version 0.6: conversion to WeeChat 0.3.0+
#                  move commands for highlight and pv to new script launcher.pl
# 2007-09-17, FlashCode <flashcode@flashtux.org>:
#     version 0.5: fixed security problem with message parsing and execution
#                  of system command
# 2007-08-10, FlashCode <flashcode@flashtux.org>:
#     version 0.4: upgraded licence to GPL 3
# 2006-05-30, FlashCode <flashcode@flashtux.org>:
#     added plugin options for commands
# 2004-10-01, FlashCode <flashcode@flashtux.org>:
#     initial release
#

use strict;

my $version = "0.7";
my $command_suffix = " >/dev/null 2>&1 &";

# default values in setup file (~/.weechat/plugins.conf)
my $default_cmd_ctcp        = "alsaplay -i text \$filename";
my $default_sound_extension = ".wav";

weechat::register("sound", "FlashCode <flashcode\@flashtux.org>", $version, "GPL3",
                  "Sound for IRC \"CTCP SOUND\" message", "", "");
weechat::config_set_plugin("cmd_ctcp", $default_cmd_ctcp) if (weechat::config_get_plugin("cmd_ctcp") eq "");
weechat::config_set_plugin("sound_extension", $default_sound_extension) if (weechat::config_get_plugin("sound_extension") eq "");

weechat::hook_signal("*,irc_in_privmsg", "sound", "");
weechat::hook_command("sound", "Play sound on IRC channel", "filename", "filename: sound filename", "", "sound_cmd", "");

sub sound
{
    my ($data, $server, $signal) = ($_[0], $_[1], $_[2]);
    if ($signal =~ /(.*) PRIVMSG (.*)/)
    {
        my ($host, $msg) = ($1, $2);
	if ($host ne "localhost")
	{
            # sound received
            if ($msg =~ /\001SOUND ([a-zA-Z0-9-_\.]*)\001/)
            {
                my $filename = $1;
                my $command = weechat::config_get_plugin("cmd_ctcp");
                if ($command ne "")
                {
                    $command =~ s/(\$\w+)/$1/gee;
                    system($command.$command_suffix);
                }
            }
	}
    }
    return weechat::WEECHAT_RC_OK;
}

sub sound_cmd
{
    if ($#_ == 1)
    {
        my $extension = weechat::config_get_plugin("sound_extension");
        my $filename = $_[1];
        $filename .= $extension if ($extension ne "");
        my $command = weechat::config_get_plugin("cmd_ctcp");
        if ($command ne "")
        {
            $command =~ s/(\$\w+)/$1/gee;
            system($command.$command_suffix);
        }
        weechat::command($_[0], "/quote PRIVMSG ".weechat::buffer_get_string($_[0], "localvar_channel")." :\001SOUND $filename\001") if (@_);
    }
    return weechat::WEECHAT_RC_OK;
}
