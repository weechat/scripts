# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 - 2018  Stefan Wold <ratler@stderr.eu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# (This script requires WeeChat 0.4.2 or higher).
#
# WeeChat script that enables automatic OTP (OATH-TOTP) support for UnderNET's X
# and Login on Connect (LoC) authentication.
#
# The script will generate an OTP and automatically append it when it
# notices /msg x@channels.undernet.org login <username> <password> command.
# This allows OTP login when using irc.server.*.command to automatically
# sign in to the X service when connecting to an undernet server.
#
# Commands:
#  /uotp otp [server]
#  /uotp list
#  /uotp add <server> <seed>
#  /uotp remove <server>
#  /uotp enable <server>
#  /uotp disable <server>


SCRIPT_NAME    = "undernet_totp"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.4.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Automatic OTP (OATH-TOTP) authentication with UnderNET's channel services (X) and Login on Connect (LoC)."
SCRIPT_COMMAND = "uotp"

HOOKS = {}

SETTINGS = {
    "otp_server_names": ("", "List of undernet server for which to enable OTP, use comma as separator"),
    "debug"           : ("off", "Debug output"),
}

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

try:
    import hmac
    import re
    from base64 import b32decode
    from hashlib import sha1
    from struct import pack, unpack
    from time import time
    from binascii import unhexlify
except ImportError as err:
    print "Missing module(s) for %s: %s" % (SCRIPT_NAME, err)
    import_ok = False


def print_debug(message):
    if weechat.config_get_plugin('debug') == 'on':
        weechat.prnt("", "%s DEBUG: %s" % (SCRIPT_NAME, message))

def sprint(message, buffer=""):
    weechat.prnt(buffer, "%s: %s" % (SCRIPT_NAME, message))


def unhook(hook):
    global HOOKS

    if hook in HOOKS:
        print_debug('Unhooking %s' % hook)
        weechat.unhook(HOOKS[hook])
        del HOOKS[hook]


def unhook_all(server):
    for hook in [server+'.notice', server+'.modifier', server+'.modifier2']:
        unhook(hook)


def hook_all(server):
    print_debug("hook_all(%s)" % server)
    global HOOKS

    notice = server + '.notice'
    modifier = server + '.modifier'
    modifier2 = server + '.modifier2'

    if notice not in HOOKS:
        HOOKS[notice] = weechat.hook_signal("%s,irc_raw_in_notice" % server, "auth_success_cb", server)
    if modifier not in HOOKS:
        HOOKS[modifier] = weechat.hook_modifier("irc_out_privmsg", "totp_login_modifier_cb", server)
    if modifier2 not in HOOKS:
        HOOKS[modifier2] = weechat.hook_modifier("irc_out_pass", "totp_login_modifier_cb", server)


def totp_login_modifier_cb(data, modifier, server, cmd):
    if server == data and server in enabled_servers():
        if re.match(r'(?i)^(PRIVMSG x@channels.undernet.org :login .+ .+|PASS .*)', cmd):
            print_debug("totp_login_modifier_cb(%s)" % cmd)
            otp = generate_totp(server)
            if otp is not None:
                cmd += " %s" % otp
    return cmd


def auth_success_cb(server, signal, signal_data):
    if signal_data.startswith(":X!cservice@undernet.org NOTICE"):
        if re.match(r'^:X!cservice@undernet.org NOTICE .+ :AUTHENTICATION SUCCESSFUL', signal_data):
            unhook_all(server)

    return weechat.WEECHAT_RC_OK


def signal_cb(data, signal, server):
    if server in enabled_servers():
        print_debug('signal_cb(%s)' % signal)
        if signal == 'irc_server_connecting':
            hook_all(server)
        elif signal == 'irc_server_disconnected':
            unhook_all(server)

    return weechat.WEECHAT_RC_OK


def get_otp_cb(data, buffer, server):
    if server:
        server = [server]
    else:
        server = enabled_servers()

    for _server in server:
        otp = generate_totp(_server)
        if otp is not None:
            weechat.prnt("", "%s OTP: %s" % (_server, otp))

    return weechat.WEECHAT_RC_OK


def get_irc_servers():
    """ Returns a list of configured IRC servers in weechat"""
    serverptrlist = weechat.infolist_get('irc_server', '', '')
    serverlist = []
    while weechat.infolist_next(serverptrlist):
         serverlist.append(weechat.infolist_string(serverptrlist, 'name'))
    return serverlist


