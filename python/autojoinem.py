# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2017 by nils_2 <weechatter@arcor.de>
#
# add/del channel(s) to/from autojoin option
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
# idea by azizLIGHTS
#
# 2017-01-06: nils_2, (freenode.#weechat)
#       0.6 : fix problem with non existing server (reported by Niols)
# 2016-12-19: nils_2, (freenode.#weechat)
#       0.5 : fix problem with empty autojoin (reported by Caelum)
# 2016-06-05: nils_2, (freenode.#weechat)
#       0.4 : make script python3 compatible
# 2015-11-14: nils_2, (freenode.#weechat)
#       0.3 : fix: problem with (undef) option
# 2014-01-19: nils_2, (freenode.#weechat)
#       0.2 : fix: adding keys to already existing keys failed
# 2013-12-22: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.x
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "autojoinem"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.6"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "add/del channel(s) to/from autojoin option"

OPTIONS         = { 'sorted'        : ('off','channels will be sorted in autojoin-option. if autojoin-option contains channel-keys, this option will be ignored.'),
                  }

def add_autojoin_cmd_cb(data, buffer, args):
    if args == "":                                                                              # no args given. quit
        return weechat.WEECHAT_RC_OK

    argv = args.strip().split(' ')

#    if (len(argv) <= 1):
#        weechat.prnt(buffer,"%s%s: too few arguments." % (weechat.prefix('error'),SCRIPT_NAME))
#        return weechat.WEECHAT_RC_OK

    server = weechat.buffer_get_string(buffer, 'localvar_server')                               # current server
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')                             # current channel
    buf_type = weechat.buffer_get_string(buffer, 'localvar_type')

    # only "add <servername>" given by user
    if (len(argv) == 2):
        weechat.prnt(buffer,"%s%s: invalid number of arguments." % (weechat.prefix('error'),SCRIPT_NAME))
        return weechat.WEECHAT_RC_OK

    # '-key' keyword in command line?
    if '-key' in argv:
        found_key_word = argv.index('-key')
        key_words = argv[int(found_key_word)+1:]
        # don't use "-key" in argv
        argv = argv[:int(found_key_word)]

    # ADD argument
    if (argv[0].lower() == 'add'):
        # add current channel to autojoin. Only option "add" was given..
        if (len(argv) == 1):
            if server == "" or channel == "" or server == channel or buf_type == "" or buf_type != 'channel':
                weechat.prnt(buffer,"%s%s: current buffer is not a channel buffer." % (weechat.prefix('error'),SCRIPT_NAME))
                return weechat.WEECHAT_RC_OK
            list_of_channels, list_of_current_keys = get_autojoin_list(buffer,server)
            # no channels in option!
            if list_of_channels == 1 and list_of_current_keys == 1:
                ptr_config_autojoin = weechat.config_get('irc.server.%s.autojoin' % server)
                rc = weechat.config_option_set(ptr_config_autojoin,channel,1)
                return weechat.WEECHAT_RC_OK
            if channel in list_of_channels:
                weechat.prnt(buffer,"%s%s: channel '%s' already in autojoin for server '%s'" % (weechat.prefix("error"),SCRIPT_NAME,channel,server))
            else:
                # first char of channel '#' ?
                if channel[0] == '#':
                    if '-key' in args and len(key_words) > 1:
                        weechat.prnt(buffer,"%s%s: too many key(s) for given channel(s) " % (weechat.prefix('error'),SCRIPT_NAME))
                        return weechat.WEECHAT_RC_OK
                    elif '-key' in args and len(key_words) == 1:
                        list_of_channels.insert(0,channel)
                        list_of_current_keys = ','.join(key_words)
                        # strip leading ','
                        if list_of_current_keys[0] == ',':
                            list_of_current_keys = list_of_current_keys.lstrip(',')
                    else:
                        list_of_channels.append(channel)

                    if not set_autojoin_list(server,list_of_channels, list_of_current_keys):
                        weechat.prnt(buffer,"%s%s: set new value for option failed..." % (weechat.prefix('error'),SCRIPT_NAME))
        # server and channels given by user
        elif (len(argv) >= 3):
            server = argv[1]
            list_of_channels = argv[2:]
            if '-key' in args and len(list_of_channels) < len(key_words):
                weechat.prnt(buffer,"%s%s: too many key(s) for given channel(s) " % (weechat.prefix('error'),SCRIPT_NAME))
                return weechat.WEECHAT_RC_OK

            list_of_current_channels,list_of_current_keys = get_autojoin_list(buffer,server)
            # autojoin option is empty
            if list_of_current_channels == 1:
                # no channel -> no key!
                list_of_current_keys = ""
                if '-key' in args:
                    list_of_current_keys = ','.join(key_words)
                    # strip leading ','
                    if list_of_current_keys[0] == ',':
                        list_of_current_keys = list_of_current_keys.lstrip(',')
                if not set_autojoin_list(server,list_of_channels, list_of_current_keys):
                    weechat.prnt(buffer,"%s%s: set new value for option failed..." % (weechat.prefix('error'),SCRIPT_NAME))
            else:
                if '-key' in args:
                    j = 0
                    new_keys = []
                    list_of_new_keys = []
                    for i in list_of_channels:
                        if i not in list_of_current_channels and j <= len(key_words):
