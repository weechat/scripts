"""Marquee-style auto-scrolling for long buffer titles."""

SCRIPT_NAME = "title_scroll"
SCRIPT_AUTHOR = "nleytem"
SCRIPT_EMAIL = "nmleytem@gmail.com"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "GPL-3.0-only"
SCRIPT_DESC = (
    "Auto-scrolls buffer titles that don't fit the window width, "
    "marquee-style, with a marker between the end and repeated start "
    "(note: embedded title colors are stripped while scrolling)"
)
COPYRIGHT = "SPDX-FileCopyrightText: 2026 Nick Leytem <nmleytem@gmail.com>"
LICENSE = "SPDX-License-Identifier: GPL-3.0-only"

try:
    import weechat  # type: ignore[import]
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    IMPORT_OK = False

SETTINGS = {
    "enabled": (
        "on",
        "enable/disable scrolling (off: item shows static/truncated text)",
    ),
    "interval": (
        "200",
        "milliseconds between each scroll step (lower = faster)",
    ),
    "step": (
        "1",
        "characters to advance per scroll step (higher = faster)",
    ),
    "pause": (
        "2",
        "scroll steps to pause when a title's loop restarts (0: no pause)",
    ),
    "separator": (
        " • ",
        "text inserted between the end and the repeated start of a "
        "scrolled title",
    ),
    "width_margin": (
        "2",
        "characters subtracted from the window width when deciding "
        "if/how much to scroll",
    ),
    "text_color": (
        "",
        "WeeChat color name for the title text (empty: bar's default "
        "foreground color)",
    ),
    "separator_color": (
        "cyan",
        "WeeChat color name for the separator marker (empty: same "
        "color as the title text)",
    ),
}

# buffer pointer -> {"offset": int, "pause_left": int}
SCROLL_STATE = {}

TIMER_HOOK = None


def get_str(name):
    return weechat.config_get_plugin(name)


def get_int(name):
    try:
        return int(weechat.config_get_plugin(name))
    except (TypeError, ValueError):
        return 0


def is_enabled():
    return get_str("enabled") == "on"


def title_scroll_build_cb(data, item, window):
    if not window:
        window = weechat.current_window()
    buffer = weechat.window_get_pointer(window, "buffer")
    if not buffer:
        buffer = weechat.current_buffer()

    title = weechat.buffer_get_string(buffer, "title")
    plain = weechat.string_remove_color(title, "")
    if not plain:
        return ""

    margin = get_int("width_margin")
    width = weechat.window_get_integer(window, "win_width") - margin
    if width < 1:
        width = 1

    text_color_name = get_str("text_color")
    color_text = weechat.color(text_color_name) if text_color_name else weechat.color("bar_fg")

    if len(plain) <= width:
        return "%s%s" % (color_text, plain)

    separator = get_str("separator")
    sep_color_name = get_str("separator_color")
    color_sep = weechat.color(sep_color_name) if sep_color_name else color_text

    cycle_len = len(plain) + len(separator)
    state = SCROLL_STATE.get(buffer, {"offset": 0, "pause_left": 0})
    offset = state.get("offset", 0) % cycle_len if cycle_len else 0

    looped = plain + separator + plain
    src = ("T" * len(plain)) + ("S" * len(separator)) + ("T" * len(plain))
    chunk = looped[offset:offset + width]
    chunk_src = src[offset:offset + width]

    out = []
    current = None
    for ch, s in zip(chunk, chunk_src):
        col = color_sep if s == "S" else color_text
        if col != current:
            out.append(col)
            current = col
        out.append(ch)
    return "".join(out)


def title_scroll_timer_cb(data, remaining_calls):
    if not is_enabled():
        return weechat.WEECHAT_RC_OK

    step = max(get_int("step"), 1)
    pause_ticks = get_int("pause")
    margin = get_int("width_margin")
    separator = get_str("separator")

    active_buffers = set()
    any_scrolling = False

    infolist = weechat.infolist_get("window", "", "")
    if infolist:
        while weechat.infolist_next(infolist):
            buffer = weechat.infolist_pointer(infolist, "buffer")
            if not buffer:
                continue
            win_width = weechat.infolist_integer(infolist, "win_width") - margin
            if win_width < 1:
                win_width = 1

            title = weechat.buffer_get_string(buffer, "title")
            plain = weechat.string_remove_color(title, "")
            active_buffers.add(buffer)

            if len(plain) <= win_width:
                continue

            any_scrolling = True
            cycle_len = len(plain) + len(separator)
            state = SCROLL_STATE.setdefault(buffer, {"offset": 0, "pause_left": 0})
            if state["pause_left"] > 0:
                state["pause_left"] -= 1
            else:
                new_offset = state["offset"] + step
                if cycle_len and new_offset >= cycle_len:
                    new_offset %= cycle_len
                    if pause_ticks:
                        state["pause_left"] = pause_ticks
                state["offset"] = new_offset
        weechat.infolist_free(infolist)

    for buf in list(SCROLL_STATE.keys()):
        if buf not in active_buffers:
            del SCROLL_STATE[buf]

    if any_scrolling:
        weechat.bar_item_update(BAR_ITEM_NAME)

    return weechat.WEECHAT_RC_OK


