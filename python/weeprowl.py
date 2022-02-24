# -*- coding: utf-8 -*-
# Author: Josh Dick <josh@joshdick.net>
# <https://github.com/joshdick/weeprowl>
#
# Requires WeeChat version 0.3.7 or greater
# Released under GNU GPL v2
#
# Based on the 'notify' plugin version 0.0.5 by lavaramano <lavaramano AT gmail DOT com>:
# <http://www.weechat.org/scripts/source/stable/notify.py.html/>
#
# 2021-03-03, Johannes Rabenschlag <j.rabenschlag@gmail.com>
#     Version 0.8: Fixed urllib error
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#     Version 0.7: Change hook_print callback argument type of
#                  displayed/highlight (WeeChat >= 1.0)
# 2013-12-22, Josh Dick <josh@joshdick.net>
#     Version 0.6: Fixed bug that was preventing negative numbers from working with
#                  the prowl_priority setting
# 2013-12-20, Josh Dick <josh@joshdick.net>
#     Version 0.5: Now backgrounds Prowl API requests, added prowl_priority setting,
#                  now requires WeeChat version 0.3.7 or greater
# 2013-08-13, Josh Dick <josh@joshdick.net>
#     Version 0.4: No longer sending notifications for text you send in private messages
# 2012-09-16, Josh Dick <josh@joshdick.net>
#     Version 0.3: Removed 'smart_notification' and away_notification' settings
#                  in favor of more granular notification settings
# 2012-09-16, Josh Dick <josh@joshdick.net>
#     Version 0.2: Added 'away_notification' setting
# 2012-03-25, Josh Dick <josh@joshdick.net>
#     Version 0.1: Initial release

import urllib.parse, weechat

weechat.register('weeprowl', 'Josh Dick', '0.8', 'GPL', 'Prowl notifications for WeeChat', '', '')

# Plugin settings
settings = {
    'prowl_api_key': '',
    'prowl_priority': '0', # An integer value ranging [-2, 2] per http://www.prowlapp.com/api.php#add
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

# Shows an error when there was a problem sending a Prowl notification.
def show_notification_error():
    weechat.prnt('', '%sweeprowl - Could not send Prowl notification.' % weechat.prefix('error'))

# Triggered by the weechat hook above
def notification_callback(data, bufferp, uber_empty, tagsn, isdisplayed, ishilight, prefix, message):

    is_away = weechat.buffer_get_string(bufferp, 'localvar_away')
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
        if (weechat.buffer_get_string(bufferp, 'localvar_type') == 'private' and weechat.config_get_plugin('show_priv_msg') == 'on' and prefix != weechat.buffer_get_string(bufferp, 'localvar_nick')):
            send_prowl_notification(prefix, message, True)
        elif (int(ishilight) and weechat.config_get_plugin('show_hilights') == 'on'):
            buffer = (weechat.buffer_get_string(bufferp, 'short_name') or weechat.buffer_get_string(bufferp, 'name'))
            send_prowl_notification(buffer, prefix + weechat.config_get_plugin('nick_separator') + message, False)

    return weechat.WEECHAT_RC_OK

# Send a Prowl notification via the Prowl API (API documentation: <http://www.prowlapp.com/api.php>)
def send_prowl_notification(chan, message, isPrivate):

    # Make sure a Prowl API key has been configured
    prowl_api_key = weechat.config_get_plugin('prowl_api_key')
    if (prowl_api_key == ''):
        show_config_help()
        show_notification_error()
        return

    # Make sure a valid Prowl priority has been configured
    prowl_priority = weechat.config_get_plugin('prowl_priority')
    valid_prowl_priority = True
    try:
        if (int(prowl_priority) > 2 or int(prowl_priority) < -2):
            valid_prowl_priority = False
    except ValueError:
            valid_prowl_priority = False
    if (not valid_prowl_priority):
        weechat.prnt('', '%sweeprowl - Current prowl_priority setting "%s" is invalid.' % (weechat.prefix('error'), prowl_priority))
        weechat.prnt('', '%sweeprowl - Please set prowl_priority to an integer value ranging from [-2, 2].' % weechat.prefix('error'))
        show_notification_error()
        return

    # Build the Prowl API request parameters
    params = urllib.parse.urlencode({
        'apikey': prowl_api_key,
        'application': 'weechat',
        'event': 'IRC ' + 'Private Message' if isPrivate else 'Mention/Hilight',
        'description': 'Channel: ' + chan + '\n' + message,
        'priority': prowl_priority
    })

    # Build the complete Prowl API request URL
    prowl_api_url = 'https://api.prowlapp.com/publicapi/add?' + params

    # Make the Prowl API request
    weechat.hook_process_hashtable(
        'url:' + prowl_api_url,
        { 'post': '1' },
        30 * 1000,
        'send_prowl_notification_callback',
        ''
    )

# Callback that handles the result of the Prowl API request
def send_prowl_notification_callback(data, command, rc, stdout, stderr):

    # Show an error if the Prowl API request failed
    if (rc > 0):
        weechat.prnt('', '%sweeprowl - Error: There was a problem communicating with the Prowl API!' % weechat.prefix('error'))
        weechat.prnt('', '%sweeprowl - Prowl API response information:' % weechat.prefix('error'))
        weechat.prnt('', '%sweeprowl -     Response code = %s' % (weechat.prefix('error'), rc))
        weechat.prnt('', '%sweeprowl -     STDOUT = %s' % (weechat.prefix('error'), stdout))
        weechat.prnt('', '%sweeprowl -     STDERR = %s' % (weechat.prefix('error'), stderr))
        show_notification_error()

    return weechat.WEECHAT_RC_OK

# Initialization
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == '':
        weechat.config_set_plugin(option, default_value)

if (weechat.config_get_plugin('prowl_api_key') == ''):
    show_config_help()

# vim: autoindent expandtab smarttab shiftwidth=4

