#
# Copyright (c) 2006-2007 by FlashCode <flashcode@flashtux.org>
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
# Search for text in WeeChat disk log files.
#
# History:
# 2007-11-09, darkk <leon at darkk dot net.ru>:
#     version 0.3: regular expression is optonal now, bugfixes
# 2007-08-10, FlashCode <flashcode@flashtux.org>:
#     version 0.2: upgraded licence to GPL 3
# 2006-04-17, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release
#

use strict;

my $version = "0.3";

# default values in setup file (~/.weechat/plugins.rc)
my $default_max          = "8";
my $default_server       = "off";
my $default_grep_options = "-i";

# init script
if (not weechat::register("logsearch", $version, "", "Search for text in WeeChat disk log files")) {
    die;
}
weechat::set_plugin_config("max", $default_max) if (weechat::get_plugin_config("max") eq "");
weechat::set_plugin_config("server", $default_server) if (weechat::get_plugin_config("server") eq "");
weechat::set_plugin_config("grep_options", $default_grep_options) if (weechat::get_plugin_config("grep_options") eq "");

# add command handler /logsearch
weechat::add_command_handler("logsearch", "logsearch",
                             "search for text in WeeChat disk log files",
                             "[-n#] [text]",
                             "-n#: max number or lines to display\n"
                             ."text: regular expression (used by grep)\n\n"
                             ."Plugins options (set with /setp):\n"
                             ."  - perl.logsearch.max: max number of lines displayed by default\n"
                             ."  - perl.logsearch.server: display result on server "
                             ."buffer (if on), otherwise on current buffer\n"
                             ."  - perl.logsearch.grep_options: options to give to grep program",
                             "");

# /logsearch command
sub logsearch
{
    my $server = shift;
    my $args = shift;

    # read settings
    my $conf_max = weechat::get_plugin_config("max");
    $conf_max = $default_max if ($conf_max eq "");
    my $conf_server = weechat::get_plugin_config("server");
    $conf_server = $default_server if ($conf_server eq "");
    my $output_server = "";
    $output_server = $server if (lc($conf_server) eq "on");
    my $grep_options = weechat::get_plugin_config("grep_options");

    # build log filename
    my $buffer = weechat::get_info("channel", "");
    $buffer = ".".$buffer if ($buffer ne "");
    my $log_path = weechat::get_config("log_path");
    my $wee_home = weechat::get_info("weechat_dir", "");
    $log_path =~ s/%h/$wee_home/g;
    my $file = $log_path.$server.$buffer.".weechatlog";

    # parse log file
    if ($args =~ s/^\s*-n([0-9]+)\s*//)
    {
        $conf_max = $1;
    }
    foreach my $ref (\$args, \$file) {
        # this seems to be enough for bash, don't know about other shells
        ${$ref}  =~ s/(["\`\\\$])/\\\1/g;
    }
    my $command;
    if ($args) 
    {
        $command = "grep $grep_options \"$args\" \"$file\" 2>/dev/null | tail -n$conf_max";
    }
    else
    {
        $command = "tail -n$conf_max \"$file\" 2>/dev/null";
    }
    my $result = `$command`;

    # display result
    if ($result eq "")
    {
        weechat::print("Text not found in $file", "", $output_server);
        return weechat::PLUGIN_RC_OK;
    }
    my @result_array = split(/\n/, $result);
    weechat::print($_, "", $output_server) foreach(@result_array);

    return weechat::PLUGIN_RC_OK;
}
