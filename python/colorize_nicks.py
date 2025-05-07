# SPDX-FileCopyrightText: 2010 xt <xt@bash.no>
# SPDX-FileCopyrightText: 2025 ryoskzypu <ryoskzypu@proton.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
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
# Bugs:
#   https://github.com/ryoskzypu/weechat_scripts
#
# History:
# 2025-05-08: ryoskzypu <ryoskzypu@proton.me>
#   version 33: add many improvements, features, and fixes
# 2023-10-30: Sébastien Helleu <flashcode@flashtux.org>
#   version 32: revert to info "nick_color" with WeeChat >= 4.1.1
# 2023-10-16: Sébastien Helleu <flashcode@flashtux.org>
#   version 31: use info "irc_nick_color" on IRC buffers with WeeChat >= 4.1.0
# 2022-11-07: mva
#   version 30: add ":" and "," to VALID_NICK regexp,
#               to don't reset colorization in input_line
# 2022-07-11: ncfavier
#   version 29: check nick for exclusion *after* stripping
#               decrease minimum min_nick_length to 1
# 2020-11-29: jess
#   version 28: fix ignore_tags having been broken by weechat 2.9 changes
# 2020-05-09: Sébastien Helleu <flashcode@flashtux.org>
#   version 27: add compatibility with new weechat_print modifier data
#               (WeeChat >= 2.9)
# 2018-04-06: Joey Pabalinas <joeypabalinas@gmail.com>
#   version 26: fix freezes with too many nicks in one line
# 2018-03-18: nils_2
#   version 25: fix unable to run function colorize_config_reload_cb()
# 2017-06-20: lbeziaud <louis.beziaud@ens-rennes.fr>
#   version 24: colorize utf8 nicks
# 2017-03-01, arza <arza@arza.us>
#   version 23: don't colorize nicklist group names
# 2016-05-01, Simmo Saan <simmo.saan@gmail.com>
#   version 22: invalidate cached colors on hash algorithm change
# 2015-07-28, xt
#   version 21: fix problems with nicks with commas in them
# 2015-04-19, xt
#   version 20: fix ignore of nicks in URLs
# 2015-04-18, xt
#   version 19: new option ignore nicks in URLs
# 2015-03-03, xt
#   version 18: iterate buffers looking for nicklists instead of servers
# 2015-02-23, holomorph
#   version 17: fix coloring in non-channel buffers (#58)
# 2014-09-17, holomorph
#   version 16: use weechat config facilities
#               clean unused, minor linting, some simplification
# 2014-05-05, holomorph
#   version 15: fix python2-specific re.search check
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

import weechat
import re

# Debug data structures.
#from pprint import PrettyPrinter
#pp = PrettyPrinter(indent=4)

w = weechat

SCRIPT_NAME    = 'colorize_nicks'
SCRIPT_AUTHOR  = 'xt <xt@bash.no>'
SCRIPT_VERSION = '33'
SCRIPT_LICENSE = 'GPL'
SCRIPT_DESC    = 'Use the weechat nick colors in the chat area'

# Config file/options
config_file     = ''  # Pointer
config_option   = {}
ignore_channels = []  # ignore_channels
ignore_nicks    = []  # ignore_nicks

# Dict with every nick on every channel, with its color and prefix as lookup values.
colored_nicks = {}

# Regexes

colors_rgx = r'''
                 \031
                 (?:
                     \d{2}                      # Fixed 'weechat.color.chat.*' codes
                     |
                     (?:                        # Foreground
                         [F*]
                         [*!\/_%.|]?            # IRC colors (00–15)
                         \d{2}
                         |
                         (?: F@ | \*@)          # IRC colors (16–99) and WeeChat colors (16–255)
                         [*!\/_%.|]?
                         \d{5}
                     )
                     (?:                        # Background
                         ~
                         (?: \d{2} | @\d{5})
                     )?
                 )
             '''
attr_rgx   = r'''
                 (?: \032 | \033)
                 [\001-\006]
                 |
                 \031\034                       # Reset color and keep attributes
             '''
reset_rgx  = r'\034'
split_rgx  = rf'''
                 ({colors_rgx})                 # Colors
                 |
                 ({attr_rgx})                   # Attributes
                 |
                 ({reset_rgx})                  # Reset all
                 |
                                                # Chars
             '''
