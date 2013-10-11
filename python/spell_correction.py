# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by nils_2 <weechatter@arcor.de>
#
# a simple spell correction for a "misspelled" word
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
# 2013-10-04: nils_2, (freenode.#weechat)
#       0.6 : add: new option replace_mode
#           : add: support of /eval (weechat >= 0.4.2)
#           : fix: typo in help
#
# 2013-06-27: nils_2, (freenode.#weechat)
#       0.5 : fix: bug with root input bar
#
# 2013-02-16: nils_2, (freenode.#weechat)
#       0.4 : bug with empty localvar removed (reported by swimmer)
#
# 2013-01-31: nils_2, (freenode.#weechat)
#       0.3 : using new info "aspell_dict" (weechat >= 0.4.1)
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.2 : make script compatible with Python 3.x
#
# 2012-01-13: nils_2, (freenode.#weechat)
#       0.1 : - initial release -
#
# requires: WeeChat version >= 0.4.0
# better use latest stable or devel version : http://www.weechat.org/download/
#
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#

try:
    import weechat, re #sys

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "spell_correction"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.6"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "a simple spell correction for a 'misspelled' word"

OPTIONS         = { 'auto_pop_up_item'       : ('off','automatic pop-up suggestion item on a misspelled word'),
                    'auto_replace'           : ('on','replaces misspelled word with selected suggestion, automatically. If you use "off" you will have to bind command "/%s replace" to a key' % SCRIPT_NAME),
                    'catch_input_completion' : ('on','will catch the input_complete commands [TAB-key]'),
                    'eat_input_char'         : ('on','will eat the next char you type, after replacing a misspelled word'),
                    'suggest_item'           : ('${white}%S${default}', 'item format (%S = suggestion, %D = dict). Colors are allowed with format "${color}". note: since WeeChat 0.4.2 content is evaluated, see /help eval.'),
                    'hide_single_dict'       : ('on','will hide dict in item if you have a single dict for buffer only'),
                    'complete_near'          : ('0','show suggestions item only if you are n-chars near the misspelled word (0 = off). Using \'replace_mode\' cursor has to be n-chars near misspelled word to cycle through suggestions.'),
                    'replace_mode'           : ('off','misspelled word will be replaced directly by suggestions. Use option \'complete_near\' to specify range and item \'spell_suggest\' to show possible suggestions.'),
                  }

Hooks = {'catch_input_completion': '', 'catch_input_return': ''}
regex_color=re.compile('\$\{([^\{\}]+)\}')
regex_optional_tags=re.compile('%\{[^\{\}]+\}')
multiline_input = 0
# ================================[ weechat options & description ]===============================
def init_options():
    for option,value in OPTIONS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value

    if OPTIONS['catch_input_completion'].lower() == "off":
        if Hooks['catch_input_completion']:
            weechat.unhook(Hooks['catch_input_completion'])
            Hooks['catch_input_completion'] = ''
            weechat.unhook(Hooks['catch_input_return'])
            Hooks['catch_input_return'] = ''
    elif OPTIONS['catch_input_completion'].lower() == "on":
        if not Hooks['catch_input_completion']:
            Hooks['catch_input_completion'] = weechat.hook_command_run('/input complete*', 'input_complete_cb', '')
            Hooks['catch_input_return'] = weechat.hook_command_run('/input return', 'input_return_cb', '')

    return weechat.WEECHAT_RC_OK

# ================================[ hooks() ]===============================
# called from command and when TAB is pressed
def auto_suggest_cmd_cb(data, buffer, args):

    input_line = weechat.buffer_get_string(buffer, 'input')
    weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_input_line', '%s' % input_line)

    if args.lower() == 'replace':
        replace_misspelled_word(buffer)
        return weechat.WEECHAT_RC_OK

