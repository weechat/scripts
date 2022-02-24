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
# plugins.var.python.twitch.notice_notify_block (default: 1)
# plugins.var.python.twitch.client_id (default: awtv6n371jb7uayyc4jaljochyjbfxs)
# plugins.var.python.twitch.token (default: "")
#
# # History:
#
# 2020-07-27,
#     v0.9: added support for Oauth token to support twitch APIs requirement -mumixam
#           fix bug for when api returns null for game_id -mas90
#
# 2019-10-13, mumixam
#     v0.8: changed input modifier hooks to use irc_in2_* instead
#           added setting 'plugins.var.python.twitch.notice_notify_block'
#           added setting 'plugins.var.python.twitch.client_id'
#
# 2019-09-21, mumixam
#     v0.7: updated script to use current api
# 2019-03-03,
#     v0.6: added support for CLEARMSG -MentalFS
#           fixed issue with /whois -mumixam
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
SCRIPT_VERSION = "0.9"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "twitch.tv Chat Integration"
OPTIONS={
    'servers': ('twitch','Name of server(s) which script will be active on, space seperated'),
    'prefix_nicks': ('1','Prefix nicks based on ircv3 tags for mods/subs, This can be cpu intensive on very active chats [1 for enabled, 0 for disabled]'),
    'debug': ('0','Debug mode'),
    'ssl_verify': ('1', 'Verify SSL/TLS certs'),
    'notice_notify_block': ('1', 'Changes notify level of NOTICEs to low'),
    'client_id': ('awtv6n371jb7uayyc4jaljochyjbfxs', 'Twitch App ClientID'),
    'token': ('', 'Twitch User Token')
}

import weechat
import json
from calendar import timegm
from datetime import datetime, timedelta
import time
import string
import ast

curlopt = {
    "httpheader": "\n".join([
        "Authorization: Bearer "+OPTIONS['token'][0],
        "Client-ID: "+OPTIONS['client_id'][0],
    ]),
    "timeout": "5",
    "verbose": "0",
    "ssl_verifypeer": "1",
    "ssl_verifyhost": "2"
}


gameid_cache = {}
uid_cache = {}

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
    url = 'https://api.twitch.tv/helix/streams?user_login=' + username
    weechat.hook_process_hashtable(
        "url:" + url, curlopt, 7 * 1000, "stream_api", buffer)
    return weechat.WEECHAT_RC_OK


