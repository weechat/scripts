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

import weechat, urllib2

SCRIPT_NAME    = "whatismyip"
SCRIPT_AUTHOR  = "John Anderson <sontek@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Get your current external ip"

process_output = ""

def whatismyip(data, buffer, args):
    global process_output

    url = 'http://www.whatismyip.com/automation/n09230945.asp'

    process_output = ''
    python2_bin = weechat.info_get("python2_bin", "") or "python"
    url_hook_process = weechat.hook_process(
        python2_bin + " -c \"import urllib2; print urllib2.urlopen('" + url + "').readlines()[0]\"",
        30 * 1000, "process_complete", '')
    return weechat.WEECHAT_RC_OK

def process_complete(data, command, rc, stdout, stderr):
    global process_output
    process_output += stdout.strip()
    if int(rc) >= 0:
        weechat.prnt(weechat.current_buffer(), '[%s]' % process_output)

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command("whatismyip", SCRIPT_DESC, "", "", "", "whatismyip", "")
