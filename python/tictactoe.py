# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Sébastien Helleu <flashcode@flashtux.org>
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
# Tic-tac-toe for WeeChat.
#
# History:
#
# 2016-10-22, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

"""Tic-tac-toe game."""

from __future__ import print_function

SCRIPT_NAME = 'tictactoe'
SCRIPT_AUTHOR = 'Sébastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Tic-tac-toe game'

SCRIPT_COMMAND = 'tictactoe'

# pylint: disable=invalid-name
IMPORT_OK = True

try:
    # pylint: disable=wrong-import-position
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://weechat.org/')
    IMPORT_OK = False

try:
    # pylint: disable=wrong-import-position
    import copy
    import operator
    import random
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    IMPORT_OK = False

tictactoe = {
    'buffer': '',
    'board': [],
    'human': 1,
    'computer': 2,
    'symbols': [
        ['      ',
         '      '],
        ['  ╱╲  ',
         '  ╲╱  '],
        ['  ╲╱  ',
         '  ╱╲  '],
    ],
    'colors': [
        'default',
        'plugins.var.python.%s.color_human' % SCRIPT_NAME,
        'plugins.var.python.%s.color_computer' % SCRIPT_NAME,
    ],
    'end': '',
}

# options
tictactoe_settings_default = {
    'color_board': ('blue', 'board color'),
    'color_digits': ('magenta', 'color for digits'),
    'color_human': ('yellow', 'color for human player'),
    'color_computer': ('lightred', 'color for computer player'),
    'color_status': ('white', 'color for status (win/lose/draw game)'),
}
tictactoe_settings = {}

# mouse keys
tictactoe_mouse_keys = {
    '@chat(python.tictactoe):button1': ('/window ${_window_number};'
                                        'hsignal:tictactoe_mouse')
}


def tictactoe_display(clear=False):
    """Display board."""
    if not tictactoe['buffer']:
        return
    if clear:
        weechat.buffer_clear(tictactoe['buffer'])

    line = 1
    for y in range(0, 3):
        for i in range(0, 3):
            str_line = '  '
            for x in range(0, 3):
                pos = (y * 3) + x
                if i == 0:
                    str_line += '%s%d     ' % (
                        weechat.color(tictactoe_settings['color_digits']),
                        9 - ((y * 3) + (2 - x)))
                else:
                    str_line += '%s%s' % (
                        weechat.color(
                            tictactoe['colors'][tictactoe['board'][pos]]),
                        tictactoe['symbols'][tictactoe['board'][pos]][i - 1])
                if x < 2:
                    str_line += '%s%s' % (
                        weechat.color(tictactoe_settings['color_board']), '│')
            if y == 0 and i == 0:
                str_line += '     %sO%s = you' % (
                    weechat.color(tictactoe_settings['color_human']),
                    weechat.color('default'))
            if y == 0 and i == 1:
                str_line += '     %sX%s = computer' % (
                    weechat.color(tictactoe_settings['color_computer']),
                    weechat.color('default'))
            weechat.prnt_y(tictactoe['buffer'], line, str_line)
            line += 1
        if y < 2:
            weechat.prnt_y(tictactoe['buffer'], line,
                           '  %s──────┼──────┼──────' %
                           weechat.color(tictactoe_settings['color_board']))
            line += 1
    line += 1
    weechat.prnt_y(tictactoe['buffer'], line, '%s%s' % (
        weechat.color(tictactoe_settings['color_status']), tictactoe['end']))


def tictactoe_new_game(computer_begins=False):
    """Create a new game: initialize board and some variables."""
    tictactoe['board'] = [0] * 9
    tictactoe['end'] = ''
    if computer_begins:
        tictactoe_play_computer()
    tictactoe_display()


def tictactoe_input_buffer(data, buf, input_data):
    """Input data in tictactoe buffer."""
    # pylint: disable=unused-argument
    if input_data:
        args = input_data.split(' ')
        if args[0] in ('n', 'new'):
            tictactoe_new_game()
        elif args[0] in ('c', 'computer'):
            tictactoe_new_game(computer_begins=True)
        elif args[0] in ('q', 'quit'):
            weechat.buffer_close(tictactoe['buffer'])
        elif args[0].isdigit() and not tictactoe['end']:
            pos = int(args[0])
            if 1 <= pos <= 9:
                posconv = {
                    1: 6,
                    2: 7,
                    3: 8,
                    4: 3,
                    5: 4,
                    6: 5,
                    7: 0,
                    8: 1,
                    9: 2,
                }
                tictactoe_play(tictactoe['human'], posconv[pos])
    return weechat.WEECHAT_RC_OK


def tictactoe_close_buffer(data, buf):
    """Called when tictactoe buffer is closed."""
    # pylint: disable=unused-argument
    tictactoe['buffer'] = ''
    return weechat.WEECHAT_RC_OK


def tictactoe_init():
    """Initialize tictactoe: create buffer, new game."""
    if tictactoe['buffer']:
        return
    tictactoe['buffer'] = weechat.buffer_search('python', 'tictactoe')
    if not tictactoe['buffer']:
        tictactoe['buffer'] = weechat.buffer_new('tictactoe',
                                                 'tictactoe_input_buffer', '',
                                                 'tictactoe_close_buffer', '')
        if tictactoe['buffer']:
            weechat.buffer_set(tictactoe['buffer'], 'type', 'free')
            weechat.buffer_set(tictactoe['buffer'], 'title',
                               'Tictactoe | mouse: play, alt-n: new game | '
                               'alt-c: new game, computer begins | '
                               'Command line: (n)ew, +/-: change size, '
                               '(q)uit, 3-6: number of colors')
            weechat.buffer_set(tictactoe['buffer'], 'key_bind_meta-n',
                               '/tictactoe new')
            weechat.buffer_set(tictactoe['buffer'], 'key_bind_meta-c',
                               '/tictactoe computer')
    if tictactoe['buffer']:
        tictactoe_new_game()


