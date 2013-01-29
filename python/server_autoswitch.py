# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2013 by nils_2 <weechatter@arcor.de>
#
# cylce to currently used server if you are using merged server buffer
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
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
#
# 2012-01-28: nils_2,(freenode.#weechat)
#       0.3 : adapted to bugfix #31158 and new signal hook_signal("window_switch")
#
# 2012-01-27: nils_2,(freenode.#weechat)
#       0.2 : fix: bug with split windows removed (reported by meingtsla)
#
# 2012-01-22: nils_2,(freenode.#weechat)
#       0.1 : initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "server_autoswitch"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.4"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "cycle to currently used server if you are using merged server buffer"

look_server = ""

def window_switch_cb(data, signal, signal_data):
    bufpointer = weechat.window_get_pointer(signal_data,"buffer")
    buffer_switch_cb(data,signal,bufpointer)
    return weechat.WEECHAT_RC_OK
def buffer_switch_cb(data, signal, signal_data):
    global look_server
    look_server = ""
    look_server = weechat.config_string(weechat.config_get("irc.look.server_buffer"))
    if  look_server == "independent":                                                   # server buffer independent?
        return weechat.WEECHAT_RC_OK                                                    # better remove script, you don't need it.

    if weechat.buffer_get_string(signal_data,'name') != 'weechat':                      # not weechat core buffer
        if (weechat.buffer_get_string(signal_data,'localvar_type') == '') or (weechat.buffer_get_string(signal_data,'localvar_type') == 'server'):
            return weechat.WEECHAT_RC_OK
    elif weechat.buffer_get_string(signal_data,'name') == 'weechat':
        return weechat.WEECHAT_RC_OK

    # buffer is channel or private?
    if (weechat.buffer_get_string(signal_data,'localvar_type') == 'channel') or (weechat.buffer_get_string(signal_data,'localvar_type') == 'private'):
        bufpointer = weechat.window_get_pointer(weechat.current_window(),"buffer")
        servername_from_current_buffer = weechat.buffer_get_string(bufpointer, 'localvar_server')
        name = weechat.buffer_get_string(bufpointer, 'name')
        server_switch(signal_data,servername_from_current_buffer,name)
    return weechat.WEECHAT_RC_OK

def server_switch(signal_data,servername_from_current_buffer,name):
    global look_server
    SERVER = {}

    bufpointer = weechat.window_get_pointer(weechat.current_window(),"buffer")
    servername_current_buffer = servername_from_current_buffer
    if look_server == "merge_with_core":                                                # merge_with_core
        SERVER["weechat"] = "core.weechat"

# get ALL server buffers and save them
    infolist = weechat.infolist_get("buffer","","*server.*")                            # we are only interest in server-buffers
    while weechat.infolist_next(infolist):
        bufpointer = weechat.infolist_pointer(infolist,"pointer")
        server = weechat.infolist_string(infolist, "name")                              # full servername (server.<servername>)
        servername = weechat.infolist_string(infolist, "short_name")                    # get servername from server (without prefix "server")
        active = weechat.infolist_integer(infolist,"active")
        SERVER[servername] = server
        if (active == 1) and (servername_current_buffer != servername):                 # buffer active but not correct server buffer?
            weechat.command(bufpointer,"/input switch_active_buffer")                   # switch server buffer
    weechat.infolist_free(infolist)                                                     # do not forget to free infolist!

# switch though all server and stop at server from current buffer
    i = 0
    while i <= len(SERVER):
        for servername,full_name in list(SERVER.items()):
            bufpointer = weechat.buffer_search("irc","%s" % full_name)                  # search pointer from server buffer
            if bufpointer == "":                                                        # core buffer
                if weechat.buffer_get_integer(weechat.buffer_search_main(),'active') == 1:
                    weechat.command(weechat.buffer_search_main(),"/input switch_active_buffer")
            else:                                                                       # server buffer!
                if (servername != servername_current_buffer) and (weechat.buffer_get_integer(bufpointer,'active') == 1):
                    weechat.command(bufpointer,"/input switch_active_buffer")
                elif (servername == servername_current_buffer) and (weechat.buffer_get_integer(bufpointer,'active') == 1):
                    i = len(SERVER)
                    break
        i += 1
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0
        if int(version) >= 0x00030600:
            weechat.hook_signal("buffer_switch","buffer_switch_cb","")
            weechat.hook_signal("window_switch","window_switch_cb","")
        else:
            weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.6 or higher"))
