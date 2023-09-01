# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2018 by nils_2 <weechatter@arcor.de>, Filip H.F. "FiXato" Slagter <fixato+weechat@gmail.com>
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
# 2023-08-01: nils_2 (libera.#weechat)
#     0.6.1 : fix a timing problem when joining autojoin-channels (reported by thecdnhermit)
#
# 2021-05-05: Sébastien Helleu <flashcode@flashtux.org>
#       0.6 : add compatibility with XDG directories (WeeChat >= 3.2)
#
# 2018-08-08: nils_2, (freenode.#weechat)
#       0.5 : fix TypeError with python3.6
#
# 2017-04-14: nils_2 & FiXato, (freenode.#weechat)
#       0.4 : big rewrite:
#           : added extra hooks:
#           - query buffers are now also stored when opening/closing queries
#           - queries only restored on connect; no longer on every reconnect
#           : current buffer position is retained
#           : manual saving of query list (https://github.com/weechat/scripts/issues/196)
#
# 2015-02-27: nils_2, (freenode.#weechat)
#       0.3 : make script consistent with "buffer_switch_autojoin" option (idea haasn)
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
SCRIPT_VERSION  = '0.6.1'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'save and restore query buffers after /quit and on open/close of queries'
DEBUG           = False

queryman_filename = 'queryman.txt'
servers_opening = set([])
servers_closing = set([])
stored_query_buffers_per_server = {}

# ================================[ callback ]===============================
# signal_data = buffer pointer
def buffer_closing_signal_cb(data, signal, signal_data):
    global servers_closing

    buf_type = weechat.buffer_get_string(signal_data,'localvar_type')
    # When closing a server buffer, save all buffers
    if buf_type == 'server':
        # Prevent closing private buffers on this server, from triggering saving.
        servers_closing.add(weechat.buffer_get_string(signal_data, 'localvar_server'))

        # # FIXME: This shouldn't be necessary, as buffers are already save when opened/closed
        # reset_stored_query_buffers()
        # save_stored_query_buffers_to_file()
    # Only save the query buffers
    elif buf_type == 'private':
        server_name = weechat.buffer_get_string(signal_data, 'localvar_server')
        # Don't trigger when all buffer's closing because its server buffer is closing
        if server_name not in servers_closing:
            channel_name = weechat.buffer_get_string(signal_data, 'localvar_channel')
            remove_channel_from_stored_list(server_name, channel_name)
            save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

def quit_signal_cb(data, signal, signal_data):
    reset_stored_query_buffers()
    save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

# signal_data = buffer pointer
def irc_pv_opened_cb(data, signal, signal_data):
    server_name = weechat.buffer_get_string(signal_data, 'localvar_server')
    channel_name = weechat.buffer_get_string(signal_data, 'localvar_channel')
    add_channel_to_stored_list(server_name, channel_name)
    save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

# signal_data = server name
def remove_server_from_servers_closing_cb(data, signal, signal_data):
    global servers_closing
    if signal_data in servers_closing:
        servers_closing.remove(signal_data)
    return weechat.WEECHAT_RC_OK

# signal_data = buffer pointer
def irc_server_opened_cb(data, signal, signal_data):
    global servers_opening

    server_name = weechat.buffer_get_string(signal_data, 'localvar_server')
    servers_opening.add(server_name)
    return weechat.WEECHAT_RC_OK

# signal_data = servername
def irc_server_connected_signal_cb(data, signal, signal_data):
    global servers_opening

    # Only reopen the query buffers if the server buffer was recently opened
    if signal_data in servers_opening:
        open_stored_query_buffers_for_server(signal_data)
        servers_opening.remove(signal_data)

    return weechat.WEECHAT_RC_OK

# ================================[ file ]===============================
def get_filename_with_path():
    global queryman_filename
    path = weechat.info_get("weechat_data_dir", "") \
        or weechat.info_get("weechat_dir", "")
    return os.path.join(path,queryman_filename)

# ======== [ Stored Query Buffers List ] ==========
def get_stored_list_of_query_buffers():
    global stored_query_buffers_per_server

    filename = get_filename_with_path()
    stored_query_buffers_per_server = {}

    if os.path.isfile(filename):
        f = open(filename, 'r')
        for line in f:
            server_name,nick = line.strip().split(' ')
            stored_query_buffers_per_server.setdefault(server_name, set([]))
            stored_query_buffers_per_server[server_name].add(nick)
        f.close()
    else:
        debug_print('Error loading query buffer from "%s"' % filename)
    return stored_query_buffers_per_server

def remove_channel_from_stored_list(server_name, channel_name):
    global stored_query_buffers_per_server

    if server_name in stored_query_buffers_per_server and channel_name in stored_query_buffers_per_server[server_name]:
        stored_query_buffers_per_server[server_name].remove(channel_name)
        if not len(stored_query_buffers_per_server[server_name]):
            stored_query_buffers_per_server.pop(server_name, None)

