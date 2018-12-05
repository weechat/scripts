# -*- coding: utf-8 -*-

# Blackmore's Enhanced IRC-Notification Collection (BEINC) v3.0
# Copyright (C) 2013-2018 Simeon Simeonov

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import datetime
import json
import os
import socket
import ssl
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.parse import urlencode
    from urllib.request import urlopen
else:
    from urllib import urlencode
    from urllib2 import urlopen

import weechat


__author__ = 'Simeon Simeonov'
__version__ = '3.0'
__license__ = 'GPL3'


enabled = True
global_values = dict()

# few constants #
BEINC_POLICY_NONE = 0
BEINC_POLICY_ALL = 1
BEINC_POLICY_LIST_ONLY = 2
BEINC_CURRENT_CONFIG_VERSION = 2


class WeechatTarget(object):
    """
    The target (destination) class
    Each remote destination is represented as a WeechatTarget object
    """

    def __init__(self, target_dict):
        """
        target_dict: the config-dictionary node that represents this instance
        """
        self.__name = target_dict.get('name', '')
        if self.__name == '':
            raise Exception('"name" not defined for target')
        self.__url = target_dict.get('target_url', '')
        if self.__url == '':
            raise Exception('"target_url" not defined for target')
        self.__password = target_dict.get('target_password', '')
        self.__pm_title_template = target_dict.get('pm_title_template',
                                                   '%s @ %S')
        self.__pm_message_template = target_dict.get('pm_message_template',
                                                     '%m')
        self.__cm_title_template = target_dict.get('cm_title_template',
                                                   '%c @ %S')
        self.__cm_message_template = target_dict.get('cm_message_template',
                                                     '%s -> %m')
        self.__nm_title_template = target_dict.get('nm_title_template',
                                                   '%c @ %S')
        self.__nm_message_template = target_dict.get('nm_message_template',
                                                     '%s -> %m')
        self.__chans = set(target_dict.get('channel_list', list()))
        self.__nicks = set(target_dict.get('nick_list', list()))
        self.__chan_messages_policy = int(target_dict.get(
            'channel_messages_policy',
            BEINC_POLICY_LIST_ONLY))
        self.__priv_messages_policy = int(target_dict.get(
            'private_messages_policy',
            BEINC_POLICY_ALL))
        self.__notifications_policy = int(target_dict.get(
            'notifications_policy',
            BEINC_POLICY_ALL))
        self.__cert_file = target_dict.get('target_cert_file')
        self.__timestamp_format = target_dict.get('target_timestamp_format',
                                                  '%H:%M:%S')
        self.__debug = bool(target_dict.get('debug', False))
        self.__enabled = bool(target_dict.get('enabled', True))
        self.__socket_timeout = int(target_dict.get('socket_timeout', 3))
        self.__ssl_ciphers = target_dict.get('ssl_ciphers', '')
        self.__disable_hostname_check = bool(
            target_dict.get('disable-hostname-check', False))
        self.__ssl_version = target_dict.get('ssl_version', 'auto')
        self.__last_message = None  # datetime.datetime instance
        self.__context = None
        self.__context_setup()

    @property
    def name(self):
        """
        Target name (read-only property)
        """
        return self.__name

    @property
    def chans(self):
        """
        Target channel list (read-only property)
        """
        return self.__chans

    @property
    def nicks(self):
        """
        Target nick list (read-only property)
        """
        return self.__nicks

    @property
    def channel_messages_policy(self):
        """
        The target's channel messages policy (read-only property)
        """
        return self.__chan_messages_policy

    @property
    def private_messages_policy(self):
        """
        The target's private messages policy (read-only property)
        """
        return self.__priv_messages_policy

    @property
    def notifications_policy(self):
        """
        The target's notifications policy (read-only property)
        """
        return self.__notifications_policy

    @property
    def enabled(self):
        """
        The target's enabled status (bool property)
        """
        return self.__enabled

    @enabled.setter
    def enabled(self, value):
        """
        The target's enabled status (bool property)
        """
        self.__enabled = value

    def __repr__(self):
        """
        """
        last_message = 'never'
        if self.__last_message is not None:
            last_message = self.__last_message.strftime('%Y-%m-%d %H:%M:%S')
        return ('name: {0}\nurl: {1}\nenabled: {2}\nchannel_list: {3}\n'
                'nick_list: {4}\nchannel_messages_policy: {5}\n'
                'private_messages_policy: {6}\nnotifications_policy: {7}\n'
                'last message: {8}\nsocket timeout: {9}\nssl-version: {10}\n'
                'ciphers: {11}\ndisable hostname check: {12}\n'
                'debug: {13}\n\n'.format(
                    self.__name,
                    self.__url,
                    'yes' if self.__enabled else 'no',
                    ', '.join(self.__chans),
                    ', '.join(self.__nicks),
                    self.__chan_messages_policy,
                    self.__priv_messages_policy,
                    self.__notifications_policy,
                    last_message,
                    self.__socket_timeout,
                    self.__ssl_version,
                    self.__ssl_ciphers or 'auto',
                    'yes' if self.__disable_hostname_check else 'no',
                    'yes' if self.__debug else 'no'))

    def send_private_message_notification(self, values):
        """
        sends a private message notification to the represented target

        values: dict pupulated by the irc msg-handler
        """
        try:
            title = self.__fetch_formatted_str(self.__pm_title_template,
                                               values)
            message = self.__fetch_formatted_str(
                self.__pm_message_template,
                values)
            if not self.__send_beinc_message(title, message) and self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_private_message_notification-ERROR '
                    'for "{0}": __send_beinc_message -> False'.format(
                        self.__name))
        except Exception as e:
            if self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_private_message_notification-ERROR '
                    'for "{0}": {1}'.format(self.__name, e))

    def send_channel_message_notification(self, values):
        """
        sends a channel message notification to the represented target

        values: dict pupulated by the irc msg-handler
        """
        try:
            title = self.__fetch_formatted_str(self.__cm_title_template,
                                               values)
            message = self.__fetch_formatted_str(self.__cm_message_template,
                                                 values)
            if not self.__send_beinc_message(title, message) and self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_channel_message_notification-ERROR '
                    'for "{0}": __send_beinc_message -> False'.format(
                        self.__name))
        except Exception as e:
            if self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_channel_message_notification-ERROR '
                    'for "{0}": {1}'.format(self.__name, e))

    def send_notify_message_notification(self, values):
        """
        sends a notify message notification to the represented target

        values: dict pupulated by the irc msg-handler
        """
        try:
            title = self.__fetch_formatted_str(self.__nm_title_template,
                                               values)
            message = self.__fetch_formatted_str(self.__nm_message_template,
                                                 values)
            if not self.__send_beinc_message(title, message) and self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_notify_message_notification-ERROR '
                    'for "{0}": __send_beinc_message -> False'.format(
                        self.__name))
        except Exception as e:
            if self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_notify_message_notification-ERROR '
                    'for "{0}": {1}'.format(self.__name, e))

    def send_broadcast_notification(self, message):
        """
        sends a 'pure' broadcast / test message notification
        to the represented target

        message: a single message string
        """
        try:
            title = 'BEINC broadcast'
            if not self.__send_beinc_message(title, message) and self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_broadcast_notification-ERROR '
                    'for "{0}": __send_beinc_message -> False'.format(
                        self.__name))
        except Exception as e:
            if self.__debug:
                beinc_prnt(
                    'BEINC DEBUG: send_broadcast_notification-ERROR '
                    'for "{0}": {1}'.format(self.__name, e))

    def __context_setup(self):
        """
        """
        if self.__context is not None:
            return True
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_NONE
            if self.__cert_file:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(cafile=os.path.expanduser(
                    self.__cert_file))
                context.check_hostname = bool(
                    not self.__disable_hostname_check)
            if self.__ssl_ciphers and self.__ssl_ciphers != 'auto':
                context.set_ciphers(self.__ssl_ciphers)
            self.__context = context
            return True
        except ssl.SSLError as e:
            if self.__debug:
                beinc_prnt('BEINC DEBUG: SSL/TLS error: {0}\n'.format(e))
        except Exception as e:
            if self.__debug:
                beinc_prnt('BEINC DEBUG: Generic context error: {0}\n'.format(
                    e))
        self.__context = None
        return False

    def __fetch_formatted_str(self, template, values):
        """
        returns a formatted string by replacing the defined
        macros in 'template' the the corresponding values from 'values'

        values: dict
        template: str
        """
        timestamp = datetime.datetime.now().strftime(self.__timestamp_format)
        replacements = {'%S': values['server'],
                        '%s': values['source_nick'],
                        '%c': values['channel'],
                        '%m': values['message'],
                        '%t': timestamp,
                        '%p': u'BEINC',
                        '%n': values['own_nick']}
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template.encode('utf-8')

    def __send_beinc_message(self, title, message):
        """
        the function implements the BEINC "protocol" by generating a simple
        POST request
        """
        try:
            if self.__context is None and not self.__context_setup():
                return False
            response = urlopen(
                self.__url,
                data=urlencode(
                    (
                        ('resource_name', self.__name),
                        ('password', self.__password),
                        ('title', title),
                        ('message', message)
                        )).encode('utf-8'),
                timeout=self.__socket_timeout,
                context=self.__context)
            response_dict = json.loads(response.read().decode('utf-8'))
            if response.code != 200:
                raise socket.error(response_dict.get('message', ''))
            if self.__debug:
                beinc_prnt('BEINC DEBUG: Server responded: {0}'.format(
                    response_dict.get('message')))
            self.__last_message = datetime.datetime.now()
            return True
        except ssl.SSLError as e:
            if self.__debug:
                beinc_prnt('BEINC DEBUG: SSL/TLS error: {0}\n'.format(e))
        except socket.error as e:
            if self.__debug:
                beinc_prnt('BEINC DEBUG: Connection error: {0}\n'.format(e))
        except Exception as e:
            if self.__debug:
                beinc_prnt('BEINC DEBUG: Unable to send message: {0}\n'.format(
                    e))
        return False


