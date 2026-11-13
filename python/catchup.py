# SPDX-FileCopyrightText: 2026 Nils Görs <libera.#weechat.nils_2>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# catchup.py - overview of what happened while you were away
#
# Requires WeeChat >= 4.0.0.
#
# History:
#
# 2026-11-11, Nils Görs <libera.#weechat.nils_2>:
#     version 0.1.0: initial release
#
# 2026-11-12, Nils Görs <libera.#weechat.nils_2>:
#     version 0.2.0: add option "-debug" in command /catchup, fix catchup
#                    buffer never refreshed again after an error while
#                    opening it
#
# 2026-11-13, Nils Görs <libera.#weechat.nils_2>:
#     version 0.3.0: add option hotlist_counts (numbers of messages taken
#                    from the hotlist), display number of events, fix time
#                    of hotlist with WeeChat >= 4.3.0
import re
import time

try:
    import weechat
    IMPORT_OK = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    IMPORT_OK = False

SCRIPT_NAME = "catchup"
SCRIPT_AUTHOR = "Nils Görs <libera.#weechat.nils_2>"
SCRIPT_VERSION = "0.3.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Overview of unread messages, highlights and active buffers"

SCRIPT_COMMAND = "catchup"

# WeeChat 4.0.0 is required for the new key names ("up", "down", "return")
MIN_WEECHAT_VERSION = 0x04000000

# type of a buffer with formatted content (not a "free" buffer)
BUFFER_TYPE_FORMATTED = 0

# hotlist priorities (index in the hotlist counts)
HOTLIST_LOW = 0
HOTLIST_MESSAGE = 1
HOTLIST_PRIVATE = 2
HOTLIST_HIGHLIGHT = 3
HOTLIST_NUM_PRIORITIES = 4

# values allowed for "-since" and the options default_since / back_since
SINCE_VALUES = (
    "a duration (format: 1d2h30m, units: d = days, h = hours, m = minutes, "
    "s = seconds), \"away\" = all messages since you went away, "
    "\"read_marker\" = unread messages since the read marker of each buffer"
)

SETTINGS = {
    "back_since": (
        "away",
        "messages displayed when the catchup buffer is opened automatically "
        "(see option open_on_back), same values as /catchup -since: "
        + SINCE_VALUES,
    ),
    "char_active": (
        "▲",
        "char displayed before the title of section \"Active buffers\" "
        "(empty = no char)",
    ),
    "char_highlights": (
        "★",
        "char displayed before the title of section \"Highlights\" "
        "(empty = no char)",
    ),
    "char_quiet": (
        "·",
        "char displayed before the title of section \"Quiet\" and between "
        "the buffers in this section (empty = no char)",
    ),
    "close_on_jump": (
        "off",
        "close the catchup buffer when jumping to a buffer",
    ),
    "default_since": (
        "read_marker",
        "messages displayed by /catchup without argument, same values as "
        "/catchup -since: " + SINCE_VALUES,
    ),
    "color_count": (
        "lightgreen",
        "color for the number of messages",
    ),
    "color_highlight": (
        "lightmagenta",
        "color for the number of highlights",
    ),
    "color_section": (
        "yellow",
        "color for the title and section names",
    ),
    "color_visited": (
        "darkgray",
        "color for the lines of buffers you already jumped to",
    ),
    "color_selected": (
        "white,blue",
        "color for the selected line (format: \"fg,bg\")",
    ),
    "hotlist_counts": (
        "off",
        "with \"-since read_marker\", take the number of messages, "
        "highlights and events from the hotlist, so that they are the same "
        "as the numbers displayed by WeeChat in the hotlist; the hotlist "
        "counts lines by priority, so the option message_tags is then "
        "ignored for these numbers",
    ),
    "ignore_buffers": (
        "",
        "comma-separated list of buffers to ignore (full name, wildcard "
        "\"*\" is allowed, a name beginning with \"!\" is excluded), "
        "for example: \"irc.libera.#spam,irc.*.#offtopic*\"",
    ),
    "message_tags": (
        "notify_message,notify_private,notify_highlight",
        "comma-separated list of tags for lines counted as messages, the "
        "other lines (joins, parts, ...) are counted as events; "
        "like in filters, \"+\" means logical \"and\", \"!\" is a negation "
        "and wildcard \"*\" is allowed, for example: "
        "\"irc_privmsg+!self_msg,irc_notice\"; "
        "highlighted lines are always counted as messages",
    ),
    "max_highlights": (
        "20",
        "maximum number of highlights and private messages displayed "
        "(the most recent ones are kept, 0 = hide the section)",
    ),
    "open_on_back": (
        "off",
        "open the catchup buffer automatically when you are back "
        "(on any IRC server: /away without message, or away removed by "
        "another script)",
    ),
    "quiet_max_messages": (
        "5",
        "buffers with at most this number of messages (and no highlight "
        "or private message) "
        "are displayed on a single line in section \"Quiet\" instead of "
        "section \"Active buffers\" (0 = disable)",
    ),
    "refresh_on_highlight": (
        "on",
        "refresh the catchup buffer automatically on a new highlight or "
        "private message (the selected line is kept)",
    ),
    "skip_displayed": (
        "on",
        "skip buffers displayed in a window (you can already see them)",
    ),
    "time_format": (
        "%H:%M",
        "format for times (see man strftime); the date is added "
        "automatically for messages older than 24 hours",
    ),
}

