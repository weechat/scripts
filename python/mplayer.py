# -*- coding: utf-8 -*-
"""
Ported to weechat by llua (Two & a half LoC. AWWWWWW YEA, 1337)
Contact: llua at irc://irc.freenode.net
----------------------------------------------------------------------------
xchat_mplayer by Csigaa
Prints 'NICK is playing FILENAME [MPlayer version]' action to the active channel/dialog.

This version is entirely based on procfs, so finally works on
all POSIX-compilant OS (*BSD, Solaris, Linux, etc) without calling any commands
(except for version number, but it is now optional)

NOTE FOR PASTEBIN: save the file as xchat_mplayer.py to your xchat directory


Contact: csigaa@gmail.com
License: Beer-ware (by phk) ;p
----------------------------------------------------------------------------
 "THE BEER-WARE LICENSE" (Revision 42):
 Csigaa wrote this file. As long as you retain this notice you
 can do whatever you want with this stuff. If we meet some day, and you think
 this stuff is worth it, you can buy me a beer in return
----------------------------------------------------------------------------

"""


import weechat
import os
import re

weechat.register("mplayer", "llua", "0.1", "The Beer-ware License", "Now Playing for MPlayer", "", "")

if os.name != 'posix':
    raise NotImplementedError,'non-POSIX systems are not supported'

def getFilename():
    # Get the video file name (identified by naming pattern) from procfs

    # list&walk the directory contents
    proclist = sorted(os.listdir('/proc'))
    for proc in os.listdir('/proc'):
	# if it is a directory with a name of digits only
	if os.path.isdir('/proc/'+proc) and re.match('[0-9]+',proc):
	    try:
		exe = os.readlink('/proc/'+proc+'/exe').split('/')
		# if executable name is 'mplayer'
		if exe.pop() == 'mplayer':
		    filelist = os.listdir('/proc/'+proc+'/fd')
		    # walk the list of open files
		    for file in filelist:
			try:
			    path = os.readlink('/proc/'+proc+'/fd/'+file)
			    if re.match('.*(avi|mpg|mkv|mp4|nuv|ogg|ogm|wmv|iso|img)$',path,re.I):
				# if video filename found, return
				return path.split('/').pop()
			except:
			    # if link not readable, skip
			    continue
	    except:
		# if process directory not readable, skip
		continue
    return None

def getVersion():
    try:
	import commands
	try:
	    # release version, begins with number (incl. optional rc sign with maximum 2 digits); if no match, exception occurs (empty list - 0 index is out of range)
	    ver = re.findall('^MPlayer\s\d[.]\d+\w{0,4}',commands.getoutput('mplayer'))[0]
	except:
	    # SVN version, begins with 'SVN' (revision number maximum 6 digits)
	    ver = re.findall('^MPlayer\sSVN-r\d{0,6}',commands.getoutput('mplayer'))[0]
	return ver
    except:
	# if any error occured above, return only the player name
	return 'MPlayer'

def mplayer_msg(world,world_eol,userdata):
    fn = getFilename()
    ver = getVersion()
    if type(fn) == str:
	# we've got a string for fn
	all = '/me is now watching: ' + fn + ' [' + ver + ']'
	weechat.command(weechat.current_buffer(), all)
	return 0
    else:
	# we've got None (or something went very-very wrong)
	return 1

weechat.hook_command("mplayer", "Now Watching", "", "/mplayer", "", "mplayer_msg", "")