def makeutf8(data):
    data = data.encode('utf8')
    if not isinstance(data, str):
        data=str(data,'utf8')
    return data


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
    if not 'data' in jsonDict.keys():
        weechat.prnt(data, 'twitch.py: Error with twitch API (data key missing from json)')
        if OPTIONS['debug']:
            weechat.prnt(data, 'twitch.py: %s' % stdout.strip())
        return weechat.WEECHAT_RC_OK
    if not jsonDict['data']:
        line = "STREAM: %sOFFLINE%s %sCHECKED AT: (%s)" % (
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
        if len(jsonDict['data']) == 1:
            jsonDict['data'] = jsonDict['data'][0]
        output = 'STREAM: %sLIVE%s' % (green, title_fg)
        if 'game_id' in jsonDict['data']:
            if jsonDict['data']['game_id']:
                game = jsonDict['data']['game_id']
                game_id = game
                if game in gameid_cache:
                    game = gameid_cache[game]
                output += ' <%s> with' % game
            else:
                game_id = None
        else:
            game_id = None
        if 'viewer_count' in jsonDict['data']:
            viewers = jsonDict['data']['viewer_count']
            output += ' %s viewers started' % viewers
        if 'started_at' in jsonDict['data']:
            createtime = jsonDict['data']['started_at'].replace('Z', 'GMT')
            starttime = timegm(
                time.strptime(createtime, '%Y-%m-%dT%H:%M:%S%Z'))
            dur = timedelta(seconds=currenttime - starttime)
            uptime = days_hours_minutes(dur)
            output += ' %s ago' % uptime
        if 'title' in jsonDict['data']:
            titleutf8=jsonDict['data']['title'].replace('\n',' ').encode('utf8')
            titleascii=jsonDict['data']['title'].encode('ascii','replace')
            if not isinstance(titleutf8, str):
                titleascii=str(titleascii,'utf8')
                titleutf8=str(titleutf8,'utf8')
            oldtitle = weechat.buffer_get_string(data, 'localvar_tstatus')
            if not oldtitle == titleascii:
                weechat.prnt(data, '%s--%s Title is "%s"' %
                             (pcolor, ccolor, titleutf8))
                weechat.buffer_set(data, 'localvar_set_tstatus', titleascii)

        output += ' (%s)' % ptime
        if subs:
            output += " %s[SUBS]" % title_fg
        if r9k:
            output += " %s[R9K]" % title_fg
        if slow:
            output += " %s[SLOW@%s]" % (title_fg, slow)
        if emote:
            output += " %s[EMOTE]" % title_fg
        weechat.buffer_set(data, "title", output)
        if game_id is not None and not game_id in gameid_cache:
            url = 'https://api.twitch.tv/helix/games?id=' + game_id
            weechat.hook_process_hashtable(
                "url:" + url, curlopt, 7 * 1000, "game_api", data)

    return weechat.WEECHAT_RC_OK



def game_api(data, command, rc, stdout, stderr):
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

    if 'data' in jsonDict.keys():
        if not jsonDict['data']:
            return weechat.WEECHAT_RC_OK
        if len(jsonDict['data']) == 1:
            jsonDict['data'] = jsonDict['data'][0]
        old_title = weechat.buffer_get_string(data, "title")
        id = jsonDict['data']['id']
        name = makeutf8(jsonDict['data']['name'])
        new_title = old_title.replace('<{}>'.format(id),'<{}>'.format(name))
        weechat.buffer_set(data, "title", new_title)
        gameid_cache[id] = name
    return weechat.WEECHAT_RC_OK



def channel_api(data, command, rc, stdout, stderr):
    try:
        jsonDict = json.loads(stdout.strip())
    except Exception as e:
        weechat.prnt(data, '%stwitch.py: error communicating with twitch api' % weechat.prefix('error'))
        if OPTIONS['debug']:
            weechat.prnt(data['buffer'],'%stwitch.py: return code: %s' % (weechat.prefix('error'),rc))
            weechat.prnt(data['buffer'],'%stwitch.py: stdout: %s' % (weechat.prefix('error'),stdout))
            weechat.prnt(data['buffer'],'%stwitch.py: stderr: %s' % (weechat.prefix('error'),stderr))
            weechat.prnt(data['buffer'],'%stwitch.py: exception: %s' % (weechat.prefix('error'),e))
        return weechat.WEECHAT_RC_OK
    currentbuf = weechat.current_buffer()
    pcolor = weechat.color('chat_prefix_network')
    ccolor = weechat.color('chat')
    dcolor = weechat.color('chat_delimiters')
    ncolor = weechat.color('chat_nick')
    ul = weechat.color("underline")
    rul = weechat.color("-underline")
    pformat = weechat.config_string(
        weechat.config_get("weechat.look.prefix_network"))

    if 'total' in jsonDict:
        uid = command.split('=')[-1]
        name = 'WHOIS'
        if 'to_id' in command:
            followers = jsonDict['total']
            if uid in uid_cache:
                name = uid_cache[uid]
            output = '%s%s %s[%s%s%s]%s %sFollowers%s: %s' % (
                pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, followers)
            weechat.prnt(data, makeutf8(output))
            url = 'https://api.twitch.tv/helix/users/follows?from_id=' + uid
            url_hook = weechat.hook_process_hashtable(
                "url:" + url, curlopt, 7 * 1000, "channel_api", data)
            return weechat.WEECHAT_RC_OK
        if 'from_id' in command:
            following = jsonDict['total']
            if uid in uid_cache:
                name = uid_cache[uid]
            output = '%s%s %s[%s%s%s]%s %sFollowing%s: %s' % (
                pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, following)
            weechat.prnt(data, makeutf8(output))
            return weechat.WEECHAT_RC_OK
    if ('users' in jsonDict) and jsonDict['users'] and len(jsonDict['users'][0]) == 8:
        dname = jsonDict['users'][0]['display_name']
        name = jsonDict['users'][0]['name']
        create = jsonDict['users'][0]['created_at'].split('T')[0]
        status = jsonDict['users'][0]['bio']
        uid = jsonDict['users'][0]['_id']
        uid_cache[uid] = name
        output = '%s%s %s[%s%s%s]%s %sDisplay Name%s: %s' % (
                            pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, dname)
        output += '\n%s%s %s[%s%s%s]%s %sAccount Created%s: %s' % (
            pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, create)
        if status:
            output += '\n%s%s %s[%s%s%s]%s %sBio%s: %s' % (
                pcolor, pformat, dcolor, ncolor, name, dcolor, ccolor, ul, rul, status)
        weechat.prnt(data, makeutf8(output))
        url = 'https://api.twitch.tv/helix/users/follows?to_id=' + uid
        url_hook = weechat.hook_process_hashtable(
            "url:" + url, curlopt, 7 * 1000, "channel_api", data)

    else:
        weechat.prnt(data, 'Error: No Such User')

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


def twitch_clearmsg(data, modifier, modifier_data, string):
    mp = weechat.info_get_hashtable(
    'irc_message_parse', {"message": string})
    server = modifier_data
    channel = mp['channel']
    try:
        tags = dict([s.split('=') for s in mp['tags'].split(';')])
    except:
        tags = ''
    buffer = weechat.buffer_search("irc", "%s.%s" % (server, channel))
    if buffer:
        pcolor = weechat.color('chat_prefix_network')
        ccolor = weechat.color('chat')
        if 'login' in tags:
            weechat.prnt(buffer,"%s--%s a message from %s was deleted" % (pcolor, ccolor, tags['login']))
        else:
            weechat.prnt(buffer, "%s--%s a message was deleted" % (pcolor, ccolor))
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
    if not '#' in mp['channel']:
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
    url = 'https://api.twitch.tv/kraken/users?login=' + username
    params='&api_version=5'
    url_hook = weechat.hook_process_hashtable(
        "url:" + url+params, curlopt, 7 * 1000, "channel_api", currentbuf)
    return ""


def twitch_notice(data, line):
    if not OPTIONS['notice_notify_block']: return string
    return {"notify_level": "0"}


def config_setup():
    for option,value in OPTIONS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            weechat.config_set_desc_plugin(option, '%s' % value[1])
            OPTIONS[option] = value[0]
        else:
            if option == 'prefix_nicks' or option == 'debug' or option == 'ssl_verify' or option == 'notice_notify_block':
                OPTIONS[option] = weechat.config_string_to_boolean(
                    weechat.config_get_plugin(option))
            else:
                OPTIONS[option] = weechat.config_get_plugin(option)
            if option == 'debug':
                curlopt['verbose'] = weechat.config_get_plugin(option)
            if option == 'ssl_verify':
                if weechat.config_get_plugin(option) == 0:
                    curlopt['ssl_verifypeer'] = "0"
                    curlopt['ssl_verifyhost'] = "0"
                else:
                    curlopt['ssl_verifypeer'] = "1"
                    curlopt['ssl_verifyhost'] = "2"
            if option == 'client_id':
                hlist = []
                cidv = weechat.config_get_plugin(option)
                tokv = weechat.config_get_plugin('token')
                if cidv:
                    hlist.append('Client-ID: '+cidv)
                if tokv:
                    hlist.append('Authorization: Bearer '+tokv)
                if hlist:
                    curlopt['httpheader'] = '\n'.join(hlist)
            if option == 'token':
                hlist = []
                cidv = weechat.config_get_plugin('client_id')
                tokv = weechat.config_get_plugin(option)
                if tokv:
                    hlist.append('Authorization: Bearer '+tokv)
                if cidv:
                    hlist.append('Client-ID: '+cidv)
                if hlist:
                    curlopt['httpheader'] = '\n'.join(hlist)


def config_change(pointer, name, value):
    option = name.replace('plugins.var.python.'+SCRIPT_NAME+'.','')
    if option == 'prefix_nicks' or option == 'debug' or option == 'ssl_verify' or option == 'notice_notify_block':
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
    if option == 'client_id':
        for x in curlopt['httpheader'].split('\n'):
            if x.startswith('Authorization: Bearer'):
                curlopt['httpheader'] = x + '\n' + "Client-ID: " + value
                break
    if option == 'token':
        for x in curlopt['httpheader'].split('\n'):
            if x.startswith('Client-ID:'):
                curlopt['httpheader'] = x + '\n' + "Authorization: Bearer " + value
                break

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
        "    plugins.var.python.twitch.notice_notify_block (default: 1)\n"
        "    plugins.var.python.twitch.client_id (default: awtv6n371jb7uayyc4jaljochyjbfxs)\n"
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
        "    https://mumixam.github.io/weechat_twitch\n"
        "\n"
        "  This script now by default limits the level of NOTICEs from twitch server\n"
        "  What this does is makes it so 'Now hosting' notifications are classes as a low level message\n"
        "  So they no longer show up in your hotlist like a 'actual' message\n"
        "  If you would like to disable this set the following\n"
        "    /set plugins.var.python.twitch.notice_notify_block 0\n"
        "\n"
        "  If would like to use your own Client-ID it can be set with\n"
        "    /set plugins.var.python.twitch.client_id (clientid)\n"
        "\n"
        "  Twitch Helix API now requires a OAuth token for any API calls. Your token has the match your ClientID\n"
        "  One can be generated here that matches the default CleintID here:\n"
        "    https://mumixam.github.io/weechat_twitch\n"
        "    /set plugins.var.python.twitch.token (token from url)\n"
        "\n"
        "  This script also has whisper support that works like a standard query. \"/query user\"\n\n",
        "", "twitch_main", "")
    weechat.hook_signal('buffer_switch', 'twitch_buffer_switch', '')
    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'config_change', '')
    config_setup()
    weechat.hook_line("", "", "irc_notice+nick_tmi.twitch.tv", "twitch_notice", "")
    weechat.hook_modifier("irc_in2_CLEARCHAT", "twitch_clearchat", "")
    weechat.hook_modifier("irc_in2_CLEARMSG", "twitch_clearmsg", "")
    weechat.hook_modifier("irc_in2_RECONNECT", "twitch_reconnect", "")
    weechat.hook_modifier("irc_in2_USERSTATE", "twitch_suppress", "")
    weechat.hook_modifier("irc_in2_HOSTTARGET", "twitch_suppress", "")
    weechat.hook_modifier("irc_in2_ROOMSTATE", "twitch_roomstate", "")
    weechat.hook_modifier("irc_in2_USERNOTICE", "twitch_usernotice", "")
    weechat.hook_modifier("irc_in_WHISPER", "twitch_whisper", "")
    weechat.hook_modifier("irc_out_PRIVMSG", "twitch_privmsg", "")
    weechat.hook_modifier("irc_out_WHOIS", "twitch_whois", "")
    weechat.hook_modifier("irc_in2_PRIVMSG", "twitch_in_privmsg", "")
