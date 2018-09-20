# Copyright 2018 adtac <weechat@adtac.in>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This script allows you to enable push notifications for WeeChat messages on
# your devices using Pushover. See the GitHub repo for more details:
#   https://github.com/adtac/weepushover

import json
import re
import urllib
import time

import weechat as w


description = 'push notifications from weechat to pushover'


help_text = '''
settings: (prefix with plugins.var.python.weepushover.<setting>)
    token                 your application token (required)
    user                  your user token (required)
    ignored_channels      space-separated list of channels to ignore
    subscribed_channels   space-separated list of channels to subscribe to
    away_only             send only when marked as away
    inactive_only         send only when the message is in an inactive buffer
    min_notify_interval   minimum number of seconds to wait before another notification
    debug                 print debug messages in core
'''


configs = {                      # some sane defaults
    'token': '_required',
    'user': '_required',
    'ignored_channels': '',      # no ignored channels
    'subscribed_channels': '',   # no subscribed channels
    'away_only': '1',            # send only when away
    'inactive_only': '0',        # send even if buffer is active
    'min_notify_interval': '60', # send notifications at least a minute apart
    'debug': '0',                # enable debugging
}


last_notification = 0


def debug(msg):
    if str(w.config_get_plugin('debug')) != '0':
        w.prnt('', '[weepushover] debug: {}'.format(str(msg)))


def register():
    global last_notification
    last_notification = 0

    w.register('weepushover', 'adtac', '0.1', 'MIT', description, '', '')


def load_settings():
    for (option, default_value) in configs.items():
        if w.config_get_plugin(option) == '':
            if configs[option] == '_required':
                w.prnt('', 'missing plugins.var.python.weepushover.{}'.format(option))
            else:
                w.config_set_plugin(option, configs[option])


def setup_hooks():
    global description
    global help_text

    w.hook_print('', '', '', 1, 'message_hook', '')
    w.hook_command('weepushover', description, '[command]', help_text, '', 'show_help', '')


def get_channels(kind):
    channels = w.config_get_plugin('{}_channels'.format(kind)).strip()
    if channels == '':
        return set([])
    else:
        return set([channel.strip() for channel in channels.split(' ') if channel])


def show_help(data, buffer, args):
    w.prnt('', help_text)
    return w.WEECHAT_RC_OK


def away_only_check(bufferp):
    if w.config_get_plugin('away_only') != '1':
        return False

    return not w.buffer_get_string(bufferp, 'localvar_away')


def inactive_only_check(bufferp):
    if w.config_get_plugin('inactive_only') != '1':
        return False

    return w.current_buffer() == bufferp


def interval_limit_check():
    interval = w.config_get_plugin('min_notify_interval')

    if interval is None or interval == '':
        return False

    try:
        interval = int(interval)
    except ValueError:
        w.prnt('', '[weepushover] min_notify_interval not an integer')
        return False

    global last_notification

    debug('current={}, last_notification={}, earliest_possible={}'.format(
        time.time(), last_notification, last_notification + interval))
    return time.time() < last_notification + interval


def get_buf_name(bufferp):
    short_name = w.buffer_get_string(bufferp, 'short_name')
    name = w.buffer_get_string(bufferp, 'name')
    return (short_name or name).decode('utf-8')


def is_ignored(bufferp):
    buf_name = get_buf_name(bufferp)
    return buf_name in get_channels('ignored')


def is_subscribed(bufferp):
    buf_name = get_buf_name(bufferp)
    return buf_name in get_channels('subscribed')


def message_hook(data, bufferp, uber_empty, tagsn, is_displayed, is_highlighted, prefix, message):
    is_pm = w.buffer_get_string(bufferp, 'localvar_type') == 'private'
    regular_channel = not is_subscribed(bufferp) and not is_pm

    if away_only_check(bufferp):
        debug('failed away_only_check; skipping')
        return w.WEECHAT_RC_OK

    if inactive_only_check(bufferp):
        debug('failed inactive_only_check; skipping')
        return w.WEECHAT_RC_OK

    if interval_limit_check():
        debug('failed interval_limit_check; skipping')
        return w.WEECHAT_RC_OK

    if is_ignored(bufferp) and regular_channel:
        debug('ignored regular channel skipping')
        return w.WEECHAT_RC_OK

    if not is_displayed:
        debug('not a displayed message; skipping')
        return w.WEECHAT_RC_OK

    if not is_highlighted and regular_channel:
        debug('not highlighted on a regular channel; skipping')
        return w.WEECHAT_RC_OK

    debug('passed all checks')

    if is_pm:
        title = 'Private message from {}'.format(prefix.decode('utf-8'))
    else:
        title = 'Message on {} from {}'.format(get_buf_name(bufferp), prefix.decode('utf-8'))

    send_push(title=title, message=message.decode('utf-8'))

    global last_notification
    last_notification = time.time()

    return w.WEECHAT_RC_OK


def http_request_callback(data, url, status, response, err):
    j = json.loads(response)
    if j['status'] != '1':
        w.prnt('', '[weepushover] error: {}'.format(response))
        return w.WEECHAT_RC_ERROR

    return w.WEECHAT_RC_OK


def send_push(title, message):
    postfields = {
        'token': w.config_get_plugin('token'),
        'user': w.config_get_plugin('user'),
        'title': title,
        'message': message,
        'url': 'https://glowing-bear.org',
    }

    w.hook_process_hashtable(
        'url:https://api.pushover.net/1/messages.json',
        {'postfields': urllib.urlencode(postfields)},
        20*1000,
        'http_request_callback',
        '',
    )


def main():
    register()
    load_settings()
    setup_hooks()


main()
