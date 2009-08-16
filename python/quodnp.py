#       quodnp.py
#
#       Copyright 2009 Brandon Hartshorn <sharntehnub AT gmail DOT com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import weechat, os, sys, re
from stat import *

SCRIPT_NAME    = "quodnp"
SCRIPT_AUTHOR  = "Sharn"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL2"
SCRIPT_DESC    = "Full control of Quodlibet from Weechat"

SCRIPT_COMMAND = "quodnp"

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command(
        SCRIPT_COMMAND,
        "Control of Quodlibet in Weechat",
        "np | next | prev | play-pause",
        "            np: print song now playing to current buffer\n"
        "next/prev/play: control quodlibet - next song/previous song/play-pause"
        " respectively\n"
        "For np_format configuration, you can use anything avaliable"
        "from \"cat ~/.quodlibet/current\" - just ignore the ~#s\n"
        "and add a \"$\" - for example, to print the artist put $artist, or $album for album.",
        "np|next|prev|play-pause",
        "command_handle", ""
        )

# default options
settings = {
    "autonp"                    : "off",
    "np_format"                 : "np: $artist - $title",
    "debug"                     : "off",
}

for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

def quodlibet_nowplaying(buffer):
    values = {}

    current_file = os.path.expanduser("~/.quodlibet/current")
    if os.path.isfile(current_file):
        open_file = open(current_file, "r")
        for line in open_file:
            key, val = line.lstrip("~#").strip().split("=", 1)
            if key == "bitrate":
                val = val[:3] + "Kbps"
            elif key == "length":
                val = val
            values.update({
            key : val,
            })
        weechat.command(weechat.current_buffer(), (format_output(weechat.config_get_plugin("np_format"), values)))
        open_file.close()
    else:
        weechat.prnt("", "Error opening " + current_file + ". Are you sure Quodlibet is running?")

    ouput = format_output(weechat.config_get_plugin("np_format"), values)

def quodlibet_control(action):
    control_file = os.path.expanduser("~/.quodlibet/control")
    error = "Error opening " + control_file + ". Are you sure Quodlibet is running?"
    try:
        mode = os.stat(control_file)[ST_MODE]
        if S_ISFIFO(mode):
            open_file = open(control_file, "w")
            open_file.write(action)
            open_file.close()
        else:
            weechat.prnt("", error)
    except:
        weechat.prnt("", error)

def format_output(format, values):
  out = ""
  n = 0
  for match in re.finditer(findvar, format):
    if match is None: continue
    else:
      l, r = match.span()
      nam = match.group(1)
      out += format[n:l+1] + values.get(nam, "").strip()
      n = r
  return out + format[n:]

findvar = re.compile(r'[^\\]\$([a-z_]+)(\b|[^a-z_])')

def command_handle(data, buffer, args):
    largs = args.split(" ")
    if len(largs) > 1:
        weechat.prnt("", "This script can only use 1 argument at a time, see /help " + SCRIPT_COMMAND + " if you need help")
    elif largs[0] in ("next", "prev", "play-pause"):
        quodlibet_control(largs[0])
    elif largs[0] == "np":
        quodlibet_nowplaying(buffer)
    else:
        if weechat.config_get_plugin("autonp") == "on":
            quodlibet_nowplaying(buffer)
        else:
            weechat.prnt("", "No action specified, see /help " + SCRIPT_COMMAND + " if you need help")
    return weechat.WEECHAT_RC_OK
