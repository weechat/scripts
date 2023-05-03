# -*- coding: utf-8 -*-

# Blackmore's Enhanced IRC-Notification Collection (BEINC) v4.3
# Copyright (C) 2013-2022 Simeon Simeonov

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
"""BEINC client for Weechat"""
import datetime
import io
import json
import os
import socket
import ssl
import urllib.parse
import urllib.request

import weechat

__author__ = 'Simeon Simeonov'
__version__ = '4.3'
__license__ = 'GPL3'


enabled = True
global_values = {}

# few constants #
BEINC_POLICY_NONE = 0
BEINC_POLICY_ALL = 1
BEINC_POLICY_LIST_ONLY = 2
BEINC_CURRENT_CONFIG_VERSION = 2


class WeechatTarget:
    """
    The target (destination) class

    Each remote destination is represented as a WeechatTarget object
    """

    def __init__(self, target_dict):
        """
        :param target_dict: The config-dict node that represents this instance
        :type target_dict: dict
        """
        self._name = target_dict.get('name', '')
        if self._name == '':
            raise Exception('"name" not defined for target')
        self._url = target_dict.get('target_url', '')
        if self._url == '':
            raise Exception('"target_url" not defined for target')
        self._password = target_dict.get('target_password', '')
        self._pm_title_template = target_dict.get(
            'pm_title_template', '%s @ %S'
        )
        self._pm_message_template = target_dict.get(
            'pm_message_template', '%m'
        )
        self._cm_title_template = target_dict.get(
            'cm_title_template', '%c @ %S'
        )
        self._cm_message_template = target_dict.get(
            'cm_message_template', '%s -> %m'
        )
        self._nm_title_template = target_dict.get(
            'nm_title_template', '%c @ %S'
        )
        self._nm_message_template = target_dict.get(
            'nm_message_template', '%s -> %m'
        )
        self._chans = set(target_dict.get('channel_list', []))
        self._nicks = set(target_dict.get('nick_list', []))
        self._chan_messages_policy = int(
            target_dict.get('channel_messages_policy', BEINC_POLICY_LIST_ONLY)
        )
        self._priv_messages_policy = int(
            target_dict.get('private_messages_policy', BEINC_POLICY_ALL)
        )
        self._notifications_policy = int(
            target_dict.get('notifications_policy', BEINC_POLICY_ALL)
        )
        self._cert_file = target_dict.get('target_cert_file')
        self._timestamp_format = target_dict.get(
            'target_timestamp_format', '%H:%M:%S'
        )
        self._debug = bool(target_dict.get('debug', False))
        self._enabled = bool(target_dict.get('enabled', True))
        self._socket_timeout = int(target_dict.get('socket_timeout', 3))
        self._ssl_ciphers = target_dict.get('ssl_ciphers', '')
        self._disable_hostname_check = bool(
            target_dict.get('disable-hostname-check', False)
        )
        self._ssl_version = target_dict.get('ssl_version', 'auto')
        self._last_message = None  # datetime.datetime instance
        self._context = None
        self._context_setup()

    @property
    def name(self):
        """Target name (read-only property)"""
        return self._name

    @property
    def chans(self):
        """Target channel list (read-only property)"""
        return self._chans

    @property
    def nicks(self):
        """Target nick list (read-only property)"""
        return self._nicks

    @property
    def channel_messages_policy(self):
        """The target's channel messages policy (read-only property)"""
        return self._chan_messages_policy

    @property
    def private_messages_policy(self):
        """The target's private messages policy (read-only property)"""
        return self._priv_messages_policy

    @property
    def notifications_policy(self):
        """The target's notifications policy (read-only property)"""
        return self._notifications_policy

    @property
    def enabled(self):
        """The target's enabled status (bool property)"""
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        """The target's enabled status (bool property)"""
        self._enabled = value

    def __repr__(self):
        """repr() implementation"""
        last_message = 'never'
        if self._last_message is not None:
            last_message = self._last_message.strftime('%Y-%m-%d %H:%M:%S')
        return (
            f'name: {self._name}\nurl: {self._url}\n'
            f"enabled: {'yes' if self._enabled else 'no'}\n"
            f"channel_list: {', '.join(self._chans)}\n"
            f"nick_list: {', '.join(self._nicks)}\n"
            f'channel_messages_policy: {self._chan_messages_policy}\n'
            f'private_messages_policy: {self._priv_messages_policy}\n'
            f'notifications_policy: {self._notifications_policy}\n'
            f'last message: {last_message}\n'
            f'socket timeout: {self._socket_timeout}\n'
            f'ssl-version: {self._ssl_version}\n'
            f"ciphers: {self._ssl_ciphers or 'auto'}\n"
            "disable hostname check: "
            f"{'yes' if self._disable_hostname_check else 'no'}\n"
            f"debug: {'yes' if self._debug else 'no'}\n\n"
        )

    def send_private_message_notification(self, values):
        """
        Sends a private message notification to the represented target

        :param value: Dict pupulated by the irc msg-handler
        :type value: dict
        """
        try:
            title = self._fetch_formatted_str(self._pm_title_template, values)
            message = self._fetch_formatted_str(
                self._pm_message_template,
                values,
            )
            if not self._send_beinc_message(title, message) and self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_private_message_notification-ERROR '
                    f'for "{self._name}": _send_beinc_message -> False'
                )
        except Exception as e:
            if self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_private_message_notification-ERROR '
                    f'for "{self._name}": {e}'
                )

    def send_channel_message_notification(self, values):
        """
        Sends a channel message notification to the represented target

        :param value: Dict pupulated by the irc msg-handler
        :type value: dict
        """
        try:
            title = self._fetch_formatted_str(self._cm_title_template, values)
            message = self._fetch_formatted_str(
                self._cm_message_template, values
            )
            if not self._send_beinc_message(title, message) and self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_channel_message_notification-ERROR '
                    f'for "{self._name}": _send_beinc_message -> False'
                )
        except Exception as e:
            if self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_channel_message_notification-ERROR '
                    f'for "{self._name}": {e}'
                )

    def send_notify_message_notification(self, values):
        """
        Sends a notify message notification to the represented target

        :param value: Dict pupulated by the irc msg-handler
        :type value: dict
        """
        try:
            title = self._fetch_formatted_str(self._nm_title_template, values)
            message = self._fetch_formatted_str(
                self._nm_message_template, values
            )
            if not self._send_beinc_message(title, message) and self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_notify_message_notification-ERROR '
                    f'for "{self._name}": _send_beinc_message -> False'
                )
        except Exception as e:
            if self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_notify_message_notification-ERROR '
                    f'for "{self._name}": {e}'
                )

    def send_broadcast_notification(self, message):
        """
        Sends a 'pure' broadcast / test message notification
        to the represented target

        :param message: A single message string
        :type message: str
        """
        try:
            title = 'BEINC broadcast'
            if not self._send_beinc_message(title, message) and self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_broadcast_notification-ERROR '
                    f'for "{self._name}": _send_beinc_message -> False'
                )
        except Exception as e:
            if self._debug:
                beinc_prnt(
                    f'BEINC DEBUG: send_broadcast_notification-ERROR '
                    f'for "{self._name}": {e}'
                )

    def _context_setup(self):
        """Sets up the SSL context"""
        if self._context is not None:
            return True
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self._cert_file:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_verify_locations(
                    cafile=os.path.expanduser(self._cert_file)
                )
                context.check_hostname = bool(not self._disable_hostname_check)
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            if self._ssl_ciphers and self._ssl_ciphers != 'auto':
                context.set_ciphers(self._ssl_ciphers)
            self._context = context
            return True
        except ssl.SSLError as e:
            if self._debug:
                beinc_prnt(f'BEINC DEBUG: SSL/TLS error: {e}\n')
        except Exception as e:
            if self._debug:
                beinc_prnt(f'BEINC DEBUG: Generic context error: {e}\n')
        self._context = None
        return False

    def _fetch_formatted_str(self, template, values):
        """
        Returns a formatted string by replacing the defined
        macros in 'template' the the corresponding values from 'values'

        :param template: The template to use
        :type template: str

        :param values: The values dict
        :type values: dict

        :return: The formatted string
        :rtype: str
        """
        timestamp = datetime.datetime.now().strftime(self._timestamp_format)
        replacements = {
            '%S': values['server'],
            '%s': values['source_nick'],
            '%c': values['channel'],
            '%m': values['message'],
            '%t': timestamp,
            '%p': 'BEINC',
            '%n': values['own_nick'],
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    def _send_beinc_message(self, title, message):
        """
        The method implements the BEINC "protocol" by generating a simple
        POST request

        :param title: The title
        :type title: str

        :param message: The message
        :type message: str

        :return: The status
        :rtype: bool
        """
        try:
            if self._context is None and not self._context_setup():
                return False
            response = urllib.request.urlopen(
                self._url,
                data=urllib.parse.urlencode(
                    (
                        ('resource_name', self._name),
                        ('password', self._password),
                        ('title', title),
                        ('message', message),
                    )
                ).encode('utf-8'),
                timeout=self._socket_timeout,
                context=self._context,
            )
            response_dict = json.loads(response.read().decode('utf-8'))
            if response.code != 200:
                raise socket.error(response_dict.get('message', ''))
            if self._debug:
                beinc_prnt(
                    "BEINC DEBUG: Server responded: "
                    f"{response_dict.get('message')}"
                )
            self._last_message = datetime.datetime.now()
            return True
        except ssl.SSLError as e:
            if self._debug:
                beinc_prnt(f'BEINC DEBUG: SSL/TLS error: {e}\n')
        except socket.error as e:
            if self._debug:
                beinc_prnt(f'BEINC DEBUG: Connection error: {e}\n')
        except Exception as e:
            if self._debug:
                beinc_prnt(f'BEINC DEBUG: Unable to send message: {e}\n')
        return False


def beinc_prnt(message_str):
    """wrapper around weechat.prnt"""
    if global_values['use_current_buffer']:
        weechat.prnt(weechat.current_buffer(), message_str)
    else:
        weechat.prnt('', message_str)


def beinc_cmd_broadcast_handler(cmd_tokens):
    """handles: '/beinc broadcast' command actions"""
    if not cmd_tokens:
        beinc_prnt('beinc broadcast <message>')
        return weechat.WEECHAT_RC_OK
    for target in target_list:
        if target.enabled:
            target.send_broadcast_notification(' '.join(cmd_tokens))
    return weechat.WEECHAT_RC_OK


def beinc_cmd_target_handler(cmd_tokens):
    """handles: '/beinc target' command actions"""
    if not cmd_tokens or cmd_tokens[0] not in ['list', 'enable', 'disable']:
        beinc_prnt('beinc target [ list | enable <name> | disable <name> ]')
        return weechat.WEECHAT_RC_OK
    if cmd_tokens[0] == 'list':
        beinc_prnt('--- Globals ---')
        for key, value in global_values.items():
            beinc_prnt(f'{key} -> {str(value)}')
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
                beinc_prnt(f'target "{name}" enabled')
                break
        else:
            beinc_prnt(f'no matching target for "{name}"')
    elif cmd_tokens[0] == 'disable':
        if not cmd_tokens[1:]:
            beinc_prnt('missing a name-argument')
            return weechat.WEECHAT_RC_OK
        name = ' '.join(cmd_tokens[1:])
        for target in target_list:
            if target.name == name:
                target.enabled = False
                beinc_prnt(f'target "{name}" disabled')
                break
        else:
            beinc_prnt(f'no matching target for "{name}"')
    return weechat.WEECHAT_RC_OK


def beinc_command(data, buffer_obj, args):
    """Callback function handling the Weechat's /beinc command"""
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
        beinc_prnt(
            'syntax: /beinc < on | off | reload |'
            ' broadcast <text> | target <action> >'
        )
    return weechat.WEECHAT_RC_OK


def beinc_privmsg_handler(data, signal, signal_data):
    """Callback function the *PRIVMSG* IRC messages hooked by Weechat"""
    if not enabled:
        return weechat.WEECHAT_RC_OK
    prvmsg_dict = weechat.info_get_hashtable(
        'irc_message_parse', {'message': signal_data}
    )
    # packing the privmsg handler values
    ph_values = {}
    ph_values['server'] = signal.split(',')[0]
    ph_values['own_nick'] = weechat.info_get('irc_nick', ph_values['server'])
    ph_values['channel'] = prvmsg_dict['arguments'].split(':')[0].strip()
    ph_values['source_nick'] = prvmsg_dict['nick']
    ph_values['message'] = ':'.join(
        prvmsg_dict['arguments'].split(':')[1:]
    ).strip()
    if ph_values['channel'] == ph_values['own_nick']:
        # priv messages are handled here
        if not global_values['global_private_messages_policy']:
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            p_messages_policy = target.private_messages_policy
            if p_messages_policy == BEINC_POLICY_ALL or (
                p_messages_policy == BEINC_POLICY_LIST_ONLY
                and f"{ph_values['server']}.{ph_values['source_nick'].lower()}"
                in target.nicks
            ):
                target.send_private_message_notification(ph_values)
    elif ph_values['own_nick'].lower() in ph_values['message'].lower():
        # notify messages are handled here
        if not global_values['global_notifications_policy']:
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            if target.notifications_policy == BEINC_POLICY_ALL or (
                target.notifications_policy == BEINC_POLICY_LIST_ONLY
                and f"{ph_values['server']}.{ph_values['channel'].lower()}"
                in target.chans
            ):
                target.send_notify_message_notification(ph_values)
    elif global_values['global_channel_messages_policy']:
        # chan messages are handled here
        if not global_values['global_notifications_policy']:
            return weechat.WEECHAT_RC_OK
        for target in target_list:
            if not target.enabled:
                continue
            c_messages_policy = target.channel_messages_policy
            if c_messages_policy == BEINC_POLICY_ALL or (
                c_messages_policy == BEINC_POLICY_LIST_ONLY
                and f"{ph_values['server']}.{ph_values['channel'].lower()}"
                in target.chans
            ):
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
    global_values = {}
    target_list = []
    custom_error = ''
    global_values['global_channel_messages_policy'] = False
    global_values['global_private_messages_policy'] = False
    global_values['global_notifications_policy'] = False
    global_values['use_current_buffer'] = False

    try:
        beinc_config_file_str = os.path.join(
            weechat.info_get('weechat_dir', ''),
            'beinc_weechat.json',
        )
        beinc_prnt(f'Parsing {beinc_config_file_str}...')
        custom_error = 'load error'
        with io.open(beinc_config_file_str, 'r', encoding='utf-8') as fp:
            config_dict = json.load(fp)
        custom_error = 'target parse error'
        global_values['use_current_buffer'] = bool(
            config_dict['irc_client'].get('use_current_buffer', False)
        )
        if (
            config_dict.get('config_version', 0)
            != BEINC_CURRENT_CONFIG_VERSION
        ):
            beinc_prnt(
                "WARNING: The version of the config-file: "
                f"{beinc_config_file_str} "
                f"({config_dict.get('config_version', 0)}) "
                "does not correspond to the latest version supported "
                f"by this program ({BEINC_CURRENT_CONFIG_VERSION})\n"
                "Check beinc_config_sample.json for the newest features!"
            )
        for target in config_dict['irc_client']['targets']:
            try:
                new_target = WeechatTarget(target)
            except Exception as e:
                beinc_prnt(f'Unable to add target: {e}')
                continue
            if new_target.channel_messages_policy:
                global_values['global_channel_messages_policy'] = True
            if new_target.private_messages_policy:
                global_values['global_private_messages_policy'] = True
            if new_target.notifications_policy:
                global_values['global_notifications_policy'] = True
            target_list.append(new_target)
            beinc_prnt(f'BEINC target "{new_target.name}" added')
        beinc_prnt('Done!')
    except Exception as e:
        beinc_prnt(
            f'ERROR: unable to parse {beinc_config_file_str}: '
            f'{custom_error} - {e}\nBEINC is now disabled'
        )
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
    '',
)
version = weechat.info_get('version_number', '') or 0
if int(version) < 0x00040000:
    weechat.prnt('', 'WeeChat version >= 0.4.0 is required to run beinc')
else:
    weechat.hook_command(
        'beinc',
        'BEINC command',
        '< broadcast <message> | on | off | reload | target <action> >',
        (
            'Available target actions:\n'
            'disable <target name>\nenable <target name>\nlist'
        ),
        'None',
        'beinc_command',
        '',
    )
    weechat.hook_signal('*,irc_in2_privmsg', 'beinc_privmsg_handler', '')
    beinc_init()
    weechat.prnt('', 'beinc initiated!')
