# Author: Josh Dick <josh@joshdick.net>
# <https://github.com/joshdick/weeprowl>
#
# Requires weechat version 0.3.0 or greater
# Released under GNU GPL v2
#
# Based on the 'notify' plugin version 0.0.5 by lavaramano <lavaramano AT gmail DOT com>:
# <http://www.weechat.org/scripts/source/stable/notify.py.html/>
#
# 2012-09-16, Josh Dick <josh@joshdick.net>
#     Version 0.3: Removed 'smart_notification' and away_notification' settings
#                  in favor of more granular notification settings
# 2012-09-16, Josh Dick <josh@joshdick.net>
#     Version 0.2: Added 'away_notification' setting
# 2012-03-25, Josh Dick <josh@joshdick.net>
#     Version 0.1: Initial release

import httplib, urllib, weechat

weechat.register('weeprowl', 'Josh Dick', '0.3', 'GPL', 'Prowl notifications for weechat', '', '')

# Plugin settings
settings = {
    'prowl_api_key': '',
    'show_hilights': 'on',
    'show_priv_msg': 'on',
    'nick_separator': ': ',
    'notify_focused_active': 'on', # If 'on', send Prowl notifications for the currently-focused buffer when not away
    'notify_focused_away': 'on', # If 'on', send Prowl notifications for the currently-focused buffer when away
    'notify_unfocused_active': 'on', # If 'on', send Prowl notifications for non-focused buffers when not away
    'notify_unfocused_away': 'on' # If 'on', send Prowl notifications for non-focused buffers when away
}

# Hook for private messages/hilights
weechat.hook_print('', 'irc_privmsg', '', 1, 'notification_callback', '')

# Shows an error/help message if prowl_api_key is not set
def show_config_help():
    weechat.prnt('', '%sweeprowl - Error: Your Prowl API key is not set!' % weechat.prefix('error'))
    weechat.prnt('', '%sweeprowl - To obtain a Prowl API key, visit <http://prowlapp.com>.' % weechat.prefix('error'))
    weechat.prnt('', '%sweeprowl - Once you have a Prowl API key, configure weeprowl to use it by running:' % weechat.prefix('error'))
    weechat.prnt('', '%sweeprowl - /set plugins.var.python.weeprowl.prowl_api_key "your_prowl_api_key_here"' % weechat.prefix('error'))

# Triggered by the weechat hook above
def notification_callback(data, bufferp, uber_empty, tagsn, isdisplayed, ishilight, prefix, message):

    is_away = weechat.buffer_get_string(bufferp, "localvar_away")
    is_focused = bufferp == weechat.current_buffer()
    do_prowl = True # If set to False depending on state and settings, no Prowl notification will be sent

    if (is_away):
        if (is_focused and weechat.config_get_plugin('notify_focused_away') != 'on'):
            do_prowl = False
        elif (not is_focused and weechat.config_get_plugin('notify_unfocused_away') != 'on'):
            do_prowl = False
    else:
        if (is_focused and weechat.config_get_plugin('notify_focused_active') != 'on'):
            do_prowl = False
        elif (not is_focused and weechat.config_get_plugin('notify_unfocused_active') != 'on'):
            do_prowl = False

    if (do_prowl):
        if (weechat.buffer_get_string(bufferp, 'localvar_type') == 'private' and weechat.config_get_plugin('show_priv_msg') == 'on'):
            send_prowl_notification(prefix, message, True)
        elif (ishilight == '1' and weechat.config_get_plugin('show_hilights') == 'on'):
            buffer = (weechat.buffer_get_string(bufferp, 'short_name') or weechat.buffer_get_string(bufferp, 'name'))
            send_prowl_notification(buffer, prefix + weechat.config_get_plugin('nick_separator') + message, False)

    return weechat.WEECHAT_RC_OK

# Send a Prowl notification via the Prowl API (API documentation: <http://www.prowlapp.com/api.php>)
def send_prowl_notification(chan, message, isPrivate):

    # Error checking - we need a valid prowl API key to be set in order to send a Prowl notification
    prowl_api_key = weechat.config_get_plugin('prowl_api_key')
    if (prowl_api_key == ''):
        show_config_help()
        weechat.prnt('', '%sweeprowl - Could not send Prowl notification.' % weechat.prefix('error'))
        return

    # Build the Prowl API request
    params = urllib.urlencode({
        'apikey': prowl_api_key,
        'application': 'weechat',
        'event': 'IRC ' + 'Private Message' if isPrivate else 'Mention/Hilight',
        'description': 'Channel: ' + chan + '\n' + message
    })

    # Make the Prowl API request
    conn = httplib.HTTPSConnection('api.prowlapp.com')
    conn.request('POST', '/publicapi/add?' + params)

    # Error checking - make sure the Prowl API request was successful
    response = conn.getresponse()

    if (response.status != 200):
        weechat.prnt('', '%sweeprowl - Error: There was a problem communicating with the Prowl API!' % weechat.prefix('error'))
        weechat.prnt('', '%sweeprowl - Prowl API response information:' % weechat.prefix('error'))
        weechat.prnt('', '%sweeprowl -     Response status code = %s' % (weechat.prefix('error'), response.status))
        weechat.prnt('', '%sweeprowl -     Response reason phrase = %s' % (weechat.prefix('error'), response.reason))
        weechat.prnt('', '%sweeprowl - Could not send Prowl notification.' % weechat.prefix('error'))

    conn.close()

# Initialization
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == '':
        weechat.config_set_plugin(option, default_value)

if (weechat.config_get_plugin('prowl_api_key') == ''):
    show_config_help()

# vim: autoindent expandtab smarttab shiftwidth=4
