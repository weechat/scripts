# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2015 by nils_2 <weechatter@arcor.de>
#
# save channel key from protected channel(s) to autojoin or secure data
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
# idea by freenode.elsae
#
# 2015-05-09: nils_2, (freenode.#weechat)
#       0.3 : fix: ValueError (reported by: Darpa)
#
# 2014-12-20: nils_2, (freenode.#weechat)
#       0.2 : add option "add" to automatically add channel/key to autojoin option after a /join (idea by Prezident)
#
# 2013-10-03: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.2
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re

except Exception:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()

SCRIPT_NAME     = "autosavekey"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.3"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "save channel key from protected channel(s) to autojoin or secure data"

OPTIONS         = { 'mute'        : ('off','execute command silently, only error messages will be displayed.'),
                    'secure'      : ('off','change channel key in secure data.'),
                    'add'         : ('off','adds channel and key to autojoin list on /join, if channel/key does not already exists'),
                  }
# /join #channel key
# signal = freenode,irc_raw_in_324
# signal_data = :asimov.freenode.net 324 nick #channel +modes key
def irc_raw_in_324_cb(data, signal, signal_data):
    parsed = get_hashtable(signal_data)
    server = signal.split(',',1)[0]
    argv = parsed['arguments'].split(" ")

    # buffer without channel key
    if len(argv) < 4:
        return weechat.WEECHAT_RC_OK

    channel = argv[1]
    new_key = argv[3]

    autojoin_list = get_autojoin(server)
    if not autojoin_list:
        return weechat.WEECHAT_RC_OK

    # check autojoin for space
    if len(re.findall(r" ", autojoin_list)) > 1:
        weechat.prnt('', '%s%s: autojoin format for server "%s" invalid (two or more spaces).' % (weechat.prefix('error'),SCRIPT_NAME,server) )
        return weechat.WEECHAT_RC_OK

    # no keylist, only channels in autojoin option
    if len(re.findall(r" ", autojoin_list)) == 0:
        argv_channels = autojoin_list.split(',')
        argv_keys = []
    else:
        # split autojoin option to a channel and a key list
        arg_channel,arg_keys = autojoin_list.split(' ')
        argv_channels = arg_channel.split(',')
        argv_keys = arg_keys.split(',')

    # check channel position
    try:
        channel_position = argv_channels.index(channel)
    except ValueError:
        channel_position = -1

    sec_data = 0
    # does buffer already exist in autojoin list?
    if channel_position >= 0:
        # remove channel from list
        argv_channels.pop(channel_position)
        # check if there is at least one key in list
        if len(argv_keys) >= 1:
            # check channel position and number of keys
            if channel_position <= len(argv_keys):
                # remove key from list
                sec_data = check_key_for_secure(argv_keys,channel_position)
                sec_data_name = argv_keys[channel_position][11:-1]
                argv_keys.pop(channel_position)
    else:
        if OPTIONS['add'].lower() == 'off':
            return weechat.WEECHAT_RC_OK

    # add channel and key at first position
    argv_channels.insert(0, channel)
    argv_keys.insert(0,new_key)


    # check weechat version and if secure option is on and secure data will be used for this key?
    if int(version) >= 0x00040200 and OPTIONS['secure'].lower() == 'on' and sec_data == 1:
        weechat.command('','%s/secure set %s %s' % (use_mute(),sec_data_name,new_key))
    else:
        if sec_data == 1:
            weechat.prnt('', '%s%s: key for channel "%s.%s" not changed! option "plugins.var.python.%s.secure" is off and you are using secured data for key.' % (weechat.prefix('error'),SCRIPT_NAME,server,channel,SCRIPT_NAME) )
            return weechat.WEECHAT_RC_OK
        new_joined_option = '%s %s' % (','.join(argv_channels),','.join(argv_keys))
        save_autojoin_option(server,new_joined_option)
    return weechat.WEECHAT_RC_OK

# replace an already existing channel key with an new one
# when OP changes channel key
def irc_raw_in_mode_cb(data, signal, signal_data):
    parsed = get_hashtable(signal_data)

    server = signal.split(',',1)[0]
    argv = parsed['arguments'].split(" ")

    if argv[1] != "+k":
        return weechat.WEECHAT_RC_OK

    channel = argv[0]
    new_key = argv[2]

    add_key_to_list(server,channel,new_key)
    return weechat.WEECHAT_RC_OK

