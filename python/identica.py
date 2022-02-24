# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010 by Nicolas Reynolds <fauno@kiwwwi.com.ar>
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

## ABOUT
# This plugin gives format to identi.ca's bot messages, converting
# the @sender into the bot's nick and colorizing usernames, groups
# and hashtags.

# For example:
# 11:37:45 update | fauno: hi there

# Will turn into
# 11:37:45 fauno | hi there

# It's written for bitlbee, but should work with anything that permits
# the XMPP bot open a query buffer with you.

# Since version 0.2 it includes suscription handling and whois
# habilities.

# HISTORY
# 2009-07-27, fauno:
#        initial release
#
# 2009-09-17, fauno:
#       added basic suscription handling (sub/unsub/block/unblock)
#       username whois
#       remind user color
#
# 2009-09-27, fauno:
#       help definition
#
# 2009-10-11, fauno:
#       hability to check up to 20 updates from users (/sn updates <username> <quantity>)
#
# 2010-01-20, fauno:
#       fixed int to str error caused by api changes.
#       default regexp's for @names, etc. includes trailing space
#
# 2010-03-15, fauno:
#       new commands:
#       - groups see in which groups a user is subscribed
#       - join   join a group
#       - leave  leave a group
#       - group  group profile
#
#      nick completion adding %(sn_nicks) to weechat.completion.default_template
#      unicode hashtags, usernames and groups
#        (changes in plugins.var.python.identica.nick_re
#                    plugins.var.python.identica.hashtag_re
#                    plugins.var.python.identica.group_re)
#      prepopulate nicklist with plugins.var.python.identica.prepopulate
#        (will take a while to download all subscriptions)
#
# 2011-01-16, fauno:
#      - Removed chat_nick_colors in favor of configurable array (useful for
#        weechat's 256 colors on 0.3.4)
#        see plugins.var.python.identica.colors
#      - Fixed nick completion
#
# 2011-01-18, fauno:
#      - Fixed error on load when no username nor password were given
#
# 2020-05-09, FlashCode:
#      - Add compatibility with new weechat_print modifier data
#        (WeeChat >= 2.9)
#
# TODO - cache json requests

import weechat
import re
import urllib2
import simplejson as json

from base64 import encodestring
from urllib import urlencode
from random import randint


SCRIPT_NAME    = 'identica'
SCRIPT_AUTHOR  = 'fauno <fauno@kiwwwi.com.ar>'
SCRIPT_VERSION = '0.4.3'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Formats identi.ca\'s bot messages'

settings = {
        'username'                : '',
        'password'                : '',
        'service'                 : 'identi.ca',
        'scheme'                  : 'https',
        'channel'                 : 'localhost.update',
        're'                      : '^(?P<update>\w+)(?P<separator>\W+?)(?P<username>\w+): (?P<dent>.+)$',
        'me'                      : '^(?P<update>\w+)(?P<separator>\W+?)(?P<username>\w+): \/me (?P<dent>.+)$',

        'nick_color'              : 'green',
        'hashtag_color'           : 'blue',
        'group_color'             : 'red',

        'nick_color_identifier'   : 'blue',
        'hashtag_color_identifier': 'green',
        'group_color_identifier'  : 'green',

        'nick_re'                 : '(@)(\w+)',
        'hashtag_re'              : '(#)(\w+)',
        'group_re'                : '(!)(\w+)',

        'prepopulate'             : 'on',
        'completion_blacklist'    : '',

        'shorten'                 : 'on',
        'shorten_service'         : 'http://ur1.ca',

        'colors'                  : 'red,lightred,green,lightgreen,brown,yellow,blue,lightblue,magenta,lightmagenta,cyan,lightcyan,white'
}

users = {}
groups = {}

