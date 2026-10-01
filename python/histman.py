# SPDX-FileCopyrightText: 2012-2026 nils_2@libera.#weechat
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 2026-09-29
#       0.9.0 : revised version (security and robustness fixes)
#           : fix: negative value for option 'number' truncated the history file
#             and raised an exception
#           : fix: IndexError for one-character lines in mode "text"
#           : fix: options 'min_length' and 'number' are validated
#           : fix: restore honours localvar 'save_history' / 'save_buffer'
#             (condition in read_history() was never true)
#           : fix: option 'skip_double' is really case sensitive (as documented)
#           : security: buffer names are sanitized before they are used as
#             file names (no path traversal); legacy file names are still read
#           : security: files are written with mode 0600, atomically
#             (temporary file + rename), symlinks are not followed
#           : security: invalid regex in option 'pattern' -> nothing is saved
#             (fail closed); pattern is compiled only once
#           : security: broader default value for option 'pattern' (new
#             installations only, existing settings are not changed)
#           : files are read and written as UTF-8; empty and multi-line
#             entries are skipped
#           : one failing buffer does not abort saving of all other buffers
#           : infolists are always freed
#           : add option 'save_free': buffers with free content (fset, color,
#             secure, script, ...) are only saved/restored if it is "on"
#           : entries typed in free-content buffers are also removed from the
#             global history if 'save_free' is "off"
#           : requires WeeChat >= 3.2 (string_eval_path_home), Python 3 only
#           : add SPDX copyright and license tags
#
# 2021-05-02, Sébastien Helleu <flashcode@flashtux.org>
#       0.8.2 : add compatibility with WeeChat >= 3.2 (XDG directories)
#
# 2018-08-04: nils_2 (freenode.#weechat)
#       0.8 : add option 'save_buffer'
#           : thanks catbeard for revise the help text
#
# 2018-08-01: nils_2 (freenode.#weechat)
#       0.7 : rmodifier routine removed
#           : bug fixes
#
# 2017-12-14: Sébastien Helleu <flashcode@flashtux.org>
#       0.6 : rename command "/autosetbuffer" by "/buffer_autoset" in example
#
# 2015-04-05: nils_2 (freenode.#weechat)
#       0.5 : change priority of hook_signal('buffer_opened') to 100
#
# 2013-01-25: nils_2 (freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
#
# 2013-01-20: nils_2, (freenode.#weechat)
#       0.3: fix wrong command argument in help-text
#
# 2012-12-21: nils_2, (freenode.#weechat)
#       0.2 : fix UnicodeEncodeError
#
# 2012-12-09: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# thanks to nestib for help with regex and for the rmodifier idea
#
# requires: WeeChat version 3.2
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

import hashlib
import io
import os
import re
import sys
from collections import Counter
from urllib.parse import quote

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    sys.exit(1)

SCRIPT_NAME     = 'histman'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.9.0'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'save and restore global and/or buffer command history'

OPTION_DEFAULTS = {
    'number'       : ('0', 'number of history commands/text to save. A positive number will save from oldest to latest, a negative number will save from latest to oldest. 0 = save whole history (e.g. -10 will save the last 10 history entries)'),
    'pattern'      : ('(.*password|.*passphrase|.*nickserv|.*chanserv|.*authserv|/(oper|secure|identify)( |$)|/quote pass|/quit)', 'a simple regex (case insensitive, matched at the beginning of the line) to ignore commands/text. Empty value disables pattern matching. If the regex is invalid, nothing will be saved'),
    'skip_double'  : ('on', 'skip lines that already exist (case sensitive)'),
    'save'         : ('all', 'define what should be saved from history. Possible values are "command", "text", "all". This is a fallback option (see /help ' + SCRIPT_NAME + ')'),
    'history_dir'  : ('%h/history', 'local cache directory for history files ("%h" will be replaced by WeeChat data directory)'),
    'save_global'  : ('off', 'save global history, possible values are "command", "text", "all" or "off" (default: off)'),
    'save_buffer'  : ('off', 'save buffer history from all buffers, possible values are "on", "off". Using this option, localvar from buffer will be ignored (default: off)'),
    'save_free'    : ('off', 'save and restore history of buffers with free content (e.g. fset, color, secure, script), possible values are "on", "off". If "off", these buffers are never handled, even if localvar "save_history" is set or "save_buffer" is "on" (default: off)'),
    'min_length'   : ('2', 'minimum length of command/text (default: 2)'),
    'buffer_close' : ('off', 'save command history, when buffer will be closed (default: off)'),
}

