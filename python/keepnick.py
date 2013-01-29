# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2013 by nils_2 <weechatter@arcor.de>
# Copyright (c) 2006 by EgS <i@egs.name>
#
# script to keep your nick and recover it in case it's occupied
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
# 2013-01-27: nils_2 (freenode.#weechat)
#       0.8 : make script compatible with Python 3.x
#
# 2012-10-05: nils_2, (freenode.#weechat)
#       0.7 : add options "plugins.var.python.keepnick.nickserv", "plugins.var.python.keepnick.<server>.password"
#           : changed default "delay" value from 60 to 600 seconds.
#
# 2012-10-04: nils_2, (freenode.#weechat)
#       0.6 : fix bug with case-sensitive nicks (reported by Faethor)
#
# 2012-02-08: nils_2, (freenode.#weechat)
#       0.5 : sync with 0.3.x API (requested by CAHbI4)
#
# requires: WeeChat version 0.3.4
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
#######################################################################
#                                                                     #
# This script enables the user to keep their nicks and recover it in  #
# case it get's stolen. It uses the servers prefered nicks, so there  #
# is no need for any kind of setup.                                   #
#                                                                     #
# Name:    Keepnick                                                   #
# Licence: GPL v2                                                     #
# Author:  Marcus Eggenberger <i@egs.name>                            #
#                                                                     #
#  Usage:                                                             #
#   /keepnick on|off|<positive number>                                #
#                                                                     #
#   use /help command for  detailed information                       #
#                                                                     #
#  Changelog:                                                         #
#   0.4: now starts on load and features user defined check intervals #
#   0.3: Fixed major bug with continuous nickchanges                  #
#   0.2: Fixed Bug: now only checks connected servers                 #
#   0.1: first version released                                       #
#                                                                     #
#######################################################################

try:
    from string import Template
    import weechat,sys#


except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

# -------------------------------[ Constants ]-------------------------------------
SCRIPT_NAME     = "keepnick"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.8"
SCRIPT_LICENCE  = "GPL3"
SCRIPT_DESC     = "keep your nick and recover it in case it's occupied"

ISON            = '/ison %s'

OPTIONS         =       { 'delay'       : ('600','delay (in seconds) to look at occupied nick (0 means OFF). It is not recommended to flood the server with /ison requests)'),
                          'timeout'     : ('60','timeout (in seconds) to wait for an answer from server.'),
                          'serverlist'  : ('','comma separated list of servers to look at. Try to register a nickname on server (see: /msg NickServ help).'),
                          'text'        : ('Nickstealer left Network: %s!','text that will be displayed if your nick will not be occupied anymore. (\"%s\" is a placeholder for the servername)'),
                          'nickserv'    : ('/msg -server $server NICKSERV IDENTIFY $passwd','use this command to IDENTIFY you on server (following placeholder will be used: \"$server\" for server; \"$passwd\" for password. You have to create a option \"plugins.var.python.%s.<servername>.password\" to store your nick password. Use SASL authentification, if possible.' %  SCRIPT_NAME),
                          'command'     : ('/nick %s','This command will be used to rename your nick (\"%s\" will be filled with your nickname for specific server)'),
                        }
HOOK            =       { 'timer': '', 'redirect': '' }
serverlist = []

# ================================[ redirection ]===============================
# calling /ison all x seconds using hook:timer()
def ison(bufpointer,servername,nick,nicklist):
    command = ISON % ' '.join(nicklist)
    weechat.hook_hsignal_send('irc_redirect_command',
                                  { 'server': servername, 'pattern': 'ison', 'signal': SCRIPT_NAME, 'count': '1', 'string': servername, 'timeout': OPTIONS['timeout'], 'cmd_filter': '' })
    weechat.hook_signal_send('irc_input_send', weechat.WEECHAT_HOOK_SIGNAL_STRING, '%s;;;;%s' % (servername,command))

