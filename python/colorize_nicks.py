# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by xt <xt@bash.no>
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

# This script colors nicks in IRC channels in the actual message
# not just in the prefix section.
#
#
# History:
# 2013-01-29, nils_2
#   version 14: make script compatible with Python 3.x
# 2012-10-19, ldvx
#   version 13: Iterate over every word to prevent incorrect colorization of
#               nicks. Added option greedy_matching.
# 2012-04-28, ldvx
#   version 12: added ignore_tags to avoid colorizing nicks if tags are present
# 2012-01-14, nesthib
#   version 11: input_text_display hook and modifier to colorize nicks in input bar
# 2010-12-22, xt
#   version 10: hook config option for updating blacklist
# 2010-12-20, xt
#   version 0.9: hook new config option for weechat 0.3.4
# 2010-11-01, nils_2
#   version 0.8: hook_modifier() added to communicate with rainbow_text
# 2010-10-01, xt
#   version 0.7: changes to support non-irc-plugins
# 2010-07-29, xt
#   version 0.6: compile regexp as per patch from Chris quigybo@hotmail.com
# 2010-07-19, xt
#   version 0.5: fix bug with incorrect coloring of own nick
# 2010-06-02, xt
#   version 0.4: update to reflect API changes
# 2010-03-26, xt
#   version 0.3: fix error with exception
# 2010-03-24, xt
#   version 0.2: use ignore_channels when populating to increase performance.
# 2010-02-03, xt
#   version 0.1: initial (based on ruby script by dominikh)
#
# Known issues: nicks will not get colorized if they begin with a character
# such as ~ (which some irc networks do happen to accept)

import weechat
import re
w = weechat

SCRIPT_NAME    = "colorize_nicks"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "14"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "Use the weechat nick colors in the chat area"

settings = {
    "blacklist_channels"        : '',     # comma separated list of channels (use short_name)
    "blacklist_nicks"           : 'so,root',  # comma separated list of nicks
    "min_nick_length"           : '2',    # length
    "colorize_input"            : 'off',  # boolean
    "ignore_tags"               : '', # comma separated list of tags to ignore. I.e. irc_join,irc_part,irc_quit
    "greedy_matching"           : 'on',  # if off, then let's use lazy matching instead
}


VALID_NICK = r'([@~&!%+])?([-a-zA-Z0-9\[\]\\`_^\{|\}]+)'
valid_nick_re = re.compile(VALID_NICK)
PREFIX_COLORS = {
        '@' : 'nicklist_prefix1',
        '~' : 'nicklist_prefix1',
        '&' : 'nicklist_prefix1',
        '!' : 'nicklist_prefix1',
        '%' : 'nicklist_prefix2',
        '+' : 'nicklist_prefix3',
}
ignore_channels = []
ignore_nicks = []

# Dict with every nick on every channel with its color as lookup value
colored_nicks = {}

def colorize_cb(data, modifier, modifier_data, line):
    ''' Callback that does the colorizing, and returns new line if changed '''

    global ignore_nicks, ignore_channels, colored_nicks

    full_name = modifier_data.split(';')[1]
    server = full_name.split('.')[0]
    channel = '.'.join(full_name.split('.')[1:])

    buffer = w.buffer_search('', full_name)
    # Check if buffer has colorized nicks
    if not buffer in colored_nicks:
        return line

    if channel in ignore_channels:
        return line

    try:
        min_length = int(w.config_get_plugin('min_nick_length'))
    except ValueError:
        w.prnt('', '%sError with option min_nick_length, should be a integer' % weechat.prefix('error'))
        w.config_set_plugin('min_nick_length', settings['min_nick_length'])

    reset = w.color('reset')

    # Don't colorize if the ignored tag is present in message
    tags_line = modifier_data.rsplit(';')
    if len(tags_line) >= 3:
        tags_line = tags_line[2].split(',')
        for i in w.config_get_plugin('ignore_tags').split(','):
            if i in tags_line:
                return line

    for words in valid_nick_re.findall(line):
        prefix, nick = words[0], words[1]
        # Check that nick is not ignored and longer than minimum length
        if len(nick) < min_length or nick in ignore_nicks:
            continue
        # Check that nick is in the dictionary colored_nicks
        if nick in colored_nicks[buffer]:
            nick_color = colored_nicks[buffer][nick]

            # Let's use greedy matching. Will check against every word in a line.
            if w.config_get_plugin('greedy_matching') == "on":
                for word in line.split():
                   if nick in word:
                       # Is there a nick that contains nick and has a greater lenght?
                       # If so let's save that nick into var biggest_nick
                       biggest_nick = ""
                       for i in colored_nicks[buffer]:
                           if nick in i and nick != i and len(i) > len(nick):
                               if i in word:
                                   # If a nick with greater len is found, and that word
                                   # also happens to be in word, then let's save this nick
                                   biggest_nick = i
                       # If there's a nick with greater len, then let's skip this
                       # As we will have the chance to colorize when biggest_nick
                       # iterates being nick.
                       if len(biggest_nick) > 0 and biggest_nick in word:
                           pass
                       elif len(word) < len(biggest_nick) or len(biggest_nick) == 0:
                           new_word = word.replace(nick, '%s%s%s' %(nick_color, nick, reset))
                           line = line.replace(word, new_word)
            # Let's use lazy matching for nick
            elif w.config_get_plugin('greedy_matching') == "off":
                if nick in colored_nicks[buffer]:
                    nick_color = colored_nicks[buffer][nick]
                    # The two .? are in case somebody writes "nick:", "nick,", etc
                    # to address somebody
                    regex = r"(\A|\s).?(%s).?(\Z|\s)" % re.escape(nick)
                    match = re.search(regex, line)
                    if str(type(match)) == "<type '_sre.SRE_Match'>":
                        new_line = line[:match.start(2)] + nick_color+nick+reset + line[match.end(2):]
                        line = new_line
    return line

