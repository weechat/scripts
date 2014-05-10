# -*- coding: utf-8 -*-
"""
Author: Gosuke Miyashita <gosukenator@gmail.com>
Homepage: https://github.com/mizzy/weechat-plugins/
Version: 1.3
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

weechat.register("im_kayac_com_notify", "Gosuke Miyashita", "1.3", "MIT License",
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

def postIm(message, handler=None, label=None, title=None, buffer_name=None, prefix=None):
    USERNAME  = weechat.config_get_plugin("username")
    PASSWORD  = weechat.config_get_plugin("password")
    SECRETKEY = weechat.config_get_plugin("secretkey")

    if USERNAME != "":
        url = "http://im.kayac.com/api/post/" + USERNAME
        opt_dict = {
            "message": "[%s][%s] - %s\n%s %s" % (label, buffer_name, title, prefix, message),
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

def print_callback(data, buffer, date, tags, displayed, highlight, prefix, message):
    buffer_name = weechat.buffer_get_string(buffer, "name")
    if int(highlight):
        postIm(message, label="weechat", title="Highlight", buffer_name=buffer_name, prefix=prefix)
    elif "notify_private" in tags.split(','):
        postIm(message, label="weechat", title="Private Message", buffer_name=buffer_name, prefix=prefix)
    return weechat.WEECHAT_RC_OK

weechat.hook_print("", "", "", 1, "print_callback", "");

