# -*- coding: utf-8 -*-

"""
xfer_scp.py - a weechat script to scp files after xfer completes

Settings:
    * plugins.var.python.xfer_scp.remote_host <string: ip/hostname>
    * plugins.var.python.xfer_scp.remote_user <string: ip/hostname>
    * plugins.var.python.xfer_scp.remote_port <int: port number>
    * plugins.var.python.xfer_scp.remote_default_dir <string: path to a default directory for files received that don't match a pattern, must set send_only_matches to false>
    * plugins.var.python.xfer_scp.local_identity_key <string: path to RSA key to use for scp auth>
    * plugins.var.python.xfer_scp.delete_after_send <string: true/false to delete file from filesystem after successful send>
    * plugins.var.python.xfer_scp.send_only_matches <string: true/false to send files not found with matching pattern to remote_default_dir>

Commands:
    * /scp add <regex> <remote_dir>
        Send files matching <regex> to a different directory on the remote host
    * /scp list
        See all existing rules
    * /scp del <rule_number>
        Remove an existing rule

Version: 1.0.5
Author: Grant Bacon <btnarg@gmail.com>
License: GPL3
Date: 17 Mar 2017
"""

import_ok = True

try:
    import weechat
    import re
except:
    print("You must run this script within Weechat!")
    print("http://www.weechat.org")
    import_ok = False

#####
# Registration
#####
SCRIPT_NAME = "xfer_scp"
SCRIPT_AUTHOR = "Grant Bacon <btnarg@gmail.com>"
SCRIPT_VERSION = "1.0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Send files via scp after xfer completes, optionally delete after"


#####
# Configuration
#####
patterns = {}
configurations = {
        "delete_after_send" : "false",
        "remote_host" : "",
        "remote_user" : "",
        "local_identity_key" : "",
        "remote_port" : "",
        "remote_default_dir" : "",
        "only_send_matches" : "true",
        "patternlist" : ""
}

def xfer_scp_process_cb(data, command, rc, out, err):
    if rc == 0:
        # process has terminated successfully
        weechat.prnt('', "xfer_scp: File " + data + " sent via SCP successfully")
        if configurations['delete_after_send'].lower() == "true":
            del_file(data)

        weechat.hook_signal_send("xfer_scp_success", weechat.WEECHAT_HOOK_SIGNAL_STRING, data.rsplit("/", 1).pop())
        return weechat.WEECHAT_RC_OK

    elif rc > 0:
        # process terminated unsuccesfully
        weechat.prnt('', "xfer_scp: File " + data + " did not send successfully")

        weechat.hook_signal_send("xfer_scp_failure", weechat.WEECHAT_HOOK_SIGNAL_STRING, data.rsplit("/", 1).pop())
        return weechat.WEECHAT_RC_ERROR

    else:
        return weechat.WEECHAT_RC_OK

def xfer_del_process_cb(data, command, rc, out, err):
    if rc == 0:
        weechat.prnt('', "xfer_scp: File " + data + " deleted.")
        return weechat.WEECHAT_RC_OK
    else:
        weechat.prnt('', "xfer_scp: Error deleting file " + data + ". Msg: " + err)
        return weechat.WEECHAT_RC_ERROR

def scp_file(filename, remote_dir):
    command_string = "scp -q"
    if configurations['local_identity_key'] != "":
        command_string += " -i " + configurations['local_identity_key']
    if configurations['remote_port'] != "":
        command_string += " -P " + configurations['remote_port']
    command_string += " " + filename
    if configurations['remote_user'] != "":
        command_string += " " + configurations['remote_user'] + "@"
    command_string += configurations['remote_host']
    command_string += ":"
    command_string += remote_dir

    weechat.hook_process(command_string, 0, 'xfer_scp_process_cb', filename)

def del_file(filename):
    command_string = "rm " + filename
    weechat.hook_process(command_string, 0, 'xfer_del_process_cb', filename)

def refresh_configurations():
    global configurations
    for key in configurations.keys():
        configurations[key] = weechat.config_get_plugin(key)

def refresh_patterns():
    global patterns
    patlist = weechat.config_get_plugin('patternlist')
    if patlist != "":
        patterns = dict(item.split('|') for item in patlist.split('||'))
    else:
        patterns = {}


####
# rebuild_patternlist
####
def rebuild_patternlist():
    new_patlist = "||".join(map("|".join, patterns.items()))
    weechat.config_set_plugin('patternlist', new_patlist)

#####
# xfer_scp Command
#####
def xfer_scp_cmd_cb(data, buffer, args):
    """/xfer_scp callback"""
    global patterns
    largs = args.split(' ') # split args into list of arguments
    refresh_patterns()

    if largs[0] == 'list':
        count = 1
        if len(patterns) is 0:
            weechat.prnt("", "xfer_scp: There are no patterns (create new pattern with /xfer_scp add <regex> <remote_dir>)")
        for item in patterns.items():
            line = "%d: \t %s -->\t %s" % (count, item[0], item[1])
            weechat.prnt('', line)
            count += 1

    elif largs[0] == 'add':
        rule = (regex, remote_dir) = largs[1], " ".join(largs[2:])
        patterns[regex] = remote_dir
        rebuild_patternlist()
        refresh_patterns()

    elif largs[0] == 'del':
        try:
            rule = int(largs[1])
        except TypeError:
            weechat.prnt("", "xfer_scp: You must supply a rule number as an integer.")

        if rule != "":
            del patterns[patterns.items()[rule-1][0]] # remove by key as integer, seems kind of hacky though.
            rebuild_patternlist()
            refresh_patterns()
            weechat.prnt("", "xfer_scp: Removed rule #%d" % (rule))

    else:
        return weechat.WEECHAT_RC_ERROR

    return weechat.WEECHAT_RC_OK

#####
# hooks
#####
def xfer_ended_signal_cb(data, signal, signal_data):
    weechat.infolist_next(signal_data)
    status_string, filename, local_filename = weechat.infolist_string(signal_data, 'status_string'), weechat.infolist_string(signal_data, 'filename'), weechat.infolist_string(signal_data, 'local_filename')

    if status_string == "done":
        for pattern in patterns.keys():
            if re.match(pattern, filename):
                scp_file(local_filename, patterns[pattern])
                return weechat.WEECHAT_RC_OK
        if configurations['only_send_matches'] == "false" and 'remote_default_dir' in configurations:
            scp_file(local_filename, configurations['remote_default_dir'])
            return weechat.WEECHAT_RC_OK

    return weechat.WEECHAT_RC_OK


def config_changed_cb(data, option, value):
    if option is "plugins.var.python.xfer_scp.patternlist":
        refresh_patterns()
    else:
        refresh_configurations()

    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        for option, default_value in configurations.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

        weechat.hook_command(SCRIPT_NAME,
            'Manage xfer_scp patterns list',
            '[add pattern remote_dir] | [list] | [del pattern_num]',
            '   add: add a pattern to the list\n'
            '   list: list existing patterns\n'
            '   del: remove a pattern from the list\n',
            '', # TODO: completions
            'xfer_scp_cmd_cb',
            '')

        weechat.hook_signal('xfer_ended', 'xfer_ended_signal_cb', '')
        weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "config_changed_cb", "")
        refresh_patterns()
        refresh_configurations()
