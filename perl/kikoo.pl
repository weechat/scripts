# This script is a port from the kikoo 
# script originaly written by Ozh for mIRC 
# and adapted by Yoda-BZH in perl
# 
# usage : /kikoo nick1 nick2 ...
# Author: Aymeric 'mRk' Derazey <mrk.dzey@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

weechat::register("kikoo" ,"0.1", "", "lame greetings");
weechat::add_command_handler("kikoo", kikoo, "send lame greetings on the current buffer");

sub kikoo
{
	my ($server,$data) = @_;
	$front = int(rand(13))+1;
	$back = int(rand(13))+1;
	while($back == $front) 
		{
			$back = int(rand(13))+1;
		}
	$xclam = int(rand(11))+2;
	$oo = int(rand(11))+2;
	$par = int(rand(11))+2;
	$output = "\002\003" . "$front,$back" . " KIKOO" . "O" x $oo . " $data " . "!" x $xclam . " :o" . ")" x $par ." ";
	weechat::command($output);
	return weechat::PLUGIN_RC_OK;
}
