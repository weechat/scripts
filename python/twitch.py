# -*- coding: utf-8 -*-

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
# This script checks stream status of any channel on any servers
# listed in the "plugins.var.python.twitch.servers" setting. When you
# switch to a buffer it will display updated infomation about the stream
# in the title bar. Typing '/twitch' in buffer will also fetch updated
# infomation. '/whois nick' will lookup user info and display it in current
# buffer.
#
# https://github.com/mumixam/weechat-twitch
#
# settings:
# plugins.var.python.twitch.servers (default: twitch)
# plugins.var.python.twitch.prefix_nicks (default: 1)
# plugins.var.python.twitch.debug (default: 0)
# plugins.var.python.twitch.ssl_verify (default: 1)
#
# # History:
#
# 2018-06-03, mumixam
#     v0.5: enable curl verbose mode when debug is active, add option to disable ssl/tls verification,
#           if stream title contains newline char replace it with space
# 2017-11-02, mumixam
#     v0.4: added debug mode for API calls, minor bugfixes
# 2017-06-10, mumixam
#     v0.3: fixed whois output of utf8 display names
# 2016-11-03, mumixam
#     v0.2: added detailed /help
# 2016-10-30, mumixam
#     v0.1: script added to weechat.org



SCRIPT_NAME = "twitch"
SCRIPT_AUTHOR = "mumixam"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "twitch.tv Chat Integration"
OPTIONS={
    'servers': ('twitch','Name of server(s) which script will be active on, space seperated'),
    'prefix_nicks': ('1','Prefix nicks based on ircv3 tags for mods/subs, This can be cpu intensive on very active chats [1 for enabled, 0 for disabled]'),
    'debug': ('0','Debug mode'),
    'ssl_verify': ('1', 'Verify SSL/TLS certs')
}


import weechat
import json
from calendar import timegm
from datetime import datetime, timedelta
import time
import string
import ast

clientid='awtv6n371jb7uayyc4jaljochyjbfxs'
params = '?client_id='+clientid
curlopt = {
    "timeout": "5",
    "verbose": "0",
    "ssl_verifypeer": "1",
    "ssl_verifyhost": "2"
}

def days_hours_minutes(td):
    age = ''
    hours = td.seconds // 3600
    min = td.seconds // 60 % 60
    if not td.days == 0:
        age += str(td.days) + 'd '
    if not hours == 0:
        age += str(hours) + 'h '
    if not min == 0:
        age += str(min) + 'm'
    return age.strip()


def twitch_main(data, buffer, args):
    if not args == 'bs':
        weechat.buffer_set(buffer, 'localvar_set_tstatus', '')
    username = weechat.buffer_get_string(buffer, 'short_name').replace('#', '')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    type = weechat.buffer_get_string(buffer, 'localvar_type')
    if not (server in OPTIONS['servers'].split() and type == 'channel'):
        return weechat.WEECHAT_RC_OK
    url = 'https://api.twitch.tv/kraken/streams/' + username
    weechat.hook_process_hashtable(
        "url:" + url+params, curlopt, 7 * 1000, "stream_api", buffer)
    return weechat.WEECHAT_RC_OK


gamelist = [
    "Counter-Strike: Global Offensive;CSGO",
    "World of Warcraft: Warlords of Draenor;WOW",
    "Hearthstone: Heroes of Warcraft;Hearthstone",
    "H1Z1: King of the Kill;H1Z1 KotK",
    "Tom Clancy\'s The Division;The Division"
]


def gameshort(game):
    for games in gamelist:
        gamelong = games.split(';')[0]
        if gamelong.lower() == game.lower():
            return('<' + games.split(';')[-1] + '>')
    return '<' + game + '>'

def makeutf8(data):
    data = data.encode('utf8')
    if not isinstance(data, str):
        data=str(data,'utf8')
    return data

