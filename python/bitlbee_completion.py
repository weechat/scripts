# -*- coding: utf-8 -*-
# Add tab completion to bitlbee commands
# based on http://scripts.irssi.org/scripts/bitlbee_tab_completion.pl
#
# History:
#
# 2023-10-04, Andrea Beciani <andrea.beciani.0@gmail.com>:
#     version 0.3: set default template, fix command executed, fix function names
# 2015-11-02, Mickaël Thomas <mickael9@gmail.com>:
#     version 0.2: strip color attributes for topic detection
# 2015-03-22, Roger Duran <rogerduran@gmail.com>:
#     version 0.1: initial version

import weechat

SCRIPT_NAME = "bitlbee_completion"
SCRIPT_AUTHOR = "Roger Duran <rogerduran@gmail.com>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Add tab completion to bitlbee commands"
TEMPLATE_NAME = "bitlbee_completion"

OPTS = {
    "server": None,
    "channel": None
    }

TOPIC = "Welcome to the control channel. "\
    "Type help for help information."

commands = []


def request_completion():
    """
    Request the completion to the bitlbee server and wait for response
    """
    server = OPTS["server"]
    weechat.command("", "/quote -server %s COMPLETIONS" % server)


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


def completion_cb(data, completion_item, buffer, completion):
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

def check_config():
    option = weechat.config_get("weechat.completion.default_template")
    default_template = weechat.config_string(option)
    if TEMPLATE_NAME not in default_template:
        rc = weechat.config_option_set(option, default_template + "|%(" + TEMPLATE_NAME + ")", 1)
        if rc == weechat.WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE:
            weechat.prnt("", SCRIPT_NAME + " -  warning! - weechat.completion.default_template same value")
        elif rc == weechat.WEECHAT_CONFIG_OPTION_SET_ERROR:
            weechat.prnt("", SCRIPT_NAME + " -  error! - writing weechat.completion.default_template option")

def find_buffer():
    """
    Find the buffer when the plugin starts
    """
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        topic = weechat.infolist_string(infolist, "title")
        if weechat.string_remove_color(topic, "") == TOPIC:
            name = weechat.infolist_string(infolist, "name")
            set_options(name)
            request_completion()
            break
    weechat.infolist_free(infolist)


def set_options(name):
    server, channel = name.split(".")
    OPTS["server"] = server
    OPTS["channel"] = channel


def print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):
    """
    Find the buffer when a new one is open
    """
    current_topic = weechat.string_remove_color(message, "").split('"')[1]
    if current_topic == TOPIC:
        name = weechat.buffer_get_string(buffer, "name")
        set_options(name)
        request_completion()
    return weechat.WEECHAT_RC_OK


def main():
    check_config()
    weechat.hook_modifier("irc_in_notice", "modifier_cb", "")
    weechat.hook_completion(TEMPLATE_NAME, "TAB completion to bitlbee",
                            "completion_cb", "")

    weechat.hook_print('', 'irc_332', '', 1, 'print_cb', '')
    weechat.hook_print('', 'irc_topic', '', 1, 'print_cb', '')
    find_buffer()

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        main()
