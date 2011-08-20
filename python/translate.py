# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Sébastien Helleu <flashcode@flashtux.org>
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
#
# History:
#
# 2011-08-20, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.3: fix typo in /help translate
# 2011-03-11, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.2: get python 2.x binary for hook_process (fix problem when
#                  python 3.x is default python version)
# 2009-10-15, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = "translate"
SCRIPT_AUTHOR  = "Sébastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Translate string using Google translate API"

import_ok = True

try:
    import weechat
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

try:
    import simplejson
except:
    print "Package python-simplejson must be installed for script '%s'." % SCRIPT_NAME
    import_ok = False

try:
    import lxml.html
except:
    print "Package python-lxml must be installed for script '%s'." % SCRIPT_NAME
    import_ok = False

# script options
translate_settings = {
    "url"     : "http://ajax.googleapis.com/ajax/services/language/translate", # google API url
    "from_to" : "fr_en", # default from_to languages
    "marker"  : "&&",    # translate from this marker in string
}

translate_hook_process     = ""
translate_stdout           = ""
translate_input_before     = ""
translate_input_after      = ""
translate_options          = []

def translate_process_cb(data, command, rc, stdout, stderr):
    """ Callback reading HTML data from website. """
    global translate_hook_process, translate_stdout, translate_input_before, translate_input_after, translate_options
    if stdout != "":
        translate_stdout += stdout
    if int(rc) >= 0:
        text = ""
        try:
            resp = simplejson.loads(translate_stdout)
            text = resp["responseData"]["translatedText"]
        except:
            weechat.prnt("", "%sTranslate error (answer: %s)" % (weechat.prefix("error"), translate_stdout.strip()))
        if text != "":
            text2 = lxml.html.fromstring(text)
            translated = text2.text_content().encode("utf-8")
            if translate_options["word"]:
                translate_input_before = weechat.buffer_get_string(weechat.current_buffer(), "input")
                input = translate_input_before
                if input == "":
                    input = translated
                else:
                    pos = input.rfind(" ")
                    if pos < 0:
                        input = translated
                    else:
                        input = "%s %s" % (input[0:pos], translated)
                weechat.buffer_set(weechat.current_buffer(), "input", input)
                translate_input_after = input
            else:
                translate_input_before = weechat.buffer_get_string(weechat.current_buffer(), "input")
                if translate_options["before_marker"] != "":
                    translated = "%s%s" % (translate_options["before_marker"], translated)
                weechat.buffer_set(weechat.current_buffer(), "input", translated)
                translate_input_after = translated
        translate_hook_process = ""
    return weechat.WEECHAT_RC_OK

def translate_extract_options(options):
    words = options["string"].split(" ")
    if words:
        if words[0] == "!":
            options["lang"].reverse()
            pos = options["string"].find(" ")
            if pos >= 0:
                options["string"] = options["string"][pos+1:].strip()
            else:
                options["string"] = ""
        else:
            pos = words[0].find("_")
            if pos >= 0:
                options["lang"] = [words[0][0:pos], words[0][pos+1:]]
                pos = options["string"].find(" ")
                if pos >= 0:
                    options["string"] = options["string"][pos+1:].strip()
                else:
                    options["string"] = ""
    words = options["string"].split(" ")
    if words:
        if words[0] == "+":
            options["word"] = True
            pos = options["string"].find(" ")
            if pos >= 0:
                options["string"] = options["string"][pos+1:].strip()
            else:
                options["string"] = ""

