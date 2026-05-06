# SPDX-FileCopyrightText: 2026 Petteri <petteri@gmail.com>
#
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
#
# irc_react_inline.py
#
# Show IRCv3 draft/react reactions inline on the original message:
#   <petteri> hei! [😀 Enska, Spuge | 👍 mauno]
#
# Commands:
#   /react <emoji> [msgid]
#   /unreact <emoji> [msgid]
#
# Requirements:
#   - message-tags capability enabled
#   - server supports draft/react
#

import re
import time
import weechat

SCRIPT_NAME = "irc_react_inline"
SCRIPT_AUTHOR = "Petteri"
SCRIPT_VERSION = "0.3.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Inline IRCv3 draft/react reactions with commands"

TAG_MSGID = "msgid"
TAG_REPLY = "+draft/reply"
TAG_REACT = "+draft/react"
TAG_UNREACT = "+draft/unreact"

DEFAULTS = {
    "suffix_color": "darkgray",
    "max_scan_lines": "80",
    "debug": "off",
}

messages = {}
reactions = {}
latest_msgid = {}
pending = []


IRC_FORMAT_RE = re.compile(
    r"\x03(?:\d{1,2}(?:,\d{1,2})?)?|"
    r"\x04(?:[0-9A-Fa-f]{6}(?:,[0-9A-Fa-f]{6})?)?|"
    r"[\x02\x0f\x11\x16\x1d\x1e\x1f]"
)


def dbg(msg):
    if weechat.config_get_plugin("debug").lower() in ("1", "on", "true", "yes"):
        weechat.prnt("", "{}: {}".format(SCRIPT_NAME, msg))


def ensure_config():
    for key, value in DEFAULTS.items():
        if not weechat.config_is_set_plugin(key):
            weechat.config_set_plugin(key, value)


def color(name):
    return weechat.color(name) if name else ""


def strip_colors(text):
    return weechat.string_remove_color(text or "", "")


def normalize_text(text):
    return IRC_FORMAT_RE.sub("", strip_colors(text)).strip()


def get_server(signal):
    return signal.split(",", 1)[0]


def get_tag(msg, tag_name):
    value = msg.get("tag_" + tag_name, "")
    if value or not tag_name.startswith("+"):
        return value
    return msg.get("tag_" + tag_name[1:], "")


def has_tag(msg, tag_name):
    if ("tag_" + tag_name) in msg:
        return True
    if tag_name.startswith("+") and ("tag_" + tag_name[1:]) in msg:
        return True
    return False


def own_nick(server):
    return weechat.info_get("irc_nick", server) or ""


def get_target(msg, server):
    target = msg.get("channel", "") or msg.get("param1", "") or ""
    nick = msg.get("nick", "") or ""
    me = own_nick(server)

    if target and me and target.lower() == me.lower():
        return nick
    return target or nick


def get_buffer_ptr(server, target):
    return weechat.info_get("irc_buffer", "{},{}".format(server, target)) or ""


def server_cap_list(server):
    value = weechat.info_get("irc_server_isupport_value", "{},CAP".format(server)) or ""
    if value:
        return {cap.strip().lower() for cap in value.split() if cap.strip()}

    value = weechat.info_get("irc_server_cap_value", "{},cap".format(server)) or ""
    if value:
        return {cap.strip().lower() for cap in value.split() if cap.strip()}

    value = weechat.info_get("irc_server_cap", server) or ""
    return {cap.strip().lower() for cap in value.split() if cap.strip()}


def warn_missing_caps(server):
    caps = server_cap_list(server)
    dbg("capabilities for {}: {}".format(server, ", ".join(sorted(caps)) or "<none>"))
    if not caps:
        return

    missing = [cap for cap in ("echo-message", "message-tags") if cap not in caps]
    if missing:
        weechat.prnt(
            "",
            "{}: server {} missing recommended capabilities: {}".format(
                SCRIPT_NAME, server, ", ".join(missing)
            ),
        )


def warn_missing_caps_cb(data, remaining_calls):
    server = data
    if server:
        warn_missing_caps(server)
    return weechat.WEECHAT_RC_OK


def is_regular_message(msg):
    if (msg.get("command", "") or "").upper() != "PRIVMSG":
        return False
    if has_tag(msg, TAG_REACT) or has_tag(msg, TAG_UNREACT):
        return False
    return True


def render_suffix(server, target, msgid):
    data = reactions.get((server, target, msgid), {})
    if not data:
        return ""

    parts = []
    for emoji in sorted(data.keys()):
        nicks = sorted(data[emoji], key=str.lower)
        if len(nicks) > 3:
            parts.append("{} +{}".format(emoji, len(nicks)))
        else:
            parts.append("{} {}".format(emoji, ", ".join(nicks)))

    suffix = " [{}]".format(" | ".join(parts))
    return color(weechat.config_get_plugin("suffix_color")) + suffix + color("reset")