STATE = {
    # pointer to the catchup buffer ("" if not opened)
    "buffer": "",
    # value of "-since": a duration, "away" or "read_marker"
    "since_spec": "read_marker",
    # None = unread messages since read marker, otherwise a timestamp
    "since": None,
    # lines displayed: list of tuples (text, target buffer, key),
    # see function build_lines
    "lines": [],
    # index of the selected line (-1 = no line can be selected)
    "selected": -1,
    # IRC servers where you are away: server name => time you went away
    "away": {},
    # time you went away on the servers where you just came back
    # (servers are not all back at the same time with "/away -all")
    "back_since": None,
    # time you went away the last time (used by "/catchup -since away")
    "last_away": None,
    # hooks on printed lines and buffer/window switch (only while the
    # catchup buffer is opened)
    "hooks": [],
    # buffers you jumped to from the catchup buffer
    "visited": set(),
    # True while the catchup buffer is being opened (no refresh by signals)
    "opening": False,
    # timer for the automatic refresh ("" if no refresh is scheduled)
    "refresh_timer": "",
}

# delay (in milliseconds) before the automatic refresh of the catchup
# buffer, so that many highlights at once cause only one refresh
REFRESH_DELAY = 500

# title of the catchup buffer: help on keys and input (like fset)
BUFFER_TITLE = ("Keys: up/down: select, enter: jump to buffer | "
                "Input: q: close, r: mark all buffers as read, $: refresh")

# delay (in milliseconds) to wait for the answers of all servers when
# you are back, before opening the catchup buffer
BACK_DELAY = 1000


# ============================================================================
# helpers
# ============================================================================

def get_option(name):
    """Return value of a script option."""
    return weechat.config_get_plugin(name)


def get_option_bool(name):
    """Return value of a boolean script option."""
    return weechat.config_string_to_boolean(get_option(name)) == 1


def get_option_int(name, default):
    """Return value of an integer script option."""
    try:
        return int(get_option(name))
    except ValueError:
        return default


def print_error(message):
    """Display an error message in core buffer."""
    weechat.prnt("", f"{weechat.prefix('error')}{SCRIPT_NAME}: {message}")


