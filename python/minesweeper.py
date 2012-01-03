# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Sebastien Helleu <flashcode@flashtux.org>
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

#
# Minesweeper game for WeeChat.
# (mouse supported with WeeChat >= 0.3.6)
#
# History:
#
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: make script compatible with Python 3.x
# 2011-10-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: stop timer when game ends (win with flags remaining) or when
#                  minesweeper buffer is not displayed
# 2011-10-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: fix end of game when player blows up
# 2011-10-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: end game (win) if all squares without mines are explored
# 2011-10-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add option "utf8" (to disable utf-8 chars for grid and flags)
# 2011-10-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'minesweeper'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.6'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Minesweeper game'

SCRIPT_COMMAND = 'minesweeper'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import random, copy
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

minesweeper = {
    'buffer'      : '',
    'board'       : [],
    'mines'       : { 8: 10, 15: 35, 30: 100, 50: 350 },
    'size'        : 8,
    'zoom'        : 1,
    'x'           : 7,
    'y'           : 7,
    'flags'       : 0,
    'timer'       : '',
    'time'        : 0,
    'end'         : '',
    'endmsg'      : { 'win': ('lightgreen', 'Congratulations!'), 'lose': ('lightred', 'You blew up!') },
    'color_digits': [],
    'cursor'      : False,
    'cheat'       : False,
}

# script options
minesweeper_settings_default = {
    'color_grid'        : ('243',     'default',   'color for grid'),
    'color_square_bg'   : ('239',     'blue',      'color for square (background)'),
    'color_flag'        : ('white',   'yellow',    'color for flag'),
    'color_cursor_bg'   : ('19',      'lightblue', 'color for cursor (background)'),
    'color_mine'        : ('white',   'white',     'color for mine'),
    'color_mine_bg'     : ('97',      'magenta',   'color for mine (background)'),
    'color_explosion_bg': ('172',     'red',       'color for explosion (background)'),
    'color_digits'      : ('21,126,34,209,201,185,15,160,9',
                           'blue,magenta,green,brown,lightmagenta,default,white,red,lightred',
                           'comma-separated list of 9 colors (for digits 1-9)'),
    'utf8'              : ('on',      'on',        'use utf-8 chars to draw grid and flags (your terminal/font must support these chars)'),
    'zoom'              : ('',        '',          'zoom for board: 0 or 1 (size of squares: 0 = 4x2, 1 = 6x3 (better), empty means automatic zoom according to size of window)'),
}
minesweeper_settings = {}

# mouse keys
minesweeper_mouse_keys = { '@chat(python.minesweeper):button1*': '/window ${_window_number};hsignal:minesweeper_mouse',
                           '@chat(python.minesweeper):button2*': '/window ${_window_number};hsignal:minesweeper_mouse' }

def minesweeper_display_status():
    """Display status line below board."""
    global minesweeper
    if not minesweeper['buffer']:
        return
    msgend = ''
    if minesweeper['end']:
        msgend = '%s%s' % (weechat.color(minesweeper['endmsg'][minesweeper['end']][0]), minesweeper['endmsg'][minesweeper['end']][1])
    else:
        if minesweeper['flags'] == 0:
            msgend = '%sSome bad flags, remove and go on!' % weechat.color('yellow')
    hours = minesweeper['time'] // 3600
    minutes = (minesweeper['time'] % 3600) // 60
    seconds = (minesweeper['time'] % 3600) % 60
    if minesweeper_settings['utf8'] == 'on':
        flag = '⚑'
    else:
        flag = 'p'
    weechat.prnt_y(minesweeper['buffer'], 2 + (minesweeper['size'] * (minesweeper['zoom'] + 2)),
                   '%s %3d%s/%-3d%s%5d:%02d:%02d  %s' % (flag, minesweeper['flags'], weechat.color('green'),
                                                         minesweeper['mines'][minesweeper['size']],
                                                         weechat.color('reset'), hours, minutes, seconds,
                                                         msgend))

