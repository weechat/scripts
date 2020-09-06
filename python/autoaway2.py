try:
    import weechat as w
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False
import time

SCRIPT_NAME    = "autoaway2"
SCRIPT_AUTHOR  = "jesopo"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC    = "auto-away without auto-unaway and with weechat-android support"

LAST_ACTION = 0

def idle_check(data, remain):
    try:
        timeout = int(w.config_get_plugin("timeout"))
    except ValueError:
        timeout = 0
    message     = w.config_get_plugin("message")

    inactivity  = int(w.info_get("inactivity", "0")) / 60
    last_action = (time.monotonic()-LAST_ACTION) / 60
    inactivity  = min(inactivity, last_action)

    if timeout > 0 and inactivity >= timeout:
        servers = w.infolist_get("irc_server", "", "")
        while w.infolist_next(servers):
            if (w.infolist_integer(servers, "is_connected") == 1 and
                    w.infolist_integer(servers, "is_away") == 0):
                ptr = w.infolist_pointer(servers, "buffer")
                w.command(ptr, f"/away {message}")
        w.infolist_free(servers)

    return w.WEECHAT_RC_OK

SETTINGS = {
    "timeout": ["20",   "Minutes of inactivity before autoaway"],
    "message": ["Idle", "Autoaway message"]
}

def _action():
    global LAST_ACTION
    LAST_ACTION = time.monotonic()
def signal_privmsg(data, signal, signal_data):
    _action()
    return w.WEECHAT_RC_OK
def signal_unaway(data, signal, signal_data):
    _action()
    return w.WEECHAT_RC_OK
def command_input(data, buffer, command):
    _action()
    return w.WEECHAT_RC_OK

if import_ok and w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for name, (default, description) in SETTINGS.items():
        if not w.config_is_set_plugin(name):
            w.config_set_plugin(name, default)
            w.config_set_desc_plugin(name, description)

    # every 60 seconds, on 00
    w.hook_timer(60 * 1000, 60, 0, "idle_check", "")

    # these hooks are to also catch activity from weechat-android

    # catch us sending a PRIVMSG
    w.hook_signal(
        "*,irc_out_privmsg",
        "signal_privmsg",
        ""
    )
    # catch us no longer being marked as away, for manual /away
    w.hook_signal(
        "*,irc_in_305",
        "signal_unaway",
        ""
    )
    # catch weechat-android switching buffers
    w.hook_command_run(
        "/input set_unread_current_buffer",
        "command_input",
        ""
    )
