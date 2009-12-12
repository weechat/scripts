# -*- coding: utf-8 -*-
###
# Copyright (c) 2009 by Elián Hanisch <lambdae2@gmail.com>
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
###

###
# Prints user's country and local time information in
# whois/whowas replies (for WeeChat 0.3.*)
#
#   This script uses MaxMind's GeoLite database from
#   http://www.maxmind.com/app/geolitecountry
#
#   This script depends in pytz third party module for retrieving
#   timezone information for a given country. Without it the local time
#   for a user won't be displayed.
#   Get it from http://pytz.sourceforge.net or from your distro packages,
#   python-tz in Ubuntu/Debian
#
#   Commands:
#   * /country
#     Prints country for a given ip, uri or nick. See /help country
#
#   Settings:
#   * plugins.var.python.country.show_in_whois:
#     If 'off' /whois or /whowas replies won't contain country information.
#     Valid values: on, off
#   * plugins.var.python.country.show_localtime:
#     If 'off' timezone and local time infomation won't be looked for.
#     Valid values: on, off
#
#   History:
#   2009-12-12
#   version 0.3: update WeeChat site.
#
#   2009-09-17
#   version 0.2: added timezone and local time information.
#
#   2009-08-24
#   version 0.1.1: fixed python 2.5 compatibility.
#
#   2009-08-21
#   version 0.1: initial release.
#
###

SCRIPT_NAME    = "country"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Prints user's country and local time in whois replies"
SCRIPT_COMMAND = "country"

try:
	import weechat
	WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://www.weechat.org/"
	import_ok = False
try:
	import pytz, datetime
	pytz_module = True
except:
	pytz_module = False

import os

### ip database
database_url = 'http://geolite.maxmind.com/download/geoip/database/GeoIPCountryCSV.zip'
database_file = 'GeoIPCountryWhois.csv'

### config
class ValidValuesDict(dict):
	"""
	Dict that returns the default value defined by 'defaultKey' key if __getitem__ raises
	KeyError. 'defaultKey' must be in the supplied dict.
	"""
	def _error_msg(self, key):
		error("'%s' is an invalid option value, allowed: %s. Defaulting to '%s'" \
				%(key, ', '.join(map(repr, self.keys())), self.default))

	def __init__(self, dict, defaultKey):
		self.update(dict)
		assert defaultKey in self
		self.default = defaultKey

	def __getitem__(self, key):
		try:
			return dict.__getitem__(self, key)
		except KeyError:
			# user set a bad value
			self._error_msg(key)
			return dict.__getitem__(self, self.default)

settings = (('show_in_whois', 'on'), ('show_localtime', 'on'))

boolDict = ValidValuesDict({'on':True, 'off':False}, 'off')
def get_config_boolean(config):
	"""Gets our config value, returns a sane default if value is wrong."""
	return boolDict[weechat.config_get_plugin(config)]