OPTIONS = {}

HELP_TEXT = '\n'.join([
    '  save: save the command history now (do not wait for /quit)',
    '  list: list the "save_history" settings made with buffer_autoset',
    '',
    'What is saved, and when:',
    '  - On /quit the history of all selected buffers (and the global history, if enabled) is written',
    '    to files in the directory given by option "history_dir".',
    '  - With option "buffer_close" set to "on", the history of a buffer is also saved when the buffer is closed.',
    '  - When a buffer is opened again (or WeeChat starts), its history is restored from the file.',
    '',
    'Which buffers are handled:',
    '  - buffers with the local variable "save_history" set (values: see below)',
    '  - all buffers, if option "save_buffer" is "on" (the local variable is then not required;',
    '    buffers without it use the value of option "save")',
    '  - the global history, if option "save_global" is not "off"',
    '  - buffers with free content (fset, color, secure, script, ...) only if option "save_free" is "on",',
    '    regardless of the settings above',
    '',
    'Values for the local variable "save_history" (and for the options "save" and "save_global"):',
    '  command: save commands only (lines starting with a command char; "//text" counts as text)',
    '     text: save text only (e.g. messages sent to a channel)',
    '      all: save commands and text',
    '',
    'A local variable is lost when WeeChat restarts. Use the command "/buffer setauto" to make it persistent',
    '(see examples below).',
    '',
    'Lines that are not saved:',
    '  - lines shorter than option "min_length"',
    '  - lines matching the regex in option "pattern" (case insensitive, matched from the beginning of the line)',
    '  - duplicates, if option "skip_double" is "on" (case sensitive)',
    '  - empty and multi-line entries',
    'Option "number" limits the amount: a positive value N saves the first (oldest) N entries, a negative',
    'value saves the last N entries, 0 saves everything.',
    '',
    'Security:',
    '  History files are written with mode 0600. The option "pattern" is a blacklist and can not catch every',
    '  secret; if the regex is invalid, nothing is saved. Be careful with "save_buffer" and "save_free".',
    '',
    'Examples:',
    '  save the command history manually (e.g. from a /trigger or a cron job):',
    '    /' + SCRIPT_NAME + ' save',
    '  save and restore only the text typed in buffer #weechat on libera:',
    '    /command -buffer irc.libera.#weechat core /buffer setauto localvar_set_save_history text',
    '  save and restore only the commands typed in current buffer:',
    '    /buffer setauto localvar_set_save_history command',
])

FILENAME_GLOBAL_HISTORY = 'global_history'
POSSIBLE_SAVE_OPTIONS = ('command', 'text', 'all')
MAX_FILENAME_LEN = 200

# cache for the compiled 'pattern' option
_filter = {'source': None, 'regex': None, 'valid': True}

# history entries of free-content buffers that were closed in this session
# (they stay in the global history, so they must be excluded from it)
_closed_free_lines = Counter()


# ==================================[ helpers ]===================================
def report(message):
    weechat.prnt('', '%s%s: %s' % (weechat.prefix('error'), SCRIPT_NAME, message))


def info(message):
    weechat.prnt('', '%s: %s' % (SCRIPT_NAME, message))


def opt_int(name, default):
    try:
        return int(str(OPTIONS.get(name, default)).strip())
    except ValueError:
        return default


def opt_on(name):
    return str(OPTIONS.get(name, '')).strip().lower() == 'on'


def compile_filter():
    source = OPTIONS.get('pattern', '')
    _filter['source'] = source
    _filter['regex'] = None
    _filter['valid'] = True
    if source != '':
        try:
            _filter['regex'] = re.compile(source, re.I)
        except re.error as e:
            _filter['valid'] = False
            report('invalid regular expression in option "pattern" (%s). '
                   'Nothing will be saved until this is fixed.' % e)


