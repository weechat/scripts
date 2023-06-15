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
# 2023-06-15 : Improved help
# 2023-06-14 : Initial release

set SCRIPT_VERSION 1.1
set SCRIPT_NAME wttr
set SCRIPT_SUMMARY "Adds an item showing weather"

set SCRIPT_ARGS "loc <location>|format <1-4|format>|lang <ISO lang>"
set SCRIPT_ADESC "loc <location> : sets the new location\n\
:  example : /wttr loc Paris, France\n\
* format <format>: Formats of the output, can be an integer (predefined formats from 1 to 4) or a string (custom format).\n\
:  example : /wttr format %l:+%C+%t+(%f)+%w\n\
-- Main format variables --\n\
:  %l : location\n\
:  %c / %C / %x: weather condition (icon / textual)\n\
:  %t / %f : temperature (actual / feels like)\n\
:  %w : wind\n\
-- Predefined formats --\n\
:  1 - %c+%t\n\
:  2 - %c+%t+%w (with icons)\n\
:  3 - %l:+%c+%t\n\
:  4 - %l:%c+%t+%w (with icons)\n\
:  More explanation @ https://github.com/chubin/wttr.in#one-line-output\n\
* lang <ISO lang>: Defines the lang to use (EN for english, FR for french, ...). Default is your weechat lang.\n\
Think to add the \[wttr\] item to a bar. Example to add it to the status bar:\n\
  /eval /set weechat.bar.status.items \"\${weechat.bar.status.items},wttr\")"

weechat::register $SCRIPT_NAME {CrazyCat <crazycat@c-p-f.org>} $SCRIPT_VERSION GPL3 $SCRIPT_SUMMARY {} {}
weechat::hook_command wttr $SCRIPT_SUMMARY $SCRIPT_ARGS $SCRIPT_ADESC {loc || format || lang} wttr_cmds {}

# Management of settings
proc wttr_cmds {data buffer args} {
   set value [lassign {*}$args cmd]
   if {$cmd eq "" || [string tolower $cmd] eq "help"} {
      weechat::command "" "/help wttr"
      return $::weechat::WEECHAT_RC_OK
   }
   set cmd [string tolower $cmd]
   switch -nocase $cmd {
      "loc" {
         if {$value eq ""} {
            weechat::print $buffer "Use /wttr set loc City"
            return $weechat::WEECHAT_RC_ERROR
         }
         weechat::config_set_plugin city [join $value]
      }
      "format" {
         if {$value eq ""} {
            weechat::print $buffer "Using default format"
            set value 4
         }
         weechat::config_set_plugin wformat [join $value]
      }
      "lang" {
         if {$value eq ""} {
            weechat::print $buffer "Using weechat locale"
            set value [lindex [split [::weechat::info_get "locale" ""] "_"] 0]
         }
         weechat::config_set_plugin lang $value
      }
      default {
         weechat::print $buffer "Usage : /wttr <loc|format|lang> value"
         return $::weechat::WEECHAT_RC_ERROR
      }
   }
   wttr_timer_cb "" 0
   return $::weechat::WEECHAT_RC_OK
}

# Periodical call
proc wttr_timer_cb {data remaining_calls} {
   set city [string map {" " "%20"} [weechat::config_get_plugin city]]
   set url "http://wttr.in/$city?format=[weechat::config_get_plugin wformat]&lang=[weechat::config_get_plugin lang]"
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
