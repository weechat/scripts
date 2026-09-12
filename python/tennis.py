# SPDX-FileCopyrightText: 2026 Ben Abulafia <ben@synapsereality.io>
#
# SPDX-License-Identifier: GPL-3.0-or-later
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#
# Live tennis scores and rankings, on demand, from the Live Tennis API.
#
# Every command prints one line per match: surnames, set scores, the points
# of the game in progress, "*" against the player serving and "BP" when the
# receiver is one point from a break.
#
# An API key is required; free keys need no card and are limited to 30
# requests per minute and 100 per day, so this script only ever talks to the
# network when you run a command. It installs no timer and polls nothing.
#
#     /set plugins.var.python.tennis.api_key "your-key"
#
# The option is evaluated, so a key kept in the secured data is fine:
#
#     /secure set livetennisapi your-key
#     /set plugins.var.python.tennis.api_key "${sec.data.livetennisapi}"
#
# settings:
# plugins.var.python.tennis.api_key (default: "")
# plugins.var.python.tennis.max_matches (default: 10)
# plugins.var.python.tennis.timeout (default: 10)
#
# History:
# 2026-09-12, Ben Abulafia <ben@synapsereality.io>
#     v1.0.0: initial release
#

import json

import weechat

SCRIPT_NAME = "tennis"
SCRIPT_AUTHOR = "Ben Abulafia <ben@synapsereality.io>"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Live tennis scores and ATP/WTA rankings on demand"

API_URL = "https://api.livetennisapi.com/api/public/v1"
SIGNUP_URL = "https://livetennisapi.com"

# WeeChat 4.1.0 is the first release with hook_url
MIN_VERSION = 0x04010000

OPTIONS = {
    "api_key": (
        "",
        ("Live Tennis API key (free keys, no card, at " + SIGNUP_URL
         + "); the value is evaluated, so \"${sec.data.livetennisapi}\" "
           "works"),
    ),
    "max_matches": (
        "10",
        ("maximum number of matches or ranking rows printed by one "
         "command (1-50)"),
    ),
    "timeout": (
        "10",
        "timeout for one API request, in seconds (1-60)",
    ),
}

# Marks the player serving, appended to the surname.
SERVE_MARK = "*"

# In-game points from which the server can still be broken; the receiver
# reaching 40 against any of these is a break point.
SERVER_BEHIND = ("0", "15", "30")

# Lower-case name particles that belong to the surname, so that
# "Botic van de Zandschulp" prints as "van de Zandschulp".
PARTICLES = (
    "bin", "da", "de", "del", "della", "der", "di", "dos", "du", "la", "le",
    "ten", "ter", "van", "von",
)

# Error codes the API returns, mapped to one line of plain English.
API_ERRORS = {
    "rate_limited": "rate limit reached (a free key allows 30 requests per "
                    "minute and 100 per day)",
    "abuse_throttled": "requests are being throttled; wait before retrying",
    "upgrade_required": "this data is not included in your plan",
    "not_found": "no match with that id",
}


def as_dict(value):
    """Return value when it is a dict, an empty dict otherwise."""
    return value if isinstance(value, dict) else {}


def option(name):
    """Return the current value of a script option."""
    return weechat.config_get_plugin(name)


def option_int(name, minimum, maximum):
    """Return an integer option, clamped to the given range."""
    default = int(OPTIONS[name][0])
    try:
        value = int(option(name))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def api_key():
    """Return the API key, evaluated so that /secure data can be used."""
    key = weechat.string_eval_expression(option("api_key"), {}, {}, {})
    return key.strip()


def print_line(full_name, text):
    """Print one line on the buffer the command was run from."""
    buffer_pointer = weechat.buffer_search("==", full_name)
    if not buffer_pointer:
        buffer_pointer = weechat.current_buffer()
    weechat.prnt(buffer_pointer, text)


def print_error(full_name, text):
    """Print one error line on the buffer the command was run from."""
    print_line(
        full_name,
        "%s%s: %s" % (weechat.prefix("error"), SCRIPT_NAME, text),
    )