def get_filter():
    if _filter['source'] != OPTIONS.get('pattern', ''):
        compile_filter()
    return _filter['regex'], _filter['valid']


# ===================================[ paths ]====================================
def get_history_dir():
    options = {'directory': 'data'}
    return weechat.string_eval_path_home(OPTIONS['history_dir'], {}, {}, options)


def config_create_dir():
    path = get_history_dir()
    if not os.path.isdir(path):
        os.makedirs(path, mode=0o700, exist_ok=True)
        try:
            os.chmod(path, 0o700)       # do not depend on umask
        except OSError:
            pass


def inside_dir(path, base):
    """True if the (resolved) path is a direct child of base."""
    return os.path.dirname(os.path.realpath(path)) == base


def history_path(name):
    """Return a safe path for the history file 'name' (raises ValueError)."""
    base = os.path.realpath(get_history_dir())
    safe = quote(name, safe='#@+', errors='replace')
    if len(safe) > MAX_FILENAME_LEN:
        digest = hashlib.sha1(name.encode('utf-8', 'replace')).hexdigest()[:12]
        safe = safe[:MAX_FILENAME_LEN - 20] + '~' + digest
    path = os.path.join(base, safe)
    if not inside_dir(path, base):
        raise ValueError('invalid history file name: %r' % name)
    return path


def resolve_read_path(name):
    """Return path of an existing history file or None."""
    try:
        path = history_path(name)
    except ValueError:
        return None
    if os.path.isfile(path):
        return path
    # fallback: file name as used by histman < 0.9.0
    base = os.path.realpath(get_history_dir())
    legacy = os.path.join(base, name)
    if os.path.isfile(legacy) and inside_dir(legacy, base):
        return legacy
    return None


def buffer_filename(ptr_buffer):
    plugin = weechat.buffer_get_string(ptr_buffer, 'localvar_plugin')
    name = weechat.buffer_get_string(ptr_buffer, 'localvar_name')
    return '%s.%s' % (plugin, name)


# ===============================[ collect history ]==============================
def is_free_buffer(ptr_buffer):
    """True for buffers with free content (fset, color, secure, script, ...)."""
    return weechat.buffer_get_integer(ptr_buffer, 'type') == 1


def buffer_wanted(ptr_buffer):
    """Should the history of this buffer be saved?"""
    if is_free_buffer(ptr_buffer) and not opt_on('save_free'):
        return False
    if weechat.buffer_get_string(ptr_buffer, 'localvar_save_history'):
        return True
    return opt_on('save_buffer')


def get_save_mode(ptr_buffer):
    """Return 'command', 'text', 'all' or '' (= save nothing)."""
    if ptr_buffer:
        mode = weechat.buffer_get_string(ptr_buffer, 'localvar_save_history').strip().lower()
    else:
        mode = str(OPTIONS.get('save_global', '')).strip().lower()
    if mode in POSSIBLE_SAVE_OPTIONS:
        return mode
    fallback = str(OPTIONS.get('save', '')).strip().lower()
    return fallback if fallback in POSSIBLE_SAVE_OPTIONS else ''


def get_command_chars():
    extra = weechat.config_string(weechat.config_get('weechat.look.command_chars')) or ''
    return '/' + extra


def is_command(line, command_chars):
    # a valid command has at least two chars, first and second char differ ("//" = text)
    return len(line) > 1 and line[0] in command_chars and line[0] != line[1]


def line_matches_mode(line, mode, command_chars):
    if mode == 'command':
        return is_command(line, command_chars)
    if mode == 'text':
        return not is_command(line, command_chars)
    return mode == 'all'


def count_history_lines(ptr_buffer, counts):
    """Add the history entries of a buffer to the Counter 'counts'."""
    infolist = weechat.infolist_get('history', ptr_buffer, '')
    if not infolist:
        return
    try:
        while weechat.infolist_next(infolist):
            counts[weechat.infolist_string(infolist, 'text')] += 1
    finally:
        weechat.infolist_free(infolist)


