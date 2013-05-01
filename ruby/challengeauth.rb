# Copyright (c) 2013 Dominik Honnef <dominikh@fork-bomb.org>

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

# History:
# 2013-04-20, Dominik Honnef
#   version 0.0.1: initial version

require "openssl"

QBot = "Q@CServe.quakenet.org"
QBotHost = "Q!TheQBot@CServe.quakenet.org"
Request = Struct.new(:username, :hash)

def weechat_init
  @requests = {}

  Weechat.register("challengeauth",
                   "Dominik Honnef",
                   "0.0.1",
                   "MIT",
                   "Securely authenticate with QuakeNet by using CHALLENGEAUTH",
                   "",
                   "")

  Weechat.hook_command("challengeauth",
                       "Authenticate with Q using CHALLENGEAUTH",
                       "[username] [password]",
                       "",
                       "",
                       "challengeauth",
                       "")

  Weechat.hook_modifier("irc_in_notice", "challenge_notice", "")

  return Weechat::WEECHAT_RC_OK
end

def calculate_q_hash(username, hash, challenge)
  username = username.tr("A-Z[]\\\\^", "a-z{}|~")

  key = OpenSSL::Digest::SHA256.hexdigest("#{username}:#{hash}")
  return OpenSSL::HMAC.hexdigest("SHA256", key, challenge)
end

def get_server_buffer(server)
  Weechat.buffer_search("irc", "server." + server)
end

def challengeauth(data, buffer, args)
  plugin = Weechat.buffer_get_string(buffer, "localvar_plugin")
  if plugin != "irc"
    Weechat.print(buffer, "/challengeauth only works for IRC buffers.")
    return Weechat.WEECHAT_RC_ERROR
  end

  server = Weechat.buffer_get_string(buffer, "localvar_server")
  args = args.split(" ", 2)
  username = args[0]
  password = args[1]
  hash = OpenSSL::Digest::SHA256.hexdigest(password[0, 10])

  @requests[server] = Request.new(username, hash)
  server_buffer = get_server_buffer(server)
  Weechat.print(server_buffer, "Authenticating as #{username}...")
  Weechat.command(server_buffer, "/quote PRIVMSG #{QBot} :CHALLENGE")

  return Weechat::WEECHAT_RC_OK
end

def challenge_notice(modifier, data, server, line)
  return line unless @requests.has_key?(server)

  parts = line.split(" ")
  return line unless parts.size > 5

  host = parts[0][1..-1]
  command = parts[3][1..-1]
  challenge = parts[4]

  return line if host != QBotHost || command != "CHALLENGE"

  request = @requests[server]
  response = calculate_q_hash(request.username, request.hash, challenge)
  server_buffer = get_server_buffer(server)

  Weechat.print(server_buffer, "Sending challengeauth for #{request.username}...")
  Weechat.command(server_buffer,
                  "/quote PRIVMSG %s :CHALLENGEAUTH %s %s HMAC-SHA-256" % [QBot, request.username, response])

  @requests.delete(server)

  return line
end
