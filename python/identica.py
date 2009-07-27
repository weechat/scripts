# Copyright (c) 2009 by fauno <fauno@kiwwwi.com.ar>
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

# ABOUT
# This plugin gives format to identi.ca's bot messages, converting
# the @sender into the bot's nick and colorizing usernames, groups
# and hashtags.

# It's written for bitlbee.

# HISTORY
# 2009-07-27, fauno:
#		initial release

# PLANNED FEATURES
# 	- colorize sender nickname
# 	- @replies recolection for nick autocompletion

import weechat
import re

SCRIPT_NAME = "identica"
SCRIPT_AUTHOR = "fauno <fauno@kiwwwi.com.ar>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Formats identi.ca's bot messages"

settings = {
		"channel"                 : "localhost.update",
		"re"                      : "^(?P<update>\w+)(?P<separator>\W+?)(?P<username>\w+): (?P<dent>.+)$",

		"nick_color"              : "green",
		"hashtag_color"           : "blue",
		"group_color"             : "red",

		"nick_color_identifier"   : "blue",
		"hashtag_color_identifier": "green",
		"group_color_identifier"  : "green",

		"nick_re"                 : "(@)([a-zA-Z0-9]+)",
		"hashtag_re"              : "(#)([a-zA-Z0-9]+)",
		"group_re"                : "(!)([a-zA-Z0-9]+)"
		}

def colorize (message):
	"""Colorizes replies, hashtags and groups"""

	for identifier in ['nick','hashtag','group']:
		identifier_name = ''.join([identifier, '_re'])
		identifier_color = ''.join([identifier, '_color'])
		identifier_color_identifier = ''.join([identifier, '_color_identifier'])

		identifier_re = re.compile(weechat.config_get_plugin(identifier_name), re.UNICODE)

		replace = r''.join([
			weechat.color(weechat.config_get_plugin(identifier_color_identifier)),
			'\\1',
			weechat.color(weechat.config_get_plugin(identifier_color)),
			'\\2',
			weechat.color('reset')
			])

		message = identifier_re.sub(replace, message)

	return message

def parse (server, modifier, data, the_string):
	"""Parses weechat_print modifier on update@identi.ca pv"""

	plugin, channel, flags = data.split(';')

	if channel == weechat.config_get_plugin('channel'):
		the_string = weechat.string_remove_color(the_string, "")
		matcher = re.compile(weechat.config_get_plugin('re'), re.UNICODE)

		if debug == "true":
			weechat.prnt("", the_string)

		m = matcher.search(the_string)

		if not m: return colorize(the_string)

		dent = colorize(m.group('dent'))

		the_string = ''.join([ m.group('username'), m.group('separator'), dent ])

	return the_string

# init

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, "", ""):

	for option, default_value in settings.iteritems():
		if not weechat.config_is_set_plugin(option):
			weechat.config_set_plugin(option, default_value)

	weechat.hook_modifier('weechat_print', "parse", "")