has_colors_rgx  = rf'{colors_rgx} | {attr_rgx}'
is_color_rgx    = rf'\A(?: {has_colors_rgx})\Z'
exact_color_rgx = rf'\A{colors_rgx}\Z'

# Dict of regexes to compile.
regex = {
        'colors':      colors_rgx,
        'attr':        attr_rgx,
        'reset':       reset_rgx,
        'split':       split_rgx,
        'has_colors':  has_colors_rgx,
        'is_color':    is_color_rgx,
        'exact_color': exact_color_rgx,
}

# Reset color code
reset = w.color('reset')

# Space hex code
space = '\x20'

# Unique escape codes
uniq_esc_nick = '\36'  # Nick
uniq_esc_pref = '\37'  # Prefix

def config_init():
    '''
    Initialization of configuration file.
    Sections: look.
    '''

    global config_file

    # Create config.
    if (config_file := w.config_new(SCRIPT_NAME, '', '')) == '':
        return 'failed to create config file'

    # Create 'look' section.
    if (section_look := w.config_new_section(
        config_file, 'look', 0, 0, '', '', '', '', '', '', '', '', '', '')) == '':
        w.config_free(config_file)
        return 'failed to create look section'

    # Create 'look' options.

    opts = [
            {
                'option':       'ignore_channels',
                'opt_type':     'string',
                'desc':         'comma separated list of channels to ignore',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      '',
                'value':        '',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'ignore_nicks',
                'opt_type':     'string',
                'desc':         'comma separated list of nicks to ignore',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      '',
                'value':        '',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'colorize_filter',
                'opt_type':     'boolean',
                'desc':         'colorize nicks in filtered messages from /filter',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      'off',
                'value':        'off',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'colorize_input',
                'opt_type':     'boolean',
                'desc':         'colorize nicks in input',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      'off',
                'value':        'off',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'irc_only',
                'opt_type':     'boolean',
                'desc':         'ignore non IRC messages; i.e. set buffer restrictions: plugin = irc, tags = irc_privmsg and irc_notice, type = channel and private',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      'off',
                'value':        'off',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'ignore_tags',
                'opt_type':     'string',
                'desc':         'comma separated list of tags to ignore; i.e. irc_join,irc_part,irc_quit',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      '',
                'value':        '',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'min_nick_length',
                'opt_type':     'integer',
                'desc':         'minimum length of nicks to colorize',
                'str_val':      '',
                'min_val':      1,
                'max_val':      20,
                'default':      '1',
                'value':        '1',
                'null_val':     0,
                'check_val_cb': '',
            },
            {
                'option':       'nick_suffixes',
                'opt_type':     'string',
                'desc':         'character set of nick suffixes; matches only one out of several characters',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      ':,',
                'value':        ':,',
                'null_val':     0,
                'check_val_cb': 'check_affix_cb',
            },
            # Default charset is based on IRC channel membership prefixes.
            {
                'option':       'nick_prefixes',
                'opt_type':     'string',
                'desc':         'character set of nick prefixes; matches only one out of several characters',
                'str_val':      '',
                'min_val':      0,
                'max_val':      0,
                'default':      '~&@%+',
                'value':        '~&@%+',
                'null_val':     0,
                'check_val_cb': 'check_affix_cb',
            }
    ]

    if (rc := set_options(config_file, section_look, opts)):
        return rc

def set_options(config, section, options):
    ''' Creates config file options of a section. '''

    for i in options:
        option = i['option']

        config_option[option] = w.config_new_option(
                config,
                section,
                option,
                i['opt_type'],
                i['desc'],
                i['str_val'],
                i['min_val'],
                i['max_val'],
                i['default'],
                i['value'],
                i['null_val'],
                i['check_val_cb'],
                '', '', '', '', '')

        if not config_option[option]:
            return f"failed to create config '{option}' option"

def config_read():
    ''' Reads the configuration file and updates config pointers. '''

    rc = w.config_read(config_file)

    try:
        if rc == w.WEECHAT_CONFIG_READ_MEMORY_ERROR:
            raise ValueError('not enough memory to read config file')
        elif rc == w.WEECHAT_CONFIG_READ_FILE_NOT_FOUND:
            raise ValueError('config file was not found')

    except ValueError as err:
        w.prnt('', f'{SCRIPT_NAME}\t{err.args[0]}')
        raise

