#
# Copyright (c) 2009 by Oleg Melnik <boten@blindage.org>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# When you are got highlighted or private message, this script send a notification to remote address.
# This script sends simple data via a socket (_HEADER_ (nick_of_slapper) slapped on (channel) _END_HEADER_ _TEXT_ (text_of_message) _END_TEXT_)
# You can easily use your own program on remote machine to receive and show notifications. For example, download script which shows
# these message this libnotify: http://boten.blindage.org/?attachment_id=433
use IO::Socket;

my $version = "0.1";

#Default values of address of remote server
my $defaddress = "localhost";
my $defport = "10020";

#Register script
weechat::register("remnotify", $version, "", "Sends notification about highlighted and private msg to remote address");

#Set default settings on first register
weechat::set_plugin_config("remaddress", $defaddress) if (weechat::get_plugin_config("remaddress") eq "");
weechat::set_plugin_config("remport", $defport) if (weechat::get_plugin_config("remport") eq "");

#Bind events to our functions
weechat::add_message_handler("weechat_highlight", "on_highlight");
weechat::add_message_handler("weechat_pv", "on_pv");

sub on_highlight {
	my $message = $_[1];
	my $nick = $+ if $message =~ /([^:]+)!/;
	my $channel = $+ if $message =~ /PRIVMSG\s(#*\S+)\s.+/;
	my $text = $+ if $message =~ /PRIVMSG\s#*.+\s:(.+)$/;
	my $remaddress = weechat::get_plugin_config("remaddress");
	my $remport = weechat::get_plugin_config("remport");
	my $nsocket = IO::Socket::INET->new(Type=>SOCK_STREAM, Proto=>'tcp', PeerAddr => $remaddress, PeerPort => $remport)
	or die "Couldn't connect to remove server: $@";
	my $msg = "_HEADER_ $nick wrote to $channel _END_HEADER_ _TEXT_ $text _END_TEXT_";
	print $nsocket "$msg\n";
	close $nsocket;
	return weechat::PLUGIN_RC_OK;
}
sub on_pv {
	my $message = $_[1];
	on_highlight(" ", $message);
	return weechat::PLUGIN_RC_OK;
}