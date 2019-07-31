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
#    v 0.3 - add option to change service from which the IP is gathered
#          - better recognition of ipv4 addresses and support of ipv6
#          - add mute option
#    v 0.4 - check if xfer plugin is loaded.
#    v 0.5 - make script python3 compatible.

from __future__ import print_function

SCR_NAME    = "xfer_setip"
SCR_AUTHOR  = "Stephan Huebner <shuebnerfun01@gmx.org>"
SCR_VERSION = "0.5"
SCR_LICENSE = "GPL3"
SCR_DESC    = "Set apropriate xfer-option for external ip"
SCR_COMMAND = "xfer_setip"

import_ok = True
ip_from_option = 0

OPTIONS         = { 'mute'      : ('off','hide output'),
                    'url'       : ('http://checkip.dyndns.org/','url to fetch'),
                  }

import re

try:
    from html.parser import HTMLParser  # Python 3
except ImportError:
    from HTMLParser import HTMLParser  # Python 2

try:
    import weechat as w
except ImportError:
    print("Script must be run under weechat. http://www.weechat.org")
    import_ok = False

def alert(myString):
    w.prnt("", myString)
    return

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    def handle_data(self, data):
        global OPTIONS, ip_from_option

        data=data.strip()

        ipv6 = re.compile(r"""
        \s*                         # Leading whitespace
        (?!.*::.*::)                # Only a single whildcard allowed
        (?:(?!:)|:(?=:))            # Colon iff it would be part of a wildcard
        (?:                         # Repeat 6 times:
            [0-9a-f]{0,4}           #   A group of at most four hexadecimal digits
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
        ){6}                        #
        (?:                         # Either
            [0-9a-f]{0,4}           #   Another group
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
            [0-9a-f]{0,4}           #   Last group
            (?: (?<=::)             #   Colon iff preceeded by exacly one colon
             |  (?<!:)              #
             |  (?<=:) (?<!::) :    #
             )                      # OR
         |                          #   A v4 address with NO leading zeros
            (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            (?: \.
                (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            ){3}
        )
        \s*                         # Trailing whitespace
        $
    """, re.VERBOSE | re.IGNORECASE | re.DOTALL)

        ipv4 = re.compile('(([2][5][0-5]\.)|([2][0-4][0-9]\.)|([0-1]?[0-9]?[0-9]\.)){3}'
                +'(([2][5][0-5])|([2][0-4][0-9])|([0-1]?[0-9]?[0-9]))')

        matchipv4 = ipv4.search(data)
        matchipv6 = ipv6.search(data)
        set_ip = ""
        current_ip = ""

        if matchipv4:
            current_ip = matchipv4.group()
            set_ip = "/set xfer.network.own_ip %s" % matchipv4.group()
        if matchipv6:
            current_ip = matchipv6.group()
            set_ip = "/set xfer.network.own_ip %s" % matchipv6.group()
        if OPTIONS['mute'].lower() == "on":
            set_ip = "/mute %s" % set_ip

        if set_ip != "" and current_ip != ip_from_option:
            w.command("", set_ip)

def fn_setip(data, command, return_code, out, err):
    if return_code != w.WEECHAT_HOOK_PROCESS_ERROR:
        parser.feed(out)
    return w.WEECHAT_RC_OK

def fn_connected(data, signal, signal_data):
    global ip_from_option
    # check if xfer option exists
    own_ip_option = w.config_get("xfer.network.own_ip")
    if not own_ip_option:
        return w.WEECHAT_RC_OK
    ip_from_option = w.config_string(own_ip_option)
    w.hook_process('url:%s' % OPTIONS['url'], 60000, "fn_setip", "")
    return w.WEECHAT_RC_OK

def fn_command(data, buffer, args):
    fn_connected("", "", "")
    return w.WEECHAT_RC_OK

# ================================[ weechat options & description ]===============================
def init_options():
    for option,value in OPTIONS.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = w.config_get_plugin(option)
        w.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCR_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    return w.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if w.register(SCR_NAME, SCR_AUTHOR, SCR_VERSION, SCR_LICENSE,
                  SCR_DESC, "", ""):
        init_options()
        w.hook_config('plugins.var.python.' + SCR_NAME + '.*', 'toggle_refresh', '')
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
