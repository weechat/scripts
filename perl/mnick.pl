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
# Set WeeChat and plugins options interactively.
#
# Description:
#
# This script allows to change your nick on the different networks you are
# connected, by appending or removing a suffix to your current nick on the
# network, based on the defined mask
# Command: /mnick [suffix]
# * if suffix is set and script enabled on network, will do a
#   /nick <current_nick><formatted_suffix>
# * if suffix is not set, will do a
#   /nick <previous_nick>
#
# Settings:
#  * plugins.var.perl.mnick.<network>_enabled : on/off
#  * plugins.var.perl.mnick.<network>_mask : default [%s]
#
# Example
# I'm CrazyCat on net1 and net3, GatoLoco on net2
#  * plugins.var.perl.mnick.net1_enabled : on
#  * plugins.var.perl.mnick.net1_mask : [%s]
#  * plugins.var.perl.mnick.net2_enabled : on
#  * plugins.var.perl.mnick.net2_mask : |%s
#  * plugins.var.perl.mnick.net3_enabled : off
#  * plugins.var.perl.mnick.net3_mask : [%s]
# /mnick AFK
# => CrazyCat[AFK] on net1, GatoLoco|AFK on net2, CrazyCat on net3
# /mnick
# => CrazyCat on net1 and net3, GatoLoco on net2
#
# History:
# 2016-05-23, CrazyCat <crazycat@c-p-f.org>:
#    version 0.3 : now, you can use alternate nick without doing
#    a /mnick before
# 2015-01-09, CrazyCat <crazycat@c-p-f.org>:
#    version 0.2 : corrected a stupid bug. Nick change is now only sent
#    to connected networks
# 2014-04-01, CrazyCat <crazycat@c-p-f.org>:
#    version 0.1 : first official version

weechat::register("mnick", "CrazyCat", "0.3", "GPL", "Multi Nick Changer", "", "");
weechat::hook_command(
	"mnick",
	"Multi Nick Changer",
	"mnick [extension]",
	"",
	"",
	"mnick_change",
	""
);

sub mnick_setup
{
	$infolist = weechat::infolist_get("irc_server", "", "");
	while (weechat::infolist_next($infolist))
	{
		my $name = weechat::infolist_string($infolist, "name");
		if (!weechat::config_is_set_plugin($name."_mask"))
		{
			weechat::config_set_plugin($name."_mask", "[%s]");
		}
		if (!weechat::config_is_set_plugin($name."_enabled"))
		{
			weechat::config_set_plugin($name."_enabled", "off");
		}
	}
	weechat::infolist_free($infolist);
}

sub mnick_change
{
	my ($data, $buffer, $text) = @_;
	my $newnick;
	my $nick;
	$infolist = weechat::infolist_get("irc_server", "", "");
	if ($text)
	{
		while (weechat::infolist_next($infolist))
		{
			my $name = weechat::infolist_string($infolist, "name");
			if (weechat::config_is_set_plugin($name."_enabled")
				&& weechat::config_get_plugin($name."_enabled") eq "on"
				&& weechat::infolist_integer($infolist, "is_connected")==1)
			{
				if (!weechat::config_is_set_plugin($name."_backnick")
					|| weechat::config_get_plugin($name."_backnick") eq "")
				{
					$nick = weechat::info_get('irc_nick', $name);
					weechat::config_set_plugin($name."_backnick", $nick);
				} else {
					$nick = weechat::config_get_plugin($name."_backnick");
				}
				$newnick = sprintf($nick . weechat::config_get_plugin($name."_mask"), $text);
				weechat::command($name, "/quote -server ".$name." nick ".$newnick);
			}
		}
	} else {
		while (weechat::infolist_next($infolist))
		{
			my $name = weechat::infolist_string($infolist, "name");
			$nick = weechat::info_get('irc_nick', $name);
			if (weechat::config_is_set_plugin($name."_enabled")
				&& weechat::config_get_plugin($name."_enabled") eq "on"
				&& weechat::infolist_integer($infolist, "is_connected")==1)
			{
				if (weechat::config_is_set_plugin($name."_backnick")
					&& weechat::config_get_plugin($name."_backnick") ne "") {
					$newnick = weechat::config_get_plugin($name."_backnick");
				} else {
					@nicks = split(',', weechat::infolist_string($infolist, "nicks"));
					$newnick = $nicks[0];
				}
				weechat::command($name, "/quote -server ".$name." nick ".$newnick);
				weechat::config_set_plugin($name."_backnick", "");
			}
		}
	}
	weechat::infolist_free($infolist);
	return weechat::WEECHAT_RC_OK;
}

mnick_setup;
