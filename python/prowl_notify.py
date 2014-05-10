# Author: kidchunks <me@kidchunks.com>
# Homepage: http://github.com/kidchunks/weechat-prowl-notify
# Version: 3.0
#
# Requires Weechat 0.3.7 or Greater
# Released under the GNU GPL v3
#
# prowl_notify is derived from notifo http://www.weechat.org/files/scripts/notifo.py
# Original Author: ochameau <poirot.alex AT gmail DOT com>

## libraries
import weechat, time, urllib, xml.etree.ElementTree as ET

## registration
weechat.register("prowl_notify", "kidchunks", "3.1", "GPL3", "prowl_notify: Push notifications to iPod Touch, iPhone or iPad with Prowl", "", "")

## settings
API_KEY = '' # API key(s) from Prowl (seperated by commas)
FORCE_ENABLED = False # enables notifications even when not away "True//False"
FLOOD_INTERVAL = 30 # time in seconds between notifications, set to 0 to disable flood control

start_time = time.time() - FLOOD_INTERVAL

## functions
def flood_check():
    global start_time
    current_time = time.time()
    elapsed_time = current_time - start_time
    if FLOOD_INTERVAL >= elapsed_time:
        return False
    else:
        start_time = current_time
        return True

def post_prowl(label, title, message):
    opt_dict = urllib.urlencode({
        'apikey': API_KEY,
        'application': label,
        'event': title,
        'description': message
    });
    weechat.hook_process_hashtable("url:https://api.prowlapp.com/publicapi/add?", { "postfields": opt_dict }, 30 * 1000, "prowl_response", "")

def prowl_response(data, command, rc, stdout, stderr):
    # display request response if request failed
    if(stderr != ""):
        weechat.prnt('', 'prowl_notify plugin: '+stderr+'')
    elif "error" in (stdout):
        error_msg = ET.fromstring(stdout)
        weechat.prnt('', 'prowl_notify plugin: '+error_msg[0].text+'')

    return weechat.WEECHAT_RC_OK

def hook_callback(data, bufferp, uber_empty, tagsn, isdisplayed,
        ishighlight, prefix, message):

    if (bufferp == weechat.current_buffer() and FORCE_ENABLED):
        pass

    ## highlight
    elif int(ishighlight) and (weechat.buffer_get_string(bufferp, 'localvar_away') or FORCE_ENABLED):
        if flood_check():
            buffer = (weechat.buffer_get_string(bufferp, "short_name") or weechat.buffer_get_string(bufferp, "name"))
            if prefix == buffer: # treat as pm if user mentions your nick in a pm
                post_prowl("WeeChat", "Private Message from " + prefix, message)

            elif prefix != buffer: # otherwise, treat as highlight
                post_prowl("WeeChat", prefix + " mentioned you on " + buffer,  message)

    ## privmsg
    elif weechat.buffer_get_string(bufferp, "localvar_type") == "private" and (weechat.buffer_get_string(bufferp, 'localvar_away') or FORCE_ENABLED):
        if flood_check():
            post_prowl("WeeChat", "Private Message from " + prefix, message)

    return weechat.WEECHAT_RC_OK

# Hooks
weechat.hook_print("", "notify_message", "", 1, "hook_callback", "")
weechat.hook_print("", "notify_private", "", 1, "hook_callback", "")
