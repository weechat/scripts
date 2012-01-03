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
# Flood'it game for WeeChat.
# (mouse supported with WeeChat >= 0.3.6)
#
# History:
#
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: make script compatible with Python 3.x
# 2011-09-29, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: fix error on floodit buffer after /upgrade
# 2011-08-20, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add "q" (or "quit") to close floodit buffer
# 2011-08-20, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'floodit'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.4'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Flood\'it game'

SCRIPT_COMMAND = 'floodit'

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

floodit = {
    'buffer'   : '',
    'mode'     : 'single',
    'board'    : [],
    'sizes'    : { 14: 25, 21: 35, 28: 50 },
    'size'     : 14,
    'zoom'     : 1,
    'colors'   : [],
    'color'    : 0,
    'count'    : 0,
    'count_max': 25,
    'end'      : '',
    'timer'    : '',
}

# script options
floodit_settings_default = {
    'colors'           : ['blue,red,green,yellow,magenta,cyan', 'comma-separated list of 6 colors for squares'],
    'zoom'             : ['',                                   'zoom for board (0-N, empty means automatic zoom according to size of window)'],
}
floodit_settings = {}

# mouse keys
floodit_mouse_keys = { '@chat(python.floodit):button1': '/window ${_window_number};hsignal:floodit_mouse' }

def floodit_display(clear=False):
    """Display status and board."""
    global floodit
    if not floodit['buffer']:
        return
    if clear:
        weechat.buffer_clear(floodit['buffer'])
    spaces = ' ' * ((floodit['zoom'] + 1) * 2)
    str_line = ''
    for index, color in enumerate(floodit['colors']):
        str_select = [' ', ' ']
        if floodit['color'] == index:
            str_select = ['»', '«']
        str_line += '%s%s%s%s%s%s%s' % (weechat.color('white,default'),
                                        str_select[0],
                                        weechat.color(',%s' % color),
                                        spaces,
                                        weechat.color('white,default'),
                                        str_select[1],
                                        spaces[0:-2])
    str_status = ''
    str_end = ''
    if floodit['mode'] == 'single':
        board = copy.deepcopy(floodit['board'])
        floodit_flood_xy(board, 0, 0, board[0][0])
        percent = (floodit_count_color(board, -1) * 100) // (floodit['size'] * floodit['size'])
        str_status = '%2d/%d%s (%d%%)' % (floodit['count'], floodit['count_max'],
                                          weechat.color('chat'), percent)
        message_end = { 'win': '** CONGRATS! **', 'lose': '...GAME OVER!...' }
    elif floodit['mode'] == 'versus':
        colors = ['yellow', 'lightred']
        board = copy.deepcopy(floodit['board'])
        floodit_flood_xy(board, 0, 0, board[0][0])
        count_player = floodit_count_color(board, -1)
        board = copy.deepcopy(floodit['board'])
        floodit_flood_xy(board, floodit['size'] - 1, floodit['size'] - 1, board[floodit['size'] - 1][floodit['size'] - 1])
        count_computer = floodit_count_color(board, -1)
        if count_player == count_computer:
            colors[1] = 'yellow'
        elif count_computer > count_player:
            colors.reverse()
        str_status = '%sYou: %d%s / %sWee: %d' % (weechat.color(colors[0]), count_player,
                                                  weechat.color('default'),
                                                  weechat.color(colors[1]), count_computer)
        message_end = { 'win': '** YOU WIN! **', 'lose': '...You lose...', 'equality': 'Equality!' }
    str_end = '%s%s' % (weechat.color('white'), message_end.get(floodit['end'], ''))
    weechat.prnt_y(floodit['buffer'], 0, '%s %s %s' % (str_line, str_status, str_end))
    for i in range (0, floodit['zoom']):
        weechat.prnt_y(floodit['buffer'], 1 + i, str_line)
    weechat.prnt_y(floodit['buffer'], floodit['zoom'] + 1, '%s%s' % (weechat.color('blue'), '─' * (floodit['size'] * ((floodit['zoom'] + 1) * 2))))
    for y, line in enumerate(floodit['board']):
        str_line = ''
        for color in line:
            str_line += '%s%s' % (weechat.color(',%s' % floodit['colors'][color]), spaces)
        str_line += '%s' % weechat.color('chat')
        for i in range (0, floodit['zoom'] + 1):
            weechat.prnt_y(floodit['buffer'], floodit['zoom'] + 2 + (y * (floodit['zoom'] + 1)) + i, str_line)

