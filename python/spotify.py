# -*- coding: utf-8 -*-
#
#Copyright (c) 2009 by xt <xt@bash.no>
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
#
# If someone posts a spotify track URL in a configured channel
# this script will post back which track it is using spotify.url.fi service

#
#
# History:
# 2017-06-02, butlerx
#   version 0.8: add now required oauth support
# 2016-01-22, creadak
#   version 0.7: Updated for the new spotify API
# 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>
#   version 0.6: get python 2.x binary for hook_process (fix problem when
#                python 3.x is default python version)
# 2010-01-12, xt
#   version 0.5: add option to use notice instead of message
# 2009-12-02, xt
#   version 0.4 small bugfix with some songs and popularity
# 2009-10-29, xt
#   version 0.3 use official spotify API, and add support for albums
# 2009-09-25, xt
#   version 0.2: use spotify.url.fi
# 2009-06-19, xt <xt@bash.no>
#     version 0.1: initial
#

import re
import datetime
import weechat as w
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

SCRIPT_NAME    = "spotify"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.8"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "Look up spotify urls"

settings = {
    "buffers"       : 'freenode.#mychan,',     # comma separated list of buffers
    "emit_notice"   : 'off',                   # on or off, use notice or msg
    "client_id"     : 'client_id',
    "client_secret" : 'client_secret'
}

settings_help = {
    "buffers"       : 'A comma separated list of buffers the script should check',
    "emit_notice"   : 'If on, this script will use /notice, if off, it will use /msg to post info',
    "client_id"     : 'required client id token go to https://developer.spotify.com/my-applications/#!/applications to generate your own',
    "client_secret" : 'required client secret token go to https://developer.spotify.com/my-applications/#!/applications to generate your own'
}

spotify_track_res = (re.compile(r'spotify:(?P<type>\w+):(?P<id>\w{22})'),
                     re.compile(r'https?://open.spotify.com/(?P<type>\w+)/(?P<id>\w{22})'))

def get_spotify_ids(s):
    for r in spotify_track_res:
        for type, track in r.findall(s):
            yield type, track

def parse_response(data, type):
    if type == 'track':
        name = data['name']
        album = data['album']['name']
        artist = data['artists'][0]['name']
        duration = str(datetime.timedelta(milliseconds=data['duration_ms'])).split('.')[0]
        popularity = data['popularity']
        return "%s - %s / %s %s %d%%" % (artist, name, album, duration, popularity)
    elif type == 'album':
        name = data['name']
        artist = data['artists'][0]['name']
        tracks = data['tracks']['total']
        released = data['release_date'].split('-')[0]
        length = 0
        for track in data['tracks']['items']:
            length += track['duration_ms']
        duration = str(datetime.timedelta(milliseconds=length)).split('.')[0]
        return "%s - %s (%s) - %d tracks (%s)" % (artist, name, released, tracks, duration)
    elif type == 'artist':
        name = data['name']
        followers = data['followers']['total']
        return "%s - %s followers" % (name, followers)

def spotify_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):
    notice = w.config_get_plugin('emit_notice')
    buffer_name = w.buffer_get_string(buffer, "name")
    server, channel = buffer_name.split('.')
    buffers_to_check = w.config_get_plugin('buffers').split(',')
    client_credentials_manager = SpotifyClientCredentials(w.config_get_plugin('client_id'), w.config_get_plugin('client_secret'))
    spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    command = "msg"
    if notice == "on":
        command = "notice"

    if buffer_name.lower() not in [buffer.lower() for buffer in buffers_to_check]:
        return w.WEECHAT_RC_OK

    for type, id in get_spotify_ids(message):
        if type == 'album':
            results = spotify.album(id)
        elif type == 'track':
            results = spotify.track(id)
        elif type == 'artist':
            results = spotify.artist(id)
        reply = parse_response(results, type)
        w.command('', "/%s -server %s %s %s" % (command, server, channel, reply))

    return w.WEECHAT_RC_OK

if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                  SCRIPT_DESC, "", ""):
        # Set default settings
        for option, default in settings.iteritems():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, default)

        # Set help text
        for option, description in settings_help.iteritems():
            w.config_set_desc_plugin(option, description)

        w.hook_print("", "", "spotify", 1, "spotify_print_cb", "")
