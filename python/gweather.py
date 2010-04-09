# -*- coding: utf-8 -*-
# Copyright (c) 2010 by Jani Kesänen <jani.kesanen@gmail.com>
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

#
# Google Weather to bar item
# (This script requires WeeChat 0.3.0.)
#
# Usage: Add "gweather" to weechat.bar.status.items or other bar you like.
#        Specify city: "/set plugins.var.python.gweather.city Tokyo".
#
# History:
# 2010-04-07, jkesanen <jani.kesanen@gmail.com>
#   version 0.2: - fetch weather using non-blocking hook_process interface
# 2010-04-06, jkesanen <jani.kesanen@gmail.com>
#   version 0.1: - initial release.
#

import weechat

from urllib import quote
from xml.dom import minidom
from time import time
from sys import version_info

SCRIPT_NAME    = "gweather"
SCRIPT_AUTHOR  = "Jani Kesänen <jani.kesanen@gmail.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with current Google weather"

# Script options
settings = {
    # City to monitor (ex. "Tokyo", "Austin, Texas", ...)
    'city'              : '',
    # Temperature units (C or F)
    'unit'              : 'C',
    # Update interval in minutes
    'interval'          : '10',
    # Timeout in seconds for fetching weather data
    'timeout'           : '10',
    # Visual settings
    'city_color'        : 'default',
    'condition_color'   : 'white',
    'display_city'      : 'on',
    'display_condition' : 'on',
}

# Timestamp for the last update
last_run = 0

# Which city's conditions were fetched the last
last_city = ''

# Cached copy of the last successful output
gweather_output = 'WAIT'

gweather_hook_process = ''
gweather_stdout = ''

# The url to Google's "unofficial" weather API
GOOGLE_WEATHER_URL = 'http://www.google.com/ig/api?weather=%s&hl=%s'

def parse_google_weather(xml_response):
    '''
    Parses weather report from Google

    This uses code from python-weather-api 0.2.2 by Eugene Kaznacheev <qetzal@gmail.com>.

    Returns:
      weather_data: a dictionary of weather data that exists in XML feed.
    '''
    try:
        dom = minidom.parseString(xml_response)
        weather_data = {}
        weather_dom = dom.getElementsByTagName('weather')[0]
    except:
        return

    data_structure = {
        'forecast_information': ('city', 'postal_code', 'latitude_e6', 'longitude_e6', 'forecast_date', 'current_date_time', 'unit_system'),
        'current_conditions': ('condition','temp_f', 'temp_c', 'humidity', 'wind_condition', 'icon')
    }

    for (tag, list_of_tags2) in data_structure.iteritems():
        tmp_conditions = {}
        for tag2 in list_of_tags2:
            try:
                tmp_conditions[tag2] = weather_dom.getElementsByTagName(tag)[0].getElementsByTagName(tag2)[0].getAttribute('data')
            except IndexError:
                pass
        weather_data[tag] = tmp_conditions

    dom.unlink()

    return weather_data


def format_weather(weather_data):
    '''
    Formats the weather data dictionary received from Google

    Returns:
      output: a string of formatted weather data.
    '''
    output = ''

    if weechat.config_get_plugin('display_city') == 'on':
        output = '%s%s: ' % (\
                 weechat.color(weechat.config_get_plugin('city_color')),
                 weechat.config_get_plugin('city'))

    if weather_data:
        if len(weather_data['current_conditions']):
            if weechat.config_get_plugin('unit') == 'F':
                weather = '%sF' % (weather_data['current_conditions']['temp_f'])
            else:
                weather = '%sC' % (weather_data['current_conditions']['temp_c'])

            if weechat.config_get_plugin('display_condition') == 'on' and \
                   weather_data['current_conditions']['condition']:
                weather += ', %s' % (weather_data['current_conditions']['condition'])
        else:
            weather = 'N/A'
    else:
        weather = 'N/A'

    output += '%s%s' % (\
             weechat.color(weechat.config_get_plugin('condition_color')),
             str(weather))

    output += weechat.color('reset')

    return output


def gweather_data_cb(data, command, rc, stdout, stderr):
    '''
    Callback for the data fetching process.
    '''
    global last_city, last_run, gweather_output
    global gweather_hook_process, gweather_stdout

    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR or stderr != '':
        weechat.prnt('', '%sgweather: Weather information fetching failed: %s' % (\
            weechat.prefix("error"), stderr))
        return weechat.WEECHAT_RC_ERROR

    if stdout:
        gweather_stdout += stdout

    if int(rc) < 0:
        # Process not ready
        return weechat.WEECHAT_RC_OK

    gweather_hook_process = ''
    last_run = time()
    last_city = weechat.config_get_plugin('city')

    if not gweather_stdout:
        return weechat.WEECHAT_RC_OK

    try:
        # The first row should contain "content-type" from HTTP header
        content_type, xml_response = gweather_stdout.split('\n', 1)
    except:
        # Failed to split received data in two at carridge return
        weechat.prnt('', '%sgweather: Invalid data received' % (weechat.prefix("error")))
        gweather_stdout = ''
        return weechat.WEECHAT_RC_ERROR

    gweather_stdout = ''

    # Determine the used character set in the response
    try:
        charset = content_type.split('charset=')[1]
    except:
        charset = 'utf-8'

    if charset.lower() != 'utf-8':
        xml_response = xml_response.decode(charset).encode('utf-8')

    # Feed the respose to parser and parsed data to formatting
    weather_data = parse_google_weather(xml_response)
    gweather_output = format_weather(weather_data)

    # Request bar item to update to the latest "gweather_output" 
    weechat.bar_item_update('gweather')

    return weechat.WEECHAT_RC_OK


def gweather_cb(*kwargs):
    ''' Callback for the Google weather bar item. '''
    global last_run, gweather_output, last_city, gweather_hook_process

    # Nag if user has not specified the city
    if not weechat.config_get_plugin('city'):
        return 'SET CITY'

    # Use cached copy if it is updated recently enough
    if weechat.config_get_plugin('city') == last_city and \
       (time() - last_run) < (int(weechat.config_get_plugin('interval')) * 60):
        return gweather_output

    location_id, hl = map(quote, (weechat.config_get_plugin('city'), 'en'))
    url = GOOGLE_WEATHER_URL % (location_id, hl)

    command = 'urllib2.urlopen(\'%s\')' % (url)

    if gweather_hook_process != "":
        weechat.unhook(gweather_hook_process)
        gweather_hook_process = ''

    # Fire up the weather informationg fetching
    gweather_hook_process = weechat.hook_process(\
        "python -c \"import urllib2;\
                     handler = " + command + ";\
                     print handler.info().dict['content-type'];\
                     print handler.read();\
                     handler.close();\"",
        int(weechat.config_get_plugin('timeout')) * 1000, "gweather_data_cb", "")

    # The old cached string is returned here. gweather_data_cb() will 
    # request a new update after the data is fetched and parsed.
    return gweather_output


def gweather_update(*kwargs):
    weechat.bar_item_update('gweather')

    return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):
    for option, default_value in settings.iteritems():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    weechat.bar_item_new('gweather', 'gweather_cb', '')
    weechat.hook_timer(int(weechat.config_get_plugin('interval')) * 1000 * 60,
            0, 0, 'gweather_update', '')