def channel_api(data, command, rc, stdout, stderr):
    data = ast.literal_eval(data)
    try:
        jsonDict = json.loads(stdout.strip())
    except Exception as e:
        weechat.prnt(data['buffer'], '%stwitch.py: error communicating with twitch api' % weechat.prefix('error'))
        if OPTIONS['debug']:
            weechat.prnt(data['buffer'],'%stwitch.py: return code: %s' % (weechat.prefix('error'),rc))
            weechat.prnt(data['buffer'],'%stwitch.py: stdout: %s' % (weechat.prefix('error'),stdout))
            weechat.prnt(data['buffer'],'%stwitch.py: stderr: %s' % (weechat.prefix('error'),stderr))
            weechat.prnt(data['buffer'],'%stwitch.py: exception: %s' % (weechat.prefix('error'),e))
        return weechat.WEECHAT_RC_OK
    currentbuf = weechat.current_buffer()
    name = data['name']
    pcolor = weechat.color('chat_prefix_network')
    ccolor = weechat.color('chat')
    dcolor = weechat.color('chat_delimiters')
    ncolor = weechat.color('chat_nick')
    ul = weechat.color("underline")
    rul = weechat.color("-underline")
    pformat = weechat.config_string(
        weechat.config_get("weechat.look.prefix_network"))
    if len(jsonDict) == 22:
        dname = jsonDict['display_name']
        create = jsonDict['created_at'].split('T')[0]
        status = jsonDict['status']
        follows = jsonDict['followers']
        partner = str(jsonDict['partner'])
        output = '%s%s %s[%s%s%s]%s %sDisplay Name%s: %s' % (
                            pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, dname)
        output += '\n%s%s %s[%s%s%s]%s %sAccount Created%s: %s' % (
            pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, create)
        if status:
            output += '\n%s%s %s[%s%s%s]%s %sStatus%s: %s' % (
                pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, status)
        output += '\n%s%s %s[%s%s%s]%s %sPartnered%s: %s %sFollowers%s: %s' % (
            pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, partner, ul, rul, follows)
        weechat.prnt(data['buffer'], makeutf8(output))
        url = 'https://api.twitch.tv/kraken/users/' + \
            name.lower() + '/follows/channels'
        weechat.hook_process_hashtable(
            "url:" + url+params, curlopt, 7 * 1000, "channel_api", str({'buffer': currentbuf, 'name': name, 'dname': dname}))

    if len(jsonDict) == 18:
        dname = jsonDict['display_name']
        s64id = jsonDict['steam_id']
        if s64id:
            sid3 = int(s64id) - 76561197960265728
            highaid = "{0:b}".format(sid3).zfill(32)[:31]
            lowaid = "{0:b}".format(sid3).zfill(32)[31:]
            id32bit = "STEAM_0:%s:%s" % (lowaid, int(highaid, 2))

            output = '%s%s %s[%s%s%s]%s %ssteamID64%s: %s %ssteamID3%s: %s %ssteamID%s: %s' % (
                pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, s64id, ul, rul, sid3, ul, rul, id32bit)
            weechat.prnt(data['buffer'], makeutf8(output))

    if len(jsonDict) == 3:
        if 'status' in jsonDict.keys():
            if jsonDict['status'] == 404 or jsonDict['status'] == 422:
                user = jsonDict['message'].split()[1].replace("'", "")
                weechat.prnt(data['buffer'], '%s%s %s[%s%s%s]%s No such user' % (
                    pcolor, pformat, dcolor, ncolor, user, dcolor, ccolor))
        else:
            url = 'https://api.twitch.tv/api/channels/' + data['name'].lower()
            weechat.hook_process_hashtable(
                "url:" + url+params, curlopt, 7 * 1000, "channel_api", str({'buffer': currentbuf, 'name': name, 'dname': data['name']}))
            count = jsonDict['_total']
            if count:
                output = '%s%s %s[%s%s%s]%s %sFollowing%s: %s' % (
                    pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, count)
                weechat.prnt(data['buffer'], makeutf8(output))
    return weechat.WEECHAT_RC_OK


def stream_api(data, command, rc, stdout, stderr):
    try:
        jsonDict = json.loads(stdout.strip())
    except Exception as e:
        weechat.prnt(data, '%stwitch.py: error communicating with twitch api' % weechat.prefix('error'))
        if OPTIONS['debug']:
            weechat.prnt(data,'%stwitch.py: return code: %s' % (weechat.prefix('error'),rc))
            weechat.prnt(data,'%stwitch.py: stdout: %s' % (weechat.prefix('error'),stdout))
            weechat.prnt(data,'%stwitch.py: stderr: %s' % (weechat.prefix('error'),stderr))
            weechat.prnt(data,'%stwitch.py: exception: %s' % (weechat.prefix('error'),e))
        return weechat.WEECHAT_RC_OK
    currentbuf = weechat.current_buffer()
    title_fg = weechat.color(
        weechat.config_color(weechat.config_get("weechat.bar.title.color_fg")))
    title_bg = weechat.color(
        weechat.config_color(weechat.config_get("weechat.bar.title.color_bg")))
    pcolor = weechat.color('chat_prefix_network')
    ccolor = weechat.color('chat')
    red = weechat.color('red')
    blue = weechat.color('blue')
    green = weechat.color('green')
    ptime = time.strftime("%H:%M:%S")
    subs = weechat.buffer_get_string(data, 'localvar_subs')
    r9k = weechat.buffer_get_string(data, 'localvar_r9k')
    slow = weechat.buffer_get_string(data, 'localvar_slow')
    emote = weechat.buffer_get_string(data, 'localvar_emote')
    if 'status' in jsonDict.keys():
        if jsonDict['status'] == 422:
            weechat.prnt(data, 'ERROR: The community has closed this channel due to terms of service violations.')
        if jsonDict['status'] == 404:
            weechat.prnt(data, 'ERROR: The page could not be found, or has been deleted by its owner.')
        return weechat.WEECHAT_RC_OK
    if not 'stream' in jsonDict.keys():
        weechat.prnt(data, 'twitch.py: Error with twitch API (stream key missing from json)')
        return weechat.WEECHAT_RC_OK
    if not jsonDict['stream']:
        line = "STREAM: %sOFFLINE%s %sCHECKED AT: %s" % (
            red, title_fg, blue, ptime)
        if subs:
            line += " %s[SUBS]" % title_fg
        if r9k:
            line += " %s[R9K]" % title_fg
        if slow:
            line += " %s[SLOW@%s]" % (title_fg, slow)
        if emote:
            line += " %s[EMOTE]" % title_fg
        weechat.buffer_set(data, "title", line)
    else:
        currenttime = time.time()
        output = 'STREAM: %sLIVE%s' % (green, title_fg)
        if 'game' in jsonDict['stream']:
            if jsonDict['stream']['game']:
                game = gameshort(jsonDict['stream']['game'])
                output += ' %s with' % makeutf8(game)
        if 'viewers' in jsonDict['stream']:
            viewers = jsonDict['stream']['viewers']
            output += ' %s viewers started' % viewers
        if 'created_at' in jsonDict['stream']:
            createtime = jsonDict['stream']['created_at'].replace('Z', 'GMT')
            starttime = timegm(
                time.strptime(createtime, '%Y-%m-%dT%H:%M:%S%Z'))
            dur = timedelta(seconds=currenttime - starttime)
            uptime = days_hours_minutes(dur)
            output += ' %s ago' % uptime
        if 'channel' in jsonDict['stream']:
            if 'followers' in jsonDict['stream']['channel']:
                followers = jsonDict['stream']['channel']['followers']
                output += ' [%s followers]' % followers
            if 'status' in jsonDict['stream']['channel']:
                titleutf8=jsonDict['stream']['channel']['status'].replace('\n',' ').encode('utf8')
                titleascii=jsonDict['stream']['channel']['status'].encode('ascii','replace')
                if not isinstance(titleutf8, str):
                    titleascii=str(titleascii,'utf8')
                    titleutf8=str(titleutf8,'utf8')
                oldtitle = weechat.buffer_get_string(data, 'localvar_tstatus')
                if not oldtitle == titleascii:
                    weechat.prnt(data, '%s--%s Title is "%s"' %
                                 (pcolor, ccolor, titleutf8))
                    weechat.buffer_set(data, 'localvar_set_tstatus', titleascii)
            if 'updated_at' in jsonDict['stream']['channel']:
                updateat = jsonDict['stream']['channel'][
                    'updated_at'].replace('Z', 'GMT')
                updatetime = timegm(
                    time.strptime(updateat, '%Y-%m-%dT%H:%M:%S%Z'))
                udur = timedelta(seconds=currenttime - updatetime)
                titleage = days_hours_minutes(udur)

        output += ' %s' % ptime
        if subs:
            output += " %s[SUBS]" % title_fg
        if r9k:
            output += " %s[R9K]" % title_fg
        if slow:
            output += " %s[SLOW@%s]" % (title_fg, slow)
        if emote:
            output += " %s[EMOTE]" % title_fg
        weechat.buffer_set(data, "title", output)
    return weechat.WEECHAT_RC_OK


def twitch_clearchat(data, modifier, modifier_data, string):
    mp = weechat.info_get_hashtable(
    'irc_message_parse', {"message": string})
    server = modifier_data
    user = mp['text']
    channel = mp['channel']
    try:
        tags = dict([s.split('=') for s in mp['tags'].split(';')])
    except:
        tags = ''
    buffer = weechat.buffer_search("irc", "%s.%s" % (server, channel))
    if buffer:
        pcolor = weechat.color('chat_prefix_network')
        ccolor = weechat.color('chat')
        ul = weechat.color("underline")
        rul = weechat.color("-underline")
        if user:
            if 'ban-duration' in tags:
                if 'ban-reason' in tags and tags['ban-reason']:
                    bn=tags['ban-reason'].replace('\s',' ')
                    weechat.prnt(buffer,"%s--%s %s has been timed out for %s seconds %sReason%s: %s" %
                        (pcolor, ccolor, user, tags['ban-duration'], ul, rul, bn))
                else:
                    weechat.prnt(buffer,"%s--%s %s has been timed out for %s seconds" %
                        (pcolor, ccolor, user, tags['ban-duration']))
            elif 'ban-reason' in tags:
                if tags['ban-reason']:
                    bn=tags['ban-reason'].replace('\s',' ')
                    weechat.prnt(buffer,"%s--%s %s has been banned %sReason%s: %s" %
                        (pcolor, ccolor, user, ul, rul,bn))
                else:
                    weechat.prnt(buffer,"%s--%s %s has been banned" %
                        (pcolor, ccolor, user))
            else:
                weechat.prnt(
                    buffer, "%s--%s %s's Chat Cleared By Moderator" % (pcolor, ccolor, user))
        else:
            weechat.prnt(
                buffer, "%s--%s Entire Chat Cleared By Moderator" % (pcolor, ccolor))
    return ""


def twitch_suppress(data, modifier, modifier_data, string):
    return ""


def twitch_reconnect(data, modifier, modifier_data, string):
    server = modifier_data
    buffer = weechat.buffer_search("irc", "server.%s" % server)
    if buffer:
        pcolor = weechat.color('chat_prefix_network')
        ccolor = weechat.color('chat')
        weechat.prnt(
            buffer, "%s--%s Server sent reconnect request. Issuing /reconnect" % (pcolor, ccolor))
        weechat.command(buffer, "/reconnect")
    return ""


def twitch_buffer_switch(data, signal, signal_data):
    server = weechat.buffer_get_string(signal_data, 'localvar_server')
    type = weechat.buffer_get_string(signal_data, 'localvar_type')
    if not (server in OPTIONS['servers'].split() and type == 'channel'):
        return weechat.WEECHAT_RC_OK
    twitch_main('', signal_data, 'bs')
    return weechat.WEECHAT_RC_OK


def twitch_roomstate(data, modifier, server, string):
    message = weechat.info_get_hashtable(
        'irc_message_parse', {"message": string})
    buffer = weechat.buffer_search(
        "irc", "%s.%s" % (server, message['channel']))
    for tag in message['tags'].split(';'):
        if tag == 'subs-only=0':
            weechat.buffer_set(buffer, 'localvar_set_subs', '')
        if tag == 'subs-only=1':
            weechat.buffer_set(buffer, 'localvar_set_subs', '1')
        if tag == 'r9k=0':
            weechat.buffer_set(buffer, 'localvar_set_r9k', '')
        if tag == 'r9k=1':
            weechat.buffer_set(buffer, 'localvar_set_r9k', '1')
        if tag == 'emote-only=0':
            weechat.buffer_set(buffer, 'localvar_set_emote', '')
        if tag == 'emote-only=1':
            weechat.buffer_set(buffer, 'localvar_set_emote', '1')
        if tag.startswith('slow='):
            value = tag.split('=')[-1]
            if value == '0':
                weechat.buffer_set(buffer, 'localvar_set_slow', '')
            if value > '0':
                weechat.buffer_set(buffer, 'localvar_set_slow', value)
        twitch_main('', buffer, 'bs')
    return ''


def twitch_usernotice(data, modifier, server, string):
    pcolor = weechat.color('chat_prefix_network')
    ccolor = weechat.color('chat')
    mp = weechat.info_get_hashtable(
        'irc_message_parse', {"message": string})
    buffer = weechat.buffer_search(
        "irc", "%s.%s" % (server, mp['channel']))
    if mp['tags']:
        tags = dict([s.split('=') for s in mp['tags'].split(';')])
        msg = tags['system-msg'].replace('\s',' ')
        if mp['text']:
            msg += ' [Comment] '+mp['text']
        weechat.prnt(buffer, '%s--%s %s' % (pcolor, ccolor, msg))
    return ''


def twitch_whisper(data, modifier, modifier_data, string):
    message = weechat.info_get_hashtable(
        'irc_message_parse', {"message": string})
    if message['tags']: string = '@'+message['tags']+' '
    else: string = ''
    string += ':'+message['host']
    string += ' PRIVMSG'
    string += ' '+message['arguments']
    return string


def twitch_privmsg(data, modifier, server_name, string):
    if not server_name in OPTIONS['servers'].split():
        return string
    message = weechat.info_get_hashtable(
        'irc_message_parse', {"message": string})
    if message['channel'].startswith('#'):
        return string
    newmsg = 'PRIVMSG #%s :/w %s %s' % (message['nick'],message['nick'],message['text'])
    return newmsg


def twitch_in_privmsg(data, modifier, server_name, string, prefix=''):
    if not OPTIONS['prefix_nicks']: return string
    if not server_name in OPTIONS['servers'].split():
        return string

    mp = weechat.info_get_hashtable("irc_message_parse", {"message": string})

    if not mp['tags']:
        return string
    if '#' + mp['nick'] == mp['channel']:
        return mp['message_without_tags'].replace(mp['nick'], '~' + mp['nick'], 1)

    tags = dict([s.split('=') for s in mp['tags'].split(';')])
    if tags['user-type'] == 'mod':
        prefix += '@'
    if tags['subscriber'] == '1':
        prefix += '%'
    if prefix:
        msg = mp['message_without_tags'].replace(
            mp['nick'], prefix + mp['nick'], 1)
        return '@' + mp['tags'] + ' ' + msg
    else:
        return string


def twitch_whois(data, modifier, server_name, string):
    if not server_name in OPTIONS['servers'].split():
        return string
    msg = weechat.info_get_hashtable("irc_message_parse", {"message": string})
    username = msg['nick'].lower()
    currentbuf = weechat.current_buffer()
    url = 'https://api.twitch.tv/kraken/channels/' + username
    url_hook = weechat.hook_process_hashtable(
        "url:" + url+params, curlopt, 7 * 1000, "channel_api", str({'buffer': currentbuf, 'name': username}))
    return ""

def config_setup():
    for option,value in OPTIONS.items():
        weechat.config_set_desc_plugin(option, '%s' % value[1])
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            if option == 'prefix_nicks' or option == 'debug' or option == 'ssl_verify':
                OPTIONS[option] = weechat.config_string_to_boolean(
                    weechat.config_get_plugin(option))
                if option == 'debug':
                    if value == 0:
                        curlopt['verbose'] = "0"
                    else:
                        curlopt['verbose'] = "1"
                if option == 'ssl_verify':
                    if value == 0:
                        curlopt['ssl_verifypeer'] = "0"
                        curlopt['ssl_verifyhost'] = "0"
                    else:
                        curlopt['ssl_verifypeer'] = "1"
                        curlopt['ssl_verifyhost'] = "2"
            else:
                OPTIONS[option] = weechat.config_get_plugin(option)

