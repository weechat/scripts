#
# Copyright (c) 2009 - 2018 by kinabalu (https://mysticcoders.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Kickban script with a timeout, waits for N seconds and unbans user
#
# History:
#
# 2018-07-22, kinabalu (https://mysticcoders.com)
#       version 0.2, script cleanup and ensure py3 compatibility
# 2009-05-03, kinabalu
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
# https://www.mysticcoders.com/
#
# If you have any questions, please contact me on-line at:
#
# irc.freenode.net - kinabalu (op): ##java
#
# - kinabalu
#

import os
import string

try:
    import weechat
except ImportError:
    print('This script has to run under WeeChat (https://weechat.org/).')
    sys.exit(1)

SCRIPT_NAME = 'kbtimeout'
SCRIPT_AUTHOR = 'kinabalu (https://mysticcoders.com)'
SCRIPT_VERSION = '0.2'
SCRIPT_LICENSE = 'GPL3'

def handler(data, buffer, argList):

  split_args = argList.split(" ")
  if len(split_args) < 2:
  	weechat.prnt("", "Wrong number of parameters for kbtimeout")
  	return weechat.WEECHAT_RC_ERROR;

  nick = split_args[0]
  timeout = split_args[1]

  message = ""
  if len(split_args) > 2:
  	message = argList.split(" ", 2)[2]

  nick_ptr = weechat.nicklist_search_nick(buffer, "", nick)
  infolist = weechat.infolist_get("irc_nick", "", "{},{}".format("freenode", "##kbtimeout"))

  buffer_name = weechat.buffer_get_string(buffer, "name");

  found_ban_host = None
  while weechat.infolist_next(infolist):
      ban_nick = weechat.infolist_string(infolist, "name")
      ban_host = weechat.infolist_string(infolist, "host")
      ban_account = weechat.infolist_string(infolist, "account")

      if ban_nick == nick:
          found_ban_host = ban_host
  weechat.infolist_free(infolist)

  found_ban_host = found_ban_host[1:]

  if found_ban_host:
    weechat.command(buffer, "/kickban " + found_ban_host + " " + message)
    weechat.hook_timer(int(timeout) * 1000, 0, 1, "kickban_callback", buffer_name + ":" + found_ban_host)

  return weechat.WEECHAT_RC_OK
# END handler

def kickban_callback(data, times_left):
  details = data.split(":")
  buffer_ptr = weechat.buffer_search("irc", details[0])

  if buffer_ptr:
    weechat.command(buffer_ptr, "/unban " + details[1])
  return weechat.WEECHAT_RC_OK
# END kickban_callback

if __name__ == '__main__':
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, "kickban with timeout", "", "")

    weechat.hook_command(SCRIPT_NAME, "Kickban with ban timeout", "[nick] [timeout] [comment]", "kickban nick with comment", "%(irc_channel_nicks_hosts) %-", "handler", "")
    weechat.hook_command("kbt", "Kickban with ban timeout", "[nick] [timeout] [comment]", "kickban nick with comment", "%(irc_channel_nicks_hosts) %-", "handler", "")