#                            weechat.prnt(buffer,"channel: %s, channel key is: '%s'" % (i,key_words[j]))
                            list_of_current_channels.insert(j,i)
                            new_keys.insert(j,key_words[j])
                        j += 1
                    missing_channels = list_of_current_channels
                    list_of_new_keys = ','.join(new_keys)
                    if list_of_current_keys:
                        list_of_current_keys = list_of_new_keys + ',' + list_of_current_keys
                    else:
                        list_of_current_keys = list_of_new_keys
                    # strip leading ','
                    if list_of_current_keys[0] == ',':
                        list_of_current_keys = list_of_current_keys.lstrip(',')
                else:
                    # check given channels with channels already set in option
                    missing_channels = get_difference(list_of_channels,list_of_current_channels)
                    missing_channels = list_of_current_channels + missing_channels

                if not set_autojoin_list(server,missing_channels, list_of_current_keys):
                    weechat.prnt(buffer,"%s%s: set new value for option failed..." % (weechat.prefix('error'),SCRIPT_NAME))
        return weechat.WEECHAT_RC_OK

    # DEL argument
    if (argv[0].lower() == 'del'):
        # del current channel from autojoin. Only option "del" was given..
        if (len(argv) == 1):
            if server == "" or channel == "" or server == channel or buf_type == "" or buf_type != 'channel':
                weechat.prnt(buffer,"%s%s: current buffer is not a channel buffer." % (weechat.prefix('error'),SCRIPT_NAME))
                return weechat.WEECHAT_RC_OK
            list_of_channels, list_of_keys = get_autojoin_list(buffer,server)
            # no channels in option, nothing to delete
            if list_of_channels == 1 and list_of_current_keys == 1:
                return weechat.WEECHAT_RC_OK
            if channel not in list_of_channels:
                weechat.prnt(buffer,"%s%s: channel '%s' not found in autojoin for server '%s'" % (weechat.prefix("error"),SCRIPT_NAME,channel,server))
                return weechat.WEECHAT_RC_OK
            else:
                # first char of channel '#' ?
                if channel[0] == '#':
                    channel_key_index = list_of_channels.index(channel)
                    if not list_of_keys:
                        list_of_channels.remove(list_of_channels[channel_key_index])
                        list_of_current_keys = ''
                    else:
                        list_of_keys_tup = list_of_keys.split(",")
                        list_of_current_keys = list_of_keys
                        # channel does not have a key (position of channel > number of keys!)
                        if channel_key_index + 1 > len(list_of_keys_tup):
                            list_of_channels.remove(list_of_channels[channel_key_index])
                        # remove channel and key from autjoin option
                        else:
                            list_of_channels.remove(list_of_channels[channel_key_index])
                            list_of_keys_tup.remove(list_of_keys_tup[channel_key_index])
                            # does a key exists, after removing?
                            if len(list_of_keys_tup) > 0:
                                list_of_current_keys = ','.join(list_of_keys_tup)
                                # strip leading ','
                                if list_of_current_keys[0] == ',':
                                    list_of_current_keys = list_of_current_keys.lstrip(',')
                            else:   # all keys deleted
                                list_of_current_keys = ''

                    # unset option if everything is gone.
                    if not list_of_channels and not list_of_current_keys:
                        ptr_config_autojoin = weechat.config_get('irc.server.%s.autojoin' % server)
                        if ptr_config_autojoin:
                            rc = weechat.config_option_unset(ptr_config_autojoin)
                        return weechat.WEECHAT_RC_OK
                    
                    if not set_autojoin_list(server,list_of_channels, list_of_current_keys):
                        weechat.prnt(buffer,"%s%s: set new value for option failed..." % (weechat.prefix('error'),SCRIPT_NAME))

        # server and channels given by user
        elif (len(argv) >= 3):
            server = argv[1]
            list_of_current_channels,list_of_current_keys = get_autojoin_list(buffer,server)

            # autojoin option is empty
            if list_of_current_channels == 1:
                weechat.prnt(buffer,"%s%s: nothing to delete..." % (weechat.prefix('error'),SCRIPT_NAME))
                return weechat.WEECHAT_RC_OK
            else:
                list_of_channels = args.split(" ")[2:]
                if list_of_current_keys:
                    list_of_current_keys_tup = list_of_current_keys.split(",")
                else:
                    list_of_current_keys_tup = ''

                for i in list_of_channels:
                    # check if given channel is in list of options
                    if not i in list_of_current_channels:
                        continue
                    channel_key_index = list_of_current_channels.index(i)
                    # channel does not have a key (position of channel > number of keys!)
                    if channel_key_index + 1 > len(list_of_current_keys_tup):
                        list_of_current_channels.remove(i)
