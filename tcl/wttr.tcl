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
# Uses https://github.com/chubin/wttr.in
# ---------------------------------------------
# History
# 2023-05-29 : Initial release

set SCRIPT_VERSION 1.0
set SCRIPT_NAME wttr
set SCRIPT_SUMMARY "Adds an item showing weather"

weechat::register $SCRIPT_NAME {CrazyCat <crazycat@c-p-f.org>} $SCRIPT_VERSION GPL3 $SCRIPT_SUMMARY {} {}
weechat::hook_command wttr $SCRIPT_SUMMARY {} {Type /wttr help} {} wttr_cmds {}

# Management of settings
proc wttr_cmds {data buffer args} {
   lassign {*}$args cmd item value
   if {$cmd eq "" || [string tolower $cmd] eq "help"} {
      weechat::print $buffer "Usage : /wttr set <loc|format|lang> value"
      weechat::print $buffer "Example for location : /wttr set loc Paris,France"
      weechat::print $buffer "Format can be integer (1-4) or string as explained at https://github.com/chubin/wttr.in#one-line-output"
      weechat::print $buffer "Change language: /wttr set lang fr"
      return $::weechat::WEECHAT_RC_OK
   }
   set cmd [string tolower $cmd]
   if {$cmd ne "set"} {
      weechat::print $buffer "Use /wttr <set|help> when getting $cmd"
      return $::weechat::WEECHAT_RC_ERROR
   }
   switch -nocase $item {
      "loc" {
         if {$value eq ""} {
            weechat::print $buffer "Use /wttr set loc City"
            return $weechat::WEECHAT_RC_ERROR
         }
         weechat::config_set_plugin city [join $value]
         return $::weechat::WEECHAT_RC_OK
      }
      "format" {
         if {$value eq ""} {
            weechat::print $buffer "Using default format"
            set value 4
         }
         weechat::config_set_plugin wformat [join $value]
         return $::weechat::WEECHAT_RC_OK
      }
      "lang" {
         if {$value eq ""} {
            weechat::print $buffer "Using weechat locale"
            set value [lindex [split [::weechat::info_get "locale" ""] "_"] 0]
         }
         weechat::config_set_plugin lang $value
         return $::weechat::WEECHAT_RC_OK
      }
      default {
         weechat::print $buffer "Usage : /wttr set <loc|format|lang> value"
         return $::weechat::WEECHAT_RC_ERROR
      }
   }
}

# Periodical call
proc wttr_timer_cb {data remaining_calls} {
   set url "http://wttr.in/[weechat::config_get_plugin city]?format=[weechat::config_get_plugin wformat]&lang=[weechat::config_get_plugin lang]"
    weechat::hook_process "url:${url}" 5000 "wttr_get_cb" ""
    return $::weechat::WEECHAT_RC_OK
}

# Callback when getting datas from wttr.in
proc wttr_get_cb { data command rc out err} {
   global wttr_value
   if {$out ne ""} {
      set wttr_value $out
      weechat::bar_item_update "wttr"
   }
   return $::weechat::WEECHAT_RC_OK
}

# Update of the item
proc wttr_show {args} {
   global wttr_value
   if {[info exists wttr_value] && $wttr_value ne ""} {
      return $wttr_value
   }
   return "[weechat::config_get_plugin city] : no data"
}

# Initial settings
if {[set city [weechat::config_get_plugin city]] eq ""} {
    weechat::config_set_plugin city "Paris"
}
if {[set wformat [weechat::config_get_plugin wformat]] eq ""} {
    weechat::config_set_plugin wformat 4
}
if {[set refresh [weechat::config_get_plugin refresh]] eq ""} {
    weechat::config_set_plugin refresh 300
}
if {[set refresh [weechat::config_get_plugin lang]] eq ""} {
   set tlang [split [::weechat::info_get "locale" ""] "_"]
   weechat::config_set_plugin lang [lindex $tlang 0]
}

weechat::hook_timer [expr [weechat::config_get_plugin refresh]*1000] 60 0 wttr_timer_cb ""
weechat::bar_item_new "wttr" "wttr_show" ""
