#
# Copyright (C) 2006-2011 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2011 Nils Görs <weechatter@arcor.de>
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
# Speaker beep on highlight/private msg or new DCC.
#
# History:
# 2011-03-11, nils_2 <weechatter@arcor.de>:
#     version 0.6: add additional command options for dcc and highlight
# 2011-03-09, nils_2 <weechatter@arcor.de>:
#     version 0.5: add option for beep command and dcc
# 2009-05-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: sync with last API changes
# 2008-11-05, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: conversion to WeeChat 0.3.0+
# 2007-08-10, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: upgraded licence to GPL 3
# 2006-09-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

use strict;
my $SCRIPT_NAME = "beep";
my $VERSION = "0.6";

# default values in setup file (~/.weechat/plugins.conf)
my %options = ( "beep_highlight"         => "on",
                "beep_pv"                => "on",
                "beep_dcc"               => "on",
                "beep_command"           => "echo -n '\\a'",
                "beep_command_highlight" => "echo -n '\\a'",
                "beep_command_dcc"       => "echo -n '\\a'",
);

weechat::register($SCRIPT_NAME, "FlashCode <flashcode\@flashtux.org>", $VERSION,
                  "GPL3", "Speaker beep on highlight/private message and new DCC", "", "");
init_config();

weechat::hook_config("plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "");
weechat::hook_signal("weechat_highlight", "highlight", "");
weechat::hook_signal("irc_pv", "pv", "");
weechat::hook_signal("irc_dcc", "dcc", "");


sub highlight
{
    system($options{beep_command_highlight}) if ($options{beep_highlight} eq "on");
    return weechat::WEECHAT_RC_OK;
}

sub pv
{
    system($options{beep_command}) if ($options{beep_pv} eq "on");
    return weechat::WEECHAT_RC_OK;
}

sub dcc
{
    system($options{beep_command_dcc}) if ($options{beep_dcc} eq "on");
    return weechat::WEECHAT_RC_OK;
}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".$SCRIPT_NAME."."), length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

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