def minesweeper_display(clear=False):
    """Display status and board."""
    global minesweeper, minesweeper_settings
    if not minesweeper['buffer']:
        return
    if clear:
        weechat.buffer_clear(minesweeper['buffer'])
    if minesweeper_settings['utf8'] == 'on':
        hbar = '▁'
        vbar = '▕'
        flag = '⚑'
    else:
        hbar = '_'
        vbar = '|'
        flag = 'p'
    str_grid = '%s%s%s%s ' % (hbar, hbar, hbar, hbar * minesweeper['zoom'] * 2)
    weechat.prnt_y(minesweeper['buffer'], 0, '%s%s' % (weechat.color(minesweeper_settings['color_grid']), str_grid * minesweeper['size']))
    color_explosion = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_explosion_bg'])
    color_explosion_text = '%s,%s' % (minesweeper_settings['color_flag'], minesweeper_settings['color_explosion_bg'])
    color_mine = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_mine_bg'])
    color_mine_text = '%s,%s' % (minesweeper_settings['color_mine'], minesweeper_settings['color_mine_bg'])
    for y, line in enumerate(minesweeper['board']):
        if minesweeper['zoom'] == 0:
            str_lines = ['', '']
        else:
            str_lines = ['', '', '']
        for x, status in enumerate(line):
            if minesweeper['cursor'] and minesweeper['x'] == x and minesweeper['y'] == y:
                color_nostatus = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_cursor_bg'])
                color_flag = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_cursor_bg'])
                color_flag_text = '%s,%s' % (minesweeper_settings['color_flag'], minesweeper_settings['color_cursor_bg'])
                color_digit = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_cursor_bg'])
                color_digit_text_bg = ',%s' % minesweeper_settings['color_cursor_bg']
            else:
                color_nostatus = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_square_bg'])
                color_flag = '%s,%s' % (minesweeper_settings['color_grid'], minesweeper_settings['color_square_bg'])
                color_flag_text = '%s,%s' % (minesweeper_settings['color_flag'], minesweeper_settings['color_square_bg'])
                color_digit = '%s,default' % minesweeper_settings['color_grid']
                color_digit_text_bg = ',default'
            if status[1] == ' ':
                char = ' '
                if status[0] and minesweeper['cheat']:
                    char = '*'
                if minesweeper['zoom'] == 0:
                    str_lines[0] += '%s %s %s%s' % (weechat.color(color_nostatus), char, vbar, weechat.color('reset'))
                    str_lines[1] += '%s%s%s%s' % (weechat.color(color_nostatus), hbar * 3, vbar, weechat.color('reset'))
                else:
                    str_lines[0] += '%s     %s%s' % (weechat.color(color_nostatus), vbar, weechat.color('reset'))
                    str_lines[1] += '%s  %s  %s%s' % (weechat.color(color_nostatus), char, vbar, weechat.color('reset'))
                    str_lines[2] += '%s%s%s%s' % (weechat.color(color_nostatus), hbar * 5, vbar, weechat.color('reset'))
            elif status[1] == 'F':
                if minesweeper['zoom'] == 0:
                    str_lines[0] += '%s %s%s%s %s%s' % (weechat.color(color_flag), weechat.color(color_flag_text), flag, weechat.color(color_flag), vbar, weechat.color('reset'))
                    str_lines[1] += '%s%s%s%s' % (weechat.color(color_flag), hbar * 3, vbar, weechat.color('reset'))
                else:
                    str_lines[0] += '%s     %s%s' % (weechat.color(color_flag), vbar, weechat.color('reset'))
                    str_lines[1] += '%s  %s%s%s  %s%s' % (weechat.color(color_flag), weechat.color(color_flag_text), flag, weechat.color(color_flag), vbar, weechat.color('reset'))
                    str_lines[2] += '%s%s%s%s' % (weechat.color(color_flag), hbar * 5, vbar, weechat.color('reset'))
            elif status[1].isdigit():
                char = status[1]
                if char == '0':
                    char = ' '
                    color_digit_text = 'default'
                else:
                    color_digit_text = minesweeper['color_digits'][int(status[1]) - 1]
                if minesweeper['zoom'] == 0:
                    str_lines[0] += '%s %s%s%s %s%s' % (
                        weechat.color(color_digit), weechat.color(color_digit_text + color_digit_text_bg), char, weechat.color(color_digit), vbar, weechat.color('reset'))
                    str_lines[1] += '%s%s%s%s' % (weechat.color(color_digit), hbar * 3, vbar, weechat.color('reset'))
                else:
                    str_lines[0] += '%s     %s%s' % (weechat.color(color_digit), vbar, weechat.color('reset'))
                    str_lines[1] += '%s  %s%s%s  %s%s' % (
                        weechat.color(color_digit), weechat.color(color_digit_text + color_digit_text_bg), char, weechat.color(color_digit), vbar, weechat.color('reset'))
                    str_lines[2] += '%s%s%s%s' % (weechat.color(color_digit), hbar * 5, vbar, weechat.color('reset'))
            elif status[1] == '+':
                if minesweeper['zoom'] == 0:
                    str_lines[0] += '%s %s*%s %s%s' % (weechat.color(color_mine), weechat.color(color_mine_text), weechat.color(color_mine), vbar, weechat.color('reset'))
                    str_lines[1] += '%s%s%s%s' % (weechat.color(color_mine), hbar * 3, vbar, weechat.color('reset'))
                else:
                    str_lines[0] += '%s     %s%s' % (weechat.color(color_mine), vbar, weechat.color('reset'))
                    str_lines[1] += '%s  %s*%s  %s%s' % (weechat.color(color_mine), weechat.color(color_mine_text), weechat.color(color_mine), vbar, weechat.color('reset'))
                    str_lines[2] += '%s%s%s%s' % (weechat.color(color_mine), hbar * 5, vbar, weechat.color('reset'))
            elif status[1] == '*':
                if minesweeper['zoom'] == 0:
                    str_lines[0] += '%s %s*%s %s%s' % (
                        weechat.color(color_explosion), weechat.color(color_explosion_text), weechat.color(color_explosion), vbar, weechat.color('reset'))
                    str_lines[1] += '%s%s%s%s' % (weechat.color(color_explosion), hbar * 3, vbar, weechat.color('reset'))
                else:
                    str_lines[0] += '%s     %s%s' % (weechat.color(color_explosion), vbar, weechat.color('reset'))
                    str_lines[1] += '%s  %s*%s  %s%s' % (
                        weechat.color(color_explosion), weechat.color(color_explosion_text), weechat.color(color_explosion), vbar, weechat.color('reset'))
                    str_lines[2] += '%s%s%s%s' % (weechat.color(color_explosion), hbar * 5, vbar, weechat.color('reset'))
        for i, str_line in enumerate(str_lines):
            weechat.prnt_y(minesweeper['buffer'], 1 + (y * len(str_lines)) + i, str_line)
    minesweeper_display_status()

