#
# SPDX-FileCopyrightText: 2013-2025 Nils Görs <weechatter@arcor.de>
# SPDX-FileCopyrightText: 2017 Filip H.F. 'FiXato' Slagter <fixato+weechat@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Save and restore query buffers after /quit.
#
# Idea by lasers@freenode.#weechat
#
# 2026-10-03: nils_2 (libera.#weechat)
#       0.8 : fix: /quit no longer overwrites the stored list with the currently
#             open buffers (queries of servers that were not connected were lost)
#           : fix: "display auto" is now executed after the query was opened
#             (timer instead of "/wait 1", which means 1 second)
#           : fix: only IRC private buffers are stored (no DCC or buffers of
#             other scripts), empty server/nick values are ignored
#           : security: nicks and server names are validated before they are
#             used in a command (no leading "-", whitespace, control chars, "${")
#           : file is written atomically, utf-8 encoded, with mode 0600
#           : file is only written when the list really changed
#           : nicks are compared case-insensitively
#           : add options "debug" and "max_queries_per_server"
#           : "/queryman save" now also adds currently open queries
#           : restore queries on already connected servers when script is loaded
#           : error message for unsupported WeeChat versions
#
# 2025-10-02: nils_2 (libera.#weechat)
#       0.7 : fix a ValueError in config file, when using dcc. localvar "server", is missing for dcc buffer (reported by roughnecks)
#           : add some more DEBUG() text
#
# 2023-08-01: nils_2 (libera.#weechat)
#     0.6.1 : fix a timing problem when joining autojoin-channels (reported by thecdnhermit)
#
# 2021-05-05: Sébastien Helleu <flashcode@flashtux.org>
#       0.6 : add compatibility with XDG directories (WeeChat >= 3.2)
#
# 2018-08-08: nils_2, (freenode.#weechat)
#       0.5 : fix TypeError with python3.6
#
# 2017-04-14: nils_2 & FiXato, (freenode.#weechat)
#       0.4 : big rewrite:
#           : added extra hooks:
#           - query buffers are now also stored when opening/closing queries
#           - queries only restored on connect; no longer on every reconnect
#           : current buffer position is retained
#           : manual saving of query list (https://github.com/weechat/scripts/issues/196)
#
# 2015-02-27: nils_2, (freenode.#weechat)
#       0.3 : make script consistent with "buffer_switch_autojoin" option (idea haasn)
#
# 2013-11-07: nils_2, (freenode.#weechat)
#       0.2 : fix file not found error (reported by calcifea)
#           : make script compatible with Python 3.x
#
# 2013-07-26: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# script will create a config file "queryman.txt" in the WeeChat data directory
# (e.g. ~/.local/share/weechat/ or ~/.weechat/)
# format: "servername nickname" (without "")
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

import os
import re
import sys

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    sys.exit(1)

SCRIPT_NAME     = 'queryman'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.8'
SCRIPT_LICENSE  = 'GPL3'
SCRIPT_DESC     = 'save and restore query buffers after /quit and on open/close of queries'

DEFAULTS        = { 'debug'                  : ('off', 'print debug messages.'),
                    'max_queries_per_server' : ('100', 'maximum number of queries stored per server for newly opened queries (0 = unlimited).'),
                  }
OPTIONS         = {}

queryman_filename = 'queryman.txt'
servers_opening = set()
servers_closing = set()
stored_query_buffers_per_server = {}
quitting = False

# ================================[ validation ]===============================
# Server names and nicks are written to a file and later used in a command, so
# only accept values that cannot be mistaken for options or extra arguments.
SERVER_RE = re.compile(r'[^\s,\-\x00-\x1f\x7f][^\s,\x00-\x1f\x7f]{0,63}')
NICK_RE   = re.compile(r'[^\s,\-#&+!\x00-\x1f\x7f][^\s,\x00-\x1f\x7f]{0,99}')

