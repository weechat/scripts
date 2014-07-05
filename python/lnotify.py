#  Project: lnotify
#  Description: A libnotify script for weechat. Uses
#  subprocess.call to execute notify-send with arguments.
#  Author: kevr <kevr@nixcode.us>
#  License: GPL3
#
# 0.1.2
# added option to display weechat's icon by tomboy64
#
# 0.1.3
# changed the way that icon to WeeChat notification is specified.
# (No absolute path is needed)
# /usr/bin/notify-send isn't needed anymore.
# (pynotify is handling notifications now)
# changed the way that lnotify works. When using gnome 3, every new
# notification was creating a new notification instance. The way that
# it is now, all WeeChat notifications are in a group (that have the
# WeeChat icon and have WeeChat name).
# Got report that it has better look for KDE users too.
#
# 0.1.4
# change hook_print callback argument type of displayed/highlight
# (WeeChat >= 1.0)
#
# 0.2.0
# - changed entire system to hook_process_hashtable calls to notify-send
# - also changed the configuration option names and methods
# Note: If you want pynotify, refer to the 'notify.py' weechat script
import weechat as weechat

lnotify_name = "lnotify"
lnotify_version = "0.2.0"
lnotify_license = "GPL3"

# convenient table checking for bools
true = { "on": True, "off": False }

# declare this here, will be global config() object
# but is initialized in __main__
cfg = None

class config(object):
    def __init__(self):
        # default options for lnotify
        self.opts = {
            "highlight": "on",
            "query": "on",
            "notify_away": "off",
            "icon": "weechat",
        }

        self.init_config()
        self.check_config()

    def init_config(self):
        for opt, value in self.opts.items():
            temp = weechat.config_get_plugin(opt)
            if not len(temp):
                weechat.config_set_plugin(opt, value)

    def check_config(self):
        for opt in self.opts:
            self.opts[opt] = weechat.config_get_plugin(opt)

    def __getitem__(self, key):
        return self.opts[key]

def printc(msg):
    weechat.prnt("", msg)

def handle_msg(data, pbuffer, date, tags, displayed, highlight, prefix, message):
    highlight = bool(highlight) and cfg["highlight"]
    query = true[cfg["query"]]
    notify_away = true[cfg["notify_away"]]
    buffer_type = weechat.buffer_get_string(pbuffer, "localvar_type")
    away = weechat.buffer_get_string(pbuffer, "localvar_away")

    if pbuffer == weechat.current_buffer():
        return weechat.WEECHAT_RC_OK

    if away and not notify_away:
        return weechat.WEECHAT_RC_OK

    buffer_name = weechat.buffer_get_string(pbuffer, "short_name")

    if buffer_type == "private" and query:
        notify_user(buffer_name, message)
    elif buffer_type == "channel" and highlight:
        notify_user("{} @ {}".format(prefix, buffer_name), message)

    return weechat.WEECHAT_RC_OK

def process_cb(data, command, return_code, out, err):
    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" % command)
    elif return_code != 0:
        weechat.prnt("", "return_code = %d" % return_code)
        weechat.prnt("", "notify-send has an error")
    return weechat.WEECHAT_RC_OK

def notify_user(origin, message):
    hook = weechat.hook_process_hashtable("notify-send",
        { "arg1": "-i", "arg2": cfg["icon"],
          "arg3": "-a", "arg4": "WeeChat",
          "arg5": origin, "arg6": message },
        20000, "process_cb", "")

    return weechat.WEECHAT_RC_OK

# execute initializations in order
if __name__ == "__main__":
    weechat.register(lnotify_name, "kevr", lnotify_version, lnotify_license,
        "{} - A libnotify script for weechat".format(lnotify_name), "", "")

    cfg = config()
    print_hook = weechat.hook_print("", "", "", 1, "handle_msg", "")

