# SPDX-FileCopyrightText: 2019-2026 Nils Görs <weechatter@arcor.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 2019-03-13: nils_2, (freenode.#weechat)
#       0.1 : initial release, py3k-ok
#
# 2019-03-19: nils_2, (freenode.#weechat)
#       0.2 : add function exclude hotlist
#
# 2019-03-19: nils_2, (freenode.#weechat)
#       0.3 : add function activity
#
# 2019-03-21: nils_2, (freenode.#weechat)
#       0.4 : workaround for bug https://github.com/weechat/weechat/issues/1325#event-2214793184
#           : workaround for signal buffer_switch, otherwise the warning "/allchan -current" will be printed
#           : add command help
#           : fix "/allchan -current" warning when /server raw is executed
#
# 2019-03-23: nils_2, (freenode.#weechat)
#       0.5 : fix "/allchan -current" warning when signal "buffer_opened" is called
#           : changed default value for hotlist option
#
# 2019-05-09: nils_2, (freenode.#weechat)
#       0.6 : fix hiding of channel buffer when private buffer opens
#
# 2019-09-06: nils_2, (freenode.#weechat)
#       0.7 : fix: ignore "slack" for signal "buffer_switch"
#
# 2020-07-20: Sébastien Helleu
#       0.8 : fix: add missing "/" in /allchan command
#
# 2021-11-06: Sébastien Helleu
#       0.9 : make script compatible with WeeChat >= 3.4
#             (new parameters in function hdata_search)
#
# 2023-09-01: nils_2, (libera.#weechat)
#       1.0 : check for buffer_ptr and for irc buffer
#
# 2023-09-02: nils_2, (libera.#weechat)
#       1.1 : one more check for buffer_ptr
#
# 2023-09-08: nils_2, (libera.#weechat)
#       1.2 : when in non-irc buffers (eg. /server raw) exclude channels are ignored, internal changes
#
# 2024-11-16: nils_2, (libera.#weechat)
#       1.3 : hook_signal(hotlist_changed) fixed.
#
# 2026-09-10: nils_2, (libera.#weechat)
#       1.4 : improve script logic and overall stability, with better error handling
#           : add: /help text

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    raise SystemExit(1)

import fnmatch
import traceback

SCRIPT_NAME = "collapse_channel"
SCRIPT_AUTHOR = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION = "1.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "collapse channel buffers from servers without focus"

# Static metadata (default value + description) for every option. Kept
# separate from OPTIONS (below), which only ever holds the current runtime
# value of each option - that way the descriptions stay available to build
# a full help text later, instead of being overwritten once the script
# reads the option's actual value.
#
# Hotlist priorities in WeeChat: 0=low (joins/parts/...), 1=message,
# 2=private message, 3=highlight.
OPTION_HELP = {
    "enabled": (
        "on",
        'turn the filter on/off (on/off)',
    ),
    "hotlist_min_level": (
        "1",
        'minimum hotlist priority for a channel on a NON-focused server to '
        'be shown anyway: 0=any activity (incl. joins/parts), 1=message, '
        '2=private message, 3=highlight only. Use "off" to never show '
        "channels of other servers, no matter their activity. Channels of "
        "the currently focused server are always shown and are not "
        "affected by this option",
    ),
    "show_server_buffer": (
        "on",
        "keep the server buffer of the focused server visible (on/off)",
    ),
    "show_all_queries": (
        "off",
        "always show every private/query buffer, on every server, "
        "regardless of focused server or unread state (on/off)",
    ),
    "server_exclude": (
        "",
        "always show every buffer of these servers, comma separated, "
        'wildcard "*" allowed (e.g. "libera,oper*")',
    ),
    "channel_exclude": (
        "",
        "always show these channels regardless of server or unread state, "
        'comma separated, wildcard "*" allowed, server independent',
    ),
    "single_channel_exclude": (
        "",
        "always show one specific channel on one specific server, space "
        'separated list of "server.#channel" (e.g. "libera.#weechat")',
    ),
}

# Current value of every option, filled in by init_options(). Never holds
# the (default, description) tuples - only plain strings.
OPTIONS = {}