def valid_server(name):
    return bool(SERVER_RE.fullmatch(name)) and '${' not in name

def valid_nick(nick):
    return bool(NICK_RE.fullmatch(nick)) and '${' not in nick

# ================================[ options ]===============================
def opt_on(name):
    return OPTIONS.get(name, 'off').strip().lower() in ('on', 'yes', 'true', '1')

def opt_int(name, default):
    try:
        return int(OPTIONS.get(name, default))
    except (TypeError, ValueError):
        return default

def print_error(message):
    weechat.prnt('', '%s%s: %s' % (weechat.prefix('error'), SCRIPT_NAME, message))

def debug_print(message):
    if opt_on('debug'):
        weechat.prnt('', 'DEBUG/%s: %s' % (SCRIPT_NAME, message))

# ================================[ buffer helpers ]===============================
def get_query_info(buf):
    """Return (server, nick) for an IRC query buffer, else None."""
    if weechat.buffer_get_string(buf, 'plugin') != 'irc':
        return None
    if weechat.buffer_get_string(buf, 'localvar_type') != 'private':
        return None
    server_name = weechat.buffer_get_string(buf, 'localvar_server')
    nick = weechat.buffer_get_string(buf, 'localvar_channel')
    if not server_name or not nick:
        return None
    return server_name, nick

def get_current_query_buffers():
    queries = {}
    infolist = weechat.infolist_get('buffer', '', '')
    if not infolist:
        return queries
    while weechat.infolist_next(infolist):
        info = get_query_info(weechat.infolist_pointer(infolist, 'pointer'))
        if info:
            queries.setdefault(info[0], set()).add(info[1])
    weechat.infolist_free(infolist)
    return queries

def get_connected_servers():
    servers = []
    infolist = weechat.infolist_get('irc_server', '', '')
    if not infolist:
        return servers
    while weechat.infolist_next(infolist):
        if weechat.infolist_integer(infolist, 'is_connected'):
            servers.append(weechat.infolist_string(infolist, 'name'))
    weechat.infolist_free(infolist)
    return servers

# ================================[ callback ]===============================
# signal_data = buffer pointer
def buffer_closing_signal_cb(data, signal, signal_data):
    # while quitting, buffers are closed one by one: keep the stored list as it is
    if quitting:
        return weechat.WEECHAT_RC_OK
    if weechat.buffer_get_string(signal_data, 'plugin') != 'irc':
        return weechat.WEECHAT_RC_OK

    buf_type = weechat.buffer_get_string(signal_data, 'localvar_type')
    if buf_type == 'server':
        # Prevent closing private buffers on this server from triggering saving.
        servers_closing.add(weechat.buffer_get_string(signal_data, 'localvar_server'))
    elif buf_type == 'private':
        info = get_query_info(signal_data)
        # Don't trigger when all buffers close because their server buffer closes
        if info and info[0] not in servers_closing:
            if remove_query(info[0], info[1]):
                save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

def quit_signal_cb(data, signal, signal_data):
    global quitting
    quitting = True
    return weechat.WEECHAT_RC_OK

# signal_data = buffer pointer
def irc_pv_opened_cb(data, signal, signal_data):
    info = get_query_info(signal_data)
    if info:
        debug_print("signal: irc_pv_opened server: %s query: %s" % info)
        if add_query(info[0], info[1]):
            save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

# signal_data = server name
def remove_server_from_servers_closing_cb(data, signal, signal_data):
    if signal_data in servers_closing:
        servers_closing.discard(signal_data)
        debug_print("signal: irc_server_disconnected %s" % signal_data)
    return weechat.WEECHAT_RC_OK

# signal_data = buffer pointer
def irc_server_opened_cb(data, signal, signal_data):
    server_name = weechat.buffer_get_string(signal_data, 'localvar_server')
    servers_opening.add(server_name)
    # a re-created server must not inherit a stale "closing" state
    servers_closing.discard(server_name)
    debug_print("signal: irc_server_opened %s" % server_name)
    return weechat.WEECHAT_RC_OK

