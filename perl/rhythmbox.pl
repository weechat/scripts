#
# Copyright (c) 2009 by jnbek <jnbek@yahoo.com>
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

# See <rhythmbox_src_dir>/remote/dbus/rb-client.c in the parse_pattern
# function for a complete list of available properties.
my $album        = '%at';
my $year         = '%ay';
my $disc_number  = '%an';
my $genre        = '%ag';
my $title        = '%tt';
my $artist       = '%ta';
my $track_number = '%tN';
my $duration     = '%td';
my $elapsed      = '%te';
my $bitrate      = '%tb';

my $format = "$title by $artist on $album (Track: $track_number)($elapsed/$duration)($genre)($bitrate bps)";
weechat::register ("rhythmbox", "jnbek", "0.1", "GPL", "Rhythmbox-Weechat: display the song info currently playing (usage: /rb)", "", "");
weechat::hook_command("rb", "", "", "", "", "rb", "");

sub rb {
    my ($data, $buffer, $args) = @_; 
    chomp(my $cs = (`rhythmbox-client --print-playing-format "$format"`)); #Dbl Quotes required
    weechat::command($buffer, "/say Now Playing: $cs");
    return weechat::WEECHAT_RC_OK;
}
