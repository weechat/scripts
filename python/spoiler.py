# Copyright (c) 2022 Thomas Faughnan <tom@tjf.sh>
# Released under GNU GPLv3
# https://www.gnu.org/licenses/gpl-3.0.html

# =============================================================================
#                               SPOILER.PY
#
# Send spoiler text (same foreground and background color) like so:
#   The answer to life, the universe, and everything is <spoiler>42</spoiler>.
# An optional color integer in [0, 98] or color name may be provided like so:
#   <spoiler 3>Darth Vader</spoiler> is <spoiler blue>Luke</spoiler>'s father.
# If unspecified, the color defaults to 14 (darkgray in WeeChat).
#
# For documentation on WeeChat color names and U+0003 manual input (Ctrl+c, c):
# https://weechat.org/files/doc/stable/weechat_user.en.html#command_line_colors
#
# For general guidelines on how IRC clients may interpret colors:
# https://modern.ircdocs.horse/formatting.html#colors

# Email patches or PR https://github.com/tfaughnan/weechat-spoilers
# =============================================================================

import re

import_ok = True

try:
    import weechat
except ImportError:
    print('Script must be run under WeeChat')
    import_ok = False

MESSAGE_PATTERN = r'^(?P<prefix>PRIVMSG \S+ :)(?P<body>.*)$'
SPOILER_PATTERN = r'<spoiler(\s(\d{1,2}|[a-z]+))?>(.+?)</spoiler>'
CTRL_CHAR = '\u0003'
DEFAULT_COLORINT = 14
COLOR_NAMES = [
    'white', 'black', 'blue', 'green', 'lightred', 'red', 'magenta', 'brown',
    'yellow', 'lightgreen', 'cyan', 'lightcyan', 'lightblue', 'lightmagenta',
    'darkgray', 'gray'
]


def repl(m: re.Match) -> str:
    color = m.group(2)
    spoilertext = m.group(3)

    if color and color.isdigit() and int(color) in range(99):
        colorint = int(color)
    elif color and color in COLOR_NAMES:
        colorint = COLOR_NAMES.index(color)
    else:
        colorint = DEFAULT_COLORINT

    return f'{CTRL_CHAR}{colorint:02},{colorint:02}{spoilertext}{CTRL_CHAR}'


def spoilerize_buffer(data: str, mod: str, ptr: str, content: str) -> str:
    return re.sub(SPOILER_PATTERN, repl, content)


def spoilerize_irc(data: str, mod: str, server: str, msg: str) -> str:
    m = re.match(MESSAGE_PATTERN, msg)
    if not m:
        return msg

    prefix, body = m.groups()

    return prefix + re.sub(SPOILER_PATTERN, repl, body)


if __name__ == '__main__' and import_ok:
    weechat.register('spoiler', 'Thomas Faughnan', '0.1.0', 'GPL3',
                     'Send spoiler text <spoiler>like this</spoiler>', '', '')
    weechat.hook_modifier('input_text_for_buffer', 'spoilerize_buffer', '')
    weechat.hook_modifier('irc_out_privmsg', 'spoilerize_irc', '')
