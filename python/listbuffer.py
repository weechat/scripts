# -*- coding: utf-8 -*-
#
# ListBuffer, version 0.8.1 for WeeChat version 0.3
# Latest development version: https://github.com/FiXato/listbuffer
#
#   Show /list results in a common buffer and interact with them.
#
#   This script allows you to easily join channels from the /list output.
#   It will open a common buffer for the /list result, through which you
#   browse with your cursor keys, and join with the meta-enter keys.
#   Adjust sorting with meta->, meta-< and meta-/ keybindings.
#
## History:
### 2011-09-08: FiXato:
#
# * version 0.1:  initial release.
#     * added a common buffer for /list results
#     * added highlighting for currently selected line
#     * added /join support via enter key
#     * added scroll_top and scroll_bottom support
#
# * version 0.2:  /list format bugfix
#     * added support for /list results without modes
#     * some servers don't send 321 (/list start). Taken into account.
#
# * version 0.3: Sorting support
#     * Added some basic sorting support. Scroll through sort options
#       with meta-> and meta-< (users, channel, topic, modes)
#
### 2011-09-19: FiXato
#
# * version 0.4:
#     * Case-insensitive buffer lookup fix.
#     * Removed default enter keybind
#
### 2011-12-28: troydm:
#
# * version 0.5: It's an upside-down-world
#     * Added inverted sorting support provided by Dmitry "troydm" Geurkov
#       Use meta-/ to switch between inverted and regular sorting.
#
### 2012-02-10: FiXato:
#
# * version 0.6: Stop shoving that buffer in my face!
#     * The listbuffer should no longer pop up by itself when you load the script.
#       It should only pop up now when you actually do a /list query.
#
# * version 0.7: .. but please pop it up in my current window when I ask for it
#     * Added setting plugins.var.python.listbuffer.autofocus
#       This will autofocus the listbuffer in the current window if another window isn't
#       already showing it, and of course only when the user issues /list
#
### 2012-07-10: FiXato:
#
# * version 0.7.1: Forgetful bugfix
#     * Made sure lb_curline global variable is defined
#
### 2013-03-19: FiXato:
#
# * version 0.8: Sorted out the sorting
#     * Added automatically updating options for sorting:
#       * plugins.var.python.listbuffer.sort_inverted
#       * plugins.var.python.listbuffer.sort_order
# * version 0.8.1: Pad it baby!
#     * Channel modes are equally padded even when there are no channel modes.
#     * Added padding options:
#       * plugins.var.python.listbuffer.modes_min_width
#       * plugins.var.python.listbuffer.channel_min_width
#       * plugins.var.python.listbuffer.users_min_width
#
## Acknowledgements:
# * Dmitry "troydm" Geurkov, for providing the inverse-sorting patch to the project.
# * Sebastien "Flashcode" Helleu, for developing the kick-ass IRC client WeeChat
#    and the iset.pl script which inspired me to this script.
# * Nils "nils_2" Görs, for his contributions to iset.pl which served as
#    example code.
# * David "drubin" Rubin, for his urlgrab.py script, which also served
#    as example code.
# * ArZa, whose listsort.pl script helped me getting started with
#    grabbing the /list results. Parts of his code have been shamelessly
#    copied and ported to Python.
# * Khaled Mardam-Bey, for making me yearn for similar /list support in
#    WeeChat as mIRC already offered. :P
# * mave_, for pointing out that sort orders weren't remembered.
#
## TODO:
#   - Auto-scroll selected line upon window scroll.
#   - Add option to hide already joined channels.
#   - Improve sorting methods
#   - Add auto-join support
#   - Detect if channel is already in auto-join
#   - Allow automatically switching to the listbuffer
#   - Add support for ALIS (/squery alis LIST * -mix 100 (IRCNet)
#   - Make colours configurable
#   - Limit number of channels to parse
#   - Add filter support a la iset
#   - Allow selecting multiple channels
#   - Add optional command redirection.
#
## Copyright (c) 2011,2012,2013 Filip H.F. "FiXato" Slagter,
#   <FiXato [at] Gmail [dot] com>
#   http://profile.fixato.org
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
SCRIPT_NAME    = "listbuffer"
SCRIPT_AUTHOR  = "Filip H.F. 'FiXato' Slagter <fixato [at] gmail [dot] com>"
SCRIPT_VERSION = "0.8.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC    = "A common buffer for /list output."
SCRIPT_COMMAND = "listbuffer"