def surname(name):
    """Return the surname used to identify a player on one line.

    Copes with the shapes the feed uses: "Novak Djokovic", "Djokovic, Novak",
    "Djokovic N." and the "Name/Name" of a doubles team.
    """
    if not name:
        return "?"
    name = str(name).strip()
    if not name:
        return "?"
    if "/" in name:
        return "/".join(surname(part) for part in name.split("/"))
    if "," in name:
        return name.split(",")[0].strip() or "?"
    tokens = name.split()
    # Drop trailing initials, so that "Djokovic N." keeps only "Djokovic".
    while len(tokens) > 1 and len(tokens[-1].rstrip(".")) <= 1:
        tokens.pop()
    if len(tokens) == 1:
        return tokens[0]
    for index, token in enumerate(tokens[:-1]):
        if token.lower() in PARTICLES:
            return " ".join(tokens[index:])
    return tokens[-1]


def server_of(score):
    """Return 1 or 2 for the player serving, or 0 when it is not known."""
    try:
        server = int(as_dict(score).get("server"))
    except (TypeError, ValueError):
        return 0
    return server if server in (1, 2) else 0


def format_sets(games):
    """Render the per-set game counts as "6-4 3-6 2-1".

    The API is player-major: games is [games_p1, games_p2], each a per-set
    list, so [[6, 3, 2], [4, 6, 1]] reads 6-4, 3-6, 2-1.
    """
    if not isinstance(games, list) or len(games) < 2:
        return ""
    first = games[0] if isinstance(games[0], list) else []
    second = games[1] if isinstance(games[1], list) else []
    sets = []
    for index in range(max(len(first), len(second))):
        won = first[index] if index < len(first) else None
        lost = second[index] if index < len(second) else None
        if won is None and lost is None:
            continue
        sets.append(
            "%s-%s" % (
                "?" if won is None else won,
                "?" if lost is None else lost,
            )
        )
    return " ".join(sets)


def format_points(score):
    """Render the game in progress, "40-30", or "TB 5-3" in a tiebreak.

    Point entries can be null on a match that has just finished, in which
    case there is nothing to show.
    """
    points = as_dict(score).get("points")
    if not isinstance(points, list) or len(points) < 2:
        return ""
    if points[0] is None or points[1] is None:
        return ""
    prefix = "TB " if as_dict(score).get("is_tiebreak") else ""
    return "%s%s-%s" % (prefix, points[0], points[1])


def is_break_point(score):
    """Return True when the receiver is one point from breaking serve.

    That is the receiver holding advantage, or the receiver at 40 while the
    server is still at 0, 15 or 30. Deuce and an advantage to the server are
    not break points, and neither is anything inside a tiebreak, where no
    service game is at stake.
    """
    score = as_dict(score)
    if score.get("is_tiebreak"):
        return False
    server = server_of(score)
    if not server:
        return False
    points = score.get("points")
    if not isinstance(points, list) or len(points) < 2:
        return False
    server_point = points[server - 1]
    receiver_point = points[2 - server]
    if server_point is None or receiver_point is None:
        return False
    server_point = str(server_point).upper()
    receiver_point = str(receiver_point).upper()
    if receiver_point == "AD":
        return True
    return receiver_point == "40" and server_point in SERVER_BEHIND


def match_context(match):
    """Return the tournament and round of a match, for the end of the line."""
    parts = [str(match.get("tournament") or "").strip()]
    round_name = str(match.get("round") or "").strip()
    if round_name:
        parts.append(round_name)
    return ", ".join(part for part in parts if part)


def format_match(match):
    """Render one match on one line."""
    score = as_dict(match.get("score"))
    players = as_dict(match.get("players"))
    names = [
        surname(as_dict(players.get("p1")).get("name")),
        surname(as_dict(players.get("p2")).get("name")),
    ]
    server = server_of(score)
    if server:
        names[server - 1] += SERVE_MARK
    fields = [
        "%s%s%s" % (
            weechat.color("chat_delimiters"),
            match.get("id", "?"),
            weechat.color("reset"),
        ),
        "%s v %s" % (names[0], names[1]),
    ]
    for text in (format_sets(score.get("games")), format_points(score)):
        if text:
            fields.append(text)
    if is_break_point(score):
        fields.append(
            "%sBP%s" % (weechat.color("red"), weechat.color("reset"))
        )
    context = match_context(match)
    if context:
        fields.append(
            "%s%s%s" % (
                weechat.color("darkgray"), context, weechat.color("reset")
            )
        )
    return "  ".join(fields)


