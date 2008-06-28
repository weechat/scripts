# Copyright (c) 2006 by SpideR <spider312@free.fr> http://spiderou.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

# WeeChat clone scanner
# Scans clones on a chan when you ask it to do (/clones)
# Able to scan for a nick's clones on each join, if you ask it to do (/autoscan)

# TODO : 
# * Disable scan for a nick's join on multiple chans
# * ( Scan for previous nick of a host ) DONE
# ** Stock time, to clean on timer and display it
# * Modularize messages display, configure where it displays

import weechat		# WeeChat API
import re		# Regular Expressions
import time		# Time

################################################################## CONSTANTS ###
SCRIPT_NAME="clonescan"
SCRIPT_VERSION="0.3"
SCRIPT_DESC="clonescan script for weechat"
SCRIPT_DISP=SCRIPT_NAME+" v"+SCRIPT_VERSION

######################################################################## API ###
# Register, Handlers, config check/creation
if weechat.register(SCRIPT_NAME, SCRIPT_VERSION, "unload", SCRIPT_DESC):
	weechat.set_plugin_config('test','test')
	# Usefull global declaration
	yes = [ "1", "yes", "enable", "true" ] # Things considered as "true" in settings
	no = [ "0", "no", "disable", "false" ] # Things considered as "false" in settings
	hosts = [[],[],[]]
	#  Messages
	weechat.add_message_handler("join","onjoin")
	weechat.add_message_handler("part","onpart")
	# Default config management
	def check_config_bool(config_name,default_value):
		config_value = weechat.get_plugin_config(config_name)
		if ( ( config_value not in yes ) and ( config_value not in no ) ):
			weechat.set_plugin_config(config_name,default_value)
			weechat.prnt("Unconfigured "+config_name+" set to '"+default_value+"/"+weechat.get_plugin_config(config_name)+"', see /"+config_name)
	check_config_bool("autoscan","false")
	check_config_bool("checkhost","false")
	# Handlers
	#  Commands
	weechat.add_command_handler("clones","scanchan","Scans clones on specified or current chan","[#chan]")
	weechat.add_command_handler("autoscan","autoscan","Manage auto clone-scanning","[enable|disable|show]")
	weechat.add_command_handler("checkhost","checkhost","Manage host checking","[view|enable|disable|list|clear]")
	weechat.add_command_handler("clone_ignore","toggle_ignore","Manage ignores lists (server,chan,nick,user,host)",
		"[server,chan,nick,user,host] [view|add|del|set] [match|coma separated list]")
	# All seems loaded here
	weechat.prnt(SCRIPT_DISP+" loaded")
else:
	weechat.prnt(SCRIPT_DISP+" not loaded")

# Unload handler
def unload():
	weechat.prnt(SCRIPT_DISP+" now unloaded")
	return weechat.PLUGIN_RC_OK

