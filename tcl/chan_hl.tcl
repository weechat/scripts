# Copyright (c) 2009 by Dmitry Kobylin <fnfal@academ.tsc.ru>
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
#
# mark channels to highlight on each message
#
# this script is useful with other scripts like:
# beep.pl, welauncher.pl, notify.py etc
#
# to mark channels on strartup set option "default_list" of this
# script ( via iset.pl plugin (/iset command) or /setp command)
#
# by default if message appeared on current channel ( and channel
# is marked) highlight event is not sended, to prevent this behaviour
# set "hl_on_cur_chan" option to 1
#
# Usage:
#   /mark
#   /smark
#   /unmark
#   /unmark all
#   /set plugins.var.tcl.chan_hl.default_list "#chan1,#chan2,#somechan"
#   /set plugins.var.tcl.chan_hl.hl_on_cur_chan 0 
#
# TODO:
#   * separate channels with same name on different servers
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes
# 2009-04-17, Dmitry Kobylin <fnfal@academ.tsc.ru>:
#     version 0.1
#

set VERSION 0.2
set SCRIPT_NAME chan_hl

weechat::register \
    $SCRIPT_NAME {Karvur <fnfal@academ.tsc.ru>} $VERSION GPL3 \
    {mark channels to highlight on each message} {} {}

set MARK_LIST [list]
if {[set DEFAULT_LIST [weechat::config_get_plugin default_list]] eq ""} {
    weechat::config_set_plugin default_list "" 
} else {
    foreach element [split $DEFAULT_LIST ,] {lappend MARK_LIST $element}
}

if {[set HL_ON_CUR_CHAN [weechat::config_get_plugin hl_on_cur_chan]] eq ""} {
    weechat::config_set_plugin hl_on_cur_chan 0 
    set HL_ON_CUR_CHAN 0
}

proc config_changed {data option value} {
    set ::HL_ON_CUR_CHAN $value
    return $::weechat::WEECHAT_CONFIG_OPTION_SET_OK_CHANGED
}

proc mark_cmd {data buffer args} {
    set channel [weechat::buffer_get_string $buffer localvar_channel]
    if {[weechat::info_get irc_is_channel $channel] eq "1"} {
	if {[lsearch $::MARK_LIST $channel] == -1} {
	    lappend ::MARK_LIST $channel
	    weechat::print $buffer "channel \"$channel\" was appended to notify list"
	} else {
	    weechat::print $buffer "channel \"$channel\" already in notify list"
	}
    } else {
	weechat::print $buffer "this command must be executed on channel"
    }
    return $::weechat::WEECHAT_RC_OK
}

proc unmark_cmd {data buffer args} {
    if {[lindex $args 0] eq "all"} {
	set ::MARK_LIST [list]
	weechat::print $buffer "all channels was removed from notify list"
	return $::weechat::WEECHAT_RC_OK
    }

    set channel [weechat::buffer_get_string $buffer localvar_channel]
    if {[weechat::info_get irc_is_channel $channel] eq "1"} {
	if {[set index [lsearch $::MARK_LIST $channel]] != -1} {
	    set ::MARK_LIST [lreplace $::MARK_LIST $index $index]
	    weechat::print $buffer "channel \"$channel\" was removed from notify list"
	} else {
	    weechat::print $buffer "channel \"$channel\" not on notify list"
	}
    } else {
	weechat::print $buffer "this command must be executed on channel"
    }
    return $::weechat::WEECHAT_RC_OK
}

proc smark_cmd {data buffer args} {
    set channel [weechat::buffer_get_string $buffer localvar_channel]
    if {[weechat::info_get irc_is_channel $channel] eq "1"} {
	if {[set index [lsearch $::MARK_LIST $channel]] == -1} {
	    lappend ::MARK_LIST $channel
	    weechat::print $buffer "channel \"$channel\" was appended to notify list"
	} else {
	    set ::MARK_LIST [lreplace $::MARK_LIST $index $index]
	    weechat::print $buffer "channel \"$channel\" was removed from notify list"
	}
    } else {
	weechat::print $buffer "this command must be executed on channel"
    }
    return $::weechat::WEECHAT_RC_OK
}

proc signal_proc {data signal irc_msg} {
    if {[regexp {.+@.+\sPRIVMSG\s(#.+)\s:.+} $irc_msg wh channel] == 1} {
	if {[lsearch $::MARK_LIST $channel] != -1} {
	    set buffer [weechat::current_buffer]
	    if {$channel ne [weechat::buffer_get_string $buffer localvar_channel]} {
		weechat::print $buffer "$::SCRIPT_NAME: there is new message on $channel"
		weechat::hook_signal_send weechat_highlight $::weechat::WEECHAT_HOOK_SIGNAL_STRING $channel
	    } else {
		if {$::HL_ON_CUR_CHAN} {
		    weechat::hook_signal_send weechat_highlight $::weechat::WEECHAT_HOOK_SIGNAL_STRING $channel
		}
	    }
	}
    }
    return $::weechat::WEECHAT_RC_OK
}

weechat::hook_command mark {mark current channel to highlight on each message} {} {} {} mark_cmd {}
weechat::hook_command unmark {unmark channel(s)} {[all]} {} {} unmark_cmd {}
weechat::hook_command smark {unmark channel(s)} {[all]} {} {} smark_cmd {}
weechat::hook_signal *,irc_in_PRIVMSG signal_proc {}
weechat::hook_config plugins.var.tcl.chan_hl.hl_on_cur_chan config_changed {}

