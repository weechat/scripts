# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 by Ricky Brent <ricky@rickybrent.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""Automatically merge new irc buffers according to defined rules.

History:
    * 2017-03-22, Ricky Brent <ricky@rickybrent.com>:
          version 0.1: initial release
"""

from __future__ import print_function
import re
try:
    import weechat
    IMPORT_OK = True
except ImportError:
    print('Script must be run under weechat. http://www.weechat.org')
    IMPORT_OK = False

VERSION = '0.1'
NAME = 'automerge'
AUTHOR = 'Ricky Brent <ricky@rickybrent.com>'
DESC = 'Merge new irc buffers according to defined rules.'

DELIMITER1 = '|@|'
DELIMITER2 = '|!|'

CMD_DESC = '''List, add, delete or apply automerge rules.

Adding a rule takes two parameters: a regular expression to match the target, and \
a regular expression, integer, or the special string 'server' to match the \
destination.

Optionally, the first parameter can be omitted; in this case, the active buffer name will be used.

Rules can be deleted by their regular expression or their index.'''
CMD_LIST = ['list', 'add', 'delete', 'bufferlist', 'apply']
CMD_COMPLETE = '||'.join(CMD_LIST)

def find_merge_id(buf, merge):
    """Find the id of the buffer to merge to."""
    mid = -1
    if merge.isdigit():
        mid = merge
    elif merge == "server":
        server = weechat.buffer_get_string(buf, 'localvar_server')
        infolist = weechat.infolist_get("buffer", "", "")
        while weechat.infolist_next(infolist) and mid < 0:
            if weechat.infolist_string(infolist, "plugin_name") == "irc":
                buf2 = weechat.infolist_pointer(infolist, "pointer")
                server2 = weechat.buffer_get_string(buf2, 'localvar_server')
                if server == server2:
                    mid = weechat.infolist_integer(infolist, 'number')
        weechat.infolist_free(infolist)
    else:
        infolist = weechat.infolist_get("buffer", "", "")
        prog = re.compile(merge)
        while weechat.infolist_next(infolist) and mid < 0:
            if prog.match(weechat.infolist_string(infolist, "full_name")):
                mid = weechat.infolist_integer(infolist, 'number')
        weechat.infolist_free(infolist)
    return mid

def get_rules():
    """Return a list of rules."""
    rules = weechat.config_get_plugin('rules')
    if rules:
        return rules.split(DELIMITER1)
    else:
        return []

def cb_signal_apply_rules(data, signal, buf):
    """Callback for signal applying rules to the buffer."""
    name = weechat.buffer_get_string(buf, "full_name")
    rules = get_rules()
    for rule in rules:
        pattern, merge = rule.split(DELIMITER2)
        if re.match(pattern, name):
            mid = find_merge_id(buf, merge)
            if mid >= 0:
                weechat.command(buf, "/merge " + str(mid))
    return weechat.WEECHAT_RC_OK

def cb_command(data, buf, args):
    """Handle user commands; add/remove/list rules."""
    list_args = args.split(" ")
    commands = {
        'list': cb_command_list,
        'bufferlist': cb_command_bufferlist,
        'add': cb_command_add,
        'delete': cb_command_delete,
        'del': cb_command_delete,
        'apply': cb_command_apply
    }
    if len(list_args) == 0:
        weechat.command(buf, '/help ' + NAME)
        return weechat.WEECHAT_RC_OK
    elif list_args[0] in commands:
        commands[list_args[0]](data, buf, list_args)
    else:
        weechat.prnt(buf, ("[" + NAME + "] Bad option for /" + NAME + " "
                           "command, try '/help " + NAME + "' for more info."))
    return weechat.WEECHAT_RC_OK

def cb_command_list(data, buf, list_args):
    """Print a list all rules."""
    weechat.prnt('', "[" + NAME + "] rules (list)")
    rules = get_rules()
    if len(rules) == 0:
        return weechat.WEECHAT_RC_OK
    for idx, rule in enumerate(rules):
        pattern, merge = rule.split(DELIMITER2)
        weechat.prnt('', '  ' + str(idx) + ": " + pattern + ' = ' + merge)
    return weechat.WEECHAT_RC_OK

def cb_command_bufferlist(data, buf, list_args):
    """Print a list of all buffer names."""
    infolist = weechat.infolist_get("buffer", "", "")
    weechat.prnt('', "[" + NAME + "] buffer list")
    while weechat.infolist_next(infolist):
        weechat.prnt('', '  ' + weechat.infolist_string(infolist, "full_name"))
    weechat.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK

def cb_command_add(data, buf, list_args):
    """Add a rule."""
    rules = get_rules()
    if len(list_args) == 3:
        rule = list_args[1]
        match = list_args[2]
    elif len(list_args) == 2:
        rule = weechat.buffer_get_string(buf, "name")
        match = list_args[1]
    else:
        return bad_command(buf)
    rules.append(DELIMITER2.join([rule, match]))
    weechat.config_set_plugin('rules', DELIMITER1.join(rules))
    weechat.prnt('', "[" + NAME + "] rule added: " + rule + " => " + match)
    return weechat.WEECHAT_RC_OK

def cb_command_delete(data, buf, list_args):
    """Delete a rule."""
    rules = get_rules()
    if len(list_args) == 2:
        rules2 = []
        for idx, rule in enumerate(rules):
            pattern, dummy = rule.split(DELIMITER2)
            if str(idx) != list_args[1] and pattern != list_args[1]:
                rules2.append(rule)
        weechat.config_set_plugin('rules', DELIMITER1.join(rules2))
        if len(rules2) == len(rules):
            weechat.prnt('', "[" + NAME + "] rule not found")
        else:
            weechat.prnt('', "[" + NAME + "] rule deleted")
    return weechat.WEECHAT_RC_OK

def cb_command_apply(data, buf, list_args):
    """Apply the rules the all existing buffers; useful when testing a new rule."""
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        buf2 = weechat.infolist_pointer(infolist, "pointer")
        cb_signal_apply_rules(data, None, buf2)
    weechat.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK

def bad_command(buf):
    """Print an error message about the command."""
    weechat.prnt(buf, ("[" + NAME + "] Bad option for /" + NAME + " "
                       "command, try '/help " + NAME + "' for more info."))
    return weechat.WEECHAT_RC_OK

if IMPORT_OK:
    weechat.register(NAME, AUTHOR, VERSION, 'GPL2', DESC, '', '')
    weechat.hook_signal('irc_channel_opened', 'cb_signal_apply_rules', '')
    weechat.hook_signal('irc_pv_opened', 'cb_signal_apply_rules', '')
    weechat.config_set_desc_plugin('rules', 'Rules to follow when automerging.')
    if not weechat.config_is_set_plugin('rules'):
        weechat.config_set_plugin('rules', '')
    weechat.hook_command(NAME, CMD_DESC, '[' + '|'.join(CMD_LIST) + ']',
                         '', CMD_COMPLETE, 'cb_command', '')