def format_movement(record):
    """Render the weekly move of a ranking row, "+2", "-1" or "=" ."""
    rank = record.get("rank")
    previous = record.get("previous_rank")
    if not isinstance(rank, int) or not isinstance(previous, int):
        return ""
    moved = previous - rank
    if moved == 0:
        return "="
    return "%+d" % moved


def format_ranking(record):
    """Render one ranking row on one line."""
    rank = record.get("rank")
    points = record.get("points")
    fields = [
        "%3s" % ("?" if rank is None else rank),
        str(record.get("player_name") or "?"),
    ]
    if points is not None:
        fields.append("%s pts" % points)
    movement = format_movement(record)
    if movement:
        fields.append(
            "%s%s%s" % (
                weechat.color("darkgray"), movement, weechat.color("reset")
            )
        )
    return "  ".join(fields)


def http_message(code, payload):
    """Return one readable line for a response that was not a success."""
    api_code = ""
    detail = ""
    if isinstance(payload, dict):
        api_code = str(payload.get("error") or "")
        detail = str(payload.get("detail") or "")
    if api_code in API_ERRORS:
        return API_ERRORS[api_code]
    if code == 401:
        return ("API key rejected; check "
                "plugins.var.python.%s.api_key" % SCRIPT_NAME)
    if code == 403:
        return "this data is not included in your plan"
    if code == 404:
        return "no match with that id"
    if code == 410:
        return "that match is no longer served"
    if code == 429:
        return API_ERRORS["rate_limited"]
    if detail:
        return "%s (HTTP %d)" % (detail, code)
    if api_code:
        return "%s (HTTP %d)" % (api_code, code)
    return "the API returned HTTP %d" % code


def read_response(output):
    """Return (payload, error) for a hook_url result; one of the two is set."""
    transfer = str(output.get("error") or "").strip()
    if transfer:
        return None, "request failed (%s)" % transfer
    try:
        code = int(output.get("response_code") or 0)
    except (TypeError, ValueError):
        code = 0
    payload = None
    body = str(output.get("output") or "").strip()
    if body:
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
    if code != 200:
        return None, http_message(code, payload)
    if not isinstance(payload, (dict, list)):
        return None, "the API answer could not be read"
    return payload, ""


def rows_of(payload):
    """Return the data rows of a list response."""
    rows = as_dict(payload).get("data")
    return [row for row in rows if isinstance(row, dict)] \
        if isinstance(rows, list) else []


def request(full_name, path, params, callback):
    """Ask the API for one path, without blocking WeeChat.

    Every value in params is either a literal from this script or a string
    of digits checked by the caller, so the query needs no escaping.
    """
    key = api_key()
    if not key:
        print_error(
            full_name,
            "no API key set. Free keys need no card: get one at %s, then "
            "/set plugins.var.python.%s.api_key \"your-key\""
            % (SIGNUP_URL, SCRIPT_NAME),
        )
        return
    url = API_URL + path
    if params:
        url += "?" + "&".join(
            "%s=%s" % (name, value) for name, value in params
        )
    options = {
        "httpheader": "\n".join([
            "X-API-Key: " + key,
            "Accept: application/json",
            "User-Agent: %s.py/%s" % (SCRIPT_NAME, SCRIPT_VERSION),
        ]),
    }
    timeout = option_int("timeout", 1, 60) * 1000
    weechat.hook_url(url, options, timeout, callback, full_name)


def matches_cb(data, url, options, output):
    """Print the live matches."""
    payload, error = read_response(output)
    if error:
        print_error(data, error)
        return weechat.WEECHAT_RC_OK
    matches = rows_of(payload)
    if not matches:
        print_line(data, "%s: no match is being played right now"
                   % SCRIPT_NAME)
        return weechat.WEECHAT_RC_OK
    for match in matches:
        print_line(data, format_match(match))
    return weechat.WEECHAT_RC_OK


def match_cb(data, url, options, output):
    """Print one match in a little more detail."""
    payload, error = read_response(output)
    if error:
        print_error(data, error)
        return weechat.WEECHAT_RC_OK
    match = as_dict(payload)
    if not match:
        print_error(data, "no match with that id")
        return weechat.WEECHAT_RC_OK
    print_line(data, format_match(match))
    players = as_dict(match.get("players"))
    for side in ("p1", "p2"):
        player = as_dict(players.get(side))
        name = str(player.get("name") or "?")
        extra = [str(player.get("country") or "").strip()]
        if player.get("ranking") is not None:
            extra.append("rank %s" % player.get("ranking"))
        detail = ", ".join(part for part in extra if part)
        print_line(data, "  %s%s" % (name, " (%s)" % detail if detail else ""))
    state = [str(match.get("status") or "unknown")]
    for field in ("event_status", "surface", "format", "scheduled_time"):
        value = str(match.get(field) or "").strip()
        if value:
            state.append(value)
    print_line(data, "  %s" % ", ".join(state))
    return weechat.WEECHAT_RC_OK


