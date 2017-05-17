# -*- coding: utf-8 -*-
# Author: Caspar Clemens Mierau <ccm@screenage.de>
# Homepage: https://github.com/leitmedium/weechat-irssinotifier
# Derived from: notifo
#   Author: ochameau <poirot.alex AT gmail DOT com>
#   Homepage: https://github.com/ochameau/weechat-notifo
# And from: notify
#   Author: lavaramano <lavaramano AT gmail DOT com>
#   Improved by: BaSh - <bash.lnx AT gmail DOT com>
#   Ported to Weechat 0.3.0 by: Sharn - <sharntehnub AT gmail DOT com)
# And from: notifo_notify
#   Author: SAEKI Yoshiyasu <laclef_yoshiyasu@yahoo.co.jp>
#   Homepage: http://bitbucket.org/laclefyoshi/weechat/
#
# This plugin brings IrssiNotifier to your Weechat. Setup and install
# IrssiNotifier first: https://irssinotifier.appspot.com
#
# Requires Weechat >= 0.3.7, openssl
# Released under GNU GPL v3
#
# 2017-05-17, das_aug <wct@fnanp.in-ulm.de>
#     version 0.8.1 - change openssl commandline to how the android app uses it now
#                     (add "-md md5")
# 2017-05-11, paalka <paal@128.no>
#     version 0.8: - add the ability to store the API token and
#                    encryption key as secured data.
# 2016-01-11, dbendit <david@ibendit.com>
#     version 0.7: - ignore_nicks option
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#     version 0.6.3: - change hook_print callback argument type of
#                      displayed/highlight (WeeChat >= 1.0)
# 2013-12-07, zigdon
#     version 0.6.2: - support ignoring all buffers in a server, add help text.
# 2013-08-20, balu
#     version 0.6.1: - support for every private notification not only irc (especialy also jabber)
# 2013-08-16, kang@insecure.ws
#     version 0.6: - only_away option (only notify if set away)
# 2013-01-18, ccm <ccm@screenage.de>:
#     version 0.5: - removed version check and legacy curl usage
# 2012-12-27, ccm <ccm@screenage.de>:
#     version 0.4: - use non-blocking hook_process_hashtable for url call
#                    for weechat >= 0.3.7
# 2012-12-22, ccm <ccm@screenage.de>:
#     version 0.3: - no longer notifies if the message comes from the user
#                    itself
#                  - removed curl dependency
#                  - cleaned up openssl call
#                  - no more crashes due to missing escaping
#                  - Kudos to Juergen "@tante" Geuter <tante@the-gay-bar.com>
#                    for the patches!
# 2012-10-27, ccm <ccm@screenage.de>:
#     version 0.2: - curl uses secure command call (decreases risk of command
#                    injection)
#                  - correct split of nick and channel name in a hilight
# 2012-10-26, ccm <ccm@screenage.de>:
#     version 0.1: - initial release - working proof of concept

import weechat, string, os, urllib, urllib2, shlex
from subprocess import Popen, PIPE

weechat.register("irssinotifier",
                 "Caspar Clemens Mierau <ccm@screenage.de>",
                 "0.8.1",
                 "GPL3",
                 "irssinotifier: Send push notifications to Android's IrssiNotifier about your private message and highligts.",
                 "",
                 "")

settings = {
    "api_token": "API token from http://irssinotifier.appspot.com.",
    "encryption_password": "Your password, same as on the phone's client.",
    "only_away": "Only send notifications when set as away.",
    "ignore_buffers": "Comma separated list of buffers to ignore.",
    "ignore_servers": "Comma separated list of servers to ignore.",
    "ignore_nicks": "Comma separated list of nicks to ignore.",
}

required_settings = ["api_token", "encryption_password"]

for option, help_text in settings.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, "")

    if option in required_settings and weechat.config_get_plugin(option) == "":
        weechat.prnt("", weechat.prefix("error") + "irssinotifier: Please set option: %s" % option)
        weechat.prnt("", "irssinotifier: /set plugins.var.python.irssinotifier.%s STRING" % option)

    weechat.config_set_desc_plugin(option, help_text)

# Hook privmsg/hilights
weechat.hook_print("", "notify_message", "", 1, "notify_show", "")
weechat.hook_print("", "notify_private", "", 1, "notify_show", "")

# Functions
def notify_show(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    # irc PMs are caught by notify_private, but we need notify_message to
    # capture hilights in channels.
    if 'notify_message' in tagsn and not ishilight:
        return weechat.WEECHAT_RC_OK

    # are we away?
    away = weechat.buffer_get_string(bufferp,"localvar_away")
    if (away == "" and weechat.config_get_plugin("only_away") == "on"):
        return weechat.WEECHAT_RC_OK

    # get local nick for buffer
    mynick = weechat.buffer_get_string(bufferp,"localvar_nick")

    # get buffer info
    name = weechat.buffer_get_string(bufferp,"name")
    server = weechat.buffer_get_string(bufferp, "localvar_server")
    channel = weechat.buffer_get_string(bufferp, "localvar_channel")

    # ignore buffers on ignorelists
    if not (server in weechat.config_get_plugin("ignore_servers").split(",") or
        name in weechat.config_get_plugin("ignore_buffers").split(",") or
        prefix in weechat.config_get_plugin("ignore_nicks").split(",")):

        # only notify if the message was not sent by myself
        if (weechat.buffer_get_string(bufferp, "localvar_type") == "private") and (prefix!=mynick):
            show_notification(channel, prefix, message)

        elif int(ishilight):
            buffer = (weechat.buffer_get_string(bufferp, "short_name") or name)
            show_notification(buffer, prefix, message)

    return weechat.WEECHAT_RC_OK

def encrypt(text):
    encryption_password = weechat.config_get_plugin("encryption_password")

    # decrypt the password if it is stored as secured data
    if encryption_password.startswith("${sec."):
        encryption_password = weechat.string_eval_expression(encryption_password, {}, {}, {})

    command="openssl enc -aes-128-cbc -salt -base64 -md md5 -A -pass env:OpenSSLEncPW"
    opensslenv = os.environ.copy();
    opensslenv['OpenSSLEncPW'] = encryption_password
    output,errors = Popen(shlex.split(command),stdin=PIPE,stdout=PIPE,stderr=PIPE,env=opensslenv).communicate(text+" ")
    output = string.replace(output,"/","_")
    output = string.replace(output,"+","-")
    output = string.replace(output,"=","")
    return output

def show_notification(chan, nick, message):
    API_TOKEN = weechat.config_get_plugin("api_token")

    # decrypt the API token if it is stored as secured data
    if API_TOKEN.startswith("${sec."):
        API_TOKEN = weechat.string_eval_expression(API_TOKEN, {}, {}, {})

    if API_TOKEN != "":
        url = "https://irssinotifier.appspot.com/API/Message"
        postdata = urllib.urlencode({'apiToken':API_TOKEN,'nick':encrypt(nick),'channel':encrypt(chan),'message':encrypt(message),'version':13})
        version = weechat.info_get("version_number", "") or 0
        hook1 = weechat.hook_process_hashtable("url:"+url, { "postfields":  postdata}, 2000, "", "")

# vim: autoindent expandtab smarttab shiftwidth=4
