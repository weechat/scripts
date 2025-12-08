# SPDX-FileCopyrightText: 2025 D. Bohdan <dbohdan@dbohdan.com>
# SPDX-License-Identifier: MIT
#
# Censor messages by nick and text without affecting logs using color.
# This is an alternative to /ignore and triggers that modify logs.
#
# ---------------------------------------------------------------------------
# INSTALLATION & USAGE
# ---------------------------------------------------------------------------
# 1. Save this file with WeeChat Python scripts:
#      ~/.local/share/weechat/python/censor.py
#
# 2. Edit the configuration section below to suit your needs:
#      - Add nick and/or text regexes to CENSORED_NICKS and CENSORED_TEXT.
#      - Change CENSOR_COLOR if desired.
#
# 3. Load it in WeeChat:
#      /python load censor.py
#
# This script only modifies the display of censored messages.
# The original messages still exists in the buffer and the logs.
#
# Example:
#   CENSORED_NICKS = [r"^AnnoyingUser", r"troll\d+", r"bot$"]
#   CENSOR_COLOR = "darkgray"
#
# ---------------------------------------------------------------------------

import re

import_ok = True
try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

SCRIPT_NAME = "censor"
SCRIPT_AUTHOR = "D. Bohdan <dbohdan@dbohdan.com>"
SCRIPT_VERSION = "0.2.0"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = (
    "Censor messages by nick and text without affecting logs using color."
)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

CENSORED_NICKS = [
    # r"troll\d+",
]
CENSORED_TEXT = [
    # r"hello\?{5}",
]

CENSOR_COLOR = "darkgray:darkgray"

# ---------------------------------------------------------------------------
# IMPLEMENTATION
# ---------------------------------------------------------------------------


def tags_nick(tags):
    """Extract nick from tags."""
    if not tags:
        return ""

    for tag in tags.split(","):
        if tag.startswith("nick_"):
            return tag[5:]

    return ""


def censor_line(line):
    color = weechat.color(CENSOR_COLOR)
    reset = weechat.color("reset")
    line["message"] = f"{color}{line['message']}{reset}"


def censor_line_cb(_data, line):
    """hook_line callback: style censored message text."""
    tags = line.get("tags", "")
    nick = tags_nick(tags)

    if not nick:
        return line

    for pat in CENSORED_NICKS:
        if re.search(pat, nick, flags=re.IGNORECASE):
            censor_line(line)
            break

    for pat in CENSORED_TEXT:
        if re.search(pat, line["message"], flags=re.IGNORECASE):
            censor_line(line)
            break

    return line


if __name__ == "__main__" and import_ok:
    weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    )

    weechat.hook_line("", "", "", "censor_line_cb", "")
