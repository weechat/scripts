# weejoin
# KittyKatt (kittykatt@teknik.io)
# Released under the BSD license.
# vim: set fileencoding=utf8 ts=4 sw=4 expandtab :

import json
import re
import urllib.parse
import urllib.request
import time

import weechat as w

# Constant used to check if configs are required
REQUIRED = '_required'

w.register('weejoin',
           'KittyKatt (Lefty for weebullet)',
           '1.0',
           'BSD',
           'weejoin pushes notifications from IRC to Join.',
           '', '')

w.hook_print("", "irc_privmsg", "", 1, "priv_msg_cb", "")
w.hook_command(
    "send_push_note",      # command
    "send a push note",    # description
    "[message]"            # arguments description,
    "",                    # argument
    "",
    "",
    "cmd_send_push_note", ""
)
w.hook_command(
    "weejoin",
    "pushes notifications from IRC to Join",
    "[command]",
    "Available commands are:\n"
    "   help        : prints config options and defaults\n"
    "   listdevices : prints a list of all devices associated"
    "                 with your Join API key\n"
    "   listignores : prints a list of channels that highlights "
    "                 won't be pushed for\n"
    "   ignore      : adds a channel to the blacklist\n"
    "   unignore    : removes a channel from the blacklist",
    "",
    "cmd_help", ""
)
configs = {
    "api_key": REQUIRED,
    "away_only": "1",            # only send when away
    "inactive_only": "1",        # only send if buffer inactive
    "device_iden": "all",        # send to all devices
    "ignored_channels": "",      # no ignored channels
    "min_notify_interval": "0",  # seconds, don't notify
                                 #   more often than this
    "debug": "0",                # enable debugging
    "ignore_on_relay": "0",      # if relay connected,
                                 #   don't send push notification
}

last_notification = 0   # 0 seconds from the epoch
# Icon used by Join for notification icon
notification_icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Weechat_logo.png/64px-Weechat_logo.png'

for option, default_value in configs.items():
    if w.config_get_plugin(option) == "":
        if configs[option] == REQUIRED:
            w.prnt("", w.prefix("error") +
                   "join: Please set option: %s" % option)
            if type(default_value) == "str":
                w.prnt("", "join: /set plugins.var.python.weejoin.%s STRING" % option)
            elif type(default_value) == "int":
                w.prnt("", "join: /set plugins.var.python.weejoin.%s INT" % option)
            else:
                w.prnt("", "join: /set plugins.var.python.weejoin.%s VALUE" % option)
        else:
            w.config_set_plugin(option, configs[option])


def debug(msg):
    if str(w.config_get_plugin("debug")) is not "0":
        w.prnt("", "[weejoin] DEBUG: %s" % str(msg))


def process_devicelist_cb(data, url, status, response, err):
    try:
        devices = json.loads(response)["records"]
        w.prnt("", "Device List:")
        for device in devices:
            if "deviceName" in device:
                w.prnt("", "---\n%s" % device["deviceName"])
            else:
                w.prnt("", "---\nUnnamed")
            w.prnt("", "%s" % device["id"])
    except KeyError:
        w.prnt("", "[weejoin] Error accessing device list: %s" % response)
        return w.WEECHAT_RC_ERROR
    return w.WEECHAT_RC_OK


def get_ignored_channels():
    ignored_channels = w.config_get_plugin("ignored_channels")
    if ignored_channels == "":
        return []
    else:
        return [channel.strip() for channel in ignored_channels.split(',')]


def cmd_help(data, buffer, args):
    # Get current list of ignored channels in list form
    ignored_channels = get_ignored_channels()

    # Used for checking for ignore/unignore commands and getting the arguments
    ignore_command = re.match("^ignore\s+(.+)", args)
    unignore_command = re.match("^unignore\s+(.+)", args)

    if(ignore_command is not None):
        channels_to_ignore = ignore_command.group(1).split(' ')

        for channel in channels_to_ignore:
            if channel not in ignored_channels:
                ignored_channels.append(channel)

        w.config_set_plugin("ignored_channels", ','.join(ignored_channels))
        w.prnt("", "Updated. Ignored channels: %s" % w.config_get_plugin("ignored_channels"))
    elif(unignore_command is not None):
        channels_to_unignore = unignore_command.group(1).split(' ')

        for channel in channels_to_unignore:
            if channel in ignored_channels:
                ignored_channels.remove(channel)

        w.config_set_plugin("ignored_channels", ','.join(ignored_channels))
        w.prnt("", "Updated. Ignored channels: %s" % w.config_get_plugin("ignored_channels"))
    elif(args == "listignores"):
        w.prnt("", "Ignored channels: %s" % w.config_get_plugin("ignored_channels"))
    elif(args == "listdevices"):
        apikey = w.string_eval_expression(w.config_get_plugin("api_key"), {}, {}, {})
        apiurl = "https://joinjoaomgcd.appspot.com/_ah/api/registration/v1/listDevices?apikey=%s" % (apikey)
        w.hook_process("url:" + apiurl, 20000, "process_devicelist_cb", "")
    else:
        w.prnt("", """
WeeJoin requires an API key from your Join account to work. Set your API key with (evaluated):
    /set plugins.var.python.weejoin.api_key <KEY>

WeeJoin will by default only send notifications when you are marked away on IRC. You can change this with:
    /set plugins.var.python.weejoin.away_only [0|1]

WeeJoin will by default send to all devices associated with your Join account. You can change this with:
    /set plugins.var.python.weejoin.device_iden <ID>

WeeJoin can ignore repeated notifications if they arrive too often.  You can set this with (0 or blank to disable):
    /set plugins.var.python.weejoin.min_notify_interval <NUMBER>

You can get a list of your devices from the Join website, or by using
    /weejoin listdevices
""")
    return w.WEECHAT_RC_OK


