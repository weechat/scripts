#
# Copyright (c) 2006 by DeltaS4 <deltas4@gmail.com>
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

# This script is a port from the kikoo
# script originaly written by Ozh for mIRC
# and adapted by Yoda-BZH in perl
#
# usage : /kikoo nick1 nick2 ...
# Author: Aymeric 'mRk' Derazey <mrk.dzey@gmail.com>

# Changelog:
#  0.1: first version
#  0.2: port to WeeChat 0.3.0

weechat::register("kikoo" ,"mrk", "0.2", "GPL", "send lame greetings on the current buffer (usage: /kikoo nick)", "", "");
weechat::hook_command("kikoo", "", "", "", "", "kikoo", "");


sub kikoo
{
    my ($data, $buffer, $args) = @_;
    $front = int(rand(13))+1;
    $back = int(rand(13))+1;
    while($back == $front)
    {
	$back = int(rand(13))+1;
    }
    $xclam = int(rand(11))+2;
    $oo = int(rand(11))+2;
    $par = int(rand(11))+2;
    $output = "\002\003" . "$front,$back" . " KIKOO" . "O" x $oo . " $args " . "!" x $xclam . " :o" . ")" x $par ." ";
    weechat::command($buffer, $output);
    return weechat::WEECHAT_RC_OK;
}
