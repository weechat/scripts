#
# SPDX-FileCopyrightText: 2013-2026 nils_2 <libera.#weechat>
# SPDX-FileCopyrightText: 2015 Damien Bargiacchi <icymidnight@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# idea by shad0VV@freenode.#weechat
#
# 2026-10-03: nils_2, (libera.#weechat)
#       0.7 : fix: "/buffer <subcommand>" (close, list, clear, hide, zoom ...) is no
#             longer mistaken for a buffer name and swallowed
#           : fix: "/input jump_smart" switches by buffer pointer instead of the
#             short name (wrong buffer when a name exists on several servers)
#           : fix: "/buffer 0" is no longer treated as "no number"
#           : fix: buffers are switched with the API (buffer_set display) instead of
#             a composed "/buffer <name>" command (names with spaces, double hook run)
#           : fix: window number is validated (digits only, window must exist)
#           : fix: name lookup prefers an exact match; ambiguous names and numbers
#             out of range are left to WeeChat instead of guessing
#           : fix: merged buffers: the active buffer of a number is used
#           : fix: UnboundLocalError on empty hotlist, isdigit() with non-ASCII digits,
#             multiple spaces and upper case in the command
#           : cleanup: unused code removed, examples use libera and the
#             "localvar_set_stick_buffer_to_window" property
#
# 2017-12-14: Sébastien Helleu <flashcode@flashtux.org>
#       0.6 : rename command "/autosetbuffer" by "/buffer_autoset" in example
#
# 2017-04-02: nils_2, (freenode.#weechat)
#       0.5 : support of "/input jump_smart" and "/buffer +/-" (reported: squigz)
#
# 2017-03-25: nils_2, (freenode.#weechat)
#       0.4 : script did not work with /go script and buffer names (reported: squigz)
#
# 2015-05-12: Damien Bargiacchi <icymidnight@gmail.com>
#       0.3 : Stop script from truncating localvar lookup to first character of the buffer number
#           : Clean up destination buffer number logic
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.2 : make script compatible with Python 3.x
#           : smaller improvements
#
# 2013-01-21: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.6
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

import re
import sys

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    sys.exit(1)

SCRIPT_NAME     = "stick_buffer"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.7"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Stick buffers to particular windows, like irssi"

DIGITS = re.compile(r'[0-9]+')

# single-word arguments of /buffer that are subcommands, not buffer names/numbers
BUFFER_SUBCOMMANDS = frozenset([
    'list', 'add', 'clear', 'move', 'swap', 'cycle', 'merge', 'unmerge', 'hide',
    'unhide', 'switch', 'zoom', 'renumber', 'close', 'notify', 'localvar', 'set', 'get',
])

# ======================================[      config      ]====================================== #
SW_CONFIG_DEFAULTS = {
    'default_stick_window' : ('', 'The default window to stick a buffer to if no localvar '
                                  'stick_buffer_to_window is set'),
}

sw_config = {}
warned = set()

def init_config():
    for option, (default_value, description) in SW_CONFIG_DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)
            sw_config[option] = default_value
        else:
            sw_config[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (description, default_value))
    check_default_window(sw_config.get('default_stick_window', ''))

    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'update_config', '')

def update_config(pointer, name, value):
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]
    sw_config[option] = value
    if option == 'default_stick_window':
        check_default_window(value)
    return weechat.WEECHAT_RC_OK

def check_default_window(value):
    if value.strip() and parse_window_number(value) is None:
        print_error('option default_stick_window must be a window number (1, 2, 3 ...), got "%s"' % value)

def parse_window_number(value):
    """Return window number as int, or None if value is not a positive integer."""
    value = value.strip()
    if DIGITS.fullmatch(value) and int(value) >= 1:
        return int(value)
    return None

def get_default_stick_window_number():
    return parse_window_number(sw_config.get('default_stick_window', ''))

# ======================================[       util       ]====================================== #
def show_help():
    weechat.command('', '/help %s' % SCRIPT_NAME)

def print_error(message):
    weechat.prnt('', '%s%s: %s' % (weechat.prefix("error"), SCRIPT_NAME, message))

def warn_once(key, message):
    if key not in warned:
        warned.add(key)
        print_error(message)

# ======================================[   buffer utils   ]====================================== #
def get_buffers():
    buffers = []
    infolist = weechat.infolist_get('buffer', '', '')
    if infolist:
        while weechat.infolist_next(infolist):
            buffers.append({
                'number'    : weechat.infolist_integer(infolist, 'number'),
                'full_name' : weechat.infolist_string(infolist, 'full_name'),
                'short_name': weechat.infolist_string(infolist, 'short_name'),
                'pointer'   : weechat.infolist_pointer(infolist, 'pointer'),
                'active'    : weechat.infolist_integer(infolist, 'active'),
            })
        weechat.infolist_free(infolist)
    return buffers

def get_current_buffer_pointer():
    return weechat.window_get_pointer(weechat.current_window(), 'buffer')

def get_current_buffer_number():
    return weechat.buffer_get_integer(get_current_buffer_pointer(), 'number')

def pick_by_number(buffers, number):
    matches = [b for b in buffers if b['number'] == number]
    if not matches:
        return None
    for b in matches:                      # merged buffers: prefer the active one
        if b['active']:
            return b['pointer']
    return matches[0]['pointer']

def pick_by_name(buffers, name):
    """Exact full name, then unique short name, then unique substring.
    Anything ambiguous returns None, so WeeChat can decide itself."""
    low = name.lower()
    for b in buffers:
        if b['full_name'].lower() == low:
            return b['pointer']
    matches = [b for b in buffers if b['short_name'].lower() == low]
    if not matches:
        matches = [b for b in buffers if low in b['full_name'].lower()]
    if len(matches) == 1:
        return matches[0]['pointer']
    return None

