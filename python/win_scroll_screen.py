#
# Copyright (C) 2015 Paul L <paulguy119@gmail.com>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# To get irssi style window scrolling, make sure the script is loaded and issue
# these commands:
#
# /key unbind meta2-6~
# /key unbind meta2-5~
# /key bind meta2-6~ /win_scroll_screen 0.5
# /key bind meta2-5~ /win_scroll_screen -0.5

import weechat as w

SCRIPT_NAME = "win_scroll_screen"
SCRIPT_AUTHOR = "paulguy"
SCRIPT_VERSION = "1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESCRIPTION = "Allows for scrolling by fractional screens."

def win_scroll_screen(data, buffer, args):
  screens = float(args)

  win = w.current_window()

  chat_height = w.window_get_integer(win, 'win_chat_height')
  if screens < 0:
    scrolling = w.window_get_integer(win, 'scrolling')
    if scrolling == 0: # no idea why but this is needed
      scroll = int(chat_height * screens) - (chat_height - 3)
    else:
      scroll = int(chat_height * screens)
  else:
    scroll = int(chat_height * screens)

    lines_after = w.window_get_integer(win, 'lines_after')
    if scroll >= lines_after:
      return w.command(buffer, "/window scroll_bottom")

  return w.command(buffer, "/window scroll {:+d}".format(scroll))


w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
           SCRIPT_DESCRIPTION, "", "")
hook = w.hook_command(SCRIPT_NAME,
                      SCRIPT_DESCRIPTION,
                      "<screens>",
                      "<screens> - screens to scroll, can be fractional",
                      "",
                      'win_scroll_screen',
                      '')
