# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
#
# History
#
# 2018-05-06, Serge van GInderachter <serge@vanginderachter.be
#       v0.5:  major update, taking over maintainership from Guillaume Subiron
#               - feature: add variables to customize the data fiels in the
#                 print hooks, default values are backwards compatible
#               - feature: add messages on connecting/disconnecting to mqtt
#               - feature: add script unload hook function to clean up the mqtt
#                 connection
#               - feature: add variable for mqtt client name
#               - feature: add buffer_long and buffer_full in message json
#               - fix: move mqtt connect code to global scope, avoiding
#                 new connections on each message causing lost messages due to
#                 network/socket errors, and optimized for mqtt client
#                 loop_start/stop
#               - fix: rename mqtt_timeout to mqtt_keepalive
# 2017-12-29, Miłosz Tyborowski <milosz@tyborek.pl>
#       v0.2:   - fix: correct a typo causing AttributeError
# 2016-10-30, Guillaume Subiron <maethor@subiron.org>
#       v0.1:   New script mqtt_notify.py:
#               send notifications using the MQTT protocol
#

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
try:
    import weechat
    import_ok = True
except ImportError:
    weechat.prnt('', 'mqtt_notify: this script must be run under WeeChat.')
    weechat.prnt('', 'Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import paho.mqtt.client as paho
    import json
    import socket
except ImportError as message:
    weechat.prnt('', 'mqtt_notify: missing package(s): %s' % (message))
    import_ok = False
import sys


# @srgvg on Github:
SCRIPT_MAINTAINER = 'Serge van Ginderachter <serge@vanginderachter.be>'

SCRIPT_NAME = 'mqtt_notify'
SCRIPT_AUTHOR = 'Guillaume Subiron <maethor@subiron.org>'
SCRIPT_VERSION = '0.5'
SCRIPT_LICENSE = 'WTFPL'
SCRIPT_DESC = 'Sends notifications using MQTT'

DEFAULT_OPTIONS = {
    'mqtt_host': 'localhost',
    'mqtt_port': '1883',
    'mqtt_keepalive': '60',
    'mqtt_user': '',
    'mqtt_password': '',
    'mqtt_channel': 'weechat',
    'mqtt_client_name': 'weechat_mqtt_notify',
    'mqtt_message_data': '',  # string passed in the data field of the callback
    'mqtt_private_data': 'private',
}


def mqtt_on_connect(client, userdata, flags, rc):

    if rc == 0:
        weechat.prnt('', 'mqtt_notify: connected successfully')
    else:
        weechat.prnt(
            '',
            'mqtt_notify: failed connecting - return code %s' %
            rc)


def mqtt_on_disconnect(client, userdata, rc):

    if rc != 0:
        weechat.prnt(
            '',
            'mqtt_notify: unexpected disconnection - return code %s' %
            rc)
    else:
        weechat.prnt('', 'mqtt_notify: disconnected')


def weechat_on_msg_cb(*a):

    keys = ['data', 'buffer', 'timestamp', 'tags', 'displayed', 'highlight',
            'sender', 'message']
    msg = dict(zip(keys, a))

    msg['buffer_long'] = weechat.buffer_get_string(msg['buffer'], 'name')
    msg['buffer_full'] = weechat.buffer_get_string(msg['buffer'], 'full_name')
    msg['buffer'] = weechat.buffer_get_string(msg['buffer'], 'short_name')

    mqttclient.publish(weechat.config_get_plugin('mqtt_channel'),
                       json.dumps(msg), retain=True)

    return weechat.WEECHAT_RC_OK


def mqtt_notify_script_unload():

    mqttclient.loop_stop()
    mqttclient.disconnect()
    return weechat.WEECHAT_RC_OK


if import_ok:

    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                     SCRIPT_LICENSE, SCRIPT_DESC, 'mqtt_notify_script_unload',
                     '')

    for key, val in DEFAULT_OPTIONS.items():
        if not weechat.config_is_set_plugin(key):
            weechat.config_set_plugin(key, val)

    # Setup the MQTT client
    mqttclient = paho.Client(client_id=weechat.config_get_plugin(
        'mqtt_client_name'), clean_session=False)
    mqttclient.on_connect = mqtt_on_connect
    mqttclient.on_disconnect = mqtt_on_disconnect

    if weechat.config_get_plugin('mqtt_user'):
        mqttclient.username_pw_set(weechat.config_get_plugin('mqtt_user'),
                                   password=weechat.config_get_plugin(
                                   'mqtt_password'))
    try:
        mqttclient.connect_async(weechat.config_get_plugin('mqtt_host'),
                                 int(weechat.config_get_plugin('mqtt_port')),
                                 int(weechat.config_get_plugin(
                                     'mqtt_keepalive')))
        mqttclient.loop_start()
    except socket.error as err:
        # mqttclient loop runs in background thread
        # and wil keep trying to reconnect
        pass

    weechat.hook_print("", "notify_message", "", 1, "weechat_on_msg_cb",
                       weechat.config_get_plugin("mqtt_message_data"))
    weechat.hook_print("", "notify_private", "", 1, "weechat_on_msg_cb",
                       weechat.config_get_plugin("mqtt_private_data"))