#                        if len(list_of_current_channels) <= 0:
#                            list_of_current_channels = ''
                    else: # remove channel and key from autjoin option
                        list_of_current_channels.remove(i)
                        list_of_current_keys_tup.remove(list_of_current_keys_tup[channel_key_index])
                        # does an key exists, after removing?
                        if len(list_of_current_keys_tup) > 0:
                            list_of_current_keys = ','.join(list_of_current_keys_tup)
                            # strip leading ','
                            if list_of_current_keys[0] == ',':
                                list_of_current_keys = list_of_current_keys.lstrip(',')
                        else:   # all keys deleted
                            list_of_current_keys = ''

#                for j in list_of_current_channels:
#                    weechat.prnt(buffer,"chan:%s" % j)
#                for j in list_of_current_keys_tup:
#                    weechat.prnt(buffer,"key :%s" % j)

                # unset option if everything is gone.
                if not list_of_current_channels and not list_of_current_keys:
                    ptr_config_autojoin = weechat.config_get('irc.server.%s.autojoin' % server)
                    if ptr_config_autojoin:
                        rc = weechat.config_option_unset(ptr_config_autojoin)
                    return weechat.WEECHAT_RC_OK

                if not set_autojoin_list(server,list_of_current_channels, list_of_current_keys):
                    weechat.prnt(buffer,"%s%s: set new value for option failed..." % (weechat.prefix('error'),SCRIPT_NAME))

    return weechat.WEECHAT_RC_OK

def get_difference(list1, list2):
    return list(set(list1).difference(set(list2)))

# returns a list of channels and a list of keys
# 1 = something failed, 0 = channel found
def get_autojoin_list(buffer,server):
    ptr_config_autojoin = weechat.config_get('irc.server.%s.autojoin' % server)
    # option not found! server does not exist
    if not ptr_config_autojoin:
        weechat.prnt("","%s%s: server '%s' does not exist." % (weechat.prefix('error'),SCRIPT_NAME,server))
        return 1,1

    # get value from autojoin option
    channels = weechat.config_string(ptr_config_autojoin)
    if not channels:
        return 1,1

    # check for keys
    if len(re.findall(r" ", channels)) == 0:
        list_of_channels = channels.split(",")
        list_of_keys = []
    elif len(re.findall(r" ", channels)) == 1:
        list_of_channels2,list_of_keys = channels.split(" ")
        list_of_channels = list_of_channels2.split(",")
    else:
        weechat.prnt("","%s%s: irc.server.%s.autojoin not valid..." % (weechat.prefix('error'),SCRIPT_NAME,server))
        return 1,1

    return list_of_channels, list_of_keys

