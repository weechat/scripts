# ==================================================== #
# Script Name: queue.py	
# Script Author: walk <KingPython@gmx.com>
# Script Purpose: Command queing at its finest. Hopefully.
#
# Copyright (C) 2011  walk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Version History:
#
# 0.4.2 - Nov 22nd, 2015
#    Add saving of static queues to disk and reloading them on startup.
#    Added by Tim Kuhlman - https://github.com/tkuhlman
# 0.4.1 - Jan 20th, 2011
#    Multi-list queuing seems to work flawlessly so far. Expanded on the /help qu text.
#    Properties are fully-functional. As for loading/saving of lists, I want to hold off until
#    I get some feedback on whether or not that would be applicable. Please email me
#    at the listed address in this script and let me know if you want this feature and/or
#    any other features.
#
# 0.4.0 - Jan 16th, 2011
#    Finished adding multi-list queuing. So far, no bugs that I can tell.
#    Perhaps an ability to load/save lists for multiple uses? Now working on
#    setting individual properties per list then taking a few days off this thing.
#    ** TESTED ON WeeChat 0.3.3 and 0.3.4 **
#
# 0.3.5 - Jan 15th, 2011
#    Started to implement multiple queue lists.
#
# 0.3.5 - Jan 14th, 2011
#    Wrote Queue class and merged with code. I did this because
#    some future release will include an ability to use multiple
#    queue lists. Also fixed some bugs in parsing and executing
#    arguments with /qu. /qu del by itself raised an error, /qu del j
#    raised a valueerror, fixed. /qu add singlearg wouldn't add. Fixed.
#
# 0.3.4 - Jan 11th, 2011
#    Modified configuration code to use plugins.conf
#
# 0.3.3 - Jan 9th, 2011
#    Big code clean-up. Reduced a few lines by optimizing code.
#    Next step, convertcommand_qu dictionary to array like
#    I should have done in the first place. Could save some lines.
#
# 0.3.2 - Jan 9th, 2011
#    Added RAINBOW option (requested)
#    Set as option in configuration
#
# 0.3.1 - Jan 8th, 2011
#    Added configurations (verbose, core output only)
#
# 0.3.0 - Jan 6th, 2011
#    Worked on script for quite a while. All code is functional.
#    Continuing to test for bugs and improve code
#    Fixed indexing issue after using /qu del with remove_index function
#
# 0.2.0 - Jan 5th, 2011
#   Cleaned up temporary testing code, built upon foundation. 
#   Next to include, del function and list function
#
# 0.1.0 - Jan 4th, 2011 
#   Wrote basic outline with minimal functionality
# ==================================================== #

import os
import pickle

import_ok = True
try:
	import weechat
except ImportError:
	print("This script requires WeeChat")
	print("To obtain a copy, for free, visit http://weechat.org")
	import_ok = False


class Queue():
	""" A Queuing Class """
	def __init__(self):
		self.data = []
		self.index = len(self.data)
		self.__clearable__ = True
		self.__ldl__ = ''
		self.__locked__ = False
	
	def __iter__(self):
		for char in range(self.index):
			yield self.data[char]
	
	def __len__(self):
		return len(self.data)
	
	def add(self, queue_text):
		if self.__locked__ == False:
			self.data.append(queue_text)
			self.index = len(self.data)
	
	def remove(self, info):
		if self.__locked__ == False:
			tmp = ''
			if info > 0:
				tmp = str(self.data[info-1])
				del self.data[info-1]
				self.__ldl__ = tmp
				self.index = len(self.data)
			elif info == 0:
				tmp = str(self.data[info])
				del self.data[info] 
				self.__ldl__ = tmp
				self.index = len(self.data)
		
		return self.__ldl__
	
	def viewqueue(self):
		list = ''
		if not len(self.data) == 0:
			for each in range(len(self.data)):
				list+=str(each+1) + ". " + str(self.data[each]) + "\n"
		else:
			list='Nothing in queue'
		
		return list.strip("\n")
	
	def clearqueue(self):
		if self.__clearable__ == True:
			self.data = []
			self.index = 0

	def isClear(self, cOpt):
		if not cOpt in (True, False):
			return
		
		self.__clearable__ = cOpt
	
	def isLocked(self, lockOpt):
		if not lockOpt in (True, False):
			return
		
		self.__locked__ = lockOpt
	
	def isEmpty(self):
		if len(self.data) == 0:
			return True
		else:
			return False