def minesweeper_adjust_zoom():
    """Choose zoom according to size of window."""
    global minesweeper, minesweeper_settings
    minesweeper['zoom'] = -1
    if minesweeper_settings['zoom']:
        try:
            minesweeper['zoom'] = int(minesweeper_settings['zoom'])
        except:
            minesweeper['zoom'] = -1
        if minesweeper['zoom'] > 1:
            minesweeper['zoom'] = 1
    if minesweeper['zoom'] < 0:
        width = weechat.window_get_integer(weechat.current_window(), 'win_chat_width')
        height = weechat.window_get_integer(weechat.current_window(), 'win_chat_height')
        minesweeper['zoom'] = 0
        if width >= minesweeper['size'] * 6 and height >= 1 + (minesweeper['size'] * 3) + 2:
            minesweeper['zoom'] = 1
    if minesweeper['zoom'] < 0:
        minesweeper['zoom'] = 0

def minesweeper_set_colors():
    """Set list of colors using settings."""
    global minesweeper, minesweeper_settings, minesweeper_settings_default
    minesweeper['color_digits'] = minesweeper_settings['color_digits'].split(',')
    if len(minesweeper['color_digits']) != 9:
        weechat.prnt('', '%sminesweeper: invalid colors (list must have 9 colors)' % weechat.prefix('error'))
        minesweeper['color_digits'] = minesweeper_settings_default['color_digits'][0].split(',')