def enabled_servers():
    """ Return a list of TOTP enabled servers. """
    serverlist = get_irc_servers()
    return [s for s in get_config_as_list('otp_server_names') if s in serverlist]


def disabled_servers():
    """ Return a list of configured TOTP servers that are currently disabled. """
    serverlist = get_irc_servers()
    server_seed_list = [server for server in serverlist
                        if weechat.string_eval_expression("${sec.data.%s_seed}" % server, {}, {}, {})
                        and server not in get_config_as_list('otp_server_names')]
    return [s for s in server_seed_list if s in serverlist]


def configured_servers():
    """ Return a lost of servers with an existing seed. """
    serverlist = get_irc_servers()
    return [s for s in serverlist if weechat.string_eval_expression("${sec.data.%s_seed}" % s, {}, {}, {})]


def generate_totp(server, period=30, buffer=""):
    print_debug('generate_totp(%s)' % server)
    seed = weechat.string_eval_expression("${sec.data.%s_seed}" % server, {}, {}, {})

    if not seed:
        sprint("No OATH-TOTP secret set, use: /uotp add %s <seed>" % server, buffer)
        return None

    if len(seed) == 40:  # Assume hex format
        seed = unhexlify(seed)
    else:
        seed = b32decode(seed.replace(" ", ""), True)

    t = pack(">Q", int(time() / period))
    _hmac = hmac.new(seed, t, sha1).digest()
    o = ord(_hmac[19]) & 15
    otp = (unpack(">I", _hmac[o:o+4])[0] & 0x7fffffff) % 1000000

    return '%06d' % otp


def config_update_cb(data, option, value):
    """ Reload hooks on configuration change. """
    print_debug("config_cb(%s)" % value)
    [hook_all(s.strip()) for s in value.split(',')]
    return weechat.WEECHAT_RC_OK


def options_cb(data, buffer, args):
    """ Script configuration callback """
    if not args:
        weechat.command("", "/help %s" % SCRIPT_COMMAND)
    args = args.strip().split(' ')
    opt = args[0]
    opt_args = args[1:]

    if opt == 'otp':
        if opt_args:
            servers = [opt_args[0]]
        else:
            servers = enabled_servers()
        for server in servers:
            otp = generate_totp(server, buffer=buffer)
            if otp:
                sprint("%s = %s" % (server, otp), buffer)
    elif opt == 'list':
        sprint("List of configured servers", buffer)
        for server in enabled_servers():
            weechat.prnt(buffer, "  - %s [enabled]" % server)
        for server in disabled_servers():
            weechat.prnt(buffer, "  - %s [disabled]" % server)
    elif opt == 'add':
        if len(opt_args) >= 2:
            if opt_args[0] not in enabled_servers() and opt_args[0] in get_irc_servers():
                #weechat.command("", "/secure set %s_seed %s" % (opt_args[0], opt_args[1]))
                try:
                    add_server(opt_args[0], opt_args[1:])
                    sprint("server '%s' was successfully added" % opt_args[0], buffer)
                except Exception as ex:
                    sprint("invalid TOTP seed provided", buffer)
            elif opt_args[0] not in get_irc_servers():
                sprint("No server named '%s' was found, see /help server" % opt_args[0], buffer)
            else:
                sprint("OTP already configured for '%s', to change <seed> remove the existing one first." % opt_args[0], buffer)
        else:
            sprint("/uotp -- invalid argument, valid command is /uotp add <server> <seed>", buffer)
    elif opt == 'remove':
        if opt_args[0] in enabled_servers() or opt_args[0] in disabled_servers():
            remove_server(opt_args[0], True)
            sprint("server '%s' was successfully removed" % opt_args[0], buffer)
        else:
            sprint("failed to remove server, '%s' not found" % opt_args[0], buffer)
    elif opt == 'enable':
        if opt_args and opt_args[0] not in enabled_servers():
            if opt_args[0] in get_irc_servers():
                add_server(opt_args[0])
                sprint("server '%s' was successfully enabled" % opt_args[0], buffer)
            else:
                sprint("No server named '%s' was found, see /help server" % opt_args[0], buffer)
        else:
            sprint("OTP is already enabled for the server '%s'." % opt_args[0], buffer)
    elif opt == 'disable':
        if opt_args and opt_args[0] in enabled_servers():
            remove_server(opt_args[0])
        else:
            sprint("OTP does not seem to be enabled for '%s'" % opt_args[0], buffer)
    elif opt:
        sprint("/uotp: invalid option -- '%s'" % opt, buffer)
        weechat.command("", "/help %s" % SCRIPT_COMMAND)

    return weechat.WEECHAT_RC_OK


