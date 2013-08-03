# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Chmouel Boudjnah <chmouel@chmouel.com>
# Copyright (C) 2012-2013 bwidawsk <ben@bwidawsk.net>
# License: GPL3
#
# plugin to get alternate timezones in a weechat bar
#
# Changelog:
#  0.2 Added help, and multiple timezeones
#  0.1 first version
#

import weechat as w
import pytz
import datetime

SCRIPT_NAME    = "alternatetz"
SCRIPT_AUTHOR  = "Chmouel Boudjnah <chmouel@chmouel.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display Alternate Time from different Timezones"

SCRIPT_COMMAND = 'alternatetz'

OPTIONS		= {
'timezone'	: ('GMT', 'list of timezones to display. The list is comprised of space separated list timezones using the Olson tz database'),
'timeformat'	: ('%H:%M', 'strftime compatible format')
}

def alternatetz_item_cb(*kwargs):
    ret = ''
    tznames = OPTIONS['timezone'].split()
    for tzname in tznames:
        tz = pytz.timezone(tzname)
	ret += tz.zone + ': ' + datetime.datetime.now(tz).strftime(OPTIONS['timeformat']) + ' '
    return ret[:-1]

def alternatetz_timer_cb(*kwargs):
    w.bar_item_update('alternatetz')
    return w.WEECHAT_RC_OK

if __name__ == '__main__':
    w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')
    for option,value in list(OPTIONS.items()):
        w.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = w.config_get_plugin(option)

    w.bar_item_new('alternatetz', 'alternatetz_item_cb', '')
    w.bar_item_update('alternatetz')
    w.hook_timer(1000*60, 60, 0, 'alternatetz_timer_cb', '')

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
