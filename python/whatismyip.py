# Copyright (c) 2010 by John Anderson <sontek@gmail.com>
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

# 2012-11-17, v0.2 (nils_2@freenode.#weechat)
#     use URL transfer in API (for WeeChat >= 0.3.7), update service URL

import weechat

SCRIPT_NAME    = "whatismyip"
SCRIPT_AUTHOR  = "John Anderson <sontek@gmail.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Get your current external ip, using whatismyip.com"

process_output = ""

def whatismyip(data, buffer, args):
    global process_output

    url = 'http://automation.whatismyip.com/n09230945.asp'

    process_output = ''
    url_hook_process = weechat.hook_process("url:%s" % url, 30 * 1000, "process_complete", "")
    return weechat.WEECHAT_RC_OK

def process_complete(data, command, rc, stdout, stderr):
    global process_output
    process_output += stdout.strip()

    if len(process_output) > 40:
        weechat.prnt(weechat.current_buffer(), weechat.prefix("error") + 'whatismyip: [%s]' % "Service Unavailable")
        return weechat.WEECHAT_RC_OK
    if int(rc) == 0:
        weechat.prnt(weechat.current_buffer(), '[%s]' % process_output)

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command("whatismyip", SCRIPT_DESC, "", "", "", "whatismyip", "")
