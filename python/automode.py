# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2010 by Elián Hanisch <lambdae2@gmail.com>
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
###

###
#
#   Script for auto op/voice users.
#
#   It uses expressions for match user's usermasks when they join. Use at your own risk.
#
#   Commands:
#   * /automode: see /help automode
#
#   Settings:
#   * plugins.var.python.automode.enabled:
#     Self-explanatory, disables/enables automodes.
#     Valid values: 'on', 'off' Default: 'on'
#
#   2011-09-20
#   version 0.1.1: fix bug with channels with uppercase letters.
#
###

SCRIPT_NAME    = "automode"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Script for auto op/voice users when they join."

try:
    import weechat
    from weechat import prnt
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"
    import_ok = False

from fnmatch import fnmatch

def debug(s, *args):
    if not isinstance(s, basestring):
        s = str(s)
    if args:
        s = s %args
    prnt('', '%s\t%s' % (script_nick, s))

# settings
settings = { 'enabled': 'on' }

################
### Messages ###

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), script_nick, s))

def say(s, buffer=''):
    """normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(script_nick, s))

##############
### Config ###

boolDict = {'on':True, 'off':False}
def get_config_boolean(config):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_list(config):
    value = weechat.config_get_plugin(config)
    if value:
        return value.split(',')
    else:
        return []

#################
### Functions ###

def find_matching_users(server, channel, pattern):
    # this is for check patterns when they are added
    infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
    L = []
    while weechat.infolist_next(infolist):
        nick = weechat.infolist_string(infolist, 'name')
        host = weechat.infolist_string(infolist, 'host')
        userhost = '%s!%s' %(nick, host)
        if fnmatch(userhost.lower(), pattern):
            L.append(nick)
    weechat.infolist_free(infolist)
    return L

def get_userhost(server, channel, nick):
    try:
        infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
        while weechat.infolist_next(infolist):
            _nick = weechat.infolist_string(infolist, 'name').lower()
            if _nick == nick:
                host = weechat.infolist_string(infolist, 'host')
                userhost = '%s!%s' %(nick, host)
                return userhost.lower()
    finally:
        weechat.infolist_free(infolist)

def get_patterns_in_config(filter):
    d = {}
    infolist = weechat.infolist_get('option', '', 'plugins.var.python.%s.%s' %(SCRIPT_NAME, filter))
    while weechat.infolist_next(infolist):
        name = weechat.infolist_string(infolist, 'option_name')
        name = name[len('python.%s.' %SCRIPT_NAME):]
        # channels might have dots in their names, so we'll strip type from right and server
        # from left. Lets hope that users doesn't use dots in server names.
        name, _, type = name.rpartition('.')
        if type not in ('op', 'halfop', 'voice'):
            # invalid option
            continue
        server, _, channel = name.partition('.')
        value = weechat.infolist_string(infolist, 'value')
        if not value:
            continue
        else:
            value = value.split(',')
        key = (server, channel)
        if key not in d:
            d[key] = {type:value}
        else:
            d[key][type] = value
    weechat.infolist_free(infolist)
    return d

########################
### Script callbacks ###

def join_cb(data, signal, signal_data):
    #debug('JOIN: %s %s', signal, signal_data)
    prefix, _, channel = signal_data.split()
    prefix = prefix[1:].lower()
    if channel[0] == ':':
        channel = channel[1:]
    server = signal[:signal.find(',')]
    for type in ('op', 'halfop', 'voice'):
        list = get_config_list('.'.join((server.lower(), channel.lower(), type)))
        for pattern in list:
            #debug('checking: %r - %r', prefix, pattern)
            if fnmatch(prefix, pattern):
                buffer = weechat.buffer_search('irc', '%s.%s' %(server, channel))
                if buffer:
                    weechat.command(buffer, '/%s %s' %(type, prefix[:prefix.find('!')]))
                return WEECHAT_RC_OK
    return WEECHAT_RC_OK


def command(data, buffer, args):
    global join_hook
    if not args:
        args = 'list'
            
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    
    args = args.split()
    cmd = args[0]
    try:
        if cmd in ('add', 'del'):
            if not weechat.info_get('irc_is_channel', channel):
                error("Not an IRC channel buffer.")
                return WEECHAT_RC_OK

            type, match = args[1], args[2:]
            if type not in ('op', 'voice', 'halfop'):
                raise ValueError("valid values are 'op', 'halfop' and 'voice'.")
            if not match:
                raise ValueError("missing pattern or nick.")
            match = match[0].lower()
            config = '.'.join((server, channel.lower(), type))
            L = get_config_list(config)

            if cmd == 'add':
                # check if pattern is a nick
                if weechat.info_get('irc_is_nick', match):
                    userhost = get_userhost(server, channel, match)
                    if userhost:
                        match = userhost.lower()
                nicks = find_matching_users(server, channel, match)
                n = len(nicks)
                if n == 0:
                    say("'%s' added, matches 0 users." %match, buffer)
                elif n == 1:
                    say("'%s' added, matches 1 user: %s" %(match, nicks[0]),
                            buffer)
                elif n > 1:
                    say("'%s' added, matches %s%s%s users: %s" %(
                        match, weechat.color('lightred'), n, color_reset,
                        ' '.join(nicks)), buffer)
                if match not in L:
                    L.append(match)
            elif cmd == 'del':
                    if match not in L:
                        say("'%s' not found in %s.%s" %(match, server, channel), buffer)
                    else:
                        say("'%s' removed." %match, buffer)
                        del L[L.index(match)]
            
            if L:
                weechat.config_set_plugin(config, ','.join(L))
            else:
                weechat.config_unset_plugin(config)

        elif cmd == 'disable':
            if join_hook:
                weechat.unhook(join_hook)
            weechat.config_set_plugin('enabled', 'off')
            say("%s script disabled." %SCRIPT_NAME, buffer)
        elif cmd == 'enable':
            if join_hook:
                weechat.unhook(join_hook)
            join_hook = weechat.hook_signal('*,irc_in_join', 'join_cb', '')
            weechat.config_set_plugin('enabled', 'on')
            say("%s script enabled." %SCRIPT_NAME, buffer)
        elif cmd == 'list':
            if weechat.info_get('irc_is_channel', channel):
                filter = '%s.%s.*' %(server, channel)
            else:
                filter = '*'
                buffer = '' # print in core buffer
            if not get_config_boolean('enabled'):
                say('Automodes currently disabled.', buffer)
            patterns = get_patterns_in_config(filter)
            if not patterns:
                if buffer:
                    say('No automodes for %s.' %channel, buffer)
                else:
                    say('No automodes.', buffer)
                return WEECHAT_RC_OK
            for key, items in patterns.iteritems():
                say('%s[%s%s.%s%s]' %(color_chat_delimiters,
                                      color_chat_buffer,
                                      key[0], key[1],
                                      color_chat_delimiters), buffer)
                for type, masks in items.iteritems():
                    for mask in masks:
                        say('  %s%s%s: %s%s' %(color_chat_nick, type,
                                               color_chat_delimiters,
                                               color_reset,
                                               mask), buffer)
        else:
            raise ValueError("'%s' isn't a valid option. See /help %s" %(cmd, SCRIPT_NAME))
    except ValueError, e:
        error('Bad argument: %s' %e)
        return WEECHAT_RC_OK

    return WEECHAT_RC_OK


def completer(data, completion_item, buffer, completion):
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    if not weechat.info_get('irc_is_channel', channel):
        return WEECHAT_RC_OK

    server = weechat.buffer_get_string(buffer, 'localvar_server')
    input = weechat.buffer_get_string(buffer, 'input')
    type = input.split()[2]
    patterns = get_patterns_in_config('%s.%s.%s' %(server, channel, type))

    if not patterns:
        return WEECHAT_RC_OK

    for mask in patterns[(server, channel)][type]:
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)

    return WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):
    
    # colors
    color_chat_delimiters = weechat.color('chat_delimiters')
    color_chat_nick       = weechat.color('chat_nick')
    color_reset           = weechat.color('reset')
    color_chat_buffer     = weechat.color('chat_buffer')

    # pretty [automode]
    script_nick = '%s[%s%s%s]%s' %(color_chat_delimiters,
                                   color_chat_nick,
                                   SCRIPT_NAME,
                                   color_chat_delimiters,
                                   color_reset)

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
                weechat.config_set_plugin(opt, val)

    global join_hook
    if get_config_boolean('enabled'):
        join_hook = weechat.hook_signal('*,irc_in_join', 'join_cb', '') 
    else:
        join_hook = ''

    weechat.hook_completion('automode_patterns', 'automode patterns', 'completer', '')
    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC ,
            "[ (add|del) <type> <nick|expression> | list | disable | enable ]",
            "       add: Adds a new automode for current channel. If a nick is given instead of an"
            " expression, it will use nick's exact usermask.\n"
            "       del: Removes an automode in current channel.\n"
            "      type: Specifies the user mode, it should be either 'op', 'halfop' or 'voice'.\n"
            "expression: Case insensible expression for match users when they join current channel."
            " It should be of the format 'nick!user@host', wildcards '?', '*', and character groups"
            " are allowed.\n"
            "      list: List automodes for current channel, or all automodes if current buffer"
            " isn't an IRC channel. This is the default action if no option is given.\n"
            "   disable: Disables the script.\n"
            "    enable: Enables the script.\n"
            "\n"
            "Be careful with the expressions you use, they must be specific and match only one"
            " user, if they are too vague, like 'nick!*' you might op users you don't want and lose"
            " control of your channel.",
            "add op|halfop|voice %(nicks)"\
            "||del op|halfop|voice %(automode_patterns)"\
            "||list||disable||enable", 'command', '')
