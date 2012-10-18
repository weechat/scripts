# -*- coding: utf-8 -*-
######################################################################
# Copyright (c) 2011 by Pascal Wittmann <mail@pascal-wittmann.de>
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
# Marked Parts are from Wojciech Muła <wojciech_mula@poczta.onet.pl>
# and are licensed under BSD and are avaliable at
# http://0x80.pl/proj/aspell-python/
########################################################################

# INSTALLTION
# After copying this file into your python plugin directory, start weechat
# load the script and follow futher instructions calling
#    /help correction_completion
# You can find these instructions as markdown on
#    https://github.com/pSub/weechat-correction-completion/blob/master/README.md
# too.

# Changelog:
#
# 2012-10-18 -- Version 0.3.0
#    - incorrect words have a higher priority (typo completion)
#    - the following characters are removed from the typo: , . ; : ? ! ) ( \ / " ^
#
# 2011-06-01 -- Version 0.2.2
#    - fixed a memory leak, thanks to FlashCode
#    - documentation updates
#
# 2011-03-19 -- Version 0.2.1
#    - fixed bug that resulted in a crash of weechat
#
# 2011-03-18 -- Version 0.2.0
#    - fixed out of bounds bug
#    - apply config changes without reloading
#    - improved performance
#
# 2011-02-19 -- Version 0.1.0
#    - frist working version

import re

try:
    import ctypes
    import ctypes.util
except ImportError:
    print "This script depends on ctypes"

try:
    import weechat as w
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"

SCRIPT_NAME    = "correction_completion"
SCRIPT_AUTHOR  = "Pascal Wittmann <mail@pascal-wittmann.de>"
SCRIPT_VERSION = "0.3.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Provides a completion for 's/typo/correct'"
SCRIPT_COMMAND = "correction_completion"

# Default Options
# Your can use all aspell options listed on
# http://aspell.net/man-html/The-Options.html
settings = {
        'lang' : 'en',
}

# The Bunch Class is from
# http://code.activestate.com/recipes/52308/
class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def completion(data, completion_item, buffer, completion):
    if state.used == True:
        return w.WEECHAT_RC_OK
    else:
        state.used = True

    # Current cursor position
    pos = w.buffer_get_integer(buffer, 'input_pos')

    # Current input string
    input = w.buffer_get_string(buffer, 'input')

    fst = input.find("s/")
    snd = input.find("/", fst + 2)

    # Check for typo or suggestion completion
    if pos > 2 and fst >= 0 and fst < pos:
        if snd >= 0 and snd < pos:
          complete_replacement(pos, input, buffer)
        else:
          complete_typo(pos, input, buffer)

    state.used = False
    return w.WEECHAT_RC_OK

def complete_typo(pos, input, buffer):
    # Assume that typo changes when doing a completion
    state.curRepl = -1

    # Get the text of the current buffer
    list = []
    infolist = w.infolist_get('buffer_lines', buffer, '')
    while w.infolist_next(infolist):
        list.append(strip_symbols(w.infolist_string(infolist, 'message')))
    w.infolist_free(infolist)

    # Generate a list of words
    text = (' '.join(list)).split(' ')

    # Remove duplicate elements
    text = unify(text)

    # Split words in correct and incorrect ones
    good = [word for word in text if spellcheck(word) == True]
    bad  = [word for word in text if spellcheck(word) == False]

    # Sort by alphabet and length
    good.sort(key=lambda item: (item, len(item)))
    bad.sort(key=lambda item: (item, len(item)))

    # Place incorrcet ones in front of correct ones
    text = bad + good

    i = iter(text)

    # Get index of last occurence of "s/" befor cursor position
    n = input.rfind("s/", 0, pos)

    # Get substring and search the replacement
    substr = input[n+2:pos]
    replace = search((lambda word : word.startswith(substr)), i)

    # If no replacement found, display substring
    if replace == "":
      replace = substr

    # If substring perfectly matched take next replacement
    if replace == substr:
      try:
        replace = next(i)
      except StopIteration:
        replace = substr

    changeInput(substr, replace, input, pos, buffer)

