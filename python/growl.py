# -*- coding: utf-8 -*-
#
# growl.py
# Copyright (c) 2011 Sorin Ionescu <sorin.ionescu@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


SCRIPT_NAME = 'growl'
SCRIPT_AUTHOR = 'Sorin Ionescu <sorin.ionescu@gmail.com>'
SCRIPT_VERSION = '1.0.7'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Sends Growl notifications upon events.'


# Changelog
# 2014-05-10: v1.0.6 Change hook_print callback argument type of
#                    displayed/highlight (WeeChat >= 1.0)
# 2011-12-30: v1.0.5 Fixed a NoneType error.
# 2011-10-11: v1.0.4 Handle import errors better.
# 2011-10-10: v1.0.3 Handle Growl exceptions.
# 2011-10-04: v1.0.2 Growl 1.3 requires GNTP.
# 2011-09-25: v1.0.1 Always show highlighted messages if set on.
# 2011-03-27: v1.0.0 Initial release.


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
SETTINGS = {
    'show_public_message': 'off',
    'show_private_message': 'on',
    'show_public_action_message': 'off',
    'show_private_action_message': 'on',
    'show_notice_message': 'off',
    'show_invite_message': 'on',
    'show_highlighted_message': 'on',
    'show_server': 'on',
    'show_channel_topic': 'on',
    'show_dcc': 'on',
    'show_upgrade_ended': 'on',
    'sticky': 'off',
    'sticky_away': 'on',
    'hostname': '',
    'password': '',
    'icon': 'icon.png',
}


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
try:
    import re
    import os
    import weechat
    from gntp.notifier import GrowlNotifier
    IMPORT_OK = True
except ImportError as error:
    IMPORT_OK = False
    if str(error).find('weechat') != -1:
        print('This script must be run under WeeChat.')
        print('Get WeeChat at https://weechat.org.')
    elif str(error).find('notifier') != -1:
        weechat.prnt('', 'growl: GNTP bindings are not installed')
    else:
        weechat.prnt('', 'growl: {0}'.format(error))

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------
TAGGED_MESSAGES = {
    'public message or action': set(['irc_privmsg', 'notify_message']),
    'private message or action': set(['irc_privmsg', 'notify_private']),
    'notice message': set(['irc_notice', 'notify_private']),
    'invite message': set(['irc_invite', 'notify_highlight']),
    'channel topic': set(['irc_topic', ]),
    'away status': set(['away_info', ]),
}


UNTAGGED_MESSAGES = {
    'dcc chat request':
        re.compile(r'^xfer: incoming chat request from (\w+)', re.UNICODE),
    'dcc chat closed':
        re.compile(r'^xfer: chat closed with (\w+)', re.UNICODE),
    'dcc get request':
        re.compile(
            r'^xfer: incoming file from (\w+) [^:]+: ((?:,\w|[^,])+),',
            re.UNICODE),
    'dcc get completed':
        re.compile(r'^xfer: file ([^\s]+) received from \w+: OK', re.UNICODE),
    'dcc get failed':
        re.compile(
            r'^xfer: file ([^\s]+) received from \w+: FAILED',
            re.UNICODE),
    'dcc send completed':
        re.compile(r'^xfer: file ([^\s]+) sent to \w+: OK', re.UNICODE),
    'dcc send failed':
        re.compile(r'^xfer: file ([^\s]+) sent to \w+: FAILED', re.UNICODE),
}


DISPATCH_TABLE = {
    'away status': 'set_away_status',
    'public message or action': 'notify_public_message_or_action',
    'private message or action': 'notify_private_message_or_action',
    'notice message': 'notify_notice_message',
    'invite message': 'notify_invite_message',
    'channel topic': 'notify_channel_topic',
    'dcc chat request': 'notify_dcc_chat_request',
    'dcc chat closed': 'notify_dcc_chat_closed',
    'dcc get request': 'notify_dcc_get_request',
    'dcc get completed': 'notify_dcc_get_completed',
    'dcc get failed': 'notify_dcc_get_failed',
    'dcc send completed': 'notify_dcc_send_completed',
    'dcc send failed': 'notify_dcc_send_failed',
}