def rankings_cb(data, url, options, output):
    """Print a rankings table."""
    payload, error = read_response(output)
    if error:
        print_error(data, error)
        return weechat.WEECHAT_RC_OK
    records = rows_of(payload)
    if not records:
        print_line(data, "%s: no ranking records returned" % SCRIPT_NAME)
        return weechat.WEECHAT_RC_OK
    for record in records:
        print_line(data, format_ranking(record))
    return weechat.WEECHAT_RC_OK


def tennis_cmd(data, buffer, args):
    """Run /tennis."""
    full_name = weechat.buffer_get_string(buffer, "full_name")
    argv = args.split()
    action = argv[0].lower() if argv else "live"
    limit = option_int("max_matches", 1, 50)
    if action == "live":
        request(
            full_name,
            "/matches",
            (("status", "live"), ("limit", str(limit))),
            "matches_cb",
        )
    elif action == "match":
        if len(argv) < 2 or not argv[1].isdigit():
            print_error(full_name, "usage: /tennis match <id>")
            return weechat.WEECHAT_RC_OK
        request(full_name, "/matches/" + argv[1], (), "match_cb")
    elif action in ("atp", "wta"):
        if len(argv) > 1:
            if not argv[1].isdigit():
                print_error(
                    full_name, "usage: /tennis %s [count]" % action
                )
                return weechat.WEECHAT_RC_OK
            limit = max(1, min(50, int(argv[1])))
        request(
            full_name,
            "/rankings",
            (("system", action), ("limit", str(limit))),
            "rankings_cb",
        )
    else:
        print_error(
            full_name,
            "unknown action \"%s\"; try live, match, atp or wta" % action,
        )
    return weechat.WEECHAT_RC_OK


def config_setup():
    """Create the script options, keeping any value already set."""
    for name, (default, description) in OPTIONS.items():
        if not weechat.config_is_set_plugin(name):
            weechat.config_set_plugin(name, default)
        weechat.config_set_desc_plugin(
            name, "%s (default: \"%s\")" % (description, default)
        )


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                    SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    if int(weechat.info_get("version_number", "") or 0) < MIN_VERSION:
        weechat.prnt(
            "",
            "%s%s: WeeChat 4.1.0 or newer is required (function hook_url)"
            % (weechat.prefix("error"), SCRIPT_NAME),
        )
    else:
        config_setup()
        weechat.hook_command(
            SCRIPT_NAME,
            SCRIPT_DESC,
            "live || match <id> || atp [count] || wta [count]",
            "  live: matches being played right now (the default)\n"
            " match: one match, with both players and its state\n"
            "   atp: ATP singles rankings\n"
            "   wta: WTA singles rankings\n"
            " count: how many rows to print, 1-50\n"
            "\n"
            "A match line reads: id, surnames, set scores, the points of the\n"
            "game in progress, then the tournament. \"*\" follows the player\n"
            "serving; \"BP\" means the receiver is one point from a break.\n"
            "\n"
            "An API key is required. Free keys need no card and allow 30\n"
            "requests per minute and 100 per day, so this script only calls\n"
            "the API when you run a command; it polls nothing on a timer.\n"
            "Rankings are part of a paid plan and answer \"this data is not\n"
            "included in your plan\" on a free key.\n"
            "\n"
            "  /set plugins.var.python." + SCRIPT_NAME + ".api_key \"key\"\n"
            "\n"
            "The option is evaluated, so a secured key can be used:\n"
            "\n"
            "  /secure set livetennisapi your-key\n"
            "  /set plugins.var.python." + SCRIPT_NAME + ".api_key "
            "\"${sec.data.livetennisapi}\"\n"
            "\n"
            "Keys and plans: " + SIGNUP_URL + "\n",
            "live || match || atp || wta",
            "tennis_cmd",
            "",
        )
