# -*- coding: utf-8 -*-
###
# Copyright (c) 2012 by epegzz <epegzz@gmail.com>
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
###

###
# TWMN notifications for WeeChat
#
#   Settings:
#   * plugins.var.python.twmn_notify.font:
#   Font to use.
#
#   * plugins.var.python.twmn_notify.fontsize:
#   Fontsize to use.
#
#   * plugins.var.python.twmn_notify.height:
#   Height of the notification dialog.
#
#   * plugins.var.python.twmn_notify.position:
#   Position of the notification dialog.
#
#   * plugins.var.python.twmn_notify.normal_fg:
#   Color for normal messages.
#
#   * plugins.var.python.twmn_notify.normal_bg:
#   Background color for normal messages.
#
#   * plugins.var.python.twmn_notify.normal_timeout:
#   How long to display notification (in seconds) for normal messages.
#
#   * plugins.var.python.twmn_notify.private_fg:
#   Color for private messages.
#
#   * plugins.var.python.twmn_notify.private_bg:
#   Background color for private messages.
#
#   * plugins.var.python.twmn_notify.private_timeout:
#   How long to display notification (in seconds) for private messages.
#
#   * plugins.var.python.twmn_notify.hilite_fg:
#   Color for hilite messages.
#
#   * plugins.var.python.twmn_notify.hilite_bg:
#   Background color for hilite messages.
#
#   * plugins.var.python.twmn_notify.hilite_timeout:
#   How long to display notification (in seconds) for hilite messages.
#
#
#   History:
#     2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#       version 0.1.3: change hook_print callback argument type of
#                      displayed/highlight (WeeChat >= 1.0)
#     2012-11-16, Sébastien Helleu <flashcode@flashtux.org>:
#       version 0.1.2: remove invalid calls to config functions,
#                      escape message in command for hook_process (fix security issue)
#     2012-01-25
#       version 0.1.1: initial release
#
###

SCRIPT_NAME    = "twmn_notify"
SCRIPT_AUTHOR  = "epegzz <epegzz@gmail.com>"
SCRIPT_VERSION = "0.1.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Use twmn to display notifications"

### Default Settings ###
settings = {
'font'              : 'Dina',
'fontsize'          : '10',
'height'            : '16',
'position'          : 'top_right',
'normal_fg'         : '#CCCCCC',
'normal_bg'         : '#1C1C1C',
'normal_timeout'    : '5',
'private_fg'        : '#5FD700',
'private_bg'        : '#1C1C1C',
'private_timeout'   : '5',
'hilite_fg'         : '#D7005F',
'hilite_bg'         : '#1C1C1C',
'hilite_timeout'    : '-1',
}

import weechat, sys, pipes, shlex

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

weechat.hook_print("", "irc_privmsg", "", 1, "receive", "")

for opt, val in settings.items():
    if not weechat.config_is_set_plugin(opt):
        weechat.config_set_plugin(opt, val)


def config(key):
    value = weechat.config_get_plugin(key)
    if value is None:
        value = settings[key]
    return value

def ok(*args, **kwargs):
    return weechat.WEECHAT_RC_OK


def receive(data, buf, date, tags, disp, hilite, prefix, message):

    display = False

    ## notification levels
    ## 0 none
    ## 1 highlight
    ## 2 message
    ## 3 all
    notify = weechat.buffer_get_integer(buf, "notify")
    tags = tags.split(',')

    ## generate the list of nicks we are using on our irc servers
    nicks = []
    servers = weechat.infolist_get("irc_server", "", "")
    while weechat.infolist_next(servers):
        if weechat.infolist_integer(servers, 'is_connected') == 1:
            nicks.append(weechat.infolist_string(servers, 'nick'))
    weechat.infolist_free(servers)
    ## remove duplicates from nicks
    nicks = set(nicks)

    ## sometimes we don't want notifications at all
    ## we need to strip non-alpha chars from prefix, since
    ## otherwise we wont match @nickname for example
    if notify == 0 or filter(str.isalnum, prefix) in nicks:
        return ok()

    ## always display when notify set to all or message
    ## this means we lump irc_join under this notification level
    if notify in [2, 3]:
        display = True
    elif notify == 1 and (int(hilite) or 'notify_private' in tags):
        display = True

    if display:
        font = config('font')
        fontsize = config('fontsize')
        color = config('normal_fg')
        background = config('normal_bg')
        timeout = config('normal_timeout')

        prefix = prefix.replace('"','\\"')
        message = "%s" % message.replace('"','\\"')

        channel = weechat.buffer_get_string(buf, "short_name") or weechat.buffer_get_string(buf, "name").replace('"','\\"')
        title = "[%s] <i>%s</i>" % (channel, prefix)

        if 'notify_private' in tags:
            title = "<i>%s</i>" % prefix
            color = config('private_fg')
            background = config('private_bg')
            timeout = config('private_timeout')

        if int(hilite):
            color = config('hilite_fg')
            background = config('hilite_bg')
            timeout = config('hilite_timeout')

        message = "<b> %s</b> %s " % (title, message)

        if sys.version_info >= (3,3):
            message = shlex.quote(message)
        else:
            message = pipes.quote(message)

        args = dict\
            ( message = message
            , font = font
            , fontsize = fontsize
            , timeout = int(timeout)*1000
            , color = color
            , background = background
            , height = config('height')
            , position = config('position')
            )

        cmd = 'twmnc --aot '\
            + '-t "" '\
            + '--pos %(position)s '\
            + '-d %(timeout)s '\
            + '--fg "%(color)s" '\
            + '--bg "%(background)s" '\
            + '--content=%(message)s '\
            + '--fn "%(font)s" '\
            + '-s %(height)s '\
            + '--fs %(fontsize)s '

        weechat.hook_process(cmd % args, 10000, "ok", "")

    return ok()