import_ok = True

try:
  import weechat
except ImportError:
  print "This script must be run under WeeChat."
  import_ok = False

import re

lb_settings = (
  ("autofocus", "on", "Focus the listbuffer in the current window if it isn't already displayed by a window."),
  ("sort_order", "users", "Last used sort order for the channel list."),
  ("sort_inverted", "on", "Invert the sort order for the channel list."),
  ("modes_min_width", "8", "The minimum width used for modes in the channel list. If a channel has less modes than this amount, the column will be padded with spaces."),
  ("channel_min_width", "25", "The minimum width used for the channel name in the channel list. If a channelname is shorter than this amount, the column will be padded with spaces."),
  ("users_min_width", "8", "The minimum width used for the usercount in the channel list. If the usercount has less digits than this amount, the column will be padded with spaces."),
)
lb_buffer = None
lb_curline = 0
lb_channels = []
lb_network = None
lb_list_started = False
lb_current_sort = None
lb_sort_inverted = False
lb_sort_options = (
  'channel',
  'users',
  'modes',
  'topic',
)

#                              server numeric Nick Chan  Users     Modes    Topic
lb_channel_list_expression = '(:\S+) (\d{3}) (\S+) (\S+) (\d+) :(\[(.*?)\] )?(.*)'

# Create listbuffer.
def lb_create_buffer():
  global lb_buffer, lb_curline

  if not lb_buffer:
    lb_buffer = weechat.buffer_new("listbuffer", "lb_input_cb", \
                "", "lb_close_cb", "")
    lb_set_buffer_title()
    # Sets notify to 0 as this buffer does not need to be in hotlist.
    weechat.buffer_set(lb_buffer, "notify", "0")
    weechat.buffer_set(lb_buffer, "nicklist", "0")
    weechat.buffer_set(lb_buffer, "type", "free")
    weechat.buffer_set(lb_buffer, "key_bind_ctrl-L", "/listbuffer **refresh")
    weechat.buffer_set(lb_buffer, "key_bind_meta2-A", "/listbuffer **up")
    weechat.buffer_set(lb_buffer, "key_bind_meta2-B", "/listbuffer **down")
    weechat.buffer_set(lb_buffer, "key_bind_meta2-1~", "/listbuffer **scroll_top")
    weechat.buffer_set(lb_buffer, "key_bind_meta2-4~", "/listbuffer **scroll_bottom")
    weechat.buffer_set(lb_buffer, "key_bind_meta-ctrl-J", "/listbuffer **enter")
    weechat.buffer_set(lb_buffer, "key_bind_meta-ctrl-M", "/listbuffer **enter")
    weechat.buffer_set(lb_buffer, "key_bind_meta->", "/listbuffer **sort_next")
    weechat.buffer_set(lb_buffer, "key_bind_meta-<", "/listbuffer **sort_previous")
    weechat.buffer_set(lb_buffer, "key_bind_meta-/", "/listbuffer **sort_invert")
    lb_curline = 0
  if weechat.config_get_plugin("autofocus") == "on":
    if not weechat.window_search_with_buffer(lb_buffer):
      weechat.command("", "/buffer " + weechat.buffer_get_string(lb_buffer,"name"))

def lb_set_buffer_title():
  global lb_buffer, lb_current_sort
  ascdesc = '(v)' if lb_sort_inverted else '(^)'
  weechat.buffer_set(lb_buffer, "title", lb_line_format({
    'channel': 'Channel name%s' % (ascdesc if lb_current_sort == 'channel' else ''),
    'users': 'Users%s' % (ascdesc if lb_current_sort == 'users' else ''),
    'modes': 'Modes%s' % (ascdesc if lb_current_sort == 'modes' else ''),
    'topic': 'Topic%s' % (ascdesc if lb_current_sort == 'topic' else ''),
    'nomodes': None,
  }))

def lb_list_start(data, signal, message):
  lb_initialise_list

  return weechat.WEECHAT_RC_OK

def lb_initialise_list(signal):
  global lb_channels, lb_network, lb_list_started

  lb_create_buffer()
  lb_channels = []
  lb_network = signal.split(',')[0]
  lb_list_started = True
  return


