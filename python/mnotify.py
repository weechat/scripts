# -*- coding: utf-8 -*-
# mnotify.py
# Copyleft (c) 2013 maker <maker@python.it>
# Released under Beerware License
#
# based on:
# anotify.py
# Copyright (c) 2012 magnific0 <jacco.geul@gmail.com>
#
# based on:
# growl.py
# Copyright (c) 2011 Sorin Ionescu <sorin.ionescu@gmail.com>
#
# Changelog:
# Ver: 0.4 by Antonin Skala tony762@gmx.com 3.2018
#
# Changed dcc regex to match new notify appears (weechat notify now contain IP)
# Added dcc send offer and dcc send start notify
# Setting for notify is divided to off (don't send), on (always send),
# away (send only when away).
# Changed default settings to match new scheme
# DCC get request show name with ip, network and size of file.
#
# Ver: 0.5 by Antonin Skala tony762@gmx.com 3.2019
# Repaired DCC Get FAILED message.
#
# Ver: 0.6 by Antonin Skala tony762@gmx.com 3.2019
# Support Python 2 and 3
#
# Help:
# Install and configure msmtp first (msmtp.sourceforge.net/)
# List and Change plugin settings by /set plugins.var.python.mnotify.*
# Change language to english -otherwise this will not work
# /set env LANG en_US.UTF-8
# /save
# /upgrade
#
# If running from TMux:
# /usr/bin/tmux -S /tmp/ircmux -2 new-session -d -s irc bash
# /usr/bin/tmux -S /tmp/ircmux -2 send -t irc "export LANG=en_US.UTF-8" ENTER
# /usr/bin/tmux -S /tmp/ircmux -2 send -t irc weechat ENTER

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import re
import sys
import subprocess
from email.mime.text import MIMEText

import weechat

SCRIPT_NAME = 'mnotify'
SCRIPT_AUTHOR = 'maker'
SCRIPT_VERSION = '0.6'
SCRIPT_LICENSE = 'Beerware License'
SCRIPT_DESC = 'Sends mail notifications upon events.'

# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
SETTINGS = {
    'show_public_message': 'off',
    'show_private_message': 'away',
    'show_public_action_message': 'off',
    'show_private_action_message': 'away',
    'show_notice_message': 'off',
    'show_invite_message': 'away',
    'show_highlighted_message': 'off',
    'show_server': 'away',
    'show_channel_topic': 'off',
    'show_dcc': 'on',
    'show_upgrade_ended': 'off',
    'sendmail': '/usr/bin/msmtp',
    'email_to': 'somebody@somwhere.xx',
    'email_from': 'irc@somwhere.xx'
}


# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------
TAGGED_MESSAGES = {
    'public message or action': set(['irc_privmsg', 'notify_message']),
    'private message or action': set(['irc_privmsg', 'notify_private']),
    'notice message': set(['irc_notice', 'notify_private']),
    'invite message': set(['irc_invite', 'notify_highlight']),
    'channel topic': set(['irc_topic', ]),
}


