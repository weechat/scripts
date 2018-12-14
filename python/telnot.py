# ~*~ coding: utf-8 ~*~
# Author: Frantisek Kolacek <work@kolacek.it>
# Homepage: https://github.com/fkolacek/weechat-telnot

import weechat

try:
    # Python 3
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

weechat.register('telnot',
                 'Frantisek Kolacek <work@kolacek.it>',
                 '1.0',
                 'MIT',
                 'telnot: Send notification over Telegram using TelNot',
                 '',
                 '')

settings = {
    'endpoint': 'Address of server running TelNot instance (including http:// or https://)',
    'token': 'User token',
    'bot': 'Name of Telegram bot',
}

required_settings = [
    'endpoint',
    'token',
    'bot',
]

for option, description in list(settings.items()):
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, '')

    if option in required_settings and weechat.config_get_plugin(option) == '':
        weechat.prnt('', weechat.prefix('error') + 'telnot: Please set option: {}'.format(option))
        weechat.prnt('', 'telnot: /set plugins.var.python.telnot.{} STRING'.format(option))

    weechat.config_set_desc_plugin(option, description)

# buffer, tags, message, strip_colors, callback, callback_data
weechat.hook_print('', 'notify_message', '', 1, 'process_notification', '')
weechat.hook_print('', 'notify_private', '', 1, 'process_notification', '')


def process_notification(data, buffer, date, tags, displayed, highlight, prefix, message):

    if 'notify_message' in tags and not highlight:
        return weechat.WEECHAT_RC_OK

    nick = weechat.buffer_get_string(buffer, 'localvar_nick')
    name = weechat.buffer_get_string(buffer, 'name')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')

    if weechat.buffer_get_string(buffer, 'localvar_type') == 'private' and prefix != nick:
        send_notification(server, channel, prefix, message)
    elif int(highlight):
        buff = weechat.buffer_get_string(buffer, 'short_name') or name

        send_notification(server, buff, prefix, message)

    return weechat.WEECHAT_RC_OK


def send_notification(server, channel, nick, message):
    endpoint = weechat.config_get_plugin('endpoint')
    token = weechat.config_get_plugin('token')
    bot = weechat.config_get_plugin('bot')

    if channel == nick:
        output = '[{}@{}] {}'.format(nick, server, message)
    else:
        output = '[{}@{}] {}: {}'.format(nick, server, channel, message)

    data = urlencode({
        'message': output,
        'token': token,
        'bot': bot,
    })

    options = {
        'postfields': data,
        'ssl_verifypeer': '0',
        'ssl_verifyhost': '0',
    }

    weechat.hook_process_hashtable('url:' + endpoint, options, 2000, '', '')
