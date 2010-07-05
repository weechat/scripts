
# -*- coding: utf-8 -*-
"""
Author: SAEKI Yoshiyasu <laclef_yoshiyasu@yahoo.co.jp>
Homepage: http://bitbucket.org/laclefyoshi/weechat/
Version: 1.0
License: MIT License

This plugin requires "notifo" in your iPod touch/iPhone
See here: http://notifo.com/
"""

import weechat
import urllib
import urllib2

## registration

weechat.register("notifo_notify", "SAEKI Yoshiyasu", "1.0", "MIT License",
    "notifo_notify: Push notification to iPod touch/iPhone with notifo", "", "")

## settings

script_options = {
    "username": "",
    "api_secret": ""
}

for option, default_value in script_options.items():
    if weechat.config_get_plugin(option) == "":
        weechat.prnt("", weechat.prefix("error") + "notifo_notify: Please set option: %s" % option)
        weechat.prnt("", "notifo_notify: /set plugins.var.python.notifo_notify.%s STRING" % option)

## functions

def postNotifo(message, handler=None, label=None, title=None):
    NOTIFO_USER = weechat.config_get_plugin("username")
    NOTIFO_API_SECRET = weechat.config_get_plugin("api_secret")
    if NOTIFO_USER != "" and NOTIFO_API_SECRET != "":
        url = "https://api.notifo.com/v1/send_notification"
        opt_dict = {
            "msg": message,
            "label": label,
            "title":title
            }
        opt = urllib.urlencode(opt_dict)
        req = urllib2.Request(url, opt)
        basic = "Basic %s" % ":".join([NOTIFO_USER, NOTIFO_API_SECRET]).encode("base64").strip()
        req.add_header("Authorization", basic)
        res = urllib2.urlopen(req)

def signal_callback(data, signal, signal_data):
    if signal == "weechat_pv":
        postNotifo(signal_data, label="weechat", title="Private Message")
    elif signal == "weechat_highlight":
        postNotifo(signal_data, label="weechat", title="Highlight")
    return weechat.WEECHAT_RC_OK

weechat.hook_signal("weechat_highlight", "signal_callback", "")
weechat.hook_signal("weechat_pv", "signal_callback", "")

