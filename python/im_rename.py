# This script renames your Facebook buddies to a readable format when
# using Facebook's XMPP gateway with Bitlbee or Minbif.

# Based on the Irssi script at http://browsingtheinternet.com/temp/bitlbee_rename.txt
# Ported for Weechat 0.3.0 or later by Jaakko Lintula (crwl@iki.fi)
# Modified for Minbif by 'varogami' <varogami@gmail.com>
# Remodified for Bitlbee-purple on localhost by Abhishek Cherath <abhicherath@gmail.com>
#
# This script is in the public domain.


# Edit this variables with your own minbif/bitlbee configuration settings
myChannel = "&bitlbee" # set "&bitlbee" or "&minbif" if you use default settings
myServer = "localhost" # set "bitlbee" or "minbif" if you use default settings

#minbif seems really old and unused at this point shift to only bitlbee? 
#looking around on net hangouts doesn't seem to need this tool so only keep facebook?

#facebookhostname = "chat.facebook.com"
facebookhostname = "facebook" #this is the new host name for facebook messenger
gmailhostname = "public.talk.google.com"

myBuffer = "%s.%s" % (myServer, myChannel)
nicksToRename = set()

import weechat
import re

weechat.register("im_rename", "crwl", "1.2", "Public Domain", "Renames Facebook usernames with Bitlbee", "", "") #google plus no longer exists

def message_join_minbif(data, signal, signal_data):
  """When someone logs on call whois in server"""
  signal_data = signal_data.split()
  channel = signal_data[2][signal_data[2].index(':')+1:]
  hostmask = signal_data[0]
  nick = hostmask[1:hostmask.index('!')]
  username ="_"+ hostmask[hostmask.index('!')+1:hostmask.index('@')]
  server = hostmask[hostmask.index('@')+1:]
  if server.find(':') > 1:
    server = server[:+server.index(':')]

 # if channel == myChannel and nick == username and nick[0] == '-' and server == facebookhostname:
  if channel == myChannel and nick == username and nick[0] == '_' and server == facebookhostname:
   nicksToRename.add(nick)
   weechat.command(weechat.buffer_search("irc", myBuffer), "/whois "+nick+" "+nick)

  if channel == myChannel and nick == "_"+username and nick[0] == '_' and server == gmailhostname:
   nicksToRename.add(nick)
   weechat.command(weechat.buffer_search("irc", myBuffer), "/whois "+nick+" "+nick)

  return weechat.WEECHAT_RC_OK

def whois_data_minbif(data, signal, signal_data):
  """Get data from irc_in_311 and parse name from there. """
  if "facebook" in signal_data:
    realname = signal_data[signal_data.index(" :"):].strip(" :")
    nick = signal_data[signal_data.index("_"):signal_data.index(" ",signal_data.index("_"))]
    weechat.prnt("",str(nicksToRename))

  if nick in nicksToRename:
    nicksToRename.remove(nick)
    ircname = re.sub("[^A-Za-z0-9]", "", realname)[:24]
    weechat.prnt("",ircname)
    if ircname != nick:
      weechat.command(weechat.buffer_search("irc", myBuffer), "rename %s %s" %  (nick, ircname))

  return weechat.WEECHAT_RC_OK



weechat.hook_signal(myServer+",irc_in_join", "message_join_minbif", "") #calls message_join_minbif when someone joins the channel
weechat.hook_signal(myServer+",irc_in_311", "whois_data_minbif", "") #calls the facebook name reassigner when /whois is called.