def plural(count, word):
    """Return count and word, with a "s" if count is not 1."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def pad(text, width):
    """Pad text with spaces to the given width (on screen)."""
    return text + " " * max(0, width - weechat.strlen_screen(text))


def section_title(char, title):
    """Return title of a section, with the char before if not empty."""
    return f"{char} {title}" if char else title


def parse_duration(text):
    """Parse a duration like "1d2h30m" and return number of seconds.

    Return None if the duration is invalid or zero.
    """
    match = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
                         text or "")
    if not text or not match:
        return None
    days, hours, minutes, seconds = (int(value or 0)
                                     for value in match.groups())
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total or None


def format_duration(seconds):
    """Format a number of seconds for display, like "8h 40m"."""
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_time(timestamp):
    """Format a timestamp for display."""
    time_format = get_option("time_format") or "%H:%M"
    if time.time() - timestamp >= 86400:
        time_format = f"%Y-%m-%d {time_format}"
    return time.strftime(time_format, time.localtime(timestamp))


def parse_tag_conditions(text):
    """Parse a list of tags like "irc_privmsg+!self_msg,irc_notice".

    Return a list of conditions (logical "or"), each condition is a list of
    tuples (negation, mask) (logical "and").
    """
    conditions = []
    for condition in text.split(","):
        parts = []
        for tag in condition.split("+"):
            tag = tag.strip()
            negation = tag.startswith("!")
            if negation:
                tag = tag[1:]
            if tag:
                parts.append((negation, tag))
        if parts:
            conditions.append(parts)
    return conditions


def tags_match(tags, conditions):
    """Check if tags of a line match at least one of the conditions."""
    for condition in conditions:
        if all(any(weechat.string_match(tag, mask, 0) for tag in tags)
               != negation
               for negation, mask in condition):
            return True
    return False


def buffer_is_valid(buffer):
    """Check if a buffer pointer still exists."""
    hdata_buffer = weechat.hdata_get("buffer")
    return bool(buffer) and weechat.hdata_check_pointer(
        hdata_buffer,
        weechat.hdata_get_list(hdata_buffer, "gui_buffers"),
        buffer) == 1


def catchup_window():
    """Return current window if it displays the catchup buffer, else ""."""
    window = weechat.current_window()
    if (STATE["buffer"]
            and weechat.window_get_pointer(window, "buffer")
            == STATE["buffer"]):
        return window
    return ""


def windows_with_buffer(buffer):
    """Return list of windows displaying a buffer (there can be many)."""
    windows = []
    hdata_window = weechat.hdata_get("window")
    window = weechat.hdata_get_list(hdata_window, "gui_windows")
    while window:
        if weechat.hdata_pointer(hdata_window, window, "buffer") == buffer:
            windows.append(window)
        window = weechat.hdata_pointer(hdata_window, window, "next_window")
    return windows


def window_command(window, command):
    """Execute a /window command on a given window.

    The command is executed with "-window <number>", so it works on the
    given window, even if this is not the current window.
    """
    number = weechat.window_get_integer(window, "number")
    buffer = weechat.window_get_pointer(window, "buffer")
    weechat.command(buffer, f"/window {command} -window {number}")


def display_buffer(buffer):
    """Display a buffer and return the window used.

    If the buffer is already displayed in a window, this window becomes
    the current window, otherwise the buffer is displayed in the current
    window.
    """
    windows = windows_with_buffer(buffer)
    current = weechat.current_window()
    if current in windows:
        return current
    if windows:
        number = weechat.window_get_integer(windows[0], "number")
        weechat.command("", f"/window {number}")
        return windows[0]
    weechat.buffer_set(buffer, "display", "1")
    return current


# ============================================================================
# collect data
# ============================================================================

def get_hotlist():
    """Return hotlist info: two dicts with buffer pointer as key.

    The first dict has the time the buffer was added to hotlist, the second
    one the number of lines by priority: [low, message, private,
    highlight].
    """
    # variable renamed in WeeChat 4.3.0
    version = int(weechat.info_get("version_number", "") or 0)
    time_var = "time" if version >= 0x04030000 else "creation_time.tv_sec"
    times = {}
    counts = {}
    hdata_hotlist = weechat.hdata_get("hotlist")
    ptr_hotlist = weechat.hdata_get_list(hdata_hotlist, "gui_hotlist")
    while ptr_hotlist:
        buffer = weechat.hdata_pointer(hdata_hotlist, ptr_hotlist, "buffer")
        times[buffer] = weechat.hdata_time(hdata_hotlist, ptr_hotlist,
                                           time_var)
        counts[buffer] = [
            weechat.hdata_integer(hdata_hotlist, ptr_hotlist,
                                  f"{priority}|count")
            for priority in range(HOTLIST_NUM_PRIORITIES)
        ]
        ptr_hotlist = weechat.hdata_pointer(hdata_hotlist, ptr_hotlist,
                                            "next_hotlist")
    return times, counts


def buffer_skipped_displayed(buffer):
    """Check if a buffer is skipped because it is displayed in a window."""
    return (get_option_bool("skip_displayed")
            and weechat.hdata_integer(weechat.hdata_get("buffer"), buffer,
                                      "num_displayed") > 0)


def get_line_tags(hdata_line_data, line_data):
    """Return list of tags of a line."""
    count = weechat.hdata_integer(hdata_line_data, line_data, "tags_count")
    return [weechat.hdata_string(hdata_line_data, line_data,
                                 f"{index}|tags_array")
            for index in range(count)]


def get_scan_limits(buffer, since, hotlist_times):
    """Return (lines, stop_line, min_date) for scanning a buffer.

    The lines are scanned from the last one to the first one, and the scan
    stops on line "stop_line" (excluded) or on the first line older than
    "min_date". Return None if the buffer has nothing to scan.
    """
    hdata_buffer = weechat.hdata_get("buffer")
    hdata_lines = weechat.hdata_get("lines")
    lines = weechat.hdata_pointer(hdata_buffer, buffer, "own_lines")
    if not lines:
        return None
    # buffer displayed in a window: the user can already see it
    if buffer_skipped_displayed(buffer):
        return None
    if since is not None:
        return lines, "", since
    last_read_line = weechat.hdata_pointer(hdata_lines, lines,
                                           "last_read_line")
    if last_read_line:
        return lines, last_read_line, None
    if weechat.hdata_integer(hdata_lines, lines, "first_line_not_read"):
        return lines, "", None
    # no read marker: use the time the buffer was added to hotlist
    if buffer in hotlist_times:
        return lines, "", hotlist_times[buffer]
    return None


def scan_buffer(buffer, since, hotlist_times, tag_conditions):
    """Scan lines of a buffer and return a dict with stats.

    Return None if the buffer has no new lines.
    """
    limits = get_scan_limits(buffer, since, hotlist_times)
    if not limits:
        return None
    lines, stop_line, min_date = limits

    hdata_lines = weechat.hdata_get("lines")
    hdata_line = weechat.hdata_get("line")
    hdata_line_data = weechat.hdata_get("line_data")

    stats = {
        "messages": 0,
        "highlights": 0,
        "other": 0,
        "nicks": set(),
        "important": [],
    }

    ptr_line = weechat.hdata_pointer(hdata_lines, lines, "last_line")
    while ptr_line and ptr_line != stop_line:
        line_data = weechat.hdata_pointer(hdata_line, ptr_line, "data")
        date = weechat.hdata_time(hdata_line_data, line_data, "date")
        if min_date is not None and date < min_date:
            break
        if weechat.hdata_char(hdata_line_data, line_data, "displayed"):
            scan_line(hdata_line_data, line_data, date, stats,
                      tag_conditions)
        ptr_line = weechat.hdata_pointer(hdata_line, ptr_line, "prev_line")

    if not stats["messages"] and not stats["other"]:
        return None
    # lines were scanned backwards
    stats["important"].reverse()
    return stats


def scan_line(hdata_line_data, line_data, date, stats, tag_conditions):
    """Update stats with a line."""
    tags = get_line_tags(hdata_line_data, line_data)
    highlight = weechat.hdata_char(hdata_line_data, line_data,
                                   "highlight") != 0
    if not highlight and not tags_match(tags, tag_conditions):
        # join, part, quit, nick change, etc.
        stats["other"] += 1
        return
    private = "notify_private" in tags
    stats["messages"] += 1
    for tag in tags:
        if tag.startswith("nick_"):
            stats["nicks"].add(tag[5:])
            break
    if highlight:
        stats["highlights"] += 1
    if highlight or private:
        stats["important"].append((
            date,
            weechat.hdata_string(hdata_line_data, line_data, "prefix"),
            weechat.hdata_string(hdata_line_data, line_data, "message"),
        ))


def buffer_stats(buffer, since, hotlist, tag_conditions):
    """Return stats of a buffer (None if nothing new).

    Argument hotlist is a tuple (times, counts) returned by get_hotlist;
    counts is empty if the hotlist counts must not be used.
    """
    hotlist_times, hotlist_counts = hotlist
    stats = scan_buffer(buffer, since, hotlist_times, tag_conditions)
    count = hotlist_counts.get(buffer)
    if count and not buffer_skipped_displayed(buffer):
        # same numbers as the hotlist; nicks and highlights displayed
        # come from the lines scanned
        if stats is None:
            stats = {
                "messages": 0,
                "highlights": 0,
                "other": 0,
                "nicks": set(),
                "important": [],
            }
        stats["messages"] = (count[HOTLIST_MESSAGE]
                             + count[HOTLIST_PRIVATE]
                             + count[HOTLIST_HIGHLIGHT])
        stats["highlights"] = count[HOTLIST_HIGHLIGHT]
        stats["other"] = count[HOTLIST_LOW]
    return stats


def get_hotlist_for_stats(since):
    """Return hotlist info for function buffer_stats."""
    hotlist_times, hotlist_counts = get_hotlist()
    if since is not None or not get_option_bool("hotlist_counts"):
        hotlist_counts = {}
    return hotlist_times, hotlist_counts


def collect(since):
    """Collect stats of all buffers."""
    hotlist = get_hotlist_for_stats(since)
    ignore_buffers = get_option("ignore_buffers")
    tag_conditions = parse_tag_conditions(get_option("message_tags"))
    hdata_buffer = weechat.hdata_get("buffer")

    result = {
        # buffers with messages: list of dicts
        "active": [],
        # buffers with few messages (see option quiet_max_messages)
        "quiet": [],
        # number of buffers without new messages
        "no_messages": 0,
        # highlights and private messages
        "important": [],
    }

    with_messages = []
    buffer = weechat.hdata_get_list(hdata_buffer, "gui_buffers")
    while buffer:
        full_name = weechat.hdata_string(hdata_buffer, buffer, "full_name")
        if (buffer != STATE["buffer"]
                and weechat.hdata_integer(hdata_buffer, buffer, "type")
                == BUFFER_TYPE_FORMATTED
                and not (ignore_buffers
                         and weechat.string_match_list(
                             full_name, ignore_buffers, 0))):
            stats = buffer_stats(buffer, since, hotlist, tag_conditions)
            if stats and stats["messages"]:
                name = weechat.hdata_string(hdata_buffer, buffer, "name")
                number = weechat.hdata_integer(hdata_buffer, buffer,
                                               "number")
                short_name = weechat.hdata_string(hdata_buffer, buffer,
                                                  "short_name")
                with_messages.append({
                    "buffer": buffer,
                    "label": f"{number}. {name}",
                    "short_name": short_name or name,
                    "messages": stats["messages"],
                    "highlights": stats["highlights"],
                    "events": stats["other"],
                    "important": len(stats["important"]),
                    "nicks": len(stats["nicks"]),
                })
                for date, prefix, message in stats["important"]:
                    result["important"].append(
                        (date, buffer, name, prefix, message))
            else:
                result["no_messages"] += 1
        buffer = weechat.hdata_pointer(hdata_buffer, buffer, "next_buffer")

    # buffers with highlights or private messages are never quiet
    quiet_max = get_option_int("quiet_max_messages", 0)
    for item in with_messages:
        if item["messages"] <= quiet_max and not item["important"]:
            result["quiet"].append(item)
        else:
            result["active"].append(item)

    for key in ("active", "quiet"):
        result[key].sort(key=lambda item: (-item["messages"],
                                           -item["highlights"]))
    result["important"].sort(key=lambda item: item[0])
    return result


# ============================================================================
# display
# ============================================================================

def build_lines(data, since):
    """Build list of lines to display.

    Each line is a tuple (text, target, key): target is the buffer to jump
    to ("" if the line can not be selected), key identifies the line to
    keep the selection after a refresh (None if the line can not be
    selected).
    """
    color_section = weechat.color(get_option("color_section"))
    color_count = weechat.color(get_option("color_count"))
    color_highlight = weechat.color(get_option("color_highlight"))
    reset = weechat.color("reset")
    char_highlights = get_option("char_highlights")
    char_active = get_option("char_active")
    char_quiet = get_option("char_quiet")

    lines = []

    if since is None:
        title = "Unread messages since your read markers"
    elif STATE["since_spec"] == "away":
        title = (f"Messages since you went away at {format_time(since)} "
                 f"({format_duration(time.time() - since)})")
    else:
        title = (f"Messages since {format_time(since)} "
                 f"({format_duration(time.time() - since)})")
    lines.append((f"{color_section}{title}{reset}  "
                  f"{weechat.color('chat_delimiters')}"
                  f"[-since {STATE['since_spec']}]{reset}", "", None))
    lines.append(("", "", None))

    # highlights and private messages
    max_highlights = get_option_int("max_highlights", 20)
    if max_highlights > 0:
        important = data["important"]
        lines.append((f"{color_section}"
                      f"{section_title(char_highlights, 'Highlights')} "
                      f"and private messages ({len(important)}){reset}",
                      "", None))
        if len(important) > max_highlights:
            lines.append((f"  (only the last {max_highlights} are "
                          f"displayed)", "", None))
            important = important[-max_highlights:]
        if important:
            width = max(weechat.strlen_screen(item[2]) for item in important)
            for date, buffer, name, prefix, message in important:
                lines.append((f"  {pad(name, width)}  {format_time(date)}  "
                              f"{prefix}{reset} {message}", buffer,
                              ("important", buffer, date, message)))
        else:
            lines.append(("  (none)", "", None))
        lines.append(("", "", None))

    # active buffers
    active = data["active"]
    lines.append((f"{color_section}"
                  f"{section_title(char_active, 'Active buffers')} "
                  f"({len(active)}){reset}", "", None))
    if active:
        width = max(weechat.strlen_screen(item["label"]) for item in active)
        for item in active:
            text = (f"  {pad(item['label'], width)}  "
                    f"{color_count}{plural(item['messages'], 'message')}"
                    f"{reset}")
            if item["events"]:
                text += f", {plural(item['events'], 'event')}"
            text += f", {plural(item['nicks'], 'nick')}"
            if item["highlights"]:
                text += (f", {color_highlight}"
                         f"{plural(item['highlights'], 'highlight')}"
                         f"{reset}")
            lines.append((text, item["buffer"], ("active", item["buffer"])))
    else:
        lines.append(("  (no new messages)", "", None))

    # quiet buffers (all on a single line)
    items = [f"{item['short_name']} {color_count}{item['messages']}{reset}"
             for item in data["quiet"]]
    if data["no_messages"]:
        items.append(f"{plural(data['no_messages'], 'buffer')} "
                     f"without new messages")
    if items:
        separator = f" {char_quiet} " if char_quiet else ", "
        lines.append(("", "", None))
        lines.append((f"{color_section}"
                      f"{section_title(char_quiet, 'Quiet')}{reset}  "
                      f"{separator.join(items)}", "", None))
    return lines


def line_text(index):
    """Return text of a line, with color if selected or visited."""
    text, target, _ = STATE["lines"][index]
    if index == STATE["selected"]:
        return (f"{weechat.color(get_option('color_selected'))}"
                f"{weechat.string_remove_color(text, '')}")
    if target and target in STATE["visited"]:
        return (f"{weechat.color(get_option('color_visited'))}"
                f"{weechat.string_remove_color(text, '')}")
    return text


def render():
    """Display all lines in the catchup buffer."""
    weechat.buffer_clear(STATE["buffer"])
    for index in range(len(STATE["lines"])):
        weechat.prnt_y(STATE["buffer"], index, line_text(index))


def ensure_visible(index):
    """Scroll the catchup window so that the line is visible."""
    window = catchup_window()
    if not window:
        return
    hdata_window = weechat.hdata_get("window")
    hdata_window_scroll = weechat.hdata_get("window_scroll")
    scroll = weechat.hdata_pointer(hdata_window, window, "scroll")
    start_line_y = weechat.hdata_integer(hdata_window_scroll, scroll,
                                         "start_line_y")
    chat_height = weechat.window_get_integer(window, "win_chat_height")
    if index < start_line_y:
        window_command(window, f"scroll -{start_line_y - index}")
    elif index >= start_line_y + chat_height:
        window_command(window,
                       f"scroll +{index - start_line_y - chat_height + 1}")


def find_selection(old_key, old_index):
    """Return index of the line to select after a refresh.

    Search first the line with the same key as before; if the line has
    gone (for example buffer read), select the line at the same place
    (or the line before if it was the last one).
    """
    lines = STATE["lines"]
    if old_key is not None:
        for index, (_, _, key) in enumerate(lines):
            if key == old_key:
                return index
    selectable = [index for index, (_, target, _) in enumerate(lines)
                  if target]
    if not selectable:
        return -1
    if old_index >= 0:
        after = [index for index in selectable if index >= old_index]
        return after[0] if after else selectable[-1]
    return selectable[0]


def refresh(keep_selection=False):
    """Collect data and display it in the catchup buffer.

    If keep_selection is True (automatic refresh), the selected line is
    kept and the window is not scrolled to the top.
    """
    old_key = None
    old_index = -1
    if keep_selection and STATE["selected"] >= 0:
        old_key = STATE["lines"][STATE["selected"]][2]
        old_index = STATE["selected"]
    data = collect(STATE["since"])
    STATE["lines"] = build_lines(data, STATE["since"])
    STATE["selected"] = find_selection(old_key, old_index)
    render()
    if keep_selection:
        if STATE["selected"] >= 0:
            ensure_visible(STATE["selected"])
    else:
        for window in windows_with_buffer(STATE["buffer"]):
            window_command(window, "scroll_top")


def select_move(direction):
    """Move selection to the previous (-1) or next (1) selectable line."""
    old = STATE["selected"]
    if old < 0:
        return
    end = -1 if direction < 0 else len(STATE["lines"])
    for index in range(old + direction, end, direction):
        if STATE["lines"][index][1]:
            STATE["selected"] = index
            weechat.prnt_y(STATE["buffer"], old, line_text(old))
            weechat.prnt_y(STATE["buffer"], index, line_text(index))
            ensure_visible(index)
            return


# ============================================================================
# actions
# ============================================================================

def resolve_since(spec):
    """Convert a value of "-since" to a timestamp.

    Return a tuple (since, error): since is None for "read_marker",
    error is None if the value is valid.
    """
    if spec == "read_marker":
        return None, None
    if spec == "away":
        # currently away: since the first server, otherwise the last time
        away_since = (min(STATE["away"].values()) if STATE["away"]
                      else STATE["last_away"])
        if away_since is None:
            return None, ("you have not been away since the script was "
                          "loaded")
        return away_since, None
    seconds = parse_duration(spec)
    if seconds is None:
        return None, (f"invalid value for -since: \"{spec}\" (examples: "
                      f"30m, 8h, 1d12h, away, read_marker)")
    return int(time.time()) - seconds, None


def open_since(spec):
    """Open the catchup buffer with a value of "-since"."""
    since, error = resolve_since(spec)
    if error:
        print_error(error)
        return
    open_buffer(spec, since)


def open_buffer(spec, since):
    """Open (or refresh) the catchup buffer and display it.

    The argument spec is the value of "-since" (for display), since is
    the timestamp (None = since read markers).
    """
    buffer = weechat.buffer_search("python", SCRIPT_NAME)
    if not buffer:
        buffer = weechat.buffer_new_props(
            SCRIPT_NAME,
            {
                "type": "free",
                "title": BUFFER_TITLE,
                "notify": "0",
                "localvar_set_no_log": "1",
                "key_bind_up": f"/{SCRIPT_COMMAND} -up",
                "key_bind_down": f"/{SCRIPT_COMMAND} -down",
                "key_bind_return": f"/{SCRIPT_COMMAND} -enter",
            },
            "catchup_buffer_input_cb", "",
            "catchup_buffer_close_cb", "")
        if not buffer:
            print_error("unable to create buffer")
            return
    STATE["buffer"] = buffer
    STATE["since_spec"] = spec
    STATE["since"] = since
    STATE["visited"] = set()
    # watch new lines and switches only while the catchup buffer is opened
    if not STATE["hooks"]:
        STATE["hooks"] = [
            weechat.hook_print("", "", "", 0, "catchup_print_cb", ""),
            weechat.hook_signal("buffer_switch", "catchup_switch_cb", ""),
            weechat.hook_signal("window_switch", "catchup_switch_cb", ""),
        ]
    # display the buffer first, so that the read marker of the buffer
    # displayed before in this window is updated; if the catchup buffer
    # is already displayed in another window (split), go to this window
    STATE["opening"] = True
    try:
        display_buffer(buffer)
    finally:
        # always reset the flag, otherwise the buffer would never be
        # refreshed again by signals
        STATE["opening"] = False
    refresh()


def close_buffer(buffer):
    """Close the catchup buffer (if it exists)."""
    if buffer and buffer_is_valid(buffer):
        # the close callback removes the hooks
        weechat.buffer_close(buffer)
    # in case the close callback was not called (no callback any more on a
    # buffer left by a previous instance of the script)
    STATE["buffer"] = ""


def jump():
    """Jump to the buffer of the selected line."""
    if STATE["selected"] < 0:
        return
    target = STATE["lines"][STATE["selected"]][1]
    if not buffer_is_valid(target):
        print_error("this buffer does not exist any more")
        return
    catchup_buffer = STATE["buffer"]
    STATE["visited"].add(target)
    # if the target buffer is already displayed in another window (split),
    # go to this window instead of displaying the buffer twice
    window = display_buffer(target)
    window_command(window, "scroll_unread")
    if get_option_bool("close_on_jump"):
        weechat.buffer_close(catchup_buffer)
    elif windows_with_buffer(catchup_buffer):
        # catchup buffer still visible (split): update it now
        refresh(keep_selection=True)


def mark_all_read():
    """Set read marker at end of all buffers and clear hotlist."""
    hdata_buffer = weechat.hdata_get("buffer")
    buffer = weechat.hdata_get_list(hdata_buffer, "gui_buffers")
    while buffer:
        if (buffer != STATE["buffer"]
                and weechat.hdata_integer(hdata_buffer, buffer, "type")
                == BUFFER_TYPE_FORMATTED):
            weechat.buffer_set(buffer, "unread", "")
            weechat.buffer_set(buffer, "hotlist", "-1")
        buffer = weechat.hdata_pointer(hdata_buffer, buffer, "next_buffer")


def debug_dump():
    """Display debug info in core buffer: period, away times, buffers."""

    def fmt(timestamp):
        if not timestamp:
            return "-"
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    def say(text):
        weechat.prnt("", f"{SCRIPT_NAME}: {text}")

    say("----- debug -----")
    say(f"catchup buffer opened: {'yes' if STATE['buffer'] else 'no'}")
    say(f"-since: {STATE['since_spec']}, start: {fmt(STATE['since'])}")
    away = ", ".join(f"{server}={fmt(value)}"
                     for server, value in sorted(STATE["away"].items()))
    say(f"away now: {away or '-'}")
    say(f"last away: {fmt(STATE['last_away'])}, "
        f"back pending: {fmt(STATE['back_since'])}")
    for option in ("default_since", "back_since", "open_on_back",
                   "skip_displayed", "hotlist_counts", "message_tags",
                   "ignore_buffers", "quiet_max_messages"):
        say(f"option {option} = \"{get_option(option)}\"")

    since = STATE["since"] if STATE["buffer"] else None
    hotlist = get_hotlist_for_stats(since)
    hotlist_times, all_hotlist_counts = get_hotlist()
    ignore_buffers = get_option("ignore_buffers")
    tag_conditions = parse_tag_conditions(get_option("message_tags"))
    hdata_buffer = weechat.hdata_get("buffer")
    hdata_lines = weechat.hdata_get("lines")
    buffer = weechat.hdata_get_list(hdata_buffer, "gui_buffers")
    while buffer:
        name = weechat.hdata_string(hdata_buffer, buffer, "full_name")
        lines = weechat.hdata_pointer(hdata_buffer, buffer, "own_lines")
        read_marker = (weechat.hdata_pointer(hdata_lines, lines,
                                             "last_read_line")
                       if lines else "")
        displayed = weechat.hdata_integer(hdata_buffer, buffer,
                                          "num_displayed")
        info = (f"read_marker={'yes' if read_marker else 'no'}, "
                f"displayed={displayed}, "
                f"hotlist={fmt(hotlist_times.get(buffer))}, "
                f"hotlist_counts={all_hotlist_counts.get(buffer, '-')}")
        if buffer == STATE["buffer"]:
            result = "catchup buffer"
        elif (weechat.hdata_integer(hdata_buffer, buffer, "type")
              != BUFFER_TYPE_FORMATTED):
            result = "skipped (free buffer)"
        elif ignore_buffers and weechat.string_match_list(
                name, ignore_buffers, 0):
            result = "skipped (option ignore_buffers)"
        elif buffer_skipped_displayed(buffer):
            result = "skipped (displayed in a window)"
        else:
            stats = buffer_stats(buffer, since, hotlist, tag_conditions)
            if stats:
                result = (f"{stats['messages']} messages, "
                          f"{stats['highlights']} highlights, "
                          f"{stats['other']} other lines")
            else:
                result = "nothing new"
        say(f"  {name}: {result} ({info})")
        buffer = weechat.hdata_pointer(hdata_buffer, buffer, "next_buffer")
    say("----- end of debug -----")


def handle_input(text):
    """Handle text entered in the catchup buffer."""
    if text == "q":
        weechat.buffer_close(STATE["buffer"])
    elif text == "r":
        mark_all_read()
        refresh()
    elif text == "$":
        refresh()


# ============================================================================
# callbacks
# ============================================================================

def catchup_cmd_cb(_data, _buffer, args):
    """Callback for command /catchup."""
    argv = args.split()
    if not argv:
        open_since(get_option("default_since") or "read_marker")
    elif argv[0] == "-since":
        if len(argv) < 2:
            return weechat.WEECHAT_RC_ERROR
        open_since(argv[1])
    elif argv[0] == "-debug":
        debug_dump()
    elif argv[0] == "-read":
        mark_all_read()
        if STATE["buffer"]:
            refresh()
    elif argv[0] in ("-up", "-down", "-enter"):
        # used by key bindings on the catchup buffer
        if not STATE["buffer"]:
            return weechat.WEECHAT_RC_OK
        if argv[0] == "-up":
            select_move(-1)
        elif argv[0] == "-down":
            select_move(1)
        else:
            text = weechat.buffer_get_string(STATE["buffer"], "input")
            if text.strip():
                # default action of key enter: commands are executed
                # (for example /buffer 1) and other text is sent to the
                # input callback of the catchup buffer (q, r, $);
                # the command is delayed so that it is executed after this
                # callback: commands like /upgrade or /python reload unload
                # the script, and this must not happen while the script is
                # running (Python crashes in Py_EndInterpreter)
                weechat.command_options(STATE["buffer"], "/input return",
                                        {"delay": "1"})
            else:
                jump()
    else:
        return weechat.WEECHAT_RC_ERROR
    return weechat.WEECHAT_RC_OK


def catchup_buffer_input_cb(_data, _buffer, input_data):
    """Callback for input in the catchup buffer."""
    handle_input(input_data.strip())
    return weechat.WEECHAT_RC_OK


def catchup_buffer_close_cb(_data, _buffer):
    """Callback for closing the catchup buffer."""
    for hook in STATE["hooks"]:
        weechat.unhook(hook)
    STATE["hooks"] = []
    if STATE["refresh_timer"]:
        weechat.unhook(STATE["refresh_timer"])
        STATE["refresh_timer"] = ""
    STATE["visited"] = set()
    STATE["buffer"] = ""
    STATE["lines"] = []
    STATE["selected"] = -1
    return weechat.WEECHAT_RC_OK


def catchup_print_cb(_data, buffer, _date, tags, _displayed, highlight,
                     _prefix, _message):
    """Callback for lines printed.

    A new message in a buffer you already jumped to makes it "not visited"
    again, and the catchup buffer is refreshed on a highlight or private
    message.
    """
    if buffer == STATE["buffer"]:
        return weechat.WEECHAT_RC_OK
    tags_list = tags.split(",")
    important = int(highlight) or "notify_private" in tags_list
    visited_changed = False
    if buffer in STATE["visited"] and (
            important
            or tags_match(tags_list,
                          parse_tag_conditions(get_option("message_tags")))):
        STATE["visited"].discard(buffer)
        visited_changed = True
    if ((important or visited_changed)
            and not STATE["refresh_timer"]
            and get_option_bool("refresh_on_highlight")):
        # delay the refresh, to do it only once for many lines
        STATE["refresh_timer"] = weechat.hook_timer(
            REFRESH_DELAY, 0, 1, "catchup_timer_refresh_cb", "")
    elif visited_changed and not STATE["refresh_timer"]:
        # no automatic refresh: just redraw lines without color "visited"
        render()
    return weechat.WEECHAT_RC_OK


def catchup_switch_cb(_data, signal, signal_data):
    """Callback for buffer/window switch: refresh when back in catchup."""
    if not STATE["buffer"] or STATE["opening"]:
        return weechat.WEECHAT_RC_OK
    if signal == "window_switch":
        buffer = weechat.window_get_pointer(signal_data, "buffer")
    else:
        buffer = signal_data
    if buffer == STATE["buffer"]:
        refresh(keep_selection=True)
    return weechat.WEECHAT_RC_OK


def catchup_timer_refresh_cb(_data, _remaining_calls):
    """Callback for timer: automatic refresh of the catchup buffer."""
    # the timer is removed by WeeChat after its single call
    STATE["refresh_timer"] = ""
    if STATE["buffer"]:
        refresh(keep_selection=True)
    return weechat.WEECHAT_RC_OK


def catchup_upgrade_cb(_data, _signal, _signal_data):
    """Callback for signal "upgrade": close the catchup buffer.

    The catchup buffer is a temporary view, it is closed while the script
    and its hooks are still valid, so that it is not kept without its
    callbacks during /upgrade.
    """
    close_buffer(STATE["buffer"])
    return weechat.WEECHAT_RC_OK


def catchup_unload_cb():
    """Callback called when the script is unloaded (or WeeChat quits)."""
    close_buffer(STATE["buffer"])
    return weechat.WEECHAT_RC_OK


def catchup_now_away_cb(_data, signal, _signal_data):
    """Callback for IRC message 306 (RPL_NOWAWAY): you are away."""
    server = signal.split(",", 1)[0]
    # keep the first time (the server can send 306 again)
    STATE["away"].setdefault(server, int(time.time()))
    return weechat.WEECHAT_RC_OK


def catchup_unaway_cb(_data, signal, _signal_data):
    """Callback for IRC message 305 (RPL_UNAWAY): you are back."""
    server = signal.split(",", 1)[0]
    away_since = STATE["away"].pop(server, None)
    if away_since is None:
        return weechat.WEECHAT_RC_OK
    if STATE["back_since"] is None:
        # first server back: wait for the other servers ("/away -all")
        STATE["back_since"] = away_since
        weechat.hook_timer(BACK_DELAY, 0, 1, "catchup_timer_back_cb", "")
    else:
        STATE["back_since"] = min(STATE["back_since"], away_since)
    return weechat.WEECHAT_RC_OK


def catchup_timer_back_cb(_data, _remaining_calls):
    """Callback for timer: open catchup buffer when you are back."""
    away_since = STATE["back_since"]
    STATE["back_since"] = None
    if away_since is None:
        return weechat.WEECHAT_RC_OK
    # earliest time of all servers back at the same time
    STATE["last_away"] = away_since
    if not get_option_bool("open_on_back"):
        return weechat.WEECHAT_RC_OK
    spec = get_option("back_since") or "away"
    if spec == "away":
        # use the time of the servers just back (another server may still
        # be away, it is not taken into account here)
        open_buffer(spec, away_since)
    else:
        open_since(spec)
    return weechat.WEECHAT_RC_OK


# ============================================================================
# init
# ============================================================================

def config_init():
    """Initialize script options."""
    for option, (default, description) in SETTINGS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default)
        weechat.config_set_desc_plugin(
            option, f"{description} (default: \"{default}\")")


def hooks_init():
    """Create command and hooks."""
    weechat.hook_command(
        SCRIPT_COMMAND,
        "Show what happened while you were away",
        "[-since <duration>|away|read_marker] || -read || -debug",
        "-since: show the messages since a given time:\n"
        "          <duration>: messages of the given duration in all "
        "buffers, regardless of read markers; format: 1d2h30m "
        "(units: d = days, h = hours, m = minutes, s = seconds)\n"
        "                away: messages since you went away (if you are "
        "away now) or since the last time you went away\n"
        "         read_marker: unread messages since the read marker of each "
        "buffer\n"
        " -read: mark all buffers as read and clear the hotlist\n"
        "-debug: display in core buffer the period used, the away times and "
        "for each buffer why it is counted or skipped (to report a "
        "problem)\n"
        "\n"
        "Without argument, the value of option "
        f"plugins.var.python.{SCRIPT_NAME}.default_since is used "
        "(default: read_marker).\n"
        "\n"
        "The value of -since is displayed at the top of the catchup "
        "buffer.\n"
        "\n"
        "When you are back (/away without message, on any IRC server), the "
        "catchup buffer is opened automatically if the option "
        f"plugins.var.python.{SCRIPT_NAME}.open_on_back is on; the option "
        f"plugins.var.python.{SCRIPT_NAME}.back_since defines which "
        "messages are displayed.\n"
        "\n"
        "With -since read_marker, the numbers of messages, highlights and "
        "events are taken from the hotlist (same numbers as WeeChat, the "
        f"option plugins.var.python.{SCRIPT_NAME}.message_tags is then "
        "ignored for these numbers) if the option "
        f"plugins.var.python.{SCRIPT_NAME}.hotlist_counts is on.\n"
        "\n"
        "The lines counted as messages are defined by the option "
        f"plugins.var.python.{SCRIPT_NAME}.message_tags, buffers displayed "
        "in a window are skipped if the option "
        f"plugins.var.python.{SCRIPT_NAME}.skip_displayed is on.\n"
        "\n"
        "The catchup buffer is refreshed automatically on a new highlight "
        "or private message if the option "
        f"plugins.var.python.{SCRIPT_NAME}.refresh_on_highlight is on.\n"
        "It is also refreshed when you come back to it, and the buffers "
        "you already jumped to are displayed with the color "
        f"plugins.var.python.{SCRIPT_NAME}.color_visited.\n"
        "\n"
        "Keys and input on the catchup buffer:\n"
        "  up/down: select a line\n"
        "    enter: jump to the buffer of the selected line\n"
        "        q: close the buffer\n"
        "        r: mark all buffers as read\n"
        "        $: refresh the buffer\n"
        "\n"
        "The arguments -up, -down and -enter are used by the key bindings "
        "of the catchup buffer.\n"
        "\n"
        f"Options: /fset plugins.var.python.{SCRIPT_NAME}.*\n"
        "\n"
        "Examples:\n"
        f"  /{SCRIPT_COMMAND}\n"
        f"  /{SCRIPT_COMMAND} -since 8h\n"
        f"  /{SCRIPT_COMMAND} -since 1d12h\n"
        f"  /{SCRIPT_COMMAND} -since away\n"
        f"  /{SCRIPT_COMMAND} -since read_marker",
        "-since away|read_marker|1h|8h|1d || -read || -debug",
        "catchup_cmd_cb", "")
    # answers of IRC servers to the command AWAY, they are received
    # whatever sets the away status (/away, another script, ...)
    weechat.hook_signal("*,irc_in2_306", "catchup_now_away_cb", "")
    weechat.hook_signal("*,irc_in2_305", "catchup_unaway_cb", "")
    # close the catchup buffer before /upgrade (the script is unloaded)
    weechat.hook_signal("upgrade", "catchup_upgrade_cb", "")


def away_init():
    """Get IRC servers where you are already away (script loaded later)."""
    hdata_server = weechat.hdata_get("irc_server")
    if not hdata_server:
        # irc plugin not loaded
        return
    server = weechat.hdata_get_list(hdata_server, "irc_servers")
    while server:
        if weechat.hdata_integer(hdata_server, server, "is_away"):
            away_time = weechat.hdata_time(hdata_server, server,
                                           "away_time")
            name = weechat.hdata_string(hdata_server, server, "name")
            STATE["away"][name] = away_time or int(time.time())
        server = weechat.hdata_pointer(hdata_server, server, "next_server")


def main():
    """Main function."""
    if not weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                            SCRIPT_LICENSE, SCRIPT_DESC,
                            "catchup_unload_cb", ""):
        return
    version = int(weechat.info_get("version_number", "") or 0)
    if version < MIN_WEECHAT_VERSION:
        print_error("WeeChat >= 4.0.0 is required for this script")
        return
    # close a catchup buffer left by a previous instance of the script
    close_buffer(weechat.buffer_search("python", SCRIPT_NAME))
    config_init()
    away_init()
    hooks_init()


if __name__ == "__main__" and IMPORT_OK:
    main()