def redirect_isonhandler(data, signal, hashtable):
    if hashtable['output'] == '':
        return weechat.WEECHAT_RC_OK

    nothing, message, nicks = hashtable['output'].split(':')
    nicks = [nick.lower() for nick in nicks.split()]
    for nick in server_nicks(hashtable['server']):
        mynick = weechat.info_get('irc_nick',hashtable['server'])
        if nick.lower() == mynick.lower():
            return weechat.WEECHAT_RC_OK
        elif nick.lower() not in nicks:
            password = weechat.config_get_plugin('%s.password' % hashtable['server'])   # get password for given server
            grabnick(hashtable['server'], nick)                                         # get your nick back
            if (password) != '':
                if OPTIONS['nickserv'] == '':
                    return weechat.WEECHAT_RC_OK
                t = Template(OPTIONS['nickserv'])
                run_msg = t.safe_substitute(server=hashtable['server'], passwd=password)
                weechat.command('',run_msg)
            return weechat.WEECHAT_RC_OK

    if 0 in [nick.lower() in [mynick.lower() for mynick in server_nicks(hashtable['server'])] for nick in nicks]:
        # if any nick which is return by ison is not on our checklist we're not the caller
        return weechat.WEECHAT_RC_OK
    else:
        # seems like we're the caller -> ignore the output
        return weechat.WEECHAT_RC_OK

# ================================[ functions ]===============================
def server_nicks(servername):
    infolist = weechat.infolist_get('irc_server','',servername)
    weechat.infolist_next(infolist)
    nicks = weechat.infolist_string(infolist, 'nicks')
    weechat.infolist_free(infolist)
    return nicks.split(',')

def check_nicks(data, remaining_calls):
    serverlist = OPTIONS['serverlist'].split(',')
    infolist = weechat.infolist_get('irc_server','','')

    while weechat.infolist_next(infolist):
        servername = weechat.infolist_string(infolist, 'name')
        ptr_buffer = weechat.infolist_pointer(infolist,'buffer')
        nick = weechat.infolist_string(infolist, 'nick')
        ssl_connected = weechat.infolist_integer(infolist,'ssl_connected')
        is_connected = weechat.infolist_integer(infolist,'is_connected')
        if servername in serverlist:
            if nick and ssl_connected + is_connected:
                ison(ptr_buffer,servername,nick,server_nicks(servername))
    weechat.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK

def grabnick(servername, nick):
    if nick and servername:
        weechat.prnt(weechat.current_buffer(),OPTIONS['text'] % servername)
        weechat.command(weechat.buffer_search('irc','%s.%s' % ('server',servername)), OPTIONS['command'] % nick)

# ================================[ weechat hook ]===============================
def install_hooks():
    global HOOK,OPTIONS

    if HOOK['timer'] != '' or HOOK['redirect'] != '':                                     # should not happen, but...
        return

    if not OPTIONS['delay'] or not OPTIONS['timeout']:
        return
    HOOK['timer'] = weechat.hook_timer(int(OPTIONS['delay']) * 1000, 0, 0, 'check_nicks', '')
    HOOK['redirect'] = weechat.hook_hsignal('irc_redirection_%s_ison' % SCRIPT_NAME, 'redirect_isonhandler', '' )

    if HOOK['timer'] == 0:
        weechat.prnt('',"%s: can't enable %s, hook_timer() failed" % (weechat.prefix('error'), SCRIPT_NAME))
    if HOOK['redirect'] == 0:
        weechat.prnt('',"%s: can't enable %s, hook_signal() failed" % (weechat.prefix('error'), SCRIPT_NAME))

def remove_hooks():
    global HOOK

    if HOOK['timer'] != '':
        weechat.unhook(HOOK['timer'])
        HOOK['timer'] = ''
    if HOOK['redirect'] != '':
        weechat.unhook(HOOK['redirect'])
        HOOK['redirect'] = ''

# ================================[ weechat options and description ]===============================
def init_options():
    global HOOK,OPTIONS
    for option,value in list(OPTIONS.items()):
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)

def toggle_refresh(pointer, name, value):
    global HOOK,OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]              # get optionname
    OPTIONS[option] = value                                                     # save new value

    if option == 'delay' or option == 'timeout':
        if int(OPTIONS['delay']) > 0 or int(OPTIONS['timeout']) > 0:
            remove_hooks()
            install_hooks()
        else:
            remove_hooks()                                                  # user switched timer off
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == '__main__':
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENCE, SCRIPT_DESC, '','')

    version = weechat.info_get("version_number", "") or 0
    if int(version) >= 0x00030400:
        if int(OPTIONS['delay'][0]) > 0 and int(OPTIONS['timeout'][0]) > 0:
            init_options()
            install_hooks()
            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
    else:
        weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 0.3.4 or higher'))
        weechat.command('','/wait 1ms /python unload %s' % SCRIPT_NAME)