#    if not weechat.buffer_get_string(buffer,'localvar_spell_correction_suggest_item'):
#        return weechat.WEECHAT_RC_OK

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    if not position:
        position = -1

    # get localvar for misspelled_word and suggestions from buffer or return
    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)
    if not localvar_aspell_suggest:
        return weechat.WEECHAT_RC_OK

    misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')

    aspell_suggestions = aspell_suggestions.replace('/',',')
    aspell_suggestion_list = aspell_suggestions.split(',')
    if len(aspell_suggestion_list) == 0:
        position = -1
        weechat.bar_item_update('spell_correction')
        return weechat.WEECHAT_RC_OK

    # append an empty entry to suggestions to quit without changes.
    if OPTIONS['auto_replace'].lower() == "on":
        aspell_suggestion_list.append('')

    position = int(position)
    # cycle backwards through suggestions
    if args == '/input complete_previous' or args == 'previous':
        # position <= -1? go to last suggestion
        if position <= -1:
            position = len(aspell_suggestion_list)-1
        position -= 1
    # cycle forward through suggestions
    else:
        if position >= len(aspell_suggestion_list)-1:
            position = 0
        else:
            position += 1

    # 2 = TAB or command is called
    weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:%s' % ('2',str(position),aspell_suggestion_list[position]))

    weechat.bar_item_update('spell_correction')
    return weechat.WEECHAT_RC_OK


# spell_correction_suggest_item:
def show_spell_correction_item_cb (data, item, window):

    # check for root input bar!
    if not window:
        window = weechat.current_window()
#        weechat.buffer_get_string(buffer,'localvar_spell_correction_suggest_item'):

    buffer = weechat.window_get_pointer(window,"buffer")
    if buffer == '':
        return ''

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    if not position or not aspell_suggest_item:
        return ''

#    config_spell_suggest_item = weechat.config_get_plugin('suggest_item')
#    if config_spell_suggest_item:
#        show_item = config_spell_suggest_item.replace('%S',aspell_suggest_item)
#        show_item = substitute_colors(show_item)
#        return '%s' % (show_item)
#    else:
#        return aspell_suggest_item

    # get spell dict
    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)
    dicts_found = localvar_aspell_suggest.count("/")
    config_spell_suggest_item = weechat.config_get_plugin('suggest_item')
    if dicts_found:
        # aspell.dict.full_name = en_GB,de_DE-neu
        # localvar_dict = en_GB,de_DE-neu
        dictionary = get_aspell_dict_for(buffer)
        if not dictionary:
            return aspell_suggest_item
        dictionary_list = dictionary.split(',')
        # more then one dict?
        if len(dictionary_list) > 1:
            undef,aspell_suggestions = localvar_aspell_suggest.split(':')
            dictionary = aspell_suggestions.split('/')
            words = 0
            i = -1
            for a in dictionary:
                i += 1
                words += a.count(',')+1
                if words > int(position):
                    break
            if config_spell_suggest_item:
                show_item = config_spell_suggest_item.replace('%S',aspell_suggest_item)
                show_item = show_item.replace('%D',dictionary_list[i])
                show_item = substitute_colors(show_item)
                return '%s' % (show_item)
            else:
                return aspell_suggest_item
    else:
        if config_spell_suggest_item:
            show_item = config_spell_suggest_item.replace('%S',aspell_suggest_item)
            if weechat.config_get_plugin('hide_single_dict').lower() == 'off':
                show_item = show_item.replace('%D',get_aspell_dict_for(buffer))
            else:
                show_item = show_item.replace('%D','').rstrip()

            show_item = substitute_colors(show_item)
            return '%s' % (show_item)
    return aspell_suggest_item

# if a suggestion is selected and you edit input line, then replace misspelled word!
def input_text_changed_cb(data, signal, signal_data):
    global multiline_input

    if multiline_input == '1':
        return weechat.WEECHAT_RC_OK

    buffer = signal_data
    if not buffer:
        return weechat.WEECHAT_RC_OK

#    if OPTIONS['replace_mode'].lower() == "on" and weechat.buffer_get_string(buffer,'localvar_inline_replace_mode'):
#        tab_complete,position,aspell_suggest_items = weechat.buffer_get_string(buffer,'localvar_inline_suggestions').split(':',2)
#        weechat.buffer_set(buffer, 'localvar_set_inline_suggestions', '%s:%s:%s' % ('0',position,aspell_suggest_items))
#        return weechat.WEECHAT_RC_OK

        return weechat.WEECHAT_RC_OK

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    if not position or not aspell_suggest_item:
        return weechat.WEECHAT_RC_OK

    # 1 = cursor etc., 2 = TAB, 3 = replace_mode
    if tab_complete != '0':
        if not aspell_suggest_item:
            aspell_suggest_item = ''
        weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:%s' % ('0',position,aspell_suggest_item))
        weechat.bar_item_update('spell_correction')
        return weechat.WEECHAT_RC_OK

    if OPTIONS['auto_replace'].lower() == "on":
        replace_misspelled_word(buffer)
        return weechat.WEECHAT_RC_OK

