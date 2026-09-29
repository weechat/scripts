# SPDX-FileCopyrightText: 2012-2026 Nils Görs <weechatter@arcor.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# 2012-01-22: nils_2,(freenode.#weechat)
#       0.1 : initial release
#
# 2012-01-27: nils_2,(freenode.#weechat)
#       0.2 : fix: bug with split windows removed (reported by meingtsla)
#
# 2012-01-28: nils_2,(freenode.#weechat)
#       0.3 : adapted to bugfix #31158 and new signal hook_signal("window_switch")
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
#
# 2026-09-11: nils_2, (libera.#weechat)
#       0.5 : improve script logic and overall stability, with better error handling
#           : add: /help text

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    raise SystemExit(1)

import traceback

SCRIPT_NAME = "server_autoswitch"
SCRIPT_AUTHOR = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "cycle merged server buffers to match the server of the current channel"


# ================================[ safety wrapper ]==========================
def safe_cb(func):
    """Catch any exception in a hook callback and log it to the core buffer
    instead of letting it break the script or leave a merge group mid-cycle."""

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
def merging_enabled():
    """Fast pre-check: is server-buffer merging switched on at all? Purely
    an optimization to skip the infolist scan for the (very common) case
    where it's off; the actual decision still happens via buffer numbers."""
    option = weechat.config_get("irc.look.server_buffer")
    if not option:
        return True  # option not found (future WeeChat change?) - fail open
    return weechat.config_string(option) != "independent"


def buffers_sharing_number(number):
    """Pointers of every buffer that currently shares this buffer number,
    in the same order WeeChat itself cycles through them. A number held by
    only one buffer means "not merged with anything right now"."""
    members = []
    infolist = weechat.infolist_get("buffer", "", "")
    if not infolist:
        return members
    try:
        while weechat.infolist_next(infolist):
            if weechat.infolist_integer(infolist, "number") == number:
                buf = weechat.infolist_pointer(infolist, "pointer")
                if buf:
                    members.append(buf)
    finally:
        weechat.infolist_free(infolist)
    return members


def cycle_to_server_buffer(target_buf):
    """Cycle target_buf's merge group (if it is merged with anything) until
    target_buf itself becomes the active/displayed member."""
    if not target_buf:
        return
    if weechat.buffer_get_integer(target_buf, "active") == 1:
        return  # already showing - nothing to do

    number = weechat.buffer_get_integer(target_buf, "number")
    group = buffers_sharing_number(number)
    if len(group) < 2:
        return  # not currently merged with anything

    # Bounded: never take more steps than the group has members, so a
    # buffer that unexpectedly never becomes active can't loop forever.
    for _ in range(len(group)):
        active_buf = next(
            (buf for buf in group if weechat.buffer_get_integer(buf, "active") == 1),
            None,
        )
        if active_buf is None:
            return  # shouldn't happen, but don't spin on it
        weechat.command(active_buf, "/input switch_active_buffer")
        if weechat.buffer_get_integer(target_buf, "active") == 1:
            return


def handle_buffer(buf):
    """If buf is an irc channel/private buffer, bring its server buffer to
    the front of its merge group (if merged)."""
    if not buf:
        return
    if not merging_enabled():
        return
    if weechat.buffer_get_string(buf, "localvar_plugin") != "irc":
        return
    if weechat.buffer_get_string(buf, "localvar_type") not in ("channel", "private"):
        return

    servername = weechat.buffer_get_string(buf, "localvar_server")
    if not servername:
        return

    server_buf = weechat.info_get("irc_buffer", servername)
    cycle_to_server_buffer(server_buf)


# ================================[ signal callbacks ]=========================
@safe_cb
def buffer_switch_cb(data, signal, signal_data):
    handle_buffer(signal_data)
    return weechat.WEECHAT_RC_OK


@safe_cb
def window_switch_cb(data, signal, signal_data):
    # signal_data is a window pointer here, not a buffer pointer - resolve
    # the buffer that window is actually showing.
    handle_buffer(weechat.window_get_pointer(signal_data, "buffer"))
    return weechat.WEECHAT_RC_OK


# ================================[ command ]==================================
@safe_cb
def command_cb(data, buffer, args):
    handle_buffer(weechat.current_buffer())
    return weechat.WEECHAT_RC_OK


# ================================[ main ]=====================================
if __name__ == "__main__":
    if weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    ):
        weechat.hook_command(
            SCRIPT_NAME,
            SCRIPT_DESC,
            "",
            "The script only makes sense if you have merged the server buffers.\n\n"
            "This script has no options. It runs automatically on every "
            "buffer switch and window switch.\n\n"
            "Running /%s manually re-syncs the merged server buffer to "
            "the currently viewed channel right away." % SCRIPT_NAME,
            "",
            "command_cb",
            "",
        )
        weechat.hook_signal("buffer_switch", "buffer_switch_cb", "")
        weechat.hook_signal("window_switch", "window_switch_cb", "")

        # Sync once immediately in case a channel is already open when the
        # script gets (re)loaded.
        handle_buffer(weechat.current_buffer())
