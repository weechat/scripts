# -*- coding: utf-8 -*-
#
# Chmouel Boudjnah <chmouel@chmouel.com>
# License: GPL3
#
'''
Display Different time in buffer.
Just put [alternatetz] on your bar items to add it.
'''
import weechat as w
import pytz
import datetime

SCRIPT_NAME    = "alternatetz"
SCRIPT_AUTHOR  = "Chmouel Boudjnah <chmouel@chmouel.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display Alternate Time from different TimeZone"

# script options
settings = {
    "timezone"       : 'US/Central',
    "timeformat"     : "%H:%M",
}

def alternatetz_item_cb(*kwargs):
    tzname = w.config_get_plugin('timezone')
    tz = pytz.timezone(tzname)
    return datetime.datetime.now(tz).strftime(w.config_get_plugin('timeformat'))

def alternatetz_timer_cb(*kwargs):
    w.bar_item_update('alternatetz')
    return w.WEECHAT_RC_OK
    
if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, '', ''):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.bar_item_new('alternatetz', 'alternatetz_item_cb', '')
    w.bar_item_update('alternatetz')
    w.hook_timer(1000*60, 60, 0, 'alternatetz_timer_cb', '')
