# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Sebastien Helleu <flashcode@flashtux.org>
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
# Samegame for WeeChat (http://en.wikipedia.org/wiki/SameGame).
# (requires WeeChat >= 0.3.6)
#
# History:
#
# 2012-03-16, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add undo key and bonus +1000 when all blocks are removed
# 2012-03-16, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'samegame'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.2'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Samegame'

SCRIPT_COMMAND = 'samegame'

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

samegame = {
    'buffer'    : '',
    'board'     : [],
    'sizes'     : ((15, 10), (25, 17)),
    'size'      : (15, 10),
    'zoom'      : 1,
    'colors'    : [],
    'numcolors' : 3,
    'score'     : 0,
    'end'       : '',
    'timer'     : '',
    'board_undo': None,
    'score_undo': 0,
}

# script options
samegame_settings_default = {
    'colors'   : ['blue,red,green,yellow,magenta,cyan', 'comma-separated list of 6 colors for blocks'],
    'numcolors': ['3',                                  'number of colors to use for blocks (3-6)'],
    'zoom'     : ['',                                   'zoom for board (0-N, empty means automatic zoom according to size of window)'],
    'speed'    : ['40',                                 'speed of animation when blocks are falling and columns are trimmed away (0 = immediate, 500 = slow animation'],
}
samegame_settings = {}

# mouse keys
samegame_mouse_keys = { '@chat(python.samegame):button1': '/window ${_window_number};hsignal:samegame_mouse' }

def samegame_display(clear=False):
    """Display status and board."""
    global samegame
    if not samegame['buffer']:
        return
    if clear:
        weechat.buffer_clear(samegame['buffer'])
    spaces = ' ' * ((samegame['zoom'] + 1) * 2)

    # display status
    str_status = 'Board: %s%dx%d%s    Colors: %s%d%s    Score: %s%d' % (weechat.color('white'), samegame['size'][0], samegame['size'][1],
                                                                        weechat.color('chat'),
                                                                        weechat.color('white'), samegame['numcolors'],
                                                                        weechat.color('chat'),
                                                                        weechat.color('white'), samegame['score'])
    str_end = '%s%s' % (weechat.color('white'), samegame['end'])
    weechat.prnt_y(samegame['buffer'], 0, '%s    %s' % (str_status, str_end))

    # display board
    weechat.prnt_y(samegame['buffer'], 1, '%s┌%s┐' % (weechat.color('chat'), '─' * (samegame['size'][0] * ((samegame['zoom'] + 1) * 2))))
    for y, line in enumerate(samegame['board']):
        str_line = '│'
        for color in line:
            if color < 0:
                str_color = 'default'
            else:
                str_color = samegame['colors'][color]
            str_line += '%s%s' % (weechat.color(',%s' % str_color), spaces)
        str_line += '%s│' % weechat.color('chat')
        for i in range (0, samegame['zoom'] + 1):
            weechat.prnt_y(samegame['buffer'], 2 + (y * (samegame['zoom'] + 1)) + i, str_line)
    weechat.prnt_y(samegame['buffer'], 1 + (samegame['size'][1] * (samegame['zoom'] + 1)) + 1,
                   '%s└%s┘' % (weechat.color('chat'), '─' * (samegame['size'][0] * ((samegame['zoom'] + 1) * 2))))

def samegame_adjust_zoom():
    """Choose zoom according to size of window."""
    global samegame, samegame_settings
    samegame['zoom'] = -1
    if samegame_settings['zoom']:
        try:
            samegame['zoom'] = int(samegame_settings['zoom'])
        except:
            samegame['zoom'] = -1
    if samegame['zoom'] < 0:
        width = weechat.window_get_integer(weechat.current_window(), 'win_chat_width')
        height = weechat.window_get_integer(weechat.current_window(), 'win_chat_height')
        for i in range(10, -1, -1):
            if width >= samegame['size'][0] * ((i + 1) * 2) + 2 and height >= (samegame['size'][1] * (i + 1)) + 3:
                samegame['zoom'] = i
                break
    if samegame['zoom'] < 0:
        samegame['zoom'] = 0

def samegame_set_colors():
    """Set list of colors using settings."""
    global samegame, samegame_settings, samegame_settings_default
    samegame['colors'] = samegame_settings['colors'].split(',')
    if len(samegame['colors']) != 6:
        weechat.prnt('', '%ssamegame: invalid colors (list must have 6 colors)' % weechat.prefix('error'))
        samegame['colors'] = samegame_settings_default['colors'][0].split(',')

def samegame_config_cb(data, option, value):
    """Called when a script option is changed."""
    global samegame, samegame_settings
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in samegame_settings:
            samegame_settings[name] = value
            if name == 'colors':
                samegame_set_colors()
            elif name == 'numcolors':
                try:
                    samegame['numcolors'] = int(value)
                except:
                    pass
            elif name == 'zoom':
                samegame_adjust_zoom()
    samegame_display()
    return weechat.WEECHAT_RC_OK

