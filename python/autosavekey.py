#
# SPDX-FileCopyrightText: 2013-2026 nils_2 <libera.#weechat>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# idea by freenode.elsae
#
# 2026-10-03: nils_2, (libera.#weechat)
#       0.6 : security: validate channel names and keys (no whitespace, commas,
#             control characters or "${" expressions) before touching any option
#           : security: write autojoin through the config API instead of /set,
#             so the key is never parsed/evaluated as a command and never shown
#             in a buffer
#           : fix: MODE parsing handles combined modes (+nk, +ntk ...) and
#             short/malformed messages (IndexError)
#           : fix: 324 parsing handles modes with parameters before the key (+lk)
#           : fix: off-by-one when looking up the key of a channel
#           : fix: empty autojoin no longer produces an empty channel entry
#           : fix: channels without key are moved into the keyed section
#           : fix: missing/temporary server options are handled
#           : cleanup: shared parser/serializer, no bare except, no dead code
#
# 2019-10-03: nils_2, (freenode.#weechat)
#       0.5 : channel wasn't added when autojoin was empty (reported by jackie123)
#           : bump min. version to 0.4.2
#
# 2018-05-11: nils_2, (freenode.#weechat)
#       0.4 : make script python3 compatible
#           : add /help text
#
# 2015-05-09: nils_2, (freenode.#weechat)
#       0.3 : fix: ValueError (reported by: Darpa)
#
# 2014-12-20: nils_2, (freenode.#weechat)
#       0.2 : add option "add" to automatically add channel/key to autojoin option after a /join (idea by Prezident)
#
# 2013-10-03: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.4.2
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

import re
import sys

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    sys.exit(1)

SCRIPT_NAME     = "autosavekey"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.6"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "save channel key from protected channel(s) to autojoin option or secure data"

DEFAULTS        = { 'mute'        : ('off', 'do not print a confirmation message and run /secure silently, only error messages will be displayed.'),
                    'secure'      : ('off', 'change channel key in secure data.'),
                    'add'         : ('off', 'adds channel and key to autojoin list on /join, if the channel is not already in the list'),
                  }
OPTIONS         = {}

# ================================[ validation ]===============================
# Keys and channel names end up in a comma/space separated option value that
# WeeChat evaluates later ("${...}"), so be strict about what we accept.
MAX_KEY_LEN     = 64
CHANNEL_RE      = re.compile(r'^[#&+!][^\s,\x00-\x1f\x7f]{0,199}\Z')
KEY_RE          = re.compile(r'^[^\s,\x00-\x1f\x7f]+\Z')
SECURE_KEY_RE   = re.compile(r'^\$\{sec\.data\.([A-Za-z0-9_]+)\}\Z')

def valid_channel(channel):
    return bool(CHANNEL_RE.match(channel)) and '${' not in channel

def valid_key(key):
    return (bool(key) and len(key) <= MAX_KEY_LEN
            and bool(KEY_RE.match(key)) and '${' not in key)

def error(server, text):
    weechat.prnt('', '%s%s: [%s] %s' % (weechat.prefix('error'), SCRIPT_NAME, server, text))

# ================================[ options ]===============================
def opt_on(name):
    return OPTIONS.get(name, 'off').strip().lower() in ('on', 'yes', 'true', '1')

def use_mute():
    return '/mute ' if opt_on('mute') else ''

# ================================[ autojoin helpers ]===============================
def get_autojoin_option(server):
    """Return option pointer or '' if the server/option does not exist."""
    return weechat.config_get('irc.server.%s.autojoin' % server)

def parse_autojoin(value):
    """'#a,#b,#c key1,key2' -> (['#a','#b','#c'], ['key1','key2']), None if invalid."""
    if value.count(' ') > 1:
        return None
    if ' ' in value:
        chans, keys = value.split(' ')
    else:
        chans, keys = value, ''
    return ([c for c in chans.split(',') if c],
            [k for k in keys.split(',') if k])

def build_autojoin(channels, keys):
    return ' '.join(part for part in (','.join(channels), ','.join(keys)) if part)

def save_autojoin(server, option, new_value):
    rc = weechat.config_option_set(option, new_value, 1)
    if rc == weechat.WEECHAT_CONFIG_OPTION_SET_ERROR:
        error(server, 'could not set autojoin option.')
        return False
    return True

