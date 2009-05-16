# Copyright (c) 2008, Daniel Bretoi <daniel@bretoi.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY Daniel Bretoi ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# * Simpler, more robust version of tinyurl (doesn't rely on html output)
# * Echo's urls from all channels that are over the plugin's maxlen value
#     in a shortened format.
# * allows for manual shortening of urls
# * set the shortener function alias to point to favorite shortener (qurl,tinyurl)
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 1.2: sync with last API changes
# 2008-11-11, FlashCode <flashcode@flashtux.org>:
#     version 1.1: conversion to WeeChat 0.3.0+

require 'net/http'
require 'uri'

def weechat_init
  Weechat.register "url_shorten", "Daniel Bretoi <daniel@bretoi.com>", "1.2", "BSD", "Shorten url", "", ""
  Weechat.hook_command "url_shorten", "Shorten URL", "url", "url: url to shorten", "", "url_shorten", ""
  Weechat.hook_signal "*,irc_in2_privmsg", "msg_shorten", ""
  if (maxlen = Weechat.config_get_plugin("maxlen")).empty?
    Weechat.config_set_plugin("maxlen","50")
  end
  if (color = Weechat.config_get_plugin("color")).empty?
    Weechat.config_set_plugin("color","red")
  end
  return Weechat::WEECHAT_RC_OK
end

def fetch(uri_str, limit = 10)
  raise ArgumentError, 'HTTP redirect too deep' if limit == 0
  
  response = Net::HTTP.get_response(URI.parse(uri_str))
  case response
  when Net::HTTPSuccess     then response.body
  when Net::HTTPRedirection then fetch(response['location'], limit - 1)
  else
    response.error!
  end
end

def qurl_shorten(url)
  fetch('http://www.qurl.com/automate.php?url='+url).gsub('www.','')
end

def tinyurl_shorten(url)
  fetch('http://tinyurl.com/api-create.php?url='+url)
end
alias shortener qurl_shorten

def regexp_url
  @regexp_url ||= Regexp.new('https?://[^\s]*')
  @regexp_url
end

def url_shorten(data,buffer,msg)
  if (msg.empty?)
    return Weechat::WEECHAT_RC_OK
  end
  url = (msg.scan regexp_url).to_s
  short = shortener(url)
  color = Weechat.color(Weechat.config_get_plugin("color"))
  Weechat.print(Weechat.current_buffer, "[url]\t#{color}#{short}");
  return Weechat::WEECHAT_RC_OK
end

def msg_shorten(data,signal,message)
  if (message.empty?)
    return Weechat::WEECHAT_RC_OK
  end
  
  server,null = signal.split(",",2)
  null,info,msg = message.split(":",3)
  mask,type,channel = info.split(" ")
  
  return Weechat::WEECHAT_RC_OK unless msg.match regexp_url
  
  url = (msg.scan regexp_url).to_s
  
  maxlen = Weechat.config_get_plugin "maxlen"
  return Weechat::WEECHAT_RC_OK if url.length < maxlen.to_i
  short = shortener(url)
  
  buffer = Weechat.info_get("irc_buffer", "#{server},#{channel}");
  color = Weechat.color(Weechat.config_get_plugin("color"))
  Weechat.print(buffer, "[url]\t#{color}#{short}");
  return Weechat::WEECHAT_RC_OK
end
