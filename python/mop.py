"""
    mop.py

    author: Adam Saponara <saponara AT gmail DOT com>
      desc: Op everyone in the current channel
     usage: /mop
   license: GPLv3

   history:
       0.1 - 2016-02-23, initial script
"""

import weechat

weechat.register("mop", "Adam Saponara", "0.1", "GPL3", "Op everyone in the current channel", "", "")

def mop_cmd(data, buffer, args):
    nicks = []
    nicklist = weechat.infolist_get("nicklist", buffer, "")
    while weechat.infolist_next(nicklist):
        nick = weechat.infolist_string(nicklist, "name")
        nick_type = weechat.infolist_string(nicklist, "type")
        nick_prefix = weechat.infolist_string(nicklist, "prefix")
        if nick_type == "nick" and nick_prefix != "@":
            nicks.append(nick)
    weechat.infolist_free(nicklist)
    if len(nicks) > 0:
        weechat.command(buffer, "/op " + " ".join(nicks))
    return weechat.WEECHAT_RC_OK

hook = weechat.hook_command("mop", "Op everyone in the current channel", "", "", "", "mop_cmd", "")
