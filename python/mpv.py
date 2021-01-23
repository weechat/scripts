"""
    mpv.py

    author: teraflops <cprieto.ortiz@gmail.com>
    contributor: nashgul <m.alcocer1978@gmail.com>
      desc: Sends your current mpv track to the current buffer
     usage:
       /mpv
    note: you have to run this way: mpv --input-ipc-server=/tmp/mpvsocket

   license: The Beer-ware License

"""

import weechat
import subprocess
from json import loads

MPV = {
    'SCRIPT_NAME'     : 'mpv',
    'SCRIPT_COMMAND'  : 'mpv',
    'default_options' : {
                            'message'    : '/me is now watching: ',
                            'mpv_socket' : '/tmp/mpvsocket'
                        },
}

def set_default_options():
    for option, default_value in MPV['default_options'].items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

def reload_options_cb(data, option, value):
    MPV[option.split('.')[-1]] = value
    return weechat.WEECHAT_RC_OK

def load_options():
    for option in MPV['default_options'].keys():
        MPV[option] = weechat.config_get_plugin(option)

def mpv_msg(world,world_eol,userdata):
    try:
        output = subprocess.check_output("echo \'{ \"command\": [\"get_property\", \"metadata\"] }\' | socat - %s" % MPV['mpv_socket'], shell=True)
        output_short = subprocess.check_output("echo \'{ \"command\": [\"get_property\", \"media-title\"] }\' | socat - %s" % MPV['mpv_socket'], shell=True)
        metadata = loads(output.decode('utf8'))
        metadata_short = loads(output_short.decode('utf8'))
        if 'album' not in metadata['data']:
            title = metadata_short['data'].encode('utf-8')
            all = '%s' % MPV['message'] + str(title)
            weechat.command(weechat.current_buffer(), all)
            return weechat.WEECHAT_RC_OK

        if 'album' in metadata['data']:
            title = metadata['data']['title'].encode('utf-8')
            artist = metadata['data']['artist'].encode('utf-8')
            np = str(artist) + ' ' + str(title)
            all = '%s' %  MPV['message'] + np
            weechat.command(weechat.current_buffer(), all)
            return weechat.WEECHAT_RC_OK
        else:
            return weechat.WEECHAT_RC_ERROR
    except:
        weechat.prnt('', '%s: mpv socket not properly configurated or mpv is not running' % MPV['SCRIPT_NAME'])
        return weechat.WEECHAT_RC_ERROR

weechat.register(MPV['SCRIPT_NAME'], "llua", "0.2", "The Beer-ware License", "Now Playing for mpv", "", "")
set_default_options()
load_options()
weechat.hook_config('plugins.var.python.' + MPV['SCRIPT_NAME'] + '.*', 'reload_options_cb', '')
weechat.hook_command(MPV['SCRIPT_COMMAND'], "Now Watching", "", "/%s" % MPV['SCRIPT_COMMAND'], "", "mpv_msg", "")
