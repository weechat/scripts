#
# Copyright (C) 2013 Sascha Ohms <sasch9r@gmail.com>
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
# History:
#
# 2015-06-29, Matthew Cox <matthewcpcox@gmail.com>:
#     v0.2: fix for all buffer nesting levels
# 2013-10-19, Sascha Ohms <sasch9r@gmail.com>:
#     v0.1: script creation
#

use strict;

weechat::register('hl_here', 'Sascha Ohms', '0.2', 'GPL3', 'Show any highlights in the active buffer', '', '');

sub highlight_everywhere {
    my ($data, $buffer, $date, $tags, $disp, $hl, $prefix, $msg) = @_;
    my $bfname = weechat::buffer_get_string($buffer, 'name');
    my @chan = split(/\./, $bfname);

    if($hl == 1 && $buffer ne weechat::current_buffer()) {
        weechat::print_date_tags(weechat::current_buffer(), 0, 'no_log', $chan[-1]."\t".'<'.$prefix.weechat::color('default').'> '.$msg);
    }

    return weechat::WEECHAT_RC_OK;
}

weechat::hook_print('', '', '', 0, 'highlight_everywhere', '');