def complete_replacement(pos, input, buffer):
    # Start Positions
    n = input.rfind("s/", 0, pos)
    m = input.rfind("/", n + 2, pos)

    repl = input[m + 1 : pos]
    typo = input[n + 2 : m]

    # Only query new suggestions, when typo changed
    if state.curRepl == -1 or typo != state.curTypo:
      state.suggestions = suggest(typo)
      state.curTypo = typo

    if len(state.suggestions) == 0:
      return

    # Start at begining when reached end of suggestions
    if state.curRepl == len(state.suggestions) - 1:
      state.curRepl = -1

    # Take next suggestion
    state.curRepl += 1

    # Put suggestion into the input
    changeInput(repl, state.suggestions[state.curRepl], input, pos, buffer)

def changeInput(search, replace, input, pos, buffer):
    # Put the replacement into the input
    n = len(search)
    input = '%s%s%s' %(input[:pos-n], replace, input[pos:])
    w.buffer_set(buffer, 'input', input)
    w.buffer_set(buffer, 'input_pos', str(pos - n + len(replace)))

def strip_symbols(string):
    return re_remove_chars.sub('', w.string_remove_color(string, ''))

def search(p, i):
    # Search for item matching the predicate p
    while True:
      try:
        item = next(i)
        if p(item):
          return item
      except StopIteration:
        return ""

def unify(list):
    # Remove duplicate elements from a list
    checked = []
    for e in list:
      if e not in checked:
        checked.append(e)
    return checked

# Parts are from Wojciech Muła
def suggest(word):
    if type(word) is str:
      suggestions = aspell.aspell_speller_suggest(
                      speller,
                      word.encode(),
                      len(word))
      elements = aspell.aspell_word_list_elements(suggestions)
      list = []
      while True:
          wordptr = aspell.aspell_string_enumeration_next(elements)
          if not wordptr:
              break;
          else:
              word = ctypes.c_char_p(wordptr)
              list.append(str(word.value))
      aspell.delete_aspell_string_enumeration(elements)
      return list
    else:
      raise TypeError("String expected")

def spellcheck(word):
    if type(word) is str:
        return aspell.aspell_speller_check(
            speller,
            word,
            len(word))
    else:
        raise TypeError("String expected")

def load_config(data = "", option = "", value = ""):
    global speller
    config = aspell.new_aspell_config()

    for option, default in settings.iteritems():
        if not w.config_is_set_plugin(option):
          w.config_set_plugin(option, default)
        value = w.config_get_plugin(option)
        if not aspell.aspell_config_replace(
                        config,
                        option.encode(),
                        value.encode()):
          raise Exception("Failed to replace config entry")

    # Error checking is from Wojciech Muła
    possible_error = aspell.new_aspell_speller(config)
    aspell.delete_aspell_config(config)
    if aspell.aspell_error_number(possible_error) != 0:
      aspell.delete_aspell_can_have_error(possible_error)
      raise Exception("Couldn't create speller")
    speller = aspell.to_aspell_speller(possible_error)
    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    # Saving the current completion state
    state = Bunch(used = False, curTypo = '', curRepl = -1, suggestions = [])

    # Use ctypes to access the apsell library
    aspell = ctypes.CDLL(ctypes.util.find_library('aspell'))
    speller = 0

    # Regex to remove unwanted characters
    re_remove_chars = re.compile('[,.;:?!\)\(\\\/\"\^]')

    # Load configuration
    load_config()

    template = 'correction_completion'

    # Register completion hook
    w.hook_completion(template, "Completes after 's/' with words from buffer",
            'completion', '')

    # Register hook to update config when option is changed with /set
    w.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "load_config", "")

    # Register help command
    w.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, "",
"""Usage:
If you want to correct yourself, you often do this using the
expression 's/typo/correct'. This plugin allows you to complete the
first part (the typo) by pressing *Tab*. The words from the actual
buffer are used to complet this part. If the word can be perfectly
matched the next word in alphabetical order is shown.

The second part (the correction) can also be completed. Just press
*Tab* after the slash and the best correction for the typo is fetched from aspell.
If you press *Tab* again, it shows the next suggestion.
The language used for suggestions can be set with the option

  plugins.var.python.correction_completion.lang

The aspell language pack must be installed for this language.

Setup:
Add the template %%(%(completion)s) to the default completion template.
The best way to set the template is to use the iset-plugin¹, because you can see
there the current value before changing it. Of course you can also use the
standard /set-command e.g.

  /set weechat.completion.default_template "%%(nicks)|%%(irc_channels)|%%(%(completion)s)"

Footnotes:
¹ http://weechat.org/scripts/source/stable/iset.pl/
"""
%dict(completion=template), '', '', '')