### messages
def say(s, prefix=SCRIPT_NAME, buffer=''):
	weechat.prnt(buffer, '%s: %s' %(prefix, s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
	weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

def debug(s, prefix='debug', buffer=''):
	weechat.prnt(buffer, '%s: %s' %(prefix, s))

def whois(nick, string, buffer=''):
	"""Message formatted like a whois reply."""
	prefix_network = weechat.prefix('network')
	color_delimiter = weechat.color('chat_delimiters')
	color_nick = weechat.color('chat_nick')
	weechat.prnt(buffer, '%s%s[%s%s%s] %s' %(prefix_network, color_delimiter, color_nick, nick,
		color_delimiter, string))

def string_country(country, code):
	"""Format for country info string."""
	color_delimiter = weechat.color('chat_delimiters')
	color_chat = weechat.color('chat')
	return '%s%s %s(%s%s%s)' %(color_chat, country, color_delimiter,
			color_chat, code, color_delimiter)

def string_time(dt):
	"""Format for local time info string."""
	color_delimiter = weechat.color('chat_delimiters')
	color_chat = weechat.color('chat')
	date = dt.strftime('%x %X %Z')
	tz = dt.strftime('UTC%z')
	return '%s%s %s(%s%s%s)' %(color_chat, date, color_delimiter,
			color_chat, tz, color_delimiter)

### functions
def get_script_dir():
	"""Returns script's dir, creates it if needed."""
	script_dir = weechat.info_get('weechat_dir', '')
	script_dir = os.path.join(script_dir, 'country')
	if not os.path.isdir(script_dir):
		os.makedirs(script_dir)
	return script_dir

ip_database = ''
def check_database():
	"""Check if there's a database already installed."""
	global ip_database
	if not ip_database:
		ip_database = os.path.join(get_script_dir(), database_file)
	return os.path.isfile(ip_database)

timeout = 1000*60
hook_download = ''
def update_database():
	"""Downloads and uncompress the database."""
	global hook_download, ip_database
	if not ip_database:
		check_database()
	if hook_download:
		weechat.unhook(hook_download)
		hook_download = ''
	script_dir = get_script_dir()
	say("Downloading IP database...")
	hook_download = weechat.hook_process(
			"python -c \"\n"
			"import urllib2, zipfile, os, sys\n"
			"try:\n"
			"	temp = os.path.join('%(script_dir)s', 'temp.zip')\n"
			"	try:\n"
			"		zip = urllib2.urlopen('%(url)s', timeout=10)\n"
			"	except TypeError: # python2.5\n"
			"		import socket\n"
			"		socket.setdefaulttimeout(10)\n"
			"		zip = urllib2.urlopen('%(url)s')\n"
			"	fd = open(temp, 'w')\n"
			"	fd.write(zip.read())\n"
			"	fd.close()\n"
			"	print 'Download complete, uncompressing...'\n"
			"	zip = zipfile.ZipFile(temp)\n"
			"	try:\n"
			"		zip.extractall(path='%(script_dir)s')\n"
			"	except AttributeError: # python2.5\n"
			"		fd = open('%(ip_database)s', 'w')\n"
			"		fd.write(zip.read('%(database_file)s'))\n"
			"		fd.close()\n"
			"	os.remove(temp)\n"
			"except Exception, e:\n"
			"	print >>sys.stderr, e\n\"" %{'url':database_url, 'script_dir':script_dir,
				'ip_database':ip_database, 'database_file':database_file},
			timeout, 'update_database_cb', '')

process_stderr = ''
def update_database_cb(data, command, rc, stdout, stderr):
	"""callback for our database download."""
	global hook_download, process_stderr
	#debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
	if stdout:
		say(stdout)
	if stderr:
		process_stderr += stderr
	if int(rc) >= 0:
		if process_stderr:
			error(process_stderr)
			process_stderr = ''
		else:
			say('Success.')
		hook_download = ''
	return WEECHAT_RC_OK

hook_get_ip = ''
def get_ip_process(host):
	"""Resolves host to ip."""
	# because getting the ip might take a while, we must hook a process so weechat doesn't hang.
	global hook_get_ip
	if hook_get_ip:
		weechat.unhook(hook_get_ip)
		hook_get_ip = ''
	hook_get_ip = weechat.hook_process(
			"python -c \"\n"
			"import socket, sys\n"
			"try:\n"
			"	ip = socket.gethostbyname('%(host)s')\n"
			"	print ip\n"
			"except Exception, e:\n"
			"	print >>sys.stderr, e\n\"" %{'host':host},
			timeout, 'get_ip_process_cb', '')

def get_ip_process_cb(data, command, rc, stdout, stderr):
	"""Called when uri resolve finished."""
	global hook_get_ip, reply_wrapper
	#debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
	if stdout and reply_wrapper:
		code, country = search_in_database(stdout[:-1])
		reply_wrapper(code, country)
		reply_wrapper = None
	if stderr and reply_wrapper:
		reply_wrapper(*unknown)
		reply_wrapper = None
	if int(rc) >= 0:
		hook_get_ip = ''
	return WEECHAT_RC_OK

def is_ip(ip):
	"""Checks if 'ip' is a valid ip number."""
	if ip.count('.') == 3:
		L = ip.split('.')
		try:
			for n in L:
				n = int(n)
				if not (n >= 0 and n <= 255):
					return False
		except:
			return False
		return True
	else:
		return False

def is_host(host):
	"""A valid host must have at least one dot an no slashes."""
	# This is a very poor check
	# I will fix it when it fails
	if '/' in host:
		return False
	elif '.' in host:
		return True
	return False

def get_host_by_nick(nick, buffer):
	"""Gets host from a given nick, for code simplicity we only search in current buffer."""
	channel = weechat.buffer_get_string(buffer, 'localvar_channel')
	server = weechat.buffer_get_string(buffer, 'localvar_server')
	if channel and server:
		infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
		if infolist:
			while weechat.infolist_next(infolist):
				name = weechat.infolist_string(infolist, 'name')
				if nick == name:
					host = weechat.infolist_string(infolist, 'host')
					return host[host.find('@')+1:] # strip everything in front of '@'
			weechat.infolist_free(infolist)
	return ''

def sum_ip(ip):
	"""Converts the ip number from dot-decimal notation to decimal."""
	L = map(int, ip.split('.'))
	return L[0]*16777216 + L[1]*65536 + L[2]*256 + L[3]

unknown = ('--', 'unknown')
def search_in_database(ip):
	"""
	search_in_database(ip_number) => (code, country)
	returns ('--', 'unknown') if nothing found
	"""
	import csv
	global ip_database
	if not ip or not ip_database:
		return unknown
	try:
		n = sum_ip(ip)
		fd = open(ip_database)
		reader = csv.reader(fd)
		max = os.path.getsize(ip_database)
		last_high = last_low = min = 0
		while True:
			mid = (max + min)/2
			fd.seek(mid)
			fd.readline() # move cursor to next line
			_, _, low, high, code, country = reader.next()
			if low == last_low and high == last_high:
				break
			if n < long(low):
				max = mid
			elif n > long(high):
				min = mid
			elif n > long(low) and n < long(high):
				return (code, country)
			else:
				break
			last_low, last_high = low, high
	except StopIteration:
		pass
	return unknown

def print_country(host, buffer, quiet=False, broken=False, nick=''):
	"""
	Prints country and local time for a given host, if quiet is True prints only if there's a match,
	if broken is True reply will be split in two messages.
	"""
	#debug('host: ' + host)
	def reply_country(code, country):
		if quiet and code == '--':
			return
		if pytz_module and get_config_boolean('show_localtime') and code != '--':
			dt = get_country_datetime(code)
			if broken:
				whois(nick or host, string_country(country, code), buffer)
				whois(nick or host, string_time(dt), buffer)
			else:
				s = '%s - %s' %(string_country(country, code), string_time(dt))
				whois(nick or host, s, buffer)
		else:
			whois(nick or host, string_country(country, code), buffer)

	if is_ip(host):
		# good, got an ip
		code, country = search_in_database(host)
	elif is_host(host):
		# try to resolve uri
		global reply_wrapper
		reply_wrapper = reply_country
		get_ip_process(host)
		return
	else:
		# probably a cloak
		code, country = '--', 'cloaked'
	reply_country(code, country)

### timezone
def get_country_datetime(code):
	"""Get datetime object with country's timezone."""
	tzname = pytz.country_timezones(code)[0]
	tz = pytz.timezone(tzname)
	return datetime.datetime.now(tz)

### commands
def cmd_country(data, buffer, args):
	"""Shows country and local time for a given ip, uri or nick."""
	if not args:
		weechat.command('', '/HELP %s' %SCRIPT_COMMAND)
		return WEECHAT_RC_OK
	if ' ' in args:
		# picks the first argument only
		args = args[:args.find(' ')]
	if args == 'update':
		update_database()
	else:
		if not check_database():
			error("IP database not found. You must download a database with '/country update' before "
					"using this script.", buffer=buffer)
			return WEECHAT_RC_OK
		#check if is a nick
		host = get_host_by_nick(args, buffer)
		if not host:
			host = args
		print_country(host, buffer)
	return WEECHAT_RC_OK

### signal callbacks
def whois_cb(data, signal, signal_data):
	"""function for /WHOIS"""
	if not get_config_boolean('show_in_whois') or not check_database():
		return WEECHAT_RC_OK
	nick, user, host = signal_data.split()[3:6]
	server = signal[:signal.find(',')]
	#debug('%s | %s | %s' %(data, signal, signal_data))
	buffer = weechat.buffer_search('irc', 'server.%s' %server)
	print_country(host, buffer, quiet=True, broken=True, nick=nick)
	return WEECHAT_RC_OK

### main
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, '', ''):
	weechat.hook_signal('*,irc_in2_311', 'whois_cb', '') # /whois
	weechat.hook_signal('*,irc_in2_314', 'whois_cb', '') # /whowas
	weechat.hook_command('country', cmd_country.__doc__, 'update | (nick|ip|uri)',
			"       update: Downloads/updates ip database with country codes.\n"
			"nick, ip, uri: Gets country and local time for a given ip, domain or nick.",
			'update||%(nick)', 'cmd_country', '')
	# settings
	for opt, val in settings:
		if not weechat.config_is_set_plugin(opt):
			weechat.config_set_plugin(opt, val)
	if not check_database():
		say("IP database not found. You must download a database with '/country update' before "
				"using this script.")
	if not pytz_module and get_config_boolean('show_localtime'):
		error(
			"pytz module isn't installed, local time information is DISABLED. "
			"Get it from http://pytz.sourceforge.net or from your distro packages "
			"(python-tz in Ubuntu/Debian).")
		weechat.config_set_plugin('show_localtime', 'off')

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