UNTAGGED_MESSAGES = {
    'away status':
        re.compile(r'^You ((\w+).){2,3}marked as being away', re.UNICODE),
    'dcc chat request':
        re.compile(r'^xfer: incoming chat request from ([^\s]+) ', re.UNICODE),
    'dcc chat closed':
        re.compile(r'^xfer: chat closed with ([^\s]+) \(', re.UNICODE),
    'dcc get request':
        re.compile(
            r'^xfer: incoming file from (^\s|.+), name: ((?:,\w|[^,])+), (\d+) bytes',
            re.UNICODE),
    'dcc get completed':
        re.compile(r'^xfer: file ((?:,\w|[^,])+) received from ([^\s]+) ((?:,\w|[^,]+)): OK$', re.UNICODE),
    'dcc get failed':
        re.compile(
            r'^xfer: file ((?:,\w|[^,])+) received from ([^\s]+) ((?:,\w|[^,]+)): FAILED$',
            re.UNICODE),
    'dcc send offer':
        re.compile(r'^xfer: offering file to ([^\s]+) ((?:,\w|[^,])+), name: ((?:,\w|[^,])+) \(local', re.UNICODE),
    'dcc send start':
        re.compile(r'^xfer: sending file to ([^\s]+) ((?:,\w|.)+), name: ((?:,\w|[^,])+) \(local', re.UNICODE),
    'dcc send completed':
        re.compile(r'^xfer: file ((?:,\w|[^,])+) sent to ([^\s]+) ((?:,\w|[^,]+)): OK$', re.UNICODE),
    'dcc send failed':
        re.compile(r'^xfer: file ((?:,\w|[^,])+) sent to ([^\s]+) ((?:,\w|[^,]+)): FAILED$', re.UNICODE),
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
    'dcc send offer': 'notify_dcc_send_offer',
    'dcc send start': 'notify_dcc_send_start',
    'dcc send completed': 'notify_dcc_send_completed',
    'dcc send failed': 'notify_dcc_send_failed',
}


STATE = {
    'icon': None,
    'is_away': False
}


# -----------------------------------------------------------------------------
# Notifiers
# -----------------------------------------------------------------------------
def cb_irc_server_connected(data, signal, signal_data):
    '''Notify when connected to IRC server.'''
    if (weechat.config_get_plugin('show_server') == 'on'
        or (weechat.config_get_plugin('show_server') == "away"
            and STATE['is_away'])):
        a_notify(
            'Server',
            'Server Connected',
            'Connected to network {0}.'.format(signal_data))
    return weechat.WEECHAT_RC_OK


def cb_irc_server_disconnected(data, signal, signal_data):
    '''Notify when disconnected to IRC server.'''
    if (weechat.config_get_plugin('show_server') == 'on'
        or (weechat.config_get_plugin('show_server') == "away"
            and STATE['is_away'])):
        a_notify(
            'Server',
            'Server Disconnected',
            'Disconnected from network {0}.'.format(signal_data))
    return weechat.WEECHAT_RC_OK


def cb_notify_upgrade_ended(data, signal, signal_data):
    '''Notify on end of WeeChat upgrade.'''
    if (weechat.config_get_plugin('show_upgrade_ended') == 'on'
        or (weechat.config_get_plugin('show_upgrade_ended') == "away"
            and STATE['is_away'])):
        a_notify(
            'WeeChat',
            'WeeChat Upgraded',
            'WeeChat has been upgraded.')
    return weechat.WEECHAT_RC_OK


def notify_highlighted_message(buffername, prefix, message):
    '''Notify on highlighted message.'''
    if (weechat.config_get_plugin("show_highlighted_message") == "on"
        or (weechat.config_get_plugin("show_highlighted_message") == "away"
            and STATE['is_away'])):
        a_notify(
            'Highlight',
            'Highlighted on {0} by {1}'.format(buffername, prefix),
            "{0}: {1}".format(prefix, message),
        )


def notify_public_message_or_action(buffername, prefix, message, highlighted):
    '''Notify on public message or action.'''
    if prefix == ' *':
        regex = re.compile(r'^(\w+) (.+)$', re.UNICODE)
        match = regex.match(message)
        if match:
            prefix = match.group(1)
            message = match.group(2)
            notify_public_action_message(buffername, prefix,
                                         message, highlighted)
    else:
        if highlighted:
            notify_highlighted_message(buffername, prefix, message)
        elif (weechat.config_get_plugin("show_public_message") == "on"
              or (weechat.config_get_plugin("show_public_message") == "away"
                  and STATE['is_away'])):
            a_notify(
                'Public',
                'Public Message on {0}'.format(buffername),
                '{0}: {1}'.format(prefix, message))


