#!/bin/env python
#
# TinyUrl, version 3.5, for weechat version 0.1.9 or later
#
#   Listens to all channels for long URLs, and submits them to ln-s.net or
#   tinyurl.com for easier links.
#
# Usage:
#
#   By default, any URL longer than 30 characters in length is grabbed,
#   submitted to a service, and printed in the channel for your eyes only.  For
#   example, you may see something like this:
#
# [11:21] <@lack> http://www.cbc.ca/story/canada/national/2005/11/12/mcdona
#                 lds-051112.html?ref=rss 
# [11:21] -P- [AKA] http://tinyurl.com/9dthl
#
#   Now you can just cut&paste the easier, shorter URL into your favourite
#   browser.
# 
#   If you want to be extra-helpful (or annoying) to certain channels you
#   are in, you can actually have the script say the tinyurl.com equivalent
#   of all long URLs, by adding the channel to the 'activechans' list.  In
#   that case, everyone in the channel would see the following:
#
# [11:25] <testuser> http://www.cbc.ca/story/canada/national/2005/11/12/mcdona
#                    lds-051112.html?ref=rss 
# [11:25] <@lack> [AKA] http://tinyurl.com/9dthl
#
# Configuration:
#
#   Run '/help tinyurl' for the actual usage for setting these options:
#
#   activechans
#     A comma-delimited list of channels you will actually "say" the
#     tinyurl in.  By default the list is empty.  Be warned, some channels
#     won't appreciate extra help (or 'noise' as they like to call it), and
#     some channels already have bots that do this.  Please only enable
#     this in channels where the ops have given you permission.
#
#   urllength
#     An integer, default value 30.  Any URL this long or longer will
#     trigger a tinyurl event.
#
#   printall
#     Either "on" or "off", default "on".  When ON, you will see the
#     tinyurl printed in your window for any channels not in your
#     activechans list.  When OFF, you will not see any tinyurls except in
#     your activechans list.
#
#   service
#     Either "tinyurl" or "ln-s".  tinyurl is the default.
#
# Requirements:
#
#  - Designed to run with weechat version 0.1.9 or better.
#      http://weechat.flashtux.org/
#
#  - Requires that 'curl' is in the path (tested with curl 7.15.0).
#      http://curl.haxx.se/
#
# Copyright (C) 2005 Jim Ramsay <i.am@jimramsay.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# Changelog:
#
# Version 3.5, June 3, 2008
#   Added ln-s.net support
#   Turned off some ugly verbose output unless requested
#
# Version 3.4, June 3, 2008
#   tinyurl.com changed their output page slightly, and broke our parsing
#
# Version 3.3, July 4, 2006
#   Catches possible error in os.waitpid
#   Properly prints tinyurls in query windows
#
# Version 3.2, June 15, 2006
#   Multiple configuration bugfixes, pointed out by Stalwart on #weechat.
#
# Version 3.1, June 15, 2006
#   Now kills any leftover curl processes when the script is unloaded.
#   Thanks again to kolter for the great idea!
#   Also cleaned up /tinyurl command, added comletion_template, updated
#   help text, improved option parsing logic, etc.
#
# Version 3.0, June 15, 2006
#   Fixes "tinyurl script sometimes makes weechat freeze" issue by using
#   the new timer handlers available in Weechat 0.1.9
#   Also includes URL detection fix from Raimund Specht
#   <raimund@spemaus.de>.
#
# Version 2.0, Dec 13, 2005
#   Also catches https, ftp, and ftps URLs, thanks to kolter for the
#   suggestion!
#
# Version 1.1, Dec 2, 2005
#   Fixed undefined 'urlend' thanks to kolter@irc.freenode.org#weechat
#
# TODO:
#
# - Handle outgoing messages and replace long urls with the tinyurl
#   equivalent automatically.
# - On load, check that 'curl' is installed, and fail if not.
#

import os, tempfile, re
try:
	import urllib
except:
	raise ImportError("You need to reload the python plugin to reload urllib")
import weechat

class TryAgain(UserWarning):
	def __init__(self, message):
		super(UserWarning, self).__init__(message)

# Register with weechat
weechat.register( "TinyUrl", "3.5", "tinyurlShutdown", "Waits for URLs and sends them to 'tinyurl' for you" )

# Global variables
tinyurlParams = ("urllength","activechans","printall","service","debug")
tinyurlProcessList = {}

# Set default settings values:
if weechat.get_plugin_config('urllength') == "":
	weechat.set_plugin_config('urllength', "30")
if not weechat.get_plugin_config('printall') in ("on", "off"):
	weechat.set_plugin_config('printall', "on")
if not weechat.get_plugin_config('service') in ("tinyurl", "ln-s"):
	weechat.set_plugin_config('service', "tinyurl")
if not weechat.get_plugin_config('debug') in ("on", "off"):
	weechat.set_plugin_config('debug', "off")