def floodit_adjust_zoom():
    """Choose zoom according to size of window."""
    global floodit, floodit_settings
    floodit['zoom'] = -1
    if floodit_settings['zoom']:
        try:
            floodit['zoom'] = int(floodit_settings['zoom'])
        except:
            floodit['zoom'] = -1
    if floodit['zoom'] < 0:
        width = weechat.window_get_integer(weechat.current_window(), 'win_chat_width')
        height = weechat.window_get_integer(weechat.current_window(), 'win_chat_height')
        for i in range(10, -1, -1):
            if width >= floodit['size'] * ((i + 1) * 2) and height >= (floodit['size'] * (i + 1)) + i + 2:
                floodit['zoom'] = i
                break
    if floodit['zoom'] < 0:
        floodit['zoom'] = 0

def floodit_set_colors():
    """Set list of colors using settings."""
    global floodit, floodit_settings, floodit_settings_default
    floodit['colors'] = floodit_settings['colors'].split(',')
    if len(floodit['colors']) != 6:
        weechat.prnt('', '%sfloodit: invalid colors (list must have 6 colors)' % weechat.prefix('error'))
        floodit['colors'] = floodit_settings_default['colors'][0].split(',')

def floodit_config_cb(data, option, value):
    """Called when a script option is changed."""
    global floodit_settings
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in floodit_settings:
            floodit_settings[name] = value
            if name == 'colors':
                floodit_set_colors()
            elif name == 'zoom':
                floodit_adjust_zoom()
    floodit_display()
    return weechat.WEECHAT_RC_OK

def floodit_new_game():
    """Create a new game: initialize board and some variables."""
    global floodit
    floodit['board'] = []
    for y in range(0, floodit['size']):
        line = []
        for x in range(0, floodit['size']):
            line.append(random.randint(0, 5))
        floodit['board'].append(line)
    if floodit['mode'] == 'versus':
        floodit['board'][floodit['size'] - 1][floodit['size'] - 1] = floodit['board'][0][0]
    floodit['color'] = 0
    floodit['count'] = 0
    floodit['end'] = ''
    floodit_display()

def floodit_change_size(add):
    """Change size of board."""
    global floodit
    keys = sorted(floodit['sizes'])
    index = keys.index(floodit['size']) + add
    if index >= 0 and index < len(keys):
        floodit['size'] = keys[index]
        floodit['count_max'] = floodit['sizes'][floodit['size']]
        weechat.buffer_clear(floodit['buffer'])
        floodit_adjust_zoom()
        floodit_new_game()

def floodit_timer_cb(data, remaining_calls):
    """Timer for demo mode."""
    global floodit
    floodit['color'] = floodit_find_best(0, 0)
    floodit_user_flood()
    if floodit['end']:
        weechat.unhook(floodit['timer'])
        floodit['timer'] = ''
    return weechat.WEECHAT_RC_OK

def floodit_input_buffer(data, buffer, input):
    """Input data in floodit buffer."""
    global floodit
    if input:
        args = input.split(' ')
        if args[0] in ('d', 'demo'):
            if not floodit['timer']:
                delay = 500
                if len(args) > 1:
                    try:
                        delay = int(args[1])
                    except:
                        delay = 500
                if delay <= 0:
                    delay = 1
                if floodit['end']:
                    floodit_new_game()
                floodit['timer'] = weechat.hook_timer(delay, 0, 0, 'floodit_timer_cb', '')
        elif args[0] in ('s', 'single'):
            floodit['mode'] = 'single'
            floodit_new_game()
        elif args[0] in ('v', 'versus'):
            floodit['mode'] = 'versus'
            floodit_new_game()
        elif args[0] in ('n', 'new'):
            floodit_new_game()
        elif args[0] in ('q', 'quit'):
            weechat.buffer_close(floodit['buffer'])
        elif args[0] == '+':
            floodit_change_size(+1)
        elif args[0] == '-':
            floodit_change_size(-1)
    return weechat.WEECHAT_RC_OK

def floodit_close_buffer(data, buffer):
    """Called when floodit buffer is closed."""
    global floodit
    if floodit['timer']:
        weechat.unhook(floodit['timer'])
        floodit['timer'] = ''
    floodit['buffer'] = ''
    return weechat.WEECHAT_RC_OK

