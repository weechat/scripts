# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 by nils_2 <weechatter@arcor.de>
#
# for easy toggling current buffer logging.
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
# 2019-06-24: nils_2, (freenode.#weechat)
#       0.1 : initial version
#
# requires: WeeChat version 1.0
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re

except Exception:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://www.weechat.org/')
    quit()

SCRIPT_NAME     = 'log'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.1'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'for easy toggling current buffer logging'

# eval_expression():  to match ${color:nn} tags
regex_color=re.compile('\$\{color:([^\{\}]+)\}')

# ==========================[ eval_expression() ]========================
def substitute_colors(text,window):
    global version
    if int(version) >= 0x00040200:
        buffer_ptr = weechat.window_get_pointer(window,"buffer")
        return weechat.string_eval_expression(text, {"window": window, "buffer": buffer_ptr}, {}, {})
    # substitute colors in output
    return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

# ============================[ subroutines ]============================
def log_cmd_cb(data, buffer, args):
    argv = args.strip().split(' ')

    log_level = infolist_log_buffer(buffer)

    if args == "" or (argv[0].lower() == 'show'):
        # no args given. display log level of current buffer
        weechat.prnt(buffer,'log level: %s' % log_level)
        return weechat.WEECHAT_RC_OK

    if (argv[0].lower() == 'enable') or (argv[0].lower() == 'on'):
        if log_level != 'disabled':
            return weechat.WEECHAT_RC_OK    # buffer already logging!
        else:
            enable_check(log_level,buffer)
        return weechat.WEECHAT_RC_OK

    if (argv[0].lower() == 'disable') or (argv[0].lower() == 'off'):
        if log_level == 'disabled':
            return weechat.WEECHAT_RC_OK    # buffer already disabled!
        else:
            disable_check(log_level,buffer)
        return weechat.WEECHAT_RC_OK

    if (argv[0].lower() == 'toggle'):
        if log_level == 'disabled':
            enable_check(log_level,buffer)
        else:
            disable_check(log_level,buffer)
        return weechat.WEECHAT_RC_OK

    return weechat.WEECHAT_RC_OK

# ===============================[ logger() ]=============================
def enable_check(log_level,buffer):
    log_level = buffer_get_string_log_level(buffer)
    if log_level:
        if not str(log_level).isnumeric() or (int(log_level) < 0) or (int(log_level) > 9):
            log_level = 9 # invalid log level, set default
        weechat.command(buffer,'/logger set %s' % log_level)
        buffer_del_log_level(buffer)
    else:   # no logging and no localvar.
        weechat.command(buffer,'/logger set 9')
    return weechat.WEECHAT_RC_OK

def disable_check(log_level,buffer):
    buffer_set_string_log_level(buffer,log_level)   # store old log level in localvar!
    weechat.command(buffer,'/logger disable')
    return weechat.WEECHAT_RC_OK

# =============================[ localvars() ]============================
def buffer_get_string_log_level(buffer):
    return weechat.buffer_get_string(buffer,'localvar_log_level')

def buffer_set_string_log_level(buffer,log_level):
    weechat.buffer_set(buffer, 'localvar_set_log_level', '%s' % log_level)
    return weechat.WEECHAT_RC_OK

def buffer_del_log_level(buffer):
    weechat.command(buffer,'/buffer set localvar_del_log_level')
    return weechat.WEECHAT_RC_OK

# =============================[ infolist() ]============================
def infolist_log_buffer(ptr_buffer):
    log_level = None
    infolist = weechat.infolist_get('logger_buffer','','')
    while weechat.infolist_next(infolist):
        bpointer = weechat.infolist_pointer(infolist, 'buffer')
        if ptr_buffer == bpointer:
            log_enabled = weechat.infolist_integer(infolist, 'log_enabled')
            log_level = weechat.infolist_integer(infolist, 'log_level')

    weechat.infolist_free(infolist)                  # free infolist()
    if not log_level:
        return 'disabled'
    else:
        return log_level
# ================================[ main ]===============================
if __name__ == '__main__':
    global version
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0

        # get weechat version (1.0) and store it
        if int(version) >= 0x01000000:

            weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
                             'enable|on||'
                             'disable|off||'
                             'toggle||'
                             'show',
                             '  enable/on: enable logging on current buffer, with default log-level (note: log-level from localvar will be used, if possible)\n'
                             'disable/off: disable logging on current buffer (note: log-level is stored in localvar)\n'
                             '     toggle: will toggle logging on current buffer\n'
                             '       show: will print current log-level to buffer (default)\n'
                             '\n'
                             'Examples:\n'
                             '  /log toggle',
                             'enable||'
                             'disable||'
                             'on||'
                             'off||'
                             'toggle||'
                             'show',
                             'log_cmd_cb', '')

        else:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 1.0 or higher'))
            weechat.command('','/wait 1ms /python unload %s' % SCRIPT_NAME)
