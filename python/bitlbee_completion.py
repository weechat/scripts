# based on http://scripts.irssi.org/scripts/bitlbee_tab_completion.pl

import weechat

SCRIPT_NAME = "bitlbee_completion"
SCRIPT_AUTHOR = "Roger Duran <rogerduran@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Add tab completion to bitlbee commands"

OPTS = {
    "server": None,
    "channel": None
    }

TOPIC = "Welcome to the control channel. "\
    "Type \x02help\x02 for help information."

commands = []


def request_completion():
    """
    Request the completion to the bitlbee server and wait for response
    """
    server = OPTS["server"]
    weechat.command(server, "/quote -server %s COMPLETIONS" % server)


def modifier_cb(data, modifier, modifier_data, string):
    """
    When the server returns the completion, update the commands list
    """

    if ":COMPLETIONS" not in string:
        return string
    command = string.split(":COMPLETIONS ")[1]
    if command not in ("OK", "END"):
        commands.append(command)
    return ""


def bitlbee_completion(data, completion_item, buffer, completion):
    """
    Complete bitlbee commands only in the bitlbee buffer
    """

    server = OPTS["server"]
    channel = OPTS["channel"]
    if not server or not channel:
        return weechat.WEECHAT_RC_OK

    buff_name = weechat.buffer_get_string(buffer, "name")
    if buff_name == "%s.%s" % (server, channel):
        for command in commands:
            weechat.hook_completion_list_add(completion, command, 0,
                                             weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


def find_buffer():
    """
    Find the buffer when the plugin starts
    """
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        topic = weechat.infolist_string(infolist, "title")
        if topic == TOPIC:
            name = weechat.infolist_string(infolist, "name")
            set_options(name)
            request_completion()
            break
    weechat.infolist_free(infolist)


def set_options(name):
    server, channel = name.split(".")
    OPTS["server"] = server
    OPTS["channel"] = channel


def print_332(data, buffer, time, tags, displayed, highlight, prefix, message):
    """
    Find the buffer when a new one is open
    """
    if message == TOPIC:
        name = weechat.buffer_get_string(buffer, "name")
        set_options(name)
        request_completion()
    return weechat.WEECHAT_RC_OK


def main():
    weechat.hook_modifier("irc_in_notice", "modifier_cb", "")
    weechat.hook_completion("bitlbee", "bitlbee completion",
                            "bitlbee_completion", "")

    weechat.hook_print('', 'irc_332', '', 1, 'print_332', '')
    weechat.hook_print('', 'irc_topic', '', 1, 'print_332', '')
    find_buffer()

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        main()
