"""
Weechat plugin to convert emoji shortcodes to unicode emoji.

This plugin is a thin wrapper around the emoji package for python.
It converts emoji shortcodes to Unicode emoji.

This package is based on the emoji_aliases.py script by Mike Reinhardt.

License: CC0
Author: Thom Wiggers <thom@thomwiggers.nl>
Repository: https://github.com/thomwiggers/weechat-emojize

This plugin supports python 3 and requires the 'emoji' python package.
Requires at least weechat 1.3

Changelog:
    1.0.1 - 2023-08-06: mva
        Adaptation to modern version of `emoji` package
        (use_aliases => language="alias")

"""


def register():
    weechat.register(
        "emojize",
        "Thom Wiggers",
        "1.0.1",
        "CC0",
        "Convert emoji shortcodes to unicode emoji",
        "",  # shutdown function
        "utf-8",
    )


import_ok = True

try:
    import emoji
except ImportError:
    print("Failed to import emoji package, try installing 'emoji'")
    import_ok = False

import weechat


HOOKS = (
    "away",
    "cnotice",
    "cprivmsg",
    "kick",
    "knock",
    "notice",
    "part",
    "privmsg",
    "quit",
    "wallops",
)


def convert_emoji(_data, modifier, _modifier_data, string):
    """Convert the emoji in event messages"""
    # Check if this message has a segment we shouldn't touch.
    msg = weechat.info_get_hashtable("irc_message_parse", {"message": string})
    pos_text = int(msg["pos_text"])
    if msg["text"] != "" and pos_text > 0:
        return (
            string[:pos_text]
            + emoji.emojize(msg["text"], language="alias")
            + string[(pos_text + len(msg["text"])):]
        )

    if modifier == "input_text_for_buffer":
        return emoji.emojize(string, language="alias")

    return string


if __name__ == "__main__" and import_ok:
    register()
    weechat.hook_modifier("input_text_for_buffer", "convert_emoji", "")
    for hook in HOOKS:
        weechat.hook_modifier("irc_in2_{}".format(hook), "convert_emoji", "")