def title_scroll_title_changed_cb(data, signal, signal_data):
    buffer = signal_data
    if buffer in SCROLL_STATE:
        SCROLL_STATE[buffer] = {"offset": 0, "pause_left": 0}
    weechat.bar_item_update(BAR_ITEM_NAME)
    return weechat.WEECHAT_RC_OK


def title_scroll_setup_timer():
    global TIMER_HOOK
    if TIMER_HOOK:
        weechat.unhook(TIMER_HOOK)
        TIMER_HOOK = None
    if is_enabled():
        interval = max(get_int("interval"), 10)
        TIMER_HOOK = weechat.hook_timer(interval, 0, 0, "title_scroll_timer_cb", "")


def title_scroll_config_cb(data, option, value):
    if option.endswith(".enabled") or option.endswith(".interval"):
        title_scroll_setup_timer()
    return weechat.WEECHAT_RC_OK


def title_scroll_cmd_cb(data, buffer, args):
    args = args.strip()
    if args == "enable":
        weechat.config_set_plugin("enabled", "on")
        weechat.prnt("", "%s: enabled" % SCRIPT_NAME)
    elif args == "disable":
        weechat.config_set_plugin("enabled", "off")
        weechat.prnt("", "%s: disabled" % SCRIPT_NAME)
    elif args == "reset":
        SCROLL_STATE.clear()
        weechat.bar_item_update(BAR_ITEM_NAME)
        weechat.prnt("", "%s: scroll positions reset" % SCRIPT_NAME)
    else:
        status = "enabled" if is_enabled() else "disabled"
        weechat.prnt(
            "",
            "%s: %s (interval=%sms step=%s pause=%s)"
            % (SCRIPT_NAME, status, get_int("interval"), get_int("step"), get_int("pause")),
        )
    return weechat.WEECHAT_RC_OK


def title_scroll_unload_script():
    global TIMER_HOOK
    if TIMER_HOOK:
        weechat.unhook(TIMER_HOOK)
        TIMER_HOOK = None
    return weechat.WEECHAT_RC_OK


def title_scroll_main():
    if not weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "title_scroll_unload_script",
        "",
    ):
        return

    version = weechat.info_get("version_number", "") or 0
    for option, value in SETTINGS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
        if int(version) >= 0x00030500:
            weechat.config_set_desc_plugin(
                option, '%s (default: "%s")' % (value[1], value[0])
            )

    weechat.bar_item_new(BAR_ITEM_NAME, "title_scroll_build_cb", "")
    weechat.hook_signal("buffer_title_changed", "title_scroll_title_changed_cb", "")
    weechat.hook_config(
        "plugins.var.python.%s.*" % SCRIPT_NAME, "title_scroll_config_cb", ""
    )
    weechat.hook_command(
        "title_scroll",
        "Control the scrolling title bar item",
        "enable|disable|status|reset",
        "  enable: turn scrolling on\n"
        " disable: turn scrolling off (item still shows static/truncated text)\n"
        "  status: show current settings\n"
        "   reset: reset all scroll positions to the start\n"
        "\n"
        "Add the item to your title bar with:\n"
        '  /set weechat.bar.title.items "%s"' % BAR_ITEM_NAME,
        "enable|disable|status|reset",
        "title_scroll_cmd_cb",
        "",
    )

    title_scroll_setup_timer()
    weechat.prnt(
        "",
        '%s: add the scrolling title item to your bar with: '
        '/set weechat.bar.title.items "%s"' % (SCRIPT_NAME, BAR_ITEM_NAME),
    )


if __name__ == "__main__" and IMPORT_OK:
    title_scroll_main()