def minesweeper_config_cb(data, option, value):
    """Called when a script option is changed."""
    global minesweeper_settings
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in minesweeper_settings:
            minesweeper_settings[name] = value
            if name == 'color_digits':
                minesweeper_set_colors()
            elif name == 'zoom':
                minesweeper_adjust_zoom()
    minesweeper_display()
    return weechat.WEECHAT_RC_OK

def minesweeper_timer_cb(data, remaining_calls):
    """Callback for timer."""
    global minesweeper
    if minesweeper['buffer'] and weechat.buffer_get_integer(minesweeper['buffer'], 'num_displayed') > 0:
        minesweeper['time'] += 1
    minesweeper_display_status()
    return weechat.WEECHAT_RC_OK

def minesweeper_timer_start():
    """Start timer."""
    global minesweeper
    if not minesweeper['timer']:
        minesweeper['time'] = 0
        minesweeper['timer'] = weechat.hook_timer(1000, 0, 0, 'minesweeper_timer_cb', '')

def minesweeper_timer_stop():
    """Stop timer."""
    global minesweeper
    if minesweeper['timer']:
        weechat.unhook(minesweeper['timer'])
        minesweeper['timer'] = ''

def minesweeper_new_game():
    """Create a new game: initialize board and some variables."""
    global minesweeper
    minesweeper['board'] = []
    for y in range(0, minesweeper['size']):
        line = []
        for x in range(0, minesweeper['size']):
            line.append([False, ' '])
        minesweeper['board'].append(line)
    for i in range(0, minesweeper['mines'][minesweeper['size']]):
        while 1:
            x = random.randint(0, minesweeper['size'] - 1)
            y = random.randint(0, minesweeper['size'] - 1)
            if not minesweeper['board'][y][x][0]:
                break
        minesweeper['board'][y][x][0] = True
    minesweeper['x'] = minesweeper['size'] // 2
    minesweeper['y'] = minesweeper['size'] // 2
    minesweeper['flags'] = minesweeper['mines'][minesweeper['size']]
    minesweeper_timer_stop()
    minesweeper['time'] = 0
    minesweeper['end'] = ''
    minesweeper_display(clear=True)

def minesweeper_end(end):
    """End of game."""
    global minesweeper
    minesweeper['end'] = end
    minesweeper_timer_stop()

def minesweeper_change_size(add):
    """Change size of board."""
    global minesweeper
    keys = sorted(minesweeper['mines'])
    index = keys.index(minesweeper['size']) + add
    if index >= 0 and index < len(keys):
        minesweeper['size'] = keys[index]
        minesweeper['count_max'] = minesweeper['mines'][minesweeper['size']]
        weechat.buffer_clear(minesweeper['buffer'])
        minesweeper_adjust_zoom()
        minesweeper_new_game()

def minesweeper_input_buffer(data, buffer, input):
    """Input data in minesweeper buffer."""
    global minesweeper
    if input:
        args = input.split(' ')
        if args[0] in ('n', 'new'):
            minesweeper_new_game()
        elif args[0] in ('q', 'quit'):
            weechat.buffer_close(minesweeper['buffer'])
        elif args[0] == '+':
            minesweeper_change_size(+1)
        elif args[0] == '-':
            minesweeper_change_size(-1)
    return weechat.WEECHAT_RC_OK

def minesweeper_close_buffer(data, buffer):
    """Called when minesweeper buffer is closed."""
    global minesweeper
    minesweeper_timer_stop()
    minesweeper['buffer'] = ''
    return weechat.WEECHAT_RC_OK

def minesweeper_init():
    """Init minesweeper: create buffer, adjust zoom, new game."""
    global minesweeper
    if minesweeper['buffer']:
        return
    minesweeper['buffer'] = weechat.buffer_search('python', 'minesweeper')
    if not minesweeper['buffer']:
        minesweeper['buffer'] = weechat.buffer_new('minesweeper', 'minesweeper_input_buffer', '', 'minesweeper_close_buffer', '')
        if minesweeper['buffer']:
            weechat.buffer_set(minesweeper['buffer'], 'type', 'free')
            weechat.buffer_set(minesweeper['buffer'], 'title',
                               'Minesweeper! | alt-space or mouse-b1: explore, alt-f or mouse-b2: flag, alt-n: new game, '
                               'alt-+/-: adjust board zoom | '
                               'Command line: (n)ew, +/-: change size, (q)uit')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta2-A', '/minesweeper up')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta2-B', '/minesweeper down')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta2-D', '/minesweeper left')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta2-C', '/minesweeper right')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta-f',  '/minesweeper flag')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta- ',  '/minesweeper explore')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta-n',  '/minesweeper new')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta-+',  '/minesweeper zoom')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta--',  '/minesweeper dezoom')
            weechat.buffer_set(minesweeper['buffer'], 'key_bind_meta-c',  '/minesweeper cheat')
    if minesweeper['buffer']:
        minesweeper_adjust_zoom()
        minesweeper_new_game()

