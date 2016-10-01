#!/usr/bin/python
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2014-2016 by deflax <daniel@deflax.net>
# Copyright (c) 2015 Christopher Stewart
# Copyright (c) 2016 by esch
#
#       Weechat WeatherBot using WUnderground API
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

SCRIPT_NAME    = "weatherbot"
SCRIPT_AUTHOR  = "deflax <daniel@deflax.net>"
SCRIPT_VERSION = "0.9"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "WeatherBot using the WeatherUnderground API"

try:
    import weechat as w, json, datetime
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

helptext = """
Get your own API key from http://www.wunderground.com/weather/api/
and act as weatherbot :)

\o/ hugs to all friends from #clanchill@quakenet and initlab.org \o/
"""
default_options = {"enabled": "on",
                   "units": "metric",
                   "weather_trigger": "!weather",
                   "forecast_trigger": "!forecast",
                   "apikey": "0000000000000"}

plugin_config = "plugins.var.python.{}".format(SCRIPT_NAME)

def weebuffer(reaction):
    rtnbuf = "{},{}".format(kserver, kchannel)
    buffer = w.info_get("irc_buffer", rtnbuf)
    botnick = w.info_get("irc_nick", kserver)
    if kchannel == botnick:
        #priate
        command = "msg {} {}".format(knick, reaction)
    else:
        #channel
        command = "msg {} {}".format(kchannel, reaction)

    #w.prnt("", command)
    cmdprefix = "/"
    w.command(buffer, cmdprefix + command)


def wu_autoc(data, command, return_code, out, err):
    """ weather underground auto search """
    global jname
    if return_code == w.WEECHAT_HOOK_PROCESS_ERROR:
        w.prnt("", "Error with command `%s'" % command)
        return w.WEECHAT_RC_OK
    if return_code > 0:
        w.prnt("", "return_code = %d" % return_code)
    if err != "":
        w.prnt("", "stderr: %s" % err)
    if out != "":
        i = json.loads(out)
        try:
            loc = next((l for l in i["RESULTS"] if l["type"] == "city"), None)
            if loc is None:
                weebuffer("Unable to locate query.")
                return w.WEECHAT_RC_OK
        except:
            weebuffer("Invalid query. Try again.")
            return w.WEECHAT_RC_OK

        jname = loc["name"]
        location = loc["l"]
        prefix = "[weatherbot] mode:"
        if mode == "conditions":
            cond_url = "url:http://api.wunderground.com/api/{}/conditions{}.json".format(options["apikey"], location)
            w.prnt("", '{} {} {}'.format(prefix, mode, location))
            w.hook_process(cond_url, 30 * 1000, "wu_cond", "")

        if mode == "forecast":
            fore_url = "url:http://api.wunderground.com/api/{}/forecast{}.json".format(options["apikey"], location)
            w.prnt("", '{} {} {}'.format(prefix, mode, location))
            w.hook_process(fore_url, 30 * 1000, "wu_fore", "")

    return w.WEECHAT_RC_OK


def wu_fore(data, command, return_code, out, err):
    """ wu forecast """
    if return_code == w.WEECHAT_HOOK_PROCESS_ERROR:
        w.prnt("", "Error with command '%s'" % command)
        return w.WEECHAT_RC_OK
    if return_code > 0:
        w.prnt("", "return_code = %d" % return_code)
    if err != "":
        w.prnt("", "stderr: %s" % err)
    if out != "":
        j = json.loads(out)
        try:
            error_type = j["response"]["error"]["type"]
            if error_type == "invalidquery":
                weebuffer("Error. Try again.")
                return w.WEECHAT_RC_OK
            elif error_type == "keynotfound":
                weebuffer("Invalid API key.")
                return w.WEECHAT_RC_OK
        except KeyError:
            pass

	if options["units"] == "metric":
            fcttext = 'fcttext_metric'
        else:
            fcttext = 'fcttext'

	#hour_string = j['forecast']['txt_forecast']['date']
	#hour_stripped = hour_string.rpartition(" ")[0]
        now = datetime.datetime.now()
        strhour = now.strftime('%H')
        hour = int(strhour)

        reaction = '[{}] [*'.format(jname)

        #if earlier than 1600 show forecast for today and tonight
        if hour < 16:
            reaction += j['forecast']['txt_forecast']['forecastday'][0]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][0][fcttext] + ' [*'
            reaction += j['forecast']['txt_forecast']['forecastday'][1]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][1][fcttext]
        #between 1600 and 2100 show forecast for tonight and tomorrow
        elif 16 <= hour <= 21:
            reaction += j['forecast']['txt_forecast']['forecastday'][1]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][1][fcttext] + ' [*'
            reaction += j['forecast']['txt_forecast']['forecastday'][2]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][2][fcttext]

        #after 2100 show forecast for tomorrow and tomorrow night
        elif hour > 21:
            reaction += j['forecast']['txt_forecast']['forecastday'][2]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][2][fcttext] + ' [*'
            reaction += j['forecast']['txt_forecast']['forecastday'][3]['title'] + '*]: '
            reaction += j['forecast']['txt_forecast']['forecastday'][3][fcttext]
        weebuffer(reaction)

    return w.WEECHAT_RC_OK


def wu_cond(data, command, return_code, out, err):
    """ wu condition """
    if return_code == w.WEECHAT_HOOK_PROCESS_ERROR:
        w.prnt("", "Error with command '%s'" % command)
        return w.WEECHAT_RC_OK
    if return_code > 0:
        w.prnt("", "return_code = %d" % return_code)
    if err != "":
        w.prnt("", "stderr: %s" % err)
    if out != "":
        j = json.loads(out)
        try:
            error_type = j["response"]["error"]["type"]
            if error_type == "invalidquery":
                weebuffer("Error. Try again.")
                return w.WEECHAT_RC_OK
            elif error_type == "keynotfound":
                weebuffer("Invalid API key.")
                return w.WEECHAT_RC_OK
        except KeyError:
            pass

        co = j["current_observation"]
        reaction = "[{}] {}. Temp is ".format(jname, co["weather"])

        if options["units"] == "metric":
            temp_unit = "C"
            wind_unit = "kph"
        else:
            temp_unit = "F"
            wind_unit = "mph"

        temp = co["temp_{}".format(temp_unit.lower())]
        like = co["feelslike_{}".format(temp_unit.lower())]
        if abs(int(float(temp)) - int(float(like))) > 2:
            reaction += "{0}°{1} but feels like {2}°{1}.".format(temp, temp_unit, like)
        else:
            reaction += "{}°{}.".format(temp, temp_unit)

        wind_speed = co["wind_{}".format(wind_unit)]
        if wind_speed > 0:
            reaction += " {} wind: {} {}.".format(co["wind_dir"], wind_speed, wind_unit)

        humid = co["relative_humidity"]
        if int(humid[:-1]) > 50:
            reaction += " Humidity: {}.".format(co["relative_humidity"])

        weebuffer(reaction)
    return w.WEECHAT_RC_OK


def triggerwatch(data, buffer, args):
    global kserver, kchannel, knick, mode
    if options["enabled"] == "on":
        try:
            null, srvmsg = args.split(" PRIVMSG ", 1)
        except:
            return w.WEECHAT_RC_OK

        try:
            kchannel, query = srvmsg.split(" :{} ".format(options["weather_trigger"]), 1)
            mode = "conditions"
        except ValueError:
            try:
                kchannel, query = srvmsg.split(" :{} ".format(options["forecast_trigger"]), 1)
                mode = "forecast"
            except ValueError:
                return w.WEECHAT_RC_OK

        kserver = str(buffer.split(",", 1)[0])
        knick = w.info_get("irc_nick_from_host", args)
        query = query.replace(" ", "%20")

        autoc_url = "url:http://autocomplete.wunderground.com/aq?query={}&format=JSON".format(query)
        w.hook_process(autoc_url, 30 * 1000, "wu_autoc", "")

    return w.WEECHAT_RC_OK


def config_cb(data, option, value):
    """Callback called when a script option is changed."""
    opt = option.split(".")[-1]
    options[opt] = value
    return w.WEECHAT_RC_OK


def get_option(option):
    """Returns value of w.option."""
    return w.config_string(w.config_get("{}.{}".format(plugin_config, option)))


if __name__ == "__main__" and import_ok:
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        #set options
        for option,value in default_options.items():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, value)

        options = {"enabled": get_option("enabled"),
            "units": get_option("units"),
            "weather_trigger": get_option("weather_trigger"),
            "forecast_trigger": get_option("forecast_trigger"),
            "apikey": get_option("apikey")
        }

        if options["apikey"] == "0000000000000":
            w.prnt("", "Your API key is not set. Please sign up at www.wunderground.com/weather/api and set plugins.var.python.weatherbot.*")

        #start
        w.hook_signal("*,irc_in_privmsg", "triggerwatch", "data")
        w.hook_config("{}.*".format(plugin_config), "config_cb", "")