#    weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:' % ('0','-1'))
    weechat.bar_item_update('spell_correction')
    return weechat.WEECHAT_RC_OK

# also remove localvar_suggest_item
def replace_misspelled_word(buffer):
    input_line = weechat.buffer_get_string(buffer, 'localvar_spell_correction_suggest_input_line')
    if not input_line:
        # remove spell_correction item
        weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_item', '')
        weechat.bar_item_update('spell_correction')
        return
    if OPTIONS['eat_input_char'].lower() == 'off' or input_line == '':
        input_pos = weechat.buffer_get_integer(buffer,'input_pos')
        # check cursor position
        if len(input_line) < int(input_pos) or input_line[int(input_pos)-1] == ' ' or input_line == '':
            input_line = weechat.buffer_get_string(buffer, 'input')

    weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_input_line', '')

    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)

    # localvar_aspell_suggest = word,word2/wort,wort2
    if localvar_aspell_suggest:
        misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')
        aspell_suggestions = aspell_suggestions.replace('/',',')
        aspell_suggestion_list = aspell_suggestions.split(',')
    else:
        return

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    if not position or not aspell_suggest_item:
        return

    position = int(position)

    input_line = input_line.replace(misspelled_word, aspell_suggestion_list[position])
    if input_line[-2:] == '  ':
        input_line = input_line.rstrip()
        input_line = input_line + ' '

    weechat.buffer_set(buffer,'input',input_line)
    weechat.bar_item_update('spell_correction')

    # set new cursor position. check if suggestion is longer or smaller than misspelled word
    input_pos = weechat.buffer_get_integer(buffer,'input_pos') + 1
    length_misspelled_word = len(misspelled_word)
    length_suggestion_word = len(aspell_suggestion_list[position])

    if length_misspelled_word < length_suggestion_word:
        difference = length_suggestion_word - length_misspelled_word
        new_position = input_pos + difference + 1
        weechat.buffer_set(buffer,'input_pos',str(new_position))

    weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_item', '')

# format of localvar aspell_suggest (using two dicts):   diehs:die hs,die-hs,dies/dies,Diebs,Viehs
def get_localvar_aspell_suggest(buffer):
    return weechat.buffer_get_string(buffer, 'localvar_aspell_suggest')

def get_aspell_dict_for(buffer):
    # this should never happens, but to be sure. Otherwise WeeChat will crash
    if buffer == '':
        return ''
    if int(version) >= 0x00040100:
        return weechat.info_get("aspell_dict", buffer)

    # this is a "simple" work around and it only works for buffers with given dictionary
    # no fallback for partial name like "aspell.dict.irc". Get your hands on WeeChat 0.4.1
    full_name = weechat.buffer_get_string(buffer,'full_name')
    return weechat.config_string(weechat.config_get('aspell.dict.%s' % weechat.buffer_get_string(buffer,'full_name')))

def substitute_colors(text):
    if int(version) >= 0x00040200:
        return weechat.string_eval_expression(text,{},{},{})
    # substitute colors in output
    return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

def get_position_and_suggest_item(buffer):
    if weechat.buffer_get_string(buffer,'localvar_spell_correction_suggest_item'):
        tab_complete,position,aspell_suggest_item = weechat.buffer_get_string(buffer,'localvar_spell_correction_suggest_item').split(':',2)
        return (tab_complete,position,aspell_suggest_item)
    else:
        return ('', '', '')

def aspell_suggest_cb(data, signal, signal_data):
    buffer = signal_data
    if OPTIONS['replace_mode'].lower() == 'on':
        localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)
        if localvar_aspell_suggest:
            # aspell says, suggested word is also misspelled. check out if we already have a suggestion list and don't use the new misspelled word!
            if weechat.buffer_get_string(buffer,'localvar_inline_suggestions'):
                return weechat.WEECHAT_RC_OK
            misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')
            aspell_suggestions = aspell_suggestions.replace('/',',')
            weechat.buffer_set(buffer, 'localvar_set_inline_suggestions', '%s:%s:%s' % ('2','0',aspell_suggestions))
            weechat.bar_item_update('spell_suggest')
            return weechat.WEECHAT_RC_OK

    if OPTIONS['auto_pop_up_item'].lower() == 'on':
        auto_suggest_cmd_cb('', buffer, '')
        weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_input_line', '')
    weechat.bar_item_update('spell_suggest')
    return weechat.WEECHAT_RC_OK

