# MIT License
#
# Copyright (c) Emma Eilefsen Glenna <emma@eilefsen.net> (https://eilefsen.net)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# ATTRIBUTIONS:
#
# This script was made by modifying an older script referenced below:
#
# notifications_center (https://github.com/sindresorhus/weechat-notification-center)
# Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (https://sindresorhus.com)
# included under the MIT license (https://opensource.org/license/mit/)

import datetime
import weechat


SCRIPT_NAME = "kitty_notifications"
SCRIPT_AUTHOR = "Emma Eilefsen Glenna <emma@eilefsen.net>"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Pass highlights and private messages as OS notifcations via the Kitty terminal (OSC 99)"

weechat.register(
    SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
)

WEECHAT_VERSION = weechat.info_get("version_number", "") or 0
DEFAULT_OPTIONS = {
    "show_highlights": "on",
    "show_private_message": "on",
    "show_message_text": "on",
    "ignore_old_messages": "off",
    "ignore_current_buffer_messages": "off",
    "channels": "",
    "tags": "",
}

for key, val in DEFAULT_OPTIONS.items():
    if not weechat.config_is_set_plugin(key):
        weechat.config_set_plugin(key, val)

weechat.hook_print(
    "", "irc_privmsg," + weechat.config_get_plugin("tags"), "", 1, "notify", ""
)


def notify(
    data: str,
    buffer: str,
    date: str,
    tags: str,
    displayed: int,
    highlight: int,
    prefix: str,
    message: str,
) -> int:
    # Ignore if it's yourself
    own_nick = weechat.buffer_get_string(buffer, "localvar_nick")
    if prefix == own_nick or prefix == ("@%s" % own_nick):
        return weechat.WEECHAT_RC_OK

    # Ignore messages from the current buffer
    if (
        weechat.config_get_plugin("ignore_current_buffer_messages") == "on"
        and buffer == weechat.current_buffer()
    ):
        return weechat.WEECHAT_RC_OK

    # Ignore messages older than the configured theshold (such as ZNC logs) if enabled
    if weechat.config_get_plugin("ignore_old_messages") == "on":
        message_time = datetime.datetime.fromtimestamp(int(date))
        now_time = datetime.datetime.now()

        # Ignore if the message is greater than 5 seconds old
        if (now_time - message_time).seconds > 5:
            return weechat.WEECHAT_RC_OK

    channel_allow_list = []
    if weechat.config_get_plugin("channels") != "":
        channel_allow_list = weechat.config_get_plugin("channels").split(",")
    channel = weechat.buffer_get_string(buffer, "localvar_channel")

    if channel in channel_allow_list:
        if weechat.config_get_plugin("show_message_text") == "on":
            print_osc99(
                f"{prefix} {channel}",
                message,
            )
        else:
            print_osc99(
                "Channel Activity",
                f"In {channel} by {prefix}",
            )
    elif weechat.config_get_plugin("show_highlights") == "on" and int(highlight):
        if weechat.config_get_plugin("show_message_text") == "on":
            print_osc99(
                f"{prefix} {channel}",
                message,
            )
        else:
            print_osc99(
                "Highlighted Message",
                f"In {channel} by {prefix}",
            )
    elif (
        weechat.config_get_plugin("show_private_message") == "on"
        and "irc_privmsg" in tags
        and "notify_private" in tags
    ):
        if weechat.config_get_plugin("show_message_text") == "on":
            print_osc99(
                f"{prefix} [private]",
                message,
            )
        else:
            print_osc99(
                "Private Message",
                f"From {prefix}",
            )
    return weechat.WEECHAT_RC_OK


def print_osc99(
    title: str,
    body: str,
) -> None:
    with open("/dev/tty", "w") as tty:
        tty.write(f"\x1b]99;i=1:d=0:p=title;{title}\x1b\\")
        tty.write(f"\x1b]99;i=1:d=1:p=body;{body}\x1b\\")
