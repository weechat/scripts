# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Peter A. Shevtsov <pshevtsov@severusweb.ru>
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
# Set away status if slock is running
#
# History:
#
# 2011-10-14, Peter A. Shevtsov <pshevtsov@severusweb.ru>:
#     version 0.1: initial release
#

SCRIPT_NAME = "slock_away"
SCRIPT_AUTHOR = "Peter A. Shevtsov <pshevtsov@severusweb.ru>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Set away status if slock is running"

SCRIPT_COMMAND = "slock_away"

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: https://weechat.org/"
    import_ok = False

try:
    import subprocess
except ImportError:
    print "Missing package(s) for %s: %s" % (SCRIPT_NAME, message)
    import_ok = False

TIMER = None

settings = {
        'away_message': 'Away',
        'interval': '20',  # How often to check for inactivity (in seconds)
        'away': '0'
}


def set_back(overridable_messages):
    """Removes away status for servers
    where one of the overridable_messages is set"""
    if (weechat.config_get_plugin('away') == '0'):
        return  # No need to come back again
    serverlist = weechat.infolist_get('irc_server', '', '')
    if serverlist:
        buffers = []
        while weechat.infolist_next(serverlist):
            if (weechat.infolist_string(serverlist, 'away_message')
                    in overridable_messages):
                ptr = weechat.infolist_pointer(serverlist, 'buffer')
                if ptr:
                    buffers.append(ptr)
        weechat.infolist_free(serverlist)
        for buffer in buffers:
            weechat.command(buffer, "/away")
    weechat.config_set_plugin('away', '0')


def set_away(message, overridable_messages=[]):
    """Sets away status, but respectfully
    (so it doesn't change already set statuses"""
    if (weechat.config_get_plugin('away') == '1'):
        return  # No need to go away again
                # (this prevents some repeated messages)
    serverlist = weechat.infolist_get('irc_server', '', '')
    if serverlist:
        buffers = []
        while weechat.infolist_next(serverlist):
            if weechat.infolist_integer(serverlist, 'is_away') == 0:
                ptr = weechat.infolist_pointer(serverlist, 'buffer')
                if ptr:
                    buffers.append(ptr)
            elif (weechat.infolist_string(serverlist, 'away_message')
                    in overridable_messages):
                buffers.append(weechat.infolist_pointer(serverlist, 'buffer'))
        weechat.infolist_free(serverlist)
        for buffer in buffers:
            weechat.command(buffer, "/away %s" % message)
    weechat.config_set_plugin('away', '1')


def slock_away_cb(data, buffer, args):
    """Callback for /slock_away command"""
    response = {
            'msg': lambda status:
                        weechat.config_set_plugin('away_message', status)
    }
    if args:
        words = args.strip().partition(' ')
        if words[0] in response:
            response[words[0]](words[2])
        else:
            weechat.prnt('', "slock_away error: %s not a recognized command. "
                       "Try /help slock_away" % words[0])
    weechat.prnt('', "slock_away: away message: \"%s\"" %
                      weechat.config_get_plugin('away_message'))
    return weechat.WEECHAT_RC_OK


def auto_check(data, remaining_calls):
    """Callback from timer"""
    check()
    return weechat.WEECHAT_RC_OK


def check():
    """Check for existance of process and set away if it isn't there"""
    pidof = subprocess.Popen("pidof slock",
            shell=True, stdout=subprocess.PIPE)
    pidof.wait()
    if pidof.returncode == 0:
        set_away(weechat.config_get_plugin('away_message'), [])
    else:
        set_back([weechat.config_get_plugin('away_message')])


def check_timer():
    """Sets or unsets the timer
    based on whether or not the plugin is enabled"""
    global TIMER
    if TIMER:
        weechat.unhook(TIMER)
    TIMER = weechat.hook_timer(
            int(weechat.config_get_plugin('interval')) * 1000,
            0, 0, "auto_check", "")

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                  SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        for option, default_value in settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

        weechat.hook_command(SCRIPT_COMMAND,
                             SCRIPT_DESC,
                             "msg <status>",
                             "msg: set the away message\n",
                             "", "slock_away_cb", "")
        check_timer()
