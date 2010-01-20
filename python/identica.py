# Copyright (c) 2009 by fauno <fauno@kiwwwi.com.ar>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ABOUT
# This plugin gives format to identi.ca's bot messages, converting
# the @sender into the bot's nick and colorizing usernames, groups
# and hashtags.

# It's written for bitlbee, but should work with anything that permits
# the XMPP bot open a query buffer with you.

# Since version 0.2 it includes suscription handling and whois
# habilities.

# HISTORY
# 2009-07-27, fauno:
#		initial release
# 2009-09-17, fauno:
#       added basic suscription handling (sub/unsub/block/unblock)
#		username whois
#       remind user color
# 2009-09-27, fauno:
#       help definition
# 2009-10-11, fauno:
#       hability to check up to 20 updates from users (/sn updates <username> <quantity>)
# 2010-01-20, fauno:
#       fixed int to str error caused by api changes.
#       default regexp's for @names, etc. includes trailing space

# PLANNED FEATURES
# 	- @autocompletion (if it's really possible!)

import weechat
import re
import urllib2
import simplejson as json

from base64 import encodestring
from urllib import urlencode
from random import randint


SCRIPT_NAME    = "identica"
SCRIPT_AUTHOR  = "fauno <fauno@kiwwwi.com.ar>"
SCRIPT_VERSION = "0.2.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Formats identi.ca's bot messages"

settings = {
		"username"                : "",
		"password"                : "",
		"service"                 : "identi.ca",
		"scheme"                  : "https",
		"channel"                 : "localhost.update",
		"re"                      : "^(?P<update>\w+)(?P<separator>\W+?)(?P<username>\w+): (?P<dent>.+)$",
		"me"                      : "^(?P<update>\w+)(?P<separator>\W+?)(?P<username>\w+): \/me (?P<dent>.+)$",

		"nick_color"              : "green",
		"hashtag_color"           : "blue",
		"group_color"             : "red",

		"nick_color_identifier"   : "blue",
		"hashtag_color_identifier": "green",
		"group_color_identifier"  : "green",

		"nick_re"                 : "(@)([a-zA-Z0-9]+ )",
		"hashtag_re"              : "(#)([a-zA-Z0-9]+ )",
		"group_re"                : "(!)([a-zA-Z0-9]+ )"
		}

users = {}

class StatusNet():
	def __init__(self, username, password, scheme, service):

		self.username = username
		self.password = password

		self.realm    = 'StatusNet API'
		self.service  = service
		self.scheme   = scheme

		self.opener = self.get_auth_opener()

	def get_auth_opener(self):
		'''Authentication'''
		basic_auth = encodestring(':'.join([self.username, self.password]))
		basic_auth = ' '.join(['Basic', basic_auth])

		handler = urllib2.HTTPBasicAuthHandler()
		handler.add_password(realm=self.realm,
		                     uri=self.service,
							 user=self.username,
							 passwd=self.password)
		
		self.headers = {'Authorization':basic_auth}
		return urllib2.build_opener(handler)

	def build_request(self, api_method, api_action, user_or_id, data={}):
		'''Builds an API request'''
		url = '%s://%s/api/%s/%s/%s.json' % (self.scheme,
		                                     self.service,
											 api_method,
											 api_action,
											 user_or_id)

		request = urllib2.Request(url, urlencode(data), self.headers)
		return request

	def handle_request(self, request):
		'''Sends an API request and handles errors'''
		try:
			response = self.opener.open(request)
		except urllib2.HTTPError, error:
			if error.code == 403:
				return False
			else:
				weechat.prnt(weechat.current_buffer(),
				             '%s[%s] Server responded with a %d error code' % (weechat.prefix('error'),
							                                                   self.service,
																			   error.code))
				return None
		else:
			return response

# End of StatusNet

def subscribe (username):
	if len(username) == 0:
		return weechat.WEECHAT_RC_ERROR

	response = statusnet_handler.handle_request(statusnet_handler.build_request('friendships', 'create', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sYou\'re already suscribed to %s' % (weechat.prefix('error'), username)))
	else:
		weechat.prnt(weechat.current_buffer(), ('%sSuscribed to %s updates' % (weechat.prefix('join'), username)))

	return weechat.WEECHAT_RC_OK


