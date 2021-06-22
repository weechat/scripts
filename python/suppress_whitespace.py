#  Project: suppress_whitespace
#  Description: Exclude whitespace-only text input.
#  Author: Kevin Morris <kevr@0cost.org>
#  License: MIT
#
import weechat

script_name = "suppress_whitespace"
script_author = "Kevin Morris <kevr@0cost.org>"
script_license = "MIT"
script_desc = f"{script_name} - A whitespace suppression script for weechat"
script_version = "0.0.1"


def input_modifier_cb(data, modifier, modifier_data, string):
    # Remove leading whitespace from any input typed.
    return string.lstrip()


if __name__ == "__main__":
    weechat.register(script_name, script_author, script_version,
                     script_license, script_desc, "", "")
    weechat.hook_modifier("input_text_content", "input_modifier_cb", "")