# signal_data = servername
def irc_server_connected_signal_cb(data, signal, signal_data):
    # Only reopen the query buffers if the server buffer was recently opened
    if signal_data in servers_opening:
        open_stored_query_buffers_for_server(signal_data)
        servers_opening.discard(signal_data)
        debug_print("signal: irc_server_connected %s" % signal_data)
    return weechat.WEECHAT_RC_OK

# ================================[ file ]===============================
def get_filename_with_path():
    path = weechat.info_get("weechat_data_dir", "") \
        or weechat.info_get("weechat_dir", "")
    return os.path.join(path, queryman_filename)

def load_stored_query_buffers():
    filename = get_filename_with_path()
    queries = {}
    if not os.path.isfile(filename):
        debug_print('No query file "%s"' % filename)
        return queries
    try:
        with open(filename, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2 and valid_server(parts[0]) and valid_nick(parts[1]):
                    nicks = queries.setdefault(parts[0], set())
                    if parts[1].lower() not in (n.lower() for n in nicks):
                        nicks.add(parts[1])
                elif line.strip():
                    debug_print('ignoring invalid line in "%s"' % filename)
    except OSError as e:
        print_error('Error loading query buffers from "%s": %s' % (filename, e))
    return queries

def remove_data_file():
    filename = get_filename_with_path()
    try:
        if os.path.isfile(filename):
            os.remove(filename)
    except OSError as e:
        print_error('Error removing "%s": %s' % (filename, e))

def save_stored_query_buffers_to_file():
    filename = get_filename_with_path()
    if not stored_query_buffers_per_server:
        debug_print("No stored query buffers; removing data file")
        remove_data_file()
        return True

    tmp_filename = filename + '.tmp'
    try:
        fd = os.open(tmp_filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            debug_print("Storing %s servers" % len(stored_query_buffers_per_server))
            for server_name in sorted(stored_query_buffers_per_server):
                nicks = stored_query_buffers_per_server[server_name]
                debug_print("Storing %s queries in server %s" % (len(nicks), server_name))
                for nick in sorted(nicks):
                    f.write('%s %s\n' % (server_name, nick))
        os.replace(tmp_filename, filename)
    except OSError as e:
        print_error('Error writing query buffers to "%s": %s' % (filename, e))
        try:
            os.remove(tmp_filename)
        except OSError:
            pass
        return False
    return True

# ======== [ Stored Query Buffers List ] ==========
def find_nick(nicks, nick):
    """Case-insensitive lookup, returns the stored spelling or None."""
    low = nick.lower()
    for stored in nicks:
        if stored.lower() == low:
            return stored
    return None

def add_query(server_name, nick, enforce_limit=True):
    """Add a query to the stored list. Returns True if the list changed."""
    if not (valid_server(server_name) and valid_nick(nick)):
        debug_print('ignoring query with invalid server/nick')
        return False
    nicks = stored_query_buffers_per_server.get(server_name, set())
    if find_nick(nicks, nick) is not None:
        return False
    limit = opt_int('max_queries_per_server', 100)
    if enforce_limit and limit > 0 and len(nicks) >= limit:
        debug_print('limit of %d queries reached for server %s' % (limit, server_name))
        return False
    stored_query_buffers_per_server.setdefault(server_name, set()).add(nick)
    return True

def remove_query(server_name, nick):
    """Remove a query from the stored list. Returns True if the list changed."""
    nicks = stored_query_buffers_per_server.get(server_name)
    if not nicks:
        return False
    existing = find_nick(nicks, nick)
    if existing is None:
        return False
    nicks.remove(existing)
    if not nicks:
        stored_query_buffers_per_server.pop(server_name, None)
    return True

def merge_current_into_stored():
    changed = False
    for server_name, nicks in get_current_query_buffers().items():
        for nick in nicks:
            if add_query(server_name, nick, enforce_limit=False):
                changed = True
    return changed

# ======== [ Opening ] ==========
def open_query_buffer(server_name, nick):
    if not (valid_server(server_name) and valid_nick(nick)):
        return
    switch_autojoin = weechat.config_get("irc.look.buffer_switch_autojoin")
    noswitch = '0' if weechat.config_boolean(switch_autojoin) else '1'
    debug_print("opening query buffer: %s on server %s" % (nick, server_name))
    # server and nick contain no whitespace (see validation), so TAB is a safe separator
    weechat.hook_timer(1000, 0, 1, 'open_query_timer_cb',
                       '\t'.join((weechat.current_buffer(), noswitch, server_name, nick)))

def open_query_timer_cb(data, remaining_calls):
    parts = data.split('\t')
    if len(parts) != 4:
        return weechat.WEECHAT_RC_OK
    starting_buffer, noswitch, server_name, nick = parts
    if not (valid_server(server_name) and valid_nick(nick)):
        return weechat.WEECHAT_RC_OK
    weechat.command('', '/query %s-server %s %s' % ('-noswitch ' if noswitch == '1' else '', server_name, nick))
    # go back to the buffer we started from, now that the query exists
    weechat.buffer_set(starting_buffer, 'display', 'auto')
    return weechat.WEECHAT_RC_OK

def open_stored_query_buffers_for_server(server_connected):
    nicks = stored_query_buffers_per_server.get(server_connected)
    if not nicks:
        return
    already_open = set(n.lower() for n in get_current_query_buffers().get(server_connected, ()))
    for nick in sorted(nicks):
        if nick.lower() in already_open:
            continue
        debug_print("going to open query buffer: %s on connected server %s" % (nick, server_connected))
        open_query_buffer(server_connected, nick)

# ================================[ command ]===============================
def hook_command_cb(data, buffer, args):
    argv = args.strip().split()
    if argv and argv[0].lower() == 'save':
        merge_current_into_stored()
        if save_stored_query_buffers_to_file():
            weechat.prnt('', '%s: query list saved.' % SCRIPT_NAME)
    else:
        weechat.command('', '/help %s' % SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ weechat options ]===============================
def init_options():
    for option, value in DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]
    OPTIONS[option] = value
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0
        if int(version) >= 0x00030700:
            init_options()
            weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')
            weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC,
                                 'save',
                                 'save : manual saving of the query list (also adds currently open queries)\n'
                                 '\n'
                                 'IRC query buffers are saved to queryman.txt in the WeeChat data directory and\n'
                                 'restored when a server connects after WeeChat start (not on every reconnect).\n'
                                 '\n'
                                 'Options (/set plugins.var.python.queryman.*):\n'
                                 '  debug                  : print debug messages\n'
                                 '  max_queries_per_server : limit for newly opened queries per server (0 = unlimited)\n',
                                 'save',
                                 'hook_command_cb', '')

            stored_query_buffers_per_server = load_stored_query_buffers()

            # servers that are already connected (e.g. script loaded manually)
            for server_name in get_connected_servers():
                open_stored_query_buffers_for_server(server_name)

            merge_current_into_stored()
            save_stored_query_buffers_to_file()

            weechat.hook_signal('quit', 'quit_signal_cb', '')
            weechat.hook_signal('irc_server_opened', 'irc_server_opened_cb', '')
            weechat.hook_signal('irc_server_connected', 'irc_server_connected_signal_cb', '')
            weechat.hook_signal('irc_server_disconnected', 'remove_server_from_servers_closing_cb', '')
            weechat.hook_signal('irc_pv_opened', 'irc_pv_opened_cb', '')
            weechat.hook_signal('buffer_closing', 'buffer_closing_signal_cb', '')
        else:
            print_error('needs WeeChat version 3.7 or higher')
            weechat.command('', '/wait 1ms /python unload %s' % SCRIPT_NAME)
