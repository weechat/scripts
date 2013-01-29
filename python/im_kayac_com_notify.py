# -*- coding: utf-8 -*-
"""
Author: Gosuke Miyashita <gosukenator@gmail.com>
Homepage: https://github.com/mizzy/weechat-plugins/
Version: 1.1
License: MIT License

This plugin is for pushing notifications to im.kayac.com.
See: http://im.kayac.com/

This plugin is based on notifo_notify.py.
See: http://www.weechat.org/scripts/source/stable/notifo_notify.py/

Original license is:

Author: SAEKI Yoshiyasu <laclef_yoshiyasu@yahoo.co.jp>
Homepage: http://bitbucket.org/laclefyoshi/weechat/
Version: 1.0
License: MIT License

This plugin requires "notifo" in your iPod touch/iPhone
See here: http://notifo.com/
"""

import weechat
import urllib
import hashlib

## registration

weechat.register("im_kayac_com_notify", "Gosuke Miyashita", "1.1", "MIT License",
    "im_kayac_com_notify: Push notification to iPod touch/iPhone with im.kayac.com", "", "")

## settings

script_options = {
    "username":  "",
    "password":  "",
    "secretkey": "",
}

if weechat.config_get_plugin("username") == "":
    weechat.prnt("", weechat.prefix("error") + "im_kayac_com_notify: Please set option: username")
    weechat.prnt("", "im_kayac_com_notify: /set plugins.var.python.im_kayac_com_notify.username STRING")

if weechat.config_get_plugin("password") == "" and weechat.config_get_plugin("secretkey") == "":
    weechat.prnt("", weechat.prefix("error") + "im_kayac_com_notify: Please set option: password or secretkey")
    weechat.prnt("", "im_kayac_com_notify: /set plugins.var.python.im_kayac_com_notify.[password|secretkey] STRING")

## functions

def postIm(message, handler=None, label=None, title=None):
    USERNAME  = weechat.config_get_plugin("username")
    PASSWORD  = weechat.config_get_plugin("password")
    SECRETKEY = weechat.config_get_plugin("secretkey")

    if USERNAME != "":
        url = "http://im.kayac.com/api/post/" + USERNAME
        opt_dict = {
            "message": "[%s] - %s\n%s" % (label, title, message),
            }

        if PASSWORD != "":
            opt_dict["password"] = PASSWORD
        elif SECRETKEY != "":
            opt_dict["sig"] = hashlib.sha1(opt_dict["message"] + SECRETKEY).hexdigest()
        else:
            return

        opt = urllib.urlencode(opt_dict)
        cmd = "python -c 'from urllib2 import Request, urlopen; urlopen(Request(\"%s\", \"%s\"))'" % (url, opt)
        weechat.hook_process(cmd, 10000, "hook_process_cb", "")

def hook_process_cb(data, command, rc, stdout, stderr):
    return weechat.WEECHAT_RC_OK

def signal_callback(data, signal, signal_data):
    if signal == "weechat_pv":
        postIm(signal_data, label="weechat", title="Private Message")
    elif signal == "weechat_highlight":
        postIm(signal_data, label="weechat", title="Highlight")
    return weechat.WEECHAT_RC_OK

weechat.hook_signal("weechat_highlight", "signal_callback", "")
weechat.hook_signal("weechat_pv", "signal_callback", "")

