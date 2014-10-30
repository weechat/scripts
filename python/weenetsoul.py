# -*- coding: utf-8 -*-
# Copyright (C) 2011 godric <godric@0x3f.fr>
# License: WTFPL
#
# Changelog
# v1.3
# + fix login regex
# + completion with online contacts from contact list for send and who commands
# + prevent default completion for all other commands
# v1.2
# + PEP8 almost-compliance
# + code adjustment
# + fix bug with state_time (ValueError)
# + state in config to change it at connexion
# + added a add_contact command, to add contacts at run time
# + added a reconnect command
# + try to reconnect on server disconnection
# + reconnect_time  in config, for attempts between reconnections
# + display_name in config, for buffers base name
# v1.1
# + re-implemented state change
# + changed pattern and color in nicklist
"""A simple plugin for netsoul protocol"""

SCRIPT_NAME = 'weenetsoul'
SCRIPT_AUTHOR = 'godric <godric@0x3f.fr>'
SCRIPT_VERSION = '1.3'
SCRIPT_LICENSE = 'WTFPL'
SCRIPT_DESC = 'Netsoul protocol for WeeChat'

import weechat
import time, socket, hashlib, urllib, re
from datetime import datetime as dt
from collections import OrderedDict

########################################
# Netsoul network functions
########################################

class WeeNSUser(object):

    def __init__(self, login, data='', location='', group='', state='',
                 state_time=0, machtype='', ip='', connection_time=0,
                 lastseen_time=0, user_trust=0, client_trust=0, fd=''):
        self.login = login
        self.fd = fd
        self.data = data
        self.location = location
        self.group = group
        self.state = state
        try:
            self.state_time = (dt.fromtimestamp(int(state_time))
                               .strftime('%d/%m/%Y %H:%M:%S'))
        except:
            self.state_time = (dt.fromtimestamp(0)
                               .strftime('%d/%m/%Y %H:%M:%S'))
        self.machtype = machtype
        self.ip = ip
        try:
            self.connection_time = (dt.fromtimestamp(int(connection_time))
                                    .strftime('%d/%m/%Y %H:%M:%S'))
        except:
            self.connection_time = (dt.fromtimestamp(0)
                                    .strftime('%d/%m/%Y %H:%M:%S'))
        try:
            self.lastseen_time = (dt.fromtimestamp(int(lastseen_time))
                                  .strftime('%d/%m/%Y %H:%M:%S'))
        except:
            self.lastseen_time = (dt.fromtimestamp(0)
                                  .strftime('%d/%m/%Y %H:%M:%S'))
        self.user_trust = int(user_trust)
        self.client_trust = int(client_trust)
        self.nick = None

    def prnt(self, buffer='', prefix=''):
        hcolor = weechat.color('separator')
        ncolor = weechat.color('chat_nick')
        prefix = prefix + hcolor
        weechat.prnt(buffer,
                     ("{0}{1}{2} {3}[{4}] ({5}) {6}{2}\n"
                      .format(prefix, hcolor, '=' * 15, ncolor,
                              self.login, self.fd, hcolor)))
        weechat.prnt(buffer,
                     '%s   Host . . . . . . . . : %s\n'
                     % (prefix, self.ip))
        weechat.prnt(buffer,
                     "%s   Machine type . . . . : %s\n"
                     % (prefix, self.machtype))
        weechat.prnt(buffer,
                     "%s   Group. . . . . . . . : %s\n"
                     % (prefix, self.group))
        weechat.prnt(buffer,
                     "%s   State. . . . . . . . : %s\n"
                     % (prefix, self.state))
        weechat.prnt(buffer,
                     "%s   Data . . . . . . . . : %s\n"
                     % (prefix, self.data))
        weechat.prnt(buffer,
                     "%s   Location . . . . . . : %s\n"
                     % (prefix, self.location))
        weechat.prnt(buffer,
                     "%s   Connected at . . . . : %s\n"
                     % (prefix, self.connection_time))
        weechat.prnt(buffer,
                     "%s   Last Activity. . . . : %s\n"
                     % (prefix, self.lastseen_time))
        weechat.prnt(buffer,
                     "%s   Last status change . : %s\n"
                     % (prefix, self.state_time))
        weechat.prnt(buffer,
                     "%s   Trust (User/client). : (%d/%d)\n"
                     % (prefix, self.user_trust, self.client_trust))
        weechat.prnt(buffer,
                     "%s%s%s"
                     % (prefix, hcolor, '=' * 46))