# Name of the server the user is currently focused on. Updated whenever the
# current buffer is an irc buffer; kept as-is otherwise (e.g. while looking
# at core/fset buffers) so switching to a non-irc buffer doesn't collapse
# everything.
focus_server = ""


# ================================[ safety wrapper ]==========================
def safe_cb(func):
    """Catch any exception in a hook callback.

    A single bad signal must never leave buffers stuck hidden or break the
    script entirely; log the problem to the core buffer and carry on.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - intentionally broad
            try:
                weechat.prints(
                    "",
                    "%s%s: error in %s: %s"
                    % (weechat.prefix("error"), SCRIPT_NAME, func.__name__, exc),
                )
                weechat.prints("", traceback.format_exc())
            except Exception:
                pass
            return weechat.WEECHAT_RC_OK

    wrapper.__name__ = func.__name__
    return wrapper


# ================================[ helpers ]=================================
def option_bool(name, default=True):
    value = OPTIONS.get(name, "").strip().lower()
    if value in ("on", "yes", "1", "true"):
        return True
    if value in ("off", "no", "0", "false"):
        return False
    return default


def get_min_level():
    """Return the minimum hotlist priority to treat as "unread", or None
    if the unread-filter is switched off (show all channels of the server)."""
    value = OPTIONS.get("hotlist_min_level", "1").strip().lower()
    if value in ("off", "none", ""):
        return None
    try:
        return int(value)
    except ValueError:
        return 1  # safe fallback if someone puts garbage into the option


def matches_any(value, patterns_csv):
    """fnmatch-based, case-insensitive match against a comma separated list
    of glob patterns. Never raises."""
    if not value or not patterns_csv:
        return False
    value_lower = value.lower()
    for pattern in patterns_csv.split(","):
        pattern = pattern.strip().lower()
        if pattern and fnmatch.fnmatch(value_lower, pattern):
            return True
    return False


def in_single_exclude(server, channel):
    raw = OPTIONS.get("single_channel_exclude", "")
    if not raw or not server or not channel:
        return False
    target = "%s.%s" % (server, channel)
    return target in raw.split()


def get_all_irc_buffers():
    """Pointers of every buffer currently belonging to the irc plugin.
    Always fetched fresh; never cache these pointers across callbacks.
    """
    buffers = []
    infolist = weechat.infolist_get("buffer", "", "")
    if not infolist:
        return buffers
    try:
        while weechat.infolist_next(infolist):
            buf = weechat.infolist_pointer(infolist, "pointer")
            if buf and weechat.buffer_get_string(buf, "localvar_plugin") == "irc":
                buffers.append(buf)
    finally:
        weechat.infolist_free(infolist)
    return buffers


def get_hotlist_priorities():
    """{buffer_pointer: highest priority currently in the hotlist}."""
    priorities = {}
    infolist = weechat.infolist_get("hotlist", "", "")
    if not infolist:
        return priorities
    try:
        while weechat.infolist_next(infolist):
            buf = weechat.infolist_pointer(infolist, "buffer_pointer")
            if not buf:
                continue
            prio = weechat.infolist_integer(infolist, "priority")
            if buf not in priorities or prio > priorities[buf]:
                priorities[buf] = prio
    finally:
        weechat.infolist_free(infolist)
    return priorities


def get_merged_numbers():
    """Set of buffer numbers that currently have more than one buffer
    merged into them (across ALL plugins, not just irc - a server buffer
    can be merged with the weechat core buffer, for example)."""
    counts = {}
    infolist = weechat.infolist_get("buffer", "", "")
    if not infolist:
        return set()
    try:
        while weechat.infolist_next(infolist):
            number = weechat.infolist_integer(infolist, "number")
            counts[number] = counts.get(number, 0) + 1
    finally:
        weechat.infolist_free(infolist)
    return {number for number, count in counts.items() if count > 1}


def set_hidden(buf, hide):
    want = "1" if hide else "0"
    if weechat.buffer_get_string(buf, "hidden") != want:
        weechat.buffer_set(buf, "hidden", want)


def unhide_all():
    for buf in get_all_irc_buffers():
        set_hidden(buf, False)


# ================================[ core logic ]===============================
def apply_filter():
    global focus_server

    if not option_bool("enabled", True):
        return

    current = weechat.current_buffer()
    if current and weechat.buffer_get_string(current, "localvar_plugin") == "irc":
        focus_server = weechat.buffer_get_string(current, "localvar_server")

    min_level = get_min_level()
    hotlist = get_hotlist_priorities()
    show_server_buffer = option_bool("show_server_buffer", True)
    show_all_queries = option_bool("show_all_queries", False)
    merged_numbers = get_merged_numbers()

    for buf in get_all_irc_buffers():
        # Buffers merged into the same number as another buffer are Ctrl+X
        # material: WeeChat cycles between them, but only among buffers
        # that are NOT hidden. Forcing one of them hidden would silently
        # remove it from that cycle, so merged buffers are always left
        # visible and are exempt from every rule below.
        if weechat.buffer_get_integer(buf, "number") in merged_numbers:
            set_hidden(buf, False)
            continue

        server = weechat.buffer_get_string(buf, "localvar_server")
        btype = weechat.buffer_get_string(buf, "localvar_type")
        channel = weechat.buffer_get_string(buf, "localvar_channel")

        # Excludes always win: these buffers are always shown.
        if (
            matches_any(server, OPTIONS.get("server_exclude", ""))
            or matches_any(channel, OPTIONS.get("channel_exclude", ""))
            or in_single_exclude(server, channel)
        ):
            set_hidden(buf, False)
            continue

        # Query/private buffers are exempted from every other rule when
        # this option is on - they are always shown, on every server.
        if btype == "private" and show_all_queries:
            set_hidden(buf, False)
            continue

        if buf == current:
            set_hidden(buf, False)
            continue

        is_focus_server = bool(focus_server) and server == focus_server

        # Every buffer of the focused server is always shown - channels,
        # private buffers and (unless disabled) its server buffer - no
        # matter whether it currently has unread messages or not.
        if is_focus_server:
            if btype == "server":
                set_hidden(buf, not show_server_buffer)
            else:
                set_hidden(buf, False)
            continue

        # From here on: buffer belongs to a DIFFERENT server than the one
        # currently focused. It is shown only while it carries unread
        # messages at/above hotlist_min_level - this is what makes
        # channels with activity show up across servers. With the
        # unread-filter switched off ("hotlist_min_level" = off) there is
        # no criterion left to show it, so it stays hidden.
        if min_level is None:
            set_hidden(buf, True)
            continue

        prio = hotlist.get(buf)
        has_unread = prio is not None and prio >= min_level
        set_hidden(buf, not has_unread)


# ================================[ signal callbacks ]=========================
@safe_cb
def apply_filter_timer_cb(data, remaining_calls):
    apply_filter()
    return weechat.WEECHAT_RC_OK


@safe_cb
def buffer_switch_cb(data, signal, signal_data):
    # A freshly joined/switched-to buffer may not have localvar_server set
    # yet at the exact moment this signal fires, so defer by one tick.
    weechat.hook_timer(1, 0, 1, "apply_filter_timer_cb", "")
    return weechat.WEECHAT_RC_OK


@safe_cb
def buffer_opened_cb(data, signal, signal_data):
    weechat.hook_timer(1, 0, 1, "apply_filter_timer_cb", "")
    return weechat.WEECHAT_RC_OK


@safe_cb
def buffer_closed_cb(data, signal, signal_data):
    # The closed buffer is simply gone from get_all_irc_buffers() already;
    # no delay needed.
    apply_filter()
    return weechat.WEECHAT_RC_OK


@safe_cb
def window_switch_cb(data, signal, signal_data):
    apply_filter()
    return weechat.WEECHAT_RC_OK


@safe_cb
def hotlist_changed_cb(data, signal, signal_data):
    apply_filter()
    return weechat.WEECHAT_RC_OK


@safe_cb
def irc_server_cb(data, signal, signal_data):
    apply_filter()
    return weechat.WEECHAT_RC_OK


# ================================[ options / command ]=========================
def init_options():
    for option, (default, description) in OPTION_HELP.items():
        weechat.config_set_desc_plugin(
            option, '%s (default: "%s")' % (description, default)
        )
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default)
        OPTIONS[option] = weechat.config_get_plugin(option)


def build_help_text():
    """Full option reference shown by "/help unread_channels", generated
    from OPTION_HELP so the help text can never drift out of sync with the
    options actually implemented."""
    lines = [
        "This script hides irc channel/private/server buffers and shows only:",
        "  - the buffer you are currently looking at",
        "  - every private/query buffer, on any server, if show_all_queries is on",
        "  - EVERY buffer of the server you are currently focused on (channels,",
        "    private buffers, and its server buffer unless show_server_buffer",
        "    is off), whether or not it has unread messages",
        "  - any buffer on a DIFFERENT server that currently has unread",
        "    messages (a hotlist entry at/above option hotlist_min_level)",
        "",
        "Options (set with: /set plugins.var.python.%s.<option> <value>," % SCRIPT_NAME,
        "or interactively with: /fset %s):" % SCRIPT_NAME,
        "",
    ]
    for option in OPTION_HELP:
        default, description = OPTION_HELP[option]
        current = OPTIONS.get(option, default)
        lines.append('  %s (default: "%s", current: "%s")' % (option, default, current))
        lines.append("      %s" % description)
    lines.append("")
    lines.append("Commands:")
    lines.append("  /%s enable   - turn the filter on" % SCRIPT_NAME)
    lines.append("  /%s disable  - turn the filter off and unhide every channel" % SCRIPT_NAME)
    lines.append("  /%s toggle   - switch the filter on/off" % SCRIPT_NAME)
    lines.append("  /%s refresh  - re-apply the filter immediately" % SCRIPT_NAME)
    lines.append("")
    lines.append("Note: this script only affects buffers of the irc plugin.")
    lines.append(
        "Note: buffers merged into the same number (Ctrl+X) are always "
        "left visible and are not affected by any option above."
    )
    lines.append(
        "Note: channels of a disconnected server keep their last hidden "
        "state; they are not forcibly unhidden."
    )
    return "\n".join(lines)


@safe_cb
def config_cb(pointer, name, value):
    option = name.split(".")[-1]
    if option in OPTIONS:
        OPTIONS[option] = value
    if option == "enabled" and not option_bool("enabled", True):
        unhide_all()
    else:
        apply_filter()
    return weechat.WEECHAT_RC_OK


@safe_cb
def command_cb(data, buffer, args):
    args = args.strip().lower()
    if args == "enable":
        weechat.config_set_plugin("enabled", "on")
    elif args == "disable":
        weechat.config_set_plugin("enabled", "off")
    elif args == "toggle":
        weechat.config_set_plugin(
            "enabled", "off" if option_bool("enabled", True) else "on"
        )
    elif args in ("refresh", ""):
        apply_filter()
    else:
        weechat.prints(
            "", '%s: unknown argument "%s", see /help %s' % (SCRIPT_NAME, args, SCRIPT_NAME)
        )
    return weechat.WEECHAT_RC_OK


def shutdown_cb():
    unhide_all()
    return weechat.WEECHAT_RC_OK


# ================================[ main ]=====================================
if __name__ == "__main__":
    if weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "shutdown_cb",
        "",
    ):
        init_options()
        weechat.hook_config(
            "plugins.var.python." + SCRIPT_NAME + ".*", "config_cb", ""
        )
        weechat.hook_command(
            SCRIPT_NAME,
            SCRIPT_DESC,
            "enable || disable || toggle || refresh",
            build_help_text(),
            "enable|disable|toggle|refresh",
            "command_cb",
            "",
        )
        weechat.hook_signal("buffer_switch", "buffer_switch_cb", "")
        weechat.hook_signal("buffer_opened", "buffer_opened_cb", "")
        weechat.hook_signal("buffer_closed", "buffer_closed_cb", "")
        weechat.hook_signal("window_switch", "window_switch_cb", "")
        weechat.hook_signal("hotlist_changed", "hotlist_changed_cb", "")
        weechat.hook_signal("irc_server_connected", "irc_server_cb", "")
        weechat.hook_signal("irc_server_disconnected", "irc_server_cb", "")

        apply_filter()