def get_last_position_of_misspelled_word(misspelled_word, buffer):
    input_pos = weechat.buffer_get_integer(buffer,'input_pos')
    input_line = weechat.buffer_get_string(buffer, 'input')
    x = input_line.rfind(misspelled_word, 0, int(input_pos))
    y = x + len(misspelled_word)
    return x, y, input_pos

# this is a work-around for multiline
def multiline_cb(data, signal, signal_data):
    global multiline_input

    multiline_input = signal_data
#    if multiline_input == '1':
#        buffer = weechat.window_get_pointer(weechat.current_window(),"buffer")
#        input_line = weechat.buffer_get_string(buffer, 'input')
#    else:
#        buffer = weechat.window_get_pointer(weechat.current_window(),"buffer")
#        input_line_bak = weechat.buffer_get_string(buffer, 'input')

#        if input_line != input_line_bak:
#            input_text_changed_cb('','',buffer)

    return weechat.WEECHAT_RC_OK

# ================================[ hook_keys() ]===============================
# TAB key pressed?
def input_complete_cb(data, buffer, command):

    # check if a misspelled word already exists!
    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)
    if not localvar_aspell_suggest and not weechat.buffer_get_string(buffer,'localvar_inline_replace_mode'):
        return weechat.WEECHAT_RC_OK

    # first [TAB] on a misspelled word in "replace mode"
    if OPTIONS['replace_mode'].lower() == "on" and not weechat.buffer_get_string(buffer,'localvar_inline_replace_mode') and int(OPTIONS['complete_near']) >= 0:
        weechat.buffer_set(buffer, 'localvar_set_inline_replace_mode', '1')

        misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')
        begin_last_position, end_last_position, input_pos = get_last_position_of_misspelled_word(misspelled_word, buffer)

        # maybe nick completion?
        if begin_last_position == -1:
            delete_localvar_replace_mode(buffer)
            return weechat.WEECHAT_RC_OK

        if input_pos - end_last_position > int(OPTIONS['complete_near']):
            delete_localvar_replace_mode(buffer)
            return weechat.WEECHAT_RC_OK

        aspell_suggestions = aspell_suggestions.replace('/',',')
        weechat.buffer_set(buffer, 'localvar_set_inline_suggestions', '%s:%s:%s' % ('2','0',aspell_suggestions))
        weechat.buffer_set(buffer, 'localvar_set_save_position_of_word', '%s:%s' % (begin_last_position, end_last_position))
        inline_suggestions = aspell_suggestions.split(',')

        input_line = weechat.buffer_get_string(buffer, 'input')
        input_line = input_line[:begin_last_position] + inline_suggestions[0] + input_line[end_last_position:]

#        input_line = input_line.replace(misspelled_word, inline_suggestions[0])
        word_differ = 0
        if len(misspelled_word) > len(inline_suggestions[0]):
            word_differ = len(misspelled_word) - len(inline_suggestions[0])
        else:
            word_differ = len(inline_suggestions[0]) - len(misspelled_word)
        if input_line[-2:] == '  ':
            input_line = input_line.rstrip()
            input_line = input_line + ' '

        weechat.buffer_set(buffer,'input',input_line)
        input_pos = int(input_pos) + word_differ
        weechat.buffer_set(buffer,'input_pos',str(input_pos))
        weechat.bar_item_update('spell_suggest')
        return weechat.WEECHAT_RC_OK

    # after first [TAB] on a misspelled word in "replace mode"
    if OPTIONS['replace_mode'].lower() == "on" and weechat.buffer_get_string(buffer,'localvar_inline_replace_mode') == "1" and int(OPTIONS['complete_near']) >= 0:
        tab_complete,position,aspell_suggest_items = weechat.buffer_get_string(buffer,'localvar_inline_suggestions').split(':',2)

        if not position or not aspell_suggest_items:
            weechat.buffer_set(buffer, 'localvar_del_inline_replace_mode', '')
            return weechat.WEECHAT_RC_OK
        inline_suggestions = aspell_suggest_items.split(',')

        position = int(position)
        previous_position = position
        # cycle backwards through suggestions
        if command == '/input complete_previous':
            # position <= -1? go to last suggestion
            if position <= -1:
                position = len(inline_suggestions)-1
            else:
                position -= 1
        # cycle forward through suggestions
        elif command == '/input complete_next':
            if position >= len(inline_suggestions)-1:
                position = 0
            else:
                position += 1

        begin_last_position, end_last_position, input_pos = get_last_position_of_misspelled_word(inline_suggestions[previous_position], buffer)

        if input_pos - end_last_position > int(OPTIONS['complete_near']):
            delete_localvar_replace_mode(buffer)
            return weechat.WEECHAT_RC_OK

        input_line = weechat.buffer_get_string(buffer, 'input')
        input_line = input_line[:begin_last_position] + inline_suggestions[position] + input_line[end_last_position:]
