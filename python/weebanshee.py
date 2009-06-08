# Weechat now-playing script for Banshee (tested for 1.4.3)
# Author: Vitaly Dolgov [ ferhiord@gmail.com ]
# Usage: /weebanshee
# Released under GPLv2

import os
import weechat

name = 'weebanshee'
version = '0.1'
banshee = 'banshee-1'

weechat.register(name, version, '', 
    'now-playing script for banshee (usage: /%s)' % name)
weechat.add_command_handler(name, 'show')

def show(server, args) :
  if os.popen('ps -e | grep %s' % banshee).read() == '' :
    return weechat.PLUGIN_RC_KO
  if os.popen('%s --query-current-state' % banshee
      ).read().strip().split(' ')[1] == 'idle' :
    return weechat.PLUGIN_RC_KO
  artist = os.popen('%s --query-artist' % banshee
      ).read().strip().split(' ', 1)[1]
  title  = os.popen('%s --query-title'  % banshee
      ).read().strip().split(' ', 1)[1]
  text = '/me : %s - %s' % (artist, title)
  weechat.command(text)
  return weechat.PLUGIN_RC_OK