def process_join_cb(data, url, status, response, err):
    body = None
    headers = {}
    lines = response.rstrip().splitlines()
    status_code = int(lines.pop(0).split()[1])
    for line in lines:
        if body == "":
            body += line
            continue
        header_line = line.split(":", 2)
        if len(header_line) != 2:
            body = ""
            continue
        headers[header_line[0].strip()] = header_line[1].strip()

    # response is the string of http body
    if status == w.WEECHAT_HOOK_PROCESS_ERROR:
        w.prnt("", "[weejoin] Error sending to join: %s - %s" % (status, url))
        return w.WEECHAT_RC_ERROR

    if status_code is 401 or status_code is 403:
        w.prnt("", "[weejoin] Invalid API Token: %s" % (w.string_eval_expression(w.config_get_plugin("api_key"), {}, {}, {})))
        return w.WEECHAT_RC_ERROR
    if status_code is not 200:
        w.prnt("", "[weejoin] Error sending to join: %s - %s - %s" % (url, status_code, body))
        return w.WEECHAT_RC_ERROR

    return w.WEECHAT_RC_OK


def send_push(title, body):
    global last_notification

    interval = w.config_get_plugin("min_notify_interval")
    if interval is not None and interval != "" and int(interval) != 0:
        interval = int(interval)

        earliest_notification = last_notification + int(interval)

        if last_notification is not None and time.time() <= earliest_notification:
            debug("Too soon since last notification, skipping")
            return w.WEECHAT_RC_OK

    last_notification = time.time()

    # check to see if the relay is connected, ignore if so
    check_relays = w.config_string_to_boolean(w.config_get_plugin('ignore_on_relay'))
    CONNECTED_RELAY = False
    if check_relays:
        infolist = w.infolist_get('relay', '', '')
        if infolist:
            while w.infolist_next(infolist):
                status = w.infolist_string(infolist, 'status_string')
                if status == 'connected':
                    CONNECTED_RELAY = True
                    break
            w.infolist_free(infolist)

    if CONNECTED_RELAY is True:
        # we have a relay conected, don't notify
        debug("Relay is connected, not sending push.")
        return w.WEECHAT_RC_OK

    debug("Sending push.  Title: [%s], body: [%s]" % (title, body))

    apikey = w.string_eval_expression(w.config_get_plugin("api_key"), {}, {}, {})
    apiurl = "https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?apikey=%s" % (apikey)
    timeout = 20000  # FIXME - actually use config
    if len(title) is not 0 or len(body) is not 0:
        deviceiden = w.config_get_plugin("device_iden")
        if deviceiden == "all":
            payload = urllib.parse.urlencode({'title': title, 'text': body, 'deviceId': 'group.all', 'icon': notification_icon})
            debug("Full Payload: %s%s" % (apiurl, payload))
        else:
            payload = urllib.parse.urlencode({'title': title, 'text': body, 'deviceId': deviceiden, 'icon': notification_icon})
            debug("Full Payload: %s%s" % (apiurl, payload))
        w.hook_process_hashtable("url:" + apiurl, {"postfields": payload, "header": "1"}, timeout, "process_join_cb", "")


def cmd_send_push_note(data, buffer, args):
    send_push(
        title="Manual Notification from weechat",
        body=args)
    return w.WEECHAT_RC_OK


def priv_msg_cb(data, bufferp, uber_empty,
                tagsn, isdisplayed,
                ishilight, prefix, message):
    """Sends highlighted message to be printed on notification"""

    if w.config_get_plugin("away_only") == "1":
        am_away = w.buffer_get_string(bufferp, 'localvar_away')
    else:
        am_away = True

    if not am_away:
        # TODO: make debug a configurable
        debug("Not away, skipping notification")
        return w.WEECHAT_RC_OK

    # If 'inactive_only' is enabled, we need to check if the notification is
    # coming from the active buffer.
    if w.config_get_plugin("inactive_only") == "1":
        if w.current_buffer() == bufferp:
            # The notification came from the current buffer - don't notify
            debug("Notification came from the active buffer, "
                  "skipping notification")
            return w.WEECHAT_RC_OK

    notif_body = u"<%s> %s" % (prefix, message)

    # Check that it's in a "/q" buffer and that I'm not the one writing the msg
    is_pm = w.buffer_get_string(bufferp, "localvar_type") == "private"
    is_notify_private = re.search(r'(^|,)notify_private(,|$)', tagsn) is not None
    # PM (query)
    if (is_pm and is_notify_private):
        send_push(
            title="Privmsg from %s" % prefix,
            body=notif_body
        )

    # Highlight (your nick is quoted)
    elif (str(ishilight) == "1"):
        bufname = (w.buffer_get_string(bufferp, "short_name") or
                   w.buffer_get_string(bufferp, "name"))

        ignored_channels = get_ignored_channels()

        if bufname not in ignored_channels:
            send_push(
                title="Highlight in %s" % bufname,
                body=notif_body
            )
        else:
            debug("[weejoin] Ignored channel, skipping notification in %s" % bufname)

    return w.WEECHAT_RC_OK
