# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 p3lim <weechat@p3lim.net>
#
# https://github.com/p3lim/weechat-detach-away
#
# Changelog:
# Ver: 0.1.1 Python3 support by Antonin Skala skala.antonin@gmail.com 3.2019
# Ver: 0.1.2 Support Python 2 and 3 by Antonin Skala skala.antonin@gmail.com 3.2019

try:
    import weechat
except ImportError:
    from sys import exit
    print('This script has to run under WeeChat (https://weechat.org/).')
    exit(1)

import sys

if sys.version_info[0] > 2:
    from urllib.parse import urlencode
else:
    from urllib import urlencode

SCRIPT_NAME = 'detach_away'
SCRIPT_AUTHOR = 'p3lim'
SCRIPT_VERSION = '0.1.2'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Automatically sets away message based on number of relays connected'

SETTINGS = {
    'message': (
        'I am away',
        'away message'),
    'debugging': (
        'off',
        'debug flag'),
}

num_relays = 0

def DEBUG():
    return weechat.config_get_plugin('debug') == 'on'

def set_away(is_away, message=''):
    if is_away:
        message = weechat.config_get_plugin('message')

    weechat.command('', '/away -all ' + message)

def relay_connected(data, signal, signal_data):
    global num_relays

    if DEBUG():
        weechat.prnt('', 'DETACH_AWAY: last #relays: ' + str(num_relays))

    if int(num_relays) == 0:
        set_away(False)

    num_relays = weechat.info_get('relay_client_count', 'connected')
    return weechat.WEECHAT_RC_OK

def relay_disconnected(data, signal, signal_data):
    global num_relays

    if DEBUG():
        weechat.prnt('', 'DETACH_AWAY: last #relays: ' + str(num_relays))

    if int(num_relays) > 0:
        set_away(True)

    num_relays = weechat.info_get('relay_client_count', 'connected')
    return weechat.WEECHAT_RC_OK

# register plugin
weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

# register for relay status
weechat.hook_signal('relay_client_connected', 'relay_connected', '')
weechat.hook_signal('relay_client_disconnected', 'relay_disconnected', '')

# register configuration defaults
for option, value in SETTINGS.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, value[0])
    weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
