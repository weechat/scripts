# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 by nils_2 <weechatter@arcor.de>
#
# set message tag, when confusables chars will be used in words
#
# eg /!\ THΙS ⅭᎻΑΝNΕᏞ HᎪЅ ΜOVED TⲞ ⅠᎡϹ.ᏞⅠⲂERА.ⅭⲎᎪТ #HAΜᎡᎪⅮIΟ ⁄!＼
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
# 2021-06-23: nils_2, (libera.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 3.2
# idea by trn
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# pip3 install confusables2

import_ok = True
hook_line = False

try:
    import weechat,re
except Exception:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://www.weechat.org/')
    import_ok = False

try:
    import confusables
    from confusables import is_confusable
    from confusables import confusable_regex

except Exception:
    print('Confusables has to be installed.')
    print('Install it using `pip3 install confusables2`')
    import_ok = False

SCRIPT_NAME     = 'weefusables'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.1'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'set message tag when confusables chars will be used in words'

OPTIONS         = {'tags'        : ('confusable_filter','set tag to use for /filter'),
                   'message_tags': ('irc_privmsg','catch only messages with these tags (optional): comma-separated list of tags that must be in message (logical "or"); it is possible to combine many tags as a logical "and" with separator +; wildcard * is allowed in tags'),
                   'list_of_words': ('moved,irc,freenode','comma separated list of words to check'),
                  }

# ===================[ weechat options & description ]===================
def init_options():
    for option,value in list(OPTIONS.items()):
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option,'%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS,hook_line
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value

    if hook_line and option == 'message_tags' and value == "":
        weechat.unhook(hook_line)
        hook_line = False
    elif not hook_line and option == 'message_tags' and value != "":
        hook_line = weechat.hook_line('', '', OPTIONS['message_tags'], 'confusables', '')
    return weechat.WEECHAT_RC_OK

def shutdown_cb():
    return weechat.WEECHAT_RC_OK

def confusables(data, line):
    buf_ptr = line['buffer']
    message = line['message']
    tags = line['tags']
    prefix = line['prefix']

    if OPTIONS['list_of_words'] == "":                                    # no words given, to look at
        return weechat.WEECHAT_RC_OK

    search_strings = OPTIONS['list_of_words'].split(',')

    for i in search_strings:
        regex_string = confusable_regex(i, include_character_padding=True)
        regex = re.compile(regex_string)

        conf_result = regex.search(message)                             # get match to test with original string later
        if regex.search(message) and conf_result.group() != i:          # matching string is original string?
            return {"tags": tags + ',' + OPTIONS['tags']}

#    weechat.prnt_date_tags(buf_ptr,0,tags + ',' + OPTIONS['tags'],message)
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == "__main__" and import_ok:
    global version
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, 'shutdown_cb', ''):
        weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
                        '',
                        'How to use script:\n'
                        '\n'
                        'configure script options with either /set command or /fset ' + SCRIPT_NAME + '\n'
                        'create an filter to filter messages with tags created by this script '
                        '(by default, the script is using tag "confusable_filter").\n'
                        '/filter add confusable * confusable_filter *\n'
                        'see /help filter\n'
                        '',
                        '',
                        '',
                        '')

        version = weechat.info_get('version_number', '') or 0

        # get weechat version (3.2) and store it
        if int(version) >= 0x03020000:
            # init options from your script
            init_options()

            hook_line = weechat.hook_line('', '', OPTIONS['message_tags'], 'confusables', '')
            # create a hook for your options
            hook_config = weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
        else:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 3.2 or higher'))
            weechat.command('','/wait 1ms /python unload %s' % SCRIPT_NAME)