def colorize_input_cb(data, modifier, modifier_data, line):
    ''' Callback that does the colorizing in input '''

    global ignore_nicks, ignore_channels, colored_nicks

    try:
        min_length = int(w.config_get_plugin('min_nick_length'))
    except ValueError:
        w.prnt('', '%sError with option min_nick_length, should be a integer' % weechat.prefix('error'))
        w.config_set_plugin('min_nick_length', settings['min_nick_length'])

    if w.config_get_plugin('colorize_input') == 'on':
        pass
    elif w.config_get_plugin('colorize_input') == 'off':
        return line
    else:
        w.prnt('', '%sError with option colorize_input, should be on or off' % weechat.prefix('error'))
        w.config_set_plugin('colorize_input', settings['colorize_input'])
        return line

    buffer = w.current_buffer()
    # Check if buffer has colorized nicks
    if not buffer in colored_nicks:
        return line

    channel = w.buffer_get_string(buffer,'name')
    if channel in ignore_channels:
        return line

    reset = w.color('reset')

    for words in valid_nick_re.findall(line):
        prefix, nick = words[0], words[1]
        # Check that nick is not ignored and longer than minimum length
        if len(nick) < min_length or nick in ignore_nicks:
            continue
        if nick in colored_nicks[buffer]:
            nick_color = colored_nicks[buffer][nick]
            line = line.replace(nick, '%s%s%s' %(nick_color, nick, reset))

    return line

def populate_nicks(*args):
    ''' Fills entire dict with all nicks weechat can see and what color it has
    assigned to it. '''
    global colored_nicks

    colored_nicks = {}

    servers = w.infolist_get('irc_server', '', '')
    while w.infolist_next(servers):
        servername = w.infolist_string(servers, 'name')
        colored_nicks[servername] = {}
        my_nick = w.info_get('irc_nick', servername)
        channels = w.infolist_get('irc_channel', '', servername)
        while w.infolist_next(channels):
            pointer = w.infolist_pointer(channels, 'buffer')
            nicklist = w.infolist_get('nicklist', pointer, '')
            channelname = w.infolist_string(channels, 'name')

            if not pointer in colored_nicks:
                colored_nicks[pointer] = {}

            while w.infolist_next(nicklist):
                nick = w.infolist_string(nicklist, 'name')
                if nick == my_nick:
                    nick_color = w.color(\
                            w.config_string(\
                            w.config_get('weechat.color.chat_nick_self')))
                else:
                    nick_color = w.info_get('irc_nick_color', nick)

                colored_nicks[pointer][nick] = nick_color

            w.infolist_free(nicklist)

        w.infolist_free(channels)

    w.infolist_free(servers)

    return w.WEECHAT_RC_OK

def add_nick(data, signal, type_data):
    ''' Add nick to dict of colored nicks '''
    global colored_nicks

    pointer, nick = type_data.split(',')
    if not pointer in colored_nicks:
        colored_nicks[pointer] = {}

    servername = w.buffer_get_string(pointer, 'localvar_server')
    my_nick = w.buffer_get_string(pointer, 'localvar_nick')

    if nick == my_nick:
        nick_color = w.color(\
        w.config_string(\
        w.config_get('weechat.color.chat_nick_self')))
    else:
        nick_color = w.info_get('irc_nick_color', nick)

    colored_nicks[pointer][nick] = nick_color

    return w.WEECHAT_RC_OK

def remove_nick(data, signal, type_data):
    ''' Remove nick from dict with colored nicks '''
    global colored_nicks

    pointer, nick = type_data.split(',')

    if pointer in colored_nicks and nick in colored_nicks[pointer]:
        del colored_nicks[pointer][nick]

    return w.WEECHAT_RC_OK

def update_blacklist(*args):
    global ignore_channels, ignore_nicks
    if w.config_get_plugin('blacklist_channels'):
        ignore_channels = w.config_get_plugin('blacklist_channels').split(',')
    ignore_nicks = w.config_get_plugin('blacklist_nicks').split(',')
    return w.WEECHAT_RC_OK

if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        # Set default settings
#        for option, default_value in settings.iteritems():
        for option, default_value in list(settings.items()):
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, default_value)

        for key, value in list(PREFIX_COLORS.items()):
#        for key, value in PREFIX_COLORS.iteritems():
            PREFIX_COLORS[key] = w.color(w.config_string(w.config_get('weechat.look.%s'%value)))

        update_blacklist() # Set blacklist
        populate_nicks() # Run it once to get data ready
        w.hook_signal('nicklist_nick_added', 'add_nick', '')
        w.hook_signal('nicklist_nick_removed', 'remove_nick', '')
        w.hook_modifier('weechat_print', 'colorize_cb', '')
        # Hook config for changing colors
        w.hook_config('weechat.color.chat_nick_colors', 'populate_nicks', '')
        # Hook for working togheter with other scripts (like colorize_lines)
        w.hook_modifier('colorize_nicks', 'colorize_cb', '')
        # Hook for modifying input
        w.hook_modifier('250|input_text_display', 'colorize_input_cb', '')
        # Hook for updating blacklist (this could be improved to use fnmatch)
        weechat.hook_config('plugins.var.python.%s.blacklist*' %SCRIPT_NAME, 'update_blacklist', '')
