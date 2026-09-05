# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2026 PeGaSuS <pegasus@computer4u.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# oidentd.py — WeeChat mini-identd integration
#
# Spins a small RFC 1413 ident server integrated into WeeChat's event loop
# via hook_fd(). oidentd forwards queries to it via:
#
#   force forward <listen_ip> <listen_port>
#
# in /etc/oidentd.conf (inside your user block). The script answers each
# query by looking up which server connection owns that local port, first
# from a proactively-built lport→server cache (populated as soon as each
# socket opens), then falling back to a live hdata walk.
#
# The cache is what solves the reconnect race: the ident query arrives
# immediately after TCP connect, before WeeChat updates hdata with the new
# sock fd. The poll timer detects the new fd within ~50ms and caches the
# lport, so it's ready before the IRC server gets around to querying ident.
#
# Installation:
#   cp oidentd.py ~/.local/share/weechat/python/autoload/oidentd.py
#
# /etc/oidentd.conf:
#   user <you> {
#       default {
#           allow spoof
#           allow spoof_all
#           force forward 127.0.0.1 1113
#       }
#   }
#
# Commands:
#   /oidentd status          — show listener state and port→server map
#   /oidentd debug <server>  — show fd/inode/lport detail for one server
#   /oidentd restart         — rebind the listener
#

import weechat
import os
import socket

SCRIPT_NAME    = "oidentd"
SCRIPT_AUTHOR  = "PeGaSuS"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Mini RFC 1413 ident server integrated into WeeChat's event loop"

_config_file    = None
_config_section = None
_options        = {}

_server_sock    = None   # listening socket
_server_hook    = None   # hook_fd on the listening socket
_client_hooks   = {}     # fd -> (hook, client_sock)

# lport (int) -> server_name  — proactively populated cache
_lport_cache    = {}
# server_name -> hook_timer (while polling for new sock after connecting)
_poll_hooks     = {}

# id -> (hook_timer, client_sock, fport, lport)  — queries deferred while a
# server is mid-connect, so we can retry the lookup instead of answering
# with default_ident immediately on a miss
_pending_replies = {}
_pending_next_id = 0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def config_init():
    global _config_file, _config_section

    _config_file = weechat.config_new("oidentd", "config_reload_cb", "")
    if not _config_file:
        weechat.prnt("", "[oidentd] ERROR: config_new failed")
        return False

    _config_section = weechat.config_new_section(
        _config_file, "main",
        0, 0,
        "", "", "", "", "", "", "", "", "", "",
    )
    if not _config_section:
        weechat.prnt("", "[oidentd] ERROR: config_new_section failed")
        weechat.config_free(_config_file)
        return False

    _options["listen_ip"] = weechat.config_new_option(
        _config_file, _config_section,
        "listen_ip", "string",
        "IP address the mini-identd listens on. Use 127.0.0.1 for IPv4 "
        "loopback or ::1 for IPv6. Must match the 'force forward' address "
        "in /etc/oidentd.conf",
        "", 0, 0, "127.0.0.1", "127.0.0.1", 0,
        "", "", "config_change_cb", "", "", "",
    )

    _options["listen_port"] = weechat.config_new_option(
        _config_file, _config_section,
        "listen_port", "integer",
        "TCP port the mini-identd listens on. Must match the 'force forward' "
        "port in /etc/oidentd.conf. Ports below 1024 require root.",
        "", 1024, 65535, "1113", "1113", 0,
        "", "", "config_change_cb", "", "", "",
    )

    _options["default_ident"] = weechat.config_new_option(
        _config_file, _config_section,
        "default_ident", "string",
        "Ident reply used when no irc.server.<name>.username is set, or when "
        "the queried port does not match any known server connection",
        "", 0, 0, "KRNLPNC", "KRNLPNC", 0,
        "", "", "", "", "", "",
    )

    _options["poll_interval"] = weechat.config_new_option(
        _config_file, _config_section,
        "poll_interval", "integer",
        "How often (in milliseconds) to poll for the server socket fd "
        "after a connection attempt starts, used to populate the lport cache",
        "", 10, 5000, "50", "50", 0,
        "", "", "", "", "", "",
    )

    _options["poll_max"] = weechat.config_new_option(
        _config_file, _config_section,
        "poll_max", "integer",
        "Maximum number of polling attempts before giving up waiting "
        "for the server socket fd (total wait = poll_interval * poll_max ms)",
        "", 1, 200, "20", "20", 0,
        "", "", "", "", "", "",
    )

    _options["reply_retry_interval"] = weechat.config_new_option(
        _config_file, _config_section,
        "reply_retry_interval", "integer",
        "How often (in milliseconds) to retry an ident lookup that missed "
        "while a server is still mid-connect, before giving up and "
        "answering with default_ident",
        "", 5, 1000, "20", "20", 0,
        "", "", "", "", "", "",
    )

    _options["reply_retry_max"] = weechat.config_new_option(
        _config_file, _config_section,
        "reply_retry_max", "integer",
        "Maximum number of retries for a deferred ident reply "
        "(total wait = reply_retry_interval * reply_retry_max ms)",
        "", 1, 200, "25", "25", 0,
        "", "", "", "", "", "",
    )

    _options["verbose"] = weechat.config_new_option(
        _config_file, _config_section,
        "verbose", "boolean",
        "Print routine per-query/per-connect diagnostic messages (cache "
        "hits, replies, defers). Off by default — errors and the "
        "listener start/stop messages always print regardless.",
        "", 0, 0, "off", "off", 0,
        "", "", "", "", "", "",
    )

    weechat.config_read(_config_file)
    return True


