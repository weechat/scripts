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
	name => 'xclip',
	author => 'stfn <stfnmd@googlemail.com>',
	version => '0.2',
	license => 'GPL3',
	desc => 'Paste content from X11 clipboard',
);
my $TIMEOUT = 10 * 1000;
my $BUF = "";

weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
weechat::hook_command($SCRIPT{"name"}, $SCRIPT{"desc"}, "", "You should bind the command to a key, e.g. \"/key bind ctrl-V /xclip\"", "", "command_cb", "");

sub command_cb
{
	my ($data, $buffer, $args) = @_;
	weechat::hook_process("xclip -o", $TIMEOUT, "process_cb", $buffer);

	return weechat::WEECHAT_RC_OK;
}

sub process_cb
{
	my ($data, $command, $return_code, $out, $err) = @_;
	my $buffer = $data;

	if ($return_code == 0 && $out) {
		$BUF .= $out;
		$BUF =~ s/[\t\n\r]/ /g; # strip some escape sequences
		$BUF =~ s/ {2,}/ /g; # strip multiple spaces

		my $input = weechat::buffer_get_string($buffer, "input");
		my $pos = weechat::buffer_get_integer($buffer, "input_pos");
		substr($input, $pos, 0, $BUF);
		$pos += length($BUF);
		$BUF = "";

		weechat::buffer_set($buffer, "input", $input);
		weechat::buffer_set($buffer, "input_pos", $pos);
	} elsif ($return_code == weechat::WEECHAT_HOOK_PROCESS_RUNNING && $out) {
		$BUF .= $out;
	} else {
		$BUF = "";
	}

	return weechat::WEECHAT_RC_OK;
}
