# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by xt <xt@bash.no>
# License: GPL3
#
#
#
#   Usage scenarios:
#
#   * Remote control weechat from a jabber account (from phone for example)
#       Requires you to send commands starting with a /
#   * Reply to messages sent via away_action
#       Requires away_action.py installed, will send input to the last buffer away_action recieved a
#       message from
#       
#
#   History:
#   2010-11-08:
#   version 0.2: check that message is from remote side
#   2010-11-04
#   version 0.1: initial release
#
###

SCRIPT_NAME    = "msg_command"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Run chat recieved in a buffer as commands"

### Default Settings ###
settings = {
        'buffer': 'jabber.gtalk.otheraccount@otherserver.com', # Buffer to listen for commands
}

buffer_hooked_pointer = ''
hook = ''

try:
    import weechat
    w = weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

def msg_command_cb(data, buffer, time, tags, display, hilight, prefix, msg):

    if msg.startswith('/'):
        w.command('', msg)
    else:
        buffer_name = w.info_get('away_action_buffer', '')
        plugin = buffer_name.split('.')[0]
        buffer_name = '.'.join(buffer_name.split('.')[1:])
        buffer = w.buffer_search(plugin, buffer_name)
        if buffer:
            # Check if message is from remote and not a local
            if prefix in w.config_get_plugin('buffer'):
                w.command(buffer, msg)
    return WEECHAT_RC_OK

def hook_it(buffer_pointer):
    ''' Check if we need new hook, remove previous hook if exists '''

    global buffer_hooked_pointer, hook
    if buffer_pointer != buffer_hooked_pointer:
        w.unhook(hook)
        buffer_hooked_pointer = buffer_pointer
        hook = w.hook_print(buffer_pointer, '', '', 1, 'msg_command_cb', '')

def msg_command_conf_update(*args):
    if w.config_get_plugin('buffer'):
        buffer = w.buffer_search('', w.config_get_plugin('buffer'))
        hook_it(buffer)
    return WEECHAT_RC_OK


def msg_command_buffer_opened_cb(data, signal, signal_data):

    buffer = signal_data
    buffer_name = w.buffer_get_string(buffer, "name")
    if buffer_name == w.config_get_plugin('buffer'):
        hook_it(buffer)

    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):


    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_signal('buffer_opened', 'msg_command_buffer_opened_cb', '')
    weechat.hook_config('plugins.var.python.%s' %SCRIPT_NAME, 'msg_command_conf_update', '')
    msg_command_conf_update() # To init hook


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
