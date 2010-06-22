"""
  Author:
    Pablo Escobar <pablo__escobar AT tlen DOT pl>

  Adapted for Weechat 0.3.0 by:
    Apprentice <apprent1ce AT livejournal DOT com>

  What it does:
    This script shows the currently played song in mpd 

  Usage:
    /weempd - Displays the songname 

  Released under GNU GPL v3 or newer
"""

import weechat as wc
import re
from os.path import basename, splitext
from os import popen

wc.register("weempd", "Apprentice", "0.1.1", "GPL3", "np for mpd", "", "")

def subst(text, values):
  out = ""
  n = 0
  for match in re.finditer(findvar, text):
    if match is None:
      continue 
    else:
      l, r = match.span()
      nam = match.group(1)
      out += text[n:l+1] + values.get(nam, "") #"$" + nam)
      n = r
  return out + text[n:]


def np(data, buffer, args):
  """
   Send information about the currently
   played song to the channel.
  """
  spacer = wc.config_get_plugin("spacer")
  msg_head = wc.config_get_plugin("msg_head")
  tempinfo = popen('mpc').readline().rstrip()
  if tempinfo.find("volume:") == -1:
    all = '/me ' + msg_head + spacer + tempinfo 
    wc.command(wc.current_buffer(), all)
  return 0
  
wc.hook_command("weempd", "now playing", "", np.__doc__, "", "np", "")

default = {
  "msg_head": "np:",
  "spacer": " " ,
}

for k, v in default.items():
  if not wc.config_is_set_plugin(k):
    wc.config_set_plugin(k, v)
