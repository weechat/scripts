# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2012 Sebastien Helleu <flashcode@flashtux.org>
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
# Display content of viedemerde.fr/fmylife.com website.
# (this script requires WeeChat 0.3.7 or newer)
#
# History:
#
# 2012-12-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.3: fix parsing: replace "\r" by space
# 2012-11-12, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.2: use URL transfer in API (for WeeChat >= 0.3.7)
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.1: make script compatible with Python 3.x
# 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.0: get python 2.x binary for hook_process (fix problem when
#                  python 3.x is default python version)
# 2011-03-04, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.9: fix memory leak in XML parser
# 2010-04-28, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.8: switch to vdm buffer if already opened
# 2009-10-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: use "q" to close vdm buffer
# 2009-06-12, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: fix bug when vdm buffer is closed: clear old list
# 2009-05-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: sync with last API changes
# 2009-03-16, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: use existing vdm buffer if found (for example after /upgrade)
# 2009-03-15, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: do not switch to vdm buffer if there's nothing new to
#                  display, do not display time for each line on vdm buffer
# 2009-03-12, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: fix bug with "&quot;" in string
# 2009-03-08, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

import weechat, sys, xml.dom.minidom

SCRIPT_NAME    = "vdm"
SCRIPT_AUTHOR  = "Sebastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "1.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display content of viedemerde.fr/fmylife.com website"

# script options
settings = {
    # language: en or fr
    "lang"             : "en",
    # url for API
    "url"              : "http://api.betacie.com/view/%s?key=readonly&language=%s",
    # auto-switch to buffer when data is ready (when using /vdm command)
    "auto_switch"      : "on",
    # color for # VDM
    "color_number"     : "cyan",
    # display number as prefix for each line?
    "number_as_prefix" : "on",
    # colors for displaying items (one or more colors, separated by ";")
    "colors"           : "default;green;brown",
    # blank line between each VDM
    "blank_line"       : "on",
    # reverse order (most recent entry displayed last)
    "reverse"          : "off",
}

vdm_buffer           = ""
vdm_switch_to_buffer = False
vdm_hook_process     = ""
vdm_key              = ""
vdm_stdout           = ""
vdm_oldlist          = []

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    weechat.hook_command("vdm",
                         "Display content of viedemerde.fr/fmylife.com website "
                         "in a buffer",
                         "[[*]key | r | - | + | fr | en]",
                         "key: key for website:\n"
                         "           last: last VDMs\n"
                         "         random: random VDM\n"
                         "            top: top VDMs\n"
                         "           flop: flop VDMs\n"
                         "              #: a VDM number\n"
                         "       category: english: love, money, kids, work, "
                         "health, sex, miscellaneous\n"
                         "                 french: amour, argent, travail, "
                         "sante, sexe, inclassable\n"
                         "     - if key begins with \"*\", then VDM buffer is "
                         "cleared before reading website\n"
                         "     - default key is \"last\"\n"
                         "     - for last/top/flop/category, you can add "
                         "\"/\" + page number (1 is second page)\n"
                         "  r: replay last query\n"
                         "  -: get previous page for last query\n"
                         "  +: get next page for last query\n"
                         " fr: set language to french (content of "
                         "viedemerde.fr)\n"
                         " en: set language to english (content of "
                         "fmylife.com)\n\n"
                         "Examples:\n"
                         "  /vdm last     => display last VDMs\n"
                         "  /vdm last/1   => display second page of last VDMs\n"
                         "  /vdm top      => display top VDMs\n"
                         "  /vdm *random  => clear VDM buffer and display a "
                         "random VDM\n"
                         "  /vdm +        => display next page\n"
                         "  /vdm *+       => clear VDM buffer and display "
                         "next page\n\n"
                         "All arguments for this command can be used as input "
                         "on VDM buffer.",
                         "", "vdm_cmd", "")
    for option, default_value in settings.items():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value)

def vdm_buffer_set_title():
    """ Set buffer title, using key used by user. """
    global vdm_buffer, vdm_key
    lang = weechat.config_get_plugin("lang")
    weechat.buffer_set(vdm_buffer, "title",
                       SCRIPT_NAME + " " + SCRIPT_VERSION + " [" + lang + "]  |  "
                       + "Keys: last, random, top, flop, #, category "
                       + "(current: '" + vdm_key + "')  |  "
                       + "Get help with /help vdm")

def vdm_display(vdm):
    """ Display VDMs in buffer. """
    global vdm_buffer
    weechat.buffer_set(vdm_buffer, "unread", "1")
    if weechat.config_get_plugin("number_as_prefix") == "on":
        separator = "\t"
    else:
        separator = " > "
    colors = weechat.config_get_plugin("colors").split(";");
    vdm2 = vdm[:]
    if weechat.config_get_plugin("reverse") == "on":
        vdm2.reverse()
    for index, item in enumerate(vdm2):
        item_id = item["id"]
        item_text = item["text"]
        if sys.version_info < (3,):
            # python 2.x: convert unicode to str (in python 3.x, id and text are already strings)
            item_id = item_id.encode("UTF-8")
            item_text = item_text.encode("UTF-8")
        weechat.prnt_date_tags(vdm_buffer,
                               0, "notify_message",
                               "%s%s%s%s%s" %
                               (weechat.color(weechat.config_get_plugin("color_number")),
                                item_id,
                                separator,
                                weechat.color(colors[0]),
                                item_text))
        colors.append(colors.pop(0))
        if index == len(vdm) - 1:
            weechat.prnt(vdm_buffer, "------")
        elif weechat.config_get_plugin("blank_line") == "on":
            weechat.prnt(vdm_buffer, "")

