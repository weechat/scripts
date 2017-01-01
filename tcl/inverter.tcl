# Copyright (c) 2016 by CrazyCat <crazycat@c-p-f.org>
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
# Invert all letters of your text
#
# Usage: /inv Your text here
#
# Output: <CrazyCat> ereh txet ruoY

set VERSION 0.1
set SCRIPT_NAME inverter

weechat::register $SCRIPT_NAME {CrazyCat <crazycat@c-p-f.org>} $VERSION GPL3 {invert all letters of your text} {} {}

weechat::hook_command inv {invert all letters of the text} {} {} {} invert_cmd {}

proc invert_cmd {data buffer args} {
	set text [join $args]
	set channel [weechat::buffer_get_string $buffer localvar_channel]
	if { $text eq "" } {
		weechat::print $buffer "You need a text to revert"
		return $::weechat::WEECHAT_RC_ERROR
	}
	set inv ""
	for {set i 0} {$i<=[string length $text]} {incr i} {
		append inv [string index $text end-$i]
	}
	weechat::command $buffer "/msg $channel $inv"
	return $::weechat::WEECHAT_RC_OK
}
