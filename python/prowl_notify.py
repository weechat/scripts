# Author: kidchunks <me@kidchunks.com>
# Homepage: http://github.com/kidchunks/weechat-prowl-notify
# Version: 2.0
#
# prowl_notify requires Prowl on your iPod Touch, iPhone or iPad.
# See more at http://www.prowlapp.com
#
# Requires Weechat 0.3.7 or Greater
# Released under the GNU GPL v3
#
# Prowl Limitations
# IP addresses are limited to 1000 API calls per hour which begins from the start of the first call. Create a new api key just for this script.
# See more at http://www.prowlapp.com/api.php
#
# prowl_away_notify is derived from notifo http://www.weechat.org/files/scripts/notifo.py
# Original Author: ochameau <poirot.alex AT gmail DOT com>


## settings
api_key = '' # API key from Prowl
force_enabled = 'off' # enables notifications even when not away "on//off"
flood_protection =  'on' # helps prevent flooding "on//off"
flood_interval = '30' # time in seconds until reseting.

## libraries
import weechat, time

## registration
weechat.register("prowl_notify", "kidchunks", "2.0", "GPL3", "Push notifications to iPod Touch, iPhone or iPad with Prowl", "", "")

## variables
oldTime = 0;

## functions
def flood_check():
    global oldTime
    currentTime = int(time.time())
    elaspedTime = currentTime - oldTime
    if flood_interval >= elaspedTime:
        return False
    else:
        oldTime = currentTime
        return True

def postProwl(label, title, message):
    if api_key != "":
        opt_dict = "apikey=" + api_key + "&application=" + label + "&event=" + title + "&description=" + message
        weechat.hook_process_hashtable("url:https://api.prowlapp.com/publicapi/add?",
            { "postfields": opt_dict },
            30 * 1000, "", "")
    else:
        weechat.prnt("", "API Key is missing!")
        return weechat.WEECHAT_RC_OK

def hook_callback(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishighlight, prefix, message):
    if (bufferp == weechat.current_buffer()):
        pass

    # highlight
    elif ishighlight == "1" and (weechat.buffer_get_string(bufferp, 'localvar_away') or force_enabled == 'on'):
        if flood_check() or oldTime == 0:
            buffer = (weechat.buffer_get_string(bufferp, "short_name") or weechat.buffer_get_string(bufferp, "name"))
            if prefix == buffer: # treat as pm if user mentions your nick in a pm
                postProwl("WeeChat", "Private Message from " + prefix, message)
            elif prefix != buffer: # otherwise, treat as highlight
                postProwl("WeeChat", prefix + " mentioned you on " + buffer,  message)

    # privmsg
    elif weechat.buffer_get_string(bufferp, "localvar_type") == "private" and (weechat.buffer_get_string(bufferp, 'localvar_away') or force_enabled == 'on'):
        if flood_check() or oldTime == 0:
            postProwl("WeeChat", "Private Message from " + prefix, message)

    return weechat.WEECHAT_RC_OK

weechat.hook_print("", "notify_message", "", 1, "hook_callback", "")
weechat.hook_print("", "notify_private", "", 1, "hook_callback", "")
