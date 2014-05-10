# -*- coding: utf-8 -*-
# Copyright (C) 2011  delwin <delwin@skyehaven.net>
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
#based on the 'lnotify' script for weechat, which was based on 'notify'
#
#the main reason to use this script would be if you use tmux or screen
#with weechat and would like to receive desktop notifications on multiple
#computers (regardless of whether or not you are connected to weechat on
#any of those systems.) however, there is a reason to use this if you
#only use one system for weechat. if you restart X and then reconnect
#to weechat, notifications will no longer work because of dbus errors.
#this solution solves that problem at the expense of some extra setup.
#
#IMPORTANT:
#use of this script assumes that you have:
#1) /usr/bin/notify-send
#2) ssh configured to use key identification (including localhost!)
#
#ALSO IMPORTANT:
#see comments below in the default settings section for description of options
#and tips. pay particular attention to the addresses section if you need to
#specify non-default ports or non-default display settings
#
#NOT so important:
#if you define icons to show up in the notifications, this script will expect
#to find them in the same place on all systems. missing icons will not stop the
#notification from displaying, however. (this also applies for any extra
#commands you add to be executed after notify-send. sound files and utilities
#have to exist on the machine receiving the command in order to work)
#
#
#changelog:
#v0.2.3 - Sébastien Helleu <flashcode@flashtux.org>
#         change hook_print callback argument type of displayed/highlight
#         (WeeChat >= 1.0)
#v0.2.2 - <ldvx@freenode> fixed bug in (1)  which didn't allow user to get
#         notifications on private messages if irc.look.nick_prefix or
#         irc.look.nick_suffix were used. (2012-04-27)
#v0.2.1 - added help messages and hint for empty addresses option (2011-10-15)
#v0.2.0 - added several options, including: proper weechat options
#         for multiple addresses, ignore strings, urgencies, images,
#         and extra commands to be sent along with notifications.
#         shifted handling of DISPLAY to the address portion of the command.
#         submitted to weechat scripts. (2011-10-14)
#v0.1.0 - converted lnotify to work via ssh. accepts multiple addresses
#         hardcoded into the script. (2011-09-18)
#
#TODO... if i get bored enough/anyone actually requests these things:
#         add notification whitelist, only send notifications matching whitelist
#         set up proper /sshnotify <args> command to manually send notifications
#         set up new definitions for messages so that extra_commands can use them?
#         toggle to suppress notifications when away
#         toggle to show server and channel names in notifications
#         toggle to show notifications for dcc?
#
import weechat, string, subprocess, re

weechat.register("sshnotify", "delwin", "0.2.3", "GPL3", "the overkill desktop notification solution", "", "")

#options which can be defined with /set plugins.var.python.sshnotify.foo
settings = {
    "show_highlight"     : "on", #trigger on highlighted nick/word
    "show_priv_msg"      : "on", #trigger on private message
    "ignore"             : "", #comma seperated list of strings to ignore,
                               #e.g. if using bitlbee, you might want to add
                               #'@root: jabber,@root: otr' to avoid spam on startup
    "pm-urgency"         : "critical", #notification urgency for private messages. valid values are: low,normal,critical
    "pm-image"           : "", #location of notification icon for private messages, optional
    "mention-urgency"    : "normal", #notification urgency for highlighted strings, valid values are: low,normal,critical
    "mention-image"      : "", #location of notification icon for highlighted strings, optional
    "extra_commands"     : "", #extra commands to pass via ssh, appeneded after notify command.
                               #note: you need to include && to execute the commands sequentially
                               #for example, in order to have espeak announce that you have a new message and then play an audio file:
                               #/set plugins.var.python.sshnotify.extra_commands && espeak 'hey, you have a new message' && aplay whatever.wav'
    "addresses"          : "localhost", #comma delimited lists of addresses (and options) to use via ssh
                                        #default is localhost. if no address is specified, this script won't do anything for you
                                        #if you set addresses to "", it will reset to localhost the next time it loads.
                                        #if you need to specify a different display, add DISPLAY=:1 (or the appropriate number)
                                        #by default, sshnotify will use DISPLAY=:0, so there is no need to specify that in your address string
                                        #other ssh options can be added to each address:
                                        #/set plugins.var.python.sshnotify.addresses localhost,foo@bar,-p 1234 bar@foo DISPLAY=:1
                                        #will send a notification to 3 places, you@localhost, foot@bar, and bar@foo on port 1234 on display 1

}

# Init everything
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

# Hook privmsg/hilights
weechat.hook_print("", "irc_privmsg", "", 1, "get_notified", "")

# Functions

def get_addresses():
    addies = weechat.config_get_plugin('addresses')
    if addies == '':
        weechat.prnt("","You need to specify a destination if you want notifications sent. ")
        weechat.prnt("","hint: /set plugins.var.python.sshnotify.addresses localhost")
        return []
    else:
        return addies.split(',')

#if there are any strings
def get_ignore():
    ignores = weechat.config_get_plugin('ignore')
    if ignores == '':
        return []
    else:
        return ignores.split(',')

