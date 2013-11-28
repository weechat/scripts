# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2013 Sebastien Helleu <flashcode@flashtux.org>
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
# Translate string using Google translate API.
# (this script requires WeeChat >= 0.3.7)
#
# History:
#
# 2013-11-27, luz <ne.tetewi@gmail.com>:
#     version 0.7: switch to json version of google translate api, support
#                  multiple sentences
# 2012-12-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: automatically replace old URL (not working any more) by new one
# 2012-10-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: fix call to translate API, use hook_process_hashtable
#                  (the script now requires WeeChat >= 0.3.7)
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: make script compatible with Python 3.x
# 2011-08-20, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: fix typo in /help translate
# 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: get python 2.x binary for hook_process (fix problem when
#                  python 3.x is default python version)
# 2009-10-15, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'translate'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.7'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Translate string using Google translate API'

import_ok = True

try:
    import weechat
except:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import sys
    import json
    if sys.version_info >= (3,):
        import urllib.parse as urllib
    else:
        import urllib
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

# script options
translate_settings = {
    'url'     : 'http://translate.google.com/translate_a/t', # google API url
    'from_to' : 'fr_en', # default from_to languages
    'marker'  : '&&',    # translate from this marker in string
}

translate = {
    'hook_process': '',
    'stdout': '',
    'input_before': ['', 0],
    'input_after': ['', 0],
    'options': []
}

def translate_process_cb(data, command, rc, stdout, stderr):
    """Callback reading HTML data from website."""
    global translate
    if stdout != '':
        translate['stdout'] += stdout
    if int(rc) >= 0:
        translated = ''.join([x['trans'] for x in json.loads(translate['stdout'])['sentences']])
        if sys.version_info < (3,):
            translated = translated.encode('utf-8')
        translate['input_before'][0] = weechat.buffer_get_string(weechat.current_buffer(), 'input')
        translate['input_before'][1] = weechat.buffer_get_integer(weechat.current_buffer(), 'input_pos')
        if translate['options']['word']:
            # translate last word of input
            str_input = translate['input_before'][0]
            if str_input:
                pos = str_input.rfind(' ')
                if pos < 0:
                    str_input = translated
                else:
                    str_input = '%s %s' % (str_input[0:pos], translated)
            else:
                str_input = translated
            translate['input_after'][0] = str_input
        else:
            if translate['options']['before_marker']:
                translated = '%s%s' % (translate['options']['before_marker'], translated)
            translate['input_after'][0] = translated
        # set input with translation
        translate['input_after'][1] = len(translate['input_after'][0])
        weechat.buffer_set(weechat.current_buffer(), 'input', translate['input_after'][0])
        weechat.buffer_set(weechat.current_buffer(), 'input_pos', '%d' % translate['input_after'][1])
        translate['hook_process'] = ''
    elif int(rc) == WEECHAT_HOOK_PROCESS_ERROR:
        translate['hook_process'] = ''
    return weechat.WEECHAT_RC_OK

def translate_extract_options(options):
    """
    Extract options from a string, for example (with default from_to == 'fr_en'):
      'le ciel bleu'       => { 'lang': 'fr_en', 'text': 'le ciel bleu' }
      '! the blue sky'     => { 'lang': 'en_fr', 'text': 'the blue sky' }
      'en_it the blue sky' => { 'lang': 'en_it', 'text': 'the blue sky' }
    """
    words = options['string'].split(' ')
    if words:
        if words[0] == '!':
            options['lang'].reverse()
            pos = options['string'].find(' ')
            if pos >= 0:
                options['string'] = options['string'][pos+1:].strip()
            else:
                options['string'] = ''
        else:
            pos = words[0].find('_')
            if pos >= 0 and 5 <= len(words[0]) <= 11:
                options['lang'] = [words[0][0:pos], words[0][pos+1:]]
                pos = options['string'].find(' ')
                if pos >= 0:
                    options['string'] = options['string'][pos+1:].strip()
                else:
                    options['string'] = ''
    words = options['string'].split(' ')
    if words:
        if words[0] == '+':
            options['word'] = True
            pos = options['string'].find(' ')
            if pos >= 0:
                options['string'] = options['string'][pos+1:].strip()
            else:
                options['string'] = ''

