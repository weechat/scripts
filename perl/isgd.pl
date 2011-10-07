#
# Copyright (C) 2011  stfn <stfnmd@googlemail.com>
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
use CGI;

my %SCRIPT = (
	name => 'isgd',
	author => 'stfn <stfnmd@googlemail.com>',
	version => '0.2',
	license => 'GPL3',
	desc => 'Shorten URLs with is.gd on command',
);
my $TIMEOUT = 30 * 1000;
my %LOOKUP;

weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
weechat::hook_command($SCRIPT{"name"}, $SCRIPT{"desc"},
	"[<URL> ...]\n",
	"Without any URL arguments, the last found URL in the current buffer will be shortened.\n\n" .
	"URL: URL to shorten. More than one URL may be given.",
	"", "command_cb", "");

sub command_cb
{
	my ($data, $buffer, $args) = @_;
	my @URLs;

	# If URLs were provided in command arguments, shorten them
	while ($args =~ m{(https?://\S+)}gi) {
		push(@URLs, $1);
	}
	# Otherwise search backwards in lines of current buffer
	if (@URLs == 0) {
		my $infolist = weechat::infolist_get("buffer_lines", $buffer, "");
		while (weechat::infolist_prev($infolist) == 1) {
			my $message = weechat::infolist_string($infolist, "message");
			while ($message =~ m{(https?://\S+)}gi) {
				my $url = $1;
				push(@URLs, $url) unless ($url =~ m{^https?://is\.gd/}gi);
			}
			last if (@URLs > 0);
		}
		weechat::infolist_free($infolist);
	}

	foreach (@URLs) {
		my $cmd = "wget -qO - \"http://is.gd/create.php?format=simple&url=" . CGI::escape($_) . "\"";
		$LOOKUP{$cmd} = $_;
		weechat::hook_process($cmd, $TIMEOUT, "process_cb", $buffer);
	}

	return weechat::WEECHAT_RC_OK;
}

sub process_cb
{
	my ($data, $command, $return_code, $out, $err) = @_;
	my $buffer = $data;

	if ($return_code == 0 && $out) {
		my $domain = "";
		$domain = $1 if ($LOOKUP{$command} =~  m{^https?://([^/]+)}gi);
		weechat::print($buffer, "$out ($domain)");
	}

	return weechat::WEECHAT_RC_OK;
}
