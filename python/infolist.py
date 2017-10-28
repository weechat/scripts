#
# Copyright (C) 2008-2012 Sebastien Helleu <flashcode@flashtux.org>
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

# Display infolist in a buffer.
#
# History:
# 2017-10-22, nils_2 <freenode.#weechat>:
#     version 0.6: add string_eval_expression()
# 2012-10-02, nils_2 <freenode.#weechat>:
#     version 0.5: switch to infolist buffer (if exists) when command /infolist
#                  is called with arguments, add some examples to help page
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: make script compatible with Python 3.x
# 2010-01-23, m4v <lambdae2@gmail.com>:
#     version 0.3: user can give a pointer as argument
# 2010-01-18, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: use tag "no_filter" for lines displayed, fix display bug
#                  when infolist is empty
# 2009-11-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: first version
# 2008-12-12, Sebastien Helleu <flashcode@flashtux.org>:
#     script creation

SCRIPT_NAME    = "infolist"
SCRIPT_AUTHOR  = "Sebastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.6"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display infolist in a buffer"

import_ok = True

try:
    import weechat
except:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

infolist_buffer = ""
infolist_var_type = { "i": "int",
                      "s": "str",
                      "p": "ptr",
                      "t": "tim",
                      "b": "buf",
                      }


def infolist_buffer_set_title(buffer):
    # get list of infolists available
    list = ""
    infolist = weechat.infolist_get("hook", "", "infolist")
    while weechat.infolist_next(infolist):
        list += " %s" % weechat.infolist_string(infolist, "infolist_name")
    weechat.infolist_free(infolist)

    # set buffer title
    weechat.buffer_set(buffer, "title",
                       "%s %s | Infolists:%s" % (SCRIPT_NAME, SCRIPT_VERSION, list))

def infolist_display(buffer, args):
    global infolist_var_type

    items = args.split(" ", 1)
    infolist_args = ""
    infolist_pointer = ""
    if len(items) >= 2:
        infolist_args = items[1]
        if infolist_args[:2] == "0x":
            infolist_pointer, sep, infolist_args = infolist_args.partition(" ")
        elif infolist_args[:3] == "\"\" ":
            infolist_args = infolist_args[3:]

    infolist = weechat.infolist_get(items[0], infolist_pointer, infolist_args)
    if infolist == "":
        weechat.prnt_date_tags(buffer, 0, "no_filter",
                               "%sInfolist '%s' not found."
                               % (weechat.prefix("error"), items[0]))
        return weechat.WEECHAT_RC_OK

    item_count = 0
    weechat.buffer_clear(buffer)
    weechat.prnt_date_tags(buffer, 0, "no_filter",
                           "Infolist '%s', with pointer '%s' and arguments '%s':" % (items[0],
                               infolist_pointer, infolist_args))
    weechat.prnt(buffer, "")
    count = 0
    while weechat.infolist_next(infolist):
        item_count += 1
        if item_count > 1:
            weechat.prnt(buffer, "")

        fields = weechat.infolist_fields(infolist).split(",")
        prefix = "%s[%s%d%s]\t" % (weechat.color("chat_delimiters"),
                                   weechat.color("chat_buffer"),
                                   item_count,
                                   weechat.color("chat_delimiters"))
        for field in fields:
            (type, name) = field.split(":", 1)
            value = ""
            quote = ""
            if type == "i":
                value = weechat.infolist_integer(infolist, name)
            elif type == "s":
                value = weechat.infolist_string(infolist, name)
                quote = "'"
            elif type == "p":
                value = weechat.infolist_pointer(infolist, name)
            elif type == "t":
                value = weechat.infolist_time(infolist, name)
            name_end = "." * (30 - len(name))
            weechat.prnt_date_tags(buffer, 0, "no_filter",
                                   "%s%s%s: %s%s%s %s%s%s%s%s%s" %
                                   (prefix, name, name_end,
                                    weechat.color("brown"), infolist_var_type[type],
                                    weechat.color("chat"),
                                    weechat.color("chat"), quote,
                                    weechat.color("cyan"), value,
                                    weechat.color("chat"), quote))
            prefix = ""
            count += 1
    if count == 0:
        weechat.prnt_date_tags(buffer, 0, "no_filter", "Empty infolist.")
    weechat.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK

def infolist_buffer_input_cb(data, buffer, input_data):
    if input_data == "q" or input_data == "Q":
        weechat.buffer_close(buffer)
    else:
        infolist_display(buffer, input_data)
    return weechat.WEECHAT_RC_OK

def infolist_buffer_close_cb(data, buffer):
    global infolist_buffer

    infolist_buffer = ""
    return weechat.WEECHAT_RC_OK

def infolist_buffer_new():
    global infolist_buffer

    infolist_buffer = weechat.buffer_search("python", "infolist")
    if infolist_buffer == "":
        infolist_buffer = weechat.buffer_new("infolist",
                                             "infolist_buffer_input_cb", "",
                                             "infolist_buffer_close_cb", "")
    if infolist_buffer != "":
        infolist_buffer_set_title(infolist_buffer)
        weechat.buffer_set(infolist_buffer, "localvar_set_no_log", "1")
        weechat.buffer_set(infolist_buffer, "time_for_each_line", "0")
        weechat.buffer_set(infolist_buffer, "display", "1")

def infolist_cmd(data, buffer, args):
    global infolist_buffer

    args = string_eval_expression(args)

    if infolist_buffer == "":
        infolist_buffer_new()
    if infolist_buffer != "" and args != "":
        infolist_display(infolist_buffer, args)
        weechat.buffer_set(infolist_buffer, "display", "1");

    return weechat.WEECHAT_RC_OK

def string_eval_expression(string):
    return weechat.string_eval_expression(string,{},{},{})

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        weechat.hook_command("infolist", "Display infolist in a buffer",
                             "[infolist [pointer] [arguments]]",
                             " infolist: name of infolist\n"
                             "  pointer: optional pointer for infolist (\"\" for none)\n"
                             "arguments: optional arguments for infolist\n\n"
                             "Command without argument will open buffer used "
                             "to display infolists.\n\n"
                             "On infolist buffer, you can enter name of an "
                             "infolist, with optional arguments.\n"
                             "Enter 'q' to close infolist buffer.\n\n"
                             "Examples:\n"
                             "  Show information about nick \"FlashCode\" in channel \"#weechat\" on server \"freenode\":\n"
                             "    /infolist irc_nick freenode,#weechat,FlashCode\n"
                             "  Show nicklist from a specific buffer:\n"
                             "    /infolist nicklist <buffer pointer>\n"
                             "  Show current buffer:\n"
                             "    /infolist buffer ${buffer}"
                             "",
                             "%(infolists)", "infolist_cmd", "")
