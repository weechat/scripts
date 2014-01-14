# -*- coding: utf-8 -*-
#
# Copyright (C) 2013  Stefan Wold <ratler@stderr.eu>
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
# WeeChat script for UnderNET's X OTP (OATH-TOTP) authentication
#
# The script will generate an OTP and automatically append it when it
# notices /msg x@channels.undernet.org login <username> <password> command.
# This allows OTP login when using irc.server.*.command to automatically
# sign in to the X service when connecting to an undernet server.
#
# Configuration:
#  /set plugins.var.python.undernet-totp.otp_server_names "<server1>,<server2>,..."
#  Set servers for which to automatically enable OTP login
#
# Commands:
#  /uotp <server>
#  Generate an OTP for supplied server, output in core buffer.
#


SCRIPT_NAME    = "undernet_totp"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "UnderNET X OTP (OATH-TOTP) authentication"
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


def unhook(hook):
    global HOOKS

    if hook in HOOKS:
        print_debug('Unhooking %s' % hook)
        weechat.unhook(HOOKS[hook])
        del HOOKS[hook]


def unhook_all(server):
    for hook in [server+'.notice', server+'.modifier']:
        unhook(hook)


def hook_all(server):
    global HOOKS

    notice = server + '.notice'
    modifier = server + '.modifier'

    if notice not in HOOKS:
        HOOKS[notice]   = weechat.hook_signal("%s,irc_raw_in_notice" % server, "auth_success_cb", server)
    if modifier not in HOOKS:
        HOOKS[modifier] = weechat.hook_modifier("irc_out_privmsg", "totp_login_modifier_cb", "")


def totp_login_modifier_cb(data, modifier, server, cmd):
    if server in enabled_servers() and re.match(r'(?i)^PRIVMSG x@channels.undernet.org :login .+ .+', cmd):
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
    otp = generate_totp(server)

    if otp is not None:
        weechat.prnt("", "%s OTP: %s" % (server, otp))

    return weechat.WEECHAT_RC_OK


def enabled_servers():
    def server_exists(server):
        print_debug('enabled_servers(%s)' % server)
        if weechat.config_get('irc.server.%s.addresses' % server) is not '':
            return True
        return False

    servers = weechat.config_get_plugin('otp_server_names')
    return [s.strip() for s in servers.split(',') if server_exists(s.strip())]


def generate_totp(server, period=30):
    print_debug('generate_totp(%s)' % server)
    seed = weechat.string_eval_expression("${sec.data.%s_seed}" % server, {}, {}, {})

    if seed is "":
        weechat.prnt("", "No OATH-TOTP secret set, use: /secure set %s_seed <secret>" % server)
        return None

    if len(seed) == 40:  # Assume hex format
        seed = unhexlify(seed)
    else:
        seed = b32decode(seed, True)

    t = pack(">Q", int(time() / period))
    _hmac = hmac.new(seed, t, sha1).digest()
    o = ord(_hmac[19]) & 15
    otp = (unpack(">I", _hmac[o:o+4])[0] & 0x7fffffff) % 1000000

    return '%06d' % otp


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040200:
            weechat.prnt("", "%s requires WeeChat >= 0.4.2 for secure_data support." % SCRIPT_NAME)
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND, "Generate OTP for supplied server", "<server>", "", "%(irc_servers)", "get_otp_cb", "")
        weechat.hook_signal("irc_server_connecting", "signal_cb", "")
        weechat.hook_signal("irc_server_disconnected", "signal_cb", "")

        for option, default_value in SETTINGS.items():
            if weechat.config_get_plugin(option) == "":
                weechat.config_set_plugin(option, default_value[0])
            weechat.config_set_desc_plugin(option, '%s (default: %s)' % (default_value[1], default_value[0]))

        # For now we enable the hooks until it's possible to force script plugins to
        # load before the irc plugin on weechat startup, otherwise the irc_server_connecting signal
        # get missed.
        for _server in enabled_servers():
            hook_all(_server)
