# -*- coding: utf-8 -*-
#
# IRCrypt: Secure Encryption Layer Atop IRC
# =========================================
#
# Copyright (C) 2013-2014
#    Lars Kiesow   <lkiesow@uos.de>
#    Sven Haardiek <sven@haardiek.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#
#
# == About ==================================================================
#
#  The weechat IRCrypt plug-in will send messages encrypted to all channels for
#  which a passphrase is set. A channel can either be a regular IRC multi-user
#  channel (i.e. #IRCrypt) or another users nickname.
#
# == Project ================================================================
#
# This plug-in is part of the IRCrypt project. For mor information or to
# participate, please visit
#
#   https://github.com/IRCrypt
#
#
# To report bugs, make suggestions, etc. for this particular plug-in, please
# have a look at:
#
#   https://github.com/IRCrypt/ircrypt-weechat
#


import weechat, string, os, subprocess, base64, time

# Constants used in this script
SCRIPT_NAME    = 'ircrypt'
SCRIPT_AUTHOR  = 'Sven Haardiek <sven@haardiek.de>, Lars Kiesow <lkiesow@uos.de>'
SCRIPT_VERSION = '1.0'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'IRCrypt: Encryption layer for IRC'
SCRIPT_HELP_TEXT = '''
%(bold)sIRCrypt command options: %(normal)s
list                                                    List set keys, public key ids and ciphers
set-key            [-server <server>] <target> <key>    Set key for target
remove-key         [-server <server>] <target>          Remove key for target
set-cipher         [-server <server>] <target> <cipher> Set specific cipher for target
remove-cipher      [-server <server>] <target>          Remove specific cipher for target
plain              [-server <s>] [-channel <ch>] <msg>  Send unencrypted message

%(bold)sExamples: %(normal)s
Set the key for a channel:
   /ircrypt set-key -server freenet #IRCrypt key
Remove the key:
   /ircrypt remove-key #IRCrypt
Switch to a specific cipher for a channel:
   /ircrypt set-cipher -server freenode #IRCrypt TWOFISH
Unset the specific cipher for a channel:
   /ircrypt remove-cipher #IRCrypt
Send unencrypted “Hello” to current channel
   /ircrypt plain Hello

%(bold)sConfiguration: %(normal)s
Tip: You can list all options and what they are currently set to by executing:
   /set ircrypt.*
%(bold)sircrypt.marker.encrypted %(normal)s
   If you add 'ircrypt' to weechat.bar.status.items, these option will set a
   string which is displayed in the status bar of an encrypted channels,
   indicating that the current channel is encrypted.
   If “{{cipher}}” is used as part of this string, it will be replaced by the
   cipher currently used by oneself for that particular channel.
   It is woth noting that you probably don't want to replace the whole value of
   that option but extend it instead in a way like:
      /set weechat.bar.status.items {{currentContent}},ircrypt
%(bold)sircrypt.marker.unencrypted %(normal)s
   This option will set a string which is displayed before each message that is
   send unencrypted in a channel for which a key is set. So you know when
   someone is talking to you without encryption.
%(bold)sircrypt.general.binary %(normal)s
   This will set the GnuPG binary used for encryption and decryption. IRCrypt
   will try to set this automatically.
''' % {'bold':weechat.color('bold'), 'normal':weechat.color('-bold')}

MAX_PART_LEN     = 300
MSG_PART_TIMEOUT = 300 # 5min


# Global variables and memory used to store message parts, pending requests,
# configuration options, keys, etc.
ircrypt_msg_memory       = {}
ircrypt_config_file      = None
ircrypt_config_section   = {}
ircrypt_config_option    = {}
ircrypt_keys             = {}
ircrypt_cipher           = {}
ircrypt_message_plain    = {}


class MessageParts:
	'''Class used for storing parts of messages which were split after
	encryption due to their length.'''

	modified = 0
	last_id  = None
	message  = ''

	def update(self, id, msg):
		'''This method updates an already existing message part by adding a new
		part to the old ones and updating the identifier of the latest received
		message part.
		'''
		# Check if id is correct. If not, throw away old parts:
		if self.last_id and self.last_id != id+1:
			self.message = ''
		# Check if the are old message parts which belong due to their old age
		# probably not to this message:
		if time.time() - self.modified > MSG_PART_TIMEOUT:
			self.message = ''
		self.last_id = id
		self.message = msg + self.message
		self.modified = time.time()


