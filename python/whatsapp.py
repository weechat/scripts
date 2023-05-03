# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Jochen Sprickerhof <weechat@jochen.sprickerhof.de>
# Copyright (C) 2009-2013 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2010 xt <xt@bash.no>
# Copyright (C) 2010 Aleksey V. Zapparov <ixti@member.fsf.org>
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
# whatsapp protocol for WeeChat.
# (this script requires WeeChat 2.9 (or newer) and the yowsup library)
#
# For help, see /help whatsapp
# Happy chat, enjoy :)
#
# History:
# 2022-07-17, Marcel Robohm <mrobohm@gmx.de>:
#     version 0.2: adapt to new yowsup version
# 2015-12-30, Jochen Sprickerhof <weechat@jochen.sprickerhof.de>:
#     version 0.1: Reworked for Whatsapp
# 2013-09-30, Nils Görs <freenode.nils_2>:
#     version 1.6: add support of /secure for passwords and jid
#                : fix stdout/stderr when no JID was set
# 2013-05-14, Billiam <billiamthesecond@gmail.com>:
#     version 1.5: fix unicode encoding error in /jabber buddies
# 2013-05-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.4: add tags in user messages: notify_xxx, no_highlight,
#                  nick_xxx, prefix_nick_xxx, log1
# 2012-05-12, Sebastian Rydberg <sr@rydbergtech.se>:
#     version 1.3: Added support for fetching names from roster
# 2012-04-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.2: fix deletion of server options
# 2012-03-09, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.1: fix reload of config file
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.0: changes for future compatibility with Python 3.x
# 2011-12-15, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.9: fix utf-8 encoding problem on jid
# 2011-03-21, Isaac Raway <isaac.raway@gmail.com>:
#     version 0.8: search chat buffer before opening it
# 2011-02-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: use new help format for command arguments
# 2010-11-23, xt
#     version 0.6: change format of sent ping, to match RFC
# 2010-10-05, xt, <xt@bash.no>
#     version 0.5: no highlight for status/presence messages
# 2010-10-01, xt, <xt@bash.no>
#     version 0.4:
#     add kick and invite
# 2010-08-03, Aleksey V. Zapparov <ixti@member.fsf.org>:
#     version 0.3:
#     add /jabber priority [priority]
#     add /jabber status [message]
#     add /jabber presence [online|chat|away|xa|dnd]
# 2010-08-02, Aleksey V. Zapparov <ixti@member.fsf.org>:
#     version 0.2.1:
#     fix prexence is set for current resource instead of sending
#         special presences for all buddies
# 2010-08-02, Aleksey V. Zapparov <ixti@member.fsf.org>:
#     version 0.2:
#     add priority and away_priority of resource
# 2010-08-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2010-08-01, ixti <ixti@member.fsf.org>:
#     fix bug with non-ascii resources
# 2010-06-09, iiijjjiii <iiijjjiii@gmail.com>:
#     add connect server and port options (required for google talk)
#     add private option permitting messages to be displayed in separate
#       chat buffers or in a single server buffer
#     add jid aliases
#     add keepalive ping
# 2010-03-17, xt <xt@bash.no>:
#     add autoreconnect option, autoreconnects on protocol error
# 2010-03-17, xt <xt@bash.no>:
#     add autoconnect option, add new command /jmsg with -server option
# 2009-02-22, Sebastien Helleu <flashcode@flashtux.org>:
#     first version (unofficial)
#

SCRIPT_NAME    = "whatsapp"
SCRIPT_AUTHOR  = "Jochen Sprickerhof <weechat@jochen.sprickerhof.de>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Whatsapp protocol for WeeChat"
SCRIPT_COMMAND = SCRIPT_NAME

import re

import_ok = True

try:
    import weechat
except:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

try:
    from yowsup.common import YowConstants
    from yowsup.layers import YowLayerEvent
    from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
    from yowsup.layers.network import YowNetworkLayer
    from yowsup.layers.protocol_profiles.protocolentities.iq_statuses_get import GetStatusesIqProtocolEntity
    from yowsup.layers.protocol_profiles.protocolentities.iq_statuses_result import ResultStatusesIqProtocolEntity
    from yowsup.layers.protocol_iq import YowIqProtocolLayer
    from yowsup.layers.protocol_iq.protocolentities.iq import IqProtocolEntity
    from yowsup.layers.protocol_iq.protocolentities.iq_ping import PingIqProtocolEntity
    from yowsup.layers.protocol_messages.protocolentities.message_text import TextMessageProtocolEntity
    from yowsup.layers.protocol_presence.protocolentities.presence_available import AvailablePresenceProtocolEntity
    from yowsup.layers.protocol_presence.protocolentities.presence_subscribe import SubscribePresenceProtocolEntity
    from yowsup.layers.protocol_presence.protocolentities.presence_unavailable import UnavailablePresenceProtocolEntity
    from yowsup.layers.protocol_presence.protocolentities.presence_unsubscribe import UnsubscribePresenceProtocolEntity
    from yowsup.layers.protocol_profiles.protocolentities import SetStatusIqProtocolEntity
    from yowsup.stacks import YowStackBuilder
except:
    print("Package python-yowsup (yowsup) must be installed to use whatsapp protocol.")
    print("Get yowsup with your package manager, or at this URL: https://github.com/tgalal/yowsup")
    import_ok = False

# ==============================[ global vars ]===============================

