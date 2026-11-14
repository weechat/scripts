# SPDX-FileCopyrightText: 2012 nesthib <nesthib@gmail.com>
# SPDX-FileCopyrightText: 2026 Jochen Sprickerhof <weechat@jochen.sprickerhof.de>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# This script generates a file containing a formatted list of highlights to be
# used by an external program like conky.
#
# 2026-11-14, Jochen Sprickerhof <weechat@jochen.sprickerhof.de>
#        0.4: Port to Python 3
# 2021-05-04, Sébastien Helleu <flashcode@flashtux.org>
#        0.3: add compatibility with WeeChat >= 3.2 (XDG directories)
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#        0.2: change hook_print callback argument type of displayed/highlight
#             (WeeChat >= 1.0)
# 2012-03-07: nesthib <nesthib@gmail.com>
#        0.1: initial release

import os
import re
from collections import Counter

IMPORT_OK = True

try:
    import weechat  # ty: ignore[unresolved-import]
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    IMPORT_OK = False

SCRIPT_NAME = "hl2file"
SCRIPT_AUTHOR = "nesthib <nesthib@gmail.com>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Generates a file with highlights for external programs like conky"

# script options
SETTINGS = {
    "output_file": "%h/highlights.txt",
    "output_active_buffer": "%h/active_buffer.txt",
    # "ignore_chans": "server",
    "output_format": "%{buffer}: %{nick} (%{message})",
    "summarize_by_buffer": "off",
    "short_buffer_names": "on",
    "clear_visited_buffers": "on",
}

highlights = []


def bufname(buffer: str) -> str:
    buffer_name = weechat.buffer_get_string(buffer, "name")
    if weechat.config_string_to_boolean(
        weechat.config_get_plugin("short_buffer_names")
    ):
        buffer_name = buffer_name.partition(".")[2]
    return buffer_name


def write(my_file: str, content: str | list[str]) -> None:
    if my_file == "":
        return
    options = {
        "directory": "data",
    }
    my_file = weechat.string_eval_path_home(my_file, {}, {}, options)
    try:
        with open(my_file, "w") as f:
            f.writelines(content)
    except OSError as err:
        weechat.prnt(
            "",
            f'{weechat.prefix("error")}{SCRIPT_NAME}: unable to write "{my_file}": {err}',
        )


def write_file() -> None:
    filename = weechat.config_get_plugin("output_file")
    if weechat.config_string_to_boolean(
        weechat.config_get_plugin("summarize_by_buffer")
    ):
        items = Counter([bufname(item["buffer"]) for item in highlights])
        output_lines = [f"{item} ({items[item]})\n" for item in items]
    else:
        output_regex = weechat.config_get_plugin("output_format")
        tags = re.findall(r"%\{[^\{\}]+\}", output_regex)
        output_lines = []
        for infos in highlights:
            output_string = output_regex + "\n"
            for tag in tags:
                item = tag.lstrip("%{").rstrip("}")
                if item in infos:
                    if item == "buffer":
                        new_string = bufname(infos[item])
                    else:
                        new_string = infos[item]
                    output_string = output_string.replace(tag, new_string)
            output_lines.append(output_string)
    write(filename, output_lines)


def my_print_cb(
    _data: str,
    buffer: str,
    date: str,
    tags: str,
    _displayed: str | int,
    highlight: str | int,
    prefix: str,
    message: str,
) -> int:
    if weechat.config_string_to_boolean(
        weechat.config_get_plugin("clear_visited_buffers")
    ) and buffer == weechat.window_get_pointer(weechat.current_window(), "buffer"):
        return weechat.WEECHAT_RC_OK
    if int(highlight) or "notify_private" in tags:
        infos = {
            "buffer": buffer,
            "date": date,
            "tags": tags,
            "nick": prefix,
            "message": message,
        }
        highlights.append(infos)
        write_file()
    return weechat.WEECHAT_RC_OK


def clear_file_cb(_data: str, _buffer: str, _args: str) -> int:
    global highlights
    highlights = []
    write_file()
    return weechat.WEECHAT_RC_OK


def buffer_switch_cb(_data: str, _signal: str, _signal_data: str) -> int:
    global highlights
    if weechat.config_string_to_boolean(
        weechat.config_get_plugin("clear_visited_buffers")
    ):
        buffer = weechat.window_get_pointer(weechat.current_window(), "buffer")
        write(weechat.config_get_plugin("output_active_buffer"), bufname(buffer) + "\n")
        highlights = [item for item in highlights if item["buffer"] != buffer]
        write_file()
    return weechat.WEECHAT_RC_OK


def shutdown() -> int:
    options = {
        "directory": "data",
    }
    for my_file in ["output_file", "output_active_buffer"]:
        filename = weechat.string_eval_path_home(
            weechat.config_get_plugin(my_file), {}, {}, options
        )
        if os.path.exists(filename):
            os.remove(filename)
    return weechat.WEECHAT_RC_OK


def my_config_cb(_data: str, _option: str, _value: str) -> int:
    write_file()
    return weechat.WEECHAT_RC_OK


def main() -> None:
    """Main function."""

    if not weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "shutdown",
        "",
    ):
        return

    for name, option in SETTINGS.items():
        if not weechat.config_is_set_plugin(name):
            weechat.config_set_plugin(name, option)

    for option in SETTINGS:
        weechat.hook_config(
            f"plugins.var.python.{SCRIPT_NAME}.{option}", "my_config_cb", ""
        )

    ###  HOOKS  ###
    weechat.hook_command("hl2file_clear", "", "", "", "", "clear_file_cb", "")
    weechat.hook_signal("buffer_switch", "buffer_switch_cb", "")
    weechat.hook_signal("window_switch", "buffer_switch_cb", "")
    weechat.hook_print("", "", "", 1, "my_print_cb", "")


if __name__ == "__main__" and IMPORT_OK:
    main()