def floodit_init():
    """Init floodit: create buffer, adjust zoom, new game."""
    global floodit, floodit_settings
    if floodit['buffer']:
        return
    floodit['buffer'] = weechat.buffer_search('python', 'floodit')
    if not floodit['buffer']:
        floodit['buffer'] = weechat.buffer_new('floodit', 'floodit_input_buffer', '', 'floodit_close_buffer', '')
        if floodit['buffer']:
            weechat.buffer_set(floodit['buffer'], 'type', 'free')
            weechat.buffer_set(floodit['buffer'], 'title',
                               'Flood it! | alt-f or mouse: flood, alt-n: new game, alt-+/-: adjust board zoom | '
                               'Command line: (n)ew, (s)ingle, (v)ersus, (d)emo (+delay), +/-: change size, (q)uit')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta2-D', '/floodit left')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta2-C', '/floodit right')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta-f',  '/floodit flood')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta-n',  '/floodit new')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta-+',  '/floodit zoom')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta--',  '/floodit dezoom')
            weechat.buffer_set(floodit['buffer'], 'key_bind_meta-C',  '/floodit computer')
    if floodit['buffer']:
        floodit_adjust_zoom()
        floodit_new_game()

def floodit_flood_xy(board, x, y, color):
    """Flood a board at (x,y) with color."""
    global floodit
    board[y][x] = -1
    if y > 0 and board[y-1][x] == color:
        floodit_flood_xy(board, x, y - 1, color)
    if y < floodit['size'] - 1 and board[y+1][x] == color:
        floodit_flood_xy(board, x, y + 1, color)
    if x > 0 and board[y][x-1] == color:
        floodit_flood_xy(board, x - 1, y, color)
    if x < floodit['size'] - 1 and board[y][x+1] == color:
        floodit_flood_xy(board, x + 1, y, color)

def floodit_flood_end(board, color):
    """End of flood: replace the -1 by color."""
    for y, line in enumerate(board):
        for x, c in enumerate(line):
            if c == -1:
                board[y][x] = color

def floodit_count_color(board, color):
    """Count number of times a color is used in board."""
    global floodit
    count = 0
    for line in board:
        count += line.count(color)
    return count

def floodit_flood(x, y, color):
    """Flood board at (x,y) with color, and check if game has ended."""
    global floodit
    floodit_flood_xy(floodit['board'], x, y, floodit['board'][y][x])
    floodit_flood_end(floodit['board'], color)
    floodit['count'] += 1
    if floodit['mode'] == 'single':
        if floodit_count_color(floodit['board'], floodit['board'][0][0]) == floodit['size'] * floodit['size']:
            floodit['end'] = 'win'
        elif floodit['count'] == floodit['count_max']:
            floodit['end'] = 'lose'
    elif floodit['mode'] == 'versus':
        board = copy.deepcopy(floodit['board'])
        floodit_flood_xy(board, 0, 0, board[0][0])
        count1 = floodit_count_color(board, -1)
        board = copy.deepcopy(floodit['board'])
        floodit_flood_xy(board, floodit['size'] - 1, floodit['size'] - 1, board[floodit['size'] - 1][floodit['size'] - 1])
        count2 = floodit_count_color(board, -1)
        if count1 + count2 == floodit['size'] * floodit['size']:
            if count1 > count2:
                floodit['end'] = 'win'
            elif count1 < count2:
                floodit['end'] = 'lose'
            else:
                floodit['end'] = 'equality'
    floodit_display()

def floodit_build_combs(combs, curlist, maxsize, excludecolor):
    """Build list of combinations to try for computer AI."""
    global floodit
    if len(curlist) >= maxsize:
        combs.append(curlist)
    else:
        curlist.append(-1)
        colors = list(range(0, len(floodit['colors'])))
        random.shuffle(colors)
        for i in colors:
            if i == excludecolor:
                continue
            if i != curlist[-2]:
                curlist[-1] = i
                floodit_build_combs(combs, list(curlist), maxsize, excludecolor)

def floodit_compare_scores(scores1, scores2):
    """Compare two list of scores."""
    sum1 = sum(scores1)
    sum2 = sum(scores2)
    if sum1 > sum2:
        return 1
    elif sum1 < sum2:
        return -1
    else:
        if scores1 > scores2:
            return 1
        elif scores1 < scores2:
            return -1
        else:
            return 0

def floodit_find_best(x, y):
    """Find best color for (x,y) (computer AI)."""
    global floodit
    combs = []
    excludecolor = -1
    if floodit['mode'] == 'versus':
        if x == 0:
            excludecolor = floodit['board'][floodit['size'] - 1][floodit['size'] - 1]
        else:
            excludecolor = floodit['board'][0][0]
    floodit_build_combs(combs, [floodit['board'][y][x]], 3, excludecolor)
    bestscores = []
    bestcolor = 0
    for comb in combs:
        board = copy.deepcopy(floodit['board'])
        scores = []
        for color in comb[1:]:
            floodit_flood_xy(board, x, y, board[y][x])
            floodit_flood_end(board, color)
            floodit_flood_xy(board, x, y, board[y][x])
            scores.append(floodit_count_color(board, -1))
            floodit_flood_end(board, color)
        if floodit_compare_scores(scores, bestscores) > 0:
            bestscores = scores
            bestcolor = comb[1]
    return bestcolor