def beinc_prnt(message_str):
    """
    wrapper around weechat.prnt
    """
    if global_values['use_current_buffer']:
        weechat.prnt(weechat.current_buffer(), message_str)
    else:
        weechat.prnt('', message_str)


def beinc_cmd_broadcast_handler(cmd_tokens):
    """
    handles: '/beinc broadcast' command actions
    """
    if not cmd_tokens:
        beinc_prnt('beinc broadcast <message>')
        return weechat.WEECHAT_RC_OK
    for target in target_list:
        if target.enabled:
            target.send_broadcast_notification(' '.join(cmd_tokens))
    return weechat.WEECHAT_RC_OK


def beinc_cmd_target_handler(cmd_tokens):
    """
    handles: '/beinc target' command actions
    """
    if not cmd_tokens or cmd_tokens[0] not in ['list', 'enable', 'disable']:
        beinc_prnt('beinc target [ list | enable <name> | disable <name> ]')
        return weechat.WEECHAT_RC_OK
    if cmd_tokens[0] == 'list':
        beinc_prnt('--- Targets ---')
        for target in target_list:
            beinc_prnt(str(target))
        beinc_prnt('---------------')
    elif cmd_tokens[0] == 'enable':
        if not cmd_tokens[1:]:
            beinc_prnt('missing a name-argument')
            return weechat.WEECHAT_RC_OK
        name = ' '.join(cmd_tokens[1:])
        for target in target_list:
            if target.name == name:
                target.enabled = True
                beinc_prnt('target "{0}" enabled'.format(name))
                break
        else:
            beinc_prnt('no matching target for "{0}"'.format(name))
    elif cmd_tokens[0] == 'disable':
        if not cmd_tokens[1:]:
            beinc_prnt('missing a name-argument')
            return weechat.WEECHAT_RC_OK
        name = ' '.join(cmd_tokens[1:])
        for target in target_list:
            if target.name == name:
                target.enabled = False
                beinc_prnt('target "{0}" disabled'.format(name))
                break
        else:
            beinc_prnt('no matching target for "{0}"'.format(name))
    return weechat.WEECHAT_RC_OK


