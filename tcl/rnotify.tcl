#!/bin/sh
# Remote Notification Script
# by Gotisch <gotisch@gmail.com>
#
# With help of this script you can make weechat create notification bubbles
# in ubuntu or any other distribution that supports libnotify.
#
# How does it work?
#
# The script inside weechat will either call libnotify directly, or it will
# send the data to the "server" listening on a port which will call the
# libnotify executable and create the notification. This "remote" option
# is the main use of the script.
#
# Example 1: 	Weechat runs on the local pc
#		/tcl load rnotify.tcl
#		and set the port 
#		/set plugins.var.tcl.rnotify.port local
#
# Example 2:	Weechat runs on a remote pc and you login via ssh port you 
#		want to use is 4321
#		sh location/of/rnotify.tcl 4321 & ssh -R 4321:localhost:4321 username@host
#		on server you start weechat (or resume screen or whatever).
#		Then inside weechat
#		/tcl load rnotify.tcl
#		and set the port 
#		/set plugins.var.tcl.rnotify.port 4321
#
# General Syntax:	
#		In weechat
#		/set plugins.var.tcl.notify.port <portnumber to send notifies to/ or local>
#		As script
#		notify.tcl <portnumber to listen on>
#		if no port is given it will listen on 1234.
#
# Requirements:
#		libnotify (esp. notify-send executable)
#
# Possible problems:
#		It could be other programs send data to the notify port when using remote
#		mode. This will then lead to the following: either break the script, or 
#		make weird notification bubbles.
# \
exec tclsh "$0" ${1+"$@"}

if {[namespace exists ::weechat]} {
	# We have been called inside weechat
	namespace eval weechat::script::rnotify {
		weechat::register "rnotify" {Gotisch gotisch@gmail.com} 1.0 GPL3 {Sends highlights to (remote) client} {} {}
		proc highlight { data buffer date tags displayed highlight prefix message } {
			if {$highlight == 0} { return $::weechat::WEECHAT_RC_OK }
			set buffername [weechat::buffer_get_string $buffer short_name]
			if {$buffername != $prefix} {
				set buffername "$prefix in $buffername"
			} else {
				set buffername "$prefix in query"			
			}
			if {[weechat::config_get_plugin port] == "local"} {
				catch {
					exec notify-send -u normal -c IRC -i gtk-help "$buffername" "$message"
				}
			} else {
				catch {		
					set sock [socket -async localhost [weechat::config_get_plugin port]]
					puts $sock [list normal gtk-help $buffername $message]
					close $sock
				}
			}
			return $::weechat::WEECHAT_RC_OK
		}
		weechat::hook_print "" "notify_message" "" 1 [namespace current]::highlight {}
	}
} else {
	# We probably have been called from the shell
	set port 1234
	if {[llength $argv] == 1} { set port $argv }
	proc notify_server {port} {
		set s [socket -server accept $port]
		puts "Listening on $port for Connections..."
		vwait forever
	}
	proc accept {sock addr port} {
		fileevent $sock readable [list recieve $sock]
	}
	proc recieve {sock} {
		if {[eof $sock] || [catch {gets $sock line}]} {
			close $sock
		} else {
			foreach {urgency icon title text} $line {
				exec notify-send -u $urgency -c IRC -i $icon "$title" "$text"
			}
		}
	}
	notify_server $port
}
