# Author: sitaktif <romainchossart AT gmail DOT com>
# This plugin calls the pynma bindings via python when somebody says your
# nickname, sends you a query, etc.
#
# Requires:
# Weechat 0.3.0
# pynma.py (NMA python bindings) - This is the python API for NMA.  Take it
#   from https://raw.github.com/sitaktif/weechat_plugins_nma/master/pynma.py
#   and put it in the same direactory as nma.py.
#   Note: the pynma.py script is taken from https://github.com/uskr/pynma and
#     is not modified. The only reason you should use the one in the weechat
#     plugin repo (as opposed to the pynma repo) is that you are guaranteed
#     that pynma.py is at a version that is compatible with the weechat plugin.
#
# License: Released under GNU GPL v2
#
# Acknowledgements: Based on lavaramano's script "notify.py" v. 0.0.5 (thanks!)
#
# 2013-10-06, sitaktif
#     version 1.0.6: Add a "test" action. Take API key config changes dynamically.
# 2012-09-24, sitaktif
#     version 1.0.5: Do not send a notification when one is *sending* a query
#     message.
# 2012-05-06, sitaktif
#     version 1.0.4: Add an option to send everything in push. Also change
#     default delimiters with brackets and make lines 80 chars wide.
# 2012-05-05, sitaktif
#     version 1.0.3: Manage (non-ASCII) UTF8 chars
# 2012-01-05, Ac-town
#     version 1.0.2: Fixes a few typos I ran into and adds only_away. Only_away
#     only sends notifications if you are marked away.
# 2011-09-19, sitaktif
#     version 1.0.1: Corrected a bug with debug functions
# 2011-07-22, sitaktif
#     version 1.0.0: Initial release

import re
import weechat as w

w.register("nma", "sitaktif", "1.0.6", "GPL2",
    "nma: Receive notifications on NotifyMyAndroid app.", "", "")

# script options
settings = {
    "apikey"               : ("",      "Your NMA API key"),
    "nick_separator_left"  : ("(",     "Left separator for the nick that highlighted you"),
    "nick_separator_right" : (") ",    "Right separator for the nick that highlighted you"),
    "emergency_hilights"   : ("-1",    "Emergency of the highlight notifications (-2 is lowest, 2 is highest)"),
    "emergency_priv_msg"   : ("0",     "Emergency of the query notifications (-2 is lowest, 2 is highest)"),
    "activated"            : ("on",    "Whether the plugin will send notifications or not"),
    "notify_hilights"      : ("on",    "Send NMA notifications when you get highlights"),
    "notify_priv_msg"      : ("on",    "Send NMA notifications when you get a query message"),
    "use_push_if_possible" : ("on",    "If on, will try to fit the whole message in the title, which is send with the PUSH protocol. This makes you receive queries more quickly."),
    "smart_notification"   : ("off",   "Don't send notifications if you are focusing the channel (default: off)"),
    "only_away"            : ("off",   "Only send notifications if you are away"),
    "debug"                : ("off",   "Print debug messages"),
}

#severity_t = {
#    "emergency" : 2,
#    "high" : 1,
#    "normal" : 0,
#    "moderate" : -1,
#    "low": -2
#}

"""
Init
"""

for option, (default_value, description) in settings.items():
    if w.config_get_plugin(option) == "":
        w.config_set_plugin(option, default_value)
    if description:
        w.config_set_desc_plugin(option, description)

if w.config_get_plugin("apikey") == "":
    w.prnt("", "[nma] - You haven't set your API key. Use /set "
            "plugins.var.python.nma.apikey \"you_nma_api_token\" "
            "to fix that.")


"""
Hooks
"""

# Hook command
w.hook_command("nma", "Activate NotifyMyAndroid notifications",
        "on | off | test",
        """    on : Activate notifications
    off : Deactivate notifications
    test : Test a notification\n
        """,
        "on || off || test",
        "nma_cmd_cb", "");
# Hook privmsg/hilights
w.hook_print("", "irc_privmsg", "", 1, "priv_msg_cb", "")

from pynma import PyNMA
p = PyNMA()