#################################################################### LOADERS ###
# onJOIN : Auto scan 
def onjoin(server,args): # :SpideR_test_script2!spider@RS2I-26C9FCA9.spiderou.net JOIN :#clonescan
	result = weechat.PLUGIN_RC_OK # Default : go on
	# Check activated
	if ( weechat.get_plugin_config("autoscan") != "true" ):
		result = weechat.PLUGIN_RC_KO
	# Check server not igored
	if ( server in weechat.get_plugin_config("server_ignore").split(" ") ):
		result = weechat.PLUGIN_RC_KO
		#weechat.prnt("Join ignored because of server : "+server)
	# Cut nick@user!host JOIN #chan
	if ( result == weechat.PLUGIN_RC_OK ):
		try: # Let's try cutting JOIN with ':'
			nickuserathost, chan = args.split(" JOIN :")
			#weechat.prnt("OK cutting JOIN with ':' : ["+nickuserathost+"] + ["+chan+"] on ["+server+"]",server,server)
		except ValueError:
			#weechat.prnt("NOK cutting ["+args+"] with ':' on ["+server+"]",server,server)
			try: # Didn't work so let's try without ':' (bug on ogamenet)
				nickuserathost, chan = args.split(" JOIN ")
				#weechat.prnt("OK cutting JOIN without ':' : ["+nickuserathost+"] + ["+chan+"] on ["+server+"]",server,server)
			except ValueError: # None worked
				result = weechat.PLUGIN_RC_KO
				weechat.prnt("Eror cutting JOIN : ["+args+"]",server,server)
		# Check server not igored
		if ( chan in weechat.get_plugin_config("chan_ignore").split(" ") ):
			result = weechat.PLUGIN_RC_KO
			#weechat.prnt("Join ignored because of chan : "+chan)
	# Cut nick@user!host
	if ( result == weechat.PLUGIN_RC_OK ):
		try: 
			nick,user,host = cutnickuserhost(nickuserathost)
			#weechat.prnt("OK cutting nick!user@host : ["+nick+"] ! ["+user+"] @ ["+host+"] on ["+chan+"]",server,server)
		except ValueError:
			result = weechat.PLUGIN_RC_KO
			weechat.prnt("Eror cutting nick!user@host : ["+nickuserathost+"] on ["+chan+"]",server,server)
		# Check server not igored
		if ( nick in weechat.get_plugin_config("nick_ignore").split(" ") ):
			result = weechat.PLUGIN_RC_KO
			#weechat.prnt("Join ignored because of nick : "+nick)
		# Check server not igored
		if ( user in weechat.get_plugin_config("user_ignore").split(" ") ):
			result = weechat.PLUGIN_RC_KO
			#weechat.prnt("Join ignored because of user : "+user)
		# Check server not igored
		if ( host in weechat.get_plugin_config("host_ignore").split(" ") ):
			result = weechat.PLUGIN_RC_KO
			#weechat.prnt("Join ignored because of host : "+host)
		
	
	# all cutted correctly, let's scan and display result if needed
	if ( result == weechat.PLUGIN_RC_OK ):
		clones = scannick(server,chan,nick,host) # Scan for that user's clones
		if ( len(clones) > 0):
			clones.sort() # Theorically sorting that list
			display(server,chan,"Clone sur "+chan+"@"+server+" : "+nick+" = "+", ".join(clones)+" ("+host+")")
		# See if user is in saved hosts
		if ( weechat.get_plugin_config("checkhost") == "true" ):
			if host in hosts[0]:
				posinhosts = hosts[0].index(host)
				if ( nick+'!'+user != hosts[1][posinhosts] ):
					display(server,chan,nick+"@"+chan+" seen under nick "+hosts[1][posinhosts])
	return result

# onPART : Save connexion information
def onpart(server,args): # :SpideR_test_script2!spider@RS2I-26C9FCA9.spiderou.net PART #clonescan :emerge -pv byebye
	result = weechat.PLUGIN_RC_OK
	nick,user,host = cutnickuserhost(args) # Cut nick!user@host
	savehost(host,nick,user)
	return result

# onPART subdivision : save nick/host/time for current user
def savehost(host,nick,user):
	result = False
	actualtime = round(time.time())
	if host in hosts[0]: # Host existing in list : update informations
		posinhosts = hosts[0].index(host)
		hosts[1][posinhosts] = nick+'!'+user # Change stored value for nick
		hosts[2][posinhosts] = actualtime
	else: # Host not existing in list : add it
		result = True
		hosts[0].append(host)
		hosts[1].append(nick+'!'+user)
		hosts[2].append(actualtime)
	return result

# Manual channel scan
def scanchan(server,args):
	result = weechat.PLUGIN_RC_OK
	# Defining chan to scan (contained in args, current chan otherwise)
	if ( args == "" ):
		chan = weechat.get_info("channel",server)
	else:
		chan = args
	# Scan
	if ( chan == "" ):
		result = weechat.PLUGIN_RC_KO
		weechat.prnt("Not on a chan")
	else:
		nicks = weechat.get_nick_info(server,chan)
		if nicks == None:
			result = weechat.PLUGIN_RC_KO
			weechat.prnt("Eror reading nick list")
		else:
			if nicks == {}:
				result = weechat.PLUGIN_RC_KO
				weechat.prnt("Nobody on "+chan+", are you sure it's a chan and you are present on it ?")
			else:
				weechat.prnt("Scanning "+chan+" ...")
				allclones = [] # List containing all detected clones, for not to re-scan them
				nbclones = 0 # number of clones
				for nick in nicks:
					if nick not in allclones:
						host = removeuser(nicks[nick]["host"])
						clones = scannick(server,chan,nick,host)
						if ( len(clones) > 0 ):
							allclones = allclones + clones
							nbclones = nbclones+1
							clones.append(nick) # Regrouping nick and its clones in one list
							clones.sort() # Theorically sorting that list
							weechat.prnt(" - "+", ".join(clones)+" ("+host+")",chan)
				s = "s"
				if ( len(clones) == 1 ):
					s = ""
				weechat.prnt(str(nbclones)+" clone"+s+" found")
	return result
	
