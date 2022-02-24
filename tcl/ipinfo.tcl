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
# ---------------------------------------------
# Retrieve informations about an IP
#
# Usage : /ipinfo 132.54.12.32
# ---------------------------------------------
# History
# 2022-02-24 : Initial release


set SCRIPT_VERSION 1.0
set SCRIPT_NAME ipinfo

weechat::register $SCRIPT_NAME {CrazyCat <crazycat@c-p-f.org>} $SCRIPT_VERSION GPL3 {retrieve informations about an IP} {} {}
weechat::hook_command ipinfo {retrieve informations about an IP} {} {Do /set *ipinfo* for settings} {} ipinfo {}

if {[set output [weechat::config_get_plugin output]] eq ""} {
    weechat::config_set_plugin output "CITY (COUNTRY) - ISP "
}
if {[set output [weechat::config_get_plugin lang]] eq ""} {
    weechat::config_set_plugin lang "en"
}

# Small variables for utility
set mask(ipv4) {^(?:25[0-5]|2[0-4]\d|[0-1]?\d{1,2})(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d{1,2})){3}$}
set mask(ipv6) {^([[:xdigit:]]{1,4}(?::[[:xdigit:]]{1,4}){7}|::|:(?::[[:xdigit:]]{1,4}){1,6}|[[:xdigit:]]{1,4}:(?::[[:xdigit:]]{1,4}){1,5}|(?:[[:xdigit:]]{1,4}:){2}(?::[[:xdigit:]]{1,4}){1,4}|(?:[[:xdigit:]]{1,4}:){3}(?::[[:xdigit:]]{1,4}){1,3}|(?:[[:xdigit:]]{1,4}:){4}(?::[[:xdigit:]]{1,4}){1,2}|(?:[[:xdigit:]]{1,4}:){5}:[[:xdigit:]]{1,4}|(?:[[:xdigit:]]{1,4}:){1,6}:)$}

# this will be used later
variable private {"0.0.0.0/8" "10.0.0.0/8" "100.64.0.0/10" "127.0.0.0/8" "169.254.0.0/16" "172.16.0.0/12" \
   "192.0.0.0/24" "192.0.2.0/24" "192.88.99.0/24" "162.168.0.0/16" "192.168.18.0.0/15" "198.51.100.0/24" \
   "203.0.113.0/24" "224.0.0.4/24" "233.252.0.0/24" "240.0.0.0/4" "255.255.255.255/32"}


package require http

proc ipinfo {data buffer args} {
	set ip [join $args]
	if {![isip $ip]} {
		weechat::print $buffer [format "*** %s$ip%s is not a valid IP address" [weechat::color "red"] [weechat::color "default"]]
		return $::weechat::WEECHAT_RC_ERROR
	}
	set infos [getipdatas $ip]
	if {[dict get $infos status]=="fail"} {
		weechat::print $buffer [format "*** %sERROR%s : [dict get $infos message]" [weechat::color "red"] [weechat::color "default"]]
		return $::weechat::WEECHAT_RC_ERROR
	}
	set myout [string map [list "CITY" [dict get $infos city]\
		"COUNTRY" [dict get $infos country]\
		"ISP" [dict get $infos isp]\
		] [weechat::config_get_plugin output]]
	weechat::print $buffer [format "*** IP infos for %s$ip%s: $myout" [weechat::color "red"] [weechat::color "default"]]
	return $::weechat::WEECHAT_RC_OK
}

proc isip { ip } {
	if {[regexp $::mask(ipv4) $ip ipv4]} {
		return true
	} elseif {[regexp $::mask(ipv6) $ip ipv6]} {
		return true
	} else {
		return false
	}
}

proc getipdatas { ip } {
	::http::config -useragent "lynx"
	set ipq [http::geturl http://ip-api.com/json/$ip?fields=status,message,continent,country,city,zip,lat,lon,timezone,isp,org,reverse,mobile,proxy,hosting,query&lang=[weechat::config_get_plugin lang]]
	set data [json2dict [http::data $ipq]]
	::http::cleanup $ipq
	return $data
}

proc json2dict {JSONtext} {
	string range [string trim [string trimleft [string map {\t {} \n {} \r {} , { } : { } \[ \{ \] \}} $JSONtext] {\uFEFF}]] 1 end-1
}