def resolve_buffer(arg):
    """Resolve the argument of /buffer to a buffer pointer, or None."""
    buffers = get_buffers()
    mod, rest = '', arg
    if arg[0] in '+-*' and DIGITS.fullmatch(arg[1:]):
        mod, rest = arg[0], arg[1:]

    if DIGITS.fullmatch(rest):
        number = int(rest)
        if mod == '+':
            number = get_current_buffer_number() + number
        elif mod == '-':
            number = get_current_buffer_number() - number
        # out of range -> None: WeeChat does its own wrap-around/error handling
        return pick_by_number(buffers, number)
    return pick_by_name(buffers, arg)

def get_first_hotlist_buffer():
    ptr_buffer = ''
    infolist = weechat.infolist_get('hotlist', '', '')
    if infolist:
        if weechat.infolist_next(infolist):     # first entry in hotlist
            ptr_buffer = weechat.infolist_pointer(infolist, 'buffer_pointer')
        weechat.infolist_free(infolist)
    return ptr_buffer

# ======================================[  window utils    ]====================================== #
def window_exists(number):
    found = False
    infolist = weechat.infolist_get('window', '', '')
    if infolist:
        while weechat.infolist_next(infolist):
            if weechat.infolist_integer(infolist, 'number') == number:
                found = True
                break
        weechat.infolist_free(infolist)
    return found

def get_stick_window_number(ptr_buffer):
    value = weechat.buffer_get_string(ptr_buffer, 'localvar_stick_buffer_to_window').strip()
    if value:
        number = parse_window_number(value)
        if number is None:
            warn_once(('localvar', ptr_buffer, value),
                      'localvar stick_buffer_to_window of buffer "%s" must be a window number, got "%s"'
                      % (weechat.buffer_get_string(ptr_buffer, 'full_name'), value))
        return number
    return get_default_stick_window_number()

# ======================================[    callbacks     ]====================================== #
def stick_and_switch(ptr_buffer):
    """Show ptr_buffer in its sticky window. Returns the callback return code."""
    if not ptr_buffer or ptr_buffer == get_current_buffer_pointer():
        return weechat.WEECHAT_RC_OK

    window_number = get_stick_window_number(ptr_buffer)
    if window_number is None:
        return weechat.WEECHAT_RC_OK
    if window_number == weechat.window_get_integer(weechat.current_window(), 'number'):
        return weechat.WEECHAT_RC_OK            # already in the right window
    if not window_exists(window_number):
        warn_once(('window', window_number), 'window %d does not exist, buffer not moved.' % window_number)
        return weechat.WEECHAT_RC_OK

    weechat.command('', '/window %d' % window_number)
    weechat.buffer_set(ptr_buffer, 'display', '1')
    return weechat.WEECHAT_RC_OK_EAT

# command: /buffer <name|number|+N|-N>
def buffer_switch_cb(data, buffer, command):
    args = command.split()[1:]
    if len(args) != 1:
        return weechat.WEECHAT_RC_OK
    if args[0].lower() in BUFFER_SUBCOMMANDS:
        return weechat.WEECHAT_RC_OK
    return stick_and_switch(resolve_buffer(args[0]))

# command: /input jump_smart
def jump_smart_cb(data, buffer, command):
    return stick_and_switch(get_first_hotlist_buffer())

def cmd_cb(data, buffer, args):
    argv = args.strip().lower().split()

    if argv and argv[0] == 'list':
        weechat.command('', '/set *.localvar_set_stick_buffer_to_window')
    elif not argv or argv[0] == 'help':
        show_help()
    else:
        print_error('Unrecognized command %s\n' % ' '.join(argv))
        show_help()

    return weechat.WEECHAT_RC_OK

# ======================================[       main       ]====================================== #
def main():
    version = weechat.info_get('version_number', '') or 0

    if int(version) < 0x00030600:
        print_error('script needs version 0.3.6 or higher')
        weechat.command('', "/wait 1ms /python unload %s" % SCRIPT_NAME)
        return

    init_config()

    description = """
{script_name} can make sure that when switching to a buffer it appears only in a particular window.
To trigger this behaviour set the localvar 'stick_buffer_to_window' to the desired window number.

You will need '/buffer setauto' command to make local variables persistent; see the
examples below.

Notes:
 - The window number must be a positive number and the window must exist, otherwise the
   buffer is not moved (a warning is printed once).
 - Buffer names are matched in this order: full name (irc.libera.#weechat), then short
   name (#weechat), then part of the full name. If more than one buffer matches, or a
   number is out of range, this script does nothing and WeeChat switches in the current
   window as usual. Use the full name to be sure.
 - Switching with /input jump_previously_visited_buffer, jump_next_visited_buffer and
   jump_last_buffer is not supported.

Examples:
 Temporarily stick the current buffer to window 3:
   /buffer set localvar_set_stick_buffer_to_window 3
 Stick buffer #weechat to window 2:
   /buffer irc.libera.#weechat
   /buffer set localvar_set_stick_buffer_to_window 2
   /buffer setauto localvar_set_stick_buffer_to_window 2
 Set the default stick-to window to window 5:
   /set plugins.var.python.{script_name}.default_stick_window 5
 List buffers with persistent stickiness:
   /{script_name} list
 Show this help:
   /{script_name} help
 Display local variables for current buffer:
   /buffer localvar
""".format(script_name = SCRIPT_NAME)

    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'list || help', description, 'list || help', 'cmd_cb', '')

    weechat.hook_command_run('/buffer *', 'buffer_switch_cb', '')
    weechat.hook_command_run('/input jump_smart', 'jump_smart_cb', '')

if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
                        '', ''):
        main()