def minesweeper_number_around(x, y):
    """Return number of mines around."""
    global minesweeper
    around = 0
    if x >= 0 and x <= minesweeper['size'] - 1 and y >= 0 and y <= minesweeper['size'] - 1:
        for diff in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            new_x = x + diff[0]
            new_y = y + diff[1]
            if new_x >= 0 and new_x <= minesweeper['size'] - 1 and new_y >= 0 and new_y <= minesweeper['size'] - 1:
                if minesweeper['board'][new_y][new_x][0]:
                    around += 1
    return around

def minesweeper_show_solution():
    """Show solution when game has ended."""
    global minesweeper
    for y, line in enumerate(minesweeper['board']):
        for x, status in enumerate(line):
            if status[1] != '*':
                if status[0]:
                    status[1] = '+'
                else:
                    number_around = minesweeper_number_around(x, y)
                    status[1] = '%d' % number_around

def minesweeper_all_flags_ok():
    global minesweeper
    number_ok = 0
    for x, line in enumerate(minesweeper['board']):
        for y, status in enumerate(line):
            if status[0] and status[1] == 'F':
                number_ok += 1
    return number_ok == minesweeper['mines'][minesweeper['size']]

def minesweeper_all_squares_explored():
    global minesweeper
    explored = 0
    for x, line in enumerate(minesweeper['board']):
        for y, status in enumerate(line):
            if status[1] == '*':
                return False
            if not status[0] and status[1].isdigit():
                explored += 1
    return explored == (minesweeper['size'] * minesweeper['size']) - minesweeper['mines'][minesweeper['size']]

def minesweeper_flag(x, y):
    """Add/remove flag."""
    global minesweeper
    status = minesweeper['board'][y][x]
    if status[1] in ' F':
        if status[1] == ' ':
            if minesweeper['flags'] == 0:
                return
            status[1] = 'F'
            minesweeper['flags'] -= 1
            if minesweeper['flags'] == 0 and minesweeper_all_flags_ok():
                minesweeper_end('win')
        else:
            status[1] = ' '
            minesweeper['flags'] += 1
        minesweeper_display()

def minesweeper_explore(x, y):
    """Explore!"""
    global minesweeper
    if not minesweeper['end'] and x >= 0 and x <= minesweeper['size'] - 1 and y >= 0 and y <= minesweeper['size'] - 1:
        status = minesweeper['board'][y][x]
        if status[1] == ' ':
            if status[0]:
                status[1] = '*'
                minesweeper_end('lose')
                minesweeper_show_solution()
            else:
                number_around = minesweeper_number_around(x, y)
                status[1] = '%d' % number_around
                if number_around == 0:
                    for diff in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
                        minesweeper_explore(x + diff[0], y + diff[1])

