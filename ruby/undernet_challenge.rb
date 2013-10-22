# Copyright (c) 2013, Daniel Bretoi <daniel@bretoi.com>
# Released under BSD license.

require 'net/http'
require 'net/https'
require 'uri'

SCRIPT_NAME    = 'undernet_challenge'
SCRIPT_AUTHOR  = 'Daniel Bretoi <daniel@bretoi.com>'
SCRIPT_DESC    = 'respond to undernet challenge when theres no identd. Example: Ident broken or disabled, to continue to connect you must type /QUOTE PASS 29079'
SCRIPT_VERSION = '0.1.0'
SCRIPT_LICENSE = 'BSD'
SCRIPT_REPO    = 'https://github.com/danielb2/weechat-scripts'

def weechat_init
  Weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")
  Weechat.hook_signal("irc_server_connecting", "connecting_cb", "")
  return Weechat::WEECHAT_RC_OK
end

def connecting_cb(data, signal, signal_data)
  @notice_hook ||= Weechat.hook_signal("*,irc_raw_in_notice", "notice_cb", "")
  return Weechat::WEECHAT_RC_OK
end

def notice_cb(data, signal, signal_data)
  if signal_data.include? "Ident broken or disabled, to continue to connect you must type"
    server = signal.split(',')[0]
    passwd = signal_data.split(" ")[-1]
    Weechat.print('',"Sending UnderNet quote pass: #{passwd}")
    corebuf = Weechat.buffer_search_main()
    Weechat.command(corebuf, sprintf("/quote -server %s pass %s", server,passwd))
    Weechat.unhook(@notice_hook)
    @notice_hook = nil
  end
  return Weechat::WEECHAT_RC_OK
end