class WeeNSChat(object):

    def __init__(self, server, login=None, fd=None):
        self.server = server
        self.login = login
        self.fd = fd
        self.buffer = weechat.buffer_new('%s.temp' % (self.server.name,),
                                         'wee_ns_buffer_input_cb', '',
                                         'wee_ns_buffer_close_cb', '')
        weechat.buffer_set(self.buffer, "display", "auto")
        self.update_buffer(login)
        self.server.chats.append(self)

    def update_buffer(self, login):
        self.login = login
        fd = self.fd or '*'
        login = self.login or 'unknown'
        weechat.buffer_set(self.buffer, 'title',
                           'Netsoul chat with %s on %s' % (login, fd))
        weechat.buffer_set(self.buffer, 'name',
                           '%s.%s:%s' % (self.server.name, login, fd))
        weechat.buffer_set(self.buffer, 'short_name',
                           '%s:%s' % (login, fd))
        weechat.buffer_set(self.buffer, 'nick',
                           '%s' % (self.server.get_option('login'),))
        weechat.buffer_set(self.buffer, 'channel',
                           '%s:%s' % (login, fd))
        weechat.buffer_set(self.buffer, 'server',
                           '%s' % (self.server.get_option('host'),))
        weechat.buffer_set(self.buffer, 'type',
                           'private')

    def recv(self, login, message):
        if login != self.login:
            self.update_buffer(login)
        weechat.prnt(self.buffer,
                     '%s%s\t%s'
                     % (weechat.color("chat_nick"), self.login, message))

    def send(self, message):
        weechat.prnt(self.buffer,
                     '%s%s\t%s'
                     % (weechat.color("chat_nick_self"),
                        self.server.get_option('login'), message))
        recipient = self.login if self.fd is None else (':' + self.fd)
        self.server._ns_user_cmd_msg_user(recipient, message)

    def delete(self):
        if self.buffer is not None:
            return weechat.buffer_close(self.buffer)
        self.server.chats.remove(self)


