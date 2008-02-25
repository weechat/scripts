## auto_dcc_own_ip.rb
# Copyright (C) 2008 Dag Odenhall <dag.odenhall@gmail.com>
# Licensed under the Academic Free License version 3.0
# http://www.rosenlaw.com/AFL3.0.htm

require 'open-uri'

def weechat_init
  Weechat.register("auto_dcc_own_ip", "0.1", "", "Automatic dcc_own_ip")
  Weechat.set_config("dcc_own_ip", open("http://tnx.nl/ip").read)
  Weechat::PLUGIN_RC_OK
end