# Start the timer thread and register handlers
weechat.add_timer_handler( 1, "tinyurlCheckComplete" )
weechat.add_message_handler("privmsg", "tinyurlHandleMessage")
weechat.add_command_handler("tinyurl", "tinyurlMain", \
	"Sets/Gets 'tinyurl' settings.",
	"[<variable> [[=] <value>]]",
"""When run without arguments, displays all tinyurl settings

<variable> : Sets or displays a single tinyurl setting. One of:
    activechans [[=] #chan1[,#chan2...]]
        List of channels where others will see your tinyurls.
        Default: None
    urllength [[=] length]
        Will not create tinyurls for any URLs shorter than this.
        Default: 30
    printall [[=] on|off]
        When off, will not display private tinyurls, just those
        displayed publicly in your "active channels"
        Default: on
    service [[=] tinyurl|ln-s]
        Sets the service used for shortening the URL.
        Default: tinyurl
    debug [[=] on|off]
        Creates extra debug output in the server window when on.
        Default: off""",
	 "urllength|activechans|printall|service|debug"
    )

def tinyurlShutdown():
	"""Cleanup - Kills any leftover child processes"""
	if len(tinyurlProcessList.keys()) > 0:
		weechat.prnt( "-TinyUrl- Cleaning up unfinished processes:", "", "" )
		for pid in tinyurlProcessList.keys():
			weechat.prnt( "	Process %d" % pid, "", "" )
			try:
				os.kill(pid, 9)
				os.waitpid( pid, 0 )
			except:
				weechat.prnt( "		Cleanup failed, skipping", "", "" )
	return weechat.PLUGIN_RC_OK
	
def tinyurlGet( name = "" ):
	"""Gets a variable value"""
	if name == "":
		weechat.prnt( "-TinyUrl- Get all:" )
		for name in tinyurlParams:
			weechat.prnt( "	%s = %s" % (name, weechat.get_plugin_config(name)) )
	else:
		weechat.prnt( "-TinyUrl- Get:" )
		if name in tinyurlParams:
			weechat.prnt( "	%s = %s" % (name, weechat.get_plugin_config(name)) )
		else:
			weechat.prnt( "	Unknown parameter \"%s\", try '/help tinyurl'" % name )
	return

def tinyurlSet( name, value ):
	"""Sets a variable value"""
	if value == "":
		tinyurlGet( name )
	else:
		weechat.prnt( "-TinyUrl- Set:" )
		if name in tinyurlParams:
			if name == "printall" or name == "debug":
				if value == "0" or value.lower() == "no" or value.lower() == "off":
					value = "off"
				elif value == "1" or value.lower() == "yes" or value.lower() == "on":
					value = "on"
				else:
					weechat.prnt( "	%s must be one of 'on' or 'off'" % name )
					weechat.prnt( "	value = '%s'" % value )
					return
			elif name == "service":
				if value.lower() in ("tinyurl", "ln-s"):
					value = value.lower()
				else:
					weechat.prnt( "	service must be one of 'tinyurl' or 'ln-s'" )
					weechat.prnt( "	value = '%s'" % value )
					return
			elif name == "urllength":
				try:
					v = int(value)
					if v < 0 or v > 100:
						weechat.prnt( "	urllength must be between 0 and 100" )
						weechat.prnt( "	value = '%s'" % value )
						return
				except:
					weechat.prnt( "	urllength must be a valid integer" )
					weechat.prnt( "	value = '%s'" % value )
					return
			elif name == "activechans":
				vs = re.split(", |,| ", value)
				values = []
				for v in vs:
					if v.startswith("#"):
						values.append(v)
						value = ",".join(values)
			weechat.set_plugin_config(name, value)
			weechat.prnt( "	%s = %s" % (name, weechat.get_plugin_config(name)) )
		else:
			weechat.prnt( "	Unknown parameter \'%s\'" % name )
	return

def tinyurlMain( server, args ):
	"""Main handler for the /tinyurl command"""
	args = args.split( " " )
	while '' in args:
		args.remove('')
	while ' ' in args:
		args.remove(' ')
	if len(args) == 0:
		tinyurlGet()
	else:
		name = args[0]
		value = ""
		if len(args) > 1:
			if args[1] == "=":
				value = " ".join(args[2:])
			else:
				value = " ".join(args[1:])
			tinyurlSet( args[0], value )
		else:
			tinyurlGet( name )
	return weechat.PLUGIN_RC_OK

def tinyurlGetUrl( url, channel, server ):
	"""Starts a background process which will query the appropriate service and
	put the result in a file that the timer function 'tinyurlCheck' will find and
	parse."""
	global tinyurlProcessList
	handle, filename = tempfile.mkstemp( prefix="weechat-tinyurl.py-" )
	os.close(handle)
	service = weechat.get_plugin_config('service')
	if service == "tinyurl":
		cmd = ("curl -d url=%s http://tinyurl.com/create.php --stderr /dev/null -o %s" % \
			 (urllib.quote(url), filename)).split()
	else:
		cmd = ("curl http://ln-s.net/home/api.jsp?url=%s --stderr /dev/null -o %s" % \
			 (urllib.quote(url), filename)).split()
	try:
		pid = os.spawnvp( os.P_NOWAIT, cmd[0], cmd )
		if weechat.get_plugin_config('debug') == "on":
			weechat.prnt( "Setting ProcessList[%d] to (%s, %s, %s)" % \
				(pid, filename, channel, server), "", server )
		tinyurlProcessList[pid] = (filename, url, service, channel, server)
	except Exception, e:
		weechat.prnt( "-TinyUrl- Error: Could not spawn curl: %s" % e )

