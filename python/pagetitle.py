#!/usr/bin/python

# pagetitle plugin for weechat-0.2.6
# usage example:
#  /pt check this out: http://slashdot.org
#  <user> check this out: http://slashdot.org ('Slashdot: News for nerds, stuff that matters')
# author: <wolf@unfoog.de>

import htmllib
import re
import socket
import sys
import urllib2
import weechat

# Cut off titles
limit_title_length = 50
debug = False

# Change user agent
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (weechat/pagetitle)')]
urllib2._urlopener = opener

# Short timeout to avoid freezing weechat [seconds]
socket.setdefaulttimeout(5)

# Matches http urls
regex_url = re.compile("""https?://[^ ]+""")

def unescape(s):
	"""Unescape HTML entities"""

	p = htmllib.HTMLParser(None)
	p.save_bgn()
	p.feed(s)
	return p.save_end()

def getPageTitle(url):
	"""Retrieve the HTML <title> from a webpage"""

	try:
		u = urllib2.urlopen(url)
	except urllib2.HTTPError, e:
		raise NameError(str(e))
	except urllib2.URLError, e:
		raise NameError(str(e))

	info = u.info()
	try:
		content_type = info['Content-Type']
		if not re.match(".*/html.*",content_type):
			return ""
	except:
		return ""

	head = u.read(8192)
	head = re.sub("[\r\n\t ]"," ",head)

	title_esc = re.search('(?i)\<title\>(.*?)\</title>', head)
	if title_esc:
		title_esc = title_esc.group(1)
		return unescape(title_esc)
	else:
		return ""


def on_pagetitle(server, args):
	if len(args) == 0:
		return weechat.PLUGIN_RC_KO

	msg = args

	def urlReplace(match):

		url = match.group()
		try:
			if debug:
				weechat.prnt("pagetitle: retrieving '%s'" % url)

			title = getPageTitle(url)
			if len(title) > limit_title_length:
				title = "%s [...]" % title[0:limit_title_length]
			url = "%s ('%s')" % (url, title)

		except NameError, e:
			weechat.prnt("pagetitle: URL: '%s', Error: '%s'" % (url, e))

		return url

	msg = regex_url.sub(urlReplace, msg)

	weechat.command(msg)
	return weechat.PLUGIN_RC_OK

# Register plugin
weechat.register ('pagetitle', '0.3', '', """Adds HTML titles to http:// urls in your message.""")

desc = """Sends a message to the current buffer and adds HTML titles to http:// URLs.
Example: /pt check this out: http://xkcd.com/364/
<you> check this out: http://xkcd.com/364/ (xkcd - A webcomic of romance, sarcasm, math and language)"""

weechat.add_command_handler ('pagetitle', 'on_pagetitle', desc, 'message')
weechat.add_command_handler ('pt', 'on_pagetitle', desc, 'message')

