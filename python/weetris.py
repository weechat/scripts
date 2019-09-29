# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2019 Sébastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2009 drubin <drubin [@] smartcube [dot] co[dot]za>
# Copyright (C) 2010-2011 Trashlord <dornenreich666@gmail.com>
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

# Tetris game for WeeChat.
#
# History:
#
# 2019-09-29, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.0:
#       - convert script from Perl to Python
#       - use 256 colors if available
#       - use original Tetris colors for pieces
#       - add input action "q" to close weetris buffer
#       - display next piece (new option "display_next_piece")
#       - add key ctrl-down: move to bottom (new option "key_down_slow")
# 2011-02-28, Trashlord <dornenreich666@gmail.com>:
#     version 0.9: add playing time display
# 2010-10-08, Trashlord <dornenreich666@gmail.com>:
#     version 0.8: add best score and best level statistics
# 2009-12-17, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.7: add levels, fix bugs with pause
# 2009-12-16, drubin <drubin [@] smartcube [dot] co[dot]za>:
#     version 0.6: add key for pause, basic doc and auto jump to buffer
# 2009-06-21, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.5: fix bug with weetris buffer after /upgrade
# 2009-05-02, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.4: sync with last API changes, fix problem with key alt-n
# 2008-11-14, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.3: minor code cleanup
# 2008-11-12, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.2: hook timer only when weetris buffer is open
# 2008-11-05, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-04-30, Sébastien Helleu <flashcode@flashtux.org>:
#     script creation

"""Tetris game for WeeChat, yeah!"""

from __future__ import print_function

SCRIPT_NAME = 'weetris'
SCRIPT_AUTHOR = 'Sébastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '1.0'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Tetris game for WeeChat, yeah!'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://weechat.org/')
    import_ok = False

try:
    import random
    import time
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

BUFFER_TITLE = ('%s %s - enjoy!  |  '
                'Keys: arrows: move/rotate (ctrl-down: bottom), '
                'alt-N: new game, alt-P: pause  |  '
                'Input: q = quit' % (SCRIPT_NAME, SCRIPT_VERSION))

GAME_WIDTH = 10
GAME_HEIGHT = 20

MAX_LEVEL = 10

START_Y = 0

PIECES = (
    1024+512+64+32,     # O
    2048+1024+512+256,  # I
    2048+1024+512+64,   # T
    2048+1024+512+128,  # L
    2048+1024+512+32,   # J
    1024+512+128+64,    # S
    2048+1024+64+32,    # Z
)
PIECE_COLOR = {
    # < 256 colors
    False: [
        'yellow',     # O
        'lightcyan',  # I
        'magenta',    # T
        'brown',      # L
        'blue',       # J
        'green',      # S
        'red',        # Z

    ],
    # >= 256 colors
    True: [
        'yellow',     # O
        'lightcyan',  # I
        'magenta',    # T
        '172',        # L
        'blue',       # J
        'green',      # S
        'red',        # Z
    ],
}
PIECE_X_INC = (3, 2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0)
PIECE_Y_INC = (3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0)
PIECE_ROTATION = (
    4096, 256, 16, 1,
    8192, 512, 32, 2,
    16384, 1024, 64, 4,
    32768, 2048, 128, 8,
)

# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# |32768|16384| 8192| 4096|          |  8  | 128 | 2048|32768|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# | 2048| 1024| 512 | 256 |          |  4  |  64 | 1024|16384|
# |     |     |     |     |  after   |     |     |     |     |
# -------------------------  rotate  -------------------------
# |     |     |     |     |   ===>   |     |     |     |     |
# | 128 |  64 |  32 |  16 |          |  2  |  32 | 512 | 8192|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# |  8  |  4  |  2  |  1  |          |  1  |  16 | 256 | 4096|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------

weetris = {
    # will be set to True if 256 colors are supported by the terminal
    '256colors': False,
    'buffer': '',
    'timer': '',
    'level': 1,
    'matrix': [],
    'matrix_next': [],
    'playing': False,
    'paused': False,
    'lines': 0,
    'piece_x': 0,
    'piece_y': 0,
    'piece_number': -1,
    'next_piece_number': -1,
    'piece_form': 0,
    'best_level': 1,
    'best_lines': 0,
    'play_start_time': 0,
    'time_display_timer': '',
}