def update_line(server, target, msgid):
    info = messages.get((server, target, msgid))
    if not info or not info.get("line_data"):
        return

    new_message = info["base_message"] + render_suffix(server, target, msgid)
    weechat.hdata_update(
        weechat.hdata_get("line_data"),
        info["line_data"],
        {"message": new_message},
    )


def store_message(msg, server):
    msgid = get_tag(msg, TAG_MSGID)
    if not msgid:
        return

    target = get_target(msg, server)
    buffer_ptr = get_buffer_ptr(server, target)
    if not buffer_ptr:
        return

    key = (server, target, msgid)
    dbg("store message {} from {} to {}".format(msgid, msg.get("nick", ""), target))
    messages[key] = {
        "nick": msg.get("nick", ""),
        "text": msg.get("text", "") or msg.get("param2", ""),
        "buffer": buffer_ptr,
        "line_data": "",
        "base_message": "",
        "ts": time.time(),
        "resolved": False,
    }

    latest_msgid[(server, target)] = msgid
    pending.append(key)


def update_reaction(server, target, msgid, emoji, nick, remove=False):
    key = (server, target, msgid)
    per_msg = reactions.setdefault(key, {})
    users = per_msg.setdefault(emoji, set())

    if remove:
        users.discard(nick)
        if not users:
            per_msg.pop(emoji, None)
    else:
        users.add(nick)

    if not per_msg:
        reactions.pop(key, None)


def get_line_tags(h_line_data, line_data):
    tags = []
    count = weechat.hdata_integer(h_line_data, line_data, "tags_count")
    for i in range(count):
        tags.append(weechat.hdata_string(h_line_data, line_data, "{}|tags_array".format(i)) or "")
    return tags


def tag_matches_msgid(tag, msgid):
    if not tag or not msgid:
        return False
    return (
        tag == msgid
        or tag.endswith("_" + msgid)
        or tag.endswith("=" + msgid)
        or ("msgid" in tag and msgid in tag)
    )


def find_line_by_msgid(buffer_ptr, msgid):
    h_buffer = weechat.hdata_get("buffer")
    h_lines = weechat.hdata_get("lines")
    h_line = weechat.hdata_get("line")
    h_line_data = weechat.hdata_get("line_data")

    lines = weechat.hdata_pointer(h_buffer, buffer_ptr, "own_lines")
    line = weechat.hdata_pointer(h_lines, lines, "last_line")

    for _ in range(int(weechat.config_get_plugin("max_scan_lines"))):
        if not line:
            break
        data = weechat.hdata_pointer(h_line, line, "data")
        if data:
            tags = get_line_tags(h_line_data, data)
            for tag in tags:
                if tag_matches_msgid(tag, msgid):
                    dbg("resolved line by msgid {}".format(msgid))
                    return data, weechat.hdata_string(h_line_data, data, "message")
        line = weechat.hdata_pointer(h_line, line, "prev_line")

    dbg("could not resolve line by msgid {}".format(msgid))
    return "", ""


def find_line(buffer_ptr, nick, text, msgid=None):
    h_buffer = weechat.hdata_get("buffer")
    h_lines = weechat.hdata_get("lines")
    h_line = weechat.hdata_get("line")
    h_line_data = weechat.hdata_get("line_data")

    lines = weechat.hdata_pointer(h_buffer, buffer_ptr, "own_lines")
    line = weechat.hdata_pointer(h_lines, lines, "last_line")

    want_text = normalize_text(text)
    want_nick = nick.lower()
    text_only = ("", "")

    for _ in range(int(weechat.config_get_plugin("max_scan_lines"))):
        if not line:
            break
        data = weechat.hdata_pointer(h_line, line, "data")
        if data:
            prefix = strip_colors(weechat.hdata_string(h_line_data, data, "prefix"))
            msg = weechat.hdata_string(h_line_data, data, "message")
            if normalize_text(msg) == want_text:
                if want_nick and want_nick in prefix.lower():
                    dbg("resolved line by text for nick {}".format(nick))
                    return data, msg
                if not text_only[0]:
                    text_only = (data, msg)
        line = weechat.hdata_pointer(h_line, line, "prev_line")

    if text_only[0]:
        dbg("resolved line by text-only fallback for nick {}".format(nick))
    else:
        dbg("could not resolve line by text for nick {}".format(nick))
    return text_only


def resolve_pending_cb(data, remaining_calls):
    new_pending = []

    for key in pending:
        info = messages.get(key)
        if not info or info["resolved"]:
            continue

        data, base = find_line(info["buffer"], info["nick"], info["text"], key[2])
        if data:
            dbg("pending resolved for msgid {}".format(key[2]))
            info["line_data"] = data
            info["base_message"] = base
            info["resolved"] = True
            update_line(*key)
        elif time.time() - info["ts"] < 10:
            new_pending.append(key)
        else:
            dbg("pending expired for msgid {}".format(key[2]))

    pending[:] = new_pending
    return weechat.WEECHAT_RC_OK


