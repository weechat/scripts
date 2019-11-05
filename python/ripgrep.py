import json
import time

try:
    import weechat
except ImportError:
    weechat = None
    print("This script requires WeeChat to run.")

SCRIPT_NAME = "ripgrep"
SCRIPT_AUTHOR = "Martin Weinelt <martin+weechat@linuxlounge.net>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESCRIPTION = "Use /rg to search through buffer logfiles"
SCRIPT_SHUTDOWN_FUNC = ""
SCRIPT_CHARSET = ""

STATE = {"BUSY": False, "BUFFER": list()}
CONFIG = {}
SETTINGS = {"ripgrep_path": "/usr/bin/env rg"}


def load_config_values() -> None:
    CONFIG["WEECHAT_LOOK_PREFIX_JOIN"] = weechat.config_string(
        weechat.config_get("weechat.look.prefix_join")
    )
    CONFIG["WEECHAT_LOOK_PREFIX_PART"] = weechat.config_string(
        weechat.config_get("weechat.look.prefix_part")
    )
    CONFIG["WEECHAT_LOOK_PREFIX_NETWORK"] = weechat.config_string(
        weechat.config_get("weechat.look.prefix_network")
    )
    CONFIG["WEECHAT_HISTORY_MAX_BUFFER_LINES_NUMBER"] = weechat.config_integer(
        weechat.config_get("weechat.history.max_buffer_lines_number")
    )
    CONFIG["LOGGER_FILE_TIME_FORMAT"] = weechat.config_string(
        weechat.config_get("logger.file.time_format")
    )
    CONFIG["IRC_COLOR_NICK_PREFIXES"] = weechat.config_string(
        weechat.config_get("irc.color.nick_prefixes")
    )


def get_logfile_from_buffer_pointer(buffer: str):
    infolist = weechat.infolist_get("logger_buffer", "", "")
    if infolist:
        while weechat.infolist_next(infolist):
            pointer = weechat.infolist_pointer(infolist, "buffer")
            if pointer == buffer:
                file = weechat.infolist_string(infolist, "log_filename")
                weechat.infolist_free(infolist)
                return file
        weechat.infolist_free(infolist)


def get_or_create_buffer(title: str = None):
    buffer = weechat.buffer_search("python", SCRIPT_NAME)
    if not buffer:
        buffer = weechat.buffer_new(SCRIPT_NAME, "", "", "", "")
        weechat.buffer_set(buffer, "time_for_each_line", "1")
        weechat.buffer_set(buffer, "nicklist", "0")
        weechat.buffer_set(
            buffer,
            "title",
            title or "ripgrep.py | use \\rg to search through buffer logfiles",
        )
        weechat.buffer_set(buffer, "localvar_set_no_log", "1")
    if title:
        weechat.buffer_set(buffer, "title", title)
    return buffer


def get_color_for_mode(mode):
    if mode not in "~@!%+":
        return

    idx = "~@!%+".find(mode)
    if idx == -1:
        return
    key = "qoahv"[idx]

    for mapping in CONFIG["IRC_COLOR_NICK_PREFIXES"].split(";"):
        if mapping.startswith(key):
            return weechat.color(mapping.split(":")[1])