def check_affix_cb(data, option, value):
    ''' Checks if affix option is empty. Note that it must have a value, and space
    (\x20) is ignored. '''

    if value == '':
        return 0

    return 1

def compile_regexes():
    ''' Compiles all script regexes for reuse. '''

    for k,v in regex.items():
        regex[k] = re.compile(v, flags=re.VERBOSE)

def debug_str(var, string):
    ''' Displays string information for debugging in core.weechat buffer. '''

    w.prnt('', f'{var}:')
    w.command('', f'/debug unicode {string}')
    w.prnt('', '')

def get_nick_color(buffer, nick, my_nick):
    ''' Retrieves nick color code from weechat. '''

    if nick == my_nick:
        return w.color(w.config_string(w.config_get('weechat.color.chat_nick_self')))
    else:
        version = int(w.info_get('version_number', '') or 0)

        # 'irc_nick_color' (deprecated since version 1.5, replaced by 'nick_color')
        if w.buffer_get_string(buffer, 'plugin') == 'irc' and version == 0x4010000:
            server = w.buffer_get_string(buffer, 'localvar_server')
            return w.info_get('irc_nick_color', f'{server},{nick}')

        return w.info_get('nick_color', nick)

def colorize_priv_nicks(buffer):
    ''' Colorizes nicks on IRC private buffers. '''

    # Reset the buffer dict to update nicks changes, since there is no nicklist
    # in private buffers.
    colored_nicks[buffer] = {}

    my_nick   = w.buffer_get_string(buffer, 'localvar_nick')
    priv_nick = w.buffer_get_string(buffer, 'localvar_channel')

    for nick in my_nick, priv_nick:
        nick_color = get_nick_color(buffer, nick, my_nick)

        colored_nicks[buffer][nick] = {
                'color':  nick_color,
                'prefix': '',
        }

def colorize_nicks(buffer, min_len, prefixes, suffixes, has_colors, line):
    ''' Finds every nick from the dict of colored nicks, in the line and colorizes
    them. '''

    chop_line            = line
    chop_match           = ''
    chop_match_after     = ''
    color_match          = ''
    colorized_nicks_line = ''
    nick_end             = reset

    # Mark the nick's end with a unique escape to identify its position on preserve_colors().
    if has_colors is not None:
        nick_end = uniq_esc_nick

    # Split words on spaces, since it is the most common word divider and is not
    # valid in 'nicks' on popular protocols like IRC and matrix; thus protocols
    # that allow spaces in 'nicks' are limited here.
    for word in re.split(f'{space}+', line.strip(f'{space}')):
        nick_prefix = ''  # Reset nick prefix.

        if word == '':
            continue

        # Get possible nick from word.
        nicks_rgx = rf'''
                        [{prefixes}]?     # Optional prefix char
                        (?P<nick> [^ ]+)
                     '''
        if (nick := re.search(nicks_rgx, word, flags=re.VERBOSE)) is not None:
            nick = re.escape(nick.group('nick'))

        # If the word is not a known nick and its last character is an option
        # suffix (e.g. colon ':' or comma ','), try to match the word without it.
        # This is necessary as 'foo:' is a valid nick, which could be addressed
        # as 'foo::'.
        if nick not in colored_nicks[buffer]:
            if (suffix := re.search(rf'[{suffixes}]$', nick)) is not None:
                nick = nick[:-1]

        # Nick exists on buffer.
        if nick in colored_nicks[buffer]:
            if nick in ignore_nicks or len(nick) < min_len:
                continue

            # Get its color.
            nick_color = colored_nicks[buffer][nick]['color']

            # Find nick in the line.
            line_rgx = rf'''
                           (?: \A | [ ])             # Boundary
                           (?P<pref> [{prefixes}])?  # Optional prefix char
                           (?P<nick> {nick})
                           [{suffixes}]?             # "        suffix char
                           (?: \Z | [ ])             # Boundary
                       '''

            # Nick is found in the line.
            if (line_match := re.search(line_rgx, chop_line, flags=re.VERBOSE)) is not None:
                # In order to prevent the regex engine to needless find the nicks
                # at previous match positions, preserve the state by chopping the
                # line at the start and end positions of matches.

                # Start position of nick match.
                start = line_match.start('nick')

                # Get the real nick prefix from nicklist.
                if (pref_match := line_match.group('pref')) is not None:
                    nick_prefix = colored_nicks[buffer][nick]['prefix']

                    # If it exists, update the start position match.
                    if pref_match == w.string_remove_color(nick_prefix, ''):
                        start = line_match.start('pref')

                        # Mark the prefix with a unique escape to idenfity its
                        # position on preserve_colors().
                        if has_colors is not None:
                            nick_prefix = f'{uniq_esc_pref}{nick_prefix}'
                    else:
                        nick_prefix = ''

                # End position of nick match.
                end = line_match.end('nick')

                # Chop
                chop_till_match  = chop_line[:end]
                chop_after_match = chop_line[end:]

                # Concat the chopped strings while colorizing the nick, then update
                # the chopped line.
                nick_str     = f'{nick_prefix}{nick_color}{nick}{nick_end}'
                color_match += f'{chop_till_match[:start]}{nick_str}{chop_till_match[end:]}'
                chop_line    = chop_after_match

    if color_match:
        colorized_nicks_line = f'{color_match}{chop_after_match}'

    return colorized_nicks_line

