# Copyright (c) 2022 Simon Ser <contact@emersion.fr>
#
# License: GNU Affero General Public License version 3
# https://www.gnu.org/licenses/agpl-3.0.en.html
#
# This script adds support for the draft/read-marker IRC extension, defined in
# https://ircv3.net/specs/extensions/read-marker
#
# The extension synchronizes the read marker between multiple clients. If a
# user is connected on two devices (e.g. a laptop and a phone), reading a
# message on a device will also mark it as read on the other device.

import weechat
import datetime

weechat.register("read_marker", "emersion", "0.2.0", "AGPL3", "draft/read-marker extension support", "", "")

READ_MARKER_CAP = "draft/read-marker"

weechat_version = int(weechat.info_get("version_number", "") or 0)

if weechat_version < 0x04000000:
    caps_option = weechat.config_get("irc.server_default.capabilities")
    caps = weechat.config_string(caps_option)
    if READ_MARKER_CAP not in caps:
        if caps != "":
            caps += ","
        caps += READ_MARKER_CAP
        weechat.config_option_set(caps_option, caps, 1)

read_times = {}

def server_by_name(server_name):
    hdata = weechat.hdata_get("irc_server")
    server_list = weechat.hdata_get_list(hdata, "irc_servers")
    if weechat_version >= 0x03040000:
        return weechat.hdata_search(
            hdata,
            server_list,
            "${irc_server.name} == ${name}",
            {},
            {"name": server_name},
            {},
            1,
        )
    else:
        return weechat.hdata_search(
            hdata,
            server_list,
            "${irc_server.name} == " + server_name,
            1,
        )

def set_buffer_read_time(buffer, t):
    if buffer in read_times and t <= read_times[buffer]:
        return False
    read_times[buffer] = t
    return True

def get_last_message_time(buffer):
    lines = weechat.hdata_pointer(weechat.hdata_get("buffer"), buffer, "own_lines")
    line = weechat.hdata_pointer(weechat.hdata_get("lines"), lines, "last_line")
    while line:
        line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")
        tags_count = weechat.hdata_integer(weechat.hdata_get("line_data"), line_data, "tags_count")
        tags = [
            weechat.hdata_string(weechat.hdata_get("line_data"), line_data, "{}|tags_array".format(i))
            for i in range(tags_count)
        ]
        irc_tags = [t for t in tags if t.startswith("irc_")]
        if len(irc_tags) > 0:
            break
        line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
    if not line:
        return None
    # TODO: get timestamp with millisecond granularity
    ts = weechat.hdata_time(weechat.hdata_get("line_data"), line_data, "date")
    t = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return t

def sync_buffer_hotlist(buffer):
    t = get_last_message_time(buffer)
    if t != None and buffer in read_times and read_times[buffer] >= t:
        weechat.buffer_set(buffer, "hotlist", "-1")

def handle_markread_msg(data, signal, signal_data):
    server_name = signal.split(",")[0]
    msg = weechat.info_get_hashtable("irc_message_parse", { "message": signal_data })

    args = msg["arguments"].split(" ")
    target = args[0]
    criteria = args[1]
    if criteria == "*":
        return weechat.WEECHAT_RC_OK_EAT
    if not criteria.startswith("timestamp="):
        return weechat.WEECHAT_RC_OK
    s = criteria.replace("timestamp=", "").replace("Z", "+00:00")
    t = datetime.datetime.fromisoformat(s)

    buffer = weechat.info_get("irc_buffer", server_name + "," + target)
    if buffer and set_buffer_read_time(buffer, t):
        sync_buffer_hotlist(buffer)

    return weechat.WEECHAT_RC_OK_EAT

def handle_buffer_close(data, signal, signal_data):
    buffer = signal_data

    if buffer in read_times:
        del read_times[buffer]
    return weechat.WEECHAT_RC_OK

def send_buffer_read(buffer, server_name, short_name):
    server = server_by_name(server_name)

    hdata = weechat.hdata_get("irc_server")
    cap_list = weechat.hdata_hashtable(hdata, server, "cap_list")
    if not READ_MARKER_CAP in cap_list:
        return

    t = get_last_message_time(buffer)
    if t == None:
        return

    if not set_buffer_read_time(buffer, t):
        return

    # Workaround for WeeChat timestamps missing millisecond granularity
    t += datetime.timedelta(milliseconds=999)
    t = t.astimezone(datetime.timezone.utc)
    s = t.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    cmd = "MARKREAD " + short_name + " timestamp=" + s
    server_buffer = weechat.buffer_search("irc", "server." + server_name)
    weechat.command_options(server_buffer, "/quote " + cmd, { "commands": "quote" })

def handle_hotlist_change(data, signal, signal_data):
    buffer = signal_data

    if buffer:
        sync_buffer_hotlist(buffer)
        return weechat.WEECHAT_RC_OK

    hdata = weechat.hdata_get("buffer")
    buffer = weechat.hdata_get_list(hdata, "gui_buffers")
    while buffer:
        full_name = weechat.hdata_string(hdata, buffer, "full_name")
        short_name = weechat.hdata_string(hdata, buffer, "short_name")
        hotlist = weechat.hdata_pointer(hdata, buffer, "hotlist")
        if not hotlist and full_name.startswith("irc.") and not full_name.startswith("irc.server."):
            # Trim "irc." prefix and ".<target>" suffix to obtain server name
            server_name = full_name.replace("irc.", "", 1)[:-len(short_name) - 1]
            send_buffer_read(buffer, server_name, short_name)
        buffer = weechat.hdata_pointer(hdata, buffer, "next_buffer")
    return weechat.WEECHAT_RC_OK

def handle_cap_sync_req(data, modifier, modifier_data, requested):
    supported = modifier_data.split(",")[1].split(" ")
    if READ_MARKER_CAP in supported:
        requested += " " + READ_MARKER_CAP
    return requested

weechat.hook_signal("*,irc_raw_in_markread", "handle_markread_msg", "")
weechat.hook_signal("buffer_closed", "handle_buffer_close", "")
weechat.hook_signal("hotlist_changed", "handle_hotlist_change", "")
if weechat_version >= 0x04000000:
    weechat.hook_modifier("irc_cap_sync_req", "handle_cap_sync_req", "")