#################################################################### DISPLAY ###
# Display messages where they were configures to be displayed (TODO)
def display(server,chan,disp):
	result = weechat.PLUGIN_RC_OK
	#weechat.print_infobar(5,disp) # Display on infobar
	weechat.prnt(disp) # Display on current buffer
	if ( chan != weechat.get_info("channel",server) ): # if current buffer isn't concerned chan
		weechat.prnt(disp,chan) # Display on concerned chan
	#weechat.prnt(disp,server,server) # Display on server buffer
	return result

####################################################################### SCAN ###
# Returns list of nick clones (not containing nick himself)
def scannick(server,chan,nick,host):
	cloneof = [] # Default return value : list containing no clones
	compares = weechat.get_nick_info(server,chan)
	if compares == None:
		weechat.prnt("Eror reading nicklist on "+chan+" on "+server)
	else:
		if compares == {}:
			weechat.prnt("No nicks on "+chan+" on "+server)
		else:
			for compare in compares:
				if ( ( nick != compare ) and ( host == removeuser(compares[compare]["host"])) ):
					cloneof.append(compare)
	return cloneof
################################################################## FUNCTIONS ###
# Return host by user@host
def removeuser(userathost):
	splitted = userathost.split("@")
	return splitted[1]

# Cut :nick!user@host
def cutnickuserhost(nickuserhost):
	mask = re.compile(':(\S*)!(\S*)@(\S*)') # Define RegExp
			# :SaT_!~sat@ANancy-751-1-14-249.w90-6.abo.wanadoo.fr
	# maskmatch = mask.match(nickuserhost) # Apply Regexp
	matches = mask.findall(nickuserhost)
	if len(matches) == 0 :
		result = "","",""
	else:
		result = matches[0][0],matches[0][1],matches[0][2]
	return result

########################################################## CONFIG MANAGEMENT ###
# Config auto scan
def autoscan(server,args):
	# Get current value
	autoscan = weechat.get_plugin_config("autoscan")
	# Testing / repairing
	if ( autoscan == "true" ):
		auto = True
	elif ( autoscan == "false" ):
		auto = False
	else:
		weechat.prnt("Unknown value ["+autoscan+"], disabling")
		weechat.set_plugin_config("autoscan","false")
		auto = False
	# Manage arg
	if ( args in yes ):
		if auto:
			weechat.prnt("Auto clone scanning remain enabled")
		else:
			weechat.set_plugin_config("autoscan","true")
			weechat.prnt("Auto clone scanning is now enabled")
	elif ( args in no ):
		if auto:
			weechat.set_plugin_config("autoscan","false")
			weechat.prnt("Auto clone scanning is now disabled")
		else:
			weechat.prnt("Auto clone scanning remain disabled")
	else:
		if auto:
			weechat.prnt("Auto clone scanning enabled")
		else:
			weechat.prnt("Auto clone scanning disabled")
	return weechat.PLUGIN_RC_OK