def lb_list_chan(data, signal, message):
  global lb_channels, lb_buffer, lb_list_started

  # Work-around for IRCds which don't send 321 Numeric (/List start)
  if not lb_list_started:
    lb_initialise_list(signal)

  for chan_data in re.findall(lb_channel_list_expression,message):
    lb_channels.append({
      'server':  chan_data[0][1:-1],
      'numeric': chan_data[1],
      'nick':    chan_data[2],
      'channel': chan_data[3],
      'users':   chan_data[4],
      'nomodes': chan_data[5] == '',
      'modes':   chan_data[6],
      'topic':   weechat.hook_modifier_exec("irc_color_decode", "1", chan_data[7])
    })
  return weechat.WEECHAT_RC_OK

def lb_list_end(data, signal, message):
  global lb_list_started

  # Work-around for IRCds which don't send 321 Numeric (/List start)
  if not lb_list_started:
    lb_initialise_list(signal)

  lb_list_started = False
  if lb_current_sort:
    lb_sort()
  lb_refresh()
  return weechat.WEECHAT_RC_OK

def keyEvent (data, buffer, args):
  global lb_options
  lb_options[args]()

def lb_input_cb(data, buffer, input_data):
  global lb_options, lb_curline
  lb_options[input_data]()
  return weechat.WEECHAT_RC_OK

def lb_refresh():
  global lb_channels, lb_buffer
  weechat.buffer_clear(lb_buffer)

  y = 0
  for list_data in lb_channels:
    lb_refresh_line(y)
    y += 1
  return

def lb_refresh_line(y):
  global lb_buffer, lb_curline, lb_channels
  if y >= 0 and y < len(lb_channels):
    formatted_line = lb_line_format(lb_channels[y], y == lb_curline)
    weechat.prnt_y(lb_buffer, y, formatted_line)

def lb_refresh_curline():
  global lb_curline
  lb_refresh_line(lb_curline-1)
  lb_refresh_line(lb_curline)
  lb_refresh_line(lb_curline+1)
  return

def lb_line_format(list_data,curr=False):
  str = ""
  if (curr):
    str += weechat.color("yellow,red")
  channel_text = list_data['channel'].ljust(int(weechat.config_get_plugin('channel_min_width')))
  users_text = "(%s)" % list_data['users']
  padded_users_text = users_text.rjust(int(weechat.config_get_plugin('users_min_width')) + 2)
  str += "%s%s %s " % (weechat.color("bold"), channel_text, padded_users_text)
  if not list_data['nomodes']:
    modes = "[%s]" % list_data['modes']
  else:
    modes = "[]"
  str += "%s: " % modes.rjust(int(weechat.config_get_plugin('modes_min_width')) + 2)
  str += "%s" % list_data['topic']
  return str

def lb_line_up():
  global lb_curline
  if lb_curline <= 0:
    return
  lb_curline -= 1
  lb_refresh_curline()
  lb_check_outside_window()
  return

def lb_line_down():
  global lb_curline, lb_channels
  if lb_curline+1 >= len(lb_channels):
    return
  lb_curline += 1
  lb_refresh_curline()
  lb_check_outside_window()
  return

def lb_line_run():
  global lb_channels, lb_curline, lb_network
  buff = weechat.info_get("irc_buffer", lb_network)
  channel = lb_channels[lb_curline]['channel']
  command = "/join %s" % channel
  weechat.command(buff, command)
  return

def lb_line_select():
  return

def lb_scroll_top():
  global lb_curline
  old_y = lb_curline
  lb_curline = 0
  lb_refresh_curline()
  lb_refresh_line(old_y)
  weechat.command(lb_buffer, "/window scroll_top")
  return

def lb_scroll_bottom():
  global lb_curline, lb_channels
  old_y = lb_curline
  lb_curline = len(lb_channels)-1
  lb_refresh_curline()
  lb_refresh_line(old_y)
  weechat.command(lb_buffer, "/window scroll_bottom")
  return