STATE = {
    'growl': None,
    'icon': None,
    'is_away': False
}


# -----------------------------------------------------------------------------
# Notifiers
# -----------------------------------------------------------------------------
def cb_irc_server_connected(data, signal, signal_data):
    '''Notify when connected to IRC server.'''
    if weechat.config_get_plugin('show_server') == 'on':
        growl_notify(
            'Server',
            'Server Connected',
            'Connected to network {0}.'.format(signal_data))
    return weechat.WEECHAT_RC_OK


def cb_irc_server_disconnected(data, signal, signal_data):
    '''Notify when disconnected to IRC server.'''
    if weechat.config_get_plugin('show_server') == 'on':
        growl_notify(
            'Server',
            'Server Disconnected',
            'Disconnected from network {0}.'.format(signal_data))
    return weechat.WEECHAT_RC_OK


def cb_notify_upgrade_ended(data, signal, signal_data):
    '''Notify on end of WeeChat upgrade.'''
    if weechat.config_get_plugin('show_upgrade_ended') == 'on':
        growl_notify(
            'WeeChat',
            'WeeChat Upgraded',
            'WeeChat has been upgraded.')
    return weechat.WEECHAT_RC_OK


def notify_highlighted_message(prefix, message):
    '''Notify on highlighted message.'''
    if weechat.config_get_plugin("show_highlighted_message") == "on":
        growl_notify(
            'Highlight',
            'Highlighted Message',
            "{0}: {1}".format(prefix, message),
            priority=2)


def notify_public_message_or_action(prefix, message, highlighted):
    '''Notify on public message or action.'''
    if prefix == ' *':
        regex = re.compile(r'^(\w+) (.+)$', re.UNICODE)
        match = regex.match(message)
        if match:
            prefix = match.group(1)
            message = match.group(2)
            notify_public_action_message(prefix, message, highlighted)
    else:
        if highlighted:
            notify_highlighted_message(prefix, message)
        elif weechat.config_get_plugin("show_public_message") == "on":
            growl_notify(
                'Public',
                'Public Message',
                '{0}: {1}'.format(prefix, message))


def notify_private_message_or_action(prefix, message, highlighted):
    '''Notify on private message or action.'''
    regex = re.compile(r'^CTCP_MESSAGE.+?ACTION (.+)$', re.UNICODE)
    match = regex.match(message)
    if match:
        notify_private_action_message(prefix, match.group(1), highlighted)
    else:
        if prefix == ' *':
            regex = re.compile(r'^(\w+) (.+)$', re.UNICODE)
            match = regex.match(message)
            if match:
                prefix = match.group(1)
                message = match.group(2)
                notify_private_action_message(prefix, message, highlighted)
        else:
            if highlighted:
                notify_highlighted_message(prefix, message)
            elif weechat.config_get_plugin("show_private_message") == "on":
                growl_notify(
                    'Private',
                    'Private Message',
                    '{0}: {1}'.format(prefix, message))


def notify_public_action_message(prefix, message, highlighted):
    '''Notify on public action message.'''
    if highlighted:
        notify_highlighted_message(prefix, message)
    elif weechat.config_get_plugin("show_public_action_message") == "on":
        growl_notify(
            'Action',
            'Public Action Message',
            '{0}: {1}'.format(prefix, message),
            priority=1)


def notify_private_action_message(prefix, message, highlighted):
    '''Notify on private action message.'''
    if highlighted:
        notify_highlighted_message(prefix, message)
    elif weechat.config_get_plugin("show_private_action_message") == "on":
        growl_notify(
            'Action',
            'Private Action Message',
            '{0}: {1}'.format(prefix, message),
            priority=1)


