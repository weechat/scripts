# Author: tobypadilla <tobypadilla AT gmail DOT com>
# gnotify requires Growl Python Bindings
# See here: http://growl.info/documentation/developer/python-support.php
# Requires Weechat 0.3.0
# Released under GNU GPL v2
#
# Copy weechaticn.png to /usr/local/share/pixmaps/ or change the path below
#
# gnotify is derived from notify http://www.weechat.org/files/scripts/notify.py
# Original author: lavaramano <lavaramano AT gmail DOT com>
# Improved by: BaSh - <bash.lnx AT gmail DOT com>
# Ported to Weechat 0.3.0 by: Sharn - <sharntehnub AT gmail DOT com)
#
# 2009-06-16, kba <unixprog@gmail.com.org>:
#     version 0.0.3: added config options for icon and urgency
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.0.2.1: sync with last API changes

import weechat, Growl, string

weechat.register("gnotify", "tobypadilla", "0.1", "GPL", "gnotify: Growl notifications for Weechat", "", "")

# script options
settings = {
    "show_hilights"             : "on",
    "show_priv_msg"             : "on",
    "sticky"                    : "on",
    "icon"                      : "/usr/local/share/pixmaps/weechaticn.png",
}

# Setup Growl Notification Class
class gNotifier(Growl.GrowlNotifier):
   applicationName = 'gnotify'
   notifications = ['highlight']
   # don't have/want the weechat icon? use ichat instead
   # applicationIcon = Growl.Image.imageWithIconForApplication("iChat")
   applicationIcon = Growl.Image.imageFromPath(weechat.config_get_plugin('icon'))

# Init everything
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

# Hook privmsg/hilights
weechat.hook_signal("weechat_pv", "notify_show_priv", "")
weechat.hook_signal("weechat_highlight", "notify_show_hi", "")

# Functions
def notify_show_hi( data, signal, message ):
    """Sends highlight message to be printed on notification"""
    if weechat.config_get_plugin('show_hilights') == "on":
        show_notification("Weechat",  message)
    return weechat.WEECHAT_RC_OK

def notify_show_priv( data, signal, message ):
    """Sends private message to be printed on notification"""
    if weechat.config_get_plugin('show_priv_msg') == "on":
        show_notification("Weechat Private Message",  message)
    return weechat.WEECHAT_RC_OK

def show_notification(title,message):
    isSticky = False
    if weechat.config_get_plugin('sticky') == "on":
        isSticky = True

    growl = gNotifier()
    growl.register()

    growl.notify('highlight', title, message, "", isSticky)