def translate_cmd_cb(data, buffer, args):
    """ Command /translate """
    global translate_input_before, translate_hook_process, translate_stdout, translate_options
    
    # undo last translation
    if args == "<":
        current_input = weechat.buffer_get_string(buffer, "input")
        if translate_input_before != "" and current_input != translate_input_before:
            weechat.buffer_set(buffer, "input", translate_input_before)
        elif translate_input_after != "" and current_input != translate_input_after:
            weechat.buffer_set(buffer, "input", translate_input_after)
        return weechat.WEECHAT_RC_OK
    
    # default options
    translate_options = { "lang": weechat.config_get_plugin("from_to").split("_"),
                          "word": False,
                          "before_marker": "",
                          "string": args }
    
    # read options in command arguments
    translate_extract_options(translate_options)
    
    # if there's no string given as argument of command, then use buffer input
    extract = False
    if translate_options["string"] == "":
        translate_options["string"] = weechat.buffer_get_string(buffer, "input")
        extract = True
    
    # keep only text after marker for translation
    marker = weechat.config_get_plugin("marker")
    if marker != "":
        pos = translate_options["string"].find(marker)
        if pos >= 0:
            translate_options["before_marker"] = translate_options["string"][0:pos]
            translate_options["string"] = translate_options["string"][pos+len(marker):]
            extract = True
    
    # read options in text
    if extract:
        translate_extract_options(translate_options)
    
    # keep only last word if option "1 word" is enabled
    if translate_options["word"]:
        words = translate_options["string"].split(" ")
        translate_options["string"] = words[-1]
    
    # no text to translate? exit!
    if translate_options["string"] == "":
        return weechat.WEECHAT_RC_OK
    
    # cancel current process if there is one
    if translate_hook_process != "":
        weechat.unhook(translate_hook_process)
        translate_hook_process = ""
    
    # translate!
    translate_stdout = ""
    args_urlopen = "'%s', data = urllib.urlencode({'langpair': '%s|%s', 'v': '1.0', 'q': '%s', })" \
        % (weechat.config_get_plugin("url"), translate_options["lang"][0], \
               translate_options["lang"][1], translate_options["string"].replace("'", "\\'"))
    python2_bin = weechat.info_get("python2_bin", "") or "python"
    translate_hook_process = weechat.hook_process(
        python2_bin + " -c \"import urllib; print urllib.urlopen(" + args_urlopen + ").read()\"",
        10 * 1000, "translate_process_cb", "")
    
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "", ""):
        # set default settings
        for option, default_value in translate_settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        # new command
        marker = weechat.config_get_plugin("marker")
        weechat.hook_command("translate",
                             "Translate string using Google translate API.",
                             "[from_to | !] [< | + | text]",
                             "from: base language\n"
                             "  to: target language\n"
                             "   !: invert languages (translate from \"to\" to \"from\"\n"
                             "   <: restore input as it was before last translation\n"
                             "      (if you do it again, it restore input after translation)\n"
                             "   +: translate only last word\n"
                             "text: translate this text\n"
                             "      (if no text is given, input is used, useful when this command is bound to a key)\n\n"
                             "Recommended alias for /translate:\n"
                             "  /alias tr /translate\n\n"
                             "You can bind keys on this command, for example:\n"
                             "  - translate input with alt-t + alt-t (using default from_to):\n"
                             "      /key bind meta-tmeta-t /translate\n"
                             "  - translate input with alt-t + alt-r (reverse of from_to):\n"
                             "      /key bind meta-tmeta-r /translate !\n"
                             "  - translate input from english to italian with alt-t + alt-i:\n"
                             "      /key bind meta-tmeta-i /translate en_it\n"
                             "  - translate last word in input with alt-t + alt-w (using default from_to):\n"
                             "      /key bind meta-tmeta-w /translate +\n"
                             "  - restore input with alt-t + alt-u:\n"
                             "      /key bind meta-tmeta-u /translate <\n\n"
                             "Note: when translating command line, you can start with \"from_to\" or \"!\".\n"
                             "Input can contain a marker (\"%s\"), translation will start after this marker "
                             "(beginning of input will not be translated).\n\n"
                             "To define default languages, for example english to german, do that:\n"
                             "  /set plugins.var.python.translate.default \"en_de\"\n\n"
                             "Examples:\n"
                             "  /translate ! this is a test\n"
                             "  /translate en_it I want this string in italian" % marker,
                             "", "translate_cmd_cb", "")