def config_reload_cb(data, config_file):
    return weechat.config_read(_config_file)


def config_change_cb(data, option):
    """Rebind automatically when listen_ip or listen_port changes."""
    weechat.prnt("", "[oidentd] config changed — rebinding listener")
    listener_stop()
    listener_start()
    return weechat.WEECHAT_RC_OK


def opt_string(name):
    return weechat.config_string(_options[name])


def opt_integer(name):
    return weechat.config_integer(_options[name])


def opt_boolean(name):
    return weechat.config_boolean(_options[name])


# ---------------------------------------------------------------------------
# /proc helpers — no socket duplication
# ---------------------------------------------------------------------------

def get_lport_for_fd(fd):
    """Return the local port for a socket fd via /proc/net/tcp{,6} inode lookup.
    Returns port (int) or None on failure. Never duplicates the fd."""
    try:
        inode = os.stat("/proc/self/fd/{}".format(fd)).st_ino
        for path in ("/proc/net/tcp6", "/proc/net/tcp"):
            try:
                with open(path) as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) < 10:
                            continue
                        if parts[9] == str(inode):
                            return int(parts[1].split(":")[1], 16)
            except IOError:
                continue
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Ident lookup
# ---------------------------------------------------------------------------

def get_server_ident(server_name):
    """Read irc.server.<name>.username, evaluate it, fall back to default."""
    option = weechat.config_get("irc.server.{}.username".format(server_name))
    ident = ""
    if option:
        raw = weechat.config_string(option)
        if raw:
            ident = weechat.string_eval_expression(raw, {}, {}, {})
    if not ident:
        ident = opt_string("default_ident")
    return ident.replace(" ", "_")[:512] or opt_string("default_ident")


def find_server_by_lport(lport):
    """Look up server name for lport.
    1. Check _lport_cache (populated proactively on connect)
    2. Fall back to live hdata walk
    Returns (server_name, ident) or (None, default_ident)."""

    # 1. Cache hit
    if lport in _lport_cache:
        name = _lport_cache[lport]
        return name, get_server_ident(name)

    # 2. Live hdata walk (covers initial connects where cache may not be ready)
    hdata = weechat.hdata_get("irc_server")
    server = weechat.hdata_get_list(hdata, "irc_servers")
    while server:
        sock_fd = weechat.hdata_integer(hdata, server, "sock")
        if sock_fd != -1:
            port = get_lport_for_fd(sock_fd)
            if port == lport:
                name = weechat.hdata_string(hdata, server, "name")
                _lport_cache[lport] = name  # populate cache for next time
                return name, get_server_ident(name)
        server = weechat.hdata_pointer(hdata, server, "next_server")

    return None, opt_string("default_ident")


# ---------------------------------------------------------------------------
# lport cache management
# ---------------------------------------------------------------------------