def get_free_buffer_lines():
    """Entries typed in free-content buffers. WeeChat also stores them in the global history."""
    counts = Counter(_closed_free_lines)
    infolist = weechat.infolist_get('buffer', '', '')
    if infolist:
        try:
            while weechat.infolist_next(infolist):
                ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
                if is_free_buffer(ptr_buffer):
                    count_history_lines(ptr_buffer, counts)
        finally:
            weechat.infolist_free(infolist)
    return counts


def get_buffer_history(ptr_buffer):
    """Return the lines to save (oldest first). Empty ptr_buffer = global history."""
    lines = []

    mode = get_save_mode(ptr_buffer)
    if not mode:
        return lines

    regex, valid = get_filter()
    if not valid:                       # fail closed
        return lines

    min_length = max(opt_int('min_length', 2), 1)
    skip_double = opt_on('skip_double')
    command_chars = get_command_chars()

    # global history: drop the entries that were typed in free-content buffers
    exclude = Counter()
    if not ptr_buffer and not opt_on('save_free'):
        exclude = get_free_buffer_lines()

    infolist = weechat.infolist_get('history', ptr_buffer, '')
    if not infolist:
        return lines

    seen = set()
    try:
        # WeeChat returns the newest entry first
        while weechat.infolist_next(infolist):
            line = weechat.infolist_string(infolist, 'text')
            if exclude[line] > 0:
                exclude[line] -= 1
                continue
            if len(line) < min_length or not line.strip():
                continue
            if '\n' in line or '\r' in line:    # would corrupt the file format
                continue
            if not line_matches_mode(line, mode, command_chars):
                continue
            if regex is not None and regex.match(line):
                continue
            if skip_double:
                if line in seen:
                    continue
                seen.add(line)
            lines.append(line)
    finally:
        weechat.infolist_free(infolist)

    lines.reverse()
    return lines


def select_lines(lines):
    """Apply option 'number' to the list (oldest first)."""
    n = opt_int('number', 0)
    if n > 0:
        return lines[:n]
    if n < 0:
        return lines[n:]                # the last abs(n) entries
    return lines


# ===============================[ read/write files ]=============================
def write_history(name, lines):
    lines = select_lines(lines)
    if not lines:
        return

    tmp = None
    try:
        config_create_dir()
        path = history_path(name)
        tmp = path + '.tmp'
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(tmp, flags, 0o600)
        with io.open(fd, 'w', encoding='utf-8', errors='replace', newline='\n') as f:
            for line in lines:
                f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        tmp = None
    except Exception as e:
        report('error writing history "%s": %s' % (name, e))
    finally:
        if tmp is not None:
            try:
                os.remove(tmp)
            except OSError:
                pass


def read_history(name, ptr_buffer):
    """Restore history from file. Empty ptr_buffer = global history."""
    try:
        if ptr_buffer and is_free_buffer(ptr_buffer) and not opt_on('save_free'):
            return
        if ptr_buffer and not opt_on('save_buffer'):
            # is history saving enabled for this buffer?
            plugin = weechat.buffer_get_string(ptr_buffer, 'localvar_plugin')
            bname = weechat.buffer_get_string(ptr_buffer, 'localvar_name')
            # fallback: localvar may not be set yet (buffer_autoset not applied)
            autoset = weechat.config_get('buffer_autoset.buffer.%s.%s.localvar_set_save_history' % (plugin, bname))
            if not autoset and not weechat.buffer_get_string(ptr_buffer, 'localvar_save_history'):
                return

        path = resolve_read_path(name)
        if not path:
            return

        hdata = weechat.hdata_get('history')
        if not hdata:
            return

        with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
            for raw in f:
                line = raw.rstrip('\r\n')
                if not line.strip():
                    continue
                values = {'text': line}
                if ptr_buffer:
                    values['buffer'] = ptr_buffer
                weechat.hdata_update(hdata, '', values)
    except Exception as e:
        report('error loading history "%s": %s' % (name, e))


def save_buffer_history(ptr_buffer):
    if not buffer_wanted(ptr_buffer):
        return
    lines = get_buffer_history(ptr_buffer)
    if lines:
        write_history(buffer_filename(ptr_buffer), lines)