class StatusNet():
    def __init__(self, username, password, scheme, service):

        self.username = username
        self.password = password

        self.realm    = 'StatusNet API'
        self.service  = service
        self.scheme   = scheme

        self.opener = self.__get_auth_opener()

    def __get_auth_opener(self):
        '''Authentication'''
        basic_auth = encodestring(':'.join([self.username, self.password]))
        basic_auth = ' '.join(['Basic', basic_auth])

        handler = urllib2.HTTPBasicAuthHandler()
        handler.add_password(realm=self.realm,
                             uri=self.service,
                             user=self.username,
                             passwd=self.password)
        
        self.headers = {'Authorization':basic_auth}
        return urllib2.build_opener(handler)

    def build_request(self, api_method, api_action, user_or_id, data={}):
        '''Builds an API request'''
        url = '%s://%s/api/%s/%s/%s.json' % (self.scheme,
                                             self.service,
                                             api_method,
                                             api_action,
                                             user_or_id)

        request = urllib2.Request(url, urlencode(data), self.headers)
        return request

    def handle_request(self, request):
        '''Sends an API request and handles errors'''
        try:
            response = self.opener.open(request)
        except urllib2.HTTPError, error:
            if error.code == 403:
                return False
            else:
                weechat.prnt(weechat.current_buffer(),
                             '%s[%s] Server responded with a %d error code' % (weechat.prefix('error'),
                                                                               self.service,
                                                                               error.code))
                return None
        else:
            return response

# End of StatusNet

class ur1():
    '''Shortens URL using ur1.ca free service'''
    def __init__ (self, service='http://ur1.ca'):
        self.service = service

    def __build_request (self, url):
        data = { 'longurl' : url }
        return urllib2.Request(self.service, urlencode(data))

    def __handle_request (self, request):
        try:
            response = urllib2.urlopen(request)
            return re.findall(r'Your ur1 is: <a[^>]*>([^<]*)', response.read(), re.UNICODE)[0]

        except urllib2.HTTPError, error:
            weechat.prnt('', '%s[%s] Got a HTTP %d error code, sending long url.' % (weechat.prefix('error'), self.service, error.code))
            return False

    def shorten (self, url):
        return self.__handle_request(self.__build_request(url))


## User functions
def subscribe (username):
    '''Subscribes to a user'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR

    response = statusnet_handler.handle_request(statusnet_handler.build_request('friendships', 'create', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sYou\'re already suscribed to %s' % (weechat.prefix('error'), username)))
    else:
        weechat.prnt(weechat.current_buffer(), ('%sSuscribed to %s updates' % (weechat.prefix('join'), username)))

    return weechat.WEECHAT_RC_OK


def unsubscribe (username):
    '''Drops a subscription'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR

    response = statusnet_handler.handle_request(statusnet_handler.build_request('friendships', 'destroy', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sYou aren\'t suscribed to %s' % (weechat.prefix('error'), username)))
    else:
        weechat.prnt(weechat.current_buffer(), ('%sUnsuscribed from %s\'s updates' % (weechat.prefix('quit'), username)))
    
    return weechat.WEECHAT_RC_OK