def ircrypt_gnupg(stdin, *args):
	'''Try to execute gpg with given input and options.

	:param stdin: Input for GnuPG
	:param  args: Additional command line options for GnuPG
	:returns:     Tuple containing returncode, stdout and stderr
	'''
	gnupg = weechat.config_string(weechat.config_get('ircrypt.general.binary'))
	if not gnupg:
		return (99, '', 'GnuPG could not be found')
	p = subprocess.Popen(
			[gnupg, '--batch',  '--no-tty'] + list(args),
			stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = p.communicate(stdin)
	return (p.returncode, out, err)


def ircrypt_split_msg(cmd, pre, msg):
	'''Convert encrypted message in MAX_PART_LEN sized blocks
	'''
	msg = msg.rstrip()
	return '\n'.join(['%s:>%s-%i %s' %
		(cmd, pre, i // MAX_PART_LEN, msg[i:i+MAX_PART_LEN])
		for i in range(0, len(msg), MAX_PART_LEN)][::-1])


def ircrypt_error(msg, buf):
	'''Print errors to a given buffer. Errors are printed in red and have the
	weechat error prefix.
	'''
	weechat.prnt(buf, weechat.prefix('error') + weechat.color('red') +
			('\n' + weechat.color('red')).join(msg.split('\n')))


def ircrypt_warn(msg, buf=''):
	'''Print warnings. If no buffer is set, the default weechat buffer is used.
	Warnin are printed in gray without marker.
	'''
	weechat.prnt(buf, weechat.color('gray') +
			('\n' + weechat.color('gray')).join(msg.split('\n')))


def ircrypt_info(msg, buf=None):
	'''Print ifo message to specified buffer. If no buffer is set, the current
	foreground buffer is used to print the message.
	'''
	if buf is None:
		buf = weechat.current_buffer()
	weechat.prnt(buf, msg)


def ircrypt_decrypt_hook(data, msgtype, server, args):
	'''Hook for incomming PRVMSG commands.
	This method will parse the input, check if it is an encrypted message and
	call the appropriate decryption methods if necessary.

	:param data:
	:param msgtype:
	:param server: IRC server the message comes from.
	:param args: IRC command line-
	'''
	info = weechat.info_get_hashtable('irc_message_parse', { 'message': args })

	# Check if channel is own nick and if change channel to nick of sender
	if info['channel'][0] not in '#&':
		info['channel'] = info['nick']

	# Get key
	key = ircrypt_keys.get(('%s/%s' % (server, info['channel'])).lower())

	# Return everything as it is if we have no key
	if not key:
		return args

	if not '>CRY-' in args:
		# if key exisits and no >CRY not part of message flag message as unencrypted
		pre, message = args.split(' :', 1)
		marker = weechat.config_string(ircrypt_config_option['unencrypted'])
		return '%s :%s %s' % (pre, marker, message)

	# if key exists and >CRY part of message start symmetric encryption
	pre, message    = args.split('>CRY-', 1)
	number, message = message.split(' ', 1 )

	# Get key for the message memory
	catchword = '%s.%s.%s' % (server, info['channel'], info['nick'])

	# Decrypt only if we got last part of the message
	# otherwise put the message into a global memory and quit
	if int(number) != 0:
		if not catchword in ircrypt_msg_memory:
			ircrypt_msg_memory[catchword] = MessageParts()
		ircrypt_msg_memory[catchword].update(int(number), message)
		return ''

	# Get whole message
	try:
		message = message + ircrypt_msg_memory[catchword].message
		del ircrypt_msg_memory[catchword]
	except KeyError:
		pass

	# Get message buffer in case we need to print an error
	buf = weechat.buffer_search('irc', '%s.%s' % (server,info['channel']))

	# Decode base64 encoded message
	try:
		message = base64.b64decode(message)
	except:
		ircrypt_error('Could not Base64 decode message.', buf)
		return args

	# Decrypt
	try:
		message = (key).encode('utf-8') + b'\n' + message
	except:
		# For Python 2.x
		message = key + b'\n' + message
	(ret, out, err) = ircrypt_gnupg(message,
			'--passphrase-fd', '-', '-q', '-d')

	# Get and print GPG errors/warnings
	if ret:
		ircrypt_error(err.decode('utf-8'), buf)
		return args
	if err:
		ircrypt_warn(err.decode('utf-8'))

	return pre + out.decode('utf-8')


def ircrypt_encrypt_hook(data, msgtype, server, args):
	'''Hook for outgoing PRVMSG commands.
	This method will call the appropriate methods for encrypting the outgoing
	messages either symmetric or asymmetric

	:param data:
	:param msgtype:
	:param server: IRC server the message comes from.
	:param args: IRC command line-
	'''
	info = weechat.info_get_hashtable("irc_message_parse", { "message": args })

	# check if this message is to be send as plain text
	plain = ircrypt_message_plain.get('%s/%s' % (server, info['channel']))
	if plain:
		del ircrypt_message_plain['%s/%s' % (server, info['channel'])]
		if (plain[0] - time.time()) < 5 \
				and args == 'PRIVMSG %s :%s' % (info['channel'], plain[1]):
			args = args.replace('PRIVMSG %s :%s ' % (
				info['channel'],
				weechat.config_string(ircrypt_config_option['unencrypted'])),
				'PRIVMSG %s :' % info['channel'])
			return args

	# check symmetric key
	key = ircrypt_keys.get(('%s/%s' % (server, info['channel'])).lower())
	if not key:
		# No key -> don't encrypt
		return args

	# Get cipher
	cipher = ircrypt_cipher.get(('%s/%s' % (server, info['channel'])).lower(),
			weechat.config_string(ircrypt_config_option['sym_cipher']))
	# Get prefix and message
	pre, message = args.split(':', 1)

	# encrypt message
	try:
		inp = key.encode('utf-8') + b'\n' + message.encode('utf-8')
	except:
		inp = key + b'\n' + message
	(ret, out, err) = ircrypt_gnupg(inp,
			'--symmetric', '--cipher-algo', cipher, '--passphrase-fd', '-')

	# Get and print GPG errors/warnings
	if ret:
		buf = weechat.buffer_search('irc', '%s.%s' % (server, info['channel']))
		ircrypt_error(err.decode('utf-8'), buf)
		return args
	if err:
		ircrypt_warn(err.decode('utf-8'))

	# Ensure the generated messages are not too long and send them
	return ircrypt_split_msg(pre, 'CRY', base64.b64encode(out).decode('utf-8'))


def ircrypt_config_init():
	''' This method initializes the configuration file. It creates sections and
	options in memory and prepares the handling of key sections.
	'''
	global ircrypt_config_file
	ircrypt_config_file = weechat.config_new('ircrypt', 'ircrypt_config_reload_cb', '')
	if not ircrypt_config_file:
		return

	# marker
	ircrypt_config_section['marker'] = weechat.config_new_section(
			ircrypt_config_file, 'marker', 0, 0, '', '', '', '', '', '', '', '',
			'', '')
	if not ircrypt_config_section['marker']:
		weechat.config_free(ircrypt_config_file)
		return
	ircrypt_config_option['encrypted'] = weechat.config_new_option(
			ircrypt_config_file, ircrypt_config_section['marker'],
			'encrypted', 'string', 'Marker for encrypted messages', '', 0, 0,
			'encrypted', 'encrypted', 0, '', '', '', '', '', '')
	ircrypt_config_option['unencrypted'] = weechat.config_new_option(
			ircrypt_config_file, ircrypt_config_section['marker'], 'unencrypted',
			'string', 'Marker for unencrypted messages received in an encrypted channel',
			'', 0, 0, '', 'u', 0, '', '', '', '', '', '')

	# cipher options
	ircrypt_config_section['cipher'] = weechat.config_new_section(
			ircrypt_config_file, 'cipher', 0, 0, '', '', '', '', '', '', '', '',
			'', '')
	if not ircrypt_config_section['cipher']:
		weechat.config_free(ircrypt_config_file)
		return
	ircrypt_config_option['sym_cipher'] = weechat.config_new_option(
			ircrypt_config_file, ircrypt_config_section['cipher'],
			'sym_cipher', 'string', 'symmetric cipher used by default', '', 0, 0,
			'TWOFISH', 'TWOFISH', 0, '', '', '', '', '', '')

	# general options
	ircrypt_config_section['general'] = weechat.config_new_section(
			ircrypt_config_file, 'general', 0, 0, '', '', '', '', '', '', '', '',
			'', '')
	if not ircrypt_config_section['general']:
		weechat.config_free(ircrypt_config_file)
		return
	ircrypt_config_option['binary'] = weechat.config_new_option(
			ircrypt_config_file, ircrypt_config_section['general'],
			'binary', 'string', 'GnuPG binary to use', '', 0, 0,
			'', '', 0, '', '', '', '', '', '')

	# keys
	ircrypt_config_section['keys'] = weechat.config_new_section(
			ircrypt_config_file, 'keys', 0, 0, 'ircrypt_config_keys_read_cb', '',
			'ircrypt_config_keys_write_cb', '', '', '', '', '', '', '')
	if not ircrypt_config_section['keys']:
		weechat.config_free(ircrypt_config_file)

	# Special Ciphers
	ircrypt_config_section['special_cipher'] = weechat.config_new_section(
			ircrypt_config_file, 'special_cipher', 0, 0,
			'ircrypt_config_special_cipher_read_cb', '',
			'ircrypt_config_special_cipher_write_cb', '', '', '', '', '', '', '')
	if not ircrypt_config_section['special_cipher']:
		weechat.config_free(ircrypt_config_file)


def ircrypt_config_reload_cb(data, config_file):
	'''Handle a reload of the configuration file.
	'''
	global ircrypt_keys, ircrypt_cipher
	# Forget Keys and ciphers to make sure they are properly reloaded and no old
	# ones are left
	ircrypt_keys   = {}
	ircrypt_cipher = {}
	return weechat.config_reload(config_file)


def ircrypt_config_read():
	''' Read IRCrypt configuration file (ircrypt.conf).
	'''
	return weechat.config_read(ircrypt_config_file)


def ircrypt_config_write():
	''' Write IRCrypt configuration file (ircrypt.conf) to disk.
	'''
	return weechat.config_write(ircrypt_config_file)


def ircrypt_config_keys_read_cb(data, config_file, section_name, option_name,
		value):
	'''Read elements of the key section from the configuration file.
	'''
	ircrypt_keys[option_name.lower()] = value
	return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED


def ircrypt_config_keys_write_cb(data, config_file, section_name):
	'''Write passphrases to the key section of the configuration file.
	'''
	weechat.config_write_line(config_file, section_name, '')
	for target, key in sorted(list(ircrypt_keys.items())):
		weechat.config_write_line(config_file, target.lower(), key)

	return weechat.WEECHAT_RC_OK


def ircrypt_config_special_cipher_read_cb(data, config_file, section_name,
		option_name, value):
	'''Read elements of the key section from the configuration file.
	'''
	ircrypt_cipher[option_name.lower()] = value
	return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED


def ircrypt_config_special_cipher_write_cb(data, config_file, section_name):
	'''Write passphrases to the key section of the configuration file.
	'''
	weechat.config_write_line(config_file, section_name, '')
	for target, cipher in sorted(list(ircrypt_cipher.items())):
		weechat.config_write_line(config_file, target.lower(), cipher)
	return weechat.WEECHAT_RC_OK


def ircrypt_command_list():
	'''List set keys and channel specific ciphers.
	'''
	# List keys
	keys = '\n'.join([' %s : %s' % x for x in ircrypt_keys.items()])
	ircrypt_info('Symmetric Keys:\n' + keys if keys else 'No symmetric keys set')

	# List channel specific ciphers
	ciphers = '\n'.join([' %s : %s' % x for x in ircrypt_cipher.items()])
	ircrypt_info('Special ciphers:\n' + ciphers if ciphers
			else 'No special ciphers set')
	return weechat.WEECHAT_RC_OK


def ircrypt_command_set_keys(target, key):
	'''Set key for target.

	:param target: server/channel combination
	:param key: Key to use for target
	'''
	ircrypt_keys[target.lower()] = key
	ircrypt_info('Set key for %s' % target)
	return weechat.WEECHAT_RC_OK


def ircrypt_command_remove_keys(target):
	'''Remove key for target.

	:param target: server/channel combination
	'''
	try:
		del ircrypt_keys[target.lower()]
		ircrypt_info('Removed key for %s' % target)
	except KeyError:
		ircrypt_info('No existing key for %s.' % target)
	return weechat.WEECHAT_RC_OK


def ircrypt_command_set_cip(target, cipher):
	'''Set cipher for target.

	:param target: server/channel combination
	:param cipher: Cipher to use for target
	'''
	ircrypt_cipher[target.lower()] = cipher
	ircrypt_info('Set cipher %s for %s' % (cipher, target))
	return weechat.WEECHAT_RC_OK


def ircrypt_command_remove_cip(target):
	'''Remove cipher for target.

	:param target: server/channel combination
	'''
	try:
		del ircrypt_cipher[target.lower()]
		ircrypt_info('Removed special cipher. Using default cipher for %s instead.' % target)
	except KeyError:
		ircrypt_info('No special cipher set for %s.' % target)
	return weechat.WEECHAT_RC_OK


def ircrypt_command_plain(buffer, server, args, argv):
	'''Send unencrypted message
	'''
	channel = ''
	if (len(argv) > 2 and argv[1] == '-channel'):
		channel = argv[2]
		args = (args.split(' ', 2)+[''])[2]
	else:
		# Try to determine the server automatically
		channel = weechat.buffer_get_string(buffer, 'localvar_channel')
	# If there is no text, just ignore the command
	if not args:
		return weechat.WEECHAT_RC_OK
	marker = weechat.config_string(ircrypt_config_option['unencrypted'])
	msg = marker + ' ' + args.split(' ', 1)[-1]
	ircrypt_message_plain['%s/%s' % (server, channel)] = (time.time(), msg)
	weechat.command('','/msg -server %s %s %s' % \
			(server, channel, msg))
	return weechat.WEECHAT_RC_OK


def ircrypt_command(data, buffer, args):
	'''Hook to handle the /ircrypt weechat command.
	'''
	argv = args.split()

	# list
	if not argv or argv == ['list']:
		return ircrypt_command_list()

	# Check if a server was set
	if (len(argv) > 2 and argv[1] == '-server'):
		server = argv[2]
		del argv[1:3]
		args = (args.split(' ', 2)+[''])[2]
	else:
		# Try to determine the server automatically
		server = weechat.buffer_get_string(buffer, 'localvar_server')

	# All remaining commands need a server name
	if not server:
		ircrypt_error('Unknown Server. Please use -server to specify server', buffer)
		return weechat.WEECHAT_RC_ERROR

	if argv[:1] == ['plain']:
		return ircrypt_command_plain(buffer, server, args, argv)

	try:
		target = '%s/%s' % (server, argv[1])
	except:
		ircrypt_error('Unknown command. Try  /help ircrypt', buffer)
		return weechat.WEECHAT_RC_OK

	# Set keys
	if argv[:1] == ['set-key']:
		if len(argv) < 3:
			return weechat.WEECHAT_RC_ERROR
		return ircrypt_command_set_keys(target, ' '.join(argv[2:]))

	# Remove keys
	if argv[:1] == ['remove-key']:
		if len(argv) != 2:
			return weechat.WEECHAT_RC_ERROR
		return ircrypt_command_remove_keys(target)

	# Set special cipher for channel
	if argv[:1] == ['set-cipher']:
		if len(argv) < 3:
			return weechat.WEECHAT_RC_ERROR
		return ircrypt_command_set_cip(target, ' '.join(argv[2:]))

	# Remove secial cipher for channel
	if argv[:1] == ['remove-cipher']:
		if len(argv) != 2:
			return weechat.WEECHAT_RC_ERROR
		return ircrypt_command_remove_cip(target)

	ircrypt_error('Unknown command. Try  /help ircrypt', buffer)
	return weechat.WEECHAT_RC_OK


def ircrypt_encryption_statusbar(*args):
	'''This method will set the “ircrypt” element of the status bar if
	encryption is enabled for the current channel. The placeholder {{cipher}}
	can be used, which will be replaced with the cipher used for the current
	channel.
	'''
	channel = weechat.buffer_get_string(weechat.current_buffer(), 'localvar_channel')
	server  = weechat.buffer_get_string(weechat.current_buffer(), 'localvar_server')
	key = ircrypt_keys.get(('%s/%s' % (server, channel)).lower())

	# Return nothing if no key is set for current channel
	if not key:
		return ''

	# Get cipher used for current channel
	cipher = weechat.config_string(ircrypt_config_option['sym_cipher'])
	cipher = ircrypt_cipher.get(('%s/%s' % (server, channel)).lower(), cipher)

	# Return marker, but replace {{cipher}}
	marker = weechat.config_string(ircrypt_config_option['encrypted'])
	return marker.replace('{{cipher}}', cipher)


def ircrypt_find_gpg_binary(names=('gpg2','gpg')):
	'''Check for GnuPG binary to use
	:returns: Tuple with binary name and version.
	'''
	for binary in names:
		p = subprocess.Popen([binary, '--version'],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE)
		version = p.communicate()[0].decode('utf-8').split('\n',1)[0]
		if not p.returncode:
			return binary, version
	return None, None


def ircrypt_check_binary():
	'''If binary is not set, try to determine it automatically
	'''
	cfg_option = weechat.config_get('ircrypt.general.binary')
	gnupg = weechat.config_string(cfg_option)
	if not gnupg:
		(gnupg, version) = ircrypt_find_gpg_binary(('gpg','gpg2'))
		if not gnupg:
			ircrypt_error('Automatic detection of the GnuPG binary failed and '
					'nothing is set manually. You wont be able to use IRCrypt like '
					'this. Please install GnuPG or set the path to the binary to '
					'use.', '')
		else:
			ircrypt_info('Found %s' % version, '')
			weechat.config_option_set(cfg_option, gnupg, 1)


# register plugin
if __name__ == '__main__' and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR,
		SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, 'ircrypt_unload_script',
		'UTF-8'):
	# register the modifiers
	ircrypt_config_init()
	ircrypt_config_read()
	ircrypt_check_binary()
	weechat.hook_modifier('irc_in_privmsg',  'ircrypt_decrypt_hook', '')
	weechat.hook_modifier('irc_out_privmsg', 'ircrypt_encrypt_hook', '')

	weechat.hook_command('ircrypt', 'Commands to manage IRCrypt options and execute IRCrypt commands',
			'[list]'
			'| set-key [-server <server>] <target> <key> '
			'| remove-key [-server <server>] <target> '
			'| set-cipher [-server <server>] <target> <cipher> '
			'| remove-cipher [-server <server>] <target> '
			'| plain [-server <server>] [-channel <channel>] <message>',
			SCRIPT_HELP_TEXT,
			'list || set-key %(irc_channel)|%(nicks)|-server %(irc_servers) %- '
			'|| remove-key %(irc_channel)|%(nicks)|-server %(irc_servers) %- '
			'|| set-cipher %(irc_channel)|-server %(irc_servers) %- '
			'|| remove-cipher |%(irc_channel)|-server %(irc_servers) %- '
			'|| plain |-channel %(irc_channel)|-server %(irc_servers) %-',
			'ircrypt_command', '')
	weechat.bar_item_new('ircrypt', 'ircrypt_encryption_statusbar', '')
	weechat.hook_signal('ircrypt_buffer_opened', 'update_encryption_status', '')


def ircrypt_unload_script():
	'''Hook to ensure the configuration is properly written to disk when the
	script is unloaded.
	'''
	ircrypt_config_write()
	return weechat.WEECHAT_RC_OK