def tictactoe_winner(board):
    """
    Check who won the game: return 1 or 2 for player number, 0 for draw game,
    -1 if game is not finished.
    """
    for i in range(0, 3):
        # check horizontally
        if board[i * 3] > 0 and \
                board[i * 3] == board[(i * 3) + 1] == board[(i * 3) + 2]:
            return board[i * 3]
        # check vertically
        if board[i] > 0 and board[i] == board[3 + i] == board[6 + i]:
            return board[i]
    # check diagonally
    if board[4] > 0 and (board[0] == board[4] == board[8] or
                         board[2] == board[4] == board[6]):
        return board[4]
    # game is not finished!
    if 0 in board:
        return -1
    # draw game!
    return 0


def tictactoe_score(board, player, value, pos):
    """
    Returns the score if the player "player" plays at "pos":
    a high score means that this position MUST be chosen
    (to prevent the other player to win, or to win myself).
    """
    score = [0]
    board[pos] = value
    winner = tictactoe_winner(board)
    if winner < 0:
        for i in range(0, 9):
            if board[i] == 0:
                score.append(tictactoe_score(board, player, value ^ 3, i))
    else:
        if winner == player:
            score.append(1000)
        elif winner != 0:
            score.append(-1000)
    board[pos] = 0
    return sum(score) / len(score)


def tictactoe_play_computer():
    """AI for computer."""
    board = copy.deepcopy(tictactoe['board'])
    player = tictactoe['computer']
    if board.count(0) >= 8 and board[4] == 0:
        # if the middle position is free, play there
        pos = 4
    else:
        # get the score for each possible available position in board
        score = {}
        for pos in range(0, 9):
            if board[pos] == 0:
                score[pos] = tictactoe_score(board, player, player, pos)
        # get the highest score value
        best_score = sorted(score.items(), key=operator.itemgetter(1))[-1][1]
        # choose a random position having the highest score
        pos = random.choice([s[0] for s in score.items()
                             if s[1] == best_score])
    tictactoe_play(player, pos)


def tictactoe_play(player, pos):
    """Play at "pos" for "player", and check if game has ended."""
    if tictactoe['board'][pos] > 0:
        return
    tictactoe['board'][pos] = player
    winner = tictactoe_winner(tictactoe['board'])
    if winner >= 0:
        msg = ''
        if winner == 0:
            msg = 'draw game'
        elif winner == tictactoe['computer']:
            msg = 'you lose...'
        else:
            msg = '** CONGRATS! **'
        tictactoe['end'] = 'End of game  %s' % msg
    elif player != tictactoe['computer']:
        tictactoe_play_computer()
    tictactoe_display()


def tictactoe_cmd_cb(data, buf, args):
    """The /tictactoe command."""
    tictactoe_init()
    if tictactoe['buffer']:
        weechat.buffer_set(tictactoe['buffer'], 'display', '1')
    if args == 'new':
        tictactoe_new_game()
    elif args == 'computer':
        tictactoe_new_game(computer_begins=True)
    return weechat.WEECHAT_RC_OK


def tictactoe_mouse_cb(data, hsignal, hashtable):
    """Mouse callback."""
    if not tictactoe['end']:
        pos_x = int(hashtable.get('_chat_line_x', '-1'))
        pos_y = int(hashtable.get('_chat_line_y', '-1'))
        if 2 <= pos_x <= 21 and pos_x not in (8, 15) and 1 <= pos_y <= 11 and \
                pos_y not in (4, 8):
            pos_x = (pos_x - 2) // 7
            pos_y = (pos_y - 1) // 4
            pos = (pos_y * 3) + pos_x
            tictactoe_play(1, pos)
    return weechat.WEECHAT_RC_OK


def tictactoe_config_cb(data, option, value):
    """Called when a script option is changed."""
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in tictactoe_settings:
            tictactoe_settings[name] = value
    tictactoe_display(clear=True)
    return weechat.WEECHAT_RC_OK


if __name__ == '__main__' and IMPORT_OK:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        # set default settings
        version = weechat.info_get("version_number", "") or 0
        for ttt_option, ttt_value in tictactoe_settings_default.items():
            if weechat.config_is_set_plugin(ttt_option):
                tictactoe_settings[ttt_option] = weechat.config_get_plugin(
                    ttt_option)
            else:
                weechat.config_set_plugin(ttt_option, ttt_value[0])
                tictactoe_settings[ttt_option] = ttt_value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(ttt_option,
                                               '%s (default: "%s")' % (
                                                   ttt_value[1], ttt_value[0]))

        # mouse support
        weechat.key_bind('mouse', tictactoe_mouse_keys)
        weechat.hook_hsignal('tictactoe_mouse', 'tictactoe_mouse_cb', '')

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                            'tictactoe_config_cb', '')

        # add command
        weechat.hook_command(
            SCRIPT_COMMAND, 'Tic-tac-toe game.', '',
            'Instructions:\n'
            '  - enter one digit, or click with mouse in an empty cell to '
            'play\n'
            '  - you must align 3 symbols: horizontally, vertically or '
            'diagonally\n'
            '  - you win if you align the symbols before the computer\n'
            '  - there is a draw game if 3 symbols are not aligned at the end '
            '(for you or computer).\n'
            '\n'
            'Keys:\n'
            '  alt-n: new game, you start\n'
            '  alt-c: new game, computer begins',
            '',
            'tictactoe_cmd_cb', '')

        # if buffer already exists (after /upgrade), initialize tictactoe
        if weechat.buffer_search('python', 'tictactoe'):
            tictactoe_init()