# Config host checking
def checkhost(server,args):
	global hosts
	# Get current value
	checkhost = weechat.get_plugin_config("checkhost")
	# Testing / repairing
	if ( checkhost == "true" ):
		auto = True
	elif ( checkhost == "false" ):
		auto = False
	else:
		weechat.prnt("Unknown value ["+checkhost+"], disabling")
		weechat.set_plugin_config("checkhost","false")
		auto = False
	# Manage arg
	if ( args in yes ):
		if auto:
			weechat.prnt("Host checking remain enabled")
		else:
			weechat.set_plugin_config("checkhost","true")
			weechat.prnt("Host checking is now enabled")
	elif ( args in no ):
		if auto:
			weechat.set_plugin_config("checkhost","false")
			weechat.prnt("Host checking is now disabled")
		else:
			weechat.prnt("Host checking remain disabled")
		hosts = [[],[],[]]
	elif ( args == "list" ):
		if ( len(hosts[0]) > 0 ) :
			actualtime = round(time.time())
			weechat.prnt("Host list : ( host : last nick (age) )")
			for i in range(0, len(hosts[0])):
				weechat.prnt(" - "+hosts[0][i]+" : "+hosts[1][i]+" ("+str(actualtime - hosts[2][i])+")")
			weechat.prnt(len(hosts[0])+" saved hosts in list")
		else:
			weechat.prnt("No host in list")
	elif ( args == "clear" ):
		hosts = [[],[],[]]
	else: # "show", empty, other cases
		if auto:
			weechat.prnt("Host checking enabled")
		else:
			weechat.prnt("Host checking disabled")
	return weechat.PLUGIN_RC_OK
# Config servers to ignore
def toggle_ignore(server,arg):
	result = weechat.PLUGIN_RC_OK
	# Parse args
	args = arg.split(" ")
	if ( len(args) > 0 ):
		target = args[0]
	else:
		target = ""
	if ( len(args) > 1 ):
		action = args[1]
	else:
		action = ""
	if ( len(args) > 2 ):
		params = args[2:]
	else:
		params = []
	# Check target
	if ( target not in ["server","chan","nick","user","host"]):
		weechat.prnt("Unknown target '"+target+"', please use server, chan, host or nick")
		result = weechat.PLUGIN_RC_KO
	else:
		# Parse setting
		ignore_config = weechat.get_plugin_config(target+"_ignore")
		if ( ignore_config != "" ):
			ignore = ignore_config.split(" ")
		else:
			weechat.prnt("clone "+target+" ignore list not set, setting it empty")
			ignore = []
		# Manage action
		if ( action in ["view","show"] ):
			weechat.prnt("Current clone "+target+" ignore list : "+" ".join(ignore))
		elif ( action in ["+","add"] ):
			weechat.prnt("Adding to clone "+target+" ignore list : "+" ".join(params))
			if ( len(params) > 0 ):
				for i in params:
					if ( i in ignore ):
						weechat.prnt("Not adding "+i+" from clone "+target+" ignore list because it was in list")
					else:
						ignore.append(i)
			else:
				weechat.prnt("Nothing to add to clone "+target+" ignore list")
				result = weechat.PLUGIN_RC_KO
		elif ( action in ["-","del"] ):
			weechat.prnt("Deleting from clone "+target+" ignore list : "+" ".join(params))
			if ( len(params) > 0 ):
				for i in params:
					if ( i in ignore ):
						ignore.remove(i)
					else:
						weechat.prnt("Not removing "+i+" from clone "+target+" ignore list because it was not in list")
			else:
				weechat.prnt("Nothing to remove from clone "+target+" ignore list")
				result = weechat.PLUGIN_RC_KO
		elif ( action == "set" ):
			ignore = params
			weechat.prnt("Setting clone "+target+" ignores to : "+" ".join(ignore))
		else:
			weechat.prnt("Unknown action '"+action+"' ("+str(params)+"), please use view, add, del or set")
			result = weechat.PLUGIN_RC_KO
		# Synching new list with conf
		if ( len(ignore) > 2 ): # Sorting it if needed
			ignore.sort()
		new_ignore_config = " ".join(ignore)
		if ( new_ignore_config == ignore_config ):
			weechat.prnt("Clone "+target+" ignores list unchanged")
		else:
			if ( weechat.set_plugin_config(target+"_ignore",new_ignore_config) == 1 ):
				weechat.prnt("Clone "+target+" ignores list set to : "+new_ignore_config)
			else:
				weechat.prnt("Eror while setting clone "+target+" ignores list")
				result = weechat.PLUGIN_RC_KO
	return result
