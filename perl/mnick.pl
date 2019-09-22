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
# Command: /mnick [suffix] [away reason]
# * if suffix is set and script enabled on network, will do a
#   /nick <current_nick><formatted_suffix>
# * if suffix is not set, will do a
#   /nick <previous_nick>
#
# Settings:
#  * plugins.var.perl.mnick.<network>_enabled : on/off
#  * plugins.var.perl.mnick.<network>_mask : default [%s]
#  * plugins.var.perl.mnick.<network>_away : on/off
#
# Example
# I'm CrazyCat on net1 and net3, GatoLoco on net2
#  * plugins.var.perl.mnick.net1_enabled : on
#  * plugins.var.perl.mnick.net1_mask : [%s]
#  * plugins.var.perl.mnick.net1_away : off
#  * plugins.var.perl.mnick.net2_enabled : on
#  * plugins.var.perl.mnick.net2_mask : |%s
#  * plugins.var.perl.mnick.net1_away : off
#  * plugins.var.perl.mnick.net3_enabled : on
#  * plugins.var.perl.mnick.net3_mask : [%s]
#  * plugins.var.perl.mnick.net1_away : on
# /mnick Test
# => CrazyCat[Test] on net1, GatoLoco|Test on net2, CrazyCat on net3
# => Away status won't change
# /mnick AFK I'm no more here
# => CrazyCat[AFK] on net1, GatoLoco|AFK on net2, CrazyCat on net3
# => I'll be turned away on net2 and net3 with "I'm no more here" reason
# /mnick Test
# => CrazyCat[Test] on net1, GatoLoco|Test on net2, CrazyCat on net3
# => Away status won't change (keep the previous one)
# /mnick
# => CrazyCat on net1 and net3, GatoLoco on net2
# => away status is removed on net2 and net3
#
# History:
# 2019-09-12, CrazyCat <crazycat@c-p-f.org>
#	version 0.4 : add an optionnal away reason
# 2016-05-23, CrazyCat <crazycat@c-p-f.org>:
#    version 0.3 : now, you can use alternate nick without doing
#    a /mnick before
# 2015-01-09, CrazyCat <crazycat@c-p-f.org>:
#    version 0.2 : corrected a stupid bug. Nick change is now only sent
#    to connected networks
# 2014-04-01, CrazyCat <crazycat@c-p-f.org>:
#    version 0.1 : first official version

weechat::register("mnick", "CrazyCat", "0.4", "GPL", "Multi Nick Changer", "", "");

weechat::hook_command(
	"mnick",
	"Multi Nick Changer",
	"mnick [extension] [away reason]",
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
		if (!weechat::config_is_set_plugin($name."_away"))
		{
			weechat::config_set_plugin($name."_away", "off");
		}
	}
	weechat::infolist_free($infolist);
}

sub mnick_change
{
	my ($data, $buffer, $args) = @_;
	my $ext;
	my @reason;
	if ($args ne "") {
		($ext, @reason) = split(" ", $args);
	}
	my $newnick;
	my $nick;
	my @nicks;
	my $name;
	my $hasreason = @reason;
	$infolist = weechat::infolist_get("irc_server", "", "");
	if ($ext)
	{
		while (weechat::infolist_next($infolist))
		{
			$name = weechat::infolist_string($infolist, "name");
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
				$newnick = sprintf($nick . weechat::config_get_plugin($name."_mask"), $ext);
				weechat::command($name, "/quote -server ".$name." nick ".$newnick);
			}
			if ( $hasreason != 0
				&& weechat::infolist_integer($infolist, "is_connected")==1
				&& weechat::config_is_set_plugin($name."_away")
				&& weechat::config_get_plugin($name."_away") eq "on")
			{
				weechat::command($name, "/quote -server ".$name. " away :".join(" ", @reason));
			}
		}
	} else {
		while (weechat::infolist_next($infolist))
		{
			$name = weechat::infolist_string($infolist, "name");
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
			if ( weechat::infolist_integer($infolist, "is_connected")==1
				&& weechat::config_is_set_plugin($name."_away")
				&& weechat::config_get_plugin($name."_away") eq "on")
			{
				weechat::command($name, "/quote -server ".$name. " away");
			}
		}
	}
	weechat::infolist_free($infolist);
	return weechat::WEECHAT_RC_OK;
}

mnick_setup;
