# Copyright (c) 2010 by fauno <fauno@kiwwwi.com.ar>
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

import weechat

## TODO:
# - buffer whitelist/blacklist
# - max chars per buffer (ie, bar item will turn red when count > 140 for identica buffer)

SCRIPT_NAME    = "typing_counter"
SCRIPT_AUTHOR  = "fauno <fauno@kiwwwi.com.ar>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item showing typing count. Add 'tc' to a bar."

tc_input_text = ''

def tc_count_chars (string):
	'''Returns string length as string'''
	return str(len(string.decode('utf-8')))

def tc_bar_item_update (data, modifier, modifier_data, string):
	'''Updates bar item'''
	global tc_input_text

	tc_input_text = tc_count_chars(string)

	weechat.bar_item_update('tc')

	return string

def tc_bar_item (data, item, window):
	'''Item constructor'''
	global tc_input_text

	return tc_input_text

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "", ""):

		weechat.bar_item_new('tc', 'tc_bar_item', '')
		weechat.hook_modifier('input_text_content', 'tc_bar_item_update', '')