def get_config_as_list(option):
    """ Return comma-separated <option> as a list. """
    return [o.strip() for o in weechat.config_get_plugin(option).strip().split(',')]


def add_server(server, seed=None):
    """ Append new server to the plugin configuration. """
    if seed:  # Test seed
        if len(seed[0]) == 40:
            unhexlify(seed[0])
            seed = seed[0]
        else:
            b32decode(''.join(seed).replace(" ", ""), True)
            seed = ' '.join(seed)
        weechat.command("", "/secure set %s_seed %s" % (server, seed))

    servers = get_config_as_list("otp_server_names")
    if server not in servers:
        servers.append(server)
        weechat.config_set_plugin("otp_server_names", ','.join(servers))


def remove_server(server, remove_seed=False):
    """ Remove server from the plugin configuration. """
    if remove_seed and weechat.string_eval_expression("${sec.data.%s_seed}" % server, {}, {}, {}):
        weechat.command("", "/secure del %s_seed" % server)

    servers = get_config_as_list("otp_server_names")
    if server in servers:
        servers = [v for v in servers if v != server]
        weechat.config_set_plugin("otp_server_names", ','.join(servers))


def hide_secret_cb(data, modifier, modifier_data, cmd):
    """ Callback to hide seed secret during input by replacing the seed with asterisks (*). """
    match = re.search(r'(?i)^/uotp add \w+ (.+)', cmd)
    if match:
        last_arg = match.group(1)
        rep = '*' * len(last_arg)
        cmd = re.sub('%s$' % last_arg, rep, cmd)
    return cmd


def server_completion_cb(data, completion_item, buffer, completion):
    """ Enabled or disabled server completion callback. """
    print_debug("completion " + ', '.join(globals()[data]()))
    for server in globals()[data]():
        weechat.hook_completion_list_add(completion, server, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040200:
            weechat.prnt("", "%s requires WeeChat >= 0.4.2 for secure_data support." % SCRIPT_NAME)
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND,
                             "Generate a One-Time Password (TOTP) for service authentication or login on connect.",
                             "otp [server] || list || add <server> <seed> || remove <server> || enable <server> || disable <server>",
                             "    otp: generate one-time password for one or all servers\n"+
                             "   list: list configured servers\n"+
                             "    add: add one-time password (TOTP) seed for an existing irc server\n"+
                             " remove: delete one-time password configuration for a server\n"+
                             " enable: re-enable one-time password authentication for a server\n"+
                             "disable: disable one-time password authentiction without removing the seed for a server\n\n"+
                             "Examples:\n"+
                             "  /uotp otp\n"+
                             "  /uotp otp freenode\n"+
                             "  /uotp list\n"+
                             "  /uotp add freenode 4c6fdb7d0659bae2a16d23bab99678462b9f7897\n"+
                             "  /uotp add freenode jrx5 w7ig lg5o filn eo5l tfty iyvz 66ex\n"+
                             "  /uotp remove freenode\n"+
                             "  /uotp enable freenode\n"+
                             "  /uotp disable freenode",
                             "otp %(irc_servers)"
                             " || list"
                             " || add %(irc_servers)"
                             " || remove %(configured_servers)"
                             " || enable %(irc_servers)"
                             " || disable %(disabled_servers)",
                             "options_cb", "")
        weechat.hook_signal("irc_server_connecting", "signal_cb", "")
        weechat.hook_signal("irc_server_disconnected", "signal_cb", "")
        weechat.hook_config("plugins.var.python.undernet_totp.otp_server_names", "config_update_cb", "")
        weechat.hook_completion("configured_servers", "list of otp configured servers", "server_completion_cb", "configured_servers")
        weechat.hook_completion("disabled_servers", "list of disabled servers", "server_completion_cb", "enabled_servers")
        weechat.hook_modifier("input_text_display", "hide_secret_cb", "")

        for option, default_value in SETTINGS.items():
            if weechat.config_get_plugin(option) == "":
                weechat.config_set_plugin(option, default_value[0])
            weechat.config_set_desc_plugin(option, '%s (default: %s)' % (default_value[1], default_value[0]))

        # For now we enable the hooks until it's possible to force script plugins to
        # load before the irc plugin on weechat startup, otherwise the irc_server_connecting signal
        # get missed.
        for server in enabled_servers():
            hook_all(server)