# ================================[ core logic ]===============================
def update_key(server, channel, new_key, allow_add):
    if not valid_channel(channel):
        error(server, 'ignoring invalid channel name.')
        return
    if not valid_key(new_key):
        error(server, 'key for channel "%s" ignored: contains invalid characters or is too long.' % channel)
        return

    option = get_autojoin_option(server)
    if not option:
        return                      # unknown or temporary server, nothing to do

    autojoin = weechat.config_string(option)
    parsed = parse_autojoin(autojoin)
    if parsed is None:
        error(server, 'autojoin format invalid (two or more spaces).')
        return
    channels, keys = parsed

    if channel in channels:
        pos = channels.index(channel)
        if pos < len(keys):
            old_key = keys[pos]
            match = SECURE_KEY_RE.match(old_key)
            if match:
                # key lives in secure data
                if not opt_on('secure'):
                    error(server, 'key for channel "%s" not changed! option "plugins.var.python.%s.secure" is off and you are using secured data for key.' % (channel, SCRIPT_NAME))
                    return
                weechat.command('', '%s/secure set %s %s' % (use_mute(), match.group(1), new_key))
                return
            if '${' in old_key:
                error(server, 'key for channel "%s" is an expression and was not changed.' % channel)
                return
            if old_key == new_key:
                return
            keys[pos] = new_key     # replace in place, keep order
        else:
            # channel exists but has no key yet: move it into the keyed section
            channels.pop(pos)
            channels.insert(0, channel)
            keys.insert(0, new_key)
    else:
        if not allow_add:
            return
        channels.insert(0, channel)
        keys.insert(0, new_key)

    if save_autojoin(server, option, build_autojoin(channels, keys)) and not opt_on('mute'):
        weechat.prnt('', '%s: [%s] key for channel "%s" saved to autojoin.' % (SCRIPT_NAME, server, channel))

# ================================[ mode parsing ]===============================
def mode_param_sets(server):
    """Return (modes always taking a parameter, modes taking one only when set)."""
    chanmodes = weechat.info_get('irc_server_isupport_value', '%s,CHANMODES' % server) or 'beI,k,l,imnpst'
    prefix = weechat.info_get('irc_server_isupport_value', '%s,PREFIX' % server) or '(ov)@+'
    parts = (chanmodes.split(',') + ['', '', '', ''])[:4]
    match = re.match(r'^\(([^)]*)\)', prefix)
    prefix_modes = match.group(1) if match else 'ov'
    return set(parts[0] + parts[1] + prefix_modes), set(parts[2])

def find_key_in_modes(server, modes, params):
    """Return the key set by a mode string like '+nlk 10 secret', else None."""
    always, on_set = mode_param_sets(server)
    adding = True
    idx = 0
    for char in modes:
        if char == '+':
            adding = True
        elif char == '-':
            adding = False
        elif char in always:
            param = params[idx] if idx < len(params) else None
            idx += 1
            if char == 'k' and adding:
                return param
        elif char in on_set:
            if adding:
                idx += 1
    return None

def clean_params(params):
    if params and params[-1].startswith(':'):
        params = params[:-1] + [params[-1][1:]]
    return params

# ================================[ callbacks ]===============================
def get_arguments(signal_data):
    parsed = weechat.info_get_hashtable('irc_message_parse', {'message': signal_data})
    return parsed.get('arguments', '').split(' ')

# /join #channel key
# signal = server,irc_raw_in_324
# signal_data = :asimov.freenode.net 324 nick #channel +modes key
def irc_raw_in_324_cb(data, signal, signal_data):
    server = signal.split(',', 1)[0]
    argv = get_arguments(signal_data)
    # nick #channel +modes [params...]
    if len(argv) < 4:
        return weechat.WEECHAT_RC_OK
    channel, modes, params = argv[1], argv[2], clean_params(argv[3:])
    new_key = find_key_in_modes(server, modes, params)
    if new_key:
        update_key(server, channel, new_key, opt_on('add'))
    return weechat.WEECHAT_RC_OK

# replace an already existing channel key with a new one
# when OP changes channel key
def irc_raw_in_mode_cb(data, signal, signal_data):
    server = signal.split(',', 1)[0]
    argv = get_arguments(signal_data)
    # #channel +modes [params...]
    if len(argv) < 3 or not argv[0][:1] in '#&+!':
        return weechat.WEECHAT_RC_OK
    channel, modes, params = argv[0], argv[1], clean_params(argv[2:])
    new_key = find_key_in_modes(server, modes, params)
    if new_key:
        # a key change by an OP only updates channels that are already
        # in autojoin, it never adds new ones
        update_key(server, channel, new_key, False)
    return weechat.WEECHAT_RC_OK

def cmd_autosavekey(data, buffer, args):
    weechat.command('', '/help %s' % SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ weechat options & description ]===============================
def init_options():
    for option, value in DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]
    OPTIONS[option] = value
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC,
                             '',
                             'You have to edit options with: /set *autosavekey*\n'
                             'I suggest using /fset plugin to make changes.\n'
                             '\n'
                             'Keys are only saved if they are valid: no whitespace, commas, control characters\n'
                             'or "${", and at most 64 characters.\n'
                             'A key change by an operator (MODE +k) only updates channels that are already in\n'
                             'the autojoin option. Option "add" applies to /join only.\n'
                             'Keys stored as ${sec.data.NAME} are only changed if option "secure" is on.\n',
                             '',
                             'cmd_autosavekey',
                             '')
        version = weechat.info_get("version_number", "") or 0

        if int(version) >= 0x00040200:
            init_options()
            weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')
            weechat.hook_signal("*,irc_raw_in_mode", "irc_raw_in_mode_cb", "")
            weechat.hook_signal("*,irc_raw_in_324", "irc_raw_in_324_cb", "")
        else:
            weechat.prnt("", "%s%s %s" % (weechat.prefix("error"), SCRIPT_NAME, ": needs version 0.4.2 or higher"))
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)
