# Copyright (c) 2023 by CrazyCat <crazycat@c-p-f.org>
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
# Adds an item showing weather
#
# ---------------------------------------------
# History
# 2023-06-xx : Initial release

set SCRIPT_VERSION 1.0
set SCRIPT_NAME wttr

weechat::register $SCRIPT_NAME {CrazyCat <crazycat@c-p-f.org>} $SCRIPT_VERSION GPL3 {Adds an item showing weather} {} {}

if {[set city [weechat::config_get_plugin city]] eq ""} {
    weechat::config_set_plugin city "Paris"
}
if {[set wformat [weechat::config_get_plugin wformat]] eq ""} {
    weechat::config_set_plugin wformat 4
}
if {[set refresh [weechat::config_get_plugin refresh]] eq ""} {
    weechat::config_set_plugin refresh 300
}


proc wttr_get_cb { data command rc out err} {
   global wttr_value
   if {$out ne ""} {
      set wttr_value $out
      weechat::bar_item_update "wttr"
   }
   return $::weechat::WEECHAT_RC_OK
}

proc wttr_timer_cb {data remaining_calls} {
   set url "http://wttr.in/[weechat::config_get_plugin city]?format=[weechat::config_get_plugin wformat]"
    weechat::hook_process "url:${url}" 5000 "wttr_get_cb" ""
    return $::weechat::WEECHAT_RC_OK
}

weechat::hook_timer [expr [weechat::config_get_plugin refresh]*1000] 60 0 wttr_timer_cb ""
weechat::bar_item_new "wttr" "wttr_show" ""

proc wttr_show {args} {
   global wttr_value
   if {[info exists wttr_value] && $wttr_value ne ""} {
      return $wttr_value
   }
   return [weechat::config_get_plugin city]
}

