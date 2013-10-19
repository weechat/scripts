# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2013 KokaKiwi <kokakiwi@kokakiwi.net>
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

import weechat

SCRIPT_NAME     = "sort_servers"
SCRIPT_AUTHOR   = "KokaKiwi <kokakiwi@kokakiwi.net>"
SCRIPT_VERSION  = "0.1"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Sort buffers by servers and alphabetically"

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    weechat.hook_command("sort_servers",
        SCRIPT_DESC,
        "", "", "",
        "sort_servers_cmd",
        ""
    )

def debug(data = ""):
    data = str(data)
    weechat.prnt("", "[sort_servers] %s" % (data))

def command(cmd):
    weechat.command("", cmd)

class SortServers_Buffer:
    def __init__(self, num, server, name):
        self.number = num
        self.server = server
        self.name = name

    @property
    def is_server(self):
        return self.server == 'server'

    @property
    def full_name(self):
        return '%s.%s' % (self.server, self.name)

    @staticmethod
    def sort_key(key):
        return key.name[1:].lower()

    def __str__(self):
        return '%d. %s.%s' % (self.number, self.server, self.name)

    def __repr__(self):
        return str(self)

class SortServers_Server:
    def __init__(self, buf, buffers):
        self.buffer = buf
        self.buffers = buffers

    def sort(self):
        self.buffers = sorted(self.buffers, key = SortServers_Buffer.sort_key)

    @staticmethod
    def sort_key(key):
        return key.buffer.name.lower()

    def __str__(self):
        return '%s(%s)' % (str(self.buffer), ', '.join(map(str, self.buffers)))

    def __repr__(self):
        return str(self)

class SortServersPlugin:
    def get_buffers(self):
        buffers = []

        buffer_pnt = weechat.infolist_get("buffer", "", "")

        while weechat.infolist_next(buffer_pnt):
            buffer_plugin_name = weechat.infolist_string(buffer_pnt, "plugin_name")
            buffer_name = weechat.infolist_string(buffer_pnt, "name")
            buffer_number = weechat.infolist_integer(buffer_pnt, "number")

            buffer_number = int(buffer_number)

            if buffer_plugin_name == 'irc':
                (server, name) = tuple(buffer_name.split('.', 1))

                buf = SortServers_Buffer(buffer_number, server, name)
                buffers.append(buf)

        weechat.infolist_free(buffer_pnt)

        return buffers

    def sort(self):
        buffers = self.get_buffers()

        servers = dict()
        for b in buffers:
            if b.is_server:
                servers[b.name] = SortServers_Server(b, [])
        for b in buffers:
            if not b.is_server:
                server = servers[b.server]
                server.buffers.append(b)

        servers = sorted(servers.values(), key = SortServers_Server.sort_key)
        for server in servers:
            server.sort()

        def move_buffer(src, dst):
            command('/buffer swap %s %s' % (src, dst))

        i = 1
        for server in servers:
            move_buffer(server.buffer.full_name, i)
            i += 1

            for buf in server.buffers:
                move_buffer(buf.full_name, i)
                i += 1

def sort_servers_cmd(data, buf, args):
    ''' Command /sort_servers '''
    current_buffer_name = weechat.buffer_get_string(buf,"name")

    plugin = SortServersPlugin()
    plugin.sort()

    command('/buffer %s' % (current_buffer_name))
    return weechat.WEECHAT_RC_OK
