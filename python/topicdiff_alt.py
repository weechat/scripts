import weechat
import diff_match_patch
import re

weechat.register('topicdiff_alt', 'Juerd <#####@juerd.nl>', '1.01', 'PD', "Announce topic with changes highlighted", '', '')

def topic(data, tags, msg):
    server = tags.split(",")[0]

    match = re.search(r':(\S+)\s+TOPIC\s+(\S+)\s+:(.*)', msg)

    if not match:
        return weechat.WEECHAT_RC_ERROR

    usermask, channel, newtopic = match.groups()
    nick, host = usermask.split("!", 1)

    buffer = weechat.buffer_search("irc", server + "." + channel)
    weechat.prnt("", server + "." + channel)

    if not buffer:
        return weechat.WEECHAT_RC_ERROR

    oldtopic = weechat.buffer_get_string(buffer, "title")
    if oldtopic == None:
        oldtopic = ""

    dmp = diff_match_patch.diff_match_patch()
    diff = dmp.diff_main(oldtopic, newtopic)
    dmp.diff_cleanupEfficiency(diff)

    topic = ""

    color_reset = weechat.color("reset")
    color_ins = weechat.color(weechat.config_get_plugin("color_ins"))
    color_del = weechat.color(weechat.config_get_plugin("color_del"))

    for chunk in diff:
        changed, text = chunk

        topic += "%s%s%s" % (
            # 0 (unchanged), 1 (added), -1 (removed)
            ["", color_ins, color_del][changed],
            text,
            ["", color_reset, color_reset][changed]
        )

    weechat.prnt_date_tags(buffer, 0, "irc_topicdiff",
        "%s%s%s%s has changed topic for %s%s%s: %s" % (
        weechat.prefix("network"),
        weechat.color(weechat.info_get("irc_nick_color", nick)) \
            if weechat.config_boolean("irc.look.color_nicks_in_server_messages") \
            else weechat.color("chat_nick"),
        nick,
        color_reset,
        weechat.color("chat_channel"),
        channel,
        color_reset,
        topic
    ))

    return weechat.WEECHAT_RC_OK

weechat.hook_signal("*,irc_in_topic", "topic", "")

if not weechat.config_is_set_plugin("color_ins"):
    weechat.config_set_plugin("color_ins", "lightcyan")

if not weechat.config_is_set_plugin("color_del"):
    weechat.config_set_plugin("color_del", "darkgray")