def notify_private_message_or_action(buffername, prefix, message, highlighted):
    '''Notify on private message or action.'''
    regex = re.compile(r'^CTCP_MESSAGE.+?ACTION (.+)$', re.UNICODE)
    match = regex.match(message)
    if match:
        notify_private_action_message(buffername, prefix,
                                      match.group(1), highlighted)
    else:
        if prefix == ' *':
            regex = re.compile(r'^(\w+) (.+)$', re.UNICODE)
            match = regex.match(message)
            if match:
                prefix = match.group(1)
                message = match.group(2)
                notify_private_action_message(buffername, prefix,
                                              message, highlighted)
        else:
            if highlighted:
                notify_highlighted_message(buffername, prefix, message)
            elif (weechat.config_get_plugin("show_private_message") == "on"
                  or (weechat.config_get_plugin("show_private_message") == "away"
                      and STATE['is_away'])):
                a_notify(
                    'Private',
                    'Private Message',
                    '{0}: {1}'.format(prefix, message))


def notify_public_action_message(buffername, prefix, message, highlighted):
    '''Notify on public action message.'''
    if highlighted:
        notify_highlighted_message(buffername, prefix, message)
    elif (weechat.config_get_plugin("show_public_action_message") == "on"
          or (weechat.config_get_plugin("show_public_action_message") == "away"
              and STATE['is_away'])):
        a_notify(
            'Action',
            'Public Action Message on {0}'.format(buffername),
            '{0}: {1}'.format(prefix, message),
        )


def notify_private_action_message(buffername, prefix, message, highlighted):
    '''Notify on private action message.'''
    if highlighted:
        notify_highlighted_message(buffername, prefix, message)
    elif (weechat.config_get_plugin("show_private_action_message") == "on"
          or (weechat.config_get_plugin("show_private_action_message") == "away"
              and STATE['is_away'])):
        a_notify(
            'Action',
            'Private Action Message',
            '{0}: {1}'.format(prefix, message),
        )


def notify_notice_message(buffername, prefix, message, highlighted):
    '''Notify on notice message.'''
    regex = re.compile(r'^([^\s]*) [^:]*: (.+)$', re.UNICODE)
    match = regex.match(message)
    if match:
        prefix = match.group(1)
        message = match.group(2)
        if highlighted:
            notify_highlighted_message(buffername, prefix, message)
        elif (weechat.config_get_plugin("show_notice_message") == "on"
              or (weechat.config_get_plugin("show_notice_message") == "away"
                  and STATE['is_away'])):
            a_notify(
                'Notice',
                'Notice Message',
                '{0}: {1}'.format(prefix, message))


def notify_invite_message(buffername, prefix, message, highlighted):
    '''Notify on channel invitation message.'''
    if (weechat.config_get_plugin("show_invite_message") == "on"
        or (weechat.config_get_plugin("show_invite_message") == "away"
            and STATE['is_away'])):
        regex = re.compile(
            r'^You have been invited to ([^\s]+) by ([^\s]+)$', re.UNICODE)
        match = regex.match(message)
        if match:
            channel = match.group(1)
            nick = match.group(2)
            a_notify(
                'Invite',
                'Channel Invitation',
                '{0} has invited you to join {1}.'.format(nick, channel))


def notify_channel_topic(buffername, prefix, message, highlighted):
    '''Notify on channel topic change.'''
    if (weechat.config_get_plugin("show_channel_topic") == "on"
        or (weechat.config_get_plugin("show_channel_topic") == "away"
            and STATE['is_away'])):
        regex = re.compile(
            r'^\w+ has (?:changed|unset) topic for ([^\s]+)' +
            r'(?:(?: from "(?:.+)")? to "(.+)")?',
            re.UNICODE)
        match = regex.match(message)
        if match:
            channel = match.group(1)
            topic = match.group(2) or ''
            a_notify(
                'Channel',
                'Channel Topic on {0}'.format(buffername),
                "{0}: {1}".format(channel, topic))