def unsubscribe (username):
	if len(username) == 0:
		return weechat.WEECHAT_RC_ERROR

	response = statusnet_handler.handle_request(statusnet_handler.build_request('friendships', 'destroy', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sYou aren\'t suscribed to %s' % (weechat.prefix('error'), username)))
	else:
		weechat.prnt(weechat.current_buffer(), ('%sUnsuscribed from %s\'s updates' % (weechat.prefix('quit'), username)))
	
	return weechat.WEECHAT_RC_OK

def whois (username):
	if len(username) == 0:
		return weechat.WEECHAT_RC_ERROR
	
	response = statusnet_handler.handle_request(statusnet_handler.build_request('users', 'show', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sCan\'t retrieve information about %s' % (weechat.prefix('error'), username)))
	else:
		whois = json.load(response)

		whois['summary'] = ' '.join([u'\u00B5', str(whois['statuses_count']),
		                             u'\u2764', str(whois['favourites_count']),
									 'subscribers', str(whois['followers_count']),
									 'subscriptions', str(whois['friends_count'])])

		for property in ['name', 'description', 'url', 'location', 'profile_image_url', 'summary']:
			if whois[property] != None:
				weechat.prnt(weechat.current_buffer(), ('%s[%s] %s' % (weechat.prefix('network'),
				                                                       username,
																	   whois[property].encode('utf-8'))))
		
	return weechat.WEECHAT_RC_OK

def block (username):
	'''Blocks users'''
	if len(username) == 0:
		return weechat.WEECHAT_RC_ERROR

	response = statusnet_handler.handle_request(statusnet_handler.build_request('blocks', 'create', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sCan\'t block %s' % (weechat.prefix('error'), username)))
	else:
		weechat.prnt(weechat.current_buffer(), ('%sBlocked %s' % (weechat.prefix('network'), username)))
		
	return weechat.WEECHAT_RC_OK


def unblock (username):
	'''Unblocks users'''
	if len(username) == 0:
		return weechat.WEECHAT_RC_ERROR

	response = statusnet_handler.handle_request(statusnet_handler.build_request('blocks', 'destroy', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sCan\'t unblock %s' % (weechat.prefix('error'), username)))
	else:
		weechat.prnt(weechat.current_buffer(), ('%sUnblocked %s' % (weechat.prefix('network'), username)))
		
	return weechat.WEECHAT_RC_OK

def updates (username, quantity):
	'''Shows user updates'''
	if len(username) == 0 or quantity > 20:
		return weechat.WEECHAT_RC_ERROR

	if quantity < 1:
		quantity = 1

	response = statusnet_handler.handle_request(statusnet_handler.build_request('statuses', 'user_timeline', username))

	if response == None:
		pass
	elif response == False:
		weechat.prnt(weechat.current_buffer(), ('%sCan\'t retrieve %s\'s updates' % (weechat.prefix('error'), username)))
	else:
		statuses = json.load(response)[:quantity]
		while quantity > 0:
			quantity -= 1
			weechat.prnt_date_tags(weechat.buffer_search('', weechat.config_get_plugin('channel')), 0, 'irc_privmsg', 'update\t%s: %s' % (username, statuses[quantity]['text'].encode('utf-8')))

	return weechat.WEECHAT_RC_OK


def colorize (message):
	"""Colorizes replies, hashtags and groups"""

	for identifier in ['nick','hashtag','group']:
		identifier_name = ''.join([identifier, '_re'])
		identifier_color = ''.join([identifier, '_color'])
		identifier_color_identifier = ''.join([identifier, '_color_identifier'])

		identifier_re = re.compile(weechat.config_get_plugin(identifier_name), re.UNICODE)

		replace = r''.join([
			weechat.color(weechat.config_get_plugin(identifier_color_identifier)),
			'\\1',
			weechat.color(weechat.config_get_plugin(identifier_color)),
			'\\2',
			weechat.color('reset')
			])

		message = identifier_re.sub(replace, message)

	return message