def buffer_print_match(buffer, match):
    shift = 0
    fulltext = match["data"]["lines"]["text"]
    try:
        dt, nick, msg = fulltext.split("\t", 2)
    except ValueError as ex:
        print(ex, "\t", fulltext)
        return

    # parse time str to unix timestamp
    try:
        timestamp = int(
            time.mktime(time.strptime(dt, CONFIG["LOGGER_FILE_TIME_FORMAT"]))
        )
    except ValueError:
        # if we couldn't parse dt the time_format was probably changed
        timestamp = 0

    colorize_nick = False

    # ACTION
    if nick.strip() == "*":
        nick = msg.split()[0]
    # NOTICE
    elif nick == CONFIG["WEECHAT_LOOK_PREFIX_NETWORK"] and msg.startswith("Notice("):
        nick = msg.split("(", 1)[1].split(")", 1)[0]
    # JOIN | PART
    elif (
        nick == CONFIG["WEECHAT_LOOK_PREFIX_JOIN"]
        or nick == CONFIG["WEECHAT_LOOK_PREFIX_JOIN"]
    ):
        nick = msg.split()[0]
    else:
        # TODO: currently we only colorize in privmsgs
        colorize_nick = True

    # separate channel mode from nickname
    try:
        if nick[0] in "~@!%+":
            nick = nick.lstrip("@!%+")
    except IndexError:
        pass

    color_highlight = weechat.color("red")
    color_default = weechat.color("chat")
    color_nick = weechat.info_get("nick_color", nick) or 0
    try:
        color_nick_number = int(color_nick.replace("\x19F", "", 1).lstrip("@")) or 0
    except AttributeError:
        # likely color_nick is already an int
        color_nick_number = color_nick

    if colorize_nick and color_nick:
        colored_nick = f"{color_nick}{nick}{color_default}"
        fulltext = fulltext.replace(nick, colored_nick, 1)
        shift += len(colored_nick) - len(nick)

    # match highlighting on message, matches are given as byte positions
    bytetext = bytearray(bytes(fulltext, "utf-8"))
    marker_start = bytes(color_highlight, "utf-8")
    marker_end = bytes(color_default, "utf-8")
    offset_start = len(marker_start)
    offset_end = len(marker_end)
    for submatch in match["data"]["submatches"]:
        # TODO: highlighting nicknames has issues, so let's skip this area for now
        if submatch["end"] < len(fulltext) - len(msg):
            continue

        start = shift + submatch["start"]
        bytetext = bytetext[:start] + marker_start + bytetext[start:]
        shift += offset_start

        end = shift + submatch["end"]
        bytetext = bytetext[:end] + marker_end + bytetext[end:]
        shift += offset_end

    fulltext = bytetext.decode()

    # remove datetime from fulltext if we could parse it
    if timestamp:
        fulltext = "".join(fulltext.split("\t", 1)[-1:])
    weechat.prnt_date_tags(
        buffer,
        timestamp,
        f"no_highlight,nick_{nick},prefix_nick_{color_nick_number}",
        fulltext,
    )


def rg_cmd_cb(_, buffer: str, args: str):
    if not args:
        return weechat.WEECHAT_RC_OK

    if STATE["BUSY"]:
        print("busy")
        return weechat.WEECHAT_RC_OK

    load_config_values()

    logfile = get_logfile_from_buffer_pointer(buffer)
    if not logfile:
        weechat.prnt("", "No logfile found")
        return weechat.WEECHAT_RC_OK

    STATE["PATTERN"] = args
    STATE["LOGFILE"] = logfile
    STATE["BUSY"] = True

    buffer = get_or_create_buffer(f"ripgrep.py | Pattern: {args} | Logfile: {logfile}")
    weechat.buffer_clear(buffer)

    pattern = args.replace('"', '\\"')
    weechat.hook_process(
        f'/usr/bin/env rg --json "{pattern}" "{logfile}"', 10 * 1000, "rg_cb", ""
    )

    return weechat.WEECHAT_RC_OK


def rg_cb(data, command, rc: int, out: str, err: str):
    # accumulate stdout until return code indicates clean exit
    STATE["BUFFER"].append(out)
    if rc != 0:
        return weechat.WEECHAT_RC_OK

    # decode and join buffer, then flush it
    if isinstance(STATE["BUFFER"], bytes):
        STATE["BUFFER"] = STATE["BUFFER"].decode("utf-8")
    lines = "".join(STATE["BUFFER"]).split("\n")
    STATE["BUFFER"] = list()

    # reduce matches according to max lines configured for buffers
    cutoff = False
    if len(lines) > CONFIG["WEECHAT_HISTORY_MAX_BUFFER_LINES_NUMBER"]:
        cutoff = True
        lines = lines[-CONFIG["WEECHAT_HISTORY_MAX_BUFFER_LINES_NUMBER"] :]

    if err:
        weechat.prnt("", err)

    buffer = get_or_create_buffer()
    i = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            result = json.loads(line)
        except ValueError as ex:
            print(ex, line)
            continue
        _type = result.get("type", None)
        if _type == "match":
            i += 1
            buffer_print_match(buffer, result)
        elif _type == "end":
            get_or_create_buffer(
                f"ripgrep.py | "
                f"Matches: {result['data']['stats']['matches']} (in {result['data']['stats']['matched_lines']} lines) | "
                f"Pattern: {STATE['PATTERN']} | "
                f"Logfile: {STATE['LOGFILE']}"
            )
            if cutoff:
                weechat.prnt(
                    buffer,
                    f"---\nThere were too many matches (>{CONFIG['WEECHAT_HISTORY_MAX_BUFFER_LINES_NUMBER']}) to display,"
                    f" please refine your search pattern.",
                )

    STATE["BUSY"] = False

    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and weechat:
    weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESCRIPTION,
        "",
        "",
    )

    weechat.hook_command(
        "rg",
        "Search through a buffers logfiles.",
        "<pattern>",
        "argdesc",
        "idk",
        "rg_cmd_cb",
        "",
    )
