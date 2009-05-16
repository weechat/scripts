#
# Copyright (c) 2009 by FlashCode <flashcode@flashtux.org>
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
# Launch external commands for signals.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes
# 2009-02-03, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release
#

use strict;

my $version = "0.2";
my $command_suffix = " >/dev/null 2>&1 &";

weechat::register("launcher", "FlashCode <flashcode\@flashtux.org>", $version, "GPL3",
                  "Launch external commands for signals", "", "");
weechat::hook_command("launcher", "Associate external commands to signals",
                      "[signal command] | [-del signal]",
                      " signal: name of signal, may begin or end with \"*\" to catch many signals (common signals are: \"weechat_highlight\", \"weechat_pv\")\n"
                      ."command: command to launch when this signal is received (you can separate many commands with \";\")\n"
                      ."   -del: delete commande associated to a signal\n\n"
                      ."Examples:\n"
                      ."  play a sound for highlights:\n"
                      ."    /launcher weechat_highlight alsaplay -i text ~/sound_highlight.wav\n"
                      ."  play a sound for private messages:\n"
                      ."    /launcher weechat_pv alsaplay -i text ~/sound_pv.wav\n"
                      ."  delete command for signal \"weechat_highlight\":\n"
                      ."    /launcher -del weechat_highlight\n\n"
                      ."For advanced users: it's possible to change commands with /set command:\n"
                      ."  /set plugins.var.perl.launcher.signal.weechat_highlight \"my command here\"",
                      "", "launcher_cmd", "");
weechat::hook_signal("*", "signal", "");

sub launcher_cmd
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    
    if ($args =~ /([^ ]+) (.*)/)
    {
        if ($1 eq "-del")
        {
            my $signal = $2;
            my $command = weechat::config_get_plugin("signal.${signal}");
            if ($command ne "")
            {
                weechat::config_unset_plugin("signal.${signal}");
                weechat::print("", "launcher: command deleted for signal ${signal}");
            }
            else
            {
                weechat::print("", weechat::prefix("error")."launcher: command not defined for signal \"${signal}\"");
            }
        }
        else
        {
            my $signal = $1;
            my $command = $2;
            if ($command =~ /^"(.*)"$/)
            {
                $command = $1;
            }
            weechat::config_set_plugin("signal.${signal}", "${command}");
            weechat::print("", "launcher: signal \"${signal}\" --> command: \"${command}\"");
        }
    }
    else
    {
        weechat::command($buffer, "/set plugins.var.perl.launcher.*");
    }
    return weechat::WEECHAT_RC_OK;
}

sub signal
{
    my $command = weechat::config_get_plugin("signal.$_[1]");
    system($command.$command_suffix) if ($command ne "");
    return weechat::WEECHAT_RC_OK;
}
