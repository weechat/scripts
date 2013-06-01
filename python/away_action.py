# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by xt <xt@bash.no>
# Parts from inotify.py by Elián Hanisch <lambdae2@gmail.com>
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
#   * plugins.var.python.away_action.ignore_channel:
#   Comma separated list of patterns for define ignores. Notifications from channels where its name
#   matches any of these patterns will be ignored.
#   Wildcards '*', '?' and char groups [..] can be used.
#   An ignore exception can be added by prefixing '!' in the pattern.
#
#       Example:
#       *ubuntu*,!#ubuntu-offtopic
#       any notifications from a 'ubuntu' channel will be ignored, except from #ubuntu-offtopic
#
#   * plugins.var.python.away_action.ignore_nick:
#   Same as ignore_channel, but for nicknames.
#
#       Example:
#       troll,b[0o]t
#       will ignore notifications from troll, bot and b0t
#
#   * plugins.var.python.away_action.ignore_text:
#   Same as ignore_channel, but for the contents of the message.

###
#
#
#   History:
#   2013-05-18:
#   version 0.4: add include_channel option - contributed by Atluxity
#   2010-11-04:
#   version 0.3: minor cleanups, fix import, add hook info
#   2010-03-17:
#   version 0.2: add force on option
#   2010-03-11
#   version 0.1: initial release
#
###

SCRIPT_NAME    = "away_action"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Run command on highlight and privmsg when away"

### Default Settings ###
settings = {
'ignore_channel' : '',
'ignore_nick'    : '',
'ignore_text'    : '',
'command'        : '/mute msg ', # Command to be ran, nick and message will be inserted at the end
'force_enabled'  : 'off',
'include_channel': 'off', # Option to include channel in insert after command.
}

ignore_nick, ignore_text, ignore_channel = (), (), ()
last_buffer = ''
try:
    import weechat
    w = weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
    from fnmatch import fnmatch
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

class Ignores(object):
    def __init__(self, ignore_type):
        self.ignore_type = ignore_type
        self.ignores = []
        self.exceptions = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(',')
        ignores = [ s.lower() for s in ignores if s ]
        self.ignores = [ s for s in ignores if s[0] != '!' ]
        self.exceptions = [ s[1:] for s in ignores if s[0] == '!' ]

    def __contains__(self, s):
        s = s.lower()
        for p in self.ignores:
            if fnmatch(s, p):
                for e in self.exceptions:
                    if fnmatch(s, e):
                        return False
                return True
        return False

config_string = lambda s : weechat.config_string(weechat.config_get(s))
def get_nick(s):
    """Strip nickmodes and prefix, suffix."""
    if not s: return ''
    # prefix and suffix
    prefix = config_string('irc.look.nick_prefix')
    suffix = config_string('irc.look.nick_suffix')
    if s[0] == prefix:
        s = s[1:]
    if s[-1] == suffix:
        s = s[:-1]
    # nick mode
    modes = '~+@!%'
    s = s.lstrip(modes)
    return s

def away_cb(data, buffer, time, tags, display, hilight, prefix, msg):

    global ignore_nick, ignore_text, ignore_channel, last_buffer

    # Check if we are either away or force_enabled is on
    if not w.buffer_get_string(buffer, 'localvar_away') and \
       not w.config_get_plugin('force_enabled') == 'on':
        return WEECHAT_RC_OK

    if (hilight == '1' or 'notify_private' in tags) and display == '1':
        channel = weechat.buffer_get_string(buffer, 'short_name')
        prefix = get_nick(prefix)
        if prefix not in ignore_nick \
                and channel not in ignore_channel \
                and msg not in ignore_text:
            last_buffer = w.buffer_get_string(buffer, 'plugin') + '.' + \
                          w.buffer_get_string(buffer, 'name')
            command = weechat.config_get_plugin('command')
            if not command.startswith('/'):
                w.prnt('', '%s: Error: %s' %(SCRIPT_NAME, 'command must start with /'))
                return WEECHAT_RC_OK

            if 'channel' in locals() and \
                w.config_get_plugin('include_channel') == 'on':
                w.command('', '%s @%s <%s> %s' %(command, channel, prefix, msg))
            else:
                w.command('', '%s <%s> %s' %(command, prefix, msg))
    return WEECHAT_RC_OK

def ignore_update(*args):
    ignore_channel._get_ignores()
    ignore_nick._get_ignores()
    ignore_text._get_ignores()
    return WEECHAT_RC_OK


def info_hook_cb(data, info_name, arguments):
    global last_buffer
    return last_buffer


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):


    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    ignore_channel = Ignores('ignore_channel')
    ignore_nick = Ignores('ignore_nick')
    ignore_text = Ignores('ignore_text')
    weechat.hook_config('plugins.var.python.%s.ignore_*' %SCRIPT_NAME, 'ignore_update', '')

    weechat.hook_print('', '', '', 1, 'away_cb', '')
    w.hook_info('%s_buffer' %SCRIPT_NAME, '', '', 'info_hook_cb', '')


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
