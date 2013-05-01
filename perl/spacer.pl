#
# Copyright (c) 2013 by Biohazard <notbiohazard@zoho.com>
#
# adds a /spacer command that adds a space between every character in the text supplied
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
# usage:
# /spacer <text> - adds a space between every character in the text supplied
# can also be bound to a keybinding, so the effect applies to the text in the current buffer's input bar.
#
# history:
# 0.1 - Initial release

use warnings;
use strict;

$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;

my $script_name = "spacer";
my $author = "Biohazard";
my $version = "0.1";
my $license = "GPL3";
my $description = "Adds spaces between each character in the chat box";

weechat::register($script_name, $author, $version, $license, $description, "", "");
weechat::hook_command($script_name, $description, "", "", "", $script_name, "");

sub spacer {
	Encode::_utf8_on(my $text = $_[2]);
	Encode::_utf8_on($text = weechat::buffer_get_string(weechat::current_buffer, "input")) if not $text;

	$text = join(" ", split(//, $text));
	weechat::buffer_set(weechat::current_buffer, "input", $text);

	return weechat::WEECHAT_RC_OK;
}
