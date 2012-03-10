# Copyright (c) 2012 Dominik Honnef <dominikh@fork-bomb.org>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This script relays incoming DCC SEND requests to a different nick.
# This is for example useful if you have your main weechat running on
# a server but want to download files via DCC directly to your local
# computer. In that case, you would simply run a second weechat (or
# any other client) on your local computer and configure this script
# to forward them to it.

# There are two options, one of which is required:
#
# - plugins.var.ruby.dcc_send_relay.relay_nick : The nickname to
#     forward the requests to
#
# - plugins.var.ruby.dcc_send_relay.relay_server : The server name to
#     forward the requests to. If this is not set, this script uses the
#     same server the request came from. If you're connected to multiple
#     networks, however, it is best to set this variable so that your
#     local client doesn't have to be connected to all those servers.
#     The value of the variable has to match the name of the server
#     buffer you want to use.

# History:
# 2012-03-06, Dominik Honnef
#   version 0.0.1: initial version

def weechat_init
  Weechat.register("dcc_send_relay",
                   "Dominik Honnef",
                   "0.0.1",
                   "MIT",
                   "Relay DCC SEND requests to a different IRC client.",
                   "",
                   "")
  Weechat.hook_modifier "irc_in_privmsg", "dcc_send_cb", ""
  return Weechat::WEECHAT_RC_OK
end

def dcc_send_cb(data, signal, server, args)
  msg     = Weechat.info_get_hashtable("irc_message_parse", "message" => args)
  message = msg["arguments"].split(":", 2)

  if message[1] !~ /^\001DCC SEND .+\001$/
    return args
  end

  target_server = Weechat.config_get_plugin("relay_server")
  target_server = server if target_server.empty?
  server_buffer = Weechat.buffer_search("irc", "server." + target_server)
  target_nick   = Weechat.config_get_plugin("relay_nick")

  if target_nick.empty?
    Weechat.print("", "Cannot relay DCC SEND without a configured target nick.")
    return args
  end

  if server_buffer.empty?
    Weechat.print("", "Couldn't find a server buffer for '#{target_server}'.")
    return args
  end

  Weechat.command(server_buffer, "/MSG %s %s" % [target_nick, message[1]])
  return ""
end
