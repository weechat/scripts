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

use strict;
use warnings;

my $script_name = 'ragefaces';
my $author = 'stfn <stfnmd@googlemail.com>';
my $version = '1.0';
my $license = 'GPL3';
my $description = 'Send ragefac.es';

my %RAGEFACES = (
	lol => '23',
	troll => '100',
	okay => '43',
	gtfo => '67',
	fap => '137',
	lulz => '151',
	foreveralone => '45',
	fuckyea => '57',
	pedobear => '114',
	donotwant => '31',
	yuno => '106',
	instantclassy => '151',
	challengeaccepted => '127',
	actually => '148',
	areyoukiddingme => '126',
	fuck => '74',
	pfchch => '64'
);
my $URL = 'http://ragefac.es/';

# register script
weechat::register($script_name, $author, $version, $license, $description, "", "");

# hooks
weechat::hook_command("rage", "Send ragefac.es", "<rageface>", "Use TAB-completion for help with the available ragefaces.", completion(), "rage_cmd", "");

# subroutines
sub completion
{
	my $str = "";
	while (my ($key, $value) = each(%RAGEFACES)) {
		$str .= $key . "|";
	}
	chop($str);
	return $str;
}

sub rage_cmd
{
	my $buffer = $_[1];
	my $arg = $_[2];

	if (exists $RAGEFACES{$arg}) {
		weechat::command($buffer, $URL . $RAGEFACES{$arg})
	}
	elsif ($arg =~ /^\d+$/) {
		weechat::command($buffer, $URL . $arg);
	}
}
