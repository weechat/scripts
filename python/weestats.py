# -*- coding: utf-8 -*-
#
# weestats.py, version 0.2 for WeeChat version 0.3
# Latest development version: https://github.com/FiXato/weechat_scripts
#
# Inserts some statistics into your input field about the buffers/windows
#  you have open.
# Example: 151 buffers (46 merged): 135 channels, 9 servers, 3 queries,
#  1 script, 1 python, 1 perl, 1 core; 3 windows
#
## History:
#
### 2012-03-29: FiXato:
# * version 0.1: initial release.
#     * Display a count of all the different buffers you have open.
#     * Display a count of all the open windows.
# * version 0.2: Getting the splits.
#     * Displays the how many vertical and horizontal windows.
#       (not quite sure if my approximation is correct though..)
#     * Fixed possible memleak (forgot to free an infolist)
### 2015-05-02: arza:
# * version 0.3:
#     * handle non-#-channels
#     * numerical sort for buffer info
#     * moved window split info to option -split
#     * simplified the output
#
## Acknowledgements:
# * Sebastien "Flashcode" Helleu, for developing the kick-ass chat/IRC
#    client WeeChat
#
## TODO:
#   - Add more statistics, such as:
#     - average and total history lines.
#     - average and total topic/title lengths
#     - how many are displayed in a window
#
## Copyright (c) 2012 Filip H.F. "FiXato" Slagter,
#   <FiXato+WeeChat [at] Gmail [dot] com>
#   https://google.com/profiles/FiXato
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
SCRIPT_NAME     = "weestats"
SCRIPT_AUTHOR   = "Filip H.F. 'FiXato' Slagter <fixato [at] gmail [dot] com>"
SCRIPT_VERSION  = "0.3"
SCRIPT_LICENSE  = "MIT"
SCRIPT_DESC     = "Useless statistics about your open buffers and windows"
SCRIPT_COMMAND  = "weestats"
SCRIPT_CLOSE_CB = "close_cb"

import_ok = True

try:
  import weechat as w
except ImportError:
  print "This script must be run under WeeChat."
  import_ok = False

def close_cb(*kwargs):
  return w.WEECHAT_RC_OK

def command_main(data, buffer, args):
  infolist = w.infolist_get("buffer", "", "")
  buffer_groups = {}
  results = []
  buffer_count = 0
  merge_count = 0
  numbers = set()
  while w.infolist_next(infolist):
    bplugin = w.infolist_string(infolist, "plugin_name")
    bname = w.infolist_string(infolist, "name")
    bpointer = w.infolist_pointer(infolist, "pointer")
    bnumber = w.infolist_integer(infolist, "number")
    btype = w.buffer_get_string(bpointer, 'localvar_type')
    if not bnumber in numbers:
      numbers.add(bnumber)
    else:
      merge_count += 1

    if btype == 'server':
      bdesc = 'servers'
    elif btype == 'channel':
      bdesc = 'channels'
    elif btype == 'private':
      bdesc = 'queries'
    else:
      bdesc = bplugin

    buffer_groups.setdefault(bdesc,[]).append({'name': bname, 'pointer': bpointer})

  w.infolist_free(infolist)

  infolist = w.infolist_get("window", "", "")
  windows_v = set()
  windows_h = set()
  windows = set()
  while w.infolist_next(infolist):
    window = w.infolist_pointer(infolist, "pointer")
    window_w = w.infolist_integer(infolist, "width_pct")
    window_h = w.infolist_integer(infolist, "height_pct")
    windows.add(window)
    if window_h == 100 and window_w != 100:
      windows_v.add(window)
    elif window_w == 100 and window_h != 100:
      windows_h.add(window)
    #else: #both 100%, thus no splits
  w.infolist_free(infolist)

  window_count = len(windows)

  for desc, buffers in buffer_groups.iteritems():
    buffer_count += len(buffers)
    results.append('%i %s' % (len(buffers), desc))

  buffer_stats = ', '.join(sorted(results, key = lambda item: (int(item.partition(' ')[0]) if item[0].isdigit() else float('inf'), item),reverse=True)) # descending numerical sort of strings
  stats_string = '%i buffers (%i merged): %s; %i windows' % (buffer_count, merge_count, buffer_stats, window_count)
  if '-split' in args:
    stats_string += ": %i vertically / %i horizontally split" % (len(windows_v), len(windows_h))
  w.command("", "/input insert %s" % stats_string)
  return w.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
  if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                      SCRIPT_LICENSE, SCRIPT_DESC, SCRIPT_CLOSE_CB, ""):

    w.hook_command(SCRIPT_COMMAND,
                          SCRIPT_DESC,
                          "-split",
                          "Inserts useless statistics about your open buffers and windows into your input line.\n"
                          "-split: Include information about window splits.",
                          "-split",
                          "command_main", "")