def notify_dcc_chat_request(match):
    '''Notify on DCC chat request.'''
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(1)
        a_notify(
            'DCC',
            'Direct Chat Request',
            '{0} wants to chat directly.'.format(nick))


def notify_dcc_chat_closed(match):
    '''Notify on DCC chat termination.'''
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(1)
        a_notify(
            'DCC',
            'Direct Chat Ended',
            'Direct chat with {0} has ended.'.format(nick))


def notify_dcc_get_request(match):
    'Notify on DCC get request.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(1)
        file_name = match.group(2)
        file_size = int(match.group(3))
        a_notify(
            'DCC',
            'File Transfer Request',
            '{0} wants to send you {1} and size is {2}.'.format(nick, file_name, humanbytes(file_size)))


def notify_dcc_get_completed(match):
    'Notify on DCC get completion.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(2)
        file_name = match.group(1)
        a_notify(
            'DCC',
            'Download Complete',
            'Downloading {1} from {0} completed.'.format(nick, file_name))


def notify_dcc_get_failed(match):
    'Notify on DCC get failure.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(2)
        file_name = match.group(1)
        a_notify(
            'DCC',
            'Download Failed',
            'Downloading {1} from {0} failed.'.format(nick, file_name))


def notify_dcc_send_offer(match):
    'Notify on DCC send offer.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(1)
        file_name = match.group(3)
        a_notify(
            'DCC',
            'Offering File Upload',
            'Offering {1} to {0}.'.format(nick, file_name))


def notify_dcc_send_start(match):
    'Notify on DCC send start.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(1)
        file_name = match.group(3)
        a_notify(
            'DCC',
            'Start File Upload',
            'Uploading {1} to {0}.'.format(nick, file_name))


def notify_dcc_send_completed(match):
    'Notify on DCC send completion.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(2)
        file_name = match.group(1)
        a_notify(
            'DCC',
            'Upload Complete',
            'Upload {1} to {0} completed.'.format(nick, file_name))


def notify_dcc_send_failed(match):
    'Notify on DCC send failure.'
    if (weechat.config_get_plugin("show_dcc") == "on"
        or (weechat.config_get_plugin("show_dcc") == "away"
            and STATE['is_away'])):
        nick = match.group(2)
        file_name = match.group(1)
        a_notify(
            'DCC',
            'Upload Failed',
            'Upload {1} to {0} failed.'.format(nick, file_name))


# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
def set_away_status(match):
    status = match.group(1)
    if status == 'been ':
        STATE['is_away'] = True
    if status == 'longer ':
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
        notify_private_message_or_action(buffer_name, prefix,
                                         message, highlighted)
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
            functions[DISPATCH_TABLE[key]](buffer_name, prefix,
                                           message, highlighted)
            return weechat.WEECHAT_RC_OK
    return weechat.WEECHAT_RC_OK


def humanbytes(B):
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776
    if B < KB:
        return '{0} {1}'.format(B, 'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B/KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B/MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B/GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B/TB)


def a_notify(notification, subject, message):
    msg = MIMEText(message)
    msg['From'] = weechat.config_get_plugin('email_from')
    msg['To'] = weechat.config_get_plugin('email_to')
    msg['Subject'] = subject

    p = subprocess.Popen(
        [weechat.config_get_plugin('sendmail'),
         weechat.config_get_plugin('email_to')],
        stdin=subprocess.PIPE,

    )
    if sys.version_info[0] > 2:
        p.communicate(input=str.encode(msg.as_string()))
    else:
        p.communicate(input=str(msg))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    '''Sets up WeeChat notifications.'''
    # Initialize options.
    for option, value in SETTINGS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value)
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


if __name__ == '__main__' and weechat.register(
    SCRIPT_NAME,
    SCRIPT_AUTHOR,
    SCRIPT_VERSION,
    SCRIPT_LICENSE,
    SCRIPT_DESC,
    '',
    ''
):
    main()
