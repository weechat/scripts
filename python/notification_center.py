# https://github.com/sindresorhus/weechat-notification-center
# Requires `pip install pync`

import os
import datetime
import weechat
from pync import Notifier


SCRIPT_NAME = 'notification_center'
SCRIPT_AUTHOR = 'Sindre Sorhus <sindresorhus@gmail.com>'
SCRIPT_VERSION = '1.3.0'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Pass highlights and private messages to the OS X 10.8+ Notification Center'
WEECHAT_ICON = os.path.expanduser('~/.weechat/weechat.png')

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

DEFAULT_OPTIONS = {
	'show_highlights': 'on',
	'show_private_message': 'on',
	'show_message_text': 'on',
	'sound': 'off',
	'sound_name': 'Pong',
	'activate_bundle_id': 'com.apple.Terminal',
	'ignore_old_messages': 'off',
}

for key, val in DEFAULT_OPTIONS.items():
	if not weechat.config_is_set_plugin(key):
		weechat.config_set_plugin(key, val)

weechat.hook_print('', 'irc_privmsg', '', 1, 'notify', '')

def notify(data, buffer, date, tags, displayed, highlight, prefix, message):
	# ignore if it's yourself
	own_nick = weechat.buffer_get_string(buffer, 'localvar_nick')
	if prefix == own_nick or prefix == ('@%s' % own_nick):
		return weechat.WEECHAT_RC_OK

	# ignore messages older than the configured theshold (such as ZNC logs) if enabled
	if weechat.config_get_plugin('ignore_old_messages') == 'on':
		message_time = datetime.datetime.utcfromtimestamp(int(date))
		now_time = datetime.datetime.utcnow()

		# ignore if the message is greater than 5 seconds old
		if (now_time - message_time).seconds > 5:
			return weechat.WEECHAT_RC_OK

	# passing `None` or `''` still plays the default sound so we pass a lambda instead
	sound = weechat.config_get_plugin('sound_name') if weechat.config_get_plugin('sound') == 'on' else lambda:_
	activate_bundle_id = weechat.config_get_plugin('activate_bundle_id')
	if weechat.config_get_plugin('show_highlights') == 'on' and int(highlight):
		channel = weechat.buffer_get_string(buffer, 'localvar_channel')
		if weechat.config_get_plugin('show_message_text') == 'on':
			Notifier.notify(message, title='%s %s' % (prefix, channel), sound=sound, appIcon=WEECHAT_ICON, activate=activate_bundle_id)
		else:
			Notifier.notify('In %s by %s' % (channel, prefix), title='Highlighted Message', sound=sound, appIcon=WEECHAT_ICON, activate=activate_bundle_id)
	elif weechat.config_get_plugin('show_private_message') == 'on' and 'notify_private' in tags:
		if weechat.config_get_plugin('show_message_text') == 'on':
			Notifier.notify(message, title='%s [private]' % prefix, sound=sound, appIcon=WEECHAT_ICON, activate=activate_bundle_id)
		else:
			Notifier.notify('From %s' % prefix, title='Private Message', sound=sound, appIcon=WEECHAT_ICON, activate=activate_bundle_id)
	return weechat.WEECHAT_RC_OK
