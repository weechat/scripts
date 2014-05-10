# -*- coding: utf-8 -*-
#
# irssi_awaylog.py: emulates irssi awaylog (replay of hilights and privmsg)
# - 2013, henrik <henrik at affekt dot org>
#
# TODO: store awaylog in a file instead of memory
#
###########################################################################
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
###########################################################################

import_ok = True
try:
	import weechat as wc
except Exception:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://www.weechat.org/"
	import_ok = False

import time

SCRIPT_NAME     = "irssi_awaylog"
SCRIPT_AUTHOR   = "henrik"
SCRIPT_VERSION  = "0.3"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Emulates irssis awaylog behaviour"

awaylog = []

def replaylog():
	global awaylog

	if awaylog:
		wc.prnt("", "-->\t")
		for a in awaylog:
			wc.prnt_date_tags("", a[0], "", a[1])
		wc.prnt("", "<--\t")

		awaylog = []


def away_cb(data, bufferp, command):
	isaway = wc.buffer_get_string(bufferp, "localvar_away") != ""

	if not isaway:
		replaylog()
	return wc.WEECHAT_RC_OK

def msg_cb(data, bufferp, date, tagsn, isdisplayed, ishilight, prefix, message):
	global awaylog

	isaway = wc.buffer_get_string(bufferp, "localvar_away") != ""
	isprivate = wc.buffer_get_string(bufferp, "localvar_type") == "private"

	# catch private messages or highlights when away
	if isaway and (isprivate or int(ishilight)):
		logentry = "awaylog\t"

		if int(ishilight) and not isprivate:
			buffer = (wc.buffer_get_string(bufferp, "short_name") or
					wc.buffer_get_string(bufferp, "name"))
		else:
			buffer = "priv"

		buffer = wc.color("green") + buffer + wc.color("reset")

		logentry += "[" + buffer + "]"
		logentry += wc.color("default") + " <" + wc.color("blue") + prefix + wc.color("default") + "> " + wc.color("reset") + message

		awaylog.append((int(time.time()), logentry))
	return wc.WEECHAT_RC_OK

if __name__ == "__main__":
	if import_ok and wc.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
		wc.hook_print("", "notify_message", "", 1, "msg_cb", "")
		wc.hook_print("", "notify_private", "", 1, "msg_cb", "")
		wc.hook_command_run("/away", "away_cb", "")