SCRIPT_NAME		= "queue"
SCRIPT_AUTHOR	= "walk"
SCRIPT_VERSION	= "0.4.2"
SCRIPT_LICENSE	= "GPL3"
SCRIPT_DESC		= "Command queuing"

COMM_CMD		= "qu"
COMM_DESC		= "Queuing commands in WeeChat"
COMM_ARGS		= "[add [command] | del [index] | new [list] | dellist [list] | set [property] [on|off] |list | clear | exec | listview]"
COMM_ARGS_DESC		= "Examples: \n\
   /qu add /msg chanserv op #foo bar \n\
   /qu del 1 \n\
   /qu new weechat \n\
       - Use the 'new' argument to switch to already defined lists as well. \n\
   /qu dellist weechat \n\
   /qu list - List commands in current list \n\
   /qu list weechat - With optional parameter, you can choose to list the commands of a specified list. \n\
   /qu clear - Clear current list.. add a listname to clear a specified list. \n\
   /qu exec - Execute the commands of the current list.. you can also specify a list here as well. \n\
   /qu listview - Outputs the names of all your lists. \n\
   /qu save - Save static lists to disk \n\
   /qu set static on - Sets static property to ON for current list. This means that when executed, the list WILL NOT clear. The clear command will not work either.\n \
   \n\
   PROPERTIES (for set command):\n \
   static - prevents a list from clearing manually or automatically but can still add and del commands.\n \
   lock - prevents the user from adding/deleting entries to a list. Can be combined with static."
COMM_COMPL		= "add|del|list|exec|new|listview|dellist"

COMMAND_QU = {'default': Queue()}
CURR_LIST = 'default'

def __config__():
	""" Configuration initialization """
	
	if not weechat.config_get_plugin("core_output_only") in ("yes", "no"):
		weechat.config_set_plugin("core_output_only", "yes")
	if not weechat.config_get_plugin("rainbow_allow") in ("yes", "no"):
		weechat.config_set_plugin("rainbow_allow", "no")
	if not weechat.config_get_plugin("verbose") in ("yes", "no"):
		weechat.config_set_plugin("verbose", "yes")
	
	load()
	return weechat.WEECHAT_RC_OK

def load():
    """ Load saved queues from pickle. """
    global COMMAND_QU
    pickle_path = os.path.join(weechat.info_get("weechat_dir", ""), 'queue.pickle')
    if os.path.exists(pickle_path):
        with open(pickle_path, 'r') as qu_pickle:
            COMMAND_QU = pickle.load(qu_pickle)

    if 'default' not in COMMAND_QU:
        COMMAND_QU['default'] = Queue()

def rainbow(data):
	""" Not my favorite option but a requested one """

	colors='red yellow green blue magenta'
	c=colors.split()
	count=0
	colorHolder=''
	
	for each in data:
		if count > 4: count = 0
		if not each == " ":
			colorHolder+=weechat.color(c[count])+each
			count += 1
		else:
			colorHolder+=" "
	
	return str(colorHolder)

def prntcore(data, essential=0, rb=0):
	""" Built more on weechat.prnt """

	if weechat.config_get_plugin("verbose") == 'yes' or essential==1:
		if weechat.config_get_plugin("core_output_only") =='yes':
			buffer = ''
		else:
			buffer = weechat.current_buffer()
		if rb == 0:
			weechat.prnt(buffer, data)
		else:
			weechat.prnt(buffer, rainbow(data))
	return weechat.WEECHAT_RC_OK

def save():
    """ Save to disk all static lists as a pickle. """
    global COMMAND_QU
    pickle_path = os.path.join(weechat.info_get("weechat_dir", ""), 'queue.pickle')
    to_save = {}
    for name, qu in COMMAND_QU.iteritems():
        if not qu.__clearable__:  # Note isClear method doesn't show status it sets it
            to_save[name] = qu

    with open(pickle_path, 'w') as qu_pickle:
        pickle.dump(to_save, qu_pickle, pickle.HIGHEST_PROTOCOL)

