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

weechat.register("irssinotifier", "Caspar Clemens Mierau <ccm@screenage.de>", "0.5", "GPL3", "irssinotifier: Send push notifications to Android's IrssiNotifier about your private message and highligts.", "", "")

settings = {
    "api_token": "",
    "encryption_password": ""
}

for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.prnt("", weechat.prefix("error") + "irssinotifier: Please set option: %s" % option)
        weechat.prnt("", "irssinotifier: /set plugins.var.python.irssinotifier.%s STRING" % option)

# Hook privmsg/hilights
weechat.hook_print("", "irc_privmsg", "", 1, "notify_show", "")

# Functions
def notify_show(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    #get local nick for buffer
    mynick = weechat.buffer_get_string(bufferp,"localvar_nick")

    # only notify if the message was not sent by myself
    if (weechat.buffer_get_string(bufferp, "localvar_type") == "private") and (prefix!=mynick):
            show_notification(prefix, prefix, message)

    elif ishilight == "1":
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        show_notification(buffer, prefix, message)

    return weechat.WEECHAT_RC_OK

def encrypt(text):
    encryption_password = weechat.config_get_plugin("encryption_password")
    command="openssl enc -aes-128-cbc -salt -base64 -A -pass pass:%s" % (encryption_password)
    output,errors = Popen(shlex.split(command),stdin=PIPE,stdout=PIPE,stderr=PIPE).communicate(text+" ")
    output = string.replace(output,"/","_")
    output = string.replace(output,"+","-")
    output = string.replace(output,"=","")
    return output

def show_notification(chan, nick, message):
    API_TOKEN = weechat.config_get_plugin("api_token")
    if API_TOKEN != "":
        url = "https://irssinotifier.appspot.com/API/Message"
        postdata = urllib.urlencode({'apiToken':API_TOKEN,'nick':encrypt(nick),'channel':encrypt(chan),'message':encrypt(message),'version':13})
        version = weechat.info_get("version_number", "") or 0
        hook1 = weechat.hook_process_hashtable("url:"+url, { "postfields":  postdata}, 2000, "", "")

# vim: autoindent expandtab smarttab shiftwidth=4
