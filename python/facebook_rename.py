# This script renames your Facebook buddies to a readable format when 
# using Facebook's XMPP gateway with Bitlbee. 
#
# Based on the Irssi script at http://browsingtheinternet.com/temp/bitlbee_rename.txt 
# Ported for Weechat 0.3.0 or later by Jaakko Lintula (crwl@iki.fi)
#
# This script is in the public domain.


bitlbeeChannel = "&bitlbee"
bitlbeeServer = "bitlbee"


bitlbeeBuffer = "%s.%s" % (bitlbeeServer, bitlbeeChannel)
facebookhostname = "chat.facebook.com"
nicksToRename = set()

import weechat
import re

weechat.register("facebook_rename", "crwl", "1.0.1", "Public Domain", "Renames Facebook usernames when using Bitlbee", "", "")

def message_join(data, signal, signal_data):
  signal_data = signal_data.split()
  channel = signal_data[2][1:]
  hostmask = signal_data[0]
  nick = hostmask[1:hostmask.index('!')]
  username = hostmask[hostmask.index('!')+1:hostmask.index('@')]
  server = hostmask[hostmask.index('@')+1:]
  
  if channel == bitlbeeChannel and nick == username and nick[0] == '-' and server == facebookhostname: 
    nicksToRename.add(nick)
    weechat.command(weechat.buffer_search("irc", bitlbeeBuffer), "/whois " + nick)
  
  return weechat.WEECHAT_RC_OK

def whois_data(data, signal, signal_data):
  nick = signal_data.split()[3]
  realname = signal_data[signal_data.rindex(':')+1:]
  
  if nick in nicksToRename:
    nicksToRename.remove(nick)
    
    ircname = re.sub("[^A-Za-z0-9]", "", realname)[:24]
    if ircname != nick:
      weechat.command(weechat.buffer_search("irc", bitlbeeBuffer), "/msg %s rename %s %s" % (bitlbeeChannel, nick, ircname))
      weechat.command(weechat.buffer_search("irc", bitlbeeBuffer), "/msg %s save" % (bitlbeeChannel))
      
  return weechat.WEECHAT_RC_OK


weechat.hook_signal("*,irc_in_join", "message_join", "")
weechat.hook_signal("*,irc_in_311", "whois_data", "")