class WeeNSServer(object):

    def __init__(self):
        self.buffer = None
        self.hook_fd = None
        self.socket = None
        self.netbuffer = ''
        self.chats = []
        self.contacts = {}
        lastfields = (0, '', '', '', '', '', '')
        self.options = {
            'host': weechat.config_new_option(wee_ns_config_file,
                                              wee_ns_conf_serv_sect,
                                              'host', 'string',
                                              'Server host', '', 0, 0,
                                              'ns-server.epita.fr',
                                              'ns-server.epita.fr',
                                              *lastfields),
            'port': weechat.config_new_option(wee_ns_config_file,
                                              wee_ns_conf_serv_sect,
                                              'port', 'string',
                                              'Server port', '', 0, 0,
                                              '4242', '4242',
                                              *lastfields),
            'login': weechat.config_new_option(wee_ns_config_file,
                                               wee_ns_conf_serv_sect,
                                               'login', 'string',
                                               'User login (ie: login_x)',
                                               '', 0, 0, 'login_x', 'login_x',
                                               *lastfields),
            'password': weechat.config_new_option(wee_ns_config_file,
                                                  wee_ns_conf_serv_sect,
                                                  'password', 'string',
                                                  ('User password (ie: '
                                                   'your SOCKS password)'),
                                                  '', 0, 0, 'xxxxxx', 'xxxxxx',
                                                  *lastfields),
            'location': weechat.config_new_option(wee_ns_config_file,
                                                  wee_ns_conf_serv_sect,
                                                  'location', 'string',
                                                  ('User location (ie: '
                                                   'at home)'),
                                                  '', 0, 0, '-', '-',
                                                  *lastfields),
            'data': weechat.config_new_option(wee_ns_config_file,
                                              wee_ns_conf_serv_sect,
                                              'data', 'string',
                                              ('User data (ie: '
                                               'j\'aime les chips)'),
                                              '', 0, 0, '-', '-',
                                              *lastfields),
            'state': weechat.config_new_option(wee_ns_config_file,
                                               wee_ns_conf_serv_sect,
                                               'state', 'string',
                                               'User state (ie: actif)',
                                               '', 0, 0, 'actif', 'actif',
                                               *lastfields),
            'contacts': weechat.config_new_option(wee_ns_config_file,
                                                  wee_ns_conf_serv_sect,
                                                  'contacts', 'string',
                                                  ('Comma separated login '
                                                   'list (ie: sb,rn)'),
                                                  '', 0, 0, '', '',
                                                  *lastfields),
            'display_name': weechat.config_new_option(wee_ns_config_file,
                                                      wee_ns_conf_serv_sect,
                                                      'display_name', 'string',
                                                      ('Server display name '
                                                       'in buffer list '
                                                       '("" = host value)'),
                                                      '', 0, 0,
                                                      'Netsoul', 'Netsoul',
                                                      *lastfields),
            'reconnect_time': weechat.config_new_option(wee_ns_config_file,
                                                        wee_ns_conf_serv_sect,
                                                        'reconnect_time',
                                                        'string',
                                                        ('Time in seconds '
                                                         'between two '
                                                         'reconnection '
                                                         'attempts '
                                                         '(0 = no '
                                                         'reconnection)'),
                                                        '', 0, 0, '30', '30',
                                                        *lastfields),
        }
        self.commands_hooks = {
            'salut': self._ns_parse_salut,
            'ping': self._ns_parse_ping,
            'user_cmd': self._ns_parse_user_cmd,
        }
        self.user_cmd_hooks = {
            'msg': self._ns_parse_user_cmd_msg,
            'who': self._ns_parse_user_cmd_who,
            'login': self._ns_parse_user_cmd_login,
            'logout': self._ns_parse_user_cmd_logout,
            'state': self._ns_parse_user_cmd_state,
        }

    @property
    def name(self):
        return {
            True: self.get_option('display_name'),
            False: self.get_option('host'),
        }[self.get_option('display_name') != ""]

    def get_option(self, opt_name):
        return weechat.config_string(self.options[opt_name])

    def get_default(self, opt_name):
        return weechat.config_default_string(self.options[opt_name])

    def get_chat_by_recipient(self, login=None, fd=None, create=False):
        for chat in self.chats:
            if ((fd is not None and chat.fd == fd) or
                (chat.login == login and chat.fd == fd)):
                return chat
        if create is True:
            return WeeNSChat(self, login, fd)
        return None

    def get_chat_by_buffer(self, buffer):
        for chat in self.chats:
            if chat.buffer == buffer:
                return chat
        return server

    def create_buffer(self):
        if self.buffer == None:
            self.buffer = weechat.buffer_new('server.%s' % (self.name,),
                                             'wee_ns_buffer_input_cb', '',
                                             'wee_ns_buffer_close_cb', '')
            weechat.buffer_set(self.buffer, "nicklist",
                               "1")
            weechat.buffer_set(self.buffer, "nicklist_display_groups",
                               "1")
            weechat.buffer_set(self.buffer, "display",
                               "auto")
            weechat.buffer_set(self.buffer, "nick",
                               "%s" % (self.get_option('login'),))
            weechat.buffer_set(self.buffer, "server",
                               "%s" % (self.get_option('host'),))
            weechat.buffer_set(self.buffer, "channel",
                               "%s" % (self.name,))
            weechat.buffer_set(self.buffer, "type",
                               "server")

    def connect(self):
        self.create_buffer()
        self.disconnect()
        weechat.prnt(self.buffer,
                     'Connecting to %s:%s'
                     % (self.get_option('host'), self.get_option('port')))
        try:
            hints = socket.getaddrinfo(self.get_option('host'),
                                       self.get_option('port'),
                                       socket.AF_UNSPEC, socket.SOCK_STREAM,
                                       0, socket.AI_PASSIVE)
        except socket.error as e:
            weechat.prnt(self.buffer,
                         '%s%s' % (weechat.prefix('error'), e.args[1]))
        else:
            for res in hints:
                af, socktype, proto, canonname, sa = res
                try:
                    self.socket = socket.socket(af, socktype, proto)
                    self.socket.connect(sa)
                except socket.error:
                    self.socket = None
                    continue
                break
        if self.socket is None:
            weechat.prnt(self.buffer,
                         '%sCould not connect' % (weechat.prefix('error'),))
        else:
            self.hook_fd = weechat.hook_fd(self.socket.fileno(), 1, 0, 0,
                                           'wee_ns_hook_fd_cb', '')

    def recv(self):
        data = self.socket.recv(512)
        if len(data) == 0:
            return self.reconnect()
        self.netbuffer += data
        while "\n" in self.netbuffer:
            line, ignored, buffer = self.netbuffer.partition("\n")
            index = len(line) + 1
            self.netbuffer = self.netbuffer[index:]
            weechat.prnt(self.buffer,
                         '%s[%s]' % (weechat.prefix('join'), line))
            self._ns_parse(line)

    def send(self, data):
        weechat.prnt(self.buffer,
                     '%s[%s]' % (weechat.prefix('quit'), data))
        self.socket.send('%s\n' % data)

    @property
    def is_connected(self):
        return self.socket is not None

    def disconnect(self):
        if self.hook_fd is not None:
            weechat.unhook(self.hook_fd)
        if self.socket is not None:
            self.socket.close()
        if self.buffer is not None:
            self.contacts = {}
            weechat.nicklist_remove_all(self.buffer)
            weechat.prnt(self.buffer, '... Disconnected ...')
        self.hook_fd = None
        self.socket = None
        self.contacts = {}

    def reconnect(self):
        if self.is_connected:
            self.disconnect()
        wee_ns_reconnect_loop()

    def delete(self):
        for chat in reversed(self.chats):
            chat.delete()
        self.disconnect()
        if self.buffer is not None:
            weechat.buffer_close(self.buffer)
            self.buffer = None
        for option in self.options:
            weechat.config_option_free(option)

    def setup_nick_list(self):
        contact_list = {
            True: [],
            False: self.get_option('contacts').replace(' ', '').split(',')
        }[self.get_option('contacts').replace(' ', '') == '']
        for login in contact_list:
            weechat.nicklist_add_group(self.buffer, '', login, 'lightcyan', 1)
            self.contacts[login] = {}
        self._ns_user_cmd_who('{%s}' % ','.join(contact_list))
        self._ns_user_cmd_watch_log_user(','.join(contact_list))

    def add_to_nick_list(self, *logins):
        contact_list = {
            True: [],
            False: self.get_option('contacts').replace(' ', '').split(',')
        }[self.get_option('contacts').replace(' ', '') == '']
        new_contacts = []
        for login in logins:
            if login in self.contacts:
                continue
            contact_list.append(login)
            new_contacts.append(login)
            self.contacts[login] = {}
            weechat.nicklist_add_group(self.buffer, '', login, 'lightcyan', 1)
        self._ns_user_cmd_who('{%s}' % ','.join(new_contacts))
        self._ns_user_cmd_watch_log_user(','.join(contact_list))
        weechat.config_option_set(self.options['contacts'],
                                  ','.join(contact_list), 0)

    def update_nick_list(self, user, remove=False):
        group = weechat.nicklist_search_group(self.buffer, '', user.login)
        if group is not None and user.login in self.contacts:
            if user.fd in self.contacts[user.login]:
                weechat.nicklist_remove_nick(self.buffer,
                                             (self.contacts[user.login]
                                              [user.fd].nick))
                del self.contacts[user.login][user.fd]
            if remove is False:
                user.nick = weechat.nicklist_add_nick(self.buffer, group,
                                                      ' :%s%s@%s%s'
                                                      % (user.fd,
                                                         (weechat
                                                          .color('separator')),
                                                         (weechat
                                                          .color('default')),
                                                         user.location),
                                                      '', '', '', 1)
                self.contacts[user.login][user.fd] = user

    def _ns_auth_ag(self):
        self.send("auth_ag ext_user none none")

    def _ns_ext_user_log(self, secret, ip, port):
        location = urllib.quote(self.get_option('location'))
        data = urllib.quote(self.get_option('data'))
        crypt = hashlib.md5('%s-%s/%s%s'
                            % (secret, ip, port,
                               self.get_option('password'))).hexdigest()
        self.send("ext_user_log %s %s %s %s" % (self.get_option('login'),
                                                crypt, location, data))

    def _ns_user_cmd_msg_user(self, login, msg):
        msg = unicode(msg, 'utf-8').encode('iso-8859-1')
        self.send("user_cmd msg_user %s msg %s" % (login, urllib.quote(msg)))

    def _ns_user_cmd_who(self, login):
        self.send("user_cmd who %s" % login)

    def _ns_user_cmd_watch_log_user(self, friends):
        self.send("user_cmd watch_log_user {%s}" % friends)

    def _ns_state(self, state):
        self.send("state %s:%s" % (state, int(time.time())))

    def _ns_parse(self, data):
        arglist = data.split(' ')
        if arglist[0] in self.commands_hooks:
            self.commands_hooks[arglist[0]](arglist)

    def _ns_parse_from(self, str):
        r = re.compile(r"""
        ([0-9]+):                # fd
        user:
        ([0-9]+)/([0-9]+):       # user_trust
        ([_a-z0-9-]+)@([0-9.]+): # login@ip
        ([^ :]+):                # machtype
        ([^ :]+):                # location
        ([^ :]+)                 # group
        """, re.VERBOSE)
        match = re.match(r, str)
        groups = match.groups()
        user = WeeNSUser(fd=groups[0], client_trust=groups[1],
                         user_trust=groups[2], login=groups[3],
                         ip=groups[4], machtype=groups[5],
                         location=groups[6], group=groups[7])
        return user

    def _ns_parse_salut(self, arglist):
        self._ns_auth_ag()
        self._ns_ext_user_log(arglist[2], arglist[3], arglist[4])
        self._ns_state(self.get_option('state'))
        self.setup_nick_list()

    def _ns_parse_ping(self, arglist):
        self.send("ping %s" % arglist[1])

    def _ns_parse_user_cmd(self, arglist):
        if arglist[3] in self.user_cmd_hooks:
            self.user_cmd_hooks[arglist[3]](arglist)

    def _ns_parse_user_cmd_msg(self, arglist):
        user = self._ns_parse_from(arglist[1])
        msg = urllib.unquote(arglist[4])
        msg = unicode(msg, 'iso-8859-1').encode('utf-8')
        pchat = self.get_chat_by_recipient(fd=user.fd)
        if pchat is not None:
            pchat.recv(user.login, msg)
        gchat = self.get_chat_by_recipient(user.login, create=(pchat is None))
        if gchat is not None:
            gchat.recv(user.login, msg)

    def _ns_parse_user_cmd_who(self, arglist):
        r = re.compile(r"""
        who[ ]
        ([0-9]+)[ ]             # fd
        ([_a-z0-9-]+)[ ]        # login
        ([0-9.]+)[ ]            # ip
        ([0-9]+)[ ]             # connection_time
        ([0-9]+)[ ]             # lastseen_time
        ([0-9]+)[ ]             # user_trust
        ([0-9]+)[ ]             # client_trust
        ([^ ]+)[ ]              # machtype
        ([^ ]+)[ ]              # location
        ([^ ]+)[ ]              # group
        ([^ :]+)(:([^ ]+)?)?[ ] # state:state_time
        ([^ ]+)                 # data
        """, re.VERBOSE)
        match = re.match(r, ' '.join(arglist[3:]))
        if match is not None:
            groups = match.groups()
            user = WeeNSUser(fd=groups[0], login=groups[1], ip=groups[2],
                             connection_time=groups[3],
                             lastseen_time=groups[4],
                             user_trust=groups[5], client_trust=groups[6],
                             machtype=groups[7],
                             location=urllib.unquote(groups[8]),
                             group=groups[9],
                             state=urllib.unquote(groups[10]),
                             state_time=groups[12] or 0,
                             data=urllib.unquote(groups[13]))
            self.update_nick_list(user)
            user.prnt(self.buffer, weechat.prefix('network'))

    def _ns_parse_user_cmd_state(self, arglist):
        user = self._ns_parse_from(arglist[1])
        if (user.login in self.contacts and
            user.fd in self.contacts[user.login]):
            user = self.contacts[user.login][user.fd]
            state = arglist[4].split(':')
            user.state = urllib.unquote(state[0])
            user.state_time = (dt.fromtimestamp(int(time.time()))
                               .strftime('%d/%m/%Y %H:%M:%S'))
            self.update_nick_list(user)
            msg = '%s%s%s changed state to %s' % (weechat.prefix('network'),
                                                  weechat.color('nick_color'),
                                                  user.login, user.state)
            pchat = self.get_chat_by_recipient(fd=user.fd)
            if pchat is not None:
                weechat.prnt(pchat.buffer, msg)
            gchat = self.get_chat_by_recipient(user.login)
            if gchat is not None:
                weechat.prnt(gchat.buffer, msg)

    def _ns_parse_user_cmd_login(self, arglist):
        user = self._ns_parse_from(arglist[1])
        self._ns_user_cmd_who(':%s' % user.fd)
        msg = '%s%s%s has connected' % (weechat.prefix('join'),
                                        weechat.color('nick_color'),
                                        user.login)
        pchat = self.get_chat_by_recipient(fd=user.fd)
        if pchat is not None:
            weechat.prnt(pchat.buffer, msg)
        gchat = self.get_chat_by_recipient(user.login)
        if gchat is not None:
            weechat.prnt(gchat.buffer, msg)

    def _ns_parse_user_cmd_logout(self, arglist):
        user = self._ns_parse_from(arglist[1])
        self.update_nick_list(user, remove=True)
        msg = '%s%s%s has disconnected' % (weechat.prefix('quit'),
                                           weechat.color('nick_color'),
                                           user.login)
        pchat = self.get_chat_by_recipient(fd=user.fd)
        if pchat is not None:
            weechat.prnt(pchat.buffer, msg)
        gchat = self.get_chat_by_recipient(user.login)
        if gchat is not None:
            weechat.prnt(gchat.buffer, msg)


