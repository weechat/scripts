"""Unlike most automatic op/voice plugins, this plugin uses the reop (R) and invite (I) lists of a channel for automatic op and voice control. This allows for transparent and centralised channel administration while responsibility is shared with all channel operators. This is particularly useful for networks that have no services (e.g., IRCnet).


Subcommands

    list: Show the reop and invite lists of all activated channels.
    reload: Reload the reop and invite lists for all activated channels.


Configuration

The plugin can be enabled or disabled via the following setting.

    /set plugins.var.python.reop.enabled

The plugin can be activated for channels in a particular network by adding a key-value pair to the configuration with the name of the network as the key and a comma separated list of channel names as its value. E.g., the following activates the plugin for channels #chan1 and #chan2 on ircnet.

    /set plugins.var.python.reop.net.ircnet #chan1,#chan2

Servers or other clients may also set user privileges. To avoid unnecessary chatter, the current user privileges are checked some time after a user joins. Only if the privilege level is lower than configured in the reop and invite lists, the appropriate privileges are granted. The delay is configured via the following setting.

    /set plugins.var.python.reop.delay 1000


Usage

Operator control is managed by manipulating the reop (R) list.

Grant operator privileges.

    /mode #chan1 +R nick!user@host.name

Revoke operator privileges.

    /mode #chan1 -R nick!user@host.name

Voice control is managed by manipulating the invite (I) list.

Grant voice privileges.

    /mode #chan1 +I nick!user@host.name

Revoke voice privileges.

    /mode #chan1 -I nick!user@host.name
"""
from weechat import (
    WEECHAT_RC_OK, buffer_search, command, config_get_plugin,
    config_set_plugin, hook_command, hook_modifier, hook_signal, hook_timer,
    info_get, info_get_hashtable, infolist_get, infolist_free, infolist_next,
    infolist_string, prnt, register, string_match)

_name = 'reop'
_author = 'Jeroen F.J. Laros <jlaros@fixedpoint.nl>'
_version = '1.0.0'
_license = 'MIT'
_description = 'Use reop and invite lists for automatic op/voice control.'

reop_data = {}


def _parse(signal, signal_data):
    """Parse a signal."""
    network = signal.split(',')[0]
    msg = info_get_hashtable('irc_message_parse', {'message': signal_data})
    buf = info_get('irc_buffer', '{},{}'.format(network, msg['channel']))

    return network, msg, buf


def _level(network, channel, nick):
    """Determine the current privilege level."""
    nicks = infolist_get(
        'irc_nick', '', '{},{},{}'.format(network, channel, nick))

    prefix = ' '
    while infolist_next(nicks):
        prefix = infolist_string(nicks, 'prefix')

    infolist_free(nicks)

    # y q a o h v *
    return [' ', '+', '@'].index(prefix)


def timer_cb(data, remaining_calls):
    """Timer callback."""
    buf, level, network, channel, nick = reop_data['cmd'].pop()

    if _level(network, channel, nick) < level:
        if level == 2:
            command(buf, '/mode {} +o {}'.format(channel, nick))
        elif level == 1:
            command(buf, '/mode {} +v {}'.format(channel, nick))

    return WEECHAT_RC_OK


def _schedule(buf, level, network, channel, nick):
    """Schedule a mode change."""
    reop_data['cmd'].append((buf, level, network, channel, nick))
    hook_timer(reop_data['delay'], 0, 1, 'timer_cb', '')


def _join(buf, channel):
    """Get reop and invite lists."""
    reop_data['hide'] += 2

    command(buf, '/mode {} R'.format(channel))
    command(buf, '/mode {} I'.format(channel))


def join_cb(data, signal, signal_data):
    """Join callback."""
    network, msg, buf = _parse(signal, signal_data)

    cache = reop_data['cache']
    if network in cache:
        channel = msg['channel']

        if channel in cache[network]:
            nick = msg['nick']
            host = msg['host']

            if nick != info_get('irc_nick', network):
                # Someone is joining.
                for mask in cache[network][channel]['reop']:
                    if string_match(host, mask, 1):
                        _schedule(buf, 2, network, channel, nick)
                        return WEECHAT_RC_OK

                for mask in cache[network][channel]['invite']:
                    if string_match(host, mask, 1):
                        _schedule(buf, 1, network, channel, nick)
                        return WEECHAT_RC_OK
            else:
                # User is joining.
                cache[network][channel] = {'reop': set(), 'invite': set()}
                _join(buf, channel)

    return WEECHAT_RC_OK