def notify_notice_message(prefix, message, highlighted):
    '''Notify on notice message.'''
    regex = re.compile(r'^([^\s]*) [^:]*: (.+)$', re.UNICODE)
    match = regex.match(message)
    if match:
        prefix = match.group(1)
        message = match.group(2)
        if highlighted:
            notify_highlighted_message(prefix, message)
        elif weechat.config_get_plugin("show_notice_message") == "on":
            growl_notify(
                'Notice',
                'Notice Message',
                '{0}: {1}'.format(prefix, message))


def notify_invite_message(prefix, message, highlighted):
    '''Notify on channel invitation message.'''
    if weechat.config_get_plugin("show_invite_message") == "on":
        regex = re.compile(
            r'^You have been invited to ([^\s]+) by ([^\s]+)$', re.UNICODE)
        match = regex.match(message)
        if match:
            channel = match.group(1)
            nick = match.group(2)
            growl_notify(
                'Invite',
                'Channel Invitation',
                '{0} has invited you to join {1}.'.format(nick, channel))


def notify_channel_topic(prefix, message, highlighted):
    '''Notify on channel topic change.'''
    if weechat.config_get_plugin("show_channel_topic") == "on":
        regex = re.compile(
            r'^\w+ has (?:changed|unset) topic for ([^\s]+)' +
                '(?:(?: from "(?:(?:"\w|[^"])+)")? to "((?:"\w|[^"])+)")?',
            re.UNICODE)
        match = regex.match(message)
        if match:
            channel = match.group(1)
            topic = match.group(2) or ''
            growl_notify(
                'Channel',
                'Channel Topic',
                "{0}: {1}".format(channel, topic))


def notify_dcc_chat_request(match):
    '''Notify on DCC chat request.'''
    if weechat.config_get_plugin("show_dcc") == "on":
        nick = match.group(1)
        growl_notify(
            'DCC',
            'Direct Chat Request',
            '{0} wants to chat directly.'.format(nick))


def notify_dcc_chat_closed(match):
    '''Notify on DCC chat termination.'''
    if weechat.config_get_plugin("show_dcc") == "on":
        nick = match.group(1)
        growl_notify(
            'DCC',
            'Direct Chat Ended',
            'Direct chat with {0} has ended.'.format(nick))


def notify_dcc_get_request(match):
    'Notify on DCC get request.'
    if weechat.config_get_plugin("show_dcc") == "on":
        nick = match.group(1)
        file_name = match.group(2)
        growl_notify(
            'DCC',
            'File Transfer Request',
            '{0} wants to send you {1}.'.format(nick, file_name))


def notify_dcc_get_completed(match):
    'Notify on DCC get completion.'
    if weechat.config_get_plugin("show_dcc") == "on":
        file_name = match.group(1)
        growl_notify('DCC', 'Download Complete', file_name)


def notify_dcc_get_failed(match):
    'Notify on DCC get failure.'
    if weechat.config_get_plugin("show_dcc") == "on":
        file_name = match.group(1)
        growl_notify('DCC', 'Download Failed', file_name)


def notify_dcc_send_completed(match):
    'Notify on DCC send completion.'
    if weechat.config_get_plugin("show_dcc") == "on":
        file_name = match.group(1)
        growl_notify('DCC', 'Upload Complete', file_name)


def notify_dcc_send_failed(match):
    'Notify on DCC send failure.'
    if weechat.config_get_plugin("show_dcc") == "on":
        file_name = match.group(1)
        growl_notify('DCC', 'Upload Failed', file_name)


# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
def set_away_status(prefix, message, highlighted):
    '''Sets away status for use by sticky notifications.'''
    regex = re.compile(r'^\[\w+ \b(away|back)\b:', re.UNICODE)
    match = regex.match(message)
    if match:
        status = match.group(1)
        if status == 'away':
            STATE['is_away'] = True
        if status == 'back':
            STATE['is_away'] = False