########################################
# Weechat callbacks
########################################

def wee_ns_reconnect_loop(*args):
    weechat.prnt(server.buffer, 'Trying to reconnect...')
    server.connect()
    try:
        reconnect_time = int(server.get_option('reconnect_time'))
    except ValueError:
        reconnect_time = int(server.get_default('reconnect_time'))
    if not server.is_connected and reconnect_time > 0:
        weechat.prnt(server.buffer,
                     'Failed, next attempt in %s seconds'
                     % (server.get_option('reconnect_time'),))
        weechat.hook_timer(reconnect_time * 1000, 0, 1,
                           'wee_ns_reconnect_loop', '')
    return weechat.WEECHAT_RC_OK

def wee_ns_buffer_input_cb(data, buffer, input_data):
    if server.is_connected:
        server.get_chat_by_buffer(buffer).send(input_data)
    return weechat.WEECHAT_RC_OK

def wee_ns_buffer_close_cb(data, buffer):
    context = server.get_chat_by_buffer(buffer)
    context.buffer = None
    context.delete()
    return weechat.WEECHAT_RC_OK

def wee_ns_serv_sect_read_cb(data, config_file, section, option_name, value):
    return weechat.config_option_set(server.options[option_name], value, 0)

def wee_ns_hook_fd_cb(data, fd):
    server.recv()
    return weechat.WEECHAT_RC_OK

