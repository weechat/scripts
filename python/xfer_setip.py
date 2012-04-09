# Copyright (c) 2010-2012 by Stephan Huebner <s.huebner@gmx.org>
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
#    v 0.2 - changed server from which the IP is gathered
#          - switched from Pythons' urlopen to weechats' url transfer
#            (therefore 0.3.7 is required)
#          - some small tweaks in description and (hopefully) and
#            IP-checking, to make sure that I really got a correct one.
#          - changed contact Email to one that actually exists :)

SCR_NAME    = "xfer_setip"
SCR_AUTHOR  = "Stephan Huebner <shuebnerfun01@gmx.org>"
SCR_VERSION = "0.2"
SCR_LICENSE = "GPL3"
SCR_DESC    = "Set apropriate xfer-option for external ip"
SCR_COMMAND = "xfer_setip"

import_ok = True

try:
    import weechat as w
    from HTMLParser import HTMLParser
    import re

except:
    print "Script must be run under weechat. http://www.weechat.org"
    import_ok = False

def alert(myString):
    w.prnt("", myString)
    return

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    def handle_data(self, data):
        data=data.strip()
        if re.match('([\d]{1,3}\.){3}[\d]{1,3}', data) is not None:
            w.command("", "/set xfer.network.own_ip %s" %data)

def fn_setip(data, command, return_code, out, err):
    if return_code != w.WEECHAT_HOOK_PROCESS_ERROR:
        parser.feed(out)
    return w.WEECHAT_RC_OK

def fn_connected(data, signal, signal_data):
    w.hook_process('url:http://ip.auk.ca/', 60000, "fn_setip", "")
    return w.WEECHAT_RC_OK

def fn_command(data, buffer, args):
    fn_connected("", "", "")
    return w.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if w.register(SCR_NAME, SCR_AUTHOR, SCR_VERSION, SCR_LICENSE,
                  SCR_DESC, "", ""):
        parser = MyHTMLParser()
        fn_connected("", "", "")
        # hook to "connected to a server"-signal
        w.hook_signal("irc_server_connected", "fn_connected", "")
        w.hook_command( # help-text
           SCR_COMMAND, "",
"""

The script tries to retrieve your external IP, in three cases:
  1) When it is loaded
  2) whenever you have succesfully connected to a server
  3) when the script is called as a command ("/xfer_setip").

""",
           "",
           "", "fn_command", ""
           )