def parseTinyurl( file ):
	turl = None
	for line in file:
		if( line.startswith("<input type=\"hidden\" id=\"tinyurl\" value=\"") ):
			turlend = line[41:].find("\"")
			if turlend > -1:
				turl = line[41:][:turlend]
			break
	if turl is None:
		weechat.prnt( "-TinyUrl- Error: Unrecognized response from server" )
		weechat.prnt( "          Maybe tinyurl.com changed their format again." )
		weechat.prnt( "          Try '/tinyurl service ln-s' to use ln-s.net instead" )
	return turl

def parseLns( file ):
	turl = None
	for line in file:
		(code, message) = line.split(" ", 2)
		if code == "200":
			return message.rstrip()
		elif code == "503":
			# Try again, respawn curl
			weechat.prnt( "-TinyUrl- Warning: ln-s.net is busy, trying again shortly" )
			raise TryAgain(line)
		else:
			weechat.prnt( "-TinyUrl- Error: Error response from server: %s" % (line) )
			return None

def tinyurlParsefile( filename, service ):
	"""Parses the given HTML file and pulls out the tinyurl."""
	turl = None
	try:
		html = open(filename, "r")
		if service == "tinyurl":
			turl = parseTinyurl(html)
		else:
			turl = parseLns(html)
		html.close()
	except Exception, e:
		weechat.prnt( "-TinyUrl- Error: Could not open result file %s: %s" % (filename, e) )
	return turl

def tinyurlPrint( original, url, channel, server ):
	"""Prints the new tinyurl either to just you, or to the whole channel"""
	where = "Unknown"
	locstart = original.find("//")
	if locstart > -1:
		locend = original.find("/", locstart + 2)
		if locend > -1:
			where = original[locstart + 2:locend]
	activeChans = weechat.get_plugin_config('activechans').split(',')
	if channel in activeChans:
		weechat.command( "/msg %s [AKA] %s" % ( channel, url) )
	else:
		if weechat.get_plugin_config('debug') == "on":
			weechat.prnt( "Printing url to channel '%s', server '%s'" % \
				(channel, server), "", server )
		weechat.prnt( "[AKA] %s (%s)" % (url, where), channel, server )

def tinyurlFindUrlstart( msg, start = 0 ):
	"""Finds the beginnings of URLs"""
	index = -1
	if start < 0 or start >= len(msg):
		return index
	for prefix in ( "http://", "https://", "ftp://", "ftps://" ):
		index = msg.find( prefix, start )
		if index > -1:
			break
	return index 

def tinyurlFindUrlend( msg, urlstart ):
	"""Finds the ends of URLs (Strips following punctuation)"""
	m = msg[urlstart:]
	index = m.find( " " )
	if index == -1:
		index = len(m)
	while msg[index-1] in ( "?", ".", "!" ):
		index -= 1
	return index + urlstart

def tinyurlCheckComplete():
	"""The periodic poll of all waiting processes"""
	global tinyurlProcessList
	for pid in tinyurlProcessList.keys():
		(filename, url, service, channel, server) = tinyurlProcessList[pid]
		try:
			(p, er) = os.waitpid( pid, os.WNOHANG )
			if p != 0:
				if er == 0:
					try:
						tinyurl = tinyurlParsefile(filename, service)
						if tinyurl is not None:
							tinyurlPrint( url, tinyurl, channel, server )
					except TryAgain:
						tinyurlGetUrl(url, channel, server)
				else:
					weechat.prnt( "-TinyUrl- Error: 'curl' did not run properly" )
				os.unlink(filename)
				del tinyurlProcessList[pid]
		except OSError, e:
			weechat.prnt( "-TinyUrl- Error: 'curl' process not found: %s", e )
			os.unlink(filename)
			del tinyurlProcessList[pid]
	return weechat.PLUGIN_RC_OK

def tinyurlHandleMessage( server, args ):
	"""Handles IRC PRIVMSG and checks for URLs"""
	maxlen = int(weechat.get_plugin_config( "urllength" ))
	activeChans = weechat.get_plugin_config('activechans').split(',')
	onlyActiveChans = weechat.get_plugin_config('printall') == "off"
	(source, type, channel, msg) = args.split(" ", 3)
	if onlyActiveChans and channel not in activeChans:
		return weechat.PLUGIN_RC_OK
	if not channel.startswith("#"):
		channel = source.split("!", 2)[0][1:]
	urlstart = tinyurlFindUrlstart( msg )
	while urlstart > -1 and urlstart is not None:
		urlend = tinyurlFindUrlend( msg, urlstart )
		url = msg[urlstart:urlend]
		if len(url) >= maxlen:
			tinyurlGetUrl(url, channel, server)
		# Check for more URLs
		urlstart = tinyurlFindUrlstart( msg, urlend+1 )
	return weechat.PLUGIN_RC_OK