def samegame_new_game():
    """Create a new game: initialize board and some variables."""
    global samegame
    samegame['board'] = []
    for y in range(0, samegame['size'][1]):
        line = []
        for x in range(0, samegame['size'][0]):
            line.append(random.randint(0, samegame['numcolors'] - 1))
        samegame['board'].append(line)
    samegame['score'] = 0
    samegame['end'] = ''
    samegame_display()

def samegame_change_size(add):
    """Change size of board."""
    global samegame
    keys = sorted(samegame['sizes'])
    index = keys.index(samegame['size']) + add
    if index >= 0 and index < len(keys):
        samegame['size'] = keys[index]
        weechat.buffer_clear(samegame['buffer'])
        samegame_adjust_zoom()
        samegame_new_game()

def samegame_input_buffer(data, buffer, input):
    """Input data in samegame buffer."""
    global samegame
    if input:
        args = input.split(' ')
        if args[0] in ('n', 'new'):
            samegame_new_game()
        elif args[0] in ('q', 'quit'):
            weechat.buffer_close(samegame['buffer'])
        elif args[0] == '+':
            samegame_change_size(+1)
        elif args[0] == '-':
            samegame_change_size(-1)
        elif args[0].isdigit():
            numcolors = int(args[0])
            if numcolors >= 3 and numcolors <= 6:
                samegame['numcolors'] = numcolors
                samegame_new_game()
    return weechat.WEECHAT_RC_OK

def samegame_close_buffer(data, buffer):
    """Called when samegame buffer is closed."""
    global samegame
    if samegame['timer']:
        weechat.unhook(samegame['timer'])
        samegame['timer'] = ''
    samegame['buffer'] = ''
    return weechat.WEECHAT_RC_OK

def samegame_init():
    """Init samegame: create buffer, adjust zoom, new game."""
    global samegame, samegame_settings
    if samegame['buffer']:
        return
    samegame['buffer'] = weechat.buffer_search('python', 'samegame')
    if not samegame['buffer']:
        samegame['buffer'] = weechat.buffer_new('samegame', 'samegame_input_buffer', '', 'samegame_close_buffer', '')
        if samegame['buffer']:
            weechat.buffer_set(samegame['buffer'], 'type', 'free')
            weechat.buffer_set(samegame['buffer'], 'title',
                               'Samegame | mouse: play, alt-n: new game, alt-+/-: adjust board zoom, alt-u: undo | '
                               'Command line: (n)ew, +/-: change size, (q)uit, 3-6: number of colors')
            weechat.buffer_set(samegame['buffer'], 'key_bind_meta-n',  '/samegame new')
            weechat.buffer_set(samegame['buffer'], 'key_bind_meta-+',  '/samegame zoom')
            weechat.buffer_set(samegame['buffer'], 'key_bind_meta--',  '/samegame dezoom')
            weechat.buffer_set(samegame['buffer'], 'key_bind_meta-u',  '/samegame undo')
    try:
        samegame['numcolors'] = int(samegame_settings['numcolors'])
    except:
        pass
    if samegame['numcolors'] < 3:
        samegame['numcolors'] = 3
    if samegame['numcolors'] > 6:
        samegame['numcolors'] = 6
    if samegame['buffer']:
        samegame_adjust_zoom()
        samegame_new_game()

def samegame_play_xy(board, x, y):
    """Play at (x,y) and return number of blocks removed."""
    color = board[y][x]
    count = 1
    board[y][x] = -1
    if y > 0 and board[y-1][x] == color:
        count += samegame_play_xy(board, x, y - 1)
    if y < samegame['size'][1] - 1 and board[y+1][x] == color:
        count += samegame_play_xy(board, x, y + 1)
    if x > 0 and board[y][x-1] == color:
        count += samegame_play_xy(board, x - 1, y)
    if x < samegame['size'][0] - 1 and board[y][x+1] == color:
        count += samegame_play_xy(board, x + 1, y)
    return count

def samegame_column_is_empty(x):
    """Return True if a column is empty."""
    global samegame
    count = 0
    for y in range(0, samegame['size'][1]):
        if samegame['board'][y][x] < 0:
            count += 1
    return (count == samegame['size'][1])

def samegame_collapse_blocks():
    """Collapse blocks."""
    global samegame
    columns = []
    for x in range(0, samegame['size'][0]):
        for y in range(0, samegame['size'][1] - 1):
            if samegame['board'][y][x] >= 0 and samegame['board'][y+1][x] < 0:
                columns.append(x)
                break
    if columns:
        for x in columns:
            for y in range(samegame['size'][1] - 1, 0, -1):
                if samegame['board'][y][x] < 0 and samegame['board'][y-1][x] >= 0:
                    samegame['board'][y][x] = samegame['board'][y-1][x]
                    samegame['board'][y-1][x] = -1
        return True
    for x in range(0, samegame['size'][0] - 1):
        if samegame_column_is_empty(x) and not samegame_column_is_empty(x + 1):
            for x2 in range(x, samegame['size'][0] - 1):
                for y in range(0, samegame['size'][1]):
                    samegame['board'][y][x2] = samegame['board'][y][x2+1]
            for y in range(0, samegame['size'][1]):
                samegame['board'][y][samegame['size'][0]-1] = -1
            return True
    return False

