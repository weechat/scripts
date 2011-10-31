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
#IMPORTANT:
#use of this script assumes that you have:
#1) /usr/bin/notify-send
#2) ssh configured to use key identification
#
#ALSO IMPORTANT:
#see comments below in the default settings section for description of options
#and tips. pay particular attention to the addresses section if you need to
#specify non-default ports or non-default display settings
#
#NOT so important:
#if you define icons to show up in the notifications, this script will expect
#to find them in the same place on all systems. missing icons will not stop the
#notification from displaying, however.

import weechat, string, subprocess, re

weechat.register("sshnotify", "delwin", "0.2.0", "GPL3", "A notify script for weechat based on lnotify.py", "", "")

# Set up here, go no further!
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
                                        #if you need to specify a different display, add DISPLAY=:1 (or the appropriate number)
                                        #by default, sshnotify will use DISPLAY=:0
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
        return []
    else:
        return addies.split(',')

def get_ignore():
    ignores = weechat.config_get_plugin('ignore')
    if ignores == '':
        return []
    else:
        return ignores.split(',')


def get_notified(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):

    ilist = get_ignore()
    for i in ilist:
        if re.search(i,prefix + ": " + message):
            return weechat.WEECHAT_RC_OK

    extracommands = weechat.config_get_plugin('extra_commands')
    dispnum = "DISPLAY=:0"

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

        if buffer == prefix:
          #the ' character currently needs changed to something else or the message formatting fails
          #substituting " for '
            prefix = re.sub("'",'"',prefix)
          #escaping all special characters so that the message formatting doesn't fail
            prefix = re.escape(prefix)
            message = re.sub("'",'"',message)
            message = re.escape(message)
          #setting the command which will be passed by ssh to push the notification
            disp = '"/usr/bin/notify-send ' + uistring + '\'In PM\' \'' + prefix + ': ' + message + '\' ' + extracommands + '\"'

          #fire when ready
            alist = get_addresses()
            for a in alist:
                if a != '':
                    if re.search('DISPLAY\=',a):
                        dispnum = ""
                    com = "ssh -X " + a + " " + dispnum + " "
                    weechat.hook_process(com + disp, 5000, "", "")
                    #print(com + disp)
                else:
                    #todo - add error message that actually works
                    #weechat.prnt("You need to enter at least one address (with ssh options) to notify via /set plugins.var.python.sshnotify.addresses foo@bar.com,foo@bar2.com,-p 1234 foo@bar3.com")
                    return weechat.WEECHAT_RC_OK


    elif (ishilight == "1" and
            weechat.config_get_plugin('show_highlight') == "on"):
        buffer = (weechat.buffer_get_string(bufferp, "short_name") or
                weechat.buffer_get_string(bufferp, "name"))
        buffer = re.sub("'",'"',buffer)
        buffer = re.escape(buffer)
        prefix = re.sub("'",'"',prefix)
        prefix = re.escape(prefix)
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

        disp = '"/usr/bin/notify-send ' + uistring + '\'In ' + buffer + '\' \'' + prefix + ': ' + message + '\'' + extracommands + '\"'
        alist = get_addresses()
        for a in alist:
            if a != '':
                if re.search('DISPLAY\=',a):
                    dispnum = ""
                com = "ssh -X " + a + " " + dispnum + " "
                weechat.hook_process(com + disp, 5000, "", "")
                #print(com + disp)
            else:
                #todo - print error message which actually works
                #weechat.prnt("You need to enter at least one address (with ssh options) to notify via /set plugins.var.python.sshnotify.addresses foo@bar.com,foo@bar2.com,-p 1234 foo@bar3.com")
                return weechat.WEECHAT_RC_OK

    return weechat.WEECHAT_RC_OK