def floodit_user_flood():
    """Action flood from user, and then computer plays if mode is 'versus'."""
    global floodit
    if floodit['color'] != floodit['board'][0][0]:
        if floodit['mode'] != 'versus' or floodit['color'] != floodit['board'][floodit['size'] - 1][floodit['size'] - 1]:
            floodit_flood(0, 0, floodit['color'])
            if floodit['mode'] == 'versus' and not floodit['end']:
                floodit_flood(floodit['size'] - 1,
                              floodit['size'] - 1,
                              floodit_find_best(floodit['size'] - 1, floodit['size'] - 1))

def floodit_cmd_cb(data, buffer, args):
    """The /floodit command."""
    global floodit
    if args in ('single', 'versus'):
        floodit['mode'] = args
    floodit_init()
    if floodit['buffer']:
        weechat.buffer_set(floodit['buffer'], 'display', '1')
    if not floodit['end']:
        if args == 'left':
            if floodit['color'] > 0:
                floodit['color'] -= 1
            else:
                floodit['color'] = len(floodit['colors']) - 1
            floodit_display()
        elif args == 'right':
            if floodit['color'] < len(floodit['colors']) - 1:
                floodit['color'] += 1
            else:
                floodit['color'] = 0
            floodit_display()
        elif args == 'flood':
            floodit_user_flood()
        elif args == 'computer':
            floodit['color'] = floodit_find_best(0, 0)
            floodit_user_flood()
    if args == 'new':
        floodit_new_game()
    elif args == 'zoom':
        floodit['zoom'] += 1
        floodit_display(True)
    elif args == 'dezoom':
        if floodit['zoom'] > 0:
            floodit['zoom'] -= 1
            floodit_display(True)
    return weechat.WEECHAT_RC_OK

def floodit_mouse_cb(data, hsignal, hashtable):
    """Mouse callback."""
    global floodit
    if not floodit['end']:
        x = int(hashtable.get('_chat_line_x', '-1'))
        y = int(hashtable.get('_chat_line_y', '-1'))
        if x >= 0 and y >= 0:
            color = -1
            if y <= floodit['zoom']:
                multiplier = (floodit['zoom'] + 1) * 4
                add = 2 + ((floodit['zoom'] + 1) * 2)
                for i in range (0, len(floodit['colors'])):
                    if x >= i * multiplier and x < (i * multiplier) + add:
                        color = i
                        break
            elif y >= floodit['zoom'] + 2:
                x = x // ((floodit['zoom'] + 1) * 2)
                y = (y - floodit['zoom'] - 2) // (floodit['zoom'] + 1)
                if y < floodit['size'] and x < floodit['size']:
                    color = floodit['board'][y][x]
            if color >= 0:
                floodit['color'] = color
                floodit_user_flood()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, '', ''):
        # set default settings
        version = weechat.info_get("version_number", "") or 0
        for option, value in floodit_settings_default.items():
            if weechat.config_is_set_plugin(option):
                floodit_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                floodit_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        floodit_set_colors()

        # mouse support
        if int(version) >= 0x00030600:
            weechat.key_bind('mouse', floodit_mouse_keys)
            weechat.hook_hsignal('floodit_mouse', 'floodit_mouse_cb', '')

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'floodit_config_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND, 'Flood''it game.', '[single|versus]',
                             'single: play in single mode (default)\n'
                             'versus: play versus computer\n\n'
                             'Single mode:\n'
                             '- Choose a color for the upper left square, this will paint '
                             'this square and all squares next to this one (having same color) '
                             'with your color.\n'
                             '- You win if all squares are same color.\n'
                             '- Maximum number of floods is 25, 35 or 50 (according to size).\n\n'
                             'Versus mode:\n'
                             '- You paint the upper left square, WeeChat paints bottom right.\n'
                             '- You can not paint with last color used by WeeChat.\n'
                             '- Game ends when neither you nor WeeChat can paint new squares any more.\n'
                             '- You win if you have more squares of your color than WeeChat.',
                             'single|versus', 'floodit_cmd_cb', '')

        # if buffer already exists (after /upgrade), init floodit
        if weechat.buffer_search('python', 'floodit'):
            floodit_init()