def cache_server_lport(server_name):
    """Find the current lport for server_name via hdata and cache it."""
    hdata = weechat.hdata_get("irc_server")
    server = weechat.hdata_get_list(hdata, "irc_servers")
    while server:
        name = weechat.hdata_string(hdata, server, "name")
        if name == server_name:
            sock_fd = weechat.hdata_integer(hdata, server, "sock")
            if sock_fd != -1:
                port = get_lport_for_fd(sock_fd)
                if port:
                    # Remove any old lport entry for this server
                    old = [k for k, v in _lport_cache.items() if v == server_name]
                    for p in old:
                        del _lport_cache[p]
                    if old and old != [port] and opt_boolean("verbose"):
                        weechat.prnt("", "[oidentd] {} lport changed {} → {}".format(
                            server_name, old, port))
                    _lport_cache[port] = server_name
                    if opt_boolean("verbose"):
                        weechat.prnt("", "[oidentd] cached {} → lport {}".format(server_name, port))
                    return True
            return False
        server = weechat.hdata_pointer(hdata, server, "next_server")
    return False


def uncache_server(server_name):
    """Remove all lport cache entries for server_name."""
    removed = [k for k, v in _lport_cache.items() if v == server_name]
    for p in removed:
        del _lport_cache[p]
    if removed and opt_boolean("verbose"):
        weechat.prnt("", "[oidentd] uncached {} (was lport {})".format(
            server_name, removed))


def cb_poll_sock(server_name, remaining_calls):
    """Timer callback: poll until sock != -1, then cache the lport."""
    remaining_calls = int(remaining_calls)

    if cache_server_lport(server_name):
        hook = _poll_hooks.pop(server_name, None)
        if hook:
            weechat.unhook(hook)
        return weechat.WEECHAT_RC_OK

    if remaining_calls <= 1:
        if opt_boolean("verbose"):
            weechat.prnt("", "[oidentd] {} → gave up waiting for socket".format(server_name))
        hook = _poll_hooks.pop(server_name, None)
        if hook:
            weechat.unhook(hook)

    return weechat.WEECHAT_RC_OK


def cb_connecting(data, signal, signal_data):
    """irc_server_connecting — start polling to cache the new lport ASAP."""
    server_name = signal_data
    if server_name in _poll_hooks:
        weechat.unhook(_poll_hooks.pop(server_name))
    hook = weechat.hook_timer(
        opt_integer("poll_interval"), 0, opt_integer("poll_max"),
        "cb_poll_sock", server_name)
    _poll_hooks[server_name] = hook
    return weechat.WEECHAT_RC_OK


def cb_disconnected(data, signal, signal_data):
    """irc_server_disconnected — remove cache entry for this server."""
    server_name = signal_data
    if server_name in _poll_hooks:
        weechat.unhook(_poll_hooks.pop(server_name))
    uncache_server(server_name)
    return weechat.WEECHAT_RC_OK


# ---------------------------------------------------------------------------
# Listener
# ---------------------------------------------------------------------------

def listener_start():
    global _server_sock, _server_hook

    ip   = opt_string("listen_ip")
    port = opt_integer("listen_port")

    try:
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        _server_sock = socket.socket(family, socket.SOCK_STREAM)
        _server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_sock.setblocking(False)
        _server_sock.bind((ip, port))
        _server_sock.listen(8)
    except Exception as e:
        weechat.prnt("", "[oidentd] ERROR binding {}:{} — {}".format(ip, port, e))
        _server_sock = None
        return False

    _server_hook = weechat.hook_fd(
        _server_sock.fileno(),
        1, 0, 0,
        "cb_accept", "",
    )
    weechat.prnt("", "[oidentd] listening on {}:{}".format(ip, port))
    return True


def listener_stop():
    global _server_sock, _server_hook

    for fd, (hook, sock) in list(_client_hooks.items()):
        weechat.unhook(hook)
        try:
            sock.close()
        except Exception:
            pass
    _client_hooks.clear()

    for pending_id, (hook, sock, fport, lport) in list(_pending_replies.items()):
        weechat.unhook(hook)
        try:
            sock.close()
        except Exception:
            pass
    _pending_replies.clear()

    if _server_hook:
        weechat.unhook(_server_hook)
        _server_hook = None
    if _server_sock:
        try:
            _server_sock.close()
        except Exception:
            pass
        _server_sock = None


# ---------------------------------------------------------------------------
# Accept / read callbacks
# ---------------------------------------------------------------------------

def cb_accept(data, fd):
    """hook_fd callback on the listening socket — accept a new client."""
    try:
        client_sock, _ = _server_sock.accept()
        client_sock.setblocking(False)
        fd = client_sock.fileno()
        hook = weechat.hook_fd(fd, 1, 0, 0, "cb_read", str(fd))
        _client_hooks[fd] = (hook, client_sock)
    except Exception as e:
        weechat.prnt("", "[oidentd] accept error: {}".format(e))
    return weechat.WEECHAT_RC_OK


