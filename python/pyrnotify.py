# -*- coding: utf-8 -*-
# ex:sw=4 ts=4:ai:
#
# Copyright (c) 2012 by Krister Svanlund <krister.svanlund@gmail.com>
#   based on tcl version:
#    Remote Notification Script v1.1
#    by Gotisch <gotisch@gmail.com>
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

# Example usage when Weechat is running on a remote PC and you want
# want to use port 4321 for the connection.
#
#     On the "client" (where the notifications will end up), host is
#     the remote host where weechat is running:
#		python2 location/of/pyrnotify.py 4321 & ssh -R 4321:localhost:4321 username@host
#     You can have a second argument to specified the time to display the notification
#       python2 location/of/pyrnotify.py 4321 2000 & ssh -R 4321:localhost:4321 username@host
#     Important to remember is that you should probably setup the
#     connection with public key encryption and use something like
#     autossh to do this in the background.
#
#     In weechat:
#		/python load pyrnotify.py
#		and set the port
#		/set plugins.var.python.pyrnotify.port 4321
#
# It is also possible to set which host pyrnotify shall connect to,
# this is not recommended. Using a ssh port-forward is much safer
# and doesn't require any ports but ssh to be open.

# ChangeLog:
#
# 2018-08-20: Make it work with python3
#              use of sendall instead of send
# 2014-05-10: Change hook_print callback argument type of displayed/highlight
#             (WeeChat >= 1.0)
# 2012-06-19: Added simple escaping to the title and body strings for
#             the script to handle trailing backslashes.

from __future__ import print_function

try:
    import weechat as w
    in_weechat = True
except ImportError as e:
    in_weechat = False

import os, sys, re
import socket
import subprocess
import shlex

SCRIPT_NAME    = "pyrnotify"
SCRIPT_AUTHOR  = "Krister Svanlund <krister.svanlund@gmail.com>"
SCRIPT_VERSION = "1.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Send remote notifications over SSH"

def escape(s):
    return re.sub(r'([\\"\'])', r'\\\1', s)

def run_notify(icon, nick, chan, message):
    host = w.config_get_plugin('host')
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(w.config_get_plugin('port'))))
        msg = "normal {0} \"{1} to {2}\" \"{3}\"".format(icon, nick, escape(chan), escape(message))
        s.sendall(msg.encode('utf-8'))
        s.close()
    except Exception as e:
        w.prnt("", "Could not send notification: {0}".format(e))

def on_msg(*a):
    if len(a) == 8:
        data, buffer, timestamp, tags, displayed, highlight, sender, message = a
        if data == "private" or int(highlight):
            if data == "private" and w.config_get_plugin('pm-icon'):
                icon = w.config_get_plugin('pm-icon')
            else:
                icon = w.config_get_plugin('icon')
            buffer = "me" if data == "private" else w.buffer_get_string(buffer, "short_name")
            run_notify(icon, sender, buffer, message)
            #w.prnt("", str(a))
    return w.WEECHAT_RC_OK

def weechat_script():
    settings = {'host' : "localhost",
                'port' : "4321",
                'icon' : "utilities-terminal",
                'pm-icon' : "emblem-favorite"}
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        for (kw, v) in settings.items():
            if not w.config_get_plugin(kw):
                w.config_set_plugin(kw, v)
        w.hook_print("", "notify_message", "", 1, "on_msg", "")
        w.hook_print("", "notify_private", "", 1, "on_msg", "private")
        w.hook_print("", "notify_highlight", "", 1, "on_msg", "") # Not sure if this is needed


######################################
## This is where the client starts, except for the global if-check nothing below this line is
## supposed to be executed in weechat, instead it runs when the script is executed from
## commandline.

def accept_connections(s, timeout=None):
    conn, addr = s.accept()
    try:
        data = ""
        d = conn.recv(1024)
        while d:
            data += d.decode('utf-8')
            d = conn.recv(1024)
    finally:
        conn.close()
    if data:
        try:
            urgency, icon, title, body = shlex.split(data)
            if timeout:
                subprocess.call(["notify-send", "-t", timeout, "-u", urgency, "-c", "IRC", "-i", icon, escape(title), escape(body)])
            else:
                subprocess.call(["notify-send", "-u", urgency, "-c", "IRC", "-i", icon, escape(title), escape(body)])

        except ValueError as e:
            print(e)
        except OSError as e:
            print(e)
    accept_connections(s, timeout)

def weechat_client(argv):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("localhost", int(argv[1] if len(sys.argv) > 1 else 4321)))
    s.listen(5)
    try:
        accept_connections(s, argv[2] if len(sys.argv) > 2 else None)
    except KeyboardInterrupt as e:
        print("Keyboard interrupt")
        print(e)
    finally:
        s.close()

if __name__ == '__main__':
    if in_weechat:
        weechat_script()
    else:
        weechat_client(sys.argv)
