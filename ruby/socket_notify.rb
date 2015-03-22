# socket_notify
# ruby script to write hilights to a unix socket
#
# Author: Christopher Giroir <kelsin@valefor.com>
#
# Copyright (c) 2014 Christopher Giroir
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

require 'socket'
require 'base64'

SCRIPT_NAME = 'socket_notify'
SCRIPT_AUTHOR = 'Christopher Giroir <kelsin@valefor.com>'
SCRIPT_DESC = 'Send highlights and private message to a unix socket'
SCRIPT_VERSION = '0.0.1'
SCRIPT_LICENSE = 'MIT'

SOCKET = '/tmp/weechat.notify.sock'

def weechat_init
  Weechat.register SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
  Weechat.hook_print("", "notify_message", "", 1, "hilite", "")
  Weechat.hook_print("", "notify_private", "", 1, "private", "")
  return Weechat::WEECHAT_RC_OK
end

def send(subtitle, message)
  if File.exists?(SOCKET) and File.socket?(SOCKET)
    UNIXSocket.open(SOCKET) do |socket|
      socket.puts "#{Base64.strict_encode64(subtitle)} #{Base64.strict_encode64(message)}"
    end rescue nil
  end
end

def hilite(data, buffer, date, tags, visible, highlight, prefix, message)
  if ! highlight.to_i.zero?
    data = {}
    %w{type channel server}.each do |meta|
      data[meta.to_sym] = Weechat.buffer_get_string(buffer, "localvar_#{meta}");
    end

    if data[:type] == "channel"
      subtitle = "#{data[:server]}##{data[:channel]} Highlight"
      send(subtitle, message)
    end
  end

  return Weechat::WEECHAT_RC_OK
end

def private(data, buffer, date, tags, visible, highlight, prefix, message)
  data = {}
  %w{type channel server}.each do |meta|
    data[meta.to_sym] = Weechat.buffer_get_string(buffer, "localvar_#{meta}");
  end

  unless data[:channel] == data[:server]
    subtitle = "Private message from #{data[:channel]}"
    send(subtitle, message)
  end

  return Weechat::WEECHAT_RC_OK
end