def rejoin(data, delimiter=' '):
	""" Rejoins a split string """
	tmpString = ''
	for each in data:
		tmpString+=each+delimiter
	
	tmpString = tmpString.strip()
	return tmpString
	
def qu_cb(data, buffer, args):
	""" Process hook_command info """
	
	global CURR_LIST, COMMAND_QU
	if weechat.config_get_plugin('rainbow_allow') == 'no':
		rainbowit=0
	else:
		rainbowit=1

        if args == "":
                return weechat.WEECHAT_RC_OK

	argv = args.split()
	arglist = ['add', 'del', 'new', 'dellist', 'list', 'clear', 'exec', 'listview', 'save', 'set']
	
	if not argv[0] in arglist:
		prntcore('[ queue -> not a valid argument: {0}'.format(argv[0]), rb=rainbowit)
		return weechat.WEECHAT_RC_OK
	
	if argv[0].lower() == "add" and len(argv) > 1:
		if not COMMAND_QU[CURR_LIST].__locked__ == True:
			COMMAND_QU[CURR_LIST].add(rejoin(argv[1:]))
			prntcore("[ queue added -> "+str(rejoin(argv[1:])) + " ]", rb=rainbowit)
		else:
			prntcore("[ queue -> the lock property is enabled for this list ({0}). please disable it before adding/deleting. ]", rb=rainbowit)
	
	elif argv[0].lower() == "del" and len(argv) > 1:
		if not COMMAND_QU[CURR_LIST].__locked__ == True:
			try:
				rmd = COMMAND_QU[CURR_LIST].remove(int(argv[1]))
				prntcore("[ queue -> deleted: ({0}) {1} ]".format(argv[1],rmd), rb=rainbowit)
			except (IndexError, ValueError):
				prntcore("[ queue -> invalid reference. please check /qu list and try again. ]", rb=rainbowit)
		else:
			prntcore("[ queue -> the lock property is enabled for this list ({0}). please disable it before adding/deleting. ]".format(CURR_LIST), rb=rainbowit)
		
	elif argv[0].lower() == "clear":
		this_list = None
		if len(argv) > 1 and argv[1].lower() in COMMAND_QU.keys():
			this_list = CURR_LIST
			CURR_LIST = argv[1].lower()
		
		if COMMAND_QU[CURR_LIST].__clearable__ == True:
			if not COMMAND_QU[CURR_LIST].isEmpty():
				COMMAND_QU[CURR_LIST].clearqueue()
				prntcore('[ queue -> command queue list cleared. ]', rb=rainbowit)
			else:
				prntcore('[ queue -> command queue already empty. ]', rb=rainbowit)
		else:
			prntcore('[ queue -> please turn off the static property to clear the {0} list. ]'.format(CURR_LIST), rb=rainbowit)
		
		if not this_list == None:
			CURR_LIST = this_list
			this_list = None
		
	elif argv[0].lower() == "list":
		this_list = None
		if len(argv) > 1 and argv[1].lower() in COMMAND_QU.keys():
			this_list = CURR_LIST
			CURR_LIST = argv[1].lower()
		
		qHeader = '[ COMMAND QUEUE: {0} ]'.format(CURR_LIST)
		prntcore(" ", 1)
		prntcore("-"*len(qHeader), 1, rb=rainbowit)
		prntcore(qHeader, 1, rainbowit)
		prntcore("-"*len(qHeader), 1, rainbowit)
		prntcore(COMMAND_QU[CURR_LIST].viewqueue(), 1, rb=rainbowit)
		
		if not this_list == None:
			CURR_LIST = this_list
			this_list = None
		
	elif argv[0].lower() == "exec":
		
		this_list = None
		if len(argv) > 1 and argv[1].lower() in COMMAND_QU.keys():
			this_list = CURR_LIST
			CURR_LIST = argv[1].lower()
		
		if len(COMMAND_QU[CURR_LIST]) > 0:

			for each in COMMAND_QU[CURR_LIST]:
				weechat.command(buffer, each)
			COMMAND_QU[CURR_LIST].clearqueue()
			if COMMAND_QU[CURR_LIST].__clearable__ == True:
				prntcore('[ queue -> finished executing list: {0}. command list cleared. ]'.format(CURR_LIST), rb=rainbowit)
			else:
				prntcore('[ queue -> finished executing list: {0} ]'.format(CURR_LIST), rb=rainbowit)
		else:
			prntcore("[ queue -> nothing to execute. please add to the queue using /qu add <command>", rb=rainbowit)
		
		if not this_list == None:
			CURR_LIST = this_list
			this_list = None
	
	elif argv[0].lower() == "new" and len(args.split()) > 1:
		if argv[1].lower() in COMMAND_QU.keys():
			CURR_LIST = argv[1].lower()
			prntcore("[ queue -> switched queue list to: {0}".format(CURR_LIST), rb=rainbowit)
		else:
			COMMAND_QU[argv[1].lower()] = Queue()
			CURR_LIST = argv[1].lower()
			prntcore("[ queue -> created new list. current list is: {0}".format(CURR_LIST), rb=rainbowit)
	
	elif argv[0].lower() == "listview":
		qHeader = 'QUEUE LISTS'
		listCount = 1
		
		prntcore(' ', 1)
		prntcore('-'*len(qHeader), 1, rb=rainbowit)
		prntcore(qHeader, 1, rb=rainbowit)
		prntcore('-'*len(qHeader), 1, rb=rainbowit)
		
		for each in COMMAND_QU.keys():
			prntcore(str(listCount) + ". " + str(each), 1, rb=rainbowit)
			listCount += 1
	
	elif argv[0].lower() == "dellist" and len(args.split()) > 1:
		if not argv[1].lower() in COMMAND_QU.keys():
			prntcore('[ queue -> {0} is not a list. ]'.format(argv[1].lower()), rb=rainbowit)
		elif argv[1].lower() == 'default':
			prntcore('[ queue -> cannot delete the default list. ]', rb=rainbowit)
		else:
			if argv[1].lower() == CURR_LIST:
				CURR_LIST = 'default'
			del COMMAND_QU[argv[1].lower()]
			prntcore('[ queue -> {0} successfully deleted.'.format(argv[1].lower()), rb=rainbowit)
	
	elif argv[0].lower() == "save":
		save()
	elif argv[0].lower() == "set" and len(argv) == 4:
		setargs = args.split()
		list_name = setargs[1].lower()
		set_prop = setargs[2].lower()
		toggle = setargs[3].lower()
		properties = ['static', 'lock']

		if not list_name in COMMAND_QU.keys():
			prntcore('[ queue -> list must be created before you can set properties ]', rb=rainbowit)
		elif not set_prop in properties:
			prntcore('[ queue -> invalid property. please try again. ]', rb=rainbowit)
		elif not toggle in ('on', 'off'):
			prntcore('[ queue -> only valid options for a property are ON or OFF ]', rb=rainbowit)
		else:
			if set_prop == 'static':
				if toggle=='on':
					COMMAND_QU[list_name].isClear(False)
					prntcore('[ queue -> static property toggled on for: {0} ]'.format(list_name), rb=rainbowit)
					save()
				else:
					COMMAND_QU[list_name].isClear(True)
					prntcore('[ queue -> static property toggled off for: {0} ]'.format(list_name), rb=rainbowit)
					save()
			
			elif set_prop == 'lock':
				if toggle=='on':
					COMMAND_QU[list_name].isLocked(True)
					prntcore('[ queue -> lock property toggled on for: {0} ]'.format(list_name), rb=rainbowit)
				else:
					COMMAND_QU[list_name].isLocked(False)
					prntcore('[ queue -> lock property toggled off for: {0} ]'.format(list_name), rb=rainbowit)
	
	return weechat.WEECHAT_RC_OK

if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
	weechat.hook_command(COMM_CMD, COMM_DESC, COMM_ARGS, COMM_ARGS_DESC, COMM_COMPL, "qu_cb", "")
	__config__()
