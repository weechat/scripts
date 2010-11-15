# Copyright (c) 2010 by Stephan Huebner <s.huebnerfun01@gmx.org>
#
# Intended use:
#
# Set ip-setting to the correct external IP whenever one connects to a server
# (so that dcc-sending works)
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
# History:
#    v 0.1 - first public release

SCR_NAME    = "xfer_setip"
SCR_AUTHOR  = "Stephan Huebner <shuebnerfun01@gmx.org>"
SCR_VERSION = "0.1"
SCR_LICENSE = "GPL3"
SCR_DESC    = "Set apropriate xfer-option for external ip"
SCR_COMMAND = "xfer_setip"

import_ok = True

process_output = ""

try:
	import weechat as w
except:
	print "Script must be run under weechat. http://www.weechat.org"
	import_ok = False

def alert(myString):
	w.prnt("", myString)
	return

def fn_setip(data, command, return_code, out, err):
	global process_output
	process_output += out.strip()
	if int(return_code) >= 0:
		alert("Trying to set ip: '" + process_output + "'")
		w.command("", "/set xfer.network.own_ip %s" %process_output)
	return w.WEECHAT_RC_OK

def fn_connected(data, signal, signal_data):
	global process_output
	process_output = ""
	python2_bin = w.info_get("python2_bin", "") or "python"
	myProcesss = w.hook_process(python2_bin + " -c \"from urllib2 import urlopen\n" +
										 "try:\n\t" +
										 "print urlopen('http://whatismyip.org').read()" +
										 "\nexcept:\n" +
										 "\tprint ''\"",
										 60000, "fn_setip", "")
	return w.WEECHAT_RC_OK

def fn_command(data, buffer, args):
	fn_connected(data, buffer, args)
	return w.WEECHAT_RC_OK
	
if __name__ == "__main__" and import_ok:
	if w.register(SCR_NAME, SCR_AUTHOR, SCR_VERSION, SCR_LICENSE,
						SCR_DESC, "", ""):
		# hook to "connected to (any) server"-signal
		w.hook_signal("irc_server_connected", "fn_connected", "")
		w.hook_command( # help-text
			SCR_COMMAND, "",
"""

The script tries to retrieve your external IP from "whatismyip.org". Once
started, it will do so on two occasions:
  1) whenever you have succesfully connected to *any* server (imho, the easiest
     way to make sure that your IP is set correctly after a (possible)
     disconnection from the internet).
  2) when the script is called itself as a command "/setip".
  
Attention: You should check weechats' core-buffer to make sure that the IP
was actually set (it seems that "whatismyip.org" doesn't deliver an IP if it
is called a few times within a short time-amount (which shouldn't be a problem
in "regular" use of the script.
""",
			"",
			"", "fn_command", ""
			)
