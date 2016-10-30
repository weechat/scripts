# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


from __future__ import (unicode_literals, absolute_import,
                        division, print_function)


import weechat as w
import paho.mqtt.client as mqtt
import json

SCRIPT_NAME = 'mqtt_notify'
SCRIPT_AUTHOR = 'Guillaume Subiron <maethor@subiron.org>'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'WTFPL'
SCRIPT_DESC = 'Sends notifications using MQTT'

w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
           SCRIPT_DESC, '', '')

DEFAULT_OPTIONS = {
    'mqtt_host': 'localhost',
    'mqtt_port': '1883',
    'mqtt_timeout': '60',
    'mqtt_user': '',
    'mqtt_password': '',
    'mqtt_channel': 'weechat',
}

for key, val in DEFAULT_OPTIONS.items():
    if not w.config_is_set_plugin(key):
        w.config_set_plugin(key, val)

w.hook_print("", "notify_message", "", 1, "on_msg", "")
w.hook_print("", "notify_private", "", 1, "on_msg", "private")
w.hook_print("", "notify_highlight", "", 1, "on_msg", "")  # Not sure if needed


def on_msg(*a):
    keys = ['data', 'buffer', 'timestamp', 'tags', 'displayed', 'highlight',
            'sender', 'message']
    msg = dict(zip(keys, a))
    msg['buffer'] = w.buffer_get_string(msg['buffer'], 'short_name')

    cli = mqtt.Client()
    if w.config.get_plugin('mqtt_user'):
        cli.username_pw_set(w.config_get_plugin('mqtt_user'),
                            password=w.config_get_plugin('mqtt_password'))
    cli.connect(w.config_get_plugin('mqtt_host'),
                int(w.config_get_plugin('mqtt_port')),
                int(w.config_get_plugin('mqtt_timeout')))
    cli.publish(w.config_get_plugin('mqtt_channel'),
                json.dumps(msg), retain=True)

    return w.WEECHAT_RC_OK
