# -*- coding: utf-8 -*-
###
#
# Copyright 2021 anonymous2ch (@ freenode.#s2ch)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# More info: https://opensource.org/licenses/MIT
# 
###


"""
TODO
----
 - replace len(nick)>2 with a more sane filter of messages, without need of translating
 - add outgoing message translation
"""

SCRIPT_NAME = "auto_translate"
SCRIPT_AUTHOR = "anonymous2chanonymous2ch (@ freenode.#s2ch)"
SCRIPT_VERSION = "0.0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Automatically translate every message in irc channel to target language via google translate"
SCRIPT_COMMAND = "auto_translate"

try:
    import weechat as w
    import json
    from urllib.parse import urlencode
    IMPORT_ERR = 0
except ImportError:
    IMPORT_ERR = 1
import os


auto_translate_settings_default = {
    'language': ('en','language code to translate to'),
    'translated_channels': ('freenode.#s2ch,freenode.#test','comma-separated list of channels, which should be translated'),
    'google_endpoint': ('https://clients5.google.com/translate_a/t', 'google translate endpoint'),
    'user-agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36','Browser version to emulate')
}

auto_translate_settings = {}

auto_translate = {
    'hook_process': '',
    'stdout': '',
    'buffer': ''  
}

def auto_translate_process_cb(data, command, rc, stdout, stderr):
    global auto_translate
    
    if stdout != '':
        auto_translate['stdout'] += stdout
    if int(rc) >= 0:
        translated = ''
        try:
            for sentence in json.loads(auto_translate['stdout'])['sentences']:
                try:
                    translated = translated + sentence["trans"]
                except KeyError:
                    pass
        except (ValueError, KeyError, IndexError) as e:
            auto_translate['hook_process'] = ''
            return w.WEECHAT_RC_ERROR
            
    w.prnt_date_tags(auto_translate['buffer'], 0, 'no_log,notify_none', translated)
    
    auto_translate['hook_process'] = ''
    return w.WEECHAT_RC_OK


def auto_translate_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    global auto_translate
    
    channel = w.buffer_get_string(buffer, 'name')
    
    nick = prefix
    
    if channel in str(auto_translate_settings['translated_channels']) and len(nick)>2 and displayed:
        try:
           mesg = message.decode('utf-8')
        except AttributeError:
           mesg = message

        translate_url = '%s?%s' % (auto_translate_settings['google_endpoint'], urlencode({
        "client":"dict-chrome-ex",
        "sl":"auto",
        "tl":auto_translate_settings['language'],
        "q":mesg
        }))
        

        # cancel current process if there is one
        if auto_translate['hook_process']:
            w.unhook(auto_translate['hook_process'])
            auto_translate['hook_process'] = ''


        auto_translate['stdout'] = ''
        auto_translate['buffer'] = buffer
        
        auto_translate['hook_process'] = w.hook_process_hashtable('url:%s' % translate_url,
                                                               { 'useragent': auto_translate_settings['user-agent'] , 'buffer':buffer},
                                                               10 * 1000,
                                                               'auto_translate_process_cb', '')
                                                               

    return w.WEECHAT_RC_OK

def auto_translate_load_config():
    global auto_translate_settings_default, auto_translate_settings
    version = w.info_get('version_number', '') or 0
    for option, value in auto_translate_settings_default.items():
        if w.config_is_set_plugin(option):
            auto_translate_settings[option] = w.config_get_plugin(option)
        else:
            w.config_set_plugin(option, value[0])
            auto_translate_settings[option] = value[0]
        if int(version) >= 0x00030500:
            w.config_set_desc_plugin(option, value[1])

def auto_translate_config_cb(data, option, value):
    """Called each time an option is changed."""
    auto_translate_load_config()
    return w.WEECHAT_RC_OK

def auto_translate_cmd_cb(data, buffer, args):
   
    if not args or len(args.split())>1:
        w.command('', '/help %s' %SCRIPT_COMMAND)
        return w.WEECHAT_RC_OK
        
    w.config_set_plugin("translated_channels", args)
    auto_translate_settings["translated_channels"] = w.config_get_plugin("translated_channels")
    w.prnt_date_tags(buffer, 0, 'no_log,notify_none', "Translating channel: "+auto_translate_settings["translated_channels"] )
    return w.WEECHAT_RC_OK
    
    
if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
              SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    if IMPORT_ERR:
        w.prnt("", "something bad happened")
  
    auto_translate_load_config()
 

    w.hook_print('', 'irc_privmsg', '', 1, 'auto_translate_cb', '')
    
    w.hook_command("auto_translate",
                    SCRIPT_DESC,
                   "<channel(s)>",
"""
usage: /auto_translate <channel(s)>
for example:
/auto_translate freenode.#s2ch,freenode.#chlor
""","",
"auto_translate_cmd_cb", "")
