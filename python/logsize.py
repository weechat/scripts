# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 by nils_2 <weechatter@arcor.de>
#
# Display size of current logfile in item-bar
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
# This script deletes weechatlog-files by age or size
# YOU ARE USING THIS SCRIPT AT YOUR OWN RISK!
#
# 2012-01-14: nils_2 (freenode.#weechat)
#       0.1 : initial release
#
# How to use:
# add item "logsize" to option "weechat.bar.status.items"
#
# CAVE:
# USE OPTION: plugins.var.python.logsize.display "lines" VERY CAREFULLY
# Very large logfiles will stall script and weechat.
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat
    import os, os.path, stat, time
    from datetime import date, timedelta

except Exception:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()

SCRIPT_NAME     = "logsize"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.1"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "display size of current logfile in item-bar"
OPTIONS         = { "refresh"   : ("60","refresh timer (in seconds)"),
                    "size"      : ("KB","display length in KB/MB/GB/TB. Leave option empty for byte"),
                    "display"   : ("length","could be \"length\", \"lines\" or \"both\". CAVE: Use display option \"lines\" very carefully, large logfiles can stall the script and weechat!!!"),
                    }

hooks           = { "timer": "", "bar_item": "" }

# ================================[ dos ]===============================
def sizecheck(logfile):
    filesize = float(os.path.getsize(logfile))                      # filesize in bytes
    size = "b"
    if OPTIONS["size"].lower() == "kb":
        filesize = "%.2f" % (filesize / 1024)
        size = "K"
    elif OPTIONS["size"].lower() == "mb":
        filesize = "%.2f" % (filesize / 1024 / 1024)
        size = "M"
    elif OPTIONS["size"].lower() == "gb":
        filesize = "%.2f" % (filesize / 1024 / 1024 / 1024)
        size = "G"
    elif OPTIONS["size"].lower() == "tb":
        filesize = "%.2f" % (filesize / 1024 / 1024 / 1024 / 1024)
        size = "T"
    return "%s%s" % (filesize,size)

def read_lines(logfile):
    f = open(logfile,'r')
    lines = 0L
    for line in f.xreadlines():
        lines += 1L
    f.close()
    return "%s %s" % (lines,"lines")

# ================================[ weechat item ]===============================
def show_item (data, item, window):
    logfile = get_logfile()
    output = ''
    if logfile != '':
        if OPTIONS["display"] == 'lines':           # get number of lines in logfile
            output = str(read_lines(logfile))
        elif OPTIONS["display"] == 'length':        # get lenght of logfile
            output = str(sizecheck(logfile))
        elif OPTIONS["display"] == 'both':          # get lines and lenght of log_filename
            output = "%s/%s" % ( str(read_lines(logfile)),str(sizecheck(logfile)) )
    return "%s" % output                            # this line will be printed to item-bar

def get_logfile():
    logfilename = ""
    current_buffer = weechat.current_buffer()
    infolist = weechat.infolist_get('logger_buffer','','')
    while weechat.infolist_next(infolist):
        bpointer = weechat.infolist_pointer(infolist, 'buffer')
        if current_buffer == bpointer:
            logfilename = weechat.infolist_string(infolist, 'log_filename')
            log_enabled = weechat.infolist_integer(infolist, 'log_enabled')
            log_level = weechat.infolist_integer(infolist, 'log_level')
    weechat.infolist_free(infolist)                  # free infolist()
    return logfilename

def item_update(data, remaining_calls):
    global hooks
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ weechat hook ]===============================
def unhook_timer():
    global hooks
    if hooks["timer"] != "":
        weechat.bar_item_remove(hooks["bar_item"])
        weechat.unhook(hooks["timer"])
        hooks["timer"] = ""
        hooks["bar_item"]

def hook_timer():
    global hooks
    hooks["timer"] = weechat.hook_timer(int(OPTIONS["refresh"]) * 1000, 0, 0, 'item_update', '')
    hooks["bar_item"] = weechat.bar_item_new(SCRIPT_NAME, 'show_item','')

    if hooks["timer"] == 0:
        weechat.prnt('',"%s: can't enable %s, hook failed" % (weechat.prefix("error"), SCRIPT_NAME))
        weechat.bar_item_remove(hooks["bar_item"])
        hooks["bar_item"] = ""
        return 0
    weechat.bar_item_update(SCRIPT_NAME)
    return 1

# ================================[ weechat options and description ]===============================
def toggle_refresh(pointer, name, value):
    global hooks
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value

    if option == 'refresh':                                               # option "refresh" changed by user?
        if hooks["timer"] != "":                                          # timer currently running?
            if OPTIONS['refresh'] != "0":                                 # new user setting not zero?
                unhook_timer()
                hook_timer()
            else:
                unhook_timer()                                            # user switched timer off
        elif hooks["timer"] == "":                                        # hook is empty
            if OPTIONS['refresh'] != "0":                                 # option is not zero!
                hook_timer()                                              # install hook
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK
def init_options():
    for option,value in OPTIONS.items():
        if not weechat.config_get_plugin(option):
          weechat.config_set_plugin(option, value[0])
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
# ================================[ main ]===============================
if __name__ == "__main__":
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
      init_options()

      if OPTIONS["refresh"] != 0:
          hook_timer()
          weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )

