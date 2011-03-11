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
#        Formatting: "/set plugins.var.python.gweather.format %C: %D°%U, %O".
#            Where: %C - city
#                   %D - temperature degrees
#                   %U - temperature unit
#                   %O - current condition
#
# History:
# 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>:
#   version 0.4: get python 2.x binary for hook_process (fix problem when
#                python 3.x is default python version)
# 2010-04-15, jkesanen <jani.kesanen@gmail.com>
#   version 0.3: - added output formatting
#                - removed output and city color related options
# 2010-04-09, jkesanen <jani.kesanen@gmail.com>
#   version 0.2.1: - added support for different languages
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
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with current Google weather"

# Script options
settings = {
    # City to monitor (ex. "Tokyo", "Austin, Texas", ...)
    'city'           : '',
    # Language of the conditions (ex. en, ja, fi, fr, ...)
    'language'       : 'en',
    # Temperature units (C or F)
    'unit'           : 'C',
    # Update interval in minutes
    'interval'       : '10',
    # Timeout in seconds for fetching weather data
    'timeout'        : '10',
    # The color of the output
    'output_color'   : 'white',
    # Formatting (%C = city, %D = degrees, %U = unit, %O = condition)
    'format'         : '%C: %D%U, %O',
}

# Timestamp for the last update
last_run = 0

# The last city, language and format for the need of refresh
last_city = ''
last_lang = ''
last_format = ''

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
                tmp_conditions[tag2] = weather_dom.getElementsByTagName(tag)[0].getElementsByTagName(tag2)[0].getAttribute('data').strip()
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
    output = weechat.color(weechat.config_get_plugin('output_color')) + weechat.config_get_plugin('format')
    output = output.replace('%C', weechat.config_get_plugin('city'))

    temp = 'N/A'
    condition = 'N/A'

    if weather_data:
        if len(weather_data['current_conditions']):
            if weechat.config_get_plugin('unit') == 'F':
                temp = weather_data['current_conditions']['temp_f'].encode('utf-8')
            else:
                temp = weather_data['current_conditions']['temp_c'].encode('utf-8')

            if weather_data['current_conditions'].has_key('condition'):
                condition = weather_data['current_conditions']['condition'].encode('utf-8')

    output = output.replace('%D', temp)
    output = output.replace('%O', condition)
    output = output.replace('%U', weechat.config_get_plugin('unit'))

    output += weechat.color('reset')

    return output


def gweather_data_cb(data, command, rc, stdout, stderr):
    '''
    Callback for the data fetching process.
    '''
    global last_city, last_lang, last_run, last_format
    global gweather_hook_process, gweather_stdout, gweather_output

    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR or stderr != '':
        weechat.prnt('', '%sgweather: Weather information fetching failed: %s' % (\
            weechat.prefix("error"), stderr))
        return weechat.WEECHAT_RC_ERROR

    if stdout:
        gweather_stdout += stdout

    if int(rc) < 0:
        # Process not ready
        return weechat.WEECHAT_RC_OK

    # Update status variables for succesful run
    last_run = time()
    last_city = weechat.config_get_plugin('city')
    last_lang = weechat.config_get_plugin('language')
    last_format = weechat.config_get_plugin('format')
    gweather_hook_process = ''

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
    global last_run, last_city, last_lang, last_format
    global gweather_output, gweather_hook_process

    # Nag if user has not specified the city
    if not weechat.config_get_plugin('city'):
        return 'SET CITY'

    # Nag if user has not specified the language
    if not weechat.config_get_plugin('language'):
        return 'SET LANGUAGE'

    # Use cached copy if it is updated recently enough
    if weechat.config_get_plugin('city') == last_city and \
       weechat.config_get_plugin('language') == last_lang and \
       weechat.config_get_plugin('format') == last_format and \
       (time() - last_run) < (int(weechat.config_get_plugin('interval')) * 60):
        return gweather_output

    location_id, hl = map(quote, (weechat.config_get_plugin('city'), \
                                  weechat.config_get_plugin('language')))
    url = GOOGLE_WEATHER_URL % (location_id, hl)

    command = 'urllib2.urlopen(\'%s\')' % (url)

    if gweather_hook_process != "":
        weechat.unhook(gweather_hook_process)
        gweather_hook_process = ''

    # Fire up the weather informationg fetching
    python2_bin = weechat.info_get("python2_bin", "") or "python"
    gweather_hook_process = weechat.hook_process(\
        python2_bin + " -c \"import urllib2;\
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
    weechat.bar_item_update('gweather')
    weechat.hook_timer(int(weechat.config_get_plugin('interval')) * 1000 * 60,
            0, 0, 'gweather_update', '')
