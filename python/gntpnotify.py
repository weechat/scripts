# -*- coding: utf-8 -*-
# Author: Ryan Feng <odayfans at gmail dot com>
# License: GPL3
# Version: 0.2
# Changelog
# 0.2:
# * Fewer error messages

import gntp.notifier as notifier
import weechat
import time

# Logging
def log(msg):
    weechat.prnt("",msg)

# Register plugin
weechat.register("gntpnotify",
             "Ryan Feng",
             "0.2",
             "GPL3",
             "GNTP Notify: Growl notifications using python-gntp",
             "",
             "")

# Create hooks
weechat.hook_signal("*,irc_in2_PRIVMSG","private_msg","")
weechat.hook_signal("weechat_highlight","hilight_msg","")

growl = None
grow_loaded = False
last_log_time = None
log_period = 10 # Redisplay error log in 10s
error_log_max = 3  # Only show no more than 3 error messages in 10s
error_logged = 0

def connect():
    global growl, grow_loaded, log_period, error_log_max, last_log_time, error_logged
    # Create grow object
    growl = notifier.GrowlNotifier(
        applicationName = "Weechat",
        notifications = ["irc message"],
        defaultNotifications = ["irc message"],
        )
    try:
        grow_loaded = growl.register()
    except:
        grow_loaded = False
        if last_log_time is None:
            last_log_time = time.time()
        elapsed_time = time.time() - last_log_time
        if elapsed_time >= log_period:
            error_logged = 0

        if error_logged < error_log_max:
            log("Cannot create notifier object, please make sure Growl has started")
            error_logged += 1
            last_log_time = time.time()

    return grow_loaded

def show_notification(title, message):
    if not grow_loaded:
        connect()
        return
    r = growl.notify(
            noteType = "irc message",
            title = title,
            description = message,
            sticky = False,
            priority = 1
            )
    if not r:
        log("Cannot send notification")

def private_msg(data, signal, message):
    # message is a raw irc message sent from the server
    message = message[1:]

    # Get sender
    sender = message[:message.find('!')-1]

    # Get receiver
    receiver = message.split()[2]

    # Get message body
    msg = message[message.find(':')+1:]

    # Get the server which sent this message
    server = signal.partition(',')[0]

    # Ignore all PRIVMSGs send to a channel,the rest are messages send to 'me'
    if not receiver.startswith('#'):
        show_notification("%s @ #%s" % (sender,server),msg)

    return weechat.WEECHAT_RC_OK

def hilight_msg(data, signal, message):
    # TODO: Get the sender of the message and the channel where the highlight displayed
    sender,_,tmp_msg = message.partition('\t')

    _,_,msg = tmp_msg.partition(' ')

    if grow_loaded:
        show_notification("%s" % sender, msg)
    else:
        connect()
    return weechat.WEECHAT_RC_OK

