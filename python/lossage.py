# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 Germain Z. <germanosz@gmail.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Inspired by Emacs's view-lossage, this script displays a history of the last
# keystrokes you performed and the commands invoked.
#


import collections
import dataclasses
import re
from typing import Deque, Dict, Iterable, Tuple

import weechat  # type: ignore # pylint: disable=import-error


SCRIPT_NAME = "lossage"
SCRIPT_AUTHOR = "GermainZ <germanosz@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = (
    "Displays the last few input keystrokes and the commands run, "
    "inspired by Emacs's view-lossage."
)


HISTORY_SIZE: int = 300
REGEX_COMBO_REPL: Iterable[Tuple[re.Pattern, str]] = (
    (re.compile(r"\x01\[\["), "meta2-"),
    (re.compile(r"\x01\["), "meta-"),
    (re.compile(r"\x01"), "ctrl-"),
)
REGEX_AREA_STRIP = re.compile(r"^@[^:]+:")
HEADER: Tuple[str, str, str] = ("context", "combo", "command")


@dataclasses.dataclass
class HistoryItem:
    context: str
    combo: str
    command: str


@dataclasses.dataclass
class Data:
    history: Deque[HistoryItem] = dataclasses.field(
        default_factory=lambda: collections.deque(maxlen=HISTORY_SIZE)
    )
    key_bindings: Dict[str, Dict[str, str]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(dict)
    )


DATA = Data()


def cb_key_combo(context: str, signal: str, signal_data: str):
    mode = signal.split("_")[-1]
    combo = signal_data

    for regex, repl in REGEX_COMBO_REPL:
        combo = regex.sub(repl, combo)

    command = DATA.key_bindings[context].get(combo, "")
    DATA.history.append(HistoryItem(mode, combo, command))
    return weechat.WEECHAT_RC_OK


def cb_lossage_cmd(*_):
    buffer = weechat.buffer_search("python", SCRIPT_NAME)
    if not buffer:
        buffer = weechat.buffer_new(SCRIPT_NAME, "", "", "", "")
        weechat.buffer_set(buffer, "localvar_set_no_log", "1")
        weechat.buffer_set(buffer, "time_for_each_line", "0")
        weechat.buffer_set(buffer, "nicklist", "0")
    weechat.command(buffer, f"/buffer {SCRIPT_NAME}")
    weechat.command(buffer, "/buffer clear")

    weechat.prnt(
        buffer,
        f"{weechat.color('bold')}{HEADER[0]:10} {HEADER[1]:20} {HEADER[2]}",
    )
    for item in DATA.history:
        if item is None:
            break
        weechat.prnt(
            buffer, f"{item.context:10} {item.combo:20} {item.command}"
        )

    return weechat.WEECHAT_RC_OK


def cb_key_bindings_changed(*_):
    populate_key_bindings()


def populate_key_bindings():
    for context in ("default", "search", "cursor"):
        infolist = weechat.infolist_get("key", "", context)

        while weechat.infolist_next(infolist):
            key = weechat.infolist_string(infolist, "key")
            command = weechat.infolist_string(infolist, "command")

            # In the cursor context, bindings of the form `@area:key` can be
            # created. When the binding is used, the area is not passed to the
            # key_combo_* signal, so the best we can do is print a helpful
            # warning if there are several possible matches.
            if context == "cursor":
                key = REGEX_AREA_STRIP.sub("", key)
                if DATA.key_bindings[context].get(key, None):
                    command = (
                        f"ambiguous; see `/key list {context}` -> "
                        f"`@…:{key}` key bindings"
                    )

            DATA.key_bindings[context][key] = command

        weechat.infolist_free(infolist)


if __name__ == "__main__":
    weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    )

    populate_key_bindings()

    weechat.hook_signal("key_combo_default", "cb_key_combo", "default")
    weechat.hook_signal("key_combo_search", "cb_key_combo", "search")
    weechat.hook_signal("key_combo_cursor", "cb_key_combo", "cursor")
    weechat.hook_command(
        "lossage", SCRIPT_DESC, "", "test", "", "cb_lossage_cmd", ""
    )
    weechat.hook_signal("key_bind", "cb_key_bindings_changed", "")
    weechat.hook_signal("key_unbind", "cb_key_bindings_changed", "")
