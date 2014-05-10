# -*- coding: utf-8 -*-
# Author: ochameau <poirot.alex AT gmail DOT com>
# Homepage: https://github.com/ochameau/weechat-notifo
# Derived from: notify
#   Author: lavaramano <lavaramano AT gmail DOT com>
#   Improved by: BaSh - <bash.lnx AT gmail DOT com>
#   Ported to Weechat 0.3.0 by: Sharn - <sharntehnub AT gmail DOT com)
# And from: notifo_notify
#   Author: SAEKI Yoshiyasu <laclef_yoshiyasu@yahoo.co.jp>
#   Homepage: http://bitbucket.org/laclefyoshi/weechat/
# This plugin send push notifications to your iPhone or Android smartphone
# by using Notifo.com mobile application/services
# Requires Weechat 0.3.0
# Released under GNU GPL v2
#
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#     version 0.2: change hook_print callback argument type of
#                  displayed/highlight (WeeChat >= 1.0)
#
# 2011-08-27, ochameau <poirot.alex@gmail.com>:
#     version 0.1: merge notify.py and notifo_notify.py in order to avoid
#                  sending notifications when channel or private buffer is
#                  already opened

import weechat, string, urllib, urllib2

weechat.register("notifo", "ochameau", "0.2", "GPL", "notifo: Send push notifications to your iPhone/Android about your private messages and highlights.", "", "")

credentials = {
    "username": "",
    "api_secret": ""
}

for option, default_value in credentials.items():
    if weechat.config_get_plugin(option) == "":
        weechat.prnt("", weechat.prefix("error") + "notifo: Please set option: %s" % option)
        weechat.prnt("", "notifo: /set plugins.var.python.notifo.%s STRING" % option)

# Hook privmsg/hilights
weechat.hook_print("", "irc_privmsg", "", 1, "notify_show", "")

# Functions
def notify_show(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    if (bufferp == weechat.current_buffer()):
        pass

    elif weechat.buffer_get_string(bufferp, "localvar_type") == "private":
        show_notification(prefix, message)

    elif int(ishilight):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        show_notification(buffer, prefix + ": " + message)

    return weechat.WEECHAT_RC_OK

def show_notification(chan, message):
    NOTIFO_USER = weechat.config_get_plugin("username")
    NOTIFO_API_SECRET = weechat.config_get_plugin("api_secret")
    if NOTIFO_USER != "" and NOTIFO_API_SECRET != "":
        url = "https://api.notifo.com/v1/send_notification"
        opt_dict = {
            "msg": message,
            "label": "weechat",
            "title": chan
            }
        opt = urllib.urlencode(opt_dict)
        basic = "Basic %s" % ":".join([NOTIFO_USER, NOTIFO_API_SECRET]).encode("base64").strip()
        python2_bin = weechat.info_get("python2_bin", "") or "python"
        weechat.hook_process(
            python2_bin + " -c \"import urllib2\n"
            "req = urllib2.Request('" + url + "', '" + opt + "')\n"
            "req.add_header('Authorization', '" + basic + "')\n"
            "res = urllib2.urlopen(req)\n\"",
            30 * 1000, "", "")

# vim: autoindent expandtab smarttab shiftwidth=4