def config_change(pointer, name, value):
    option = name.replace('plugins.var.python.'+SCRIPT_NAME+'.','')
    if option == 'prefix_nicks' or option == 'debug' or option == 'ssl_verify':
        value=weechat.config_string_to_boolean(value)
        if option == 'debug':
            if value == 0:
                curlopt['verbose'] = "0"
            if value == 1:
                curlopt['verbose'] = "1"
        if option == 'ssl_verify':
            if value == 0:
                curlopt['ssl_verifypeer'] = "0"
                curlopt['ssl_verifyhost'] = "0"
            if value == 1:
                curlopt['ssl_verifypeer'] = "1"
                curlopt['ssl_verifyhost'] = "2"
    OPTIONS[option] = value
    return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command("twitch", SCRIPT_DESC, "",
        "  settings:\n"
        "    plugins.var.python.twitch.servers (default: twitch)\n"
        "    plugins.var.python.twitch.prefix_nicks (default: 1)\n"
        "    plugins.var.python.twitch.debug (default: 0)\n"
        "    plugins.var.python.twitch.ssl_verify (default: 0)\n"
        "\n\n"
        "  This script checks stream status of any channel on any servers listed\n"
        "  in the \"plugins.var.python.twitch.servers\" setting. When you switch\n"
        "  to a buffer it will display updated infomation about the stream in the\n"
        "  title bar. Typing '/twitch' in a buffer will also fetch updated infomation.\n"
        "  '/whois nick' will lookup user info and display it in current buffer.\n\n"
        "  Option \"plugins.var.python.twitch.servers\" controls\n"
        "  what server this script will work on. The default is twitch\n"
        "  but you can have multiples separated by a space.\n"
        "  /set plugins.var.python.twitch.servers twitch twitchcopy\n"
        "\n\n"
        "  This script also will prefix users nicks (@ for mod, % for sub,\n"
        "  and ~ for broadcaster). This will break the traditional function\n"
        "  of `/ignore add nightbot` and will require you to prefix nicks if you\n"
        "  want to ignore someone `/ignore add re:[~@%]{0,3}nightbot` should ignore\n"
        "  a nick with all or none of the prefixes used by this script.\n"
        "  NOTE: This may cause high cpu usage in very active chat and/or on slower cpus.\n"
        "  This can also be disabled by setting\n    /set plugins.var.python.twitch.prefix_nicks off\n"
        "\n\n"
        "  If you are experiencing errors you can enable debug mode by setting\n"
        "    /set plugins.var.python.twitch.debug on\n"
        "  You can also try disabling SSL/TLS cert verification.\n"
        "    /set plugins.var.python.twitch.ssl_verify off\n"
        "\n\n"
        "  Required server settings:\n"
        "    /server add twitch irc.twitch.tv\n"
        "    /set irc.server.twitch.capabilities \"twitch.tv/membership,twitch.tv/commands,twitch.tv/tags\"\n"
        "    /set irc.server.twitch.nicks \"My Twitch Username\"\n"
        "    /set irc.server.twitch.password \"oauth:My Oauth Key\"\n"
        "\n"
        "  If you do not have a oauth token one can be generated for your account here\n"
        "    https://twitchapps.com/tmi/\n"
        "\n"
        "  This script also has whisper support that works like a standard query. \"/query user\"\n\n",
        "", "twitch_main", "")
    weechat.hook_signal('buffer_switch', 'twitch_buffer_switch', '')
    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'config_change', '')
    config_setup()
    weechat.hook_modifier("irc_in_CLEARCHAT", "twitch_clearchat", "")
    weechat.hook_modifier("irc_in_RECONNECT", "twitch_reconnect", "")
    weechat.hook_modifier("irc_in_USERSTATE", "twitch_suppress", "")
    weechat.hook_modifier("irc_in_HOSTTARGET", "twitch_suppress", "")
    weechat.hook_modifier("irc_in_ROOMSTATE", "twitch_roomstate", "")
    weechat.hook_modifier("irc_in_USERNOTICE", "twitch_usernotice", "")
    weechat.hook_modifier("irc_in_WHISPER", "twitch_whisper", "")
    weechat.hook_modifier("irc_out_PRIVMSG", "twitch_privmsg", "")
    weechat.hook_modifier("irc_out_WHOIS", "twitch_whois", "")
    weechat.hook_modifier("irc_in_PRIVMSG", "twitch_in_privmsg", "")