def vdm_parse(string):
    """ Parse XML output from HTTP output string. """
    global vdm_buffer, vdm_switch_to_buffer
    vdm = []
    try:
        dom = xml.dom.minidom.parseString(string)
    except:
        weechat.prnt(vdm_buffer,
                     "%sError reading data from website (maybe it's down? "
                     "please try again later)" % weechat.prefix("error"))
        if vdm_switch_to_buffer:
            weechat.buffer_set(vdm_buffer, "display", "1")
    else:
        for node in dom.getElementsByTagName("item"):
            texte = node.getElementsByTagName("text")
            if texte:
                vdm.append({"id": node.getAttribute("id"),
                            "text": texte[0].firstChild.data.replace("\r", " ").replace("\n", " ").replace("&quot;", "\"")})
        dom.unlink()
    return vdm

def vdm_process_cb(data, command, rc, stdout, stderr):
    """ Callback reading HTML data from website. """
    global vdm_stdout, vdm_switch_to_buffer, vdm_hook_process, vdm_key, vdm_oldlist
    if stdout != "":
        vdm_stdout += stdout
    if int(rc) >= 0:
        list = vdm_parse(vdm_stdout)
        if len(list) > 0 and list != vdm_oldlist:
            vdm_buffer_set_title()
            vdm_display(list)
            vdm_oldlist = list[:]
        if vdm_switch_to_buffer:
            weechat.buffer_set(vdm_buffer, "display", "1")
        vdm_switch_to_buffer = False
        vdm_hook_process = ""
    return weechat.WEECHAT_RC_OK

def vdm_buffer_create():
    """ Create VDM buffer. """
    global vdm_buffer
    vdm_buffer = weechat.buffer_search("python", "vdm")
    if vdm_buffer == "":
        vdm_buffer = weechat.buffer_new("vdm",
                                        "vdm_buffer_input", "",
                                        "vdm_buffer_close", "")
    if vdm_buffer != "":
        vdm_buffer_set_title()
        weechat.buffer_set(vdm_buffer, "localvar_set_no_log", "1")
        weechat.buffer_set(vdm_buffer, "time_for_each_line", "0")

def vdm_get(key):
    """ Get some VDMs by launching background process. """
    global vdm_buffer, vdm_hook_process, vdm_key, vdm_stdout, vdm_oldlist
    # open buffer if needed
    if vdm_buffer == "":
        vdm_buffer_create()
    # set language
    if key == "fr" or key == "en":
        weechat.config_set_plugin("lang", key)
        vdm_buffer_set_title()
        return
    # clear buffer
    if key[0] == "*":
        if vdm_buffer != "":
            weechat.buffer_clear(vdm_buffer)
        vdm_oldlist = []
        key = key[1:]
    # previous page
    if key == "-":
        items = vdm_key.split("/", 1)
        if len(items) == 1:
            page = 0
        else:
            page = int(items[1]) - 1
        if page <= 0:
            vdm_key = items[0]
        else:
            vdm_key = "%s/%s" % (items[0], page)
    elif key == "+":
        # next page
        items = vdm_key.split("/", 1)
        if len(items) == 1:
            page = 1
        else:
            page = int(items[1]) + 1
        vdm_key = "%s/%s" % (items[0], page)
    elif key != "r":
        vdm_key = key
    # get data from website, via hook_process
    if vdm_hook_process != "":
        weechat.unhook(vdm_hook_process)
        vdm_hook_process = ""
    vdm_stdout = ""
    url = weechat.config_get_plugin("url") % (vdm_key, weechat.config_get_plugin("lang"))
    vdm_hook_process = weechat.hook_process("url:%s" % url, 10 * 1000, "vdm_process_cb", "")

def vdm_buffer_input(data, buffer, input_data):
    """ Read data from user in VDM buffer. """
    if input_data == "q" or input_data == "Q":
        weechat.buffer_close(buffer)
    else:
        vdm_get(input_data)
    return weechat.WEECHAT_RC_OK

def vdm_buffer_close(data, buffer):
    """ User closed VDM buffer. Oh no, why? """
    global vdm_buffer, vdm_oldlist
    vdm_buffer = ""
    vdm_oldlist = []
    return weechat.WEECHAT_RC_OK

def vdm_cmd(data, buffer, args):
    """ Callback for /vdm command. """
    global vdm_switch_to_buffer
    if weechat.config_get_plugin("auto_switch") == "on":
        vdm_switch_to_buffer = True
    if args != "":
        vdm_get(args)
    else:
        vdm_get("last")
    return weechat.WEECHAT_RC_OK