"""
Helpers
"""

def _debug(text):
    if w.config_string_to_boolean(w.config_get_plugin("debug")):
        w.prnt("", "[nma] - %s" % text)

def nma_get_instance():
    global p
    for k in p._apikey:
        p.delkey(k)
    key = w.config_get_plugin("apikey")
    if key:
        p.addkey(key)
    else:
        w.prnt("", "[nma] - Cannot do anyting without an API key.")
        return None
    return p


"""
Functions
"""

# /nma command callback. Arguments: bool (on/off)
def nma_cmd_cb(data, buffer, args):
    if args.strip() == "test":
        send_notification("This is a weechat nma plugin test",
                "If you receive that, your configuration is ok", 0)
        return w.WEECHAT_RC_OK

    bool_arg = w.config_string_to_boolean(args)
    status = "%sactivated" % ("" if bool_arg else "de")
    ret = w.config_set_plugin('activated', args)
    if ret == w.WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE:
        w.prnt("", "...NMA was already %s" % status)
    elif ret == w.WEECHAT_CONFIG_OPTION_SET_ERROR:
        w.prnt("", "Error while setting the config.")
        return w.WEECHAT_RC_ERROR
    else:
        w.prnt("", "Notify My Android notifications %s." % status)
    return w.WEECHAT_RC_OK


def priv_msg_cb(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishilight, prefix, message):
    """Sends highlighted message to be printed on notification"""

    if not w.config_string_to_boolean(w.config_get_plugin('activated')):
        _debug('Plugin not activated. Not sending.')
        return w.WEECHAT_RC_OK

    if (w.config_string_to_boolean(w.config_get_plugin('smart_notification')) and
            bufferp == w.current_buffer()):
        _debug('"smart_notification" option set but you are on this buffer already. Not sending.')
        return w.WEECHAT_RC_OK

    if (w.config_string_to_boolean(w.config_get_plugin('only_away')) and not
            w.buffer_get_string(bufferp, 'localvar_away')):
        _debug('"only_away" option set but you are not away. Not sending.')
        return w.WEECHAT_RC_OK

    notif_body = u"%s%s%s%s" % (
            w.config_get_plugin('nick_separator_left').decode('utf-8'),
            prefix.decode('utf-8'),
            w.config_get_plugin('nick_separator_right').decode('utf-8'),
            message.decode('utf-8'))


    # Check that it's in a "/q" buffer and that I'm not the one writing the msg
    is_pm = w.buffer_get_string(bufferp, "localvar_type") == "private"
    is_notify_private = re.search(r'(^|,)notify_private(,|$)', tagsn) is not None
    # PM (query)
    if (is_pm and is_notify_private and
            w.config_string_to_boolean(w.config_get_plugin('notify_priv_msg'))):
        send_notification("IRC private message",
        notif_body, int(w.config_get_plugin("emergency_priv_msg")))


    # Highlight (your nick is quoted)
    elif (ishilight == "1" and
            w.config_string_to_boolean(w.config_get_plugin('notify_hilights'))):
        bufname = (w.buffer_get_string(bufferp, "short_name") or
                w.buffer_get_string(bufferp, "name"))
        send_notification(bufname.decode('utf-8'), notif_body,
                int(w.config_get_plugin("emergency_hilights")))

    return w.WEECHAT_RC_OK


def send_notification(chan, message, priority):
    p = nma_get_instance()
    if not(p):
        w.prnt("", "[nma] - Problem with NMA instance. Not sending notification")
        return None

    _debug("Sending notif with chan '%s', message '%s' and priority '%s'." %
            (chan, message, priority))
    if w.config_string_to_boolean(w.config_get_plugin('use_push_if_possible')):
        # So far, the length is hardcoded in pynma.py...
        if len(chan) + len(message) < 1021:
            chan = "%s - %s" % (chan, message)
            message = ""
    ret = p.push("[IRC]", chan, message, '', priority, batch_mode=False)
    if ret is not None:
        _debug("Message sent: %s. Return: %s." % (message, ret))

# vim: autoindent expandtab smarttab shiftwidth=4