def translate_cmd_cb(data, buffer, args):
    """Command /translate."""
    global translate

    # create keys (do NOT overwrite existing keys)
    if args == '-keys':
        rc = weechat.key_bind('default', { 'meta-tmeta-t': '/translate',
                                           'meta-tmeta-r': '/translate !',
                                           'meta-tmeta-w': '/translate +',
                                           'meta-tmeta-u': '/translate <' })
        weechat.prnt('', 'translate: %d keys added' % rc)
        return weechat.WEECHAT_RC_OK

    # undo last translation
    if args == '<':
        current_input = weechat.buffer_get_string(buffer, 'input')
        if translate['input_before'][0] and current_input != translate['input_before'][0]:
            weechat.buffer_set(buffer, 'input', translate['input_before'][0])
            weechat.buffer_set(buffer, 'input_pos', '%d' % translate['input_before'][1])
        elif translate['input_after'][0] != '' and current_input != translate['input_after'][0]:
            weechat.buffer_set(buffer, 'input', translate['input_after'][0])
            weechat.buffer_set(buffer, 'input_pos', '%d' % translate['input_after'][1])
        return weechat.WEECHAT_RC_OK

    # default options
    translate['options'] = { 'lang': weechat.config_get_plugin('from_to').split('_'),
                             'word': False,
                             'before_marker': '',
                             'string': args }

    # read options in command arguments
    translate_extract_options(translate['options'])

    # if there's no string given as argument of command, then use buffer input
    extract = False
    if translate['options']['string'] == '':
        translate['options']['string'] = weechat.buffer_get_string(buffer, 'input')
        extract = True

    # keep only text after marker for translation
    marker = weechat.config_get_plugin('marker')
    if marker != '':
        pos = translate['options']['string'].find(marker)
        if pos >= 0:
            translate['options']['before_marker'] = translate['options']['string'][0:pos]
            translate['options']['string'] = translate['options']['string'][pos+len(marker):]
            extract = True

    # read options in text
    if extract:
        translate_extract_options(translate['options'])

    # keep only last word if option "1 word" is enabled
    if translate['options']['word']:
        translate['options']['string'] = translate['options']['string'].split(' ')[-1]

    # no text to translate? exit!
    if not translate['options']['string']:
        return weechat.WEECHAT_RC_OK

    # cancel current process if there is one
    if translate['hook_process']:
        weechat.unhook(translate['hook_process'])
        translate['hook_process'] = ''

    # translate!
    url = '%s?%s' % (weechat.config_get_plugin('url'), urllib.urlencode({'client': 'a',
                                                                         'sl': translate['options']['lang'][0],
                                                                         'tl': translate['options']['lang'][1],
                                                                         'text': translate['options']['string'] }))
    translate['stdout'] = ''
    translate['hook_process'] = weechat.hook_process_hashtable('url:%s' % url,
                                                               { 'useragent': 'Mozilla/5.0' },
                                                               10 * 1000,
                                                               'translate_process_cb', '')

    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        '', ''):
        # set default settings
        for option, default_value in translate_settings.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        # replace old URL (not working any more) by new one
        if weechat.config_get_plugin('url') == 'http://ajax.googleapis.com/ajax/services/language/translate':
            weechat.config_set_plugin('url', translate_settings['url'])
            weechat.prnt('', 'translate: default URL has been set (to replace old URL)')
        # new command
        marker = weechat.config_get_plugin('marker')
        weechat.hook_command('translate',
                             'Translate string using Google translate API.',
                             '[from_to | !] [< | + | text] || -keys',
                             ' from: base language\n'
                             '   to: target language\n'
                             '    !: invert languages (translate from "to" to "from")\n'
                             '    <: restore input as it was before last translation\n'
                             '       (if you do it again, it will restore input after translation)\n'
                             '    +: translate only last word\n'
                             ' text: translate this text\n'
                             '       (if no text is given, input is used, useful when this command is bound to a key)\n'
                             '-keys: create some default keys (if some keys already exist, they are NOT overwritten):\n'
                             '         meta-tmeta-t => /translate    (translate using default from_to)\n'
                             '         meta-tmeta-r => /translate !  (reverse of from_to)\n'
                             '         meta-tmeta-w => /translate +  (translate last word)\n'
                             '         meta-tmeta-u => /translate <  (restore input)\n\n'
                             'You can define alias for /translate:\n'
                             '  /alias tr /translate\n\n'
                             'Note 1: when translating command line, you can start with "from_to" or "!".\n\n'
                             'Note 2: input can contain a marker ("%s"), translation will start after this marker '
                             '(beginning of input will not be translated).\n'
                             'Example: "this text &&est traduit" => "this text is translated"\n\n'
                             'To define default languages, for example english to german:\n'
                             '  /set plugins.var.python.translate.default "en_de"\n\n'
                             'Examples:\n'
                             '  /translate ! this is a test\n'
                             '  /translate en_it I want this string in italian' % marker,
                             '-keys|!|<|+', 'translate_cmd_cb', '')