def cb_read(data, fd):
    """hook_fd callback on a client socket — read query and reply."""
    fd = int(data)
    entry = _client_hooks.pop(fd, None)
    if not entry:
        return weechat.WEECHAT_RC_OK
    hook, client_sock = entry
    weechat.unhook(hook)

    deferred = False

    try:
        raw = client_sock.recv(64).decode("ascii", errors="replace").strip()
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            raise ValueError("malformed query: {!r}".format(raw))

        # NOTE: RFC 1413 defines the wire order as
        # "<server-side-port> , <client-side-port>" (their port first, our
        # local port second). But oidentd's `force forward` hands the query
        # to us re-ordered as "<our local port> , <their port>" — confirmed
        # empirically (the first number always matches our own ephemeral
        # port from hdata/status, the second always matches the ircd's
        # port, e.g. 6697). So parts[0] is what we look up, not parts[1].
        lport = int(parts[0])
        fport = int(parts[1])

        server_name, ident = find_server_by_lport(lport)

        if server_name is None:
            # Miss. The real lport may simply not be visible in hdata yet
            # (WeeChat's async connect handoff hasn't landed, or the signal
            # that would have started proactive caching hasn't been handled
            # yet). Don't trust _poll_hooks state here — it's exactly as
            # racy as the thing we're working around. Always give it a
            # short bounded retry window before answering with
            # default_ident.
            defer_reply(client_sock, fport, lport)
            deferred = True
            return weechat.WEECHAT_RC_OK

        reply = "{}, {} : USERID : UNIX : {}\r\n".format(lport, fport, ident)
        client_sock.sendall(reply.encode("ascii"))

        if opt_boolean("verbose"):
            if server_name:
                weechat.prnt("", '[oidentd] {}:{} → {} reply "{}"'.format(
                    lport, fport, server_name, ident))
            else:
                weechat.prnt("", '[oidentd] {}:{} → no match, default reply "{}"'.format(
                    lport, fport, ident))

    except Exception as e:
        weechat.prnt("", "[oidentd] read/reply error: {}".format(e))
        try:
            parts = [p.strip() for p in raw.split(",")]
            client_sock.sendall(
                "{}, {} : ERROR : UNKNOWN-ERROR\r\n".format(
                    parts[0] if len(parts) > 0 else "0",
                    parts[1] if len(parts) > 1 else "0",
                ).encode("ascii"))
        except Exception:
            pass
    finally:
        if not deferred:
            try:
                client_sock.close()
            except Exception:
                pass

    return weechat.WEECHAT_RC_OK


def defer_reply(client_sock, fport, lport):
    """Hold a client connection open and retry the lookup on a timer
    instead of answering immediately with default_ident. Closes the
    socket itself once resolved or once retries are exhausted."""
    global _pending_next_id

    _pending_next_id += 1
    pending_id = str(_pending_next_id)

    if opt_boolean("verbose"):
        weechat.prnt("", "[oidentd] {} miss, deferring — cache at defer time: {}".format(
            lport, _lport_cache))

    hook = weechat.hook_timer(
        opt_integer("reply_retry_interval"), 0, opt_integer("reply_retry_max"),
        "cb_retry_reply", pending_id)
    _pending_replies[pending_id] = (hook, client_sock, fport, lport)


def send_pending_reply(pending_id, server_name, ident):
    entry = _pending_replies.pop(pending_id, None)
    if not entry:
        return
    hook, client_sock, fport, lport = entry
    weechat.unhook(hook)
    try:
        reply = "{}, {} : USERID : UNIX : {}\r\n".format(lport, fport, ident)
        client_sock.sendall(reply.encode("ascii"))
        if opt_boolean("verbose"):
            if server_name:
                weechat.prnt("", '[oidentd] {}:{} → {} reply "{}" (deferred)'.format(
                    lport, fport, server_name, ident))
            else:
                weechat.prnt("", '[oidentd] {}:{} → no match after retry, default reply "{}"'.format(
                    lport, fport, ident))
    except Exception as e:
        weechat.prnt("", "[oidentd] deferred reply error: {}".format(e))
    finally:
        try:
            client_sock.close()
        except Exception:
            pass