def samegame_count_color(board, color):
    """Count number of times a color is used in board."""
    count = 0
    for line in board:
        count += line.count(color)
    return count

def samegame_check_end():
    """Check if the game has ended (play is not possible with remaining blocks)."""
    global samegame
    board = copy.deepcopy(samegame['board'])
    for x in range(0, samegame['size'][0]):
        for y in range(0, samegame['size'][1]):
            if board[y][x] >= 0:
                if samegame_play_xy(board, x, y) >= 2:
                    return False
    samegame['end'] = 'End of game!'
    blocks_remaining = (samegame['size'][0] * samegame['size'][1]) - samegame_count_color(samegame['board'], -1)
    if blocks_remaining == 0:
        samegame['end'] += '  ** CONGRATS! **'
        samegame['score'] += 1000
    else:
        samegame['end'] += '  (%d blocks remaining)' % blocks_remaining
    return True

def samegame_timer_cb(data, remaining_calls):
    """Timer for animation (blocks falling)."""
    global samegame
    if samegame_collapse_blocks():
        samegame_display()
    else:
        weechat.unhook(samegame['timer'])
        samegame['timer'] = ''
        if samegame_check_end():
            samegame_display()
    return weechat.WEECHAT_RC_OK

def samegame_play(x, y):
    """Play at (x,y), and check if game has ended."""
    global samegame, samegame_settings
    if samegame['board'][y][x] < 0:
        return
    board = copy.deepcopy(samegame['board'])
    count = samegame_play_xy(board, x, y)
    if count < 2:
        return
    samegame['board_undo'] = copy.deepcopy(samegame['board'])
    samegame['score_undo'] = samegame['score']
    count = samegame_play_xy(samegame['board'], x, y)
    samegame['score'] += (count - 1) ** 2
    delay = 50
    try:
        delay = int(samegame_settings['speed'])
    except:
        delay = 50
    if delay < 0:
        delay = 0
    elif delay > 500:
        delay = 500
    if delay == 0:
        while samegame_collapse_blocks():
            pass
        samegame_check_end()
    else:
        samegame['timer'] = weechat.hook_timer(delay, 0, 0, 'samegame_timer_cb', '')
    samegame_display()
    return

def samegame_cmd_cb(data, buffer, args):
    """The /samegame command."""
    global samegame
    samegame_init()
    if samegame['buffer']:
        weechat.buffer_set(samegame['buffer'], 'display', '1')
    if args == 'new':
        samegame_new_game()
    elif args == 'zoom':
        samegame['zoom'] += 1
        samegame_display(True)
    elif args == 'dezoom':
        if samegame['zoom'] > 0:
            samegame['zoom'] -= 1
            samegame_display(True)
    if not samegame['end']:
        if args == 'undo':
            if samegame['board_undo']:
                samegame['board'] = copy.deepcopy(samegame['board_undo'])
                samegame['board_undo'] = None
                samegame['score'] = samegame['score_undo']
                samegame['score_undo'] = 0
                samegame_display()
    return weechat.WEECHAT_RC_OK

def samegame_mouse_cb(data, hsignal, hashtable):
    """Mouse callback."""
    global samegame
    if not samegame['end'] and not samegame['timer']:
        x = int(hashtable.get('_chat_line_x', '-1'))
        y = int(hashtable.get('_chat_line_y', '-1'))
        if x >= 0 and y >= 0:
            color = -1
            if y >= 2:
                x = x // ((samegame['zoom'] + 1) * 2)
                y = (y - 2) // (samegame['zoom'] + 1)
                if y < samegame['size'][1] and x < samegame['size'][0]:
                    color = samegame['board'][y][x]
            if color >= 0:
                samegame_play(x, y)
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, '', ''):
        # set default settings
        for option, value in samegame_settings_default.items():
            if weechat.config_is_set_plugin(option):
                samegame_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                samegame_settings[option] = value[0]
            weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        samegame_set_colors()

        # mouse support
        weechat.key_bind('mouse', samegame_mouse_keys)
        weechat.hook_hsignal('samegame_mouse', 'samegame_mouse_cb', '')

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'samegame_config_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND, 'Samegame.', '',
                             'Instructions:\n'
                             '- click on a group of adjoining blocks of the same color to remove them from the screen\n'
                             '- blocks that are no longer supported will fall down, and a column without any blocks will be trimmed away by other columns sliding to the left\n'
                             '- your score is increased by (N-1)², where N is the number of blocks removed by your click\n'
                             '- the game ends when you can not play any more.',
                             '', 'samegame_cmd_cb', '')

        # if buffer already exists (after /upgrade), init samegame
        if weechat.buffer_search('python', 'samegame'):
            samegame_init()
