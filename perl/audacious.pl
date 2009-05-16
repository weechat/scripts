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

#
# Changelog:
#  0.1: first version
#  0.2: now you don't need the Song Change plugin enabled because
#  	it uses audtool --current-song to get the music name as nenolod
#  	suggested (http://boards.nenolod.net/index.php?showtopic=147). :)
#  0.3: port to WeeChat 0.3.0 by Trashlord
#

weechat::register ("audacious", "DeltaS4", "0.3", "GPL", "audacious-weechat current song script (usage: /music)", "", "");
weechat::hook_command("music", "", "", "", "", "audtool", "");

sub audtool {
    my ($data, $buffer, $args) = @_;
    chomp(my ($cs, $cslen) = (`audtool --current-song`, `audtool --current-song-length`));
    weechat::command($buffer, "/me is playing $cs ($cslen)");
    return weechat::WEECHAT_RC_OK;
}