def handle_reaction(server, msg):
    target = get_target(msg, server)
    msgid = get_tag(msg, TAG_REPLY)
    nick = msg.get("nick", "")

    dbg("reaction event from {} target={} reply={} react={} unreact={}".format(
        nick, target, msgid, get_tag(msg, TAG_REACT), get_tag(msg, TAG_UNREACT)
    ))
    if not msgid:
        dbg("ignoring reaction event without reply msgid")
        return

    key = (server, target, msgid)
    if key not in messages:
        buffer_ptr = get_buffer_ptr(server, target)
        if buffer_ptr:
            line_data, base_message = find_line_by_msgid(buffer_ptr, msgid)
            if line_data:
                dbg("created message cache entry from reaction for {}".format(msgid))
                messages[key] = {
                    "nick": "",
                    "text": normalize_text(base_message),
                    "buffer": buffer_ptr,
                    "line_data": line_data,
                    "base_message": base_message,
                    "ts": time.time(),
                    "resolved": True,
                }

    if has_tag(msg, TAG_REACT):
        emoji = get_tag(msg, TAG_REACT)
        dbg("apply react {} by {} to {}".format(emoji, nick, msgid))
        update_reaction(server, target, msgid, emoji, nick)
        update_line(server, target, msgid)

    if has_tag(msg, TAG_UNREACT):
        emoji = get_tag(msg, TAG_UNREACT)
        dbg("apply unreact {} by {} to {}".format(emoji, nick, msgid))
        update_reaction(server, target, msgid, emoji, nick, True)
        update_line(server, target, msgid)


def privmsg_cb(data, signal, signal_data):
    server = get_server(signal)
    msg = weechat.info_get_hashtable("irc_message_parse", {"message": signal_data})

    if not msg:
        return weechat.WEECHAT_RC_OK

    if is_regular_message(msg):
        store_message(msg, server)

    handle_reaction(server, msg)
    return weechat.WEECHAT_RC_OK


def tagmsg_cb(data, signal, signal_data):
    server = get_server(signal)
    msg = weechat.info_get_hashtable("irc_message_parse", {"message": signal_data})
    if msg:
        handle_reaction(server, msg)
    return weechat.WEECHAT_RC_OK


def current_server_target(buffer_ptr):
    return (
        weechat.buffer_get_string(buffer_ptr, "localvar_server"),
        weechat.buffer_get_string(buffer_ptr, "localvar_channel"),
    )


def send_react(buffer_ptr, emoji, msgid=None, remove=False):
    server, target = current_server_target(buffer_ptr)

    if not msgid:
        msgid = latest_msgid.get((server, target))

    if not msgid:
        dbg("send_react: no msgid available for {} {}".format(server, target))
        weechat.prnt(buffer_ptr, "No msgid available")
        return weechat.WEECHAT_RC_ERROR

    nick = own_nick(server)
    if nick:
        update_reaction(server, target, msgid, emoji, nick, remove)
        update_line(server, target, msgid)

    tag = TAG_UNREACT if remove else TAG_REACT
    cmd = "@{}={};{}={} TAGMSG {}".format(tag, emoji, TAG_REPLY, msgid, target)
    dbg("send {} {} to {} reply {}".format("unreact" if remove else "react", emoji, target, msgid))
    weechat.command(buffer_ptr, "/quote -server {} {}".format(server, cmd))
    return weechat.WEECHAT_RC_OK


def react_cmd(data, buffer_ptr, args):
    parts = args.split()
    if not parts:
        weechat.prnt(buffer_ptr, "Usage: /react <emoji> [msgid]")
        return weechat.WEECHAT_RC_OK

    emoji = parts[0]
    msgid = parts[1] if len(parts) > 1 else None
    return send_react(buffer_ptr, emoji, msgid)


def unreact_cmd(data, buffer_ptr, args):
    parts = args.split()
    if not parts:
        weechat.prnt(buffer_ptr, "Usage: /unreact <emoji> [msgid]")
        return weechat.WEECHAT_RC_OK

    emoji = parts[0]
    msgid = parts[1] if len(parts) > 1 else None
    return send_react(buffer_ptr, emoji, msgid, True)


if __name__ == "__main__":
    if weechat.register(
        SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
        SCRIPT_LICENSE, SCRIPT_DESC, "", ""
    ):
        ensure_config()
        server = weechat.buffer_get_string(weechat.current_buffer(), "localvar_server")
        if server:
            weechat.hook_timer(1, 0, 1, "warn_missing_caps_cb", server)
        weechat.hook_signal("*,irc_in2_privmsg", "privmsg_cb", "")
        weechat.hook_signal("*,irc_in2_tagmsg", "tagmsg_cb", "")
        weechat.hook_timer(250, 0, 0, "resolve_pending_cb", "")

        weechat.hook_command(
            "react", "Send emoji reaction",
            "<emoji> [msgid]", "", "", "react_cmd", ""
        )
        weechat.hook_command(
            "unreact", "Remove emoji reaction",
            "<emoji> [msgid]", "", "", "unreact_cmd", ""
        )
