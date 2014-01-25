# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2013 Maarten de Vries <maarten@de-vri.es>
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

SCRIPT_NAME     = "autosort_buffers"
SCRIPT_AUTHOR   = "Maarten de Vries <maarten@de-vri.es>"
SCRIPT_VERSION  = "1.0"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Automatically keeps buffers grouped by server and sorted by name."


class Buffer:
	''' Represents a buffer in Weechat. '''

	def __init__(self, name):
		''' Construct a buffer from a buffer name. '''
		self.full_name = name
		buffer_info = name.split('.', 1)
		self.server, self.name = buffer_info if len(buffer_info) == 2 else (None, name)

	@property
	def is_server_buffer(self):
		''' True if the buffer is a server buffer. '''
		return self.server == 'server'

	def __str__(self):
		''' Get a string representation of the buffer. '''
		return self.full_name


class Server:
	''' Represents a server/network in Weechat. '''

	def __init__(self, server_buffer = None, buffers = None):
		''' Construct a server from a server buffer and a buffer list. '''
		self.server_buffer = server_buffer
		self.buffers = buffers or []

	@property
	def name(self):
		''' Name of the server. '''
		return self.server_buffer.name

	def __str__(self):
		''' Get a string representation of the server. '''
		return '{}[{}]'.format(self.server_buffer.full_name, ','.join(map(str, self.buffers)))


def get_buffers():
	''' Get a list of all the buffers in weechat. '''
	buffers = []

	buffer_list = weechat.infolist_get("buffer", "", "")

	while weechat.infolist_next(buffer_list):
		buffers.append(Buffer(weechat.infolist_string(buffer_list, "name")))

	weechat.infolist_free(buffer_list)
	return buffers


def sort_key(thing):
	''' Get the name of a thing. '''
	return thing.name.lower()


def sort_buffers(buffers):
	'''
	Sort a buffer list by name, grouped by server.
	Buffers without a server are sorted after the rest.
	'''

	servers = {b.name: Server(b) for b in buffers if b.is_server_buffer}
	misc    = []

	# Add non-server buffers to their server or the misc list if they have no server.
	for buf in buffers:
		if not buf.is_server_buffer:
			(servers[buf.server].buffers if buf.server else misc).append(buf)

	# Add it all together in the right order.
	result = []
	for server in sorted(servers.values(), key = sort_key):
		result.append(server.server_buffer)
		result.extend(sorted(server.buffers, key = sort_key))
	result.extend(sorted(misc, key = sort_key))

	return result


def apply_buffer_order(buffers):
	''' Sort the buffers in weechat according to the order in the input list.  '''
	i = 1
	for buf in buffers:
		weechat.command('', '/buffer swap {} {}'.format(buf.full_name, i))
		i += 1



def on_buffers_changed(*args, **kwargs):
	''' Callback called whenever the buffer list changes. '''
	apply_buffer_order(sort_buffers(get_buffers()))
	return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
	weechat.hook_signal("buffer_opened", "on_buffers_changed", "")
	weechat.hook_signal("buffer_merged", "on_buffers_changed", "")
	weechat.hook_signal("buffer_unmerged", "on_buffers_changed", "")
	weechat.hook_signal("buffer_renamed", "on_buffers_changed", "")
	on_buffers_changed()