# script options
weetris_settings_default = {
    'display_next_piece': (
        'on',
        'display the next piece',
    ),
    'key_down_slow': (
        'on',
        'the key "down" moves the piece slowly: one position, and ctrl-down '
        'mores directly to the bottom; if disabled, the two keys are '
        'reversed',
    ),
}
weetris_settings = {}


def weetris_config_cb(data, option, value):
    """Called when a script option is changed."""
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in weetris_settings:
            weetris_settings[name] = value
    return weechat.WEECHAT_RC_OK


def buffer_input_cb(data, buf, input_data):
    """Input on weetris buffer."""
    if input_data == 'q':
        weechat.buffer_close(weetris['buffer'])
    return weechat.WEECHAT_RC_OK


def buffer_close_cb(data, buf):
    """Weetris buffer closed (oh no, why?)."""
    weetris['buffer'] = ''
    if weetris['timer']:
        weechat.unhook(weetris['timer'])
        weetris['timer'] = ''
    if weetris['time_display_timer']:
        weechat.unhook(weetris['time_display_timer'])
        weetris['play_start_time'] = 0
        weetris['time_display_timer'] = ''
    weechat.prnt('', 'Thank you for playing WeeTris!')
    return weechat.WEECHAT_RC_OK


def get_piece_block(value):
    """
    Return a string with a single block of a piece
    (spaces with background color).
    """
    if value < 0:
        block = weechat.color(',default')
    else:
        block = weechat.color(',' + PIECE_COLOR[weetris['256colors']][value])
    return block + '  '


def display_line(y):
    """Display a line of the matrix."""
    line = ' │'
    if weetris['paused']:
        if y == GAME_HEIGHT // 2:
            spaces_before = ((GAME_WIDTH * 2) - 6) // 2
            spaces_after = (GAME_WIDTH * 2) - 6 - spaces_before
            line += (' ' * spaces_before) + 'PAUSED' + (' ' * spaces_after)
        else:
            line += '  ' * GAME_WIDTH
    else:
        for x in range(GAME_WIDTH):
            line += get_piece_block(weetris['matrix'][y][x])
    line += weechat.color(',default') + '│'
    if weetris['playing'] and weetris_settings['display_next_piece'] == 'on':
        if y == 0:
            line += '    Next: '
        elif 1 <= y <= 4:
            line += '    '
            for x in range(4):
                line += get_piece_block(weetris['matrix_next'][y - 1][x])
            line += weechat.color(',default')
    weechat.prnt_y(weetris['buffer'], START_Y + y + 1, line)


def weetris_display_playing_time_cb(data, remaining_calls):
    """Callback of timer to display the playing time."""
    total_seconds = time.time() - weetris['play_start_time']
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    total_seconds += 1
    weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 6,
                   ' Playing time : %02d:%02d' % (minutes, seconds))
    return weechat.WEECHAT_RC_OK


def display_level_lines():
    """Display the current level and number of lines."""
    list_info = [
        'Level %-3d %6d line%s' % (weetris['level'],
                                   weetris['lines'],
                                   's' if weetris['lines'] > 1 else ''),
        '-' * (1 + (GAME_WIDTH * 2) + 1),
        'Highest level: %d' % weetris['best_level'],
        'Max lines    : %d' % weetris['best_lines'],
    ]
    for y, info in enumerate(list_info):
        weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 2 + y,
                       ' ' + info)


def display_piece(display):
    """Display (or hide) the current piece."""
    value = weetris['piece_number'] if display else -1
    for i in range(16):
        if weetris['piece_form'] & (1 << i):
            x2 = weetris['piece_x'] + PIECE_X_INC[i]
            y2 = weetris['piece_y'] + PIECE_Y_INC[i]
            weetris['matrix'][y2][x2] = value


def display_all():
    """Display everything on the weetris buffer."""
    display_piece(True)
    weechat.prnt_y(weetris['buffer'], START_Y,
                   ' ┌' + ('──' * GAME_WIDTH) + '┐')
    for y in range(GAME_HEIGHT):
        display_line(y)
    weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 1,
                   ' └' + ('──' * GAME_WIDTH) + '┘')
    display_piece(False)


def random_piece():
    """Return a random piece number."""
    return random.randint(0, len(PIECES) - 1)


def set_matrix_next():
    """Set the matrix for the next piece."""
    weetris['matrix_next'] = [[-1] * 4 for i in range(4)]
    number = weetris['next_piece_number']
    form = PIECES[number]
    for i in range(16):
        if form & (1 << i):
            weetris['matrix_next'][PIECE_Y_INC[i]][PIECE_X_INC[i]] = number


