# This script renames your Facebook buddies to a readable format when
# using Facebook's XMPP gateway with Bitlbee or Minbif.

# Based on the Irssi script at http://browsingtheinternet.com/temp/bitlbee_rename.txt
# Ported for Weechat 0.3.0 or later by Jaakko Lintula (crwl@iki.fi)
# Modified for Minbif by 'varogami' <varogami@gmail.com>
#
# This script is in the public domain.


# Edit this variables with your own minbif/bitlbee configuration settings
fullname="Full Name"       # set the first word in full name string that "/WHOIS nick nick" or /WII show
                           # italian - fullname="Nome"
                           # spanish - fullname="Nombre completo"
                           # english - fullname="Full Name"
myChannel = "&minbif" # set "&bitlbee" or "&minbif" if you use default settings
myServer = "minbif" # set "bitlbee" or "minbif" if you use default settings

facebookhostname = "chat.facebook.com"
gmailhostname = "public.talk.google.com"

myBuffer = "%s.%s" % (myServer, myChannel)
nicksToRename = set()

import weechat
import re

weechat.register("im_rename", "crwl", "1.2", "Public Domain", "Renames Facebook anf Google Plus usernames with Minbif", "", "")

def message_join_minbif(data, signal, signal_data):
  signal_data = signal_data.split()
  channel = signal_data[2]
  hostmask = signal_data[0]
  nick = hostmask[1:hostmask.index('!')]
  username = hostmask[hostmask.index('!')+1:hostmask.index('@')]
  server = hostmask[hostmask.index('@')+1:]
  if server.find(':') > 1:
    server = server[:+server.index(':')]

  if channel == myChannel and nick == username and nick[0] == '-' and server == facebookhostname:
   nicksToRename.add(nick)
   weechat.command(weechat.buffer_search("irc", myBuffer), "/whois "+nick+" "+nick)

  if channel == myChannel and nick == "_"+username and nick[0] == '_' and server == gmailhostname:
   nicksToRename.add(nick)
   weechat.command(weechat.buffer_search("irc", myBuffer), "/whois "+nick+" "+nick)

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
       weechat.command(weechat.buffer_search("irc", myBuffer), "/quote -server %s svsnick %s %s" % (myServer, nick, ircname))

  return weechat.WEECHAT_RC_OK



weechat.hook_signal(myServer+",irc_in_join", "message_join_minbif", "")
weechat.hook_signal(myServer+",irc_in_320", "whois_data_minbif", "")