def wee_ns_script_unload_cb():
    weechat.config_write(wee_ns_config_file)
    return weechat.WEECHAT_RC_OK

def wee_ns_hook_cmd_connect(server, *args):
    """Connect you to netsoul"""
    if not server.is_connected:
        server.connect()
    else:
        return "Already connected"

def wee_ns_hook_cmd_disconnect(server, *args):
    """Disconnect you from netsoul"""
    if server.is_connected:
        server.disconnect()
    else:
        return "Not connected"

def wee_ns_hook_cmd_reconnect(server, *args):
    """Reconnect you to netsoul"""
    server.reconnect()

def wee_ns_hook_cmd_send(server, *args):
    """Send <msg> to <login> (any client) or <:fd> (unique client)"""
    if len(args) < 2:
        return -1
    if not server.is_connected:
        return "Not connected"
    match = re.match(re.compile(r'''
    \A
    ([_a-z0-9-]+) # login
    |:([0-9]+)    # or :fd
    \Z
    ''', re.VERBOSE), args[0])
    if not match:
        return "Message recipients must be of type <login> or <:fd>"
    server.get_chat_by_recipient(*match.groups(),
                                 create=True).send(' '.join(args[1:]))

def wee_ns_hook_cmd_state(server, *args):
    """Change status to <status> (en ligne/actif/whatever)"""
    if len(args) < 1:
        return -1
    if not server.is_connected:
        return "Not connected"
    server._ns_state(args[0])

