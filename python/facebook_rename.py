# This script renames your Facebook buddies to a readable format when
# using Facebook's XMPP gateway with Bitlbee or Minbif.

# Based on the Irssi script at http://browsingtheinternet.com/temp/bitlbee_rename.txt
# Ported for Weechat 0.3.0 or later by Jaakko Lintula (crwl@iki.fi)
# Modified for Minbif by 'varogami' <varogami@gmail.com>
# Testing contrib 'bizio' <maestrozappa@gmail.com>
#
# This script is in the public domain.


# Edit this variables with your own minbif configuration settings

# Set the first word in full name string that "/WHOIS nick nick" or /WII show
#   italian - fullname="Nome"
#   spanish - fullname="Nombre completo"
fullname="Name"
mode = "minbif"  # set 'bitlbee' or 'minbif' to select gateway type
minbifChannel = "&minbif"
minbifServer = "minbif"
bitlbeeChannel = "&bitlbee"
bitlbeeServer = "bitlbee"
facebookhostname = "chat.facebook.com"

minbifBuffer = "%s.%s" % (minbifServer, minbifChannel)
bitlbeeBuffer = "%s.%s" % (bitlbeeServer, bitlbeeChannel)
nicksToRename = set()

import weechat
import re

weechat.register("facebook_rename", "crwl", "1.1.2", "Public Domain", "Renames Facebook usernames when using Bitlbee or Minbif", "", "")

def message_join_minbif(data, signal, signal_data):
  signal_data = signal_data.split()
  channel = signal_data[2]
  hostmask = signal_data[0]
  nick = hostmask[1:hostmask.index('!')]
  username = hostmask[hostmask.index('!')+1:hostmask.index('@')]
  server = hostmask[hostmask.index('@')+1:]
  if server.find(':') > 1:
    server = server[:+server.index(':')]

  if channel == minbifChannel and nick == username and nick[0] == '-' and server == facebookhostname:
   nicksToRename.add(nick)
   weechat.command(weechat.buffer_search("irc", minbifBuffer), "/whois "+nick+" "+nick)

  return weechat.WEECHAT_RC_OK

def whois_data_minbif(data, signal, signal_data):
  if fullname in signal_data:
   nick = signal_data.split(fullname)[0].strip()
   nick = nick[1:nick.index(' :')]
   nick = nick.split(' ')
   nick = nick[3]
   realname =  signal_data.split(fullname)[1].strip()

   if nick in nicksToRename:
     nicksToRename.remove(nick)
     ircname = re.sub("[^A-Za-z0-9]", "", realname)[:24]
     if ircname != nick:
       weechat.command(weechat.buffer_search("irc", minbifBuffer), "/quote -server %s svsnick %s %s" % (minbifServer, nick, ircname))

  return weechat.WEECHAT_RC_OK

def message_join_bitlbee(data, signal, signal_data):
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

def whois_data_bitlbee(data, signal, signal_data):
  nick = signal_data.split()[3]
  realname = signal_data[signal_data.rindex(':')+1:]

  if nick in nicksToRename:
    nicksToRename.remove(nick)

    ircname = re.sub("[^A-Za-z0-9]", "", realname)[:24]
    if ircname != nick:
      weechat.command(weechat.buffer_search("irc", bitlbeeBuffer), "/msg %s rename %s %s" % (bitlbeeChannel, nick, ircname))
      weechat.command(weechat.buffer_search("irc", bitlbeeBuffer), "/msg %s save" % (bitlbeeChannel))

  return weechat.WEECHAT_RC_OK

if mode == "minbif":
  weechat.hook_signal(minbifServer+",irc_in_join", "message_join_minbif", "")
  weechat.hook_signal(minbifServer+",irc_in_320", "whois_data_minbif", "")
if mode == "bitlbee":
  weechat.hook_signal(bitlbeeServer+",irc_in_join", "message_join_bitlbee", "")
  weechat.hook_signal(bitlbeeServer+",irc_in_311", "whois_data_bitlbee", "")