def preserve_colors(line, colorized_nicks_line):
    '''
    If the line string is already colored, captures every color code before the nick
    match, for restoration after nick colorizing. Otherwise string colors after the
    nick are reset.

    Testing:
      1. Create an IRC channel.
           /j ##testing-weechat

      2. Create the nick 'nick111' with perlexec:
          /perlexec my $buffer = weechat::buffer_search('==', 'irc.libera.##testing-weechat'); my $group = weechat::nicklist_add_group($buffer, '', 'test_group', 'weechat.color.nicklist_group', 1); weechat::nicklist_add_nick($buffer, $group, 'nick111', 'blue', '@', 'lightgreen', 1)

      3. Send this message in the channel with script unloaded:
          /input insert \x0305<\x03043 \x02\x0307nick111 is awesome\x02 \x0314[0 user] \x0399\x1fhttps://github.com/ \x0305n\x0355i\x0384c\x0302k\x0f\x03921\x03091\x03381 /weechat/ https\x1f\x16:// nick111 .org/

      4. Repeat step 3 with the script loaded. It should colorize the nicks and
         preserve all colors.
         The string is inspired by ##hntop messages and modified to cover some corner cases.
    '''

    new_line      = ''
    split_line    = []
    split_line_nc = []
    color_codes   = ''
    idx           = 0
    match         = 0

    # Split all color codes and bytes from the lines.
    split_line    = [x for x in regex['split'].split(line)                 if x is not None and x]
    split_line_nc = [y for y in regex['split'].split(colorized_nicks_line) if y is not None and y]

    # Debug split lists.
    #w.prnt('', f'split_line:'    + pp.pformat(split_line))
    #w.prnt('', f'split_line_nc:' + pp.pformat(split_line_nc))

    # Iterate through the original split list, comparing every char against the
    # uncolored list; while reconstructing the new line with saved color codes.
    for i in split_line:
        #w.prnt('', f'i: ' + pp.pformat(f'{i}'))
        #w.prnt('', f"split_line_nc[{idx}]: " + pp.pformat(f'{split_line_nc[idx]}'))

        # It is a color code, so append its codes to be restored.
        if regex['is_color'].search(i) is not None:
            color_codes += i
            #w.prnt('', f'color_codes: ' + pp.pformat(f'{color_codes}'))

            # Append the codes if not inside a nick match.
            if not match:
                new_line += i

            continue
        # Remove saved codes if a reset code is found.
        elif i == reset:
            if not match:
                new_line += i

            color_codes = ''
            continue
        elif split_line_nc[idx]:
            # It is a char, so compare it against the uncolored's char.
            if i == split_line_nc[idx]:
                new_line += i
                idx      += 1

                continue
            # If the char is in a nick match and uncolored's is a unique nick
            # escape code, restore the saved codes, then advance the index.
            elif match and split_line_nc[idx] == uniq_esc_nick:
                #w.prnt('', f"split_line_nc[{idx} + 1]: " + pp.pformat(f'{split_line_nc[idx + 1]}'))

                # If the chars match, advance the index.
                if split_line_nc[idx + 1] == i:
                    new_line += f'{reset}{color_codes}{i}'
                    idx      += 2
                    match     = 0

                    continue
            # It is a unique prefix escape code, so get its color code and char,
            # then advance uncolored's index to the start of colorized nick match.
            elif split_line_nc[idx] == uniq_esc_pref:
                prefix    = f'{split_line_nc[idx + 1]}{i}'
                new_line += prefix
                idx      += 3

                continue
            # It is the start of a colorized nick match, so colorize the new line,
            # then advance uncolored's index to the current char.
            elif (split_match := regex['exact_color'].search(split_line_nc[idx])) is not None:
                #w.prnt('', f"split_line_nc[{idx} + 1]: " + pp.pformat(f'{split_line_nc[idx + 1]}'))

                nick_color  = split_match.group(0)
                idx        += 1
                new_line   += f'{reset}{nick_color}{split_line_nc[idx]}'
                match       = 1

                # If the chars match, advance the index.
                if i == split_line_nc[idx]:
                    idx += 1
                    continue

    return new_line

