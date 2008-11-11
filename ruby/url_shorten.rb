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

require 'net/http'
require 'uri'

def weechat_init
  Weechat.register "url_shorten", "1.0", "", "Shorten url"
  Weechat.add_command_handler "url_shorten", "url_shorten","/url_shorten <url>"
  Weechat.add_message_handler "privmsg", "msg_shorten"
  if ( maxlen = Weechat.get_plugin_config("maxlen") ).empty?
    Weechat.set_plugin_config("maxlen","50")
  end
  return Weechat::PLUGIN_RC_OK
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

def url_shorten(server,msg)
  if (msg.empty?)
    usage
    return Weechat::PLUGIN_RC_OK
  end
  url = (msg.scan regexp_url).to_s
  short = shortener(url)
  Weechat::print("\x0305#{short}\x0F");
  return Weechat::PLUGIN_RC_OK
end

def msg_shorten(server,args)
  if (args.empty?)
    usage
    return Weechat::PLUGIN_RC_OK
  end

  null,info,msg = args.split(":",3)
  mask,type,chan = info.split(" ")

  return Weechat::PLUGIN_RC_OK unless msg.match regexp_url

  url = (msg.scan regexp_url).to_s

  maxlen = Weechat.get_plugin_config "maxlen"
  return Weechat::PLUGIN_RC_OK if url.length < maxlen.to_i
  short = shortener(url)

  Weechat::print("\x0305#{short}\x0F",chan,server);
  return Weechat::PLUGIN_RC_OK
end

def usage
  Weechat.print %|
    /url_shorten <url>
  |
end