#notification routine
def get_notified(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    #if message contains and ignored string, don't send the notification
    ilist = get_ignore()
    for i in ilist:
        if re.search(i,prefix + ": " + message):
            return weechat.WEECHAT_RC_OK

    extracommands = weechat.config_get_plugin('extra_commands')
    #set a default value for DISPLAY. this should be fine for almost everyone
    dispnum = "DISPLAY=:0"

    #if the message came in via private message...
    if (weechat.buffer_get_string(bufferp, "localvar_type") == "private" and
            weechat.config_get_plugin('show_priv_msg') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))

        #set notification image
        if weechat.config_get_plugin('pm-image') != "":
            imagestring = "--icon=" + str(weechat.config_get_plugin('pm-image')) + " "
        else:
            imagestring = ""

        #set notification urgency
        if weechat.config_get_plugin('pm-urgency') == "low":
            urgencystring = "--urgency=low "
        elif weechat.config_get_plugin('pm-urgency') == "critical":
            urgencystring = "--urgency=critical "
        else:
            urgencystring = "--urgency=normal "

        uistring = urgencystring + imagestring

        # (1) if buffer == prefix was used here, pressumibly to avoid notifications when on own
        # messages, checking for the tag notify_private has the same effect, and the user can
        # set irc.look.nick_suffix or irc.look.nick_prefix this way.
        if "notify_private" in tagsn.split(","):
            #the ' character currently needs changed to something else or the message formatting fails
            #substituting " for '
            #notification title
            prefix = re.sub("'",'"',prefix)
            #escaping all special characters so that the message formatting doesn't fail
            prefix = re.escape(prefix)
            #notification message
            message = re.sub("'",'"',message)
            message = re.escape(message)
            #setting the command which will be passed by ssh to push the notification
            #note the DISPLAY variable is now accounted for in the ssh part of the command rather than this location
            disp = '"/usr/bin/notify-send ' + uistring + '\'In PM\' \'' + prefix + ': ' + message + '\' ' + extracommands + '\"'

          #fire when ready
            alist = get_addresses()
            for a in alist:
                if a != '':
                    #first check to see if DISPLAY is set in an address listing
                    if re.search('DISPLAY\=',a):
                        #if yes, do not set the default value defined above
                        dispnum = ""
                    #generate the ssh portion of the command to send
                    com = "ssh -X " + a + " " + dispnum + " "
                    #add all the bits together and send the notification. time out if it can't connect in 5 seconds
                    weechat.hook_process(com + disp, 5000, "", "")
                    #just a debug message
                    #print(com + disp)


    #if the message comes from a highlight rather than private message
    elif (int(ishilight) and
            weechat.config_get_plugin('show_highlight') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        #convert ' to " and escape special characters so the ssh command doesn't puke
        buffer = re.sub("'",'"',buffer)
        buffer = re.escape(buffer)
        #notification title
        prefix = re.sub("'",'"',prefix)
        prefix = re.escape(prefix)
        #notification message
        message = re.sub("'",'"',message)
        message = re.escape(message)

        #set notification image
        if weechat.config_get_plugin('mention-image') != "":
            imagestring = "--icon=" + weechat.config_get_plugin('mention-image') + " "
        else:
            imagestring = ""

        #set notification urgency
        if weechat.config_get_plugin('mention-urgency') == "low":
            urgencystring = "--urgency=low "
        elif weechat.config_get_plugin('mention-urgency') == "critical":
            urgencystring = "--urgency=critical "
        else:
            urgencystring = "--urgency=normal "

        uistring = urgencystring + imagestring
        #adding the notify-send command bits together
        disp = '"/usr/bin/notify-send ' + uistring + '\'In ' + buffer + '\' \'' + prefix + ': ' + message + '\'' + extracommands + '\"'

        #decide where to send the notification
        alist = get_addresses()
        for a in alist:
            if a != '':
                #if display is set in the address, do not apply default value defined above
                if re.search('DISPLAY\=',a):
                    dispnum = ""
                #adding the ssh command bits together
                com = "ssh -X " + a + " " + dispnum + " "
                #add all the bits together and send the notification. timeout in 5 seconds
                weechat.hook_process(com + disp, 5000, "", "")
                #just a debug message
                #print(com + disp)


    return weechat.WEECHAT_RC_OK

#right now this is just to enable /help sshnotify
#might be a better way to do this but i might extend it
#to allow /sshnotify to send notications directly with
#arguments as the messages
def notifying(data,buffer,args):
    weechat.prnt("","the command /sshnotify won't do much for you...yet. see /help sshnotify for info on how to use this plugin")
    return weechat.WEECHAT_RC_OK

#the help message from /help sshnotify
hook = weechat.hook_command(
    "sshnotify","overkill desktop notification","",
"""
  This script allows you to send desktop
  notifications of private messages and
  highlighted strings to one or more
  computers via ssh. This script expects
  ssh key identification to be set up and
  /usr/bin/notify-send on the systems to
  which you are sending notifications.

  It is quite configurable, allowing you
  to specify any ssh options you might find
  necessary (e.g. custom ports and
  non-default DISPLAY settings.) It allows
  you to specify strings to be ignored to
  help cut down on notification spam. Both
  of these settings accept comma delimited lists.

  Examples:
  for multiple ssh connections:
  /set plugins.var.python.sshnotify.addresses
      localhost,foo@bar,-p 1234 bar@foo DISPLAY=:1
  (sends notifications to you@localhost, foo@bar,
   and bar@foo on port 1234 at DISPLAY 1)

  for multiple ignore values:
  /set plugins.var.python.sshnotify.ignore
      @root: jabber,@root: otr,ignore this string
  (I use these values to eliminate notification
   spam from bitlbee when I connect)

  It also allows you to chain extra commands
  to be executed after the notify-send command,
  like so:
  /set plugins.var.python.sshnotify.extra_commands
      && espeak 'you have a new message && aplay somerandom.wav
  (note: this is not comma delimited and expects '&&'
   in front of any command you wish to execute,
   including the first one.)

  You can also set the urgency level and icons
  used for private messages or highlighted
  strings (the 'mention' configure options.)
  Valid urgency levels are 'low','normal', and
  'critical'. Icons need to be on the system
  receiving the notification in order to display,
  but if they are missing it does not interfere
  with the functionality of this script.

  I should also note that apostrophes in messages
  will be converted to double quotes in your
  notifications due to formatting issues with
  the ssh/notify-send command.
    """
    ,"",'notifying','')