def init_colorize(buffer, message):
    ''' Initializes the process of nicks colorizing. '''

    colorized_nicks_msg = ''
    new_msg             = ''

    # Get options.
    min_len      = w.config_integer(config_option['min_nick_length'])
    pref_charset = re.escape(w.config_string(config_option['nick_prefixes']))
    suff_charset = re.escape(w.config_string(config_option['nick_suffixes']))

    # Check if message has color codes.
    has_colors = regex['has_colors'].search(message)

    # Remove any color codes from message in order to match and colorize the strings correctly.
    msg_nocolor = w.string_remove_color(message, '')

    # Find and colorize the nicks.
    colorized_nicks_msg = colorize_nicks(buffer, min_len, pref_charset, suff_charset, has_colors, msg_nocolor)

    # Preserve colors from message.
    if has_colors is not None and colorized_nicks_msg:
        new_msg = preserve_colors(message, colorized_nicks_msg)

    # Debug the message string.
    #debug_str('message', message)

    # Update the message.

    if colorized_nicks_msg:
        #debug_str('colorized_nicks_msg', colorized_nicks_msg)
        message = colorized_nicks_msg

    if new_msg:
        #debug_str('new_msg', new_msg)
        message = new_msg

    return message

def colorize_cb(data, hashtable):
    '''
    Callback that does the colorizing of nicks from messages and returns a new message.

    Testing:
      1. Create an IRC channel:
         /j ##testing-weechat

      2. Create the nicks: alice, :alicee, alicee:, :alicee:, and utf8©nick
         with perlexec:
           /perlexec my @nicks = qw(alice :alicee alicee: :alicee: utf8©nick); my $buffer = weechat::buffer_search('==', 'irc.libera.##testing-weechat'); my $group = weechat::nicklist_add_group($buffer, '', 'test_group', 'weechat.color.nicklist_group', 1); foreach my $i (@nicks) { weechat::nicklist_add_nick($buffer, $group, $i, 'default', '@', 'lightgreen', 1) }

      3. Then paste and send this string:
         hey alicee and utf8©nickz, how are you? sorry, alice and utf8©nick   @alicee: @:alicee @:alicee: aaaliceee @:alicee:: @::alicee:: @alicee:: %alicee:, ~:alicee,  Nice to meet you @:alicee,,  &:alicee:, @:alicee,: :alicee, :alicee alicee: <3 :alicee: :alicee::: +utf8©nick: :-) bye

      4. The colors that matter are in the message, so ignore the static nicklist
         colors. The nicks in message should be colorized correctly based on weechat's
         color algorithm, and respect the script affixes.
         Insert a reverse color code (^Cv) at the beggining of string, if having
         trouble on seeing the colors.
    '''

    buffer    = hashtable['buffer']
    tags      = hashtable['tags'].split(',')
    displayed = hashtable['displayed']
    message   = hashtable['message']

    plugin  = w.buffer_get_string(buffer, 'localvar_plugin')
    bufname = w.buffer_get_string(buffer, 'localvar_name')
    buftype = w.buffer_get_string(buffer, 'localvar_type')
    channel = w.buffer_get_string(buffer, 'localvar_channel')

    irc_only = w.config_boolean(config_option['irc_only'])

    # Colorize only IRC user messages.
    if plugin == 'irc' or irc_only and plugin != 'irc':
        # There is no point in colorizing non channel/private buffers, and IRC
        # tags other than 'irc_privmsg/notice', since tags i.e. irc_join/part/quit
        # are already colored.
        if buftype != 'channel' and buftype != 'private' or tags[0] != 'irc_privmsg' and tags[0] != 'irc_notice':
            return hashtable

    # Colorize nicks on IRC private buffers.
    if plugin == 'irc' and buftype == 'private':
        colorize_priv_nicks(buffer)

    # Check if buffer has colorized nicks.
    if not colored_nicks.get(buffer):
        return hashtable

    # Check if channel is ignored.
    if channel and channel in ignore_channels:
        return hashtable

    # Do not colorize if an ignored tag is present in message.
    tag_ignores = w.config_string(config_option['ignore_tags']).split(',')
    for tag in tags:
        if tag in tag_ignores:
            return hashtable

    # Do not colorize if message is filtered.
    if displayed == '0' and not w.config_boolean(config_option['colorize_filter']):
        return hashtable

    # Init colorizing process.
    message = init_colorize(buffer, message)

    # Debug the hashtable.
    #w.prnt('', 'hashtable:\n' + pp.pformat(hashtable))

    # Update the hashtable.
    hashtable['message'] = message

    return hashtable

