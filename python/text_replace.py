# =============================================================================
#  text_replace.py (c) Oktober 2007 by calmar <mac@calmar.ws>
#
#  Licence     : GPL
#  Description : replace text in WeeChat on incoming/outgoing messages
#  ### changelog ###
#
#
#  * version 0.1:
#      - initial
#
#  * version 0.2:
#      - no replacing on /text_replace_ commands
#
#  * version 0.3:
#      - /help text added to the add_command_handler
#
#
# =============================================================================
#
# INSTALL: e.g. download and save in your ~/.weechat/python/autostart/ folder
#
# USAGE:   Format / delimiter
#          ------------------
#          The delimiter between the abbreviation and the replacement is: ` > ' 
#          (a greater-than-arrow surrounded by a space left and exactly one on the right)
#          so: /command [[ abbreviation] > replacement ]
#
#          Commands
#          --------
#          /text_replace_out abbr. > replacement  # ADDS an outgoing replacement
#          /text_replace_in abbr. > replacement   # ADDS an incoming replacement
#
#          /text_replacement_{in,out}             # LISTS entries (without any argument) 
#
#          /text_replacement_{in,out} abbr.       # DELETES this entry (without a repl)
#
#          /text_replace_pause                    # pauses the plugin
#          /text_replace_resume                   # resumes it
#
#
#          <space>-eating sign: $  (/text_replace_OUT only)
#          ------------------------------------------------
#          Also note, when you want a OUT-replacement without an automatic space before/after it, 
#          Add an `$' to your replacement, 
#          e.g.                                : /text_replace_out gg > http://www.foo.com$
#          When you enter now                  : gg /news 
#          it results in an output             : http://www.foo.com/news
#          instead of normal                   : http://www.foo.com /news
#
#          also:                               : /text_replace_out e > $.png 
#          you enter                           : file e 
#          it results in an output             : file.png 
#          instead of                          : file .png
#
#          note: if you want a char literal $ as start or end of the out-repl. use: `$ $' 
#          e.g.                                : $ $replacement$ $
#
# BUG:     when you use multiple abbreviations (with $ space removels) side-by-side,
#          it's buggy (just won't work as expected). 
#          May create a single new abbreviation then for it instead



def command_text_replace_pause(server, args):
    if  weechat.remove_modifier("irc_in", "privmsg", "modifier_text_replace_in") and \
                weechat.remove_modifier("irc_user", "privmsg", "modifier_text_replace_out"):
        weechat.prnt("text_replace is paused ....")
    else:
        weechat.prnt("text_replace is still running. There's a problem with pausing it")
    return weechat.PLUGIN_RC_OK

def command_text_replace_resume(server, args):
    if  weechat.add_modifier("irc_in", "privmsg", "modifier_text_replace_in") and \
                weechat.add_modifier("irc_user", "privmsg", "modifier_text_replace_out"):
        weechat.prnt("text_replace got restarted ....")
    else:
        weechat.prnt("text_replace is still down . There's a problem with restarting it")
    return weechat.PLUGIN_RC_OK

def replace_initialisize (inout, dict):
    i=0
    while True:
        i += 1
        try:
            text, repl = weechat.get_plugin_config(inout + str(i)).split(" > ", 1)
            dict[text.strip()] = repl
        except (ValueError):  # no (valid) items found
            break


def modifier_text_replace_in(server, args):
    pre, middle, message = string.split(args, ":", 2)
    message = " " + message + " "   # add two extra spaces
                                    # search for words delimited by spaces ...
                                    # while the first/last on line, must match too

    for (word, rep) in replace_in.items():
        message = message.replace(" " + word + " " ," " + rep + " ")

    message = message[1:-1]         # remove the two extra spaces again
    return pre + ":" + middle + ":" + message