def set_autojoin_list(server,list_of_channels, list_of_keys):
    ptr_config_autojoin = weechat.config_get('irc.server.%s.autojoin' % server)
    if not ptr_config_autojoin:
        return 0

    if OPTIONS['sorted'].lower() == 'on' and not list_of_keys:
        # no keys, sort the channel-list
        channels = '%s' % ','.join(sorted(list_of_channels))
    else:
        # don't sort channel-list with given key
        channels = '%s' % ','.join(list_of_channels)

    # strip leading ','
    if channels[0] == ',':
        channels = channels.lstrip(',')

    # add keys to list of channels
    if list_of_keys:
        channels = '%s %s' % (channels,list_of_keys)

    rc = weechat.config_option_set(ptr_config_autojoin,channels,1)
    if not rc:
        return 0
    return 1

def autojoinem_completion_cb(data, completion_item, buffer, completion):
#    server = weechat.buffer_get_string(buffer, 'localvar_server')                               # current buffer
    input_line = weechat.buffer_get_string(buffer, 'input')

    # get information out of the input_line
    argv = input_line.strip().split(" ",3)
    if (len(argv) >= 3 and argv[1] == 'del'):
        server = argv[2]

    list_of_channels,list_of_keys = get_autojoin_list(buffer,server)
    if list_of_channels == 1:
        return weechat.WEECHAT_RC_OK

    if (len(argv) >= 4 and argv[1] == 'del'):
        list_of_current_channels = argv[3].split(' ')
        missing_channels = get_difference(list_of_channels,list_of_current_channels)
        if not missing_channels:
            return weechat.WEECHAT_RC_OK
        list_of_channels = missing_channels

    for i, elem in enumerate(list_of_channels):
        weechat.hook_completion_list_add(completion, list_of_channels[i], 0, weechat.WEECHAT_LIST_POS_END)
    return weechat.WEECHAT_RC_OK
# ================================[ weechat options & description ]===============================
def init_options():
    for option,value in OPTIONS.items():
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    return weechat.WEECHAT_RC_OK
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0
        weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
                             'add <server> [<channel1>[ <channel2>...]] | [-key <channelkey> [<channelkey>...]] ||'
                             'del <server> [<channel1>[ <channel2>...]]',
                             'add <server> <channel>: add channel to irc.server.<servername>.autojoin\n'
                             '     -key <channelkey>: name of channelkey\n'
                             'del <server> <channel>: del channel from irc.server.<servername>.autojoin\n'
                             '\n'
                             'Examples:\n'
                             ' add current channel to corresponding server option:\n'
                             '  /' + SCRIPT_NAME + ' add\n'
                             ' add all channels from all server to corresponding server option:\n'
                             '  /allchan /' + SCRIPT_NAME + ' add\n'
                             ' add channel #weechat to autojoin option on server freenode:\n'
                             '  /' + SCRIPT_NAME + ' add freenode #weechat\n'
                             ' add channel #weechat and #weechat-de to autojoin option on server freenode, with channel key for channel #weechat:\n'
                             '  /' + SCRIPT_NAME + ' add freenode #weechat #weechat-de -key my_channel_key\n'
                             ' del channels #weechat and #weechat-de from autojoin option on server freenode:\n'
                             '  /' + SCRIPT_NAME + ' del freenode #weechat #weechat-de',
                             'add %(irc_servers) %(irc_server_channels)|%*||'
                             'del %(irc_servers) %(plugin_autojoinem)|%*',
                             'add_autojoin_cmd_cb', '')

        init_options()
        weechat.hook_completion('plugin_autojoinem', 'autojoin_completion', 'autojoinem_completion_cb', '')
        weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')

#        if int(version) >= 0x00030600:
#        else:
#            weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.6 or higher"))
#            weechat.command("","/wait 1ms /python unload %s" % SCRIPT_NAME)
