#
# mslapper - weechat plugin for mass slap on current channel
# Copyright (C) 2008 Dmitry Kobylin <fnfal@academ.tsc.ru>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


my $version = "0.1";
my $nick_except;

weechat::register("MSlapper", $version, "", "Mass slap on current channel");
weechat::add_command_handler("mslap", "mslap_cmd");

sub mslap_cmd
{
	my $result_msg;
	my $server = $_[0];
	my $add_msg = $_[1];
	my $chan =  weechat::get_info("channel");
	my $nick = weechat::get_info("nick");
	$nick_except = weechat::get_plugin_config("nick_except");
	$nick_except = "\^".$nick."\$" if !$nick_except;
	my $nicks = weechat::get_nick_info($server, $chan);

	if ($nicks)
	{
		while (my ($nickname, $nickinfos) = each %$nicks)
		{
			unless( $nickname =~ /(^$nick$)|($nick_except)/ )
			{
				$result_msg .= $nickname." ";				
			}
	       	}
	}
	if($result_msg)
	{
		$result_msg .= $add_msg;
		weechat::command("/msg ".$chan." ".$result_msg);
	}
	return weechat::PLUGIN_RC_OK;
}


