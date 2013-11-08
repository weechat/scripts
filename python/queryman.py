# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by nils_2 <weechatter@arcor.de>
#
# save and restore query buffers after /quit
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
# idea by lasers@freenode.#weechat
#
# 2013-11-07: nils_2, (freenode.#weechat)
#       0.2 : fix file not found error (reported by calcifea)
#           : make script compatible with Python 3.x
#
# 2013-07-26: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# script will create a config file (~./weechat/queryman.txt)
# format: "servername nickname" (without "")
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re,os

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = 'queryman'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.2'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'save and restore query buffers after /quit'

query_buffer_list = []
queryman_filename = 'queryman.txt'

# ================================[ callback ]===============================
def quit_signal_cb(data, signal, signal_data):
    save_query_buffer_to_file()
    return weechat.WEECHAT_RC_OK

# signal_data contains servername
def irc_server_connected_signal_cb(data, signal, signal_data):
    load_query_buffer_irc_server_opened(signal_data)
    return weechat.WEECHAT_RC_OK

# ================================[ file ]===============================
def get_filename_with_path():
    global queryman_filename
    path = weechat.info_get("weechat_dir", "")
    return os.path.join(path,queryman_filename)

def load_query_buffer_irc_server_opened(server_connected):
    global query_buffer_list

    filename = get_filename_with_path()

    if os.path.isfile(filename):
        f = open(filename, 'rb')
        for line in f:
            servername,nick = line.split(' ')
            if servername == server_connected:
                weechat.command('','/query -server %s %s' % ( servername,nick ))
        f.close()
    else:
        weechat.prnt('','%s%s: Error loading query buffer from "%s"' % (weechat.prefix('error'), SCRIPT_NAME, filename))

def save_query_buffer_to_file():
    global query_buffer_list

    ptr_infolist_buffer = weechat.infolist_get('buffer', '', '')

    while weechat.infolist_next(ptr_infolist_buffer):
        ptr_buffer = weechat.infolist_pointer(ptr_infolist_buffer,'pointer')

        type = weechat.buffer_get_string(ptr_buffer, 'localvar_type')
        if type == 'private':
            server = weechat.buffer_get_string(ptr_buffer, 'localvar_server')
            channel = weechat.buffer_get_string(ptr_buffer, 'localvar_channel')
            query_buffer_list.insert(0,"%s %s" % (server,channel))

    weechat.infolist_free(ptr_infolist_buffer)

    filename = get_filename_with_path()

    if len(query_buffer_list):
        try:
            f = open(filename, 'w')
            i = 0
            while i < len(query_buffer_list):
                f.write('%s\n' % query_buffer_list[i])
                i = i + 1
            f.close()
        except:
            weechat.prnt('','%s%s: Error writing query buffer to "%s"' % (weechat.prefix('error'), SCRIPT_NAME, filename))
            raise
    else:       # no query buffer(s). remove file
        if os.path.isfile(filename):
            os.remove(filename)
    return

# ================================[ main ]===============================
if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0
        if int(version) >= 0x00030700:
            weechat.hook_signal('quit', 'quit_signal_cb', '')
            weechat.hook_signal('irc_server_connected', 'irc_server_connected_signal_cb', '')