def wee_ns_hook_cmd_who(server, *args):
    """Show infos about all <login>... specified"""
    if len(args) < 1:
        return -1
    if not server.is_connected:
        return "Not connected"
    server._ns_user_cmd_who('{%s}' % ','.join(args))

def wee_ns_hook_cmd_add_contact(server, *args):
    """Add all <login>... specified to your contacts"""
    if len(args) < 1:
        return -1
    if not server.is_connected:
        return "Not connected"
    server.add_to_nick_list(*args)

def wee_ns_hook_completion_send(data, completion_item,
                                buffer, completion):
    if server.is_connected:
        [weechat.hook_completion_list_add(completion, contact, 0,
                                          weechat.WEECHAT_LIST_POS_SORT)
         for contact, fds in server.contacts.items() if fds]
    return weechat.WEECHAT_RC_OK

def wee_ns_hook_cmd_ns(data, buffer, args):
    buffer = server.buffer if server.buffer is not None else ''
    arglist = args.split(' ')
    if arglist[0] in hook_cmd_ns:
        target = hook_cmd_ns[arglist[0]]
        res = target['cb'](server, *arglist[1:])
        if res is not None:
            if res == -1:
                res = 'usage: %s%s' % (arglist[0],
                                       '' if 'desc' not in target
                                       else " " + target['desc'])
            weechat.prnt(buffer, '%s%s' % (weechat.prefix('error'), res))
    else:
        weechat.prnt(buffer,
                     ('%sNo such command, '
                      'wrong argument count, '
                      'or you need to (dis)connect') % weechat.prefix('error'))
    return weechat.WEECHAT_RC_OK