def minesweeper_cmd_cb(data, buffer, args):
    """The /minesweeper command."""
    global minesweeper
    if args in ('16col', '256col'):
        index = 0
        if args == '16col':
            index = 1
        for option, value in minesweeper_settings_default.items():
            if option.startswith('color_'):
                weechat.config_set_plugin(option, value[index])
                minesweeper_settings[option] = value[index]
        minesweeper_set_colors()
        minesweeper_display()
        return weechat.WEECHAT_RC_OK
    minesweeper_init()
    if minesweeper['buffer']:
        weechat.buffer_set(minesweeper['buffer'], 'display', '1')
    if not minesweeper['end']:
        if args == 'up':
            minesweeper['cursor'] = True
            if minesweeper['y'] > 0:
                minesweeper['y'] -= 1
                minesweeper_display()
        elif args == 'down':
            minesweeper['cursor'] = True
            if minesweeper['y'] < minesweeper['size'] - 1:
                minesweeper['y'] += 1
                minesweeper_display()
        elif args == 'left':
            minesweeper['cursor'] = True
            if minesweeper['x'] > 0:
                minesweeper['x'] -= 1
                minesweeper_display()
        elif args == 'right':
            minesweeper['cursor'] = True
            if minesweeper['x'] < minesweeper['size'] - 1:
                minesweeper['x'] += 1
                minesweeper_display()
        elif args == 'flag':
            minesweeper_timer_start()
            minesweeper['cursor'] = True
            minesweeper_flag(minesweeper['x'], minesweeper['y'])
        elif args == 'explore':
            minesweeper_timer_start()
            minesweeper['cursor'] = True
            minesweeper_explore(minesweeper['x'], minesweeper['y'])
            if not minesweeper['end'] and minesweeper_all_squares_explored():
                minesweeper_end('win')
            minesweeper_display()
    if args == 'new':
        minesweeper_new_game()
    elif args == 'zoom':
        if minesweeper['zoom'] < 1:
            minesweeper['zoom'] += 1
            minesweeper_display(True)
    elif args == 'dezoom':
        if minesweeper['zoom'] > 0:
            minesweeper['zoom'] -= 1
            minesweeper_display(True)
    elif args == 'cheat':
        minesweeper['cheat'] = not minesweeper['cheat']
        minesweeper_display()
    return weechat.WEECHAT_RC_OK

def minesweeper_mouse_cb(data, hsignal, hashtable):
    """Mouse callback."""
    global minesweeper
    if minesweeper['end']:
        minesweeper_new_game()
    else:
        minesweeper['cursor'] = False
        x = int(hashtable.get('_chat_line_x', '-1'))
        y = int(hashtable.get('_chat_line_y', '-1'))
        key = hashtable.get('_key', '')
        if x >= 0 and y >= 1:
            x = x // (4 + (minesweeper['zoom'] * 2))
            y = (y - 1) // (minesweeper['zoom'] + 2)
            if x >= 0 and x <= minesweeper['size'] - 1 and y >= 0 and y <= minesweeper['size'] - 1:
                minesweeper_timer_start()
                if key.startswith('button1'):
                    minesweeper_explore(x, y)
                    if not minesweeper['end'] and minesweeper_all_squares_explored():
                        minesweeper_end('win')
                    minesweeper_display()
                elif key.startswith('button2'):
                    minesweeper_flag(x, y)
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, '', ''):
        # set default settings
        version = weechat.info_get('version_number', '') or 0
        for option, value in minesweeper_settings_default.items():
            if weechat.config_is_set_plugin(option):
                minesweeper_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                minesweeper_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[2], value[0]))
        minesweeper_set_colors()

        # mouse support
        if int(version) >= 0x00030600:
            weechat.key_bind('mouse', minesweeper_mouse_keys)
            weechat.hook_hsignal('minesweeper_mouse', 'minesweeper_mouse_cb', '')

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'minesweeper_config_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND, 'Minesweeper game.', '[16col|256col]',
                             '16col: set colors using basic colors (if your terminal or your WeeChat does not support 256 colors)\n'
                             '256col: set colors using 256 colors mode (default)\n\n'
                             '256 colors mode is highly recommended (WeeChat >= 0.3.5).\n'
                             'Mouse is recommended (WeeChat >= 0.3.6).\n\n'
                             'Instructions:\n'
                             '- use mouse left button (or alt-space) to explore a square, if you think there is no mine under '
                             '(if there is a mine, you lose!)\n'
                             '- use mouse right button (or alt-f) to put/remove flag on square, if you think there is a mine under\n'
                             '- you win if you put all flags on mines, of if all squares without mine are explored.\n\n'
                             'Good luck!',
                             '16col|256col', 'minesweeper_cmd_cb', '')

        # if buffer already exists (after /upgrade), init minesweeper
        if weechat.buffer_search('python', 'minesweeper'):
            minesweeper_init()
