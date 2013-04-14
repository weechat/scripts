# Copyright (c) 2010-2013 by Dmitry Kobylin <fnfal@academ.tsc.ru>
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
# show private/highlight messages with OSD
#
# 2013-03-28, Dmitry Kobylin <fnfal@academ.tsc.ru>:
#     version 0.2
#         * add /xosdtest command
#         * add config change hook
# 2010-09-29, Dmitry Kobylin <fnfal@academ.tsc.ru>:
#     version 0.1
#
#

set SCRIPT  xosdnotify
set VERSION 0.2

weechat::register $SCRIPT {Dmitry Kobylin <fnfal@academ.tsc.ru>} $VERSION GPL3 {show OSD on highlight/private message} {} {}
package require tclxosd

# default values
set default_blink on                ;# blink of OSD
set default_blink_interval 700      ;# interval of blinking
set default_blink_count 4           ;# count of blinks before OSD hides, don't set to 0
set default_lines 1		    ;# number of lines in OSD that can be shown simultaneously
set default_align {left bottom}     ;# align of OSD
set default_offset {16 16}          ;# padding of OSD from screen edge
set default_font -*-fixed-*-*-*-*-*-200-*-*-*-*-*-* ;# font of OSD
set default_encoding utf-8
set default_color #ffff00

# check config and set default values if necessary
if {[weechat::config_get_plugin blink]          eq ""} {weechat::config_set_plugin blink $default_blink}
if {[weechat::config_get_plugin blink_interval] eq ""} {weechat::config_set_plugin blink_interval $default_blink_interval}
if {[weechat::config_get_plugin blink_count]    eq ""} {weechat::config_set_plugin blink_count $default_blink_count}
if {[weechat::config_get_plugin lines]          eq ""} {weechat::config_set_plugin lines $default_lines}
if {[weechat::config_get_plugin align]          eq ""} {weechat::config_set_plugin align $default_align}
if {[weechat::config_get_plugin offset]         eq ""} {weechat::config_set_plugin offset $default_offset}
if {[weechat::config_get_plugin font]           eq ""} {weechat::config_set_plugin font $default_font}
if {[weechat::config_get_plugin encoding]       eq ""} {weechat::config_set_plugin encoding $default_encoding}
if {[weechat::config_get_plugin color]          eq ""} {weechat::config_set_plugin color $default_color}

# create xosd command
set osd [xosd::create [weechat::config_get_plugin lines]]
$osd align {*}[split [weechat::config_get_plugin align]]
$osd offset {*}[split [weechat::config_get_plugin offset]]
$osd font [weechat::config_get_plugin font]
$osd color [weechat::config_get_plugin color]

proc private_msg {osd signal msg} {
    if {[regexp {:(.+)!.+@.+\s+PRIVMSG\s.+:(.+)} \
       [weechat::iconv_from_internal [weechat::config_get_plugin encoding] $msg] -> nick msg]} {
	$osd text 0 "$nick: $msg"
    }

    set n [expr {[weechat::config_get_plugin blink_count] * 2}]
    weechat::hook_timer [weechat::config_get_plugin blink_interval] 0 $n timer [list $osd [incr ::key]]
    return $::weechat::WEECHAT_RC_OK
}

proc highlight_msg {osd signal msg} {
    $osd text 0 [weechat::iconv_from_internal [weechat::config_get_plugin encoding] $msg]

    set n [expr {[weechat::config_get_plugin blink_count] * 2}]
    weechat::hook_timer [weechat::config_get_plugin blink_interval] 0 $n timer [list $osd [incr ::key]]
    return $::weechat::WEECHAT_RC_OK
}

proc osd_test {osd buffer args} {
    if {[string length [set s [join $args]]] == 0} {
        set s test
    }
    $osd text 0 [weechat::iconv_from_internal [weechat::config_get_plugin encoding] $s]

    set n [expr {[weechat::config_get_plugin blink_count] * 2}]
    weechat::hook_timer [weechat::config_get_plugin blink_interval] 0 $n timer [list $osd [incr ::key]]
}

proc timer {data count} {
    lassign $data osd key

    # don't response to old timer
    if {$key < $::key} {
        return $::weechat::WEECHAT_RC_OK
    }

    if {[weechat::config_get_plugin blink] != "off"} {
	if {[$osd onscreen]} {
	    $osd hide
	} else {
	    $osd show
	}
    }
    if {$count == 0} {
	$osd hide
    }
    return $::weechat::WEECHAT_RC_OK
}

proc config_changed {osd option value} {
    $osd align {*}[split [weechat::config_get_plugin align]]
    $osd offset {*}[split [weechat::config_get_plugin offset]]
    $osd font [weechat::config_get_plugin font]
    $osd color [weechat::config_get_plugin color]

    return $::weechat::WEECHAT_CONFIG_OPTION_SET_OK_CHANGED
}

set ::key 0

# hook signals
weechat::hook_signal irc_pv private_msg $osd
weechat::hook_signal weechat_highlight highlight_msg $osd

# hook test command
weechat::hook_command xosdtest {show test message with OSD} {msg} {} {} osd_test $osd

# hook config change
weechat::hook_config plugins.var.tcl.$SCRIPT\.* config_changed $osd

