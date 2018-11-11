#  Project: chanotify
#  Description: A library that call notify-send when message is received
#  on specific server or channel
#  Author: manzerbredes <manzerbredes@gmx.com>
#  License: GPL3
#
#  0.1.0
#  First version, please ask for feature or bugs on my email !

import weechat as weechat

NAME="chanotify"
VERSION="0.1.0"
LICENCE="GPL3"
AUTHOR="manzerbredes"
DESCRIPTION="Call notify-send command when receive a message on a specific server and channel."
HOMEPAGE="http://people.rennes.inria.fr/Loic.Guegan"
CONFIG= {
    "filters": ("*:*", "List of <server>:<channel> separated by comma that will where chanotify will notify. \
                        Note that <server> or <channel> can be * to match every server or channel."),
    "status": ("on", "On/Off chanotify")
}
# Convenient variables
CHANNEL_BYPASS=list() # Contain channels name that will be automatically notified
SERVER_BYPASS=list() # Contain servers name that will be automatically notifier
ALL_BYPASS=False # If true every server and channel will be notified
FILTERS=dict() # Contain list of channels associated with each servers

# Parse filters parameters
def parse_filters(filters):
    global CHANNEL_BYPASS
    global SERVER_BYPASS
    global ALL_BYPASS
    global FILTERS

    elts=filters.split(",")
    for elt in elts:
        server, channel=elt.split(":")
        if server==channel and server=="*":
            ALL_BYPASS=True
        elif server == "*":
            CHANNEL_BYPASS.append(channel)
        elif channel == "*":
            SERVER_BYPASS.append(server)
        else:
            if server in FILTERS:
                FILTERS[server].append(channel)
            else:
                FILTERS[server]=[channel]

def isNotifiable(server,channel):
    global CHANNEL_BYPASS
    global SERVER_BYPASS
    global ALL_BYPASS
    global FILTERS
    global CONFIG

    if CONFIG["status"][0]=="on":
        if (channel in CHANNEL_BYPASS) or (server in SERVER_BYPASS) or ALL_BYPASS:
            return True
        else:
            if server in FILTERS:
                return (channel in FILTERS[server])
    return False

def on_receive(data, signal, signal_data):
    # Fetch server, msg and buffer
    server = signal.split(",")[0]
    msg = weechat.info_get_hashtable("irc_message_parse", {"message": signal_data})
    buffer = weechat.info_get("irc_buffer", "%s,%s" % (server, msg["channel"]))

    # Notify if we get the buffer
    if buffer and isNotifiable(server,msg["channel"]):
        notify_title="On "+msg["channel"]
        notify_msg=msg["nick"]+"> "+msg["text"]
        weechat.hook_process_hashtable("notify-send",
                { "arg1": "-i", "arg2": "weechat",
                  "arg3": "-a", "arg4": "WeeChat",
                  "arg5": notify_title, "arg6": notify_msg},
                20000, "", "")
    return weechat.WEECHAT_RC_OK

# Load the configuration
def update_config(data, option, value):
    global CONFIG
    option=option.split(".")[-1]
    if option != "filters":
        CONFIG[option]=(value,CONFIG[option][1])
    else: # Reset existing filter configuration and set them
        CHANNEL_BYPASS=list()
        SERVER_BYPASS=list()
        ALL_BYPASS=False
        FILTERS=dict()
        parse_filters(CONFIG["filters"][0])

    return weechat.WEECHAT_RC_OK

# Load the script
if __name__ == "__main__":
    # Register plugin
    weechat.register(NAME, AUTHOR, VERSION, LICENCE, DESCRIPTION, "", "UTF-8")

    # Load or set configuration
    for (option,value) in CONFIG.items():
        c = weechat.config_get_plugin(option)
        if len(c) == 0: # Set
            weechat.config_set_plugin(option, value[0])
        else: # Load
            CONFIG[option]=(c,CONFIG[option][1])

    # Watch config changes
    weechat.hook_config("*%s.*"%NAME, "update_config", "")

    # Parse filters
    parse_filters(CONFIG["filters"][0])

    # Watch incoming message
    weechat.hook_signal("*,irc_in2_privmsg", "on_receive", "")