def cb_process_message(
    data,
    wbuffer,
    date,
    tags,
    displayed,
    highlight,
    prefix,
    message
):
    '''Delegates incoming messages to appropriate handlers.'''
    tags = set(tags.split(','))
    functions = globals()
    is_public_message = tags.issuperset(
        TAGGED_MESSAGES['public message or action'])
    buffer_name = weechat.buffer_get_string(wbuffer, 'name')
    dcc_buffer_regex = re.compile(r'^irc_dcc\.', re.UNICODE)
    dcc_buffer_match = dcc_buffer_regex.match(buffer_name)
    highlighted = False
    if int(highlight):
        highlighted = True
    # Private DCC message identifies itself as public.
    if is_public_message and dcc_buffer_match:
        notify_private_message_or_action(prefix, message, highlighted)
        return weechat.WEECHAT_RC_OK
    # Pass identified, untagged message to its designated function.
    for key, value in UNTAGGED_MESSAGES.items():
        match = value.match(message)
        if match:
            functions[DISPATCH_TABLE[key]](match)
            return weechat.WEECHAT_RC_OK
    # Pass identified, tagged message to its designated function.
    for key, value in TAGGED_MESSAGES.items():
        if tags.issuperset(value):
            functions[DISPATCH_TABLE[key]](prefix, message, highlighted)
            return weechat.WEECHAT_RC_OK
    return weechat.WEECHAT_RC_OK


def growl_notify(notification, title, description, priority=None):
    '''Returns whether Growl notifications should be sticky.'''
    growl = STATE['growl']
    is_away = STATE['is_away']
    icon = STATE['icon']
    is_sticky = False
    if weechat.config_get_plugin('sticky') == 'on':
        is_sticky = True
    if weechat.config_get_plugin('sticky_away') == 'on' and is_away:
        is_sticky = True
    try:
        growl.notify(
            noteType=notification,
            title=title,
            description=description,
            icon=icon,
            sticky=is_sticky,
            priority=priority)
    except Exception as error:
        weechat.prnt('', 'growl: {0}'.format(error))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    '''Sets up WeeChat Growl notifications.'''
    # Initialize options.
    for option, value in SETTINGS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value)
    # Initialize Growl.
    name = "WeeChat"
    hostname = weechat.config_get_plugin('hostname')
    password = weechat.config_get_plugin('password')
    icon = 'file://{0}'.format(
        os.path.join(
            weechat.info_get("weechat_dir", ""),
            weechat.config_get_plugin('icon')))
    notifications = [
        'Public',
        'Private',
        'Action',
        'Notice',
        'Invite',
        'Highlight',
        'Server',
        'Channel',
        'DCC',
        'WeeChat'
    ]
    if len(hostname) == 0:
        hostname = ''
    if len(password) == 0:
        password = ''
    growl = GrowlNotifier(
        applicationName=name,
        hostname=hostname,
        password=password,
        notifications=notifications,
        applicationIcon=icon)
    try:
        growl.register()
    except Exception as error:
        weechat.prnt('', 'growl: {0}'.format(error))
    STATE['growl'] = growl
    STATE['icon'] = icon
    # Register hooks.
    weechat.hook_signal(
        'irc_server_connected',
        'cb_irc_server_connected',
        '')
    weechat.hook_signal(
        'irc_server_disconnected',
        'cb_irc_server_disconnected',
        '')
    weechat.hook_signal('upgrade_ended', 'cb_upgrade_ended', '')
    weechat.hook_print('', '', '', 1, 'cb_process_message', '')


if __name__ == '__main__' and IMPORT_OK and weechat.register(
    SCRIPT_NAME,
    SCRIPT_AUTHOR,
    SCRIPT_VERSION,
    SCRIPT_LICENSE,
    SCRIPT_DESC,
    '',
    ''
):
    main()