def colorize_input_cb(data, modifier, modifier_data, line):
    ''' Callback that does the colorizing of nicks from weechat's input. '''

    if not w.config_boolean(config_option['colorize_input']):
        return line

    buffer  = w.current_buffer()
    plugin  = w.buffer_get_string(buffer, 'localvar_plugin')
    buftype = w.buffer_get_string(buffer, 'localvar_type')
    channel = w.buffer_get_string(buffer, 'localvar_channel')

    irc_only = w.config_boolean(config_option['irc_only'])

    # Colorize only IRC user messages.
    if plugin == 'irc' or irc_only and plugin != 'irc':
        # There is no point in colorizing non channel/private buffers.
        if buftype != 'channel' and buftype != 'private':
            return line

    # Check if current buffer has colorized nicks.
    if not colored_nicks.get(buffer):
        return line

    # Check if current channel is ignored.
    if channel and channel in ignore_channels:
        return line

    # Decode IRC colors from input.
    if plugin == 'irc':
        line = w.hook_modifier_exec('irc_color_decode', '1', line)

    # Init colorizing process.
    line = init_colorize(buffer, line)

    return line

def populate_nicks_cb(*args):
    ''' Callback that fills the colored nicks dict with all nicks weechat can see,
    and what color and prefix it has assigned to it. '''

    bufname      = ''
    prefix_color = ''
    nick_prefix  = ''
    irc_only     = w.config_boolean(config_option['irc_only'])

    # Get nicks only in IRC buffers.
    if irc_only:
        bufname = 'irc.*'

    # Get list of buffers.
    if not (buffers := w.infolist_get('buffer', '', bufname)):
        w.prnt('', f'{SCRIPT_NAME}\tfailed to get list of buffers')
        return w.WEECHAT_RC_ERROR

    while w.infolist_next(buffers):
        buffer_ptr = w.infolist_pointer(buffers, 'pointer')
        channel    = w.buffer_get_string(buffer_ptr, 'localvar_channel')

        # Skip non-IRC channel buffers.
        if irc_only and not w.info_get('irc_is_channel', channel):
            continue

        my_nick = w.buffer_get_string(buffer_ptr, 'localvar_nick')

        if (nicklist := w.infolist_get('nicklist', buffer_ptr, '')):
            while w.infolist_next(nicklist):
                if buffer_ptr not in colored_nicks:
                    colored_nicks[buffer_ptr] = {}

                # Skip nick groups.
                if w.infolist_string(nicklist, 'type') != 'nick':
                    continue

                # Get nicks colors.
                nick       = w.infolist_string(nicklist, 'name')
                nick_color = get_nick_color(buffer_ptr, nick, my_nick)

                # Get nicks prefixes.
                prefix = w.infolist_string(nicklist, 'prefix')
                if prefix != space:
                    prefix_color = w.color(w.infolist_string(nicklist, 'prefix_color'))
                    nick_prefix  = f'{prefix_color}{prefix}'

                # Populate
                colored_nicks[buffer_ptr][nick] = {
                        'color':  nick_color,
                        'prefix': nick_prefix,
                }
                nick_prefix = ''

        w.infolist_free(nicklist)

    w.infolist_free(buffers)

    #w.prnt('', 'colored_nicks:\n' + pp.pformat(colored_nicks))

    return w.WEECHAT_RC_OK