def add_key_to_list(server,channel,new_key):
    autojoin_list = get_autojoin(server)
    if not autojoin_list:
        return weechat.WEECHAT_RC_OK

    # check autojoin for space
    if len(re.findall(r" ", autojoin_list)) == 0:
        weechat.prnt('', '%s%s: no password(s) set in autojoin for server "%s".' % (weechat.prefix('error'),SCRIPT_NAME,server) )
        return weechat.WEECHAT_RC_OK
    if len(re.findall(r" ", autojoin_list)) > 1:
        weechat.prnt('', '%s%s: autojoin format for server "%s" invalid (two or more spaces).' % (weechat.prefix('error'),SCRIPT_NAME,server) )
        return weechat.WEECHAT_RC_OK


    # split autojoin option to a channel and a key list
    arg_channel,arg_keys = autojoin_list.split(' ')
    argv_channels = arg_channel.split(',')
    argv_keys = arg_keys.split(',')

    # search for channel name in list of channels and get position
    if channel in argv_channels:
        channel_pos_in_list = argv_channels.index(channel)
        # enough keys in list? list counts from 0!
        if channel_pos_in_list + 1 > len(argv_keys):
            weechat.prnt('', '%s%s: not enough keys in list or channel position is not valid. check out autojoin option for server "%s".' % (weechat.prefix('error'),SCRIPT_NAME,server) )
            return weechat.WEECHAT_RC_OK

        sec_data = check_key_for_secure(argv_keys,channel_pos_in_list)

        # check weechat version and if secure option is on and secure data will be used for this key?
        if int(version) >= 0x00040200 and OPTIONS['secure'].lower() == 'on' and sec_data == 1:
            sec_data_name = argv_keys[channel_pos_in_list][11:-1]
            weechat.command('','%s/secure set %s %s' % (use_mute(),sec_data_name,new_key))
        else:
            if sec_data == 1:
                weechat.prnt('', '%s%s: key for channel "%s.%s" not changed! option "plugins.var.python.%s.secure" is off and you are using secured data for key.' % (weechat.prefix('error'),SCRIPT_NAME,server,channel,SCRIPT_NAME) )
                return weechat.WEECHAT_RC_OK
            argv_keys[channel_pos_in_list] = new_key
            new_joined_option = '%s %s' % (','.join(argv_channels),','.join(argv_keys))
            save_autojoin_option(server,new_joined_option)
    return weechat.WEECHAT_RC_OK

def get_hashtable(string):
    parsed = weechat.info_get_hashtable('irc_message_parse', dict(message=string))
    try:
        parsed['message'] = parsed['arguments'].split(' :', 1)[1]
    except:
        parsed['message'] = ""
    return parsed

def get_autojoin(server):
    return weechat.config_string(weechat.config_get('irc.server.%s.autojoin' % server))

def find_element_in_list(element,list_element):
        try:
            index_element=list_element.index(element)
            return index_element
        except ValueError:
            return -1

def save_autojoin_option(server,new_joined_option):
    weechat.command('','%s/set irc.server.%s.autojoin %s' % (use_mute(),server,new_joined_option))

def use_mute():
    use_mute = ''
    if OPTIONS['mute'].lower() == 'on':
        use_mute = '/mute '
    return use_mute

# check key for "${sec.data."
def check_key_for_secure(argv_keys,position):
    sec_data = 0
    if argv_keys[position][0:11] == '${sec.data.':
        sec_data = 1
    return sec_data
# ================================[ weechat options & description ]===============================
def init_options():
    for option,value in OPTIONS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0

        if int(version) >= 0x00030200:
            init_options()
            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
            weechat.hook_signal("*,irc_raw_in_mode","irc_raw_in_mode_cb","")
            weechat.hook_signal("*,irc_raw_in_324","irc_raw_in_324_cb","")
        else:
            weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.2 or higher"))
            weechat.command("","/wait 1ms /python unload %s" % SCRIPT_NAME)
