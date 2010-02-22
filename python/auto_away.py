# auto_away.py : A simple auto-away script for Weechat in Python 
# Copyright (c) 2010 by Specimen <spinifer at gmail dot com>
#
# Inspired in yaaa.pl by jnbek
# A very special thanks to Nils G. for helping me out with this script
# ---------------------------------------------------------------------
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
#
#
# This script requires WeeChat 0.3.0 or newer.
# 
# ---------------------------------------------------------------------
#
# Summary:
#
#   Sets status to away automatically after a given period of 
#   inactivity. Returns from away when you start typing, but not when
#   you change buffer or scroll. 
#
# Configuration:
#
#   /autoaway [time|off] [message]
#
#      time: minutes of inactivity to set away
#       off: disable auto-away (0 also disables)
#   message: away message (optional)
#
#
# Configuration options via /set:
#
# 'idletime'
#   description: Period in minutes (n) of keyboard inactivity until 
#                being marked as being away.
#                Setting idletime to "0", a negative number or a string
#                such as "off" disables auto-away. All positive values 
#                are treated as they integers.
#   command: /set plugins.var.python.auto_away.idletime n
# 
# 'message'
#   description: Away message.
#   command: /set plugins.var.python.auto_away.message "message"
#   
# 'hookinterval'
#   description: Frequency of hook_timer checks (n), default is 10,
#                change to 5 if you feel it doesn't update fast enough.
#   command: /set plugins.var.python.auto_away.hookinterval "n"
#
#
# Changelog:
#
#   2010-02-11 - 0.1    - Script created.
#   2010-02-11 - 0.1.1  - Various fixes with the help of Flashcode
#   2010-02-13 - 0.2    - Option to disable autoaway, return from away
#                         via hook_signal as suggested by Nils G.
#                         No longer uses plugin configuration to store
#                         away status.
#   2010-02-15 - 0.2.2  - Use hook_config to check idletime and
#                         enable/disable hook_timer.
#   2010-02-15 - 0.2.3  - Removed away_status.  
#   2010-02-17 - 0.2.4  - Implemented better code logic.
#   2010-02-20 - 0.2.5  - "import weechat as w", better feedback 
#                         messages format mimicks away local messages.
#   2010-02-21 - 0.3    - Implemented /autoaway command.                           

try:
    import weechat as w
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()

# Script registration
w.register("auto_away",
           "Specimen",
           "0.3",
           "GPL3", 
           "Simple auto-away script in Python", "", "")


# AutoawayCommand
w.hook_command("autoaway", 
               "Set away status automatically after a period of "
               "inactivity.", 
               "[time|off] [message]", 
               "      time: minutes of inactivity to set away\n"
               "       off: disable auto-away (0 also disables)\n"
               "   message: away message (optional)\n"
               "\n"
               "Examples:\n"
               "\n"
               "/autoaway 20 I'm away\n"
               "Sets auto-away to 20 minutes, and away message to "
               "'I'm away'.\n"
               "\n"
               "/autoaway 30\n"
               "Sets auto-away to 30 minutes, and uses the previously "
               "set, or default, away message.\n"
               "\n"
               "/autoaway off\n"
               "/autoaway 0\n"
               "Disables auto-away.\n"
               "\n",
               "", 
               "autoaway_cmd", "")


# Default Settings
idletime = "20"
message = "Idle"
hookinterval = "10"

# Register configuration	
if not w.config_get_plugin('idletime'): 
    w.config_set_plugin('idletime', idletime)
	
if not w.config_get_plugin('message'): 
    w.config_set_plugin('message', message)

if not w.config_get_plugin('hookinterval'): 
    w.config_set_plugin('hookinterval', hookinterval)


# autoaway command
def autoaway_cmd(data, buffer, args):

    value_arg = str(args.split(' ')[0])
    message_arg = str(args.strip(value_arg).strip(' '))
    
    if args == "":
        w.command("", "/help autoaway")

    else:
        w.config_set_plugin('idletime', value_arg)
        if message_arg != "":
            w.config_set_plugin('message', message_arg)
            w.prnt(w.current_buffer(), 
                   "%s[%saway message is: %s %s]"
                   % (w.color("green"), w.color("chat"),
                   message_arg, w.color("green")))
        
    return w.WEECHAT_RC_OK

# Run/Check autoaway enable/disabled/value
def away_chk():

    try:
        int_idletime = int(w.config_get_plugin('idletime'))
        
        if int_idletime > 0:
            w.prnt(w.current_buffer(), 
                   "%s[%s%sauto-away%s is set to %s%s%s minute(s)%s]"
                   % (w.color("green"), w.color("chat"), 
                   w.color("bold"), w.color("-bold"), w.color("bold"),
                   int_idletime, w.color("-bold"), w.color("green")))
            timer_func()
            return w.WEECHAT_RC_OK
            
    except ValueError:
        w.prnt(w.current_buffer(),
               "%s[%s%sauto-away%s is disabled%s]"
               % (w.color("green"), w.color("chat"),w.color("bold"),
               w.color("-bold"),w.color("green")))
        return w.WEECHAT_RC_OK

    w.prnt(w.current_buffer(),
           "%s[%s%sauto-away%s is disabled%s]"
           % (w.color("green"), w.color("chat"),w.color("bold"),
           w.color("-bold"),w.color("green")))
    return w.WEECHAT_RC_OK


# On idletime change reset hooks, rerun away_chk
def switch_chk(data, option, value):

    global timer_hook, input_hook

    try:
        w.unhook(timer_hook)
        w.unhook(input_hook)
        away_chk()
        
    except NameError:
        away_chk()
        
    return w.WEECHAT_RC_OK


# Define hooks
def timer_func():

    global timer_hook

    timer_hook = w.hook_timer(int(w.config_get_plugin('hookinterval'))
                              * 1000, 60, 0, "idle_chk", "")
    return w.WEECHAT_RC_OK


def input_func():

    global input_hook

    input_hook = w.hook_signal("input_text_changed",
                               "typing_chk", "")
    return w.WEECHAT_RC_OK
    

# Inactivity check routine
def idle_chk(data, remaining_calls):

    global timer_hook
    
    int_idletime = int(w.config_get_plugin('idletime'))
    
    if int_idletime > 0:
        if int(w.info_get("inactivity", "")) >= int_idletime * 60:
            w.unhook(timer_hook)
            w.command("", "/away -all %s" 
                      % w.config_get_plugin('message'))
            input_func()

    return w.WEECHAT_RC_OK

# Return from away routine
def typing_chk(data, signal, signal_data):

    global input_hook

    w.unhook(input_hook)
    w.command("", "/away -all")
    timer_func()

    return w.WEECHAT_RC_OK


# Check idletime value
w.hook_config("plugins.var.python.auto_away.idletime",
              "switch_chk", "")

# Start timer hook
away_chk()
