#
# Copyright (C) 2013 Ruben van Os (TheLastProject) <rubenvanos@gmx.com>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#
# Add users relayed to the nicklist in a triggersafe channel

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    exit()

weechat.register("triggerbot_helper", "Ruben van Os (TheLastProject)", "0.2", "GPL3", "Register nicknames relayed to in triggerbot's triggersafe channels nicklist", "shutdown", "")

# Check WeeChat version and only register hook if not too outdated
version = weechat.info_get("version_number", "") or 0
if int(version) < 0x00030400:
    weechat.prnt("", "Your version of WeeChat is too old. This script requires at least version 0.3.4 or newer.")
else:
    weechat.hook_signal("*,irc_in2_privmsg", "check_message", "")

triggerbotbuffers = {}

def check_message(data, signal, signal_data):
    dict = weechat.info_get_hashtable("irc_message_parse",
                                      {"message": signal_data})
    nick = dict["nick"]
    channel = dict["channel"]
    if nick == "triggerbot":
        try:
            if channel.split("_")[1]:
                triggersafechannel = True
        except IndexError:
            triggersafechannel = False
        if triggersafechannel:
            buffer = weechat.info_get("irc_buffer", "%s,%s" % (signal.split(",")[0], channel))
            group = weechat.nicklist_search_group(buffer, "", "triggerbot")
            if not group:
                group = weechat.nicklist_add_group(buffer, "", "triggerbot", "weechat.color.nicklist_group", 1)
                triggerbotbuffers[buffer] = group
            # Is this a list of nicks?
            if dict["arguments"].find("Nicks %s: [" % channel) != -1:
                names = dict["arguments"].split("Nicks %s: [" % channel)[1].split("]")[0].split(" ")
                set_nicklist(names, buffer, group)
            # Is this a join message?
            elif dict["arguments"].split(":")[1].startswith("[INFO] ") and dict["arguments"].find(" has joined") != -1:
                name = dict["arguments"].split("[INFO] ")[1].split(" has joined")[0]
                add_nick(name, buffer, group)
            # A leave message?
            elif dict["arguments"].split(":")[1].startswith("[INFO] ") and dict["arguments"].find(" has left") != -1:
                name = dict["arguments"].split("[INFO] ")[1].split(" has left")[0]
                remove_nick(name, buffer, group)
            # A quit message? (Don't search for the dot here because a reason may be displayed)
            elif dict["arguments"].split(":")[1].startswith("[INFO] ") and dict["arguments"].find(" has quit") != -1:
                name = dict["arguments"].split("[INFO] ")[1].split(" has quit")[0]
                remove_nick(name, buffer, group)
            elif dict["arguments"].split(":")[1].startswith("[INFO] ") and dict["arguments"].find(" is now known as ") != -1:
                oldname = dict["arguments"].split("[INFO] ")[1].split(" is now known as ")[0]
                newname = dict["arguments"].split("[INFO] ")[1].split(" is now known as ")[1].split(".")[0]
                remove_nick(oldname, buffer, group)
                add_nick(newname, buffer, group)
    return weechat.WEECHAT_RC_OK

def set_nicklist(names, buffer, group):
    for name in names:
        add_nick(name, buffer, group)
    return weechat.WEECHAT_RC_OK

def add_nick(name, buffer, group):
    if not weechat.nicklist_search_nick(buffer, "", name):
        weechat.nicklist_add_nick(buffer, group, name, "weechat.color.nicklist_group", " ", "lightgreen", 1)
    return weechat.WEECHAT_RC_OK

def remove_nick(name, buffer, group):
    pointer = weechat.nicklist_search_nick(buffer, "", name)
    if pointer:
        weechat.nicklist_remove_nick(buffer, pointer)
    return weechat.WEECHAT_RC_OK

def shutdown():
    for buffer in triggerbotbuffers:
        weechat.nicklist_remove_group(buffer, triggerbotbuffers[buffer])
    return weechat.WEECHAT_RC_OK
