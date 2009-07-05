#!/usr/bin/env python
#
# Author: Stefano Zamprogno <mie.iscrizioni@gmail.com>
# Licence: GPL3
#
# This plugin need:
# python (tested only with v2.6.x)
# python-twitter (tested only with v0.6)
# weechat (tested only with v0.2.6.3)
# on Archlinux distro simply:
# yaourt -S python-twitter
#
# Put wetwit.py on ~/.weechat/python/autoload/
# set below user and pwd
#
# HELP on Usage
# /twit twits [N]
#       request latest [N] messages or latest 5 if N not specified
# /twit sendmsg text2send
#       send 'text2send' to twitter

import weechat
import twitter

weechat.register("wetwit.py", "0.1.0", "",
                            "WeTwit v.0.1.0")


# To be SET by you, VERIFY 3 TIMES !!! :)
user = "john"
pwd = "doe"

# -----------------------------------------------------------
# Do not modify below this line------------------------------
# -----------------------------------------------------------

api = twitter.Api(user, pwd)

def hook_commands_cb(server, args):
    cmd = args.split()
    if len(cmd) > 1:
        cmd,txt = args.split(" ", 1)
        cmd = cmd.lower()
        if cmd == "sendmsg":
            weechat.prnt("Working...")
            if len(txt) <= 140:
                status = api.PostUpdate(txt.decode("utf-8"))
                weechat.prnt("-"*30)
                weechat.prnt(status.text.encode("utf-8"))
                weechat.prnt("-"*30)
                weechat.prnt("*** TWITTED ***")
            else:
                statuses = api.PostUpdates(txt.decode("utf-8"),
                                        continuation="...")
                for s in statuses:
                    weechat.prnt("-"*30)
                    weechat.prnt(s.text.encode('utf-8'))
                    weechat.prnt("-"*30)
                    weechat.prnt("*** TWITTED ***")
        if cmd == "twits":
            weechat.prnt("Working...")
            statuses = api.GetFriendsTimeline(count=str(txt))
            for s in statuses:
                weechat.prnt("Data: %s" % s.created_at)
                weechat.prnt("ID: %s, User: %s" % (s.id, s.user.name))
                weechat.prnt("Text: %s" % (s.text.encode('utf-8')))
                weechat.prnt("---")
    elif len(cmd) == 1:
        if cmd[0].lower() == "twits":
            weechat.prnt("Working...")
            statuses = api.GetFriendsTimeline(count=5)
            for s in statuses:
                weechat.prnt("Data: %s" % s.created_at)
                weechat.prnt("ID: %s, User: %s" % (s.id, s.user.name))
                weechat.prnt("Text: %s" % (s.text.encode('utf-8')))
                weechat.prnt("---")

    return weechat.PLUGIN_RC_OK

weechat.add_command_handler("twit", "hook_commands_cb",
                        "Send/Receive twitter messages",
                        "")


weechat.prnt("Plugin WeTwit loaded!")
