# -*- coding: utf-8 -*-

# =============================================================================
#  autoauth.py (c) October 2005 by kolter <kolter@openics.org>
#  Python script for WeeChat.
#
#  Licence     : GPL v2
#  Description : Permits to auto-authenticate when changing nick
#  Syntax      : try /autoauth help to get help on this script
#
#
# ### changelog ###
#
#  * version 1.1 (CrazyCat <crazycat@c-p-f.org>)
#      - add a way to manage NickServ nick and host
#  * version 1.0 (Simmo Saan <simmo.saan@gmail.com>)
#      - rename command /auth to /autoauth
#  * version 0.10 (Felix Eckhofer <felix@tribut.de>)
#      - fix "/auth cmd" commandline parsing
#  * version 0.9 (Felix Eckhofer <felix@tribut.de>)
#      - fix commands execution
#      - force correct server for /quote
#  * version 0.8 (excalibr@freenode)
#      - respond only to notice message from NickServ
#  * version 0.7 (Adam Spiers <weechat@adamspiers.org>)
#      - allow commas in passwords
#      - fix for FreeNode
#  * version 0.6 (CrazyCat <crazycat@c-p-f.org>)
#      - adaptation for weechat 0.3.0
#  * version 0.5
#      - fix bug when script script is run for first time
#      - rewrite half script to improve access to settings
#      - add a feature to permit to run command(s) when identified
#      - add completion for commands
#  * version 0.4
#      - use set_plugin_config and get_plugin_config to read ans save settings
#      - remove deprecated import
#  * version 0.3
#      - add return codes
#  * version 0.2
#      - correct weechatdir with weechat_dir while using weechat.get_info
#  * version 0.1 :
#      - first release
#
# =============================================================================


VERSION="1.2"
NAME="autoauth"
AUTHOR="Kolter"

DELIMITER="|@|"

import_ok = True
try:
    import weechat
except:
    print "Script must be run under weechat. https://weechat.org"
    import_ok = False

import re

weechat.register (NAME, AUTHOR, VERSION, "GPL2", "Auto authentification while changing nick", "", "")

weechat.hook_signal("*,irc_in2_notice", "auth_notice_check", "")
weechat.hook_command(
    "autoauth",
    "Auto authentification while changing nick",
    "{ add $nick $pass [$server=current] | del $nick [$server=current] | list | cmd [$command [$server=current]] | ns [$Nick[!username[@host]]] [$server=current] }",
    "  add : add authorization for $nick with password $pass for $server\n"
    "  del : del authorization for $nick for $server\n"
    " list : list all authorization settings\n"
    "  cmd : command(s) (separated by '|') to run when identified for $server\n"
    "         %n will be replaced by current nick in each command\n"
    "   ns : set NickServ mask (or part of mask) for $server, the NickServ nick is mandatory",
    "add|del|list|cmd %- %S %S",
    "auth_command",
    ""
    )

def auth_cmdlist():
    cmd = ''
    cmds = weechat.config_get_plugin("commands")
    if cmds == '':
        weechat.prnt("", "[%s] commands (empty)" % (NAME))
    else:
        weechat.prnt("", "[%s] commands (list)" % (NAME))
        for c in cmds.split("####"):
            weechat.prnt("", "  --> %s : '%s' " % (c.split(":::")[0], c.split(":::")[1]))

def auth_cmdget(server):
    cmd = ''
    cmds = weechat.config_get_plugin("commands")
    if cmds != '':
        for c in cmds.split("####"):
            if c.find(":::") != -1:
                if c.split(":::")[0] == server:
                    cmd = ":::".join(c.split(":::")[1:])
                    break
    return cmd

def auth_cmdset(server, command):
    cmds = weechat.config_get_plugin("commands")

    found = False
    conf = []
    if cmds != '':
        for c in cmds.split("####"):
            if c.find(":::") != -1:
                if c.split(":::")[0] == server:
                    found = True
                    conf.append("%s:::%s" % (server, command))
                else:
                    conf.append(c)
    if not found:
        conf.append("%s:::%s" % (server, command))

    weechat.config_set_plugin("commands", "####".join(conf))
    weechat.prnt("", "[%s] command '%s' successfully added for server %s" % (NAME, command, server))

def auth_cmdunset(server):
    cmds = weechat.config_get_plugin("commands")

    found = False
    conf = []
    if cmds != '':
        for c in cmds.split("####"):
            if c.find(":::") != -1:
                if c.split(":::")[0] != server:
                    conf.append(c)
                else:
                    found = True
    if found:
        weechat.prnt("", "[%s] command for server '%s' successfully removed" % (NAME, server))
        weechat.config_set_plugin("commands", "####".join(conf))