def cb_retry_reply(pending_id, remaining_calls):
    """Timer callback: retry a deferred lookup until it hits or times out."""
    entry = _pending_replies.get(pending_id)
    if not entry:
        return weechat.WEECHAT_RC_OK

    _, _, _, lport = entry
    server_name, ident = find_server_by_lport(lport)

    if server_name is not None:
        send_pending_reply(pending_id, server_name, ident)
        return weechat.WEECHAT_RC_OK

    if int(remaining_calls) <= 1:
        # Retries exhausted — answer with default_ident rather than
        # holding the connection open indefinitely.
        if opt_boolean("verbose"):
            weechat.prnt("", "[oidentd] {} giving up — cache at give-up time: {}".format(
                lport, _lport_cache))
        send_pending_reply(pending_id, None, opt_string("default_ident"))

    return weechat.WEECHAT_RC_OK


# ---------------------------------------------------------------------------
# /oidentd command
# ---------------------------------------------------------------------------

def cb_command(data, buffer, args):
    parts = args.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""

    if cmd == "status":
        if _server_sock:
            weechat.prnt("", "[oidentd] listening on {}:{}".format(
                opt_string("listen_ip"), opt_integer("listen_port")))
        else:
            weechat.prnt("", "[oidentd] listener is NOT running")
        weechat.prnt("", "[oidentd] lport cache: {}".format(_lport_cache))
        hdata = weechat.hdata_get("irc_server")
        server = weechat.hdata_get_list(hdata, "irc_servers")
        while server:
            name = weechat.hdata_string(hdata, server, "name")
            sock_fd = weechat.hdata_integer(hdata, server, "sock")
            if sock_fd != -1:
                port = get_lport_for_fd(sock_fd)
                cached = _lport_cache.get(port) == name if port else False
                weechat.prnt("", '[oidentd]   {} → lport {} ident "{}" cache={}'.format(
                    name, port or "?", get_server_ident(name), cached))
            server = weechat.hdata_pointer(hdata, server, "next_server")

    elif cmd == "debug" and len(parts) > 1:
        server_name = parts[1]
        hdata = weechat.hdata_get("irc_server")
        server = weechat.hdata_get_list(hdata, "irc_servers")
        while server:
            name = weechat.hdata_string(hdata, server, "name")
            if name == server_name:
                sock_fd = weechat.hdata_integer(hdata, server, "sock")
                weechat.prnt("", "[oidentd] {} sock_fd={}".format(name, sock_fd))
                if sock_fd != -1:
                    try:
                        inode = os.stat("/proc/self/fd/{}".format(sock_fd)).st_ino
                        weechat.prnt("", "[oidentd] inode={}".format(inode))
                    except Exception as e:
                        weechat.prnt("", "[oidentd] stat error: {}".format(e))
                    port = get_lport_for_fd(sock_fd)
                    weechat.prnt("", "[oidentd] lport={}".format(port))
                    cached = _lport_cache.get(port) if port else None
                    weechat.prnt("", "[oidentd] cache entry for lport: {}".format(cached))
                break
            server = weechat.hdata_pointer(hdata, server, "next_server")

    elif cmd == "restart":
        weechat.prnt("", "[oidentd] restarting listener...")
        listener_stop()
        listener_start()

    else:
        weechat.prnt("", "[oidentd] commands: status | debug <server> | restart")

    return weechat.WEECHAT_RC_OK


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

def shutdown_cb():
    listener_stop()
    weechat.config_write(_config_file)
    return weechat.WEECHAT_RC_OK


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                    SCRIPT_LICENSE, SCRIPT_DESC, "shutdown_cb", ""):
    if config_init():
        listener_start()
        weechat.hook_signal("irc_server_connecting",   "cb_connecting",   "")
        weechat.hook_signal("irc_server_disconnected", "cb_disconnected", "")
        weechat.hook_command(
            "oidentd",
            "Mini-identd management",
            "status | debug <server> | restart",
            "   status: show listener state, lport cache, and per-server map\n"
            "    debug: show fd/inode/lport detail for one server\n"
            "  restart: rebind the listener (after changing listen_ip/listen_port)",
            "status || debug %(irc_servers) || restart",
            "cb_command", "",
        )
        weechat.prnt("", "[oidentd] loaded (PID {}) — default ident: {}".format(
            os.getpid(), opt_string("default_ident")))
    else:
        weechat.prnt("", "[oidentd] ERROR: failed to initialize config")