def whois (username):
    '''Shows profile information about a given user'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR
    
    response = statusnet_handler.handle_request(statusnet_handler.build_request('users', 'show', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t retrieve information about %s' % (weechat.prefix('error'), username)))
    else:
        whois = json.load(response)

        whois['summary'] = ' '.join([u'\u00B5', str(whois['statuses_count']),
                                     u'\u2764', str(whois['favourites_count']),
                                     'subscribers', str(whois['followers_count']),
                                     'subscriptions', str(whois['friends_count'])])

        for property in ['name', 'description', 'url', 'location', 'profile_image_url', 'summary']:
            if property in whois and whois[property] != None:
                weechat.prnt(weechat.current_buffer(), ('%s[%s] %s' % (weechat.prefix('network'),
                                                                       nick_color(username),
                                                                       whois[property].encode('utf-8'))))
        
    return weechat.WEECHAT_RC_OK


def block (username):
    '''Blocks users'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR

    response = statusnet_handler.handle_request(statusnet_handler.build_request('blocks', 'create', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t block %s' % (weechat.prefix('error'), username)))
    else:
        weechat.prnt(weechat.current_buffer(), ('%sBlocked %s' % (weechat.prefix('network'), username)))
        
    return weechat.WEECHAT_RC_OK


def unblock (username):
    '''Unblocks users'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR

    response = statusnet_handler.handle_request(statusnet_handler.build_request('blocks', 'destroy', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t unblock %s' % (weechat.prefix('error'), username)))
    else:
        weechat.prnt(weechat.current_buffer(), ('%sUnblocked %s' % (weechat.prefix('network'), username)))
        
    return weechat.WEECHAT_RC_OK


def updates (username, quantity):
    '''Shows user updates'''
    if len(username) == 0 or quantity > 20:
        return weechat.WEECHAT_RC_ERROR

    if quantity < 1:
        quantity = 1

    response = statusnet_handler.handle_request(statusnet_handler.build_request('statuses', 'user_timeline', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t retrieve %s\'s updates' % (weechat.prefix('error'), username)))
    else:
        statuses = json.load(response)[:quantity]
        while quantity > 0:
            quantity -= 1
            weechat.prnt_date_tags(weechat.buffer_search('', weechat.config_get_plugin('channel')), 0, 'irc_privmsg', 'update\t%s: %s' % (username, statuses[quantity]['text'].encode('utf-8')))

    return weechat.WEECHAT_RC_OK


## Group functions
def group (group):
    '''Shows information about a group'''
    if len(group) == 0:
        return weechat.WEECHAT_RC_ERROR
    
    response = statusnet_handler.handle_request(statusnet_handler.build_request('statusnet/groups', 'show', group))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t show %s' % (weechat.prefix('error'), group)))
    else:
        group_info = json.load(response)
        for property in ['fullname', 'description', 'homepage_url', 'location', 'original_logo']:
            if property in group_info and group_info[property] != None:
                weechat.prnt(weechat.current_buffer(), ('%s[%s] %s' % (weechat.prefix('network'),
                                                                       group,
                                                                       group_info[property].encode('utf-8'))))

    return weechat.WEECHAT_RC_OK


def groups (username):
    '''Shows groups a user is in'''
    if len(username) == 0:
        return weechat.WEECHAT_RC_ERROR
    
    response = statusnet_handler.handle_request(statusnet_handler.build_request('statusnet/groups', 'list', username))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), '%sCan\'t show %s\'s groups' % (weechat.prefix('error'), username))
    else:
        groups     = json.load(response)
        group_list = ' '.join([group['nickname'].encode('utf-8') for group in groups])

        weechat.prnt(weechat.buffer_search('', weechat.config_get_plugin('channel')),
                     '%sGroups %s is in: %s' % (weechat.prefix('network'),
                                                nick_color(username),
                                                group_list))

    return weechat.WEECHAT_RC_OK


def join (group):
    '''Joins a group'''
    if len(group) == 0:
        return weechat.WEECHAT_RC_ERROR
    
    response = statusnet_handler.handle_request(statusnet_handler.build_request('statusnet/groups', 'join', group))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t join group %s' % (weechat.prefix('error'), group)))
    else:
        group_info = json.load(response)
        weechat.prnt(weechat.current_buffer(), '%sYou joined group %s (%s)' % (weechat.prefix('network'), group_info['fullname'].encode('utf-8'), group))

    return weechat.WEECHAT_RC_OK


def leave (group):
    '''Leaves a group'''
    if len(group) == 0:
        return weechat.WEECHAT_RC_ERROR
    
    response = statusnet_handler.handle_request(statusnet_handler.build_request('statusnet/groups', 'leave', group))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t leave %s' % (weechat.prefix('error'), group)))
    else:
        group_info = json.load(response)
        weechat.prnt(weechat.current_buffer(), '%sYou left group %s (%s)' % (weechat.prefix('network'), group_info['fullname'].encode('utf-8'), group))

    return weechat.WEECHAT_RC_OK


def populate_subscriptions ():
    '''Populates users dict with subscriptions'''
    response = statusnet_handler.handle_request(statusnet_handler.build_request('statuses', 'friends', weechat.config_get_plugin('username')))

    if response == None:
        pass
    elif response == False:
        weechat.prnt(weechat.current_buffer(), ('%sCan\'t obtain subscription list ' % weechat.prefix('error')))
    else:
        subscriptions = json.load(response)
        for profile in subscriptions:
            populate = nick_color(profile['screen_name'].encode('utf-8'))

        weechat.prnt(weechat.buffer_search('', weechat.config_get_plugin('channel')), ' '.join([ weechat.prefix('network'), 'Subscriptions', '(%d)' % len(users)] + [username for username in users]))

    return weechat.WEECHAT_RC_OK


## Parsing and formatting functions
def colorize (message):
    '''Colorizes replies, hashtags and groups'''

    for identifier in ['nick','hashtag','group']:
        identifier_name = ''.join([identifier, '_re'])
        identifier_color = ''.join([identifier, '_color'])
        identifier_color_identifier = ''.join([identifier, '_color_identifier'])

        identifier_re = re.compile(weechat.config_get_plugin(identifier_name), re.UNICODE)

        replace = r''.join([
            weechat.color(weechat.config_get_plugin(identifier_color_identifier)),
            '\\1',
            weechat.color(weechat.config_get_plugin(identifier_color)),
            '\\2',
            weechat.color('reset')
            ])

        message = identifier_re.sub(replace, message)

    return message


def nick_color (nick):
    '''Randomizes color for nicks'''
# Get the colors
    colors   = weechat.config_get_plugin('colors').split(',')

    if nick in users and 'color' in users[nick]:
        pass
    else:
        users[nick] = {}
        users[nick]['color'] = ''.join(colors[randint(0,len(colors)-1)])

    nick = ''.join([weechat.color(users[nick]['color']), nick, weechat.color('reset')])
    return nick


def clean (message):
    '''Cleans URLs added by bot'''
    return re.sub(r''.join([' \(http://', service, '/[a-zA-Z0-9/\-_#]+\)']), '', message)


def parse_in (server, modifier, data, the_string):
    '''Parses incoming messages'''

    if data.startswith('0x'):
        # WeeChat >= 2.9
        buffer, flags = data.split(';', 1)
    else:
        # WeeChat <= 2.8
        plugin, buffer_name, flags = data.split(';', 2)
        buffer = weechat.buffer_search(plugin, buffer_name)

    channel = weechat.buffer_get_string(buffer, 'localvar_channel')

    flag = flags.split(',')

    if channel == weechat.config_get_plugin('channel') and 'irc_privmsg' in flag:
        the_string = weechat.string_remove_color(the_string, '')
        matcher = re.compile(weechat.config_get_plugin('re'), re.UNICODE)

        m = matcher.search(the_string)

        if not m \
           or m.group('update') == weechat.config_get_plugin('username'):
            return colorize(the_string)

        dent     = colorize(clean(m.group('dent')))
        username = nick_color(m.group('username'))

        the_string = ''.join([ username, m.group('separator'), dent ])

    return the_string


def parse_out (server, modifier, data, the_string):
    '''Parses outgoing messages, provides @nick completion and url shortening'''
    # data => localhost
    # the_string => PRIVMSG update :help
    # server => 
    # modifier => irc_out_PRIVMSG

    command, buffer, message = the_string.split(' ', 2)
    channel = '.'.join([data, buffer])

    if channel == weechat.config_get_plugin('channel'):
        completion_blacklist = weechat.config_get_plugin('completion_blacklist').split(',')

        # the regexp will match any word that is not preceded by [@#!]
        # oddly, for "@fauno", it will match "auno", when the opposite
        # "(?<=[@#!])\w+" matches the full word with prefix ("@fauno")
        # nevertheless, it breaks the word, so it'll never match an
        # already prefixed nick, hashtag nor group name.
        for word in re.findall(r'[\S]+[^\W]', message, re.UNICODE):
            if word in users and not word in completion_blacklist:
                message = re.sub(r''.join(['(?<![#@!])',word]), ''.join(['@', word]), message)

        if weechat.config_get_plugin('shorten') == 'on':
            u = ur1(weechat.config_get_plugin('shorten_service'))
            for url in re.findall(r'http://[^ ]*', message, re.UNICODE):
                if len(url) > 20:
                    s = u.shorten(url)
                    if s != False:
                        message = message.replace(url, s)

        the_string = ' '.join([command, buffer, message])

    return the_string

## /SN functions
def nicklist(data, completion_item, buffer, completion):
    '''Completion for /sn'''

    if weechat.buffer_get_string(buffer, 'name') == weechat.config_get_plugin('channel'):
        for username in users:
            weechat.hook_completion_list_add(completion, username, 1, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


def sn (data, buffer, args):
    '''/sn command'''
    if args == '':
        weechat.command('', '/help sn')
        return weechat.WEECHAT_RC_OK
    
    argv = args.strip().split(' ')

    if argv[0] == 'subscribe':
        subscribe(argv[1])
    elif argv[0] == 'unsubscribe':
        unsubscribe(argv[1])
    elif argv[0] == 'whois':
        whois(argv[1])
    elif argv[0] == 'block':
        block(argv[1])
    elif argv[0] == 'unblock':
        unblock(argv[1])
    elif argv[0] == 'updates':
        try:
            updates(argv[1], int(argv[2]))
        except:
            updates(argv[1], 20)
    elif argv[0] == 'join':
        join(argv[1])
    elif argv[0] == 'leave':
        leave(argv[1])
    elif argv[0] == 'group':
        group(argv[1])
    elif argv[0] == 'groups':
        try:
            groups(argv[1])
        except:
            groups(weechat.config_get_plugin('username'))

    return weechat.WEECHAT_RC_OK
    
    

## init
if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    for option, default_value in settings.iteritems():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    username = weechat.config_get_plugin('username')
    password = weechat.config_get_plugin('password')
    service  = weechat.config_get_plugin('service')
    scheme   = weechat.config_get_plugin('scheme')

    if len(username) == 0 or len(password) == 0:
        weechat.prnt(weechat.current_buffer(),
                    '%s[%s] Please set your username and password and reload the plugin to get the /sn commands working' %
                    (weechat.prefix('error'), service))
    else:
        statusnet_handler = StatusNet(username, password, scheme, service)

        if weechat.config_get_plugin('prepopulate') == 'on':
            populate_subscriptions()

    # hook incoming messages for parsing
    weechat.hook_modifier('weechat_print', 'parse_in', '')
    # hook outgoing messages for nick completion
    weechat.hook_modifier('irc_out_privmsg', 'parse_out', '')

    # /sn
    weechat.hook_command('sn',
                         'StatusNet manager',
                         'whois | subscribe | unsubscribe | block | unblock | updates | groups <username> || group | join | leave <group>',
                         '        whois: retrieves profile information from <username>'
                         "\n"
                         '    subscribe: subscribes to <username>'
                         "\n"
                         '  unsubscribe: unsubscribes from <username>'
                         "\n"
                         '        block: blocks <username>'
                         "\n"
                         '      unblock: unblocks <username>'
                         "\n"
                         '      updates: recent updates from <username> <quantity (<20)>'
                         "\n"
                         '         join: joins group <group>'
                         "\n"
                         '        leave: leaves group <group>'
                         "\n"
                         '       groups: groups (<username>) you or a specified username is subscribed'
                         "\n"
                         '        group: shows info about <group>',
                         'whois %(sn_nicks) || subscribe %(sn_nicks) || unsubscribe %(sn_nicks) || block %(sn_nicks) || unblock %(sn_nicks) || updates %(sn_nicks) || join || leave || group || groups',
                         'sn',
                         '')

    # Completion for /sn commands
    weechat.hook_completion('sn_nicks', 'list of SN users', 'nicklist', '')

