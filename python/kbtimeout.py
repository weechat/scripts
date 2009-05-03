#
# Copyright (c) 2009 by kinabalu (andrew AT mysticcoders DOT com)
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
#

#
# Kickban script with a timeout, waits for N seconds and unbans user
#
# History:
#
# 2009-05-03, kinabalu <andrew AT mysticcoders DOT com>
#       version 0.1, initial version
#
# /kbtimeout and /kbt can be used in combination with these actions
#
# /kbt [nick] [timeout] [message]
# /help kbt
#
# The script can be laoded into WeeChat by executing:
#
# /python load kbtimeout.py
#
# The script may also be auto-loaded by WeeChat.  See the
# WeeChat manual for instructions about how to do this.
#
# For up-to-date information about this script, and new
# version downloads, please go to:
#
# http://www.mysticcoders.com/apps/kickban-timeout/
#
# If you have any questions, please contact me on-line at:
#
# irc.freenode.net - kinabalu (op): ##java
#
# - kinabalu
#


import        os
import        string
import        weechat	

def handler(data, buffer, argList):

  if len(argList.split(" ")) < 2:
  	weechat.prnt("", "Wrong number of parameters for kbtimeout")
  	return weechat.WEECHAT_RC_ERROR;
  
  nick = argList.split(" ")[0]
  timeout = argList.split(" ")[1]
  
  message = ""
  if len(argList.split(" ")) > 2:
  	message = argList.split(" ", 2)[2]

  nick_ptr = weechat.nicklist_search_nick(buffer, "", nick)
  
  buffer_name = weechat.buffer_get_string(buffer, "name");
  if nick_ptr:
    weechat.command(buffer, "/kickban " + nick + " " + message)
    weechat.hook_timer(int(timeout) * 1000, 0, 1, "kickban_callback", buffer_name + ":" + nick)
   	
  return weechat.WEECHAT_RC_OK
# END handler

def kickban_callback(data, times_left):
  details = data.split(":")
  buffer_ptr = weechat.buffer_search("irc", details[0])

  if buffer_ptr:
    weechat.command(buffer_ptr, "/unban " + details[1])
  return weechat.WEECHAT_RC_OK
# END kickban_callback  

# *** Script starts here ***

weechat.register("kbtimeout", "kinabalu <andrew@mysticcoders.com>", "0.1", "GPL2", "kickban with timeout", "", "")

weechat.hook_command("kbtimeout", "Kickban with ban timeout", "[nick] [timeout] [comment]", "kickban nick with comment", "%(irc_channel_nicks_hosts) %-", "handler", "")