#        input_line = input_line.replace(inline_suggestions[previous_position], inline_suggestions[position])

        word_differ = 0
        if len(inline_suggestions[previous_position]) > len(inline_suggestions[position]):
            word_differ = len(inline_suggestions[previous_position]) - len(inline_suggestions[position])
        else:
            word_differ = len(inline_suggestions[position]) - len(inline_suggestions[previous_position])

        if input_line[-2:] == '  ':
            input_line = input_line.rstrip()
            input_line = input_line + ' '

        weechat.buffer_set(buffer,'input',input_line)
        input_pos = int(input_pos) + word_differ
        weechat.buffer_set(buffer,'input_pos',str(input_pos))

        weechat.buffer_set(buffer, 'localvar_set_inline_suggestions', '%s:%s:%s' % ('2',str(position),aspell_suggest_items))
        weechat.bar_item_update('spell_suggest')
        return weechat.WEECHAT_RC_OK

    if int(OPTIONS['complete_near']) > 0:
        misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')
        begin_last_position, end_last_position, input_pos = get_last_position_of_misspelled_word(misspelled_word, buffer)
        if input_pos - end_last_position > int(OPTIONS['complete_near']):
            return weechat.WEECHAT_RC_OK

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:%s' % ('2',position,aspell_suggest_item))

    auto_suggest_cmd_cb('', buffer, command)
    weechat.bar_item_update('spell_suggest')
    return weechat.WEECHAT_RC_OK


def delete_localvar_replace_mode(buffer):
    if OPTIONS['replace_mode'].lower() == "on":
        weechat.buffer_set(buffer, 'localvar_del_inline_replace_mode', '')
        weechat.buffer_set(buffer, 'localvar_del_inline_suggestions', '')
        weechat.buffer_set(buffer, 'localvar_del_save_position_of_word', '')
        weechat.bar_item_update('spell_suggest')

# if a suggestion is selected and you press [RETURN] replace misspelled word!
def input_return_cb(data, signal, signal_data):
    buffer = signal

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    if not position or not aspell_suggest_item:
        return weechat.WEECHAT_RC_OK

    if OPTIONS['auto_replace'].lower() == "on" and aspell_suggest_item:
        replace_misspelled_word(buffer)

    return weechat.WEECHAT_RC_OK

# /input delete_*
def input_delete_cb(data, signal, signal_data):
    buffer = signal
    delete_localvar_replace_mode(buffer)
    weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_item', '')
    weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_input_line', '')
    weechat.bar_item_update('spell_correction')
    return weechat.WEECHAT_RC_OK

# /input move_* (cursor position)
def input_move_cb(data, signal, signal_data):
    buffer = signal

    if OPTIONS['replace_mode'].lower() == "on" and weechat.buffer_get_string(buffer,'localvar_inline_replace_mode') == "1":
        delete_localvar_replace_mode(buffer)
        weechat.buffer_set(buffer, 'localvar_del_spell_correction_suggest_item', '')
#        tab_complete,position,aspell_suggest_items = weechat.buffer_get_string(buffer,'localvar_inline_suggestions').split(':',2)
#        weechat.buffer_set(buffer, 'localvar_set_inline_suggestions', '%s:%s:%s' % ('1',position,aspell_suggest_items))
        return weechat.WEECHAT_RC_OK

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)

    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)
    if not localvar_aspell_suggest:
        return weechat.WEECHAT_RC_OK

    misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')

    if not aspell_suggest_item in aspell_suggestions:
        aspell_suggestion_list = aspell_suggestions.split(',',1)
        weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:%s' % ('1',0,aspell_suggestion_list[0]))
        weechat.bar_item_update('spell_correction')
        return weechat.WEECHAT_RC_OK

    weechat.buffer_set(buffer, 'localvar_set_spell_correction_suggest_item', '%s:%s:%s' % ('1',position,aspell_suggest_item))

    return weechat.WEECHAT_RC_OK