def beinc_command(data, buffer_obj, args):
    """
    Callback function handling the Weechat's /beinc command
    """
    global enabled
    cmd_tokens = args.split()
    if not cmd_tokens:
        return weechat.WEECHAT_RC_OK
    if args == 'on':
        enabled = True
        beinc_prnt('BEINC on')
    elif args == 'off':
        enabled = False
        beinc_prnt('BEINC off')
    elif args == 'reload':
        beinc_prnt('Reloading BEINC...')
        beinc_init()
    elif cmd_tokens[0] in ('broadcast', 'test'):
        return beinc_cmd_broadcast_handler(cmd_tokens[1:])
    elif cmd_tokens[0] == 'target':
        return beinc_cmd_target_handler(cmd_tokens[1:])
    else:
        beinc_prnt('syntax: /beinc < on | off | reload |'
                   ' broadcast <text> | target <action> >')
    return weechat.WEECHAT_RC_OK


def beinc_privmsg_handler(data, signal, signal_data):
    """
    Callback function the *PRIVMSG* IRC messages hooked by Weechat
    """
    if not enabled:
        return weechat.WEECHAT_RC_OK
    prvmsg_dict = weechat.info_get_hashtable('irc_message_parse',
                                             {'message': signal_data})
    # packing the privmsg handler values
    ph_values = dict()
    ph_values['server'] = signal.split(',')[0]
    ph_values['own_nick'] = weechat.info_get('irc_nick', ph_values['server'])
    ph_values['channel'] = prvmsg_dict['arguments'].split(':')[0].strip()
    ph_values['source_nick'] = prvmsg_dict['nick']
    ph_values['message'] = ':'.join(
        prvmsg_dict['arguments'].split(':')[1:]).strip()
    if ph_values['channel'] == ph_values['own_nick']:
        # priv messages are handled here
        if not global_values['global_private_messages_policy']:
            return weechat.WEECHAT_RC_OK
        p_messages_policy = global_values['global_private_messages_policy']
        if p_messages_policy == BEINC_POLICY_LIST_ONLY and \
           '{0}.{1}'.format(
               ph_values['server'],
               ph_values['source_nick'].lower()
           ) not in global_values['global_nicks']:
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            p_messages_policy = target.private_messages_policy
            if p_messages_policy == BEINC_POLICY_ALL or (
                    p_messages_policy == BEINC_POLICY_LIST_ONLY and
                    '{0}.{1}'.format(
                        ph_values['server'],
                        ph_values['source_nick'].lower()) in target.nicks):
                target.send_private_message_notification(ph_values)
    elif ph_values['own_nick'].lower() in ph_values['message'].lower():
        # notify messages are handled here
        if not global_values['global_notifications_policy']:
            return weechat.WEECHAT_RC_OK
        notifications_policy = global_values['global_notifications_policy']
        if notifications_policy == BEINC_POLICY_LIST_ONLY and (
                '{0}.{1}'.format(
                    ph_values['server'],
                    ph_values['channel'].lower()
                ) not in global_values['global_chans']
        ):
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            if target.notifications_policy == BEINC_POLICY_ALL or (
                    target.notifications_policy == BEINC_POLICY_LIST_ONLY and
                    '{0}.{1}'.format(
                        ph_values['server'],
                        ph_values['channel'].lower()) in target.chans
            ):
                target.send_notify_message_notification(ph_values)
    elif global_values['global_channel_messages_policy']:
        # chan messages are handled here
        if not global_values['global_notifications_policy']:
            return weechat.WEECHAT_RC_OK
        c_messages_policy = global_values['global_channel_messages_policy']
        if c_messages_policy == BEINC_POLICY_LIST_ONLY and (
                '{0}.{1}'.format(
                    ph_values['server'],
                    ph_values['channel'].lower()
                ) not in global_values['global_chans']
        ):
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            c_messages_policy = target.channel_messages_policy
            if c_messages_policy == BEINC_POLICY_ALL or (
                    c_messages_policy == BEINC_POLICY_LIST_ONLY and
                    '{0}.{1}'.format(
                        ph_values['server'],
                        ph_values['channel'].lower()) in target.chans):
                target.send_channel_message_notification(ph_values)
    return weechat.WEECHAT_RC_OK