def add_nick_cb(data, signal, signal_data):
    ''' Callback that adds a nick to the dict of colored nicks, when a nick is
    added to the nicklist. '''

    # Nicks can have ',' in them in some protocols.
    buffer, nick = signal_data.split(',', maxsplit=1)

    if buffer not in colored_nicks:
        colored_nicks[buffer] = {}

    # Get nick color.
    my_nick    = w.buffer_get_string(buffer, 'localvar_nick')
    nick_color = get_nick_color(buffer, nick, my_nick)

    # Get nick prefix.
    nick_prefix = ''
    if (nicklist := w.infolist_get('nicklist', buffer, f'nick_{nick}')):
        while w.infolist_next(nicklist):
            prefix = w.infolist_string(nicklist, 'prefix')

            if prefix != space:
                prefix_color = w.color(w.infolist_string(nicklist, 'prefix_color'))
                nick_prefix  = f'{prefix_color}{prefix}'

    # Update
    colored_nicks[buffer][nick] = {
            'color':  nick_color,
            'prefix': nick_prefix,
    }

    w.infolist_free(nicklist)
    w.infolist_free(buffer)

    #w.prnt('', 'colored_nicks:\n' + pp.pformat(colored_nicks))

    return w.WEECHAT_RC_OK

def remove_nick_cb(data, signal, signal_data):
    ''' Callback that removes a nick from the dict of colored nicks, when a nick is
    removed from the nicklist. '''

    # Nicks can have ',' in them in some protocols.
    buffer, nick = signal_data.split(',', maxsplit=1)

    if buffer in colored_nicks and nick in colored_nicks[buffer]:
        del colored_nicks[buffer][nick]

    #w.prnt('', 'colored_nicks:\n' + pp.pformat(colored_nicks))

    return w.WEECHAT_RC_OK

def remove_priv_buffer_cb(data, signal, buffer):
    ''' Callback that removes an IRC private buffer from the dict of colored nicks,
    when the buffer is closing. '''

    # For some reason, weechat crashes if the hook signal is set to 'buffer_closed'
    # while trying to get the 'localvar_*' strings.
    # Perhaps the buffer pointer is not valid anymore because it was closed?
    plugin  = w.buffer_get_string(buffer, 'localvar_plugin')
    buftype = w.buffer_get_string(buffer, 'localvar_type')

    if plugin == 'irc' and buftype == 'private' and buffer in colored_nicks:
        del colored_nicks[buffer]

    #w.prnt('', 'colored_nicks:\n' + pp.pformat(colored_nicks))

    return w.WEECHAT_RC_OK

def update_blacklist_cb(*args):
    ''' Callback that sets the blacklist for channels and nicks. '''

    global ignore_channels, ignore_nicks

    ignore_channels = w.config_string(config_option['ignore_channels']).split(',')
    ignore_nicks    = w.config_string(config_option['ignore_nicks']).split(',')

    return w.WEECHAT_RC_OK

if __name__ == '__main__':
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        # Initialize config options and regexes.
        try:
            if (msg := config_init()):
                raise ValueError(msg)

        except ValueError as err:
            w.prnt('', f'{SCRIPT_NAME}\t{err.args[0]}')
            raise

        config_read()
        compile_regexes()

        # Run once to get data ready.
        update_blacklist_cb()
        populate_nicks_cb()

        # Hooks

        # Colorize nicks.
        w.hook_line('', '', '', 'colorize_cb', '')                          # Message
        w.hook_modifier('250|input_text_display', 'colorize_input_cb', '')  # Input

        # Update nicks.
        w.hook_signal('nicklist_nick_added', 'add_nick_cb', '')
        w.hook_signal('nicklist_nick_removed', 'remove_nick_cb', '')
        w.hook_signal('buffer_closing', 'remove_priv_buffer_cb', '')

        # Repopulate nicks on colors changes from weechat's options.
        w.hook_config('weechat.color.chat_nick_colors', 'populate_nicks_cb', '')
        w.hook_config('weechat.look.nick_color_hash', 'populate_nicks_cb', '')
        w.hook_config('irc.color.nick_prefixes', 'populate_nicks_cb', '')

        # Update blacklists.
        w.hook_config(f'{SCRIPT_NAME}.look.ignore_*', 'update_blacklist_cb', '')