# aspell_suggest: "mispelled:mi spelled,mi-spelled,misspelled"
# weechat.bar_item_update('spell_suggest')
def show_spell_suggestion_item_cb (data, item, window):
    buffer = weechat.window_get_pointer(window,"buffer")
    if buffer == '':
        return ''

    if OPTIONS['replace_mode'].lower() == "on":
        if not weechat.buffer_get_string(buffer,'localvar_inline_suggestions'):
            return ''
        tab_complete,position,aspell_suggest_items = weechat.buffer_get_string(buffer,'localvar_inline_suggestions').split(':',2)
        return aspell_suggest_items

    tab_complete,position,aspell_suggest_item = get_position_and_suggest_item(buffer)
    localvar_aspell_suggest = get_localvar_aspell_suggest(buffer)

    # localvar_aspell_suggest = word,word2/wort,wort2
    if localvar_aspell_suggest:
        misspelled_word,aspell_suggestions = localvar_aspell_suggest.split(':')
        aspell_suggestions_orig = aspell_suggestions
        aspell_suggestions = aspell_suggestions.replace('/',',')
        aspell_suggestion_list = aspell_suggestions.split(',')

        if not position:
            return ''
        if int(position) < len(aspell_suggestion_list):
            reset_color = weechat.color('reset')
            color = weechat.color("red")
            new_word = aspell_suggestion_list[int(position)].replace(aspell_suggestion_list[int(position)],'%s%s%s' % (color, aspell_suggestion_list[int(position)], reset_color))
    else:
        return ''

    return aspell_suggestions_orig

def window_switch_cb(data, signal, signal_data):
    weechat.bar_item_update('spell_correction')
    return weechat.WEECHAT_RC_OK
def buffer_switch_cb(data, signal, signal_data):
    weechat.bar_item_update('spell_correction')
    return weechat.WEECHAT_RC_OK

# ================================[ check for nick ]===============================
def weechat_nicklist_search_nick(buffer, nick):
    return weechat.nicklist_search_nick(buffer, "", nick)

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0

        if int(version) < 0x00040000:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 0.4.0 or higher'))
            weechat.command('','/wait 1ms /python unload %s' % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'previous|replace',
                            '\n'
                            'Add item "spell_correction" to a bar (i suggest the input bar).\n'
                            '\n'
                            'On an misspelled word, press TAB to cycle through suggestions. Any key on suggestion will replace misspelled word\n'
                            'with current suggestion.\n'
                            '\n'
                            'You have to set "aspell.check.suggestions" to a value >= 0 (default: -1 (off)).\n'
                            'Using "aspell.check.real_time" the nick-completion will not work, until all misspelled words in input_line are replaced.\n'
                            '\n'
                            'You can bind following commands to key:\n'
                            ' /' + SCRIPT_NAME + '           : to cycle though next suggestion\n'
                            ' /' + SCRIPT_NAME + ' previous  : to cycle though previous suggestion\n'
                            ' /' + SCRIPT_NAME + ' replace   : to replace misspelled word\n'
                            '',
                            'previous|replace',
                            'auto_suggest_cmd_cb', '')

        init_options()

        weechat.hook_command_run('/input delete_*', 'input_delete_cb', '')
        weechat.hook_command_run('/input move*', 'input_move_cb', '')
        weechat.hook_signal ('input_text_changed', 'input_text_changed_cb', '')
        # multiline workaround
        weechat.hook_signal('input_flow_free', 'multiline_cb', '')

        weechat.hook_signal ('aspell_suggest', 'aspell_suggest_cb', '')

        weechat.hook_signal ('buffer_switch', 'buffer_switch_cb','')
        weechat.hook_signal ('window_switch', 'window_switch_cb','')

        if OPTIONS['catch_input_completion'].lower() == "on":
            Hooks['catch_input_completion'] = weechat.hook_command_run('/input complete*', 'input_complete_cb', '')
            Hooks['catch_input_return'] = weechat.hook_command_run('/input return', 'input_return_cb', '')
        weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')
        weechat.bar_item_new('spell_correction', 'show_spell_correction_item_cb', '')
        weechat.bar_item_new('spell_suggest', 'show_spell_suggestion_item_cb', '')
#        weechat.prnt("","%s" % sys.version_info)
