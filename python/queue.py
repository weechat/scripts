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

import_ok = True
try:
	import weechat
except ImportError:
	print("This script requires WeeChat")
	print("To obtain a copy, for free, visit http://weechat.org")
	import_ok = False

SCRIPT_NAME		= "queue"
SCRIPT_AUTHOR	= "walk"
SCRIPT_VERSION	= "0.3.4"
SCRIPT_LICENSE	= "GPL3"
SCRIPT_DESC		= "Command queuing"

COMM_CMD		= "qu"
COMM_DESC		= "Queuing commands in WeeChat"
COMM_ARGS		= "[add [command] | del [index] | list | clear | exec]"
COMM_COMPL		= "add|del|list|exec"

command_qu={}
default_index = 0

def __config__():
	""" Configuration initialization """
	
	if not weechat.config_get_plugin("core_output_only") in ("yes", "no"):
		weechat.config_set_plugin("core_output_only", "yes")
	if not weechat.config_get_plugin("rainbow_allow") in ("yes", "no"):
		weechat.config_set_plugin("rainbow_allow", "no")
	if not weechat.config_get_plugin("verbose") in ("yes", "no"):
		weechat.config_set_plugin("verbose", "yes")
	
	return weechat.WEECHAT_RC_OK

def remove_index(dict, index):
	""" Rebuilds dictionary keys to sequential value """

	dict.pop(index)
	new_index=0
	new_dict={}
	
	for k, v in dict.iteritems():
		new_dict[new_index]=v
		new_index += 1
	
	dict.clear()
	return new_dict

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

def qu_cb(data, buffer, args):
	global command_qu, default_index

	if weechat.config_get_plugin('rainbow_allow') == 'no':
		rainbowit=0
	else:
		rainbowit=1
	
	if len(args) > 0:
		my_command=args.split().pop(0).lower()
		my_args=args[args.find(' ')+1:]
	else:
		prntcore("[ queue -> no arguments wit /qu. please see /help qu ]", 
					rb=rainbowit)
		return weechat.WEECHAT_RC_OK
	
	if my_command == "add" and len(args.split()) > 2:
		command_qu[default_index] = my_args
		default_index += 1
		prntcore("[ queue added -> "+str(my_args) + " ]", rb=rainbowit)
		
	elif my_command == "del":
		try:
			command_qu=remove_index(command_qu, int(my_args))
			default_index=len(command_qu)
		except:
			prntcore("[ queue -> invalid reference. please check /qu list and try again. ]", rb=rainbowit)
		
	elif my_command == "clear":
		command_qu = {}
		default_index = 0
		prntcore('[ queue -> command queue list cleared. ]', rb=rainbowit)
		
	elif my_command == "list":
		prntcore(" ", 1)
		prntcore("-"*17, 1, rb=rainbowit)
		prntcore("[ COMMAND QUEUE ]", 1, rainbowit)
		prntcore("-"*17, 1, rainbowit)
		if len(command_qu) > 0:
			for kkey,vvalue in command_qu.iteritems():
				prntcore(str(kkey) + ". " + str(vvalue), 1, rainbowit)
			prntcore(" ", 1)
		else:
			prntcore('Nothing in queue', 1, rainbowit)
			prntcore(' ', 1)
		
	elif my_command == "exec":
		if len(command_qu) > 0:
			for k,v in command_qu.iteritems():
				weechat.command(buffer, str(v))
				prntcore('[ queue -> executing: '+str(k)+'. '+  str(v) + ' ]', rb=rainbowit)
			
			command_qu = {}
			default_index = 0
			prntcore('[ queue -> finished executing commands. command list cleared. ]', rb=rainbowit)
			
		else:
			prntcore("[ queue -> nothing to execute. please add to the queue using /qu add <command>", rb=rainbowit)
	
	return weechat.WEECHAT_RC_OK

 
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
	weechat.hook_command(COMM_CMD, COMM_DESC, COMM_ARGS, "",COMM_COMPL,"qu_cb", "")
	__config__()