def auth_cmd(args, server):
    if server == '':
        if args == '':
            auth_cmdlist()
        else:
            weechat.prnt("", "[%s] error while setting command, can't find a server" % (NAME))
    else:
        if args == '':
            auth_cmdunset(server)
        else:
            auth_cmdset(server, args)

def auth_list():
    data = weechat.config_get_plugin("data")

    if data == "":
        weechat.prnt("", "[%s] accounts (empty)" % (NAME))
    else:
        weechat.prnt("", "[%s] accounts (list)" % (NAME))
        for e in data.split(DELIMITER):
            if e.find("=") == -1:
                continue
            (serv_nick, passwd) = e.split("=")
            (server, nick) = serv_nick.split(".")
            weechat.prnt("", "  --> %s@%s " % (nick, server))

def auth_notice_check(data, buffer, args):
    server = buffer.split(',')[0]
    nickserv = auth_nsget(server)
    (nnick, nhost) = nickserv.split("!")
    if args.startswith(":"+nickserv) and args.find("/msg NickServ IDENTIFY") != -1:
      #args.find("If this is your nickname, type /msg NickServ") != -1 or args.find("This nickname is registered") != -1 :
        passwd = auth_get(weechat.info_get("irc_nick", server), server)
        if passwd != None:
            weechat.command(server, "/quote -server %s %s identify %s" % (server, nnick, passwd))
            commands = auth_cmdget(server)
            if commands != '':
                for c in commands.split("|"):
                    weechat.command(server, c.strip().replace("%n", weechat.info_get('irc_nick', server)))

    return weechat.WEECHAT_RC_OK

def auth_del(the_nick, the_server):
    data = weechat.config_get_plugin("data")

    found = False
    conf = []
    for e in data.split(DELIMITER):
        if e.find("=") == -1:
            continue
        (serv_nick, passwd) = e.split("=")
        (server, nick) = serv_nick.split(".")
        if the_nick == nick and the_server == server:
            found = True
        else:
            conf.append("%s.%s=%s" % (server, nick, passwd))

    if found:
        weechat.config_set_plugin("data", DELIMITER.join(conf))
        weechat.prnt("", "[%s] nick '%s@%s' successfully remove" % (NAME, the_nick, the_server))
    else:
        weechat.prnt("", "[%s] an error occured while removing nick '%s@%s' (not found)" % (NAME, the_nick, the_server))

def auth_add(the_nick, the_passwd, the_server):
    data = weechat.config_get_plugin("data")

    found = False
    conf = []
    for e in data.split(DELIMITER):
        if e.find("=") == -1:
            continue
        (serv_nick, passwd) = e.split("=")
        (server, nick) = serv_nick.split(".")
        if the_nick == nick and the_server == server:
            passwd = the_passwd
            found = True
        conf.append("%s.%s=%s" % (server, nick, passwd))

    if not found:
        conf.append("%s.%s=%s" % (the_server, the_nick, the_passwd))

    weechat.config_set_plugin("data", DELIMITER.join(conf))
    weechat.prnt("", "[%s] nick '%s@%s' successfully added" % (NAME, the_nick, the_server))

def auth_get(the_nick, the_server):
    data = weechat.config_get_plugin("data")
    for e in data.split(DELIMITER):
        if e.find("=") == -1:
            continue
        (serv_nick, passwd) = e.split("=")
        (server, nick) = serv_nick.split(".")
        if the_nick == nick and the_server == server:
            return passwd
    return None

def get_channel_from_buffer_args(buffer, args):
    server_name = weechat.buffer_get_string(buffer, "localvar_server")
    channel_name = args
    if not channel_name:
        channel_name = weechat.buffer_get_string(buffer, "localvar_channel")

    match_data = re.match('\A(irc.)?([^.]+)\.(#\S+)\Z', channel_name)
    if match_data:
        channel_name = match_data.group(3)
        server_name = match_data.group(2)

    return server_name, channel_name

def auth_command(data, buffer, args):
    list_args = args.split(" ")
    server, channel = get_channel_from_buffer_args(buffer, args)
    #strip spaces
    while '' in list_args:
        list_args.remove('')
    while ' ' in list_args:
        list_args.remove(' ')

    h_servers = weechat.hdata_get("irc_server")
    l_servers = weechat.hdata_get_list(h_servers, "irc_servers")

    if len(list_args) ==  0:
        weechat.command(buffer, "/help autoauth")
    elif list_args[0] not in ["add", "del", "list", "cmd", "ns"]:
        weechat.prnt(buffer, "[%s] bad option while using /autoauth command, try '/help autoauth' for more info" % (NAME))
    elif list_args[0] == "cmd":
        if len(list_args[1:]) == 1 and weechat.hdata_search(h_servers, l_servers, "${irc_server.name} == "+list_args[1], 1):
            auth_cmd("", list_args[1])
        elif len(list_args[1:]) == 1:
            auth_cmd(list_args[1], server)
        elif len(list_args[1:]) >= 2:
            if weechat.hdata_search(h_servers, l_servers, "${irc_server.name} == "+list_args[-1], 1):
                auth_cmd(" ".join(list_args[1:-1]), list_args[-1])
            else:
                auth_cmd(" ".join(list_args[1:]), server)
        else:
            auth_cmd(" ".join(list_args[1:]), server)
    elif list_args[0] == "ns":
        if len(list_args[1:]) == 1 and weechat.hdata_search(h_servers, l_servers, "${irc_server.name} == "+list_args[1], 1):
            auth_ns("", list_args[1])
        elif len(list_args[1:]) == 1:
            auth_ns(list_args[1], server)
        elif len(list_args[1:]) == 2:
            if weechat.hdata_search(h_servers, l_servers, "${irc_server.name} == "+list_args[-1], 1):
                auth_ns(" ".join(list_args[1:-1]), list_args[-1])
            else:
                auth_ns(" ".join(list_args[1:]), server)
        else:
            auth_ns(" ".join(list_args[1:]), server)
    elif list_args[0] == "list":
        auth_list()
    elif list_args[0] == "add":
        if len(list_args) < 3 or (len(list_args) == 3 and server == ''):
            weechat.prnt(buffer, "[%s] bad option while using /autoauth command, try '/help autoauth' for more info" % (NAME))
        else:
            if len(list_args) == 3:
                auth_add(list_args[1], list_args[2], server)
            else:
                auth_add(list_args[1], list_args[2], list_args[3])
    elif list_args[0] == "del":
       if len(list_args) < 2:
           weechat.prnt(buffer, "[%s] bad option while using /autoauth command, try '/help autoauth' for more info" % (NAME))
       else:
            if len(list_args) == 2:
                auth_del(list_args[1], server)
            else:
                auth_del(list_args[1], list_args[2])
    else:
        pass
    return weechat.WEECHAT_RC_OK

def auth_nslist():
    ns = 'NickServ!services@services'
    nss = weechat.config_get_plugin("nickservs")
    if nss == '':
        weechat.prnt("", "[%s] NickServ : NickServ!services@services" % (NAME))
    else:
        weechat.prnt("", "[%s] NickServ (list)" % (NAME))
        for n in nss.split("####"):
            weechat.prnt("", "  --> %s : '%s' " % (n.split(":::")[0], n.split(":::")[1]))

def auth_nsget(server):
    ns = 'NickServ!services@services'
    nss = weechat.config_get_plugin("nickservs")
    if nss != '':
        for n in nss.split("####"):
            if n.find(":::") != -1:
                if n.split(":::")[0] == server:
                    ns = ":::".join(n.split(":::")[1:])
                    break
    return ns

def auth_nsset(server, nickserv):
    nss = weechat.config_get_plugin("nickservs")

    found = False
    conf = []
    if nss != '':
        for n in nss.split("####"):
            if n.find(":::") != -1:
                if n.split(":::")[0] == server:
                    found = True
                    conf.append("%s:::%s" % (server, nickserv))
                else:
                    conf.append(n)
    if not found:
        conf.append("%s:::%s" % (server, nickserv))

    weechat.config_set_plugin("nickservs", "####".join(conf))
    weechat.prnt("", "[%s] NickServ '%s' successfully added for server %s" % (NAME, nickserv, server))

def auth_nsunset(server):
    nss = weechat.config_get_plugin("nickservs")

    found = False
    conf = []
    if nss != '':
        for n in nss.split("####"):
            if n.find(":::") != -1:
                if n.split(":::")[0] != server:
                    conf.append(n)
                else:
                    found = True
    if found:
        weechat.prnt("", "[%s] NickServ for server '%s' successfully removed" % (NAME, server))
        weechat.config_set_plugin("nickservs", "####".join(conf))

def auth_ns(args, server):
    if server == '':
        if args == '':
            auth_nslist()
        else:
            weechat.prnt("", "[%s] error while setting NickServ, can't find a server" % (NAME))
    else:
        if args == '':
            auth_nsunset(server)
        else:
            auth_nsset(server, args)