def beinc_init():
    """
    Ran every time the script is (re)loaded
    It loads the config (.json) file and (re)loads its contents into memory
    beinc_init() will disable all notifications on failure
    """

    global enabled
    global target_list
    global global_values

    # global chans/nicks sets are used to speed up the filtering
    global_values = dict()
    global_values['global_chans'] = set()
    global_values['global_nicks'] = set()
    target_list = list()
    custom_error = ''
    global_values['global_channel_messages_policy'] = False
    global_values['global_private_messages_policy'] = False
    global_values['global_notifications_policy'] = False
    global_values['use_current_buffer'] = False

    try:
        beinc_config_file_str = os.path.join(
            weechat.info_get('weechat_dir', ''),
            'beinc_weechat.json')
        beinc_prnt('Parsing {0}...'.format(beinc_config_file_str))
        custom_error = 'load error'
        with open(beinc_config_file_str, 'r') as fp:
            config_dict = json.load(fp, encoding='utf-8')
        custom_error = 'target parse error'
        global_values['use_current_buffer'] = bool(
            config_dict['irc_client'].get(
                'use_current_buffer', False))
        if config_dict.get('config_version',
                           0) != BEINC_CURRENT_CONFIG_VERSION:
            beinc_prnt('WARNING: The version of the config-file: {0} ({1}) '
                       'does not correspond to the latest version supported '
                       'by this program ({2})\nCheck beinc_config_sample.json '
                       'for the newest features!'.format(
                           beinc_config_file_str,
                           config_dict.get('config_version', 0),
                           BEINC_CURRENT_CONFIG_VERSION))
        for target in config_dict['irc_client']['targets']:
            try:
                new_target = WeechatTarget(target)
            except Exception as e:
                beinc_prnt('Unable to add target: {0}'.format(e))
                continue
            global_values['global_chans'].update(new_target.chans)
            global_values['global_nicks'].update(new_target.nicks)
            if new_target.channel_messages_policy:
                global_values['global_channel_messages_policy'] = True
            if new_target.private_messages_policy:
                global_values['global_private_messages_policy'] = True
            if new_target.notifications_policy:
                global_values['global_notifications_policy'] = True
            target_list.append(new_target)
            beinc_prnt('BEINC target "{0}" added'.format(new_target.name))
        beinc_prnt('Done!')
    except Exception as e:
        beinc_prnt('ERROR: unable to parse {0}: {1} - {2}\n'
                   'BEINC is now disabled'.format(
                       beinc_config_file_str, custom_error, e))
        enabled = False
        # do not return error / exit the script
        # in order to give a smoother opportunity to fix a 'broken' config
        return weechat.WEECHAT_RC_OK
    return weechat.WEECHAT_RC_OK


weechat.register(
    'beinc_weechat',
    __author__,
    __version__,
    __license__,
    'Blackmore\'s Extended IRC Notification Collection (Weechat Client)',
    '',
    '')
version = weechat.info_get('version_number', '') or 0
if int(version) < 0x00040000:
    weechat.prnt('', 'WeeChat version >= 0.4.0 is required to run beinc')
else:
    weechat.hook_command('beinc',
                         'BEINC command', ('< broadcast <message> | on | off |'
                                           ' reload | target <action> >'),
                         ('Available target actions:\n'
                          'disable <target name>\nenable <target name>\nlist'),
                         'None',
                         'beinc_command',
                         '')
    weechat.hook_signal('*,irc_in2_privmsg', 'beinc_privmsg_handler', '')
    beinc_init()
    weechat.prnt('', 'beinc initiated!')
