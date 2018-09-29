# -*- coding: utf-8 -*-
# execbot.py
# ExecBot - Executing bot
# ==============================
#
# Copyright (C) 2018 Giap Tran <txgvnn@gmail.com>
#  https://github.com/txgvnn/weechat-execbot
#
# == About =====================
# Execbot is a bot can execute the command from IRC message
# (You maybe want to call it is a kind of backdoor)
#
# With server is installed execbot script, the client can execute the
# command remote by send privmsg to server's nick in IRC network
#
# == Usage =====================
# /excebot list                                List server.nicknames are allowed
# /execbot add -server <server> nicknames..    Add server.nicknames are allowed to execute
# /execbot del -server <server> nicknames..    Remove server.nicknames are allowed
#
# == NOTICE ====================
# This is a POC that I want to execute a remote command via IRC
# network. It's really not security, although you can set who can
# talk with the bot.
#
# PLEASE CONSIDER CAREFULLY WHEN USING THE PLUGIN

import weechat

SCRIPT_NAME      = 'execbot'
SCRIPT_AUTHOR    = 'Giap Tran <txgvnn@gmail.com>'
SCRIPT_VERSION   = '1.1'
SCRIPT_LICENSE   = 'GPL3'
SCRIPT_DESC      = 'Executing bot'
SCRIPT_HELP_TEXT = '''
%(bold)sExecbot command options: %(normal)s
list                                   List nicknames
add -server <server>  <nicknames...>   Add server.nicknames are allowed to execute
del -server <server>  <nicknames...>   Del server.nicknames are allowed

%(bold)sExamples: %(normal)s
Allow john and jack in oftc server to talk with bot
  /execbot add -server oftc john jack
''' % {'bold':weechat.color('bold'), 'normal':weechat.color('-bold')}

execbot_config_file      = None
execbot_config_section   = {}
execbot_allows           = {}

def execbot_config_init():
    '''Init configuration file'''
    global execbot_config_file
    execbot_config_file = weechat.config_new('execbot', 'execbot_config_reload_cb', '')
    if not execbot_config_file:
        return

    execbot_config_section['allows'] = weechat.config_new_section(
        execbot_config_file, 'allows', 0, 0, 'execbot_config_allows_read_cb', '',
        'execbot_config_allows_write_cb', '', '', '', '', '', '', '')
    if not execbot_config_section['allows']:
        weechat.config_free(execbot_config_file)

def execbot_config_reload_cb(data, config_file):
    '''Handle a reload of the configuration file.'''
    global execbot_allows
    execbot_allows   = {}
    return weechat.config_reload(config_file)

def execbot_config_allows_read_cb(data, config_file, section_name, option_name, value):
    '''Read elements of the allows section from the configuration file.'''
    execbot_allows[option_name.lower()] = value
    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

def execbot_config_allows_write_cb(data, config_file, section_name):
    '''Write infomation to the allows section of the configuration file.'''
    weechat.config_write_line(config_file, section_name, '')
    for username, right in sorted(list(execbot_allows.items())):
        weechat.config_write_line(config_file, username.lower(), right)
    return weechat.WEECHAT_RC_OK

def execbot_config_read():
    ''' Read Execbot configuration file (execbot.conf).'''
    return weechat.config_read(execbot_config_file)

def execbot_config_write():
    ''' Write Execbot configuration file (execbot.conf) to disk.'''
    return weechat.config_write(execbot_config_file)

def execbot_command_list():
    '''List server.nicknames are allowed.'''
    nicknames = '\n'.join([' %s' % x for x in execbot_allows.keys()])
    # for nickname,_ in sorted(list(execbot_allows.items())):
    weechat.prnt(weechat.current_buffer(), 'Nicknames are allowed:\n' +nicknames)
    return weechat.WEECHAT_RC_OK

def execbot_command_add(server,nicknames):
    '''Add nicknames.'''
    for x in nicknames:
        execbot_allows['%s.%s'%(server,x.lower())] = 'allow'
        weechat.prnt(weechat.current_buffer(),'Add permission for %s' % '%s.%s'%(server,x.lower()))
    return weechat.WEECHAT_RC_OK

def execbot_command_del(server,nicknames):
    '''Remove nicknames.'''
    for x in nicknames:
        try:
            del execbot_allows['%s.%s'%(server,x.lower())]
            weechat.prnt(weechat.current_buffer(),'Deleted permission of %s' % '%s.%s'%(server,x.lower()))
        except KeyError:
            weechat.prnt(weechat.current_buffer(),'No existing %s.%s'%(server,x.lower()))
    return weechat.WEECHAT_RC_OK

def execbot_command(data, buffer, args):
    '''Hook to handle the /execbot weechat command.'''
    argv = args.split()

    # list
    if not argv or argv == ['list']:
        return execbot_command_list()

    # check if a server was set
    if (len(argv) > 2 and argv[1] == '-server'):
        server = argv[2]
        del argv[1:3]
        args = (args.split(' ', 2)+[''])[2]
    else:
        server = weechat.buffer_get_string(buffer, 'localvar_server')
    if not server:
        weechat.prnt(weechat.current_buffer(), 'Required -server option')
        return weechat.WEECHAT_RC_ERROR

    # add
    if argv[:1] == ['add']:
        if len(argv) < 2:
            return weechat.WEECHAT_RC_ERROR
        return execbot_command_add(server,argv[1:])

    # del
    if argv[:1] == ['del']:
        if len(argv) < 2:
            return weechat.WEECHAT_RC_ERROR
        return execbot_command_del(server,argv[1:])

    execbot_error('Unknown command. Try  /help execbot', buffer)
    return weechat.WEECHAT_RC_OK

def execbot_process(buffer, command, return_code, out, err):
    '''Execute the command and return to buffer.'''
    message = "%s ... | $? = %d\n" % (command.split()[0], return_code)
    if out != "":
        message += out
    if err != "":
        message += err

    weechat.command(buffer, message)
    return weechat.WEECHAT_RC_OK

def execbot_hook_signal(data, signal, signal_data):
    server = signal.split(",")[0]
    info = weechat.info_get_hashtable("irc_message_parse", { "message": signal_data })
    username = '.'.join([server,info['nick']])

    # Check the permission
    allowed = execbot_allows.get(username.lower())
    if not allowed:
        return weechat.WEECHAT_RC_OK
    # Prevent public channel
    if info['channel'].startswith('#'):
        return weechat.WEECHAT_RC_OK

    # buffer output
    buffer = weechat.buffer_search("irc", username)
    # command
    _, command = info['arguments'].split(':', 1)

    # timeout = 5 mins
    weechat.hook_process(command, 300000, "execbot_process", buffer)

    return weechat.WEECHAT_RC_OK

def execbot_unload_script():
    execbot_config_write()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR,
                                               SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, 'execbot_unload_script','UTF-8'):
    execbot_config_init()
    execbot_config_read()
    weechat.hook_command('execbot', 'Commands to manage Execbot options and execute Execbot commands',
                         '',
                         SCRIPT_HELP_TEXT,
                         'list %- || add -server %(irc_servers) %(nicks) %-'
                         '|| del -server %(irc_servers) %(nicks) %-',
                         'execbot_command', '')
    weechat.hook_signal("*,irc_in2_privmsg", "execbot_hook_signal", "")
