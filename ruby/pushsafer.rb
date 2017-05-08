# Pushsafer.com Kevin Siml 
# https://github.com/appzer/pushsafer-weechat
# http://www.pushsafer.com
#
# pushsafer for Weechat
# ---------------
#
# Send private messages and highlights to your Android, iOS & Windows 10 devices via
# the Pushsafer service (https://www.pushsafer.com)
#
# Install
# -------
#
#   Load the pushsafer-weechat.rb plugin into Weechat. Place it in the
#   ~/.weechat/ruby directory:
#
#        /ruby load pushsafer-weechat.rb
#
#   It also requires a Pushsafer account.
#
# Setup
# -----
#
#   Set your Pushsafer private or alias key.
#
#       /set plugins.var.ruby.pushsafer-weechat.privatekey 123456789abcdefgh
#
# Options
# -------
#
#   plugins.var.ruby.pushsafer-weechat.privatekey
#
#       The private key for your Pushsafer service.
#       Default: Empty string
#
#   plugins.var.ruby.pushsafer-weechat.interval
#
#       The interval between notifications. Doesn't notify if the last
#       notification was within x seconds.
#       Default: 60 seconds
#
#   plugins.var.ruby.pushsafer-weechat.away
#
#       Check whether the client is to /away for the current buffer and
#       notifies if they're away. Set to on for this to happen.
#       Default: off
#
#   plugins.var.ruby.pushsafer-weechat.sound
#
#       Set your notification sound
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       a number 0-28 0 = silent, blank = device default
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.device
#
#       Set your notification device
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       your device or device group id, if empty = to all devices
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.icon
#
#       Set your notification icon
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       a number 1-98
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.vibration
#
#       Set your notification vibration
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       a number 0-3
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.time2live
#
#       Set your notification time to live
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       a number 0-43200: Time in minutes, after which message automatically gets purged.
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.url
#
#       Set your notification url
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       a url or url scheme
#       Default: blank
#
#   plugins.var.ruby.pushsafer-weechat.urltitle
#
#       Set your notification url title
#       options (Current listing located at https://www.pushsafer.com/en/pushapi)
#       title of url
#       Default: blank


# fix for weechat UTF_7 encoding issue
require 'enc/encdb.so'

require 'rubygems'
require 'net/https'

SCRIPT_NAME = 'pushsafer-weechat'
SCRIPT_AUTHOR = 'Pushsafer.com Kevin Siml <kevinsiml@googlemail.com>'
SCRIPT_DESC = 'Send highlights and private messages in channels to your Android, Windows 10 or IOS device via Pushsafer'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'APL'

DEFAULTS = {
  'privatekey'      => "",
  'interval'        => "60",
  'sound'           => "",
  'device'          => "",
  'icon'            => "",
  'vibration'       => "",
  'time2live'       => "",
  'url'             => "",
  'urltitle'        => "",
  'away'            => 'off'
}

def weechat_init
  Weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")
  DEFAULTS.each_pair do |option, def_value|
    cur_value = Weechat.config_get_plugin(option)
    Weechat.config_set_plugin(option, def_value) if cur_value.nil? || cur_value.empty?
  end

  @last = Time.now - Weechat.config_get_plugin('interval').to_i

  Weechat.print("", "pushsafer-weechat: Please set your private key with: /set plugins.var.ruby.pushsafer-weechat.privatekey")
  Weechat.hook_signal("weechat_highlight", "notify", "")
  Weechat.hook_signal("weechat_pv", "notify", "")

  return Weechat::WEECHAT_RC_OK
end

def notify(data, signal, signal_data)

  @last = Time.now unless @last

  # Only check if we're away if the plugin says to, only notify if we are
  # away.
  if Weechat.config_get_plugin('away') == 'on'
    buffer = Weechat.current_buffer
    isaway = Weechat.buffer_get_string(buffer, "localvar_away") != ""

    return Weechat::WEECHAT_RC_OK unless isaway
  end

  if signal == "weechat_pv"
    event = "Weechat Private message from #{signal_data.split.first}"
  elsif signal == "weechat_highlight"
    event = "Weechat Highlight from #{signal_data.split.first}"
  end

  if (Time.now - @last) > Weechat.config_get_plugin('interval').to_i
    url = URI.parse("https://www.pushsafer.com/api")
    req = Net::HTTP::Post.new(url.path)
    req.set_form_data({
      :k   => Weechat.config_get_plugin('privatekey'),
      :s   => Weechat.config_get_plugin('sound'),
	  :d   => Weechat.config_get_plugin('device'),
	  :i   => Weechat.config_get_plugin('icon'),
	  :v   => Weechat.config_get_plugin('vibration'),
	  :l   => Weechat.config_get_plugin('time2live'),
	  :u   => Weechat.config_get_plugin('url'),
	  :ut  => Weechat.config_get_plugin('urltitle'),
      :t   => event,
      :m   => signal_data[/^\S+\t(.*)/, 1]
    })
    res = Net::HTTP.new(url.host, url.port)
    res.use_ssl = true
    res.verify_mode = OpenSSL::SSL::VERIFY_NONE
    res.start { |http| http.request(req) }
    @last = Time.now
  else
    Weechat.print("", "weechat-pushsafer: Skipping notification, too soon since last notification")
  end

  return Weechat::WEECHAT_RC_OK
end

__END__
__LICENSE__

Copyright 2017 Pushsafer.com

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