def set_new_form():
    """Choose a new random form."""
    if weetris['next_piece_number'] < 0:
        weetris['next_piece_number'] = random_piece()
    weetris['piece_number'] = weetris['next_piece_number']
    weetris['next_piece_number'] = random_piece()
    set_matrix_next()
    weetris['piece_form'] = PIECES[weetris['piece_number']]
    weetris['piece_x'] = (GAME_WIDTH // 2) - 2
    weetris['piece_y'] = 0


def init_timer():
    """Initialize timer."""
    if weetris['timer']:
        weechat.unhook(weetris['timer'])
    delay = max(100, 700 - ((weetris['level'] - 1) * 60))
    weetris['timer'] = weechat.hook_timer(delay, 0, 0, 'weetris_timer_cb', '')


def new_game():
    """New game."""
    weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 2, '')
    weetris['matrix'] = [[-1] * GAME_WIDTH for i in range(GAME_HEIGHT)]
    weetris['next_piece_number'] = -1
    set_new_form()
    weetris['playing'] = True
    weetris['paused'] = False
    weetris['lines'] = 0
    weetris['level'] = 1
    weetris['play_start_time'] = time.time()
    weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 6,
                   ' Playing time : 00:00')
    init_timer()
    weetris['time_display_timer'] = weechat.hook_timer(
        1000, 0, 0,
        'weetris_display_playing_time_cb', '',
    )
    display_all()
    display_level_lines()


def rotation(form):
    """Rotate a form."""
    new_form = 0
    for i in range(16):
        if form & (1 << i):
            new_form |= PIECE_ROTATION[i]
    return new_form


def is_possible(new_x, new_y, new_form):
    """Check if the "new_form" can be moved to position (new_x, new_y)."""
    for i in range(16):
        if not new_form & (1 << i):
            continue
        x = new_x + PIECE_X_INC[i]
        y = new_y + PIECE_Y_INC[i]
        if x < 0 or x >= GAME_WIDTH or y < 0 or y >= GAME_HEIGHT \
                or weetris['matrix'][y][x] >= 0:
            return 0
    return 1


