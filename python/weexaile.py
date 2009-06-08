# Authors: Pablo Escobar <pablo__escobar AT tlen DOT pl>
#          Vitaly Dolgov <ferhiord AT gmail DOT com>
# What it does: this script shows the currently played song in exaile. 
# Usage: /weexaile - displays the songname
# Released under GPLv2 or newer

import weechat
import re
import codecs
from os import popen

weechat.register('exaile', '0.02', '', 'exaile-weechat current song script (usage: /weexaile)')
weechat.add_command_handler('weexaile', 'show_it_to_them')

def show_it_to_them(server, args):
  to_devnull = ' 2> /dev/null'
  exaile_running = popen('exaile --get-title' + to_devnull).readline().rstrip()
  if exaile_running != "No running Exaile instance found." :
    song_name = popen('exaile --get-title' + to_devnull).readline().rstrip()
    song_artist = popen('exaile --get-artist' + to_devnull).readline().rstrip()
    text = '/me : ' + song_artist + ' - ' + song_name
    weechat.command(text)
  return weechat.PLUGIN_RC_OK
