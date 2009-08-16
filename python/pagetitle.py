# pagetitle plugin for weechat-0.3.0
#
#  /pt http://tech.slashdot.org/tech/08/11/12/199215.shtml
#  <user> http://tech.slashdot.org/tech/08/11/12/199215.shtml
#		 ('Slashdot | Microsoft's "Dead Cow" Patch Was 7 Years In the Making')
#
# xororand @ irc://irc.freenode.net/#weechat
#
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.5: sync with last API changes

import htmllib
import re
import socket
import sys
import urllib2

limit_title_length = 100
debug = True

# user agent
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (weechat/pagetitle)')]
urllib2._urlopener = opener

# set a short timeout to avoid freezing weechat [seconds]
socket.setdefaulttimeout(5)

regex_url = re.compile("""https?://[^ ]+""")

def unescape(s): #{{{
	"""Unescape HTML entities"""
	p = htmllib.HTMLParser(None)
	p.save_bgn()
	p.feed(s)
	return p.save_end() #}}}

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

	title = re.search('(?i)\<title\>(.*?)\</title\>', head)
	if title:
		title = title.group(1)
		return unescape(title)
	else:
		return ""

# /pt http://foo
def on_pagetitle(data, buffer, args):
	if len(args) == 0:
		return weechat.WEECHAT_RC_ERROR

	msg = args

	def urlReplace(match):
		url = match.group()
		try:
			if debug:
				weechat.prnt(buffer, "pagetitle: retrieving '%s'" % url)
			title = getPageTitle(url)
			if len(title) > limit_title_length:
				title = "%s [...]" % title[0:limit_title_length]
			url = "%s ('%s')" % (url, title)
		except NameError, e:
			weechat.prnt(buffer, "pagetitle: URL: '%s', Error: '%s'" % (url, e))
		return url

	msg = regex_url.sub(urlReplace, msg)
	weechat.command(buffer, "/say %s" % msg)

	return weechat.WEECHAT_RC_OK

# Register plugin
import weechat

weechat.register ('pagetitle', 'xororand', '0.5', 'GPL3', """Adds HTML titles to http:// urls in your message.""", "", "")
desc = """Sends a message to the current buffer and adds HTML titles to http:// URLs.
Example: /pt check this out: http://xkcd.com/364/
<you> check this out: http://xkcd.com/364/ (xkcd - A webcomic of romance, sarcasm, math and language)"""
weechat.hook_command ('pt', desc, 'message', 'message containing an URL', '', 'on_pagetitle', '')

# vim:set ts=4 sw=4 noexpandtab nowrap foldmethod=marker:

