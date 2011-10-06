# -*- coding: utf-8 -*-
# Copyright (C) 2011 godric <godric@0x3f.fr>
# License: WTF
# 
# Changelog
# v1.1
# + re-implemented state change
# + changed pattern and color in nicklist

SCRIPT_NAME    = 'weenetsoul'
SCRIPT_AUTHOR  = 'godric <godric@0x3f.fr>'
SCRIPT_VERSION = '1.1'
SCRIPT_LICENSE = 'WTF'
SCRIPT_DESC    = 'Netsoul protocol for WeeChat'

import weechat
import time, socket, hashlib, urllib, datetime, re

########################################
# Netsoul network functions
########################################

class weeNSUser :
    def __init__(self, login, data = '', location = '', group = '', state = '', state_time = 0, machtype = '', 
                 ip = '', connection_time = 0, lastseen_time = 0, user_trust = 0, client_trust = 0, fd = '') :
        self.login = login
        self.fd = fd
        self.data = data
        self.location = location
        self.group = group
        self.state = state
        self.state_time = int(state_time)
        self.machtype = machtype
        self.ip = ip
        self.connection_time = int(connection_time)
        self.lastseen_time = int(lastseen_time)
        self.user_trust = int(user_trust)
        self.client_trust = int(client_trust)
        self.nick = None

    def prnt(self, buffer = '', prefix = '') :
        hcolor = weechat.color('separator')
        ncolor = weechat.color('chat_nick')
        prefix = prefix+hcolor
        weechat.prnt(buffer, "%s%s=============== %s[%s] (%s) %s===============\n" % (prefix, hcolor, ncolor, self.login, self.fd, hcolor))
        weechat.prnt(buffer, '%s   Host . . . . . . . . : %s\n' % (prefix, self.ip))
        weechat.prnt(buffer, "%s   Machine type . . . . : %s\n" % (prefix, self.machtype))
        weechat.prnt(buffer, "%s   Group. . . . . . . . : %s\n" % (prefix, self.group))
        weechat.prnt(buffer, "%s   State. . . . . . . . : %s\n" % (prefix, self.state))
        weechat.prnt(buffer, "%s   Data . . . . . . . . : %s\n" % (prefix, self.data))
        weechat.prnt(buffer, "%s   Location . . . . . . : %s\n" % (prefix, self.location))
        weechat.prnt(buffer, "%s   Connected at . . . . : %s\n" % (prefix, datetime.datetime.fromtimestamp(self.connection_time).strftime('%d/%m/%Y %H:%M:%S')))
        weechat.prnt(buffer, "%s   Last Activity. . . . : %s\n" % (prefix, datetime.datetime.fromtimestamp(self.lastseen_time).strftime('%d/%m/%Y %H:%M:%S')))
        weechat.prnt(buffer, "%s   Last status change . : %s\n" % (prefix, datetime.datetime.fromtimestamp(self.state_time).strftime('%d/%m/%Y %H:%M:%S')))
        weechat.prnt(buffer, "%s   Trust (User/client). : (%d/%d)\n" % (prefix, self.user_trust, self.client_trust))
        weechat.prnt(buffer, "%s%s==============================================" % (prefix, hcolor))

class weeNSChat :
    def __init__(self, server, login = None, fd = None) :
        self.server = server
        self.login = login
        self.fd = fd
        self.buffer = weechat.buffer_new('Netsoul.temp', 'weeNS_buffer_input_cb', '', 'weeNS_buffer_close_cb', '')
        weechat.buffer_set(self.buffer, "display", "auto")
        self.updateBuffer(login)
        self.server.chats.append(self)

    def updateBuffer(self, login) :
        self.login = login
        fd = self.fd or '*'
        login = self.login or 'unknown'
        weechat.buffer_set(self.buffer, "title", 'Netsoul chat with %s on %s' % (login, fd))
        weechat.buffer_set(self.buffer, 'name', 'Netsoul.%s:%s' % (login, fd))
        weechat.buffer_set(self.buffer, 'short_name', 'Netsoul.%s:%s' % (login, fd))

    def recv(self, login, message) :
        if login != self.login :
            self.updateBuffer(login)
        weechat.prnt(self.buffer, '%s%s\t%s' % (weechat.color("chat_nick"), self.login, message))
            
    def send(self, message) :
        weechat.prnt(self.buffer, '%s%s\t%s' % (weechat.color("chat_nick_self"), self.server.getOption('login'), message))
        recipient = self.login if self.fd is None else ':'+self.fd
        self.server._ns_user_cmd_msg_user(recipient, message)

    def delete(self) :
        if self.buffer is not None :
            return weechat.buffer_close(self.buffer)
        self.server.chats.remove(self)

class weeNSServer :
    def __init__(self) :
        global weeNS_server_opt, weeNS_config_file, weeNS_config_server_section
        self.buffer = None
        self.hook_fd = None
        self.socket = None
        self.netbuffer = ''
        self.chats = []
        self.contacts = {}
        self.options = {
            'host'     : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'host', 'string', 'Server Host (default: ns-server.epita.fr)', '', 0, 0,
                                                   'ns-server.epita.fr', 'ns-server.epita.fr', 0, '', '', '', '', '', ''),
            'port'     : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'port', 'string', 'Server Port (default: 4242)', '', 0, 0,
                                                   '4242', '4242', 0, '', '', '', '', '', ''),
            'login'    : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'login', 'string', 'User login (ie: login_x)', '', 0, 0,
                                                   'login_x', 'login_x', 0, '', '', '', '', '', ''),
            'password' : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'password', 'string', 'User password (ie: your SOCKS password)', '', 0, 0,
                                                   'xxxxxx', 'xxxxxx', 0, '', '', '', '', '', ''),
            'location' : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'location', 'string', 'User location (ie: at home)', '', 0, 0,
                                                   '-', '-', 0, '', '', '', '', '', ''),
            'data'     : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'data', 'string', 'User data (ie: j\'aime les chips)', '', 0, 0,
                                                   '-', '-', 0, '', '', '', '', '', ''),
            'contacts' : weechat.config_new_option(weeNS_config_file, weeNS_config_server_section, 
                                                   'contacts', 'string', 'Comma separated login list (ie: sb,rn)', '', 0, 0,
                                                   '', '', 0, '', '', '', '', '', '')}

    def getOption(self, opt_name) :
        return weechat.config_string(self.options[opt_name])

    def getChatByRecipient(self, login = None, fd = None, create = False) :
        for chat in self.chats :
            if (fd is not None and chat.fd == fd) or (chat.login == login and chat.fd == fd) :
                return chat
        if create is True :
            return weeNSChat(self, login, fd)
        return None

    def getChatByBuffer(self, buffer) :
        for chat in self.chats :
            if chat.buffer == buffer :
                return chat
        return server

    def createBuffer(self) :
        if self.buffer == None :
            self.buffer = weechat.buffer_new('Netsoul', 'weeNS_buffer_input_cb', '', 'weeNS_buffer_close_cb', '')
            weechat.buffer_set(self.buffer, "nicklist", "1")
            weechat.buffer_set(self.buffer, "nicklist_display_groups", "1")
            weechat.buffer_set(self.buffer, "display", "auto")

    def connect(self) :
        self.createBuffer()
        self.disconnect()
        weechat.prnt(self.buffer, 'Connecting to %s:%s' % (self.getOption('host'), self.getOption('port')))
        for res in socket.getaddrinfo(self.getOption('host'), self.getOption('port'), socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE) :
            af, socktype, proto, canonname, sa = res
            try :
                self.socket = socket.socket(af, socktype, proto)
                self.socket.connect(sa)
            except socket.error, msg:
                self.socket = None
                continue
            break
        if self.socket is None :
            weechat.prnt(self.buffer, 'Could not connect')
        self.hook_fd = weechat.hook_fd(self.socket.fileno(), 1, 0, 0, 'weeNS_hook_fd_cb', '')

    def recv(self) :
#        while 1337 :            
        data = self.socket.recv(512)
        if len(data) == 0 :
            return self.disconnect()
        self.netbuffer += data
        while "\n" in self.netbuffer :
            line, ignored, buffer = self.netbuffer.partition("\n")
            index = len(line) + 1
            self.netbuffer = self.netbuffer[index:]
            weechat.prnt(self.buffer, '%s[%s]' % (
              weechat.prefix('join'),
              line))
            self._ns_parse(line)

    def send(self, data) :
        weechat.prnt(self.buffer, '%s[%s]' % (weechat.prefix('quit'), data))
        self.socket.send('%s\n' % data)
    
    def isConnected(self) :
        return (self.socket is not None)

    def disconnect(self) :
        if self.hook_fd is not None :
            weechat.unhook(self.hook_fd)
        if self.socket is not None :
            self.socket.close()
        if self.buffer is not None :
            self.contacts = {}
            weechat.nicklist_remove_all(self.buffer)
            weechat.prnt(self.buffer, '... Disconnected ...')
        self.hook_fd = None
        self.socket = None
        self.contacts = {}

    def delete(self) :
        for chat in reversed(self.chats) :
            chat.delete()
        self.disconnect()
        if self.buffer is not None :
            weechat.buffer_close(self.buffer)
            self.buffer = None
        for option in self.options.keys():
            weechat.config_option_free(option)

    def setupNicklist(self) :
        contact_list = self.getOption('contacts').replace(' ', '').split(',')
        for login in contact_list :
            weechat.nicklist_add_group(self.buffer, '', login, 'lightcyan', 1)
            self.contacts[login] = {}
        self._ns_user_cmd_who('{%s}' % ','.join(contact_list))
        self._ns_user_cmd_watch_log_user(','.join(contact_list))

    def updateNicklist(self, user, remove = False) :
        group = weechat.nicklist_search_group(self.buffer, '', user.login)
        if group is not None and user.login in self.contacts :
            if user.fd in self.contacts[user.login] :
                weechat.nicklist_remove_nick(self.buffer, self.contacts[user.login][user.fd].nick)
                del self.contacts[user.login][user.fd]
            if remove is False :
                user.nick = weechat.nicklist_add_nick(self.buffer, group, ' :%s%s@%s%s' % (user.fd, weechat.color('separator'), weechat.color('default'), user.location), '', '', '', 1)
                self.contacts[user.login][user.fd] = user


    def _ns_auth_ag(self) :
        self.send("auth_ag ext_user none none")

    def _ns_ext_user_log(self, secret, ip, port) :
        location = urllib.quote(self.getOption('location'))
        data = urllib.quote(self.getOption('data'))
        crypt = hashlib.md5('%s-%s/%s%s' % (secret, ip, port, self.getOption('password'))).hexdigest()
        self.send("ext_user_log %s %s %s %s" % (self.getOption('login'), crypt, location, data))
        
    def _ns_user_cmd_msg_user(self, login, msg) :
        msg = unicode(msg, 'utf-8').encode('iso-8859-1')
        self.send("user_cmd msg_user %s msg %s" % (login, urllib.quote(msg)))

    def _ns_user_cmd_who(self, login) :
        self.send("user_cmd who %s" % login)

    def _ns_user_cmd_watch_log_user(self, friends) :
        self.send("user_cmd watch_log_user {%s}" % friends)

    def _ns_state(self, state) :
        self.send("state %s:%s" % (state, int(time.time())))

    def _ns_parse(self, data) :
        arglist = data.split(' ')
        if arglist[0] == 'salut' :
            self._ns_parse_salut(arglist)
        elif arglist[0] == 'ping' :
            self._ns_parse_ping(arglist)
        elif arglist[0] == 'user_cmd' :
            if arglist[3] == 'msg' :
                self._ns_parse_user_cmd_msg(arglist)
            elif arglist[3] == 'who':
                self._ns_parse_user_cmd_who(arglist)
            elif arglist[3] == 'login' : 
                self._ns_parse_user_cmd_login(arglist)
            elif arglist[3] == 'logout' :
                self._ns_parse_user_cmd_logout(arglist)
            elif arglist[3] == 'state' :
                self._ns_parse_user_cmd_state(arglist)

    def _ns_parse_from(self, str) :
        r = re.compile('([0-9]+):user:([0-9]+)/([0-9]+):([_a-z]+)@([0-9.]+):([^ :]+):([^ :]+):([^ :]+)');
        match = re.match(r, str)
        groups = match.groups()
        user = weeNSUser(fd = groups[0], client_trust = groups[1], user_trust = groups[2], login = groups[3], 
                         ip = groups[4], machtype = groups[5], location = groups[6], group = groups[7])
        return user
    
    def _ns_parse_salut(self, arglist) :
        self._ns_auth_ag()
        self._ns_ext_user_log(arglist[2], arglist[3], arglist[4])
        self.setupNicklist()

    def _ns_parse_ping(self, arglist) :
        self.send("ping %s" % arglist[1])

    def _ns_parse_user_cmd_msg(self, arglist) :
        user = self._ns_parse_from(arglist[1])
        msg = urllib.unquote(arglist[4])
        msg = unicode(msg, 'iso-8859-1').encode('utf-8')
        pchat = self.getChatByRecipient(fd = user.fd)
        if pchat is not None :
            pchat.recv(user.login, msg)
        gchat = self.getChatByRecipient(user.login, create = (pchat is None))
        if gchat is not None :
            gchat.recv(user.login, msg)

    def _ns_parse_user_cmd_who(self, arglist) :
        r = re.compile('who ([0-9]+) ([_a-z]+) ([0-9.]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([^ ]+) ([^ ]+) ([^ ]+) ([^ :]+):{0,1}([0-9]+){0,1} ([^ ]+)')
        match = re.match(r, ' '.join(arglist[3:]))
        if match is not None :
            groups = match.groups()
            user = weeNSUser(fd = groups[0], login = groups[1], ip = groups[2], connection_time = groups[3], lastseen_time = groups[4], user_trust = groups[5], client_trust = groups[6], machtype = groups[7], location = urllib.unquote(groups[8]), group = groups[9], state = urllib.unquote(groups[10]), state_time = groups[11] or 0, data = urllib.unquote(groups[12]))
            self.updateNicklist(user)
            user.prnt(self.buffer, weechat.prefix('network'))

    def _ns_parse_user_cmd_state(self, arglist) :
        user = self._ns_parse_from(arglist[1])
        if user.login in self.contacts and user.fd in self.contacts[user.login] :
            user = self.contacts[user.login][user.fd]
            state = arglist[4].split(':')
            user.state = urllib.unquote(state[0])
            user.state_time = int(time.time())
            self.updateNicklist(user)
            chat = self.getChatByRecipient(fd = user.fd)
            if chat is not None :
                weechat.prnt(chat.buffer, '%s%s%s changed state : %s' % (weechat.prefix('network'), weechat.color('nick_color'), user.login, user.state))

    def _ns_parse_user_cmd_login(self, arglist) :
        user = self._ns_parse_from(arglist[1])        
        self._ns_user_cmd_who(':%s' % user.fd)
        chat = self.getChatByRecipient(fd = user.fd)
        if chat is not None :
            weechat.prnt(chat.buffer, '%s%s%s has connected' % (weechat.prefix('join'), weechat.color('nick_color'), user.login))

    def _ns_parse_user_cmd_logout(self, arglist) :
        user = self._ns_parse_from(arglist[1])
        self.updateNicklist(user, remove = True)
        chat = self.getChatByRecipient(fd = user.fd)
        if chat is not None :
            weechat.prnt(chat.buffer, '%s%s%s has disconnected' % (weechat.prefix('quit'), weechat.color('nick_color'), user.login))

########################################
# Weechat callbacks
########################################

def weeNS_buffer_input_cb(data, buffer, input_data) :
    global server
    if server.isConnected() :
        server.getChatByBuffer(buffer).send(input_data)
    return weechat.WEECHAT_RC_OK
    
def weeNS_buffer_close_cb(data, buffer) :
    global server
    context = server.getChatByBuffer(buffer)
    context.buffer = None
    context.delete()
    return weechat.WEECHAT_RC_OK

def weeNS_server_section_read_cb(data, config_file, section, option_name, value) :
    global server
    return weechat.config_option_set(server.options[option_name], value, 0)

def weeNS_hook_fd_cb(data, fd) :
    global server
    server.recv()
    return weechat.WEECHAT_RC_OK

def weeNS_script_unload_cb() :
    global weeNS_config_file
    weechat.config_write(weeNS_config_file)
    return weechat.WEECHAT_RC_OK

def weeNS_hook_cmd_ns(data, buffer, args) :
    global server

    buffer = server.buffer if server.buffer is not None else ''
    arglist = args.split(' ')
    if arglist[0] == 'connect' and not server.isConnected():
        server.connect()
    elif arglist[0] == 'disconnect' and server.isConnected() :
        server.disconnect()
    elif arglist[0] == 'send' and server.isConnected() and len(arglist) > 2 :
        match = re.match(re.compile('\A([a-z_]+)|:([0-9]+)\Z'), arglist[1])
        if match is not None :
            groups = match.groups()
            msg = ' '.join(arglist[2:])
            server.getChatByRecipient(groups[0], groups[1], create = True).send(msg)
        else :
            weechat.prnt(buffer, 'Message recipient must be of type login_x[:fd]')
    elif arglist[0] == 'who' and server.isConnected() and len(arglist) > 1 :
        server._ns_user_cmd_who(arglist[1])
    elif arglist[0] == 'state' and server.isConnected() and len(arglist) > 1 :
        server._ns_state(arglist[1])
    else :
        weechat.prnt(buffer, '%sNo such command, wrong argument count, or you need to (dis)connect' % weechat.prefix('error'))
    return weechat.WEECHAT_RC_OK

######################################
# Main
######################################

if __name__ == "__main__" :
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', 'weeNS_script_unload_cb'):
        weechat.hook_command('ns', 'weeNetsoul main command', 'connect | disconnect | send <login> <msg> | state <status> | who <login>',
                             "    connect : Connect\n"
                             " disconnect : Diconnect\n"
                             "       send : Send <msg> to <login> (any client) or to <:fd> (unique client)\n"
                             "      state : Change status to <status> (en ligne/actif/whatever)\n"
                             "        who : Show infos about <login>\n",
                             'connect|disconnect|send|state|who', 'weeNS_hook_cmd_ns', '')
        weeNS_config_file = weechat.config_new(SCRIPT_NAME, '', '')
        weeNS_config_server_section = weechat.config_new_section(weeNS_config_file, 'server', 0, 0, 'weeNS_server_section_read_cb', '', '', '',  '', '', '', '', '', '')
        server = weeNSServer()
        weechat.config_read(weeNS_config_file)
        weechat.config_write(weeNS_config_file)