def lb_check_outside_window():
  global lb_buffer, lb_curline
  if (lb_buffer):
    infolist = weechat.infolist_get("window", "", "current")
    if (weechat.infolist_next(infolist)):
      start_line_y = weechat.infolist_integer(infolist, "start_line_y")
      chat_height = weechat.infolist_integer(infolist, "chat_height")
      if(start_line_y > lb_curline):
        weechat.command(lb_buffer, "/window scroll -%i" %(start_line_y - lb_curline))
      elif(start_line_y <= lb_curline - chat_height):
        weechat.command(lb_buffer, "/window scroll +%i"%(lb_curline - start_line_y - chat_height + 1))
    weechat.infolist_free(infolist)

def lb_sort_next():
  global lb_current_sort, lb_sort_options
  if lb_current_sort:
    new_index = lb_sort_options.index(lb_current_sort) + 1
  else:
    new_index = 0

  if len(lb_sort_options) <= new_index:
    new_index = 0

  lb_set_current_sort_order(lb_sort_options[new_index])
  lb_sort()

def lb_set_current_sort_order(value):
  global lb_current_sort
  lb_current_sort = value
  weechat.config_set_plugin('sort_order', lb_current_sort)

def lb_set_invert_sort_order(value):
  global lb_sort_inverted
  lb_sort_inverted = value
  weechat.config_set_plugin('sort_inverted', ('on' if lb_sort_inverted else 'off'))

def lb_sort_previous():
  global lb_current_sort, lb_sort_options
  if lb_current_sort:
    new_index = lb_sort_options.index(lb_current_sort) - 1
  else:
    new_index = 0

  if new_index < 0:
    new_index = len(lb_sort_options) - 1

  lb_set_current_sort_order(lb_sort_options[new_index])
  lb_sort()

def lb_sort(sort_key=None):
  global lb_channels, lb_current_sort, lb_sort_inverted
  if sort_key:
    lb_set_current_sort_order(sort_key)
  if lb_current_sort == 'users':
    lb_channels = sorted(lb_channels, key=lambda chan_data: int(chan_data[lb_current_sort]))
  else:
    lb_channels = sorted(lb_channels, key=lambda chan_data: chan_data[lb_current_sort])
  if lb_sort_inverted:
    lb_channels.reverse()
  lb_set_buffer_title()
  lb_refresh()

def lb_sort_invert():
  global lb_current_sort, lb_sort_inverted
  if lb_current_sort:
    lb_set_invert_sort_order(not lb_sort_inverted)
    lb_sort()

def lb_close_cb(*kwargs):
  """ A callback for buffer closing. """
  global lb_buffer

  lb_buffer = None
  return weechat.WEECHAT_RC_OK

lb_options = {
  'refresh'     : lb_refresh,
  'up'          : lb_line_up,
  'down'        : lb_line_down,
  'enter'       : lb_line_run,
  'space'       : lb_line_select,
  'scroll_top'  : lb_scroll_top,
  'scroll_bottom': lb_scroll_bottom,
  'sort_next'   : lb_sort_next,
  'sort_previous': lb_sort_previous,
  'sort_invert': lb_sort_invert
}

def lb_command_main(data, buffer, args):
  if args[0:2] == "**":
    keyEvent(data, buffer, args[2:])
  return weechat.WEECHAT_RC_OK

def lb_set_default_settings():
  global lb_settings
  # Set default settings
  for option, default_value, description in lb_settings:
     if not weechat.config_is_set_plugin(option):
         weechat.config_set_plugin(option, default_value)
         version = weechat.info_get("version_number", "") or 0
         if int(version) >= 0x00030500:
             weechat.config_set_desc_plugin(option, description)

def lb_reset_stored_sort_order():
  global lb_current_sort, lb_sort_inverted
  lb_current_sort = weechat.config_get_plugin('sort_order')
  lb_sort_inverted = (True if weechat.config_get_plugin('sort_inverted') == 'on' else False)

if __name__ == "__main__" and import_ok:
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                      SCRIPT_LICENSE, SCRIPT_DESC, "lb_close_cb", ""):
    lb_set_default_settings()
    lb_reset_stored_sort_order()
    lb_buffer = weechat.buffer_search("python", "listbuffer")

    weechat.hook_signal("*,irc_in_321", "lb_list_start", "")
    weechat.hook_signal("*,irc_in_322", "lb_list_chan", "")
    weechat.hook_signal("*,irc_in_323", "lb_list_end", "")
    weechat.hook_command(SCRIPT_COMMAND,
                          "List Buffer",
                          "", "", "",
                          "lb_command_main", "")
