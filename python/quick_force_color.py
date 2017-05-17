# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2017 by nils_2 <weechatter@arcor.de>
#
# quickly add/del/change entry in nick_color_force
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
# 2017-05-18: ticalc-travis (https://github.com/weechatter/weechat-scripts/pull/18)
#       0.6 : Clean up some redundant code
#           : Add nicks to irc.look.nick_color_force in sorted order for easier manual editing
#           : Display proper feedback on incorrect commands
#           : Fix inconsistencies in help syntax
#           : Don't retain nicks that have been manually removed from nick_color_force
#           : Provide feedback messages for successful operations
# 2016-04-17: nils_2,(freenode.#weechat)
#       0.5 : make script compatible with option weechat.look.nick_color_force (weechat >=1.5)
# 2013-01-25: nils_2,(freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
# 2012-07-08: obiwahn, (freenode)
#     0.3.1 : fix: list nick
#           : - show nick: color if it is in list
#           :   else tell color for nick is not set
# 2012-05-23: unferth, (freenode.#weechat)
#       0.3 : add: show current colors
# 2012-02-14: nils_2, (freenode.#weechat)
#       0.2 : fix: problem with foreground/background color
#           : add: show only a given nick
# 2012-02-01: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.4
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#

try:
    import weechat, re

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "quick_force_color"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.6"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "quickly add/del/change entry in nick_color_force"

# weechat standard colours.
DEFAULT_COLORS = {  0 : "darkgray", 1 : "red", 2 : "lightred", 3 : "green",
                    4 : "lightgreen", 5 : "brown", 6 : "yellow", 7 : "blue",
                    8 : "lightblue", 9 : "magenta", 10 : "lightmagenta", 11 : "cyan",
                   12 : "lightcyan", 13 : "white"}

colored_nicks = {}
nick_option_old = "irc.look.nick_color_force"
nick_option_new = "weechat.look.nick_color_force"
nick_option = ""
# ================================[ callback ]===============================
def print_usage(buffer):
    weechat.prnt(buffer, "Usage: /%s list [nick] | add nick color | del nick" % SCRIPT_NAME)

def nick_colors_cmd_cb(data, buffer, args):
    global colored_nicks

    if args == "":                                                                              # no args given. quit
        print_usage(buffer)
        return weechat.WEECHAT_RC_OK

    argv = args.strip().split(" ")
    if (len(argv) == 0) or (len(argv) >= 4):                                                    # maximum of 3 args!!
        print_usage(buffer)
        return weechat.WEECHAT_RC_OK

    bufpointer = weechat.window_get_pointer(buffer,'buffer')                                    # current buffer

    create_list()

    if argv[0].lower() == 'list':                                                               # list all nicks
        if len(colored_nicks) == 0:
            weechat.prnt(buffer,'%sno nicks in \"%s\"...' % (weechat.prefix("error"),nick_option))
        elif len(argv) == 2:
            if argv[1] in colored_nicks:
                color = colored_nicks[argv[1]]                                                  # get color from given nick
                weechat.prnt(buffer,"%s%s: %s" % (weechat.color(color),argv[1],color))
            else:
                weechat.prnt(buffer,"no color set for: %s" % (argv[1]))

        else:
            weechat.prnt(buffer,"List of nicks in : %s" % nick_option)
            for nick,color in list(colored_nicks.items()):
                weechat.prnt(buffer,"%s%s: %s" % (weechat.color(color),nick,color))

    elif (argv[0].lower() == 'add') and (len(argv) == 3):
        if argv[1] in colored_nicks:
            weechat.prnt(buffer, "Changing nick '%s' to color %s%s" % (argv[1], weechat.color(argv[2]), argv[2]))
        else:
            weechat.prnt(buffer, "Adding nick '%s' with color %s%s" % (argv[1], weechat.color(argv[2]), argv[2]))
        colored_nicks[argv[1]] = argv[2]
        save_new_force_nicks()

    elif (argv[0].lower() == 'del') and (len(argv) == 2):
        if argv[1] in colored_nicks:                                                            # search if nick exists
            del colored_nicks[argv[1]]
            save_new_force_nicks()
            weechat.prnt(buffer, "Removed nick '%s'" % argv[1])
        else:
            weechat.prnt(buffer, "Nick '%s' not found in nick_color_force" % argv[1])
    else:
        print_usage(buffer)

    return weechat.WEECHAT_RC_OK

def save_new_force_nicks():
    global colored_nicks
    new_nick_color_force = ';'.join([ ':'.join(item) for item in sorted(colored_nicks.items())])
    config_pnt = weechat.config_get(nick_option)
    weechat.config_option_set(config_pnt,new_nick_color_force,1)

def nick_colors_completion_cb(data, completion_item, buffer, completion):
#    for id,color in DEFAULT_COLORS.items():
    for id,color in list(DEFAULT_COLORS.items()):
        weechat.hook_completion_list_add(completion, color, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def force_nick_colors_completion_cb(data, completion_item, buffer, completion):
    create_list()
#    for nick,color in colored_nicks.items():
    for nick,color in list(colored_nicks.items()):
        weechat.hook_completion_list_add(completion, nick, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def create_list():
    global nick_color_force,colored_nicks
#        colored_nicks = dict([elem.split(':') for elem in nick_color_force.split(';')])
    colored_nicks = {}
    nick_color_force = weechat.config_string(weechat.config_get(nick_option))                   # get list
    if nick_color_force != '':
        nick_color_force = nick_color_force.strip(';')                                          # remove ';' at beginning and end of string
        for elem in nick_color_force.split(';'):                                                # split nick1:color;nick2:color
            counter = elem.count(':')
            if counter == 1:
                nick,colors = elem.split(':')                                                   # nick1:color_fg,color_bg
                colored_nicks.setdefault(nick,colors)
            elif counter == 2:
                nick,color_fg,color_bg = elem.split(':')                                        # nick1:color_fg:color_bg
                colored_nicks.setdefault(nick,color_fg+':'+color_bg)

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0
        if int(version) >= 0x00030400:
            weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
            'add <nick> <color> || del <nick> <color> || list [<nick>]',
            'add <nick> <color>: add a nick with its color to nick_color_force\n'
            'del <nick>        : delete given nick with its color from nick_color_force\n'
            'list [<nick>]     : list all forced nicks with its assigned color or optional from one nick\n\n'
            'Examples:\n'
            ' add nick nils_2 with color red:\n'
            '  /' + SCRIPT_NAME + ' add nils_2 red\n'
            ' recolor nick nils_2 with foreground color yellow and background color blue:\n'
            '  /' + SCRIPT_NAME + ' add nils_2 yellow:blue\n'
            ' delete nick nils_2:\n'
            '  /' + SCRIPT_NAME + ' del nils_2\n',
            'add %(nick) %(plugin_nick_colors) %-||'
            'del %(plugin_force_nick) %-||'
            'list %(plugin_force_nick) %-',
            'nick_colors_cmd_cb', '')
            nick_option = nick_option_old
            if int(version) >= 0x01050000:
                nick_option = nick_option_new
            weechat.hook_completion('plugin_nick_colors', 'nick_colors_completion', 'nick_colors_completion_cb', '')
            weechat.hook_completion('plugin_force_nick', 'force_nick_colors_completion', 'force_nick_colors_completion_cb', '')
        else:
            weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.4 or higher"))