def save_history():
    infolist = weechat.infolist_get('buffer', '', '')
    if infolist:
        try:
            while weechat.infolist_next(infolist):
                ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
                try:
                    save_buffer_history(ptr_buffer)
                except Exception as e:      # continue with the other buffers
                    report('error saving buffer history: %s' % e)
        finally:
            weechat.infolist_free(infolist)

    if str(OPTIONS.get('save_global', 'off')).strip().lower() != 'off':
        try:
            lines = get_buffer_history('')  # no buffer pointer = global history
            if lines:
                write_history(FILENAME_GLOBAL_HISTORY, lines)
        except Exception as e:
            report('error saving global history: %s' % e)


# ===========================================[ Hooks() ]==========================================
def create_hooks():
    weechat.hook_signal('quit', 'quit_signal_cb', '')
    weechat.hook_signal('upgrade_ended', 'upgrade_ended_cb', '')
    # low priority for hook_signal('buffer_opened') to ensure that buffer_autoset hook_signal() runs first
    weechat.hook_signal('1000|buffer_opened', 'buffer_opened_cb', '')
    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')
    weechat.hook_signal('buffer_closing', 'buffer_closing_cb', '')


def quit_signal_cb(data, signal, signal_data):
    save_history()
    return weechat.WEECHAT_RC_OK


def buffer_opened_cb(data, signal, signal_data):
    read_history(buffer_filename(signal_data), signal_data)
    return weechat.WEECHAT_RC_OK


def buffer_closing_cb(data, signal, signal_data):
    if signal_data:
        try:
            if is_free_buffer(signal_data) and not opt_on('save_free'):
                # remember the entries: they stay in the global history after the buffer is gone
                count_history_lines(signal_data, _closed_free_lines)
            elif opt_on('buffer_close'):
                save_buffer_history(signal_data)
        except Exception as e:
            report('error saving buffer history: %s' % e)
    return weechat.WEECHAT_RC_OK


def upgrade_ended_cb(data, signal, signal_data):
    weechat.buffer_set(weechat.buffer_search_main(), 'localvar_set_histman', 'on')
    return weechat.WEECHAT_RC_OK


def histman_cmd_cb(data, buffer, args):
    argv = args.strip().split(' ', 1)
    command = argv[0].lower()

    if command == 'save':
        save_history()
    elif command == 'list':
        weechat.command('', '/set *.localvar_set_save_history')
    else:
        weechat.command('', '/help %s' % SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK


# ================================[ weechat options & description ]===============================
def init_options():
    for option, (default, description) in OPTION_DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (description, default))
        OPTIONS[option] = weechat.config_get_plugin(option)
    compile_filter()


def toggle_refresh(pointer, name, value):
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]
    if option in OPTION_DEFAULTS:
        OPTIONS[option] = value if value is not None else OPTION_DEFAULTS[option][0]
        if option == 'pattern':
            compile_filter()
    return weechat.WEECHAT_RC_OK


# ================================[ main ]===============================
if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        try:
            version = int(weechat.info_get('version_number', '') or 0)
        except ValueError:
            version = 0

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, '[save] || [list]',
                            HELP_TEXT,
                            'save %-'
                            '|| list %-',
                            'histman_cmd_cb', '')

        if version >= 0x03020000:
            main_buffer = weechat.buffer_search_main()
            init_options()
            if weechat.buffer_get_string(main_buffer, 'localvar_histman') == 'on':
                # script was reloaded: history is already in memory, do not restore it twice
                create_hooks()
                info('script was already started in this session, history will not be restored again.')
            else:
                try:
                    config_create_dir()
                except Exception as e:
                    report('can not create history directory: %s' % e)

                # look for global_history
                if str(OPTIONS.get('save_global', 'off')).strip().lower() != 'off':
                    read_history(FILENAME_GLOBAL_HISTORY, '')

                # core buffer is already open on script startup. Check manually!
                read_history(buffer_filename(main_buffer), main_buffer)

                create_hooks()

                # set localvar, to start script only once!
                weechat.buffer_set(main_buffer, 'localvar_set_histman', 'on')
        else:
            report('needs WeeChat version 3.2 or higher')
            weechat.command('', '/wait 1ms /python unload %s' % SCRIPT_NAME)
