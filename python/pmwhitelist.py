#
# Copyright (c) 2007 by pr3d4t0r (tek_fox AT internet.lu)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# pmwhitelist.py -- GPLv2
#
# Private messages white list for WeeChat 0.2.x.
# This script implements the commands /whitelist or
# /wl for managing users into a white list.  The WeeChat user will only
# receive private messages from white listed users.  All others will 
# receive an automatic response indicating that the message didn't reach
# the WeeChat user and instructions to make an in-channel request 
# to be added to the white list.
#
# /whitelist and /wl can be used in combination with these actions:
#
# /whitelist add nick
# /whitelist del nick
# /whitelist view
# /whitelist help
#
# The script can be loaded into WeeChat by executing:
#
# /python load pmwhitelist.py
#
# The script may also be auto-loaded by WeeChat.  See the
# WeeChat manual for instructions about how to do this.
#
# This script was tested with WeeChat versions 0.2.4 and
# 0.2.6.  An updated version of this script will be available
# when the new WeeChat API is released.
#
# For up-to-date information about this script, and new
# version downloads, please go to:
#
# http://eugeneciurana.com/site.php?page=tools
#
# If you have any questions, please contact me on-line at:
#
# irc.freenode.net - pr3d4t0r (op):  ##java, #awk, #esb
# irc.freenode.net - pr3d4t0r (op):  #java
# irc.osx86.hu     - pr3d4t0r (op):  #iphone-dev
#
# The fastest way to make feature requests or report a bug:
#
# http://eugeneciurana.com/site.php?page=contact
#
# Cheers!
#
# pr3d4t0r


import        os
import        string
import        weechat


# *** Symbolic constants ***

FILE_NAME     = "white_list.dat"

COMMANDS      = [ "add", "del", "view", "help" ]


# *** Implementation and callback functions ***

def end_PMWhiteList():
  weechat.prnt("PMWhiteList: ending...")
  
  return weechat.PLUGIN_RC_OK
# end_PMWhiteList


def killPrivateMessage(bufferSender, bufferHome, myNick):
  weechat.command("/buffer "+bufferSender)
  weechat.command("/say AUTOREPLY:  "+myNick+" does not accept unsolicited private messages.  Your message didn't reach the recipient.  Please ask for your nick to be white listed in-channel.  Thank you.")
  weechat.command("/close")
  weechat.command("/buffer "+bufferHome)
# killPrivateMessage


def whiteListFileName():
  return weechat.get_info("weechat_dir")+"/"+FILE_NAME;
# whiteListFileName


def  readList():
  whiteList = []  # init
  if os.access(whiteListFileName(), os.F_OK) == False:
    outputFile = open(whiteListFileName(), "wb")
    outputFile.writelines(whiteList)
    outputFile.close()

  inputFile = open(whiteListFileName(), "rb")
  list      = inputFile.readlines()
  inputFile.close()

  for item in list:
    item = item.replace('\n', '')
    whiteList.append(item)

  whiteList.sort()
  return whiteList
# readList


def writeList(whiteList):
  outputFile = open(whiteListFileName(), "wb")
  outputFile.writelines(whiteList)
  outputFile.close()
# writeList


def isOnList(nickSender):
  whiteList = readList()

  for nick in whiteList:
    if (nickSender.lower() == nick.lower()):
      return True

  return False
# isOnList


def whiteListAdd(nick):
  if (len(nick) < 1):
    return

  weechat.print_server("Private message white list add: "+nick)
  list = readList()
  list.append(nick)

  whiteList = []
  for item in list:
    whiteList.append(item+"\n")

  writeList(whiteList)
# whiteListAdd


def whiteListDel(nick):
  weechat.print_server("Private message white list delete: "+nick)
  list      = readList()
  whiteList = []
  for item in list:
    if item != nick:
      whiteList.append(item+"\n")

  writeList(whiteList)
# whiteListDel


def whiteListDisplay():
  weechat.print_server("*** Begin private message white list:")
  for nick in readList():
    weechat.print_server(nick)

  weechat.print_server("*** End private message white list\n")
# whiteListDisplay


def PMWLInterceptor(server, argList):
  bufferSender = argList.split(":")[1].split(" ")[0].split("!")[0]
  nickSender   = bufferSender
  bufferHome   = weechat.get_info("channel", server)
  myNick       = weechat.get_info("nick", server)

  if os.access(whiteListFileName(), os.F_OK) == False:
    killPrivateMessage(bufferSender, bufferHome)
    return weechat.PLUGIN_RC_OK

  if (False == isOnList(nickSender)):
    killPrivateMessage(bufferSender, bufferHome, myNick)

  return weechat.PLUGIN_RC_OK
# PMWLInterceptor


def PMWLCommandHandler(server, argList):
  command = argList.split(" ")[0]

  if command not in COMMANDS:
    return weechat.PLUGIN_RC_KO

  if len(argList.split(" ")) > 1:
    argument = argList.split(" ")[1]
  else:
    argument = ""

  if (command.lower() == "view"):
    whiteListDisplay()
    return weechat.PLUGIN_RC_OK

  if (len(argument) < 1):
    return weechat.PLUGIN_RC_KO

  if (command.lower() == "add"):
    whiteListAdd(argument)

  if (command.lower() == "del"):
    whiteListDel(argument)

  return weechat.PLUGIN_RC_OK
# PMWLCommandHandler


# *** Script starts here ***

weechat.register("PMWhiteList", "0.1", "end_PMWhiteList", "Private messages white list", "UTF-8");
weechat.set_charset("UTF-8");
weechat.add_message_handler("weechat_pv", "PMWLInterceptor")
weechat.add_command_handler("whitelist", "PMWLCommandHandler", "Private message white list", "add|del|view", "add nick, delete nick, or view white list", "add|del|view")
weechat.add_command_handler("wl", "PMWLCommandHandler", "Private message white list (shorthand for /whitelist)", "add|del|view", "add nick, delete nick, or view white list", "add|del|view")