# Add your commands here
hook_cmd_ns = OrderedDict([
    ('connect', {'cb': wee_ns_hook_cmd_connect,
                 'compl': '%-'}),
    ('disconnect', {'cb': wee_ns_hook_cmd_disconnect,
                    'compl': '%-'}),
    ('reconnect', {'cb': wee_ns_hook_cmd_reconnect,
                   'compl': '%-'}),
    ('send', {'cb': wee_ns_hook_cmd_send,
              'desc': "<login> <msg>",
              'compl': '%(ns_send) %-'}),
    ('state', {'cb': wee_ns_hook_cmd_state,
               'desc': "<status>",
               'compl': '%-'}),
    ('who', {'cb': wee_ns_hook_cmd_who,
             'desc': "<login>...",
             'compl': '%(ns_send) %-'}),
    ('add_contact', {'cb': wee_ns_hook_cmd_add_contact,
                     'desc': "<login>...",
                     'compl': '%-'}),
])

######################################
# Main
######################################

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '',
                        'wee_ns_script_unload_cb'):
        weechat.hook_completion('ns_send', 'login completion',
                                'wee_ns_hook_completion_send', '')
        weechat.hook_command('ns', 'weeNetsoul: A netsoul plugin for weechat',
                             ' | '.join("%s%s" % (k, "" if 'desc' not in v
                                                  else " " + v['desc'])
                                        for k, v in hook_cmd_ns.items()),
                             '\n'.join("%s: %s" % (k, v['cb'].__doc__)
                                       for k, v in hook_cmd_ns.items()),
                             ' || '.join("%s%s" % (k, "" if 'compl' not in v
                                                   else " " + v['compl'])
                                         for k, v in hook_cmd_ns.items()),
                             'wee_ns_hook_cmd_ns', '')
        wee_ns_config_file = weechat.config_new(SCRIPT_NAME, '', '')
        wee_ns_conf_serv_sect = weechat.config_new_section(wee_ns_config_file,
                                                           'server', 0, 0,
                                                           ('wee_ns_serv_'
                                                            'sect_read_cb'),
                                                           '', '', '', '', '',
                                                           '', '', '', '')
        server = WeeNSServer()
        weechat.config_read(wee_ns_config_file)
        weechat.config_write(wee_ns_config_file)