def list_cb(data, signal, signal_data):
    """List callback."""
    network, msg, _ = _parse(signal, signal_data)

    cache = reop_data['cache']
    if network in cache:
        channel = msg['channel']

        if channel in cache[network]:
            mask = msg['text']
            command = msg['command']

            if command == '344':
                cache[network][channel]['reop'].add(mask)
            elif command == '346':
                cache[network][channel]['invite'].add(mask)

    return WEECHAT_RC_OK


def mode_cb(data, signal, signal_data):
    """Mode callback."""
    network, msg, _ = _parse(signal, signal_data)

    cache = reop_data['cache']
    if network in cache:
        channel = msg['channel']

        if channel in cache[network]:
            mode, mask = msg['text'].split(' ')[:2]

            if mode == '+R':
                cache[network][channel]['reop'].add(mask)
            elif mode == '-R':
                cache[network][channel]['reop'].discard(mask)
            elif mode == '+I':
                cache[network][channel]['invite'].add(mask)
            elif mode == '-I':
                cache[network][channel]['invite'].discard(mask)

    return WEECHAT_RC_OK


def _format(d, indent=0):
    """Pretty print a dictionary."""
    for key in d:
        prnt('', '{}{}'.format(indent * ' ', key))

        if isinstance(d, dict):
            _format(d[key], indent + 2)


def _init_cache():
    """Initialise the cache."""
    reop_data.update({
        'cache': {}, 'cmd': [], 'hide': 0,
        'delay': int(config_get_plugin('delay'))})

    networks = infolist_get('irc_server', '', '')

    while infolist_next(networks):
        network = infolist_string(networks, 'name')
        channels = config_get_plugin('net.{}'.format(network))

        if channels:
            cache = reop_data['cache']
            cache[network] = {}

            for channel in channels.split(','):
                cache[network][channel] = {
                    'reop': set(), 'invite': set()}

                buf = buffer_search('irc', '{}.{}'.format(network, channel))
                if buf:
                    _join(buf, channel)

    infolist_free(networks)


def command_cb(data, buf, args):
    """Command callback."""
    cmd = args.split(' ')[0]

    if cmd == 'list':
        prnt('', '\nReop cache (pending {}):\n'.format(reop_data['hide']))
        _format(reop_data['cache'])
    elif cmd == 'reload':
        _init_cache()

    return WEECHAT_RC_OK


def modifier_cb(data, modifier, modifier_data, string):
    """Print modifier callback."""
    tagset = set(modifier_data.split(';')[-1].split(','))

    if reop_data['hide']:
        if {'irc_344', 'irc_346'} & tagset:
            return ''
        if {'irc_345', 'irc_347'} & tagset:
            reop_data['hide'] -= 1
            return ''

    return string


def _config():
    """Configuration."""
    if not config_get_plugin('enabled'):
        config_set_plugin('enabled', 'on')
    status = config_get_plugin('enabled')

    if not config_get_plugin('delay'):
        config_set_plugin('delay', '5000')

    return status == 'on'


def main():
    """Initialisation."""
    register(_name, _author, _version, _license, _description, '', '')

    if not _config():
        return

    _init_cache()

    hook_signal('*,irc_in2_join', 'join_cb', '')
    hook_signal('*,irc_in2_344', 'list_cb', '')
    hook_signal('*,irc_in2_346', 'list_cb', '')
    hook_signal('*,irc_in2_mode', 'mode_cb', '')

    hook_modifier('weechat_print', 'modifier_cb', '')

    hook_command(
        'reop', '{}\n\n{}'.format(_description, __doc__), 'list | reload',
        '', '', 'command_cb', '')


if __name__ == '__main__':
    main()
