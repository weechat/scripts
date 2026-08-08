#
# SPDX-FileCopyrightText: 2026 CrazyCat <crazycat@c-p-f.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

set SCRIPT_NAME "emphasys"
set SCRIPT_AUTHOR "CrazyCat <crazycat@c-p-f.org>"
set SCRIPT_VERSION "1.0"
set SCRIPT_LICENSE "GPL3"
set SCRIPT_DESC "Replaces *text* whith bold and /text/ with italic (or reverse)"

::weechat::register $SCRIPT_NAME $SCRIPT_AUTHOR $SCRIPT_VERSION $SCRIPT_LICENSE $SCRIPT_DESC {} {}
::weechat::hook_modifier irc_out1_privmsg cmd_emphasys {}

set rebold {(\s)\*(.+)\*(\s)}
set reital {(\s)\/(.+)\/(\s)}

proc cmd_emphasys {data modifier modifier_data irc_msg} {
   set parts [split $irc_msg {:}]
   set input [lindex $parts end]
   regsub -all -- $::rebold $input "\\1\002\\2\002\\3" input
   regsub -all -- $::reital $input "\\1\026\\2\026\\3" input
   return [join [lreplace $parts end end $input] {:}]
   return $::weechat::WEECHAT_RC_OK
}
