# Copyright (C) 2010  Kevin Morris <kevr@exdevelopment.net>
# lnotify made to use for libnotify notifications
# This script was adapted from 'notify'
# Hope you guys like it :O
#
# 0.1.2
# added option to display weechat's icon by tomboy64
#
# 0.1.3
# changed the way that icon to WeeChat notification is specified.
# (No absolute path is needed)
# /usr/bin/notify-send isn't needed anymore.
# (pynotify is handling notifications now)
# changed the way that lnotify works. When using gnome 3, every new
# notification was creating a new notification instance. The way that
# it is now, all WeeChat notifications are in a group (that have the
# WeeChat icon and have WeeChat name).
# Got report that it has better look for KDE users too.

import weechat, string, pynotify

weechat.register("lnotify", "kevr", "0.1.3", "GPL3", "lnotify - A libnotify script for weechat", "", "")

# Set up here, go no further!
settings = {
    "show_highlight"     : "on",
    "show_priv_msg"      : "on",
    "show_icon"          : "weechat"
}

# Init everything
if not pynotify.init("WeeChat"):
    print "Failed to load lnotify"

for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

# Hook privmsg/hilights
weechat.hook_print("", "irc_privmsg", "", 1, "get_notified", "")

# Functions
def get_notified(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    if (weechat.buffer_get_string(bufferp, "localvar_type") == "private" and
            weechat.config_get_plugin('show_priv_msg') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        if buffer == prefix:
            n = pynotify.Notification("WeeChat", "%s said: %s" % (prefix,
                message),weechat.config_get_plugin('show_icon'))
            if not n.show():
                print "Failed to send notification"

    elif (ishilight == "1" and
            weechat.config_get_plugin('show_highlight') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        n = pynotify.Notification("WeeChat", "In %s, %s said: %s" % (buffer,
            prefix, message),weechat.config_get_plugin('show_icon'))
        if not n.show():
            print "Failed to send notification"

    return weechat.WEECHAT_RC_OK