def remove_completed_lines():
    """Remove completed lines."""
    y = GAME_HEIGHT - 1
    lines_removed = False
    while y >= 0:
        if -1 not in weetris['matrix'][y]:
            for i in range(y, -1, -1):
                if i == 0:
                    weetris['matrix'][i] = [-1] * GAME_WIDTH
                else:
                    weetris['matrix'][i] = weetris['matrix'][i - 1]
            # Removes the line and increases the number of lines made
            # in the game in "lines"
            weetris['lines'] += 1
            lines_removed = True
            if weetris['lines'] > weetris['best_lines']:
                set_best('max_lines', weetris['lines'])
                weetris['best_lines'] = weetris['lines']
        else:
            y -= 1
    if lines_removed:
        new_level = min(MAX_LEVEL, (weetris['lines'] // 10) + 1)
        if new_level != weetris['level']:
            # Next level
            weetris['level'] = new_level
            if weetris['level'] > weetris['best_level']:
                set_best('max_level', weetris['level'])
                weetris['best_level'] = weetris['level']
            init_timer()
        display_level_lines()


def end_of_piece():
    """End of a piece (it can not go down any more)."""
    display_piece(True)
    set_new_form()
    if is_possible(weetris['piece_x'], weetris['piece_y'],
                   weetris['piece_form']):
        remove_completed_lines()
    else:
        weetris['piece_form'] = 0
        weetris['playing'] = False
        weetris['paused'] = False
        if weetris['time_display_timer']:
            weechat.unhook(weetris['time_display_timer'])
            weetris['time_display_timer'] = ''
        weechat.prnt_y(weetris['buffer'], START_Y + GAME_HEIGHT + 2,
                       '>> End of game, score: %d lines, level %d '
                       '(alt-N to restart) <<' % (weetris['lines'],
                                                  weetris['level']))


def weetris_init():
    """Initialize weetris."""
    keys = {
        'meta2-A': 'up',
        'meta2-B': 'down',
        'meta-Ob': 'bottom',
        'meta-OB': 'bottom',
        'meta2-1;5B': 'bottom',
        'meta2-D': 'left',
        'meta2-C': 'right',
        'meta-n': 'new_game',
        'meta-p': 'pause',
    }
    weetris['buffer'] = weechat.buffer_search('python', 'weetris')
    if not weetris['buffer']:
        weetris['buffer'] = weechat.buffer_new('weetris',
                                               'buffer_input_cb', '',
                                               'buffer_close_cb', '')
    if weetris['buffer']:
        weechat.buffer_set(weetris['buffer'],
                           'type', 'free')
        weechat.buffer_set(weetris['buffer'],
                           'title', BUFFER_TITLE)
        for key, action in keys.items():
            weechat.buffer_set(weetris['buffer'],
                               'key_bind_%s' % key,
                               '/weetris %s' % action)
        new_game()
        weechat.buffer_set(weetris['buffer'], 'display', '1')


def run_action(action):
    """Run an action, when a key is pressed on weetris buffer."""
    if action == 'rotate':
        new_form = rotation(weetris['piece_form'])
        if is_possible(weetris['piece_x'], weetris['piece_y'], new_form):
            weetris['piece_form'] = new_form
            display_all()
    elif action == 'left':
        if is_possible(weetris['piece_x'] - 1, weetris['piece_y'],
                       weetris['piece_form']):
            weetris['piece_x'] -= 1
            display_all()
    elif action == 'right':
        if is_possible(weetris['piece_x'] + 1, weetris['piece_y'],
                       weetris['piece_form']):
            weetris['piece_x'] += 1
            display_all()
    elif action == 'down':
        if is_possible(weetris['piece_x'], weetris['piece_y'] + 1,
                       weetris['piece_form']):
            weetris['piece_y'] += 1
        else:
            end_of_piece()
        display_all()
    elif action == 'bottom':
        while is_possible(weetris['piece_x'], weetris['piece_y'] + 1,
                          weetris['piece_form']):
            weetris['piece_y'] += 1
        end_of_piece()
        display_all()


def weetris_cmd_cb(data, buf, args):
    """Callback for command /weetris."""
    if weetris['buffer']:
        weechat.buffer_set(weetris['buffer'], 'display', '1')
    else:
        weetris_init()

    if args == 'new_game':
        new_game()
    elif args == 'pause':
        if weetris['playing']:
            weetris['paused'] = not weetris['paused']
            display_all()
    else:
        if weetris['playing'] and not weetris['paused']:
            key_slow_down = weetris_settings['key_down_slow'] == 'on'
            actions = {
                'up': 'rotate',
                'left': 'left',
                'right': 'right',
                'down': 'down' if key_slow_down else 'bottom',
                'bottom': 'bottom' if key_slow_down else 'down',
            }
            action = actions.get(args)
            if action:
                run_action(action)
    return weechat.WEECHAT_RC_OK


def weetris_timer_cb(data, remaining_calls):
    """Weetris timer callback."""
    if weetris['buffer'] and weetris['playing'] and not weetris['paused']:
        if is_possible(weetris['piece_x'], weetris['piece_y'] + 1,
                       weetris['piece_form']):
            weetris['piece_y'] += 1
        else:
            end_of_piece()
        display_all()
    return weechat.WEECHAT_RC_OK


def get_best(name, default=0):
    """Get the best level/lines."""
    value = weechat.config_get_plugin(name)
    return int(value) if value else default


def set_best(name, value):
    """Set the best level/lines."""
    weechat.config_set_plugin(name, str(value))


def main():
    """Main function."""
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        term_colors = int(weechat.info_get('term_colors', '') or '8')
        weetris['256colors'] = term_colors >= 256

        # set default settings
        version = weechat.info_get('version_number', '') or 0
        for option, value in weetris_settings_default.items():
            if weechat.config_is_set_plugin(option):
                weetris_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                weetris_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(
                    option,
                    '%s (default: "%s")' % (value[1], value[0]))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                            'weetris_config_cb', '')

        # command /weetris
        weechat.hook_command('weetris', 'Run WeeTris', '',
                             'Keys:\n'
                             '   arrow up: rotate current piece\n'
                             ' arrow left: move piece to the left\n'
                             'arrow right: move piece to the right\n'
                             ' arrow down: increase speed of the piece\n'
                             '  ctrl+down: move pieve to the bottom\n'
                             '      alt+n: restart the game\n'
                             '      alt+p: pause current game',
                             '', 'weetris_cmd_cb', '')

        # initialization
        if weechat.buffer_search('python', 'weetris'):
            weetris_init()
        weetris['best_level'] = get_best('max_level', 1)
        weetris['best_lines'] = get_best('max_lines', 0)


if __name__ == '__main__' and import_ok:
    main()
