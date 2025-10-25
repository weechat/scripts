# SPDX-FileCopyrightText: 2025-2026 D. Bohdan <dbohdan@dbohdan.com>
# SPDX-License-Identifier: MIT
#
# Censor messages by nick and text using color while still logging them.
# This is an alternative to /ignore and triggers that remove the message from logs.
#
# --------------------------------------------------------------------------------------
# INSTALLATION & USAGE
# --------------------------------------------------------------------------------------
# This script requires WeeChat with the Python plugin and Python 3.9 or later.
#
# 1. Save this file with WeeChat Python scripts:
#      ~/.local/share/weechat/python/censor.py
#
# 2. Load it in WeeChat:
#      /python load censor.py
#
# 3. Configure using the following options:
#      plugins.var.python.censor.censor_color
#      plugins.var.python.censor.nick_re
#      plugins.var.python.censor.text_re
#
# The script modifies the display of censored messages
# and removes mIRC color codes from them.
# The message still exists in the buffer and the logs.
# --------------------------------------------------------------------------------------

from __future__ import annotations

import re
from typing import TypedDict

import_ok = True
try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False

SCRIPT_NAME = "censor"
SCRIPT_AUTHOR = "D. Bohdan <dbohdan@dbohdan.com>"
SCRIPT_VERSION = "0.3.0"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Censor messages by nick and text using color while still logging them."

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

OPTIONS_PREFIX = f"plugins.var.python.{SCRIPT_NAME}."


class RegexCheck:
    def __init__(self, pattern: str = "") -> None:
        self._regex: re.Pattern | None = None
        self.pattern = pattern  # Compile the regex.

    def __str__(self) -> str:
        return self.pattern

    def check(self, string: str) -> bool:
        return self._regex is not None and bool(self._regex.search(string))

    @property
    def pattern(self) -> str:
        return "" if self._regex is None else self._regex.pattern

    @pattern.setter
    def pattern(self, pattern: str) -> None:
        self._regex = None

        if not pattern.strip():
            return

        try:
            self._regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            weechat.prnt("", f"{SCRIPT_NAME}: invalid regex: {e}")


class ScriptOptions(TypedDict):
    censor_color: str
    nick_re: RegexCheck
    text_re: RegexCheck


SCRIPT_OPTION_DESCS = {
    "censor_color": "color (fg,bg) applied to censored messages",
    "nick_re": "case-insensitive regex matched against the nick",
    "text_re": "case-insensitive regex matched against the message text",
}


script_options: ScriptOptions = {
    "censor_color": "darkgray,darkgray",
    "nick_re": RegexCheck(),
    "text_re": RegexCheck(),
}


# ---------------------------------------------------------------------------
# IMPLEMENTATION
# ---------------------------------------------------------------------------


def tags_nick(tags):
    """Extract nick from tags."""
    if not tags:
        return ""

    for tag in tags.split(","):
        if tag.startswith("nick_"):
            return tag.removeprefix("nick_")

    return ""


def set_script_option(key, value):
    if key == "censor_color":
        script_options[key] = value
    elif key in ("nick_re", "text_re"):
        script_options[key] = RegexCheck(value)


def config_cb(_data, option, value):
    """Callback called when a script option is changed."""
    key = option.removeprefix(OPTIONS_PREFIX)

    if key in script_options:
        set_script_option(key, value)

    return weechat.WEECHAT_RC_OK


def censor_line_cb(_data, line):
    """hook_line callback: style censored message text."""
    tags = line.get("tags", "")
    nick = tags_nick(tags)

    if not nick:
        return {}

    plain = weechat.string_remove_color(line["message"], "")

    if script_options["nick_re"].check(nick) or script_options["text_re"].check(plain):
        color = weechat.color(script_options["censor_color"])
        reset = weechat.color("reset")

        return {
            "message": f"{color}{plain}{reset}",
            "highlight": "0",
            "notify_level": "-1",
        }

    return {}


def main():
    if not weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    ):
        return

    for key, default_value in script_options.items():
        if weechat.config_is_set_plugin(key):
            set_script_option(key, weechat.config_get_plugin(key))
        else:
            weechat.config_set_plugin(key, str(default_value))

        weechat.config_set_desc_plugin(
            key,
            f'{SCRIPT_OPTION_DESCS[key]} (default: "{default_value}")',
        )

    weechat.hook_config(OPTIONS_PREFIX + "*", "config_cb", "")
    weechat.hook_line("", "", "", "censor_line_cb", "")


if __name__ == "__main__" and import_ok:
    main()