def modifier_text_replace_out(server, args):
    if args[0:14] == "/text_replace_":  # no replacements on that command
        return args

    args = " " + args + " "             # will search for items with a space in front/end
    for (word, rep) in replace_out.items():
        if rep[-1:] == "$" and rep[0] == "$":   #remove according spaces on $ 'sign' on repl
            args = args.replace(" " + word + " ", rep[1:-1])
        elif rep[-1:] == "$":
            args = args.replace(" " + word + " ", " " + rep[0:-1])
        elif rep[0] == "$":
            args = args.replace(" " + word + " ", rep[1:] + " ")
        else:
            args = args.replace(" " + word + " ", " " + rep + " ")

    if args[0] == " ":         # remove the added spaces again (if they are still there)
        args = args[1:]
    if args[-1] == " ":
        args = args[:-1]

    return args

def rewrite_plugin_config(inout, dict):
    i=0
    for (text, repl) in dict.items():
        i += 1
        weechat.set_plugin_config(inout + str(i), text + " > " + repl)

    weechat.set_plugin_config(inout + str(i+1),"")  # on delete: del that entry
                                                    # on adding: useless, well

def command_text_replace(server, args, inout, dict):
    try:
        text, repl = args.split(" > ", 1)
        text = text.strip()
    except ValueError, e:           # no repl -> deleting is the task...
        try:
            del dict[args.strip()]
        except KeyError, e:
            weechat.prnt("was not able to find/delete : " + args)
            return

        weechat.prnt(inout + " deleted: " + args)
        rewrite_plugin_config(inout, dict)
        return

    dict[text] = repl               # add to dict
    weechat.prnt(inout + " added: " + text + " > " + repl)
    rewrite_plugin_config(inout, dict)


def command_text_replace_in(server, args):
    if  args == "": # print a list
        if len(replace_in) == 0:
            weechat.prnt("no entries yet. Add with: /text_replace_in text > replacement")
        else:
            for (text, repl) in replace_in.items():
                weechat.prnt("in: " + text + " > " + repl)
    else:
        command_text_replace(server, args, 'in', replace_in)
    return weechat.PLUGIN_RC_OK

def command_text_replace_out(server, args):
    if  args == "":
        if len(replace_out) == 0:
            weechat.prnt("no entries yet. Add with: /text_replace_out text > replacement")
        else:
            for (text, repl) in replace_out.items():
                weechat.prnt("out: " + text + " > " + repl)
    else:
        command_text_replace(server, args, 'out', replace_out)
    return weechat.PLUGIN_RC_OK

import weechat, string 

replace_in={}
replace_out={}

weechat.register ("text_replace", "0.3", "", "replace incoming/outgoing text")

replace_initialisize ("in", replace_in)
replace_initialisize ("out", replace_out)

weechat.add_command_handler("text_replace_out", "command_text_replace_out",\
"""It replaces abbreviations on text you type (not yet dynamically)

       list all entries:     /text_replace_out
       delete an abbr.:      /text_replace_out abbreviation
       to set a new entry:   /text_replace_out abbreviation > replacement text

It normally adds a space around the replacements. 
You can prevent that with prefix- or suffix-ing your replacement with a `$'.

E.g. create a new 'gg' abbr.: /text_replace_out gg > http://www.google.com/$
when you type now: gg linux
it will result in : http://www.google.com/linux  (instead of http://www.google.com/ linux)
       """, "[[abbreviation] > replacement text]")

weechat.add_command_handler("text_replace_in", "command_text_replace_in",\
"""It replaces abbreviations on incoming text

       list all entries:     /text_replace_in
       delete an abbr.:      /text_replace_in abbreviation
       to set a new entry:   /text_replace_in abbreviation > replacement text
       """, "[[abbreviation] > replacement text]")


weechat.add_command_handler("text_replace_pause", "command_text_replace_pause",\
                                "It pauses the plugin (no further replacements)\n", \
                                "")
weechat.add_command_handler("text_replace_resume", "command_text_replace_resume",\
                                "It resumes the plugin\n", \
                                "")

weechat.add_modifier("irc_in", "privmsg", "modifier_text_replace_in")
weechat.add_modifier("irc_user", "privmsg", "modifier_text_replace_out")