def add_channel_to_stored_list(server_name, channel_name):
    global stored_query_buffers_per_server

    if server_name not in stored_query_buffers_per_server:
        stored_query_buffers_per_server[server_name] = set([])
    if channel_name not in stored_query_buffers_per_server[server_name]:
        stored_query_buffers_per_server[server_name].add(channel_name)

def open_query_buffer(server_name, nick):
    starting_buffer = weechat.current_buffer()
    noswitch = ""
    switch_autojoin = weechat.config_get("irc.look.buffer_switch_autojoin")
    if not weechat.config_boolean(switch_autojoin):
        noswitch = "-noswitch"
    weechat.command('','/wait 1 /query %s -server %s %s' % ( noswitch, server_name, nick ))
    weechat.buffer_set(starting_buffer, 'display', 'auto')

def open_stored_query_buffers_for_server(server_connected):
    global stored_query_buffers_per_server

    if server_connected in stored_query_buffers_per_server:
        for nick in stored_query_buffers_per_server[server_connected].copy():
            open_query_buffer(server_connected, nick)

def get_current_query_buffers():
    stored_query_buffers_per_server = {}

    ptr_infolist_buffer = weechat.infolist_get('buffer', '', '')
    while weechat.infolist_next(ptr_infolist_buffer):
        ptr_buffer = weechat.infolist_pointer(ptr_infolist_buffer,'pointer')

        buf_type = weechat.buffer_get_string(ptr_buffer, 'localvar_type')
        if buf_type == 'private':
            server_name = weechat.buffer_get_string(ptr_buffer, 'localvar_server')
            channel_name = weechat.buffer_get_string(ptr_buffer, 'localvar_channel')

            stored_query_buffers_per_server.setdefault(server_name, set([]))
            stored_query_buffers_per_server[server_name].add(channel_name)
    weechat.infolist_free(ptr_infolist_buffer)

    return stored_query_buffers_per_server

def reset_stored_query_buffers():
    global stored_query_buffers_per_server
    stored_query_buffers_per_server = get_current_query_buffers()


def remove_data_file():
    filename = get_filename_with_path()
    if os.path.isfile(filename):
        os.remove(filename)

def save_stored_query_buffers_to_file():
    global stored_query_buffers_per_server

    filename = get_filename_with_path()
    if len(stored_query_buffers_per_server):
        debug_print("Storing %s servers:" % len(stored_query_buffers_per_server))
        try:
            f = open(filename, 'w')
            for (server_name, channels) in stored_query_buffers_per_server.items():
                debug_print("Storing %s channels in server %s" % (len(channels), server_name))
                for channel_name in channels:
                    line = "%s %s" % (server_name,channel_name)
                    debug_print(' - %s' % line)
                    f.write("%s\n" % line)
            f.close()
        except:
            print_error('Error writing query buffer to "%s"' % filename)
            raise
    else:       # no query buffer(s). remove file
        debug_print("No stored query buffers; removing data file")
        remove_data_file()
    return

def print_error(message):
    weechat.prnt('','%s%s: %s' % (weechat.prefix('error'), SCRIPT_NAME, message))

def debug_print(message):
    if not DEBUG:
        return
    weechat.prnt('','DEBUG/%s: %s' % (SCRIPT_NAME, message))

def hook_command_cb(data, buffer, args):
    if args == "":                                                                              # no args given. quit
        return weechat.WEECHAT_RC_OK
    argv = args.strip().split(" ")
    if argv[0].lower() == 'save':
        save_stored_query_buffers_to_file()
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0
        if int(version) >= 0x00030700:
            weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
            'save',
            'save : manual saving of the query list\n',
            '',
            'hook_command_cb', '')

            stored_query_buffers_per_server = get_stored_list_of_query_buffers()
            for (server_name, channels) in get_current_query_buffers().items():
                # Reopen the buffers for the channels in the servers we already have open:
                open_stored_query_buffers_for_server(server_name)

                stored_query_buffers_per_server.setdefault(server_name, set([]))
                debug_print("Already have %s channels for server %s: %s" % (len(stored_query_buffers_per_server[server_name]), server_name, ','.join(stored_query_buffers_per_server[server_name])))
                debug_print("Adding: %s" % channels)
                stored_query_buffers_per_server[server_name].update(channels)
                debug_print("Now have %s channels for server %s: %s" % (len(stored_query_buffers_per_server[server_name]), server_name, ','.join(stored_query_buffers_per_server[server_name])))
            save_stored_query_buffers_to_file()
            weechat.hook_signal('quit', 'quit_signal_cb', '')
#            weechat.hook_signal('relay_client_disconnected', 'quit_signal_cb', '')
#            weechat.hook_signal('relay_client_connected', 'irc_server_connected_signal_cb', '')
            weechat.hook_signal('irc_server_opened', 'irc_server_opened_cb', '')
            weechat.hook_signal('irc_server_connected', 'irc_server_connected_signal_cb','')
            weechat.hook_signal('irc_server_disconnected', 'remove_server_from_servers_closing_cb', '')

            # TODO: make these triggers optional?
            weechat.hook_signal('irc_pv_opened', 'irc_pv_opened_cb', '')
            weechat.hook_signal('buffer_closing', 'buffer_closing_signal_cb', '')
