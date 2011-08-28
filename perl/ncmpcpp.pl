#
# Copyright (C) 2011 by stfn <stfnmd@googlemail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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
# Development is currently hosted at
# https://github.com/stfnm/weechat-scripts
#

use strict;
use warnings;

my %SCRIPT = (
	name => 'ncmpcpp',
	author => 'stfn <stfnmd@googlemail.com>',
	version => '0.2',
	license => 'GPL3',
	desc => 'Control and "now playing" script for ncmpcpp',
);
my %OPTIONS = (
	format => '/me np: {%a "%b" (%y) - %t}|{%a - %t}|{%f}', # see `man ncmpcpp` for song format
);
my $TIMEOUT = 20 * 1000;
my $COMMANDS = "play|pause|toggle|stop|next|prev";

weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
weechat::hook_command($SCRIPT{"name"}, "Control ncmpcpp", "[$COMMANDS]", "without any arguments, \"now playing\" info is sent", $COMMANDS, "command_cb", "");
weechat::hook_config("plugins.var.perl." . $SCRIPT{"name"} . ".*", "config_cb", "");

init_config();

sub command_cb
{
	my ($data, $buffer, $args) = @_;
	my $cmd;

	if ($args =~ /^((play)|(pause)|(toggle)|(stop)|(next)|(prev))$/i) {
		$cmd = lc($1);
	}
	elsif ($args =~ /^\s*$/) {
		$cmd = "--now-playing '$OPTIONS{format}'";
	}

	weechat::hook_process("ncmpcpp $cmd", $TIMEOUT, "process_cb", $buffer) if ($cmd);

	return weechat::WEECHAT_RC_OK;
}

sub process_cb
{
	my ($data, $command, $return_code, $out, $err) = @_;

	if ($return_code >= 0 && $out) {
		chomp($out);
		weechat::command($data, $out);
	}

	return weechat::WEECHAT_RC_OK;
}

sub init_config
{
    foreach my $option (keys %OPTIONS) {
	if (!weechat::config_is_set_plugin($option)) {
		weechat::config_set_plugin($option, $OPTIONS{$option});
	}
	else {
		$OPTIONS{$option} = weechat::config_get_plugin($option);
	}
    }
}

sub config_cb
{
	my ($pointer, $name, $value) = @_;

	$name = substr($name, length("plugins.var.perl." . $SCRIPT{"name"} . "."), length($name));
	$OPTIONS{$name} = $value;

	return weechat::WEECHAT_RC_OK;
}