whatsapp_servers = []
whatsapp_server_options = {
    "jid"          : { "type"         : "string",
                       "desc"         : "whatsapp id (user@server.tld)",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "",
                       "value"        : "",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "password"     : { "type"         : "string",
                       "desc"         : "password for whatsapp id on server",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "",
                       "value"        : "",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "autoconnect"  : { "type"         : "boolean",
                       "desc"         : "automatically connect to server when script is starting",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "off",
                       "value"        : "off",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "autoreconnect": { "type"         : "boolean",
                       "desc"         : "automatically reconnect to server when disconnected",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "on",
                       "value"        : "on",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "private"      : { "type"         : "boolean",
                       "desc"         : "display messages in separate chat buffers instead of a single server buffer",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "on",
                       "value"        : "on",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "recipes"      : { "type"         : "boolean",
                       "desc"         : "Send recipes for messages",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "on",
                       "value"        : "on",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "read"         : { "type"         : "boolean",
                       "desc"         : "Send read notifications",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "on",
                       "value"        : "on",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "ping_interval": { "type"         : "integer",
                       "desc"         : "Number of seconds between server pings. 0 = disable",
                       "min"          : 0,
                       "max"          : 9999999,
                       "string_values": "",
                       "default"      : "50",
                       "value"        : "50",
                       "check_cb"     : "ping_interval_check_cb",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "ping_timeout" : { "type"         : "integer",
                       "desc"         : "Number of seconds to allow ping to respond before timing out",
                       "min"          : 0,
                       "max"          : 9999999,
                       "string_values": "",
                       "default"      : "10",
                       "value"        : "10",
                       "check_cb"     : "ping_timeout_check_cb",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    }
whatsapp_config_file = None
whatsapp_config_section = {}
whatsapp_config_option = {}
whatsapp_jid_aliases = {}             # { 'alias1': 'jid1', 'alias2': 'jid2', ... }

# =================================[ config ]=================================

def whatsapp_config_init():
    """ Initialize config file: create sections and options in memory. """
    global whatsapp_config_file, whatsapp_config_section
    whatsapp_config_file = weechat.config_new("whatsapp", "whatsapp_config_reload_cb", "")
    if not whatsapp_config_file:
        return
    # look
    whatsapp_config_section["look"] = weechat.config_new_section(
        whatsapp_config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "")
    if not whatsapp_config_section["look"]:
        weechat.config_free(whatsapp_config_file)
        return
    whatsapp_config_option["debug"] = weechat.config_new_option(
        whatsapp_config_file, whatsapp_config_section["look"],
        "debug", "boolean", "display debug messages", "", 0, 0,
        "off", "off", 0, "", "", "", "", "", "")
    # color
    whatsapp_config_section["color"] = weechat.config_new_section(
        whatsapp_config_file, "color", 0, 0, "", "", "", "", "", "", "", "", "", "")
    if not whatsapp_config_section["color"]:
        weechat.config_free(whatsapp_config_file)
        return
    whatsapp_config_option["message_join"] = weechat.config_new_option(
        whatsapp_config_file, whatsapp_config_section["color"],
        "message_join", "color", "color for text in join messages", "", 0, 0,
        "green", "green", 0, "", "", "", "", "", "")
    whatsapp_config_option["message_quit"] = weechat.config_new_option(
        whatsapp_config_file, whatsapp_config_section["color"],
        "message_quit", "color", "color for text in quit messages", "", 0, 0,
        "red", "red", 0, "", "", "", "", "", "")
    # server
    whatsapp_config_section["server"] = weechat.config_new_section(
        whatsapp_config_file, "server", 0, 0,
        "whatsapp_config_server_read_cb", "", "whatsapp_config_server_write_cb", "",
        "", "", "", "", "", "")
    if not whatsapp_config_section["server"]:
        weechat.config_free(whatsapp_config_file)
        return
    whatsapp_config_section["jid_aliases"] = weechat.config_new_section(
        whatsapp_config_file, "jid_aliases", 0, 0,
        "whatsapp_config_jid_aliases_read_cb", "",
        "whatsapp_config_jid_aliases_write_cb", "",
        "", "", "", "", "", "")
    if not whatsapp_config_section["jid_aliases"]:
        weechat.config_free(whatsapp_config_file)
        return

def whatsapp_config_reload_cb(data, config_file):
    """ Reload config file. """
    return weechat.config_reload(config_file)

def whatsapp_config_server_read_cb(data, config_file, section, option_name, value):
    """ Read server option in config file. """
    global whatsapp_servers
    rc = weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
    items = option_name.split(".", 1)
    if len(items) == 2:
        server = whatsapp_search_server_by_name(items[0])
        if not server:
            server = Server(items[0])
            whatsapp_servers.append(server)
            stackbuilder = YowStackBuilder()
            # disable status ping as weechat seems to have a problem with threads
            stackbuilder.setProp(YowIqProtocolLayer.PROP_PING_INTERVAL, 0)
            stackbuilder.pushDefaultLayers(True).push(server).build()
        if server:
            rc = weechat.config_option_set(server.options[items[1]], value, 1)
    return rc

def whatsapp_config_server_write_cb(data, config_file, section_name):
    """ Write server section in config file. """
    global whatsapp_servers
    weechat.config_write_line(config_file, section_name, "")
    for server in whatsapp_servers:
        for name, option in sorted(server.options.items()):
            weechat.config_write_option(config_file, option)
    return weechat.WEECHAT_RC_OK

def whatsapp_config_jid_aliases_read_cb(data, config_file, section, option_name, value):
    """ Read jid_aliases option in config file. """
    global whatsapp_jid_aliases
    whatsapp_jid_aliases[option_name] = value
    option = weechat.config_new_option(
        config_file, section,
        option_name, "string", "jid alias", "", 0, 0,
        "", value, 0, "", "", "", "", "", "")
    if not option:
        return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

def whatsapp_config_jid_aliases_write_cb(data, config_file, section_name):
    """ Write jid_aliases section in config file. """
    global whatsapp_jid_aliases
    weechat.config_write_line(config_file, section_name, "")
    for alias, jid in sorted(whatsapp_jid_aliases.items()):
        weechat.config_write_line(config_file, alias, jid)
    return weechat.WEECHAT_RC_OK

def whatsapp_config_read():
    """ Read whatsapp config file (whatsapp.conf). """
    global whatsapp_config_file
    return weechat.config_read(whatsapp_config_file)

def whatsapp_config_write():
    """ Write whatsapp config file (whatsapp.conf). """
    global whatsapp_config_file
    return weechat.config_write(whatsapp_config_file)

def whatsapp_debug_enabled():
    """ Return True if debug is enabled. """
    global whatsapp_config_options
    if weechat.config_boolean(whatsapp_config_option["debug"]):
        return True
    return False

def whatsapp_config_color(color):
    """ Return color code for a whatsapp color option. """
    global whatsapp_config_option
    if color in whatsapp_config_option:
        return weechat.color(weechat.config_color(whatsapp_config_option[color]))
    return ""

def ping_timeout_check_cb(server_name, option, value):
    global whatsapp_config_file, whatsapp_config_section
    ping_interval_option = weechat.config_search_option(
        whatsapp_config_file,
        whatsapp_config_section["server"],
        "%s.ping_interval" % (server_name)
        )
    ping_interval = weechat.config_integer(ping_interval_option)
    if int(ping_interval) and int(value) >= int(ping_interval):
        weechat.prnt("", "\nwhatsapp: unable to update 'ping_timeout' for server %s" % (server_name))
        weechat.prnt("", "whatsapp: to prevent multiple concurrent pings, ping_interval must be greater than ping_timeout")
        return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

def ping_interval_check_cb(server_name, option, value):
    global whatsapp_config_file, whatsapp_config_section
    ping_timeout_option = weechat.config_search_option(
        whatsapp_config_file,
        whatsapp_config_section["server"],
        "%s.ping_timeout" % (server_name)
        )
    ping_timeout = weechat.config_integer(ping_timeout_option)
    if int(value) and int(ping_timeout) >= int(value):
        weechat.prnt("", "\nwhatsapp: unable to update 'ping_interval' for server %s" % (server_name))
        weechat.prnt("", "whatsapp: to prevent multiple concurrent pings, ping_interval must be greater than ping_timeout")
        return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

# ================================[ servers ]=================================

class Server(YowInterfaceLayer):
    """ Class to manage a server: buffer, connection, send/recv data. """

    def __init__(self, name, **kwargs):
        """ Init server """
        global whatsapp_config_file, whatsapp_config_section, whatsapp_server_options

        super(Server, self).__init__()
        self.connected = False

        self.name = name
        # create options (user can set them with /set)
        self.options = {}
        # if the value is provided, use it, otherwise use the default
        values = {}
        for option_name, props in whatsapp_server_options.items():
            values[option_name] = props["default"]
        values['name'] = name
        values.update(**kwargs)
        for option_name, props in whatsapp_server_options.items():
            self.options[option_name] = weechat.config_new_option(
                whatsapp_config_file, whatsapp_config_section["server"],
                self.name + "." + option_name, props["type"], props["desc"],
                props["string_values"], props["min"], props["max"],
                props["default"], values[option_name], 0,
                props["check_cb"], self.name, props["change_cb"], "",
                props["delete_cb"], "")
        # internal data
        self.jid = None
        self.sock = None
        self.hook_fd = None
        self.buffer = ""
        self.chats = []
        self.buddies = []
        self.buddy = None
        self.ping_timer = None              # weechat.hook_timer for sending pings
        self.ping_timeout_timer = None      # weechat.hook_timer for monitoring ping timeout

    def option_string(self, option_name):
        """ Return a server option, as string. """
        return weechat.config_string(self.options[option_name])

    def option_boolean(self, option_name):
        """ Return a server option, as boolean. """
        return weechat.config_boolean(self.options[option_name])

    def option_integer(self, option_name):
        """ Return a server option, as string. """
        return weechat.config_integer(self.options[option_name])

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()
        if notificationData:
            weechat.prnt('', "Notification: %s" % notificationData)
        else:
            weechat.prnt('', "From :%s, Type: %s" % (notification.getFrom(), notification.getType()))
        if weechat.config_boolean(self.options['recipes']):
            self.toLower(notification.ack())

    def connect(self):
        """ Connect to whatsapp server. """
        if not self.buffer:
            bufname = "%s.server.%s" % (SCRIPT_NAME, self.name)
            self.buffer = weechat.buffer_search("python", bufname)
            if not self.buffer:
                self.buffer = weechat.buffer_new(bufname,
                                                 "whatsapp_buffer_input_cb", "",
                                                 "whatsapp_buffer_close_cb", "")
            if self.buffer:
                weechat.buffer_set(self.buffer, "short_name", self.name)
                weechat.buffer_set(self.buffer, "localvar_set_type", "server")
                weechat.buffer_set(self.buffer, "localvar_set_server", self.name)
                weechat.buffer_set(self.buffer, "nicklist", "1")
                weechat.buffer_set(self.buffer, "nicklist_display_groups", "1")
                weechat.buffer_set(self.buffer, "display", "auto")

        self.buddy = Buddy(jid=eval_expression(self.option_string("jid")), server=self)

        credentials = (eval_expression(self.option_string("jid")), eval_expression(self.option_string("password")))
        self.getStack().setCredentials(credentials)
        self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))

        # set blocking, so we don't send in the select loop as asyncore does it
        self.sock = self.getStack().getLayer(0).socket.setblocking(1)
        # push initial connect message through the socket (would have been done in the select loop otherwise
        self.getStack().getLayer(0).handle_write_event()

        self.sock = self.getStack().getLayer(0).socket.fileno()
        self.hook_fd = weechat.hook_fd(self.sock, 1, 0, 0, "whatsapp_fd_cb", "")

        weechat.buffer_set(self.buffer, "highlight_words", self.buddy.alias)
        weechat.buffer_set(self.buffer, "localvar_set_nick", self.buddy.alias)
        hook_away = weechat.hook_command_run("/away -all*", "whatsapp_away_command_run_cb", "")

        # Whatsapp doesn't send context, so we use aliases as contacts instead
        for jid in whatsapp_jid_aliases.values():
            if jid != self.buddy.jid:
                self.add_buddy(jid)

    def is_connected(self):
        """Return connect status"""
        if not self.connected:
            return False
        else:
            return True

    def add_chat(self, buddy):
        """Create a chat buffer for a buddy"""
        chat = Chat(self, buddy, switch_to_buffer=False)
        self.chats.append(chat)
        return chat

    def del_buddy(self, jid):
        """ Remove a buddy and/or deny authorization request """
        entity = UnsubscribePresenceProtocolEntity(jid)
        self.toLower(entity)

    def print_debug_server(self, message):
        """ Print debug message on server buffer. """
        if whatsapp_debug_enabled():
            weechat.prnt(self.buffer, "%swhatsapp: %s" % (weechat.prefix("network"), message))

    def print_debug_handler(self, handler_name, node):
        """ Print debug message for a handler on server buffer. """
        self.print_debug_server("%s_handler, xml message:\n%s"
                                % (handler_name, node))

    def print_error(self, message):
        """ Print error message on server buffer. """
        if whatsapp_debug_enabled():
            weechat.prnt(self.buffer, "%swhatsapp: %s" % (weechat.prefix("error"), message))

    @ProtocolEntityCallback("chatstate")
    def presence_handler(self, node):
        print(node)
        print(dir(node))
        self.print_debug_handler("presence", node)
        buddy = self.search_buddy_list(node.getFrom(), by='jid')
        if not buddy:
            buddy = self.add_buddy(jid=node.getFrom())
        action='update'
        node_type = node.getType()
        if node_type in ["error", "unavailable"]:
            action='remove'
        if action == 'update':
            away = node.getShow() in ["away", "xa"]
            status = ' '
            if node.getStatus():
                status = node.getStatus()
            buddy.set_status(status=status, away=away)
        self.update_nicklist(buddy=buddy, action=action)
        return

    @ProtocolEntityCallback("iq")
    def iq_handler(self, node):
        """ Receive iq message. """
        self.print_debug_handler("iq", node)
        #weechat.prnt(self.buffer, "whatsapp: iq handler")
        if isinstance(node, ResultStatusesIqProtocolEntity):
            for jid in node.statuses:
                buddy = self.search_buddy_list(jid, by='jid')
                if not buddy:
                    buddy = self.add_buddy(jid=jid)
                buddy.set_status(status=node.statuses[jid][0])

        elif isinstance(node, IqProtocolEntity):
            self.delete_ping_timeout_timer()    # Disable the timeout feature
            if not self.is_connected() and weechat.config_boolean(self.options['autoreconnect']):
                self.connect()

    def onEvent(self, layerEvent):
        weechat.prnt('', layerEvent.getName())
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_CONNECTED:
            self.connected = True
            return True
        elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            weechat.prnt('', "Disconnected: %s" % layerEvent.getArg("reason"))
            if not self.is_connected() and weechat.config_boolean(self.options['autoreconnect']):
                self.connect()
            return True

    @ProtocolEntityCallback("message")
    def message_handler(self, node):
        """ Receive message. """
        self.print_debug_handler("message", node)
        messageOut = ""
        if node.getType() == "text":
            messageOut = self.getTextMessageBody(node)
        elif node.getType() == "media":
            messageOut = self.getMediaMessageBody(node)
        else:
            messageOut = "Unknown message type %s " % node.getType()
            self.print_debug_handler("send", messageOut.toProtocolTreeNode())

        jid = node.getFrom() if not node.isGroupMessage() else "%s/%s" % (node.getParticipant(False), node.getFrom())
        body = messageOut

        if weechat.config_boolean(self.options['recipes']):
            self.toLower(node.ack(weechat.config_boolean(self.options['recipes'])))
            self.print_debug_handler("Sent delivered receipt", "Message %s" % node.getId())

        if not jid or not body:
            return
        buddy = self.search_buddy_list(jid, by='jid')
        if not buddy:
            buddy = self.add_buddy(jid=jid)
        # If a chat buffer exists for the buddy, receive the message with that
        # buffer even if private is off. The buffer may have been created with
        # /query.
        recv_object = self
        if not buddy.chat and weechat.config_boolean(self.options['private']):
            self.add_chat(buddy)
        if buddy.chat:
            recv_object = buddy.chat
        recv_object.recv_message(buddy, body)

    def getTextMessageBody(self, message):
        return message.getBody()

    def getMediaMessageBody(self, message):
        if message.getMediaType() in ("image", "audio", "video"):
            return self.getDownloadableMediaMessageBody(message)
        else:
            return "Media Type: %s" % message.getMediaType()

    def getDownloadableMediaMessageBody(self, message):
        return "Media Type:{media_type}, Size:{media_size}, URL:{media_url}".format(
            media_type=message.getMediaType(),
            media_size=message.getMediaSize(),
            media_url=message.getMediaUrl()
        )

    def recv(self):
        """ Receive something from whatsapp server. """
        self.getStack().getLayer(0).handle_read()

    def recv_message(self, buddy, message):
        """ Receive a message from buddy. """
        weechat.prnt_date_tags(self.buffer, 0,
                               "notify_private,nick_%s,prefix_nick_%s,log1" %
                               (buddy.alias,
                                weechat.config_string(weechat.config_get("weechat.color.chat_nick_other"))),
                               "%s%s\t%s" % (weechat.color("chat_nick_other"),
                                             buddy.alias,
                                             message))

    def print_status(self, nickname, status):
        """ Print a status in server window and in chat. """
        weechat.prnt_date_tags(self.buffer, 0, "no_highlight", "%s%s has status %s" %
                               (weechat.prefix("action"),
                                nickname,
                                status))
        for chat in self.chats:
            if nickname in chat.buddy.alias:
                chat.print_status(status)
                break

    def send_message(self, buddy, message):
        """ Send a message to buddy.

        The buddy argument can be either a jid string,
        eg username@domain.tld/resource or a Buddy object instance.
        """
        recipient = buddy
        if isinstance(buddy, Buddy):
            recipient = buddy.jid
        if not self.is_connected():
            weechat.prnt(self.buffer, "%swhatsapp: unable to send message, connection is down"
                         % weechat.prefix("error"))
            return
        outgoingMessage = TextMessageProtocolEntity(message, to=self.stringify_jid(recipient))
        self.toLower(outgoingMessage)

    def send_message_from_input(self, input=''):
        """ Send a message from input text on server buffer. """
        # Input must be of format "name: message" where name is a jid, bare_jid
        # or alias. The colon can be replaced with a comma as well.
        # Split input into name and message.
        if not re.compile(r'.+[:,].+').match(input):
            weechat.prnt(self.buffer, "%swhatsapp: %s" % (weechat.prefix("network"),
                "Invalid send format. Use  jid: message"
                ))
            return
        name, message = re.split('[:,]', input, maxsplit=1)
        buddy = self.search_buddy_list(name, by='alias')
        if not buddy:
            weechat.prnt(self.buffer,
                    "%swhatsapp: Invalid jid: %s" % (weechat.prefix("network"),
                    name))
            return
        # Send activity indicates user is no longer away, set it so
        if self.buddy and self.buddy.away:
            self.set_away('')
        self.send_message(buddy=buddy, message=message)
        try:
            sender = self.buddy.alias
        except:
            sender = self.jid
        weechat.prnt_date_tags(self.buffer, 0,
                               "notify_none,no_highlight,nick_%s,prefix_nick_%s,log1" %
                               (sender,
                                weechat.config_string(weechat.config_get("weechat.color.chat_nick_self"))),
                               "%s%s\t%s" % (weechat.color("chat_nick_self"),
                                             sender,
                                             message.strip()))

    def set_away(self, message):
        """ Set/unset away on server.

        If a message is provided, status is set to 'away'.
        If no message, then status is set to 'online'.
        """
        if message:
            entity = UnavailablePresenceProtocolEntity()
            self.toLower(entity)
        else:
            entity = AvailablePresenceProtocolEntity()
            self.toLower(entity)
        self.set_presence(message)

    def set_presence(self, status=None):
        message = status if status else ''
        entity = SetStatusIqProtocolEntity(message)
        self.toLower(entity)

    def add_buddy(self, jid):
        """ Add a new buddy """
        full_jid = self.stringify_jid(jid)
        entity = SubscribePresenceProtocolEntity(full_jid)
        self.toLower(entity)
        entity = GetStatusesIqProtocolEntity([full_jid])
        self.toLower(entity)

        buddy = Buddy(jid=jid, server=self)
        self.buddies.append(buddy)
        self.update_nicklist(buddy=buddy, action='update')
        return buddy

    def display_buddies(self):
        """ Display buddies. """
        weechat.prnt(self.buffer, "")
        weechat.prnt(self.buffer, "Buddies:")

        len_max = { 'alias': 5, 'jid': 5 }
        lines = []
        for buddy in sorted(self.buddies, key=lambda x: x.jid.getStripped()):
            alias = ''
            if buddy.alias != buddy.jid:
                alias = buddy.alias
            buddy_jid_string = buddy.jid.getStripped()
            lines.append( {
                'jid': buddy_jid_string,
                'alias': alias,
                'status': buddy.away_string(),
                })
            if len(alias) > len_max['alias']:
                len_max['alias'] = len(alias)
            if len(buddy_jid_string) > len_max['jid']:
                len_max['jid'] = len(buddy_jid_string)
        prnt_format = "  %s%-" + str(len_max['jid']) + "s %-" + str(len_max['alias']) + "s %s"
        weechat.prnt(self.buffer, prnt_format % ('', 'JID', 'Alias', 'Status'))
        for line in lines:
            weechat.prnt(self.buffer, prnt_format % (weechat.color("chat_nick"),
                                                    line['jid'],
                                                    line['alias'],
                                                    line['status'],
                                                    ))

    def stringify_jid(self, jid):
        """ Serialise JID into string.

        Args:
            jid: xmpp.protocol.JID, JID instance to serialize

        Notes:
            Method is based on original JID.__str__ but with hack to allow
            non-ascii in resource names.
        """
        if '@' in jid:
            return jid
        elif "-" in jid:
            return "%s@g.us" % jid

        return "%s@s.whatsapp.net" % jid

    def search_buddy_list(self, name, by='jid'):
        """ Search for a buddy by name.

        Args:
            name: string, the buddy name to search, eg the jid or alias
            by: string, either 'alias' or 'jid', determines which Buddy
                property to match on, default 'jid'

        Notes:
            If the 'by' parameter is set to 'jid', the search matches on all
            Buddy object jid properties, followed by all bare_jid properties.
            Once a match is found it is returned.

            If the 'by' parameter is set to 'alias', the search matches on all
            Buddy object alias properties.

            Generally, set the 'by' parameter to 'jid' when the jid is provided
            from a server, for example from a received message. Set 'by' to
            'alias' when the jid is provided by the user.
        """
        if by == 'jid':
            for buddy in self.buddies:
                if self.stringify_jid(buddy.jid) == name:
                    return buddy
            for buddy in self.buddies:
                if buddy.jid == name:
                    return buddy
        else:
            for buddy in self.buddies:
                if buddy.alias == name:
                    return buddy
        return None

    def update_nicklist(self, buddy=None, action=None):
        """Update buddy in nicklist
            Args:
                buddy: Buddy object instance
                action: string, one of 'update' or 'remove'
        """
        if not buddy:
            return
        if not action in ['remove', 'update']:
            return
        ptr_nick_gui = weechat.nicklist_search_nick(self.buffer, "", buddy.alias)
        weechat.nicklist_remove_nick(self.buffer, ptr_nick_gui)
        msg = ''
        prefix = ''
        color = ''
        away = ''
        if action == 'update':
            nick_color = "bar_fg"
            if buddy.away:
                nick_color = "weechat.color.nicklist_away"
            weechat.nicklist_add_nick(self.buffer, "", buddy.alias,
                                      nick_color, "", "", 1)
            if not ptr_nick_gui:
                msg = 'joined'
                prefix = 'join'
                color = 'message_join'
                away = buddy.away_string()
        if action == 'remove':
            msg = 'quit'
            prefix = 'quit'
            color = 'message_quit'
        if msg:
            weechat.prnt(self.buffer, "%s%s%s%s has %s %s"
                         % (weechat.prefix(prefix),
                            weechat.color("chat_nick"),
                            buddy.alias,
                            whatsapp_config_color(color),
                            msg,
                            away))
        return

    def add_ping_timer(self):
        if self.ping_timer:
            self.delete_ping_timer()
        if not self.option_integer('ping_interval'):
            return
        self.ping_timer = weechat.hook_timer( self.option_integer('ping_interval') * 1000,
                0, 0, "whatsapp_ping_timer", self.name)
        return

    def delete_ping_timer(self):
        if self.ping_timer:
            weechat.unhook(self.ping_timer)
        self.ping_timer = None
        return

    def add_ping_timeout_timer(self):
        if self.ping_timeout_timer:
            self.delete_ping_timeout_timer()
        if not self.option_integer('ping_timeout'):
            return
        self.ping_timeout_timer = weechat.hook_timer(
                self.option_integer('ping_timeout') * 1000, 0, 1,
                "whatsapp_ping_timeout_timer", self.name)
        return

    def delete_ping_timeout_timer(self):
        if self.ping_timeout_timer:
            weechat.unhook(self.ping_timeout_timer)
        self.ping_timeout_timer = None
        return

    def ping(self):
        if not self.is_connected():
            if not self.connect():
                return
        iq = PingIqProtocolEntity(to = YowConstants.DOMAIN)
        self.toLower(iq)
        self.print_debug_handler("ping", iq)
        self.add_ping_timeout_timer()
        return

    def ping_time_out(self):
        self.delete_ping_timeout_timer()
        # A ping timeout indicates a server connection problem. Disconnect
        # completely.
        self.disconnect()
        return

    def disconnect(self):
        """ Disconnect from whatsapp server. """
        if self.hook_fd != None:
            weechat.unhook(self.hook_fd)
            self.hook_fd = None
        self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        self.jid = None
        self.sock = None
        self.buddy = None
        weechat.nicklist_remove_all(self.buffer)

    def close_buffer(self):
        """ Close server buffer. """
        if self.buffer != "":
            weechat.buffer_close(self.buffer)
            self.buffer = ""

    def delete(self, deleteOptions=False):
        """ Delete server. """
        for chat in self.chats:
            chat.delete()
        self.delete_ping_timer()
        self.delete_ping_timeout_timer()
        self.disconnect()
        self.close_buffer()
        if deleteOptions:
            for name, option in self.options.items():
                weechat.config_option_free(option)

def eval_expression(option_name):
    """ Return a evaluated expression """
    if int(version) >= 0x00040200:
        return weechat.string_eval_expression(option_name,{},{},{})
    else:
        return option_name

def whatsapp_search_server_by_name(name):
    """ Search a server by name. """
    global whatsapp_servers
    for server in whatsapp_servers:
        if server.name == name:
            return server
    return None

def whatsapp_search_context(buffer):
    """ Search a server / chat for a buffer. """
    global whatsapp_servers
    context = { "server": None, "chat": None }
    for server in whatsapp_servers:
        if server.buffer == buffer:
            context["server"] = server
            return context
        for chat in server.chats:
            if chat.buffer == buffer:
                context["server"] = server
                context["chat"] = chat
                return context
    return context

def whatsapp_search_context_by_name(server_name):
    """Search for buffer given name of server. """

    bufname = "%s.server.%s" % (SCRIPT_NAME, server_name)
    return whatsapp_search_context(weechat.buffer_search("python", bufname))


# =================================[ chats ]==================================

class Chat:
    """ Class to manage private chat with buddy or MUC. """

    def __init__(self, server, buddy, switch_to_buffer):
        """ Init chat """
        self.server = server
        self.buddy = buddy
        buddy.chat = self
        bufname = "%s.%s.%s" % (SCRIPT_NAME, server.name, self.buddy.alias)
        self.buffer = weechat.buffer_search("python", bufname)
        if not self.buffer:
            self.buffer = weechat.buffer_new(bufname,
                                             "whatsapp_buffer_input_cb", "",
                                             "whatsapp_buffer_close_cb", "")
        self.buffer_title = self.buddy.alias
        if self.buffer:
            weechat.buffer_set(self.buffer, "title", self.buffer_title)
            weechat.buffer_set(self.buffer, "short_name", self.buddy.alias)
            weechat.buffer_set(self.buffer, "localvar_set_type", "private")
            weechat.buffer_set(self.buffer, "localvar_set_server", server.name)
            weechat.buffer_set(self.buffer, "localvar_set_channel", self.buddy.alias)
            weechat.hook_signal_send("logger_backlog",
                                     weechat.WEECHAT_HOOK_SIGNAL_POINTER, self.buffer)
            if switch_to_buffer:
                weechat.buffer_set(self.buffer, "display", "auto")

    def recv_message(self, buddy, message):
        """ Receive a message from buddy. """
        if buddy.alias != self.buffer_title:
            self.buffer_title = buddy.alias
            weechat.buffer_set(self.buffer, "title", "%s" % self.buffer_title)
        weechat.prnt_date_tags(self.buffer, 0,
                               "notify_private,nick_%s,prefix_nick_%s,log1" %
                               (buddy.alias,
                                weechat.config_string(weechat.config_get("weechat.color.chat_nick_other"))),
                               "%s%s\t%s" % (weechat.color("chat_nick_other"),
                                             buddy.alias,
                                             message))

    def send_message(self, message):
        """ Send message to buddy. """
        if not self.server.is_connected():
            weechat.prnt(self.buffer, "%swhatsapp: unable to send message, connection is down"
                         % weechat.prefix("error"))
            return
        self.server.send_message(self.buddy, message)
        weechat.prnt_date_tags(self.buffer, 0,
                               "notify_none,no_highlight,nick_%s,prefix_nick_%s,log1" %
                               (self.server.buddy.alias,
                                weechat.config_string(weechat.config_get("weechat.color.chat_nick_self"))),
                               "%s%s\t%s" % (weechat.color("chat_nick_self"),
                                             self.server.buddy.alias,
                                             message))
    def print_status(self, status):
        """ Print a status message in chat. """
        weechat.prnt(self.buffer, "%s%s has status %s" %
                     (weechat.prefix("action"),
                      self.buddy.alias,
                      status))

    def close_buffer(self):
        """ Close chat buffer. """
        if self.buffer != "":
            weechat.buffer_close(self.buffer)
            self.buffer = ""

    def delete(self):
        """ Delete chat. """
        self.close_buffer()

# =================================[ buddies ]==================================

class Buddy:
    """ Class to manage buddies. """
    def __init__(self, jid=None, chat=None, server=None ):
        """ Init buddy

        Args:
            jid: xmpp.protocol.JID object instance or string
            chat: Chat object instance
            server: Server object instance

        The jid argument can be provided either as a xmpp.protocol.JID object
        instance or as a string, eg "username@domain.tld/resource". If a string
        is provided, it is converted and stored as a xmpp.protocol.JID object
        instance.
        """

        # The jid argument of xmpp.protocol.JID can be either a string or a
        # xmpp.protocol.JID object instance itself.
        self.jid = jid
        self.chat = chat
        self.server = server
        self.name = ''
        self.alias = ''
        self.away = True
        self.status = ''

        self.set_alias()
        return

    def away_string(self):
        """ Return a string with away and status, with color codes. """
        if not self:
            return ''
        if not self.away:
            return ''
        str_colon = ": "
        if not self.status:
            str_colon = ""
        status = self.status.replace('\n', ' ') if self.status else ''
        return "%s(%saway%s%s%s)" % (weechat.color("chat_delimiters"),
                                      weechat.color("chat"),
                                      str_colon,
                                      status,
                                      weechat.color("chat_delimiters"))

    def set_alias(self):
        """Set the buddy alias.

        If an alias is defined in whatsapp_jid_aliases, it is used. Otherwise the
        alias is set to self.jid or self.name if it exists.
        """
        self.alias = self.jid
        if not self.jid:
            self.alias = ''
        if self.name:
            self.alias = self.name
        global whatsapp_jid_aliases
        for alias, jid in whatsapp_jid_aliases.items():
            if jid == self.jid:
                self.alias = alias
                break
        return

    def set_name(self, name=''):
        self.name = name
        self.set_alias()
        return

    def set_status(self, away=True, status=''):
        """Set the buddy status.

        Two properties define the buddy status.
            away - boolean, indicates whether the buddy is away or not.
            status - string, a message indicating the away status, eg 'in a meeting'
                   Comparable to xmpp presence <status/> element.
        """
        if not away and not status:
            status = 'online'
        # If the status has changed print a message on the server buffer
        if self.away != away or self.status != status:
            self.server.print_status(self.alias, status)
        self.away = away
        self.status = status
        return

# ================================[ commands ]================================

def whatsapp_hook_commands_and_completions():
    """ Hook commands and completions. """
    weechat.hook_command(SCRIPT_COMMAND, "Manage whatsapp servers",
                         "list || add <name> <jid> <password>"
                         " || connect|disconnect|del [<server>] || alias [add|del <alias> <jid>]"
                         " || away [<message>] || buddies ||"
                         " || status [<message>]"
                         " || debug || set <server> <setting> [<value>]",
                         "      list: list servers and chats\n"
                         "       add: add a server\n"
                         "   connect: connect to server using password\n"
                         "disconnect: disconnect from server\n"
                         "       del: delete server\n"
                         "     alias: manage jid aliases\n"
                         "      away: set away with a message (if no message, away is unset)\n"
                         "    status: set status message\n"
                         "   buddies: display buddies on server\n"
                         "     debug: toggle whatsapp debug on/off (for all servers)\n"
                         "\n"
                         "Without argument, this command lists servers and chats.\n"
                         "\n"
                         "Examples:\n"
                         "  Add a server:       /whatsapp add myserver user@server.tld password\n"
                         "  Add gtalk server:   /whatsapp add myserver user@gmail.com password talk.google.com:5223\n"
                         "  Connect to server:  /whatsapp connect myserver\n"
                         "  Disconnect:         /whatsapp disconnect myserver\n"
                         "  Delete server:      /whatsapp del myserver\n"
                         "\n"
                         "Aliases:\n"
                         "  List aliases:    /whatsapp alias \n"
                         "  Add an alias:    /whatsapp alias add alias_name jid\n"
                         "  Delete an alias: /whatsapp alias del alias_name\n"
                         "\n"
                         "Other whatsapp commands:\n"
                         "  Chat with a buddy (pv buffer): /query\n"
                         "  Add buddy to roster:           /winvite\n"
                         "  Remove buddy from roster:      /wkick\n"
                         "  Send message to buddy:         /wmsg",
                         "list %(whatsapp_servers)"
                         " || add %(whatsapp_servers)"
                         " || connect %(whatsapp_servers)"
                         " || disconnect %(whatsapp_servers)"
                         " || del %(whatsapp_servers)"
                         " || alias add|del %(whatsapp_jid_aliases)"
                         " || away"
                         " || status"
                         " || buddies"
                         " || debug",
                         "whatsapp_cmd_whatsapp", "")
    weechat.hook_command("query", "Chat with a whatsapp buddy",
                         "<buddy>",
                         "buddy: buddy id",
                         "",
                         "whatsapp_cmd_query", "")
    weechat.hook_command("wmsg", "Send a message to a buddy",
                         "[-server <server>] <buddy> <text>",
                         "server: name of whatsapp server buddy is on\n"
                         " buddy: buddy id\n"
                         "  text: text to send",
                         "",
                         "whatsapp_cmd_wmsg", "")
    weechat.hook_command("winvite", "Add a buddy to your roster",
                         "<buddy>",
                         "buddy: buddy id",
                         "",
                         "whatsapp_cmd_winvite", "")
    weechat.hook_command("wkick", "Remove a buddy from your roster, or deny auth",
                         "<buddy>",
                         "buddy: buddy id",
                         "",
                         "whatsapp_cmd_wkick", "")
    weechat.hook_completion("whatsapp_servers", "list of whatsapp servers",
                            "whatsapp_completion_servers", "")
    weechat.hook_completion("whatsapp_jid_aliases", "list of whatsapp jid aliases",
                            "whatsapp_completion_jid_aliases", "")

def whatsapp_list_servers_chats(name):
    """ List servers and chats. """
    global whatsapp_servers
    weechat.prnt("", "")
    if len(whatsapp_servers) > 0:
        weechat.prnt("", "whatsapp servers:")
        for server in whatsapp_servers:
            if name == "" or server.name.find(name) >= 0:
                conn_server = ''
                connected = ""
                if server.sock >= 0:
                    connected = "(connected)"

                weechat.prnt("", "  %s - %s %s %s" % (server.name,
                    eval_expression(server.option_string("jid")), conn_server, connected))
                for chat in server.chats:
                    weechat.prnt("", "    chat with %s" % (chat.buddy))
    else:
        weechat.prnt("", "whatsapp: no server defined")

def whatsapp_cmd_whatsapp(data, buffer, args):
    """ Command '/whatsapp'. """
    global whatsapp_servers, whatsapp_config_option
    if args == "" or args == "list":
        whatsapp_list_servers_chats("")
    else:
        argv = args.split(" ")
        argv1eol = ""
        pos = args.find(" ")
        if pos > 0:
            argv1eol = args[pos+1:]
        if argv[0] == "list":
            whatsapp_list_servers_chats(argv[1])
        elif argv[0] == "add":
            if len(argv) >= 4:
                server = whatsapp_search_server_by_name(argv[1])
                if server:
                    weechat.prnt("", "whatsapp: server '%s' already exists" % argv[1])
                else:
                    kwargs = {'jid': argv[2], 'password': argv[3]}
                    server = Server(argv[1], **kwargs)
                    whatsapp_servers.append(server)
                    stackbuilder = YowStackBuilder()
                    # disable status ping as weechat seems to have a problem with threads
                    stackbuilder.setProp(YowIqProtocolLayer.PROP_PING_INTERVAL, 0)
                    stackbuilder.pushDefaultLayers(True).push(server).build()
                    weechat.prnt("", "whatsapp: server '%s' created" % argv[1])
            else:
                weechat.prnt("", "whatsapp: unable to add server, missing arguments")
                weechat.prnt("", "whatsapp: usage: /whatsapp add name jid password")
        elif argv[0] == "alias":
            alias_command = AliasCommand(buffer, argv=argv[1:])
            alias_command.run()
        elif argv[0] == "connect":
            server = None
            if len(argv) >= 2:
                server = whatsapp_search_server_by_name(argv[1])
                if not server:
                    weechat.prnt("", "whatsapp: server '%s' not found" % argv[1])
            else:
                context = whatsapp_search_context(buffer)
                if context["server"]:
                    server = context["server"]
            if server:
                if weechat.config_boolean(server.options['autoreconnect']):
                    server.ping()               # This will connect and update ping status
                    server.add_ping_timer()
                else:
                    server.connect()
        elif argv[0] == "disconnect":
            server = None
            if len(argv) >= 2:
                server = whatsapp_search_server_by_name(argv[1])
                if not server:
                    weechat.prnt("", "whatsapp: server '%s' not found" % argv[1])
            else:
                context = whatsapp_search_context(buffer)
                if context["server"]:
                    server = context["server"]
            context = whatsapp_search_context(buffer)
            if server:
                server.delete_ping_timer()
                server.disconnect()
        elif argv[0] == "del":
            if len(argv) >= 2:
                server = whatsapp_search_server_by_name(argv[1])
                if server:
                    server.delete(deleteOptions=True)
                    whatsapp_servers.remove(server)
                    weechat.prnt("", "whatsapp: server '%s' deleted" % argv[1])
                else:
                    weechat.prnt("", "whatsapp: server '%s' not found" % argv[1])
        elif argv[0] == "send":
            if len(argv) >= 3:
                context = whatsapp_search_context(buffer)
                if context["server"]:
                    buddy = context['server'].search_buddy_list(argv[1], by='alias')
                    message = ' '.join(argv[2:])
                    context["server"].send_message(buddy, message)
        elif argv[0] == "read":
            whatsapp_config_read()
        elif argv[0] == "away":
            context = whatsapp_search_context(buffer)
            if context["server"]:
                context["server"].set_away(argv1eol)
        elif argv[0] == "status":
            context = whatsapp_search_context(buffer)
            if context["server"]:
                if len(argv) == 1:
                    weechat.prnt("", "whatsapp: status = %s" % context["server"].presence.getStatus())
                else:
                    context["server"].set_presence(status=argv1eol)
        elif argv[0] == "buddies":
            context = whatsapp_search_context(buffer)
            if context["server"]:
                context["server"].display_buddies()
        elif argv[0] == "debug":
            weechat.config_option_set(whatsapp_config_option["debug"], "toggle", 1)
            if whatsapp_debug_enabled():
                weechat.prnt("", "whatsapp: debug is now ON")
            else:
                weechat.prnt("", "whatsapp: debug is now off")
        else:
            weechat.prnt("", "whatsapp: unknown action")
    return weechat.WEECHAT_RC_OK

def whatsapp_cmd_query(data, buffer, args):
    """ Command '/query'. """
    if args:
        context = whatsapp_search_context(buffer)
        if context["server"]:
            buddy = context["server"].search_buddy_list(args, by='alias')
            if not buddy:
                buddy = context["server"].add_buddy(jid=args)
            if not buddy.chat:
                context["server"].add_chat(buddy)
            weechat.buffer_set(buddy.chat.buffer, "display", "auto")
    return weechat.WEECHAT_RC_OK

def whatsapp_cmd_wmsg(data, buffer, args):
    """ Command '/wmsg'. """
    if args:
        argv = args.split()
        if len(argv) < 2:
            return weechat.WEECHAT_RC_OK
        if argv[0] == '-server':
            context = whatsapp_search_context_by_name(argv[1])
            recipient = argv[2]
            message = " ".join(argv[3:])
        else:
            context = whatsapp_search_context(buffer)
            recipient = argv[0]
            message = " ".join(argv[1:])
        if context["server"]:
            buddy = context['server'].search_buddy_list(recipient, by='alias')
            context["server"].send_message(buddy, message)

    return weechat.WEECHAT_RC_OK

def whatsapp_cmd_winvite(data, buffer, args):
    """ Command '/winvite'. """
    if args:
        context = whatsapp_search_context(buffer)
        if context["server"]:
            context["server"].add_buddy(args)
    return weechat.WEECHAT_RC_OK

def whatsapp_cmd_wkick(data, buffer, args):
    """ Command '/wkick'. """
    if args:
        context = whatsapp_search_context(buffer)
        if context["server"]:
            context["server"].del_buddy(args)
    return weechat.WEECHAT_RC_OK

def whatsapp_away_command_run_cb(data, buffer, command):
    """ Callback called when /away -all command is run """
    global whatsapp_servers
    words = command.split(None, 2)
    if len(words) < 2:
        return
    message = ''
    if len(words) > 2:
        message = words[2]
    for server in whatsapp_servers:
        server.set_away(message)
    return weechat.WEECHAT_RC_OK

class AliasCommand(object):
    """Class representing a whatsapp alias command, ie /whatsapp alias ..."""

    def __init__(self, buffer, argv=None):
        """
        Args:
            bufffer: the weechat buffer the command was run in
            argv: list, the arguments provided with the command.
                  Example, if the command is "/whatsapp alias add abc abc@server.tld"
                  argv = ['add', 'abc', 'abc@server.tld']
        """
        self.buffer = buffer
        self.argv = []
        if argv:
            self.argv = argv
        self.action = ''
        self.jid = ''
        self.alias = ''
        self.parse()
        return

    def add(self):
        """Run a "/whatsapp alias add" command"""
        global whatsapp_jid_aliases
        if not self.alias or not self.jid:
            weechat.prnt("", "\nwhatsapp: unable to add alias, missing arguments")
            weechat.prnt("", "whatsapp: usage: /whatsapp alias add alias_name jid")
            return
        # Restrict the character set of aliases. The characters must be writable to
        # config file.
        invalid_re = re.compile(r'[^a-zA-Z0-9\[\]\\\^_\-{|}@\.]')
        if invalid_re.search(self.alias):
            weechat.prnt("", "\nwhatsapp: invalid alias: %s" % self.alias)
            weechat.prnt("", "whatsapp: use only characters: a-z A-Z 0-9 [ \ ] ^ _ - { | } @ .")
            return
        # Ensure alias and jid are reasonable length.
        max_len = 64
        if len(self.alias) > max_len:
            weechat.prnt("", "\nwhatsapp: invalid alias: %s" % self.alias)
            weechat.prnt("", "whatsapp: must be no more than %s characters long" % max_len)
            return
        if len(self.jid) > max_len:
            weechat.prnt("", "\nwhatsapp: invalid jid: %s" % self.jid)
            weechat.prnt("", "whatsapp: must be no more than %s characters long" % max_len)
            return
        jid = self.jid
        alias = self.alias
        if alias in whatsapp_jid_aliases.keys():
            weechat.prnt("", "\nwhatsapp: unable to add alias: %s" % (alias))
            weechat.prnt("", "whatsapp: alias already exists, delete first")
            return
        if jid in whatsapp_jid_aliases.values():
            weechat.prnt("", "\nwhatsapp: unable to add alias: %s" % (alias))
            for a, j in whatsapp_jid_aliases.items():
                if j == jid:
                    weechat.prnt("", "whatsapp: jid '%s' is already aliased as '%s', delete first" %
                        (j, a))
                    break
        whatsapp_jid_aliases[alias] = jid
        self.alias_reset(jid)
        return

    def alias_reset(self, jid):
        """Reset objects related to the jid modified by an an alias command

        Update any existing buddy objects, server nicklists, and chat objects
        that may be using the buddy with the provided jid.
        """
        global whatsapp_servers
        for server in whatsapp_servers:
            buddy = server.search_buddy_list(jid, by='jid')
            if not buddy:
                continue
            server.update_nicklist(buddy=buddy, action='remove')
            buddy.set_alias()
            server.update_nicklist(buddy=buddy, action='update')
            if buddy.chat:
                switch_to_buffer = False
                if buddy.chat.buffer == self.buffer:
                    switch_to_buffer = True
                buddy.chat.delete()
                new_chat = server.add_chat(buddy)
                if switch_to_buffer:
                    weechat.buffer_set(new_chat.buffer, "display", "auto")
        return

    def delete(self):
        """Run a "/whatsapp alias del" command"""
        global whatsapp_jid_aliases
        if not self.alias:
            weechat.prnt("", "\nwhatsapp: unable to delete alias, missing arguments")
            weechat.prnt("", "whatsapp: usage: /whatsapp alias del alias_name")
            return
        if not self.alias in whatsapp_jid_aliases:
            weechat.prnt("", "\nwhatsapp: unable to delete alias '%s', not found" % (self.alias))
            return
        jid = whatsapp_jid_aliases[self.alias]
        del whatsapp_jid_aliases[self.alias]
        self.alias_reset(jid)
        return

    def list(self):
        """Run a "/whatsapp alias" command to list aliases"""
        global whatsapp_jid_aliases
        weechat.prnt("", "")
        if len(whatsapp_jid_aliases) <= 0:
            weechat.prnt("", "whatsapp: no aliases defined")
            return
        weechat.prnt("", "whatsapp jid aliases:")
        len_alias = 5
        len_jid = 5
        for alias, jid in whatsapp_jid_aliases.items():
            if len_alias < len(alias):
                len_alias = len(alias)
            if len_jid < len(jid):
                len_jid = len(jid)
        prnt_format = "  %-" + str(len_alias) + "s %-" + str(len_jid) + "s"
        weechat.prnt("", prnt_format % ('Alias', 'JID'))
        for alias, jid in sorted(whatsapp_jid_aliases.items()):
            weechat.prnt("", prnt_format % (alias, jid))
        return

    def parse(self):
        """Parse the alias command into components"""
        if len(self.argv) <= 0:
            return
        self.action = self.argv[0]
        if len(self.argv) > 1:
            # Pad argv list to prevent IndexError exceptions
            while len(self.argv) < 3: self.argv.append('')
            self.alias = self.argv[1]
            self.jid = self.argv[2]
        return

    def run(self):
        """Execute the alias command."""
        if self.action == 'add':
            self.add()
        elif self.action == 'del':
            self.delete()
        self.list()
        return

def whatsapp_completion_servers(data, completion_item, buffer, completion):
    """ Completion with whatsapp server names. """
    global whatsapp_servers
    for server in whatsapp_servers:
        weechat.completion_list_add(completion, server.name,
                                    0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def whatsapp_completion_jid_aliases(data, completion_item, buffer, completion):
    """ Completion with whatsapp alias names. """
    global whatsapp_jid_aliases
    for alias, jid in sorted(whatsapp_jid_aliases.items()):
        weechat.completion_list_add(completion, alias,
                                    0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

# ==================================[ fd ]====================================

def whatsapp_fd_cb(data, fd):
    """ Callback for reading socket. """
    global whatsapp_servers
    for server in whatsapp_servers:
        if server.sock == int(fd):
            server.recv()
    return weechat.WEECHAT_RC_OK

# ================================[ buffers ]=================================

def whatsapp_buffer_input_cb(data, buffer, input_data):
    """ Callback called for input data on a whatsapp buffer. """
    context = whatsapp_search_context(buffer)
    if context["server"] and context["chat"]:
        context["chat"].send_message(input_data)
    elif context["server"]:
        if input_data == "buddies" or "buddies".startswith(input_data):
            context["server"].display_buddies()
        else:
            context["server"].send_message_from_input(input=input_data)
    return weechat.WEECHAT_RC_OK

def whatsapp_buffer_close_cb(data, buffer):
    """ Callback called when a whatsapp buffer is closed. """
    context = whatsapp_search_context(buffer)
    if context["server"] and context["chat"]:
        if context["chat"].buddy:
            context["chat"].buddy.chat = None
        context["chat"].buffer = ""
        context["server"].chats.remove(context["chat"])
    elif context["server"]:
        context["server"].buffer = ""
    return weechat.WEECHAT_RC_OK

# ==================================[ timers ]==================================

def whatsapp_ping_timeout_timer(server_name, remaining_calls):
    server = whatsapp_search_server_by_name(server_name)
    if server:
        server.ping_time_out()
    return weechat.WEECHAT_RC_OK

def whatsapp_ping_timer(server_name, remaining_calls):
    server = whatsapp_search_server_by_name(server_name)
    if server:
        server.ping()
    return weechat.WEECHAT_RC_OK

# ==================================[ main ]==================================

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "whatsapp_unload_script", ""):

        version = weechat.info_get("version_number", "") or 0
        whatsapp_hook_commands_and_completions()
        whatsapp_config_init()
        whatsapp_config_read()
        for server in whatsapp_servers:
            if weechat.config_boolean(server.options['autoreconnect']):
                server.ping()               # This will connect and update ping status
                server.add_ping_timer()
            else:
                if weechat.config_boolean(server.options['autoconnect']):
                    server.connect()

# ==================================[ end ]===================================

def whatsapp_unload_script():
    """ Function called when script is unloaded. """
    global whatsapp_servers
    whatsapp_config_write()
    for server in whatsapp_servers:
        server.disconnect()
        server.delete()
    return weechat.WEECHAT_RC_OK
