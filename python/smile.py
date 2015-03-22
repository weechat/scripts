# -*- coding: utf-8 -*-
# Copyright (c) 2014 by Vlad Stoica <stoica.vl@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# History
# 02-07-2014 - Vlad Stoica
# Initial script

try:
    import weechat
    import HTMLParser
    import_error = 0
except ImportError:
    import_error = 1

SCRIPT_NAME = "smile"
SCRIPT_AUTHOR = "Vlad Stoica <stoica.vl@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Prints a random ascii smiley."

cmd_hook_process = ""
cmd_buffer       = ""
cmd_stdout       = ""
cmd_stderr       = ""

def smile_cmd(data, buffer, args):
    global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr
    if cmd_hook_process != "":
        weechat.prnt(buffer, "Already trying to grab a smiley.")
        return weechat.WEECHAT_RC_OK
    cmd_buffer = buffer
    cmd_stdout = ""
    cmd_stderr = ""
    cmd_hook_process = weechat.hook_process("url:http://dominick.p.elu.so/fun/kaomoji/get.php", 10000, "smile_cb", "")
    return weechat.WEECHAT_RC_OK

def smile_cb(data, command, rc, stdout, stderr):
    global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr
    cmd_stdout += stdout
    cmd_stderr += stderr
    if int(rc) >= 0:
        if cmd_stderr != "":
            weechat.prnt(cmd_buffer, "%s" % cmd_stderr)
        if cmd_stdout != "":
            h = HTMLParser.HTMLParser()
            sm = h.unescape(cmd_stdout)
            weechat.command(cmd_buffer, sm.encode('utf-8'))
        cmd_hook_process = ""
    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    if import_error:
        weechat.prnt("", "You need to run this script inside weechat.")
    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, "༼つ ◕_◕ ༽つ", "", "", "smile_cmd", "")
