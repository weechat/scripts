#!/usr/bin/env python
# coding: utf-8
#
# Copyright (c) 2012 by nesthib <nesthib@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# This script allows to create a nick list from pattern to highlight
# a bunch of nick in a channel
#
# 2012-01-15: nesthib <nesthib@gmail.com>
#        0.1: initial release

try:
    import weechat as w
except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

import argparse, re

name = "hl_nicks"
author = "nesthib <nesthib@gmail.com>"
version = "0.1.1"
license = "GPL"
description = "Generates a list of nicks in input by selecting nicks using flags and patterns"
shutdown_function = ""
charset = ""

w.register(name, author, version, license, description, shutdown_function, charset)

buffer = w.current_buffer()

settings = {
        'ignore_list': 'ChanServ,.*bot.*',
        'ignore_self': 'on',
        'separator'  : ', ',
        'short_regex': 'on',
        'sort_nicks' : 'on',
        'ignore_case': 'on',
        }

for opt, val in settings.iteritems():
    if not w.config_is_set_plugin(opt):
        w.config_set_plugin(opt, val)

def get_nicklist(server, channel):
    global options

    regex_flags = 0
    if options['ignore_case']:
        regex_flags = re.IGNORECASE
    ignore_list = w.config_get_plugin('ignore_list')
    if ignore_list == '':
        ignore_match = lambda x: False
    else:
        ignore_match = re.compile('(%s)$' % ignore_list.replace(',', '|'), regex_flags).match

    server = w.buffer_get_string(w.current_buffer(), 'localvar_server')
    my_nick = w.info_get('irc_nick', server)
    nicklist = {}
    infolist_nicklist = w.infolist_get('nicklist', w.current_buffer(), '')
    while w.infolist_next(infolist_nicklist):
        nick = w.infolist_string(infolist_nicklist, 'name')
        prefix = w.infolist_string(infolist_nicklist, 'prefix')
        nick_type = w.infolist_string(infolist_nicklist, 'type')
        if nick_type != 'nick' or (options['ignore_self'] and nick == my_nick) or ignore_match(nick):
            pass
        else:
            if not nicklist.has_key(prefix):
                nicklist[prefix]=[]
            nicklist[prefix].append(nick)
    w.infolist_free(infolist_nicklist)
    return nicklist

def my_hl_cb(data, buffer, args):

    flags_relations = { '~' : 'q',
                        '&' : 'a',
                        '@' : 'o',
                        '%' : 'h',
                        '+' : 'v',
                        ' ' : 'n' }

    parser = argparse.ArgumentParser(prefix_chars='-+', add_help=False)
    for flag in flags_relations.values():
        parser.add_argument('+%s' % flag, action='store_const', const=True)
        parser.add_argument('-%s' % flag, action='store_const', const=False)

    try:
        (opts, args) = parser.parse_known_args(args.split())
    except SystemExit:
        w.prnt('', 'Error: in "%s", invalid options. See /help %s for authorized options.' % (args, name))
        return w.WEECHAT_RC_ERROR

    opts = vars(opts)
    used_opts = list(set(opts.values()))

    channel = w.buffer_get_string(buffer, 'localvar_channel')
    server = w.buffer_get_string(buffer, 'localvar_server')

    nickgroups = get_nicklist(server, channel)
    nicks = []
    invert_match = False

    if args:
        regex = args[0]
        if regex.startswith('!'):
            invert_match = True
            regex = regex[1:]
        regex_flags = 0
        if options['ignore_case']:
            regex_flags = re.IGNORECASE
        try:
            if options['short_regex']:
                regex = re.compile('.*%s.*' % regex, regex_flags)
            else:
                regex = re.compile(regex, regex_flags)
        except:
            w.prnt('', 'Error with argument "%s" invalid regexp' % args[0])
            regex = None
            invert_match = False

    for flag in reversed(sorted(nickgroups)):
        if not flags_relations.has_key(flag):
            w.prnt('', 'Error: flag "%s" is not supported' % flag)
            continue
        if used_opts == [None]:
            pass
        elif True in used_opts and False in used_opts:
            w.prnt('', 'Error: + and - options are not compatible')
            return w.WEECHAT_RC_OK
        elif True in used_opts:
            if opts[flags_relations[flag]]:
                pass
            else:
                continue
        elif False in used_opts and opts[flags_relations[flag]] ==  False:
            continue
        for nick in nickgroups[flag]:
            if not args or (regex and (bool(regex.match(nick)) ^ invert_match)):
                nicks.append(nick)

    if options['sort_nicks']:
        if options['ignore_case']:
            nicks.sort(key=str.lower)
        else:
            nicks.sort()
    separator = w.config_get_plugin('separator')
    trailing_char = w.config_string(w.config_get('weechat.completion.nick_completer'))
    input_text = separator.join(nicks)
    if input_text:
        input_text = input_text+trailing_char
    w.buffer_set(w.current_buffer(), 'input', input_text)
    w.command ("", "/input move_end_of_line")

    return w.WEECHAT_RC_OK

invertdict = lambda d: dict(zip(d.itervalues(), d.keys()))
booleans = {'on': True, 'off': False}
boolean_options = ['ignore_self', 'short_regex', 'sort_nicks', 'ignore_case']

options = {}
for option in settings.keys():
    if option in boolean_options :
        options[option] = booleans[w.config_get_plugin(option)]
    else:
        options[option] = w.config_get_plugin(option)

def my_config_cb(data, option, value):
    global options

    for boolean_option in boolean_options :
        if option.endswith(boolean_option):
            if value in booleans.keys():
                options[boolean_option] = booleans[w.config_get_plugin(boolean_option)]
            else:
                w.prnt('', 'Error: "%s" is not a boolean, please use "on" or "off"' % w.config_get_plugin(boolean_option))
                w.config_set_plugin(boolean_option, invertdict(booleans)[options[boolean_option]])

    return w.WEECHAT_RC_OK

for option in settings.keys():
    w.hook_config("plugins.var.python.%s.%s" % (name, option), "my_config_cb", "")

w.hook_command("hl", description, "",
"""    usage: /hl [+/-ovn] [regex]

        +o, +v, +n  : add opped, voiced, normal nicks to highlighted nicks
        -o, -v, -n  : remove opped, voiced, normal nicks from highlighted nicks
        regex       : select nicks based on regex

        alternate flags owner (q), admin (a) and halfop (h) can be used on networks supporting them

        EXAMPLES
        /hl +ov     : highlight opped and voices users
        /hl -o      : highlight everyone except opped users
        /hl ^n      : highlight nicks starting with "n"
        /hl !bot    : do not highlight nicks comprising "bot"

        OPTIONS
        ignore_list : comma separated list of nicks to ignore
        ignore_self : boolean option to trigger addition of own nick to list
        separator   : string used as separator for list of nicks
        short_regex : boolean option to replace regex by .*regex.*
        sort_nicks  : boolean option to sort nicks alphabetically (otherwise by group)
        ignore_case : boolean option to perfom case insensitive nick matches
""", "", "my_hl_cb", "")

