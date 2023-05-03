# Script Name: sarcasm.py
# Script Author: Fsaev
# Script License: GPLv3

SCRIPT_NAME = 'sarcasm'
SCRIPT_AUTHOR = 'Fsaev <fredrik@saevland.com>'
SCRIPT_VERSION = '1.0'
SCRIPT_LICENSE = 'GPLv3'
SCRIPT_DESC = 'Adds random capitalization to your sentence'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat')
    print('You can obtain a copy of WeeChat, for free, at https://weechat.org')
    import_ok = False

from random import randint

def sarcasm_cb(data, buffer, args):
    newstring = ""
    for arg in args:
        if randint(0, 1) == 1:
            newstring += arg.upper()
        else:
            newstring += arg.lower()

    weechat.command(buffer, newstring)

    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_command(
            "sarcasm",
            """Adds random capitalization to your sentence to indicate that you are being sarcastic, e.g.
/sarcasm I love to put ketchup on my pizza

results in:
i lOVe tO Put KEtChUp oN mY pIzZa
""",
            "message", "",
            "",
            "sarcasm_cb", ""
        )