def nick_color (nick):
	"""Randomizes color for nicks"""
	if users.has_key(nick) and users[nick].has_key('color'):
		pass
	else:
		users[nick] = {}
		users[nick]['color'] = ''.join(['chat_nick_color', str(randint(1,10)).zfill(2)])

	nick = ''.join([weechat.color(users[nick]['color']), nick, weechat.color('reset')])
	return nick

def clean (message):
	'''Cleans URLs added by bot'''
	return re.sub(r''.join([' \(http://', service, '/[a-zA-Z0-9/\-_#]+\)']), '', message)

def parse (server, modifier, data, the_string):
	"""Parses weechat_print modifier on update@identi.ca pv"""

	#weechat.prnt("", the_string)
	#weechat.prnt("", data)
	plugin, channel, flags = data.split(';')
	flag = flags.split(',')

	if channel == weechat.config_get_plugin('channel') and 'irc_privmsg' in flag:
		the_string = weechat.string_remove_color(the_string, "")
		matcher = re.compile(weechat.config_get_plugin('re'), re.UNICODE)

		m = matcher.search(the_string)

		if not m: return colorize(the_string)

		dent = colorize(clean(m.group('dent')))
		username = nick_color(m.group('username'))

		the_string = ''.join([ username, m.group('separator'), dent ])

	return the_string

def nicklist(data, completion_item, buffer, completion):
	"""Completion for /sn"""
	for username, properties in users.iteritems():
		weechat.hook_completion_list_add(completion, username, 0, weechat.WEECHAT_LIST_POS_SORT)
	return weechat.WEECHAT_RC_OK

def sn (data, buffer, args):
	if args == "":
		weechat.command("", "/help sn")
		return weechat.WEECHAT_RC_OK
	
	argv = args.strip().split(' ')

	if argv[0] == 'subscribe':
		subscribe(argv[1])
	elif argv[0] == 'unsubscribe':
		unsubscribe(argv[1])
	elif argv[0] == 'whois':
		whois(argv[1])
	elif argv[0] == 'block':
		block(argv[1])
	elif argv[0] == 'unblock':
		unblock(argv[1])
	elif argv[0] == 'updates':
		updates(argv[1], int(argv[2]))

	return weechat.WEECHAT_RC_OK
	
	

# init

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, "", ""):

	for option, default_value in settings.iteritems():
		if not weechat.config_is_set_plugin(option):
			weechat.config_set_plugin(option, default_value)

	username = weechat.config_get_plugin('username')
	password = weechat.config_get_plugin('password')
	service  = weechat.config_get_plugin('service')
	scheme   = weechat.config_get_plugin('scheme')
	
	if len(username) == 0 or len(password) == 0:
		weechat.prnt(weechat.current_buffer(),
		            '%s[%s] Please set your username and password and reload the plugin' % (weechat.prefix('error'),
					                                                                        service))
	else:
		statusnet_handler = StatusNet(username, password, scheme, service)

    # hook incoming messages for parsing
	weechat.hook_modifier('weechat_print', 'parse', '')

    # /sn
	weechat.hook_command('sn',
	                     'StatusNet manager',
						 'whois | subscribe | unsubscribe | block | unblock | updates <username>',
						 '        whois: retrieves profile information from <username>'
						 "\n"
						 '    subscribe: subscribes to <username>'
						 "\n"
						 '  unsubscribe: unsubscribes from <username>'
						 "\n"
						 '        block: blocks <username>'
						 "\n"
						 '      unblock: unblocks <username>'
						 "\n"
						 '      updates: updates <username> <quantity (<20)>',
						 'whois %(sn_nicklist) || subscribe %(sn_nicklist) || unsubscribe %(sn_nicklist) || block %(sn_nicklist) || unblock %(sn_nicklist) || updates %(sn_nicklist)',
						 'sn',
						 '')

	# Completion for /sn commands
	weechat.hook_completion('sn_nicklist', 'list of SN users', 'nicklist', '')

