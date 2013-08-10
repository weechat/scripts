# Copyright (c) 2013, Daniel Bretoi <daniel@bretoi.com>
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
# * If maxlen is not set, uses window width to compute value for maxlen
# * allows for manual shortening of urls
# * allows for custom service. Just set plugins.var.ruby.url_shorten.custom to
#     <http://service.com/?url=>%s
# * set config variable 'shortener' to one of:
#
# Value   Service used
# -----   ------------
# qurl  http://qurl.com/
# tinyurl http://tinyurl.com/
# isgd  http://is.gd/
# bitly http://bit.ly/
# waaai http://waa.ai/

# access configs with /set plugins.var.ruby.url_shorten.*
#
# Contributors:
# Derek Carter <goozbach@friocorte.com>
# FlashCode <flashcode@flashtux.org>
# Kovensky <diogomfranco@gmail.com>
# nils_2 <weechatter@arcor.de>
# penryu <penryu@gmail.com>

require 'net/http'
require 'net/https'
require 'uri'

SCRIPT_NAME    = 'url_shorten'
SCRIPT_AUTHOR  = 'Daniel Bretoi <daniel@bretoi.com>'
SCRIPT_DESC    = 'Shorten url'
SCRIPT_VERSION = '1.9.0'
SCRIPT_LICENSE = 'BSD'
SCRIPT_REPO    = 'https://github.com/danielb2/weechat-scripts'

DEFAULTS = {
  'maxlen'      => '0',
  'color'       => 'red',
  'shortener'   => '',
  'custom'      => 'http://tinyurl.com/api-create.php?url=%s',
  'bitly_login' => '',
  'bitly_key'   => '',
  'yourls_url'  => '',
}

def weechat_init
  Weechat.register SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
  Weechat.hook_command SCRIPT_NAME, SCRIPT_DESC, "url", "url: url to shorten", "", SCRIPT_NAME, ""
  Weechat.hook_print "", "notify_message", "://", 1, "msg_shorten", ""
  Weechat.hook_print "", "notify_private", "://", 1, "msg_shorten", ""
  Weechat.hook_print "", "notify_highlight", "://", 1, "msg_shorten", ""
  set_defaults

  cwprint "[url] Shortener service set to: #{service}"

  configure_bitly
  configure_yourls

  return Weechat::WEECHAT_RC_OK
end

def configure_yourls
  if Weechat.config_get_plugin("shortener").eql?('yourls')
    # not quite ready for key based auth
    # should be researched http://code.google.com/p/yourls/wiki/PasswordlessAPI
    cfg_yourls_url   = Weechat.config_get_plugin("yourls_url")
    if cfg_yourls_url.empty?
      yellow = Weechat.color("yellow")
      Weechat.print("", "#{yellow}WARNING: The yourls shortener requires a valid API.")
      Weechat.print("", "#{yellow}WARNING: Please configure the `yourls_url' option before using this script.")
    end
  end
end

def configure_bitly
  if Weechat.config_get_plugin("shortener").eql?('bitly')
    cfg_bitly_login = Weechat.config_get_plugin("bitly_login")
    cfg_bitly_key   = Weechat.config_get_plugin("bitly_key")
    if cfg_bitly_login.empty? || cfg_bitly_key.empty?
      yellow = Weechat.color("yellow")
      Weechat.print("", "#{yellow}WARNING: The bit.ly shortener requires a valid API login and key.")
      Weechat.print("", "#{yellow}WARNING: Please configure the `bitly_login' and `bitly_key' options before using this script.")
    end
  end
end

def set_defaults
  DEFAULTS.each_pair { |option, def_value|
    cur_value = Weechat.config_get_plugin(option)
    if cur_value.nil? || cur_value.empty?
      Weechat.config_set_plugin(option, def_value)
    end
  }
end

def fetch(uri_str, limit = 10)
  raise ArgumentError, 'HTTP redirect too deep' if limit == 0

  req_url = URI.parse(uri_str)


  http = Net::HTTP.new(req_url.host, req_url.port)
  http.use_ssl = (req_url.port == 443)
  http.verify_mode = OpenSSL::SSL::VERIFY_NONE
  http.open_timeout = 3 # in seconds
  http.read_timeout = 3 # in seconds

  response = Net::HTTP.get_response(req_url)

  case response
  when Net::HTTPSuccess
    then
      response.body
  when Net::HTTPRedirection
    then
      fetch(response['location'], limit - 1)
  else
    response.error!
  end
rescue Exception => e
  return e.message
end

