# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 p3lim <weechat@p3lim.net>
#
# https://github.com/p3lim/weechat-pushjet

try:
	import weechat
except ImportError:
	from sys import exit
	print('This script has to run under WeeChat (https://weechat.org/).')
	exit(1)

from urllib import urlencode

SCRIPT_NAME = 'pushjet'
SCRIPT_AUTHOR = 'p3lim'
SCRIPT_VERSION = '0.1.0'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Send highlights and mentions through Pushjet.io'

SETTINGS = {
	'host': (
		'https://api.pushjet.io',
		'host for the pushjet api'),
	'secret': (
		'',
		'secret for the pushjet api'),
	'level': (
		'4',
		'severity level for the message, from 1 to 5 (low to high)'),
	'timeout': (
		'30',
		'timeout for the message sending in seconds (>= 1)'),
	'separator': (
		': ',
		'separator between nick and message in notifications'),
	'notify_on_highlight': (
		'on',
		'push notifications for highlights in buffers (on/off)'),
	'notify_on_privmsg': (
		'on',
		'push notifications for private messages (on/off)'),
	'notify_when': (
		'always',
		'when to push notifications (away/detached/always/never)'),
	'ignore_buffers': (
		'',
		'comma-separated list of buffers to ignore'),
	'ignore_nicks': (
		'',
		'comma-separated list of users to not push notifications from'),
}

def send_message(title, message):
	secret = weechat.config_get_plugin('secret')
	if secret != '':
		data = {
			'secret': secret,
			'level': int(weechat.config_get_plugin('level')),
			'title': title,
			'message': message,
		}

		host = weechat.config_get_plugin('host').rstrip('/') + '/message'
		timeout = int(weechat.config_get_plugin('timeout')) * 1000

		if timeout <= 0:
			timeout = 1

		data = urlencode(data)
		cmd = 'python -c \'from urllib2 import Request, urlopen; r = urlopen(Request("%s", "%s")); print r.getcode()\'' % (host, data)
		weechat.hook_process(cmd, timeout, 'send_message_callback', '')

def send_message_callback(data, command, return_code, out, err):
	if return_code != 0:
		# something went wrong
		return weechat.WEECHAT_RC_ERROR

	return weechat.WEECHAT_RC_OK

def get_sender(tags, prefix):
	# attempt to find sender from tags
	# nicks are always prefixed with 'nick_'
	for tag in tags:
		if tag.startswith('nick_'):
			return tag[5:]

	# fallback method to find sender from prefix
	# nicks in prefixes are prefixed with optional modes (e.g @ for operators)
	# so we have to strip away those first, if they exist
	if prefix.startswith(('~', '&', '@', '%', '+', '-', ' ')):
		return prefix[1:]

	return prefix

def get_buffer_names(buffer):
	buffer_names = []
	buffer_names.append(weechat.buffer_get_string(buffer, 'short_name'))
	buffer_names.append(weechat.buffer_get_string(buffer, 'name'))
	return buffer_names

def should_send(buffer, tags, nick, highlighted):
	if not nick:
		# a nick is required to form a correct message, bail
		return False

	if highlighted:
		if weechat.config_get_plugin('notify_on_highlight') != 'on':
			# notifying on highlights is disabled, bail
			return False
	elif weechat.buffer_get_string(buffer, 'localvar_type') == 'private':
		if weechat.config_get_plugin('notify_on_privmsg') != 'on':
			# notifying on private messages is disabled, bail
			return False
	else:
		# not a highlight or private message, bail
		return False

	notify_when = weechat.config_get_plugin('notify_when')
	if notify_when == 'never':
		# user has opted to not be notified, bail
		return False
	elif notify_when == 'away':
		# user has opted to only be notified when away
		infolist_args = (
			weechat.buffer_get_string(buffer, 'localvar_channel'),
			weechat.buffer_get_string(buffer, 'localvar_server'),
			weechat.buffer_get_string(buffer, 'localvar_nick')
		)

		if not None in infolist_args:
			infolist = weechat.infolist_get('irc_nick', '', ','.join(infolist_args))
			if infolist:
				away_status = weechat.infolist_integer(infolist, 'away')
				if not away_status:
					# user is not away, bail
					return False
	elif notify_when == 'detached':
		# user has opted to only be notified when detached (relays)
		num_relays = weechat.info_get('relay_client_count', 'connected')
		if num_relays == 0:
			# no relays connected, bail
			return False

	if nick == weechat.buffer_get_string(buffer, 'localvar_nick'):
		# the sender was the current user, bail
		return False

	if nick in weechat.config_get_plugin('ignore_nicks').split(','):
		# the sender was on the ignore list, bail
		return False

	for buffer_name in get_buffer_names(buffer):
		if buffer_name in weechat.config_get_plugin('ignore_buffers').split(','):
			# the buffer was on the ignore list, bail
			return False

	return True

def message_callback(data, buffer, date, tags, displayed, highlight, prefix, message):
	nick = get_sender(tags, prefix)

	if should_send(buffer, tags, nick, int(highlight)):
		message = '%s%s%s' % (nick, weechat.config_get_plugin('separator'), message)

		if int(highlight):
			buffer_names = get_buffer_names(buffer)
			send_message(buffer_names[0] or buffer_names[1], message)
		else:
			send_message('Private Message', message)

	return weechat.WEECHAT_RC_OK

# register plugin
weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

# grab all messages in any buffer
weechat.hook_print('', '', '', 1, 'message_callback', '')

# register configuration defaults
for option, value in SETTINGS.items():
	if not weechat.config_is_set_plugin(option):
		weechat.config_set_plugin(option, value[0])

	weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
