# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by xt <xt@bash.no>
# License: GPL3
#
#
#   History:
#   2010-11-08
#   version 0.1: initial release
#
###

SCRIPT_NAME    = "tailer"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Tail any number of files and run any command with line appended"

### Default Settings ###
settings = {
        'entries': '/var/log/logfile=/mute msg -server freenode #flood', # filename and command
        'interval': '10', # in seconds
}


entries = {}
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

import os

def tailer_conf_update(*args):
    global hook
    interval = int(w.config_get_plugin('interval'))
    # Don't hook default setting
    if not w.config_get_plugin('entries') == settings['entries']:
        if hook:
            w.unhook(hook)
        hook = w.hook_timer(interval*1000, 0, 0, 'tailer_cb', '')
    return WEECHAT_RC_OK


def tailer_cb(*args):
    for entry in w.config_get_plugin('entries').split(','):
        if not entry: continue
        filename, command = entry.split('=')
        if not filename in entries:
            #Find the size of the file and move to the end
            st_results = os.stat(filename)
            st_size = st_results[6]
            entries[filename] = st_size

        position = entries[filename]

        t_file = file(filename,'r')
        t_file.seek(position)
        lines = t_file.readlines()
        if not command.startswith('/'):
            w.prnt('', '%s: Error: %s' %(SCRIPT_NAME, 'command must start with /'))
            return WEECHAT_RC_OK
        for line in lines:
            if line:
                w.command('', '%s %s' %(command, line))
        # Update new position in file
        entries[filename] = t_file.tell()
    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):


    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_config('plugins.var.python.%s' %SCRIPT_NAME, 'tailer_conf_update', '')
    tailer_conf_update() # To init hook


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