def url_encode(url)
  begin
    return URI.parse(url).to_s
  rescue URI::InvalidURIError
    return URI.encode(url)
  end
end

def qurl_shorten(url)
  # deprecate this one later
  shorten = 'http://www.qurl.com/automate.php?url='
  Weechat.config_set_plugin('custom', shorten + '%s')
  fetch(shorten + url).gsub('www.','')
end

def waaai_shorten(url)
  # deprecate this one later
  shorten = 'http://waa.ai/api.php?url='
  Weechat.config_set_plugin('custom', shorten + '%s')
  fetch(shorten + url)
end

def tinyurl_shorten(url)
  # deprecate this one later
  shorten = 'http://tinyurl.com/api-create.php?url='
  Weechat.config_set_plugin('custom', shorten + '%s')
  fetch(shorten + url)
end

def isgd_shorten(url)
  # deprecate this one later
  shorten = 'http://is.gd/api.php?longurl='
  Weechat.config_set_plugin('custom', shorten + '%s')
  fetch(shorten + url)
end

# current window print
def cwprint(str)
  Weechat.print(Weechat.current_buffer, str.to_s)
end

def get_config_string(string)
  option = Weechat.config_get(string)
  Weechat.config_string(option)
end

def window_width
  time_stamp_width = Time.now.strftime(get_config_string('weechat.look.buffer_time_format')).size
  current_window_width = Weechat.window_get_integer(Weechat.current_window, "win_chat_width")
  max_nick_length = 16
  current_window_width - max_nick_length - time_stamp_width
end

def yourls_shorten(url)
  # use yourls shortener
  # need to provide url config option
  require 'rubygems'
  require 'json/pure'
  params = ['action=shorturl']
  params << 'format=simple'
  params << 'url=' + url
  yourls_url = Weechat.config_get_plugin('yourls_url')
  api_url = yourls_url + params.join('&')
  begin
    body_txt = fetch(api_url)
  rescue Exception => ex
    return "Failure yourls shortening url: " + ex.to_s
  end
  body_txt
end

def bitly_shorten(url)
  require 'rubygems'
  require 'json'

  params = ['longUrl=' + url]
  params << 'login=' + Weechat.config_get_plugin('bitly_login')
  params << 'apiKey=' + Weechat.config_get_plugin('bitly_key')
  api_url = 'http://api.bit.ly/shorten?version=2.0.1&' + params.join('&')

  begin
    url_data = JSON.parse(fetch(api_url))
  rescue Exception => ex
    return "Failure shortening url: " + ex.to_s
  end

  if url_data['statusCode'].eql?('OK')
    begin
      res = url_data['results']
      res[res.keys[0]]['shortUrl']
    rescue NoMethodError => ex
      "Failure parsing bitly result: #{ex}"
    end
  else
    url_data['errorMessage']
  end
end

def service
  custom =  Weechat.config_get_plugin('custom')
  return custom if custom.size > 0
  Weechat.config_get_plugin('shortener').tr('.','')
end

def shortener(url)
  return fetch(custom_url(url)) if custom_url(url).size > 0

  begin
    return send("#{service}_shorten", url_encode(url))
  rescue NoMethodError => e
      "Shortening service #{service} not supported... #{e}"
  end
end

def custom_url(url)
  sprintf Weechat.config_get_plugin('custom'), url_encode(url)
end

def regexp_url
  @regexp_url ||= Regexp.new('https?://[^\s>]*')
  @regexp_url
end

def url_shorten(data,buffer,msg)
  if (msg.empty?)
    return Weechat::WEECHAT_RC_OK
  end
  url = (msg.scan regexp_url).to_s
  short = shortener(url)
  color = Weechat.color(Weechat.config_get_plugin("color"))
  Weechat.print(Weechat.current_buffer, "[url]:\t#{color}#{short}");
  return Weechat::WEECHAT_RC_OK
end

def msg_shorten(data,buffer,time,tags,displayed,highlight,prefix,message)
  if (message.empty?)
    return Weechat::WEECHAT_RC_OK
  end

  matchdata = message.match(regexp_url)
  return Weechat::WEECHAT_RC_OK unless matchdata

  url = matchdata[0].to_s
  maxlen = Weechat.config_get_plugin("maxlen").to_i
  maxlen = window_width if maxlen == 0
  return Weechat::WEECHAT_RC_OK if url.length < maxlen

  short = shortener(url)
  color = Weechat.color(Weechat.config_get_plugin("color"))
  Weechat.print(buffer, "[url]:\t%s%s" % [color, short])
  return Weechat::WEECHAT_RC_OK
end
