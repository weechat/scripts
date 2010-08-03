# Script Name: Zerotab.py
# Script Author: Lucian Adamson <lucian.adamson@yahoo.com>
# Script License: GPL
# Alternate Contact: Freenode IRC nick i686

SCRIPT_NAME='zerotab'
SCRIPT_AUTHOR='Lucian Adamson <lucian.adamson@yahoo.com>'
SCRIPT_VERSION='1.0'
SCRIPT_LICENSE='GPL'
SCRIPT_DESC='Will tab complete the last nick in channel without typing anything first. This is good for rapid conversations.'

import_ok=True

try:
    import weechat, re
except ImportError:
    print 'This script must be run under WeeChat'
    print 'You can obtain a copy of WeeChat, for free, at http://www.weechat.org'
    import_ok=False

latest_speaker={}

def my_completer(data, buffer, command):
    global latest_speaker
    str_input = weechat.buffer_get_string(weechat.current_buffer(), "input")
    if command == "/input complete_next" and str_input == '':
        try:
            str_insert = latest_speaker[buffer]
        except:
            return weechat.WEECHAT_RC_OK
        if re.match('^[@%+~*&!-]', str_insert):
            str_insert = str_insert[1:]
        weechat.command(buffer, "/input insert " + str_insert)
    return weechat.WEECHAT_RC_OK

def hook_print_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    global latest_speaker
    if tags.find('irc_privmsg') >= 0:
        latest_speaker[buffer] = prefix
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_print("", "", "", 1, "hook_print_cb", "")
        weechat.hook_command_run('/input complete*', 'my_completer', '')
