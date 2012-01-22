# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 by nils_2 <weechatter@arcor.de>
#
# customize your title/status/input bar for each buffer
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
# 2012-01-20: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re

except Exception:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    quit()

SCRIPT_NAME     = "customize_bar"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.1"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "customize your title/status/input bar for each buffer"

OPTIONS         =  {'default.title'     : 'weechat.bar.title.items',
                    'default.status'    : 'weechat.bar.status.items',
                    'default.input'     : 'weechat.bar.input.items',}
DEFAULT_OPTION  =  {}                                                                   # save default options from weechat.bar.*.items
# ================================[ programm ]===============================
def buffer_switch(data, signal, signal_data):
    full_name = weechat.buffer_get_string(signal_data,'full_name')                      # get full_name of current buffer
    if full_name == '':                                                                 # upps, something totally wrong!
        return weechat.WEECHAT_RC_OK

    for option in OPTIONS.keys():
        option = option.split('.')
        customize_plugin = weechat.config_get_plugin('%s.%s' % (option[1], full_name))  # for example: title.irc.freenode.#weechat
        if customize_plugin:                                                            # option exists
            config_pnt = weechat.config_get('weechat.bar.%s.items' % option[1])
#            current_bar = weechat.config_string(weechat.config_get('weechat.bar.%s.items' % option[1]))
            weechat.config_option_set(config_pnt,customize_plugin,1)                    # set customize_bar
        else:
            current_bar = weechat.config_string(weechat.config_get('weechat.bar.%s.items' % option[1]))
            default_plugin = weechat.config_get_plugin('default.%s' % option[1])        # option we are looking for
            if default_plugin == '':                                                    # default_plugin removed by user?
                weechat.config_set_plugin('default.%s' % option[1],DEFAULT_OPTION[option[1]]) # set default_plugin again!
            if current_bar != default_plugin:
                config_pnt = weechat.config_get('weechat.bar.%s.items' % option[1])
                weechat.config_option_set(config_pnt,default_plugin,1)                  # set customize_bar

    return weechat.WEECHAT_RC_OK

def customize_cmd_cb(data, buffer, args):
    args = args.lower()
    argv = args.split(None)
    if (args == '') or (len(argv) != 2):
        return weechat.WEECHAT_RC_OK
    if argv[1] not in 'title status input':
        return weechat.WEECHAT_RC_OK

    full_name = weechat.buffer_get_string(buffer,'full_name')                           # get full_name of current buffer

    if argv[0] == 'add':
        if weechat.config_get_plugin('%s.%s' % (argv[1],full_name)):
            return weechat.WEECHAT_RC_OK
        else:
            default_plugin = weechat.config_get_plugin('default.%s' % (argv[1]))
            bar = weechat.config_set_plugin('%s.%s' % (argv[1],full_name),default_plugin)  # set default bar
    elif argv[0] == 'del':
        weechat.config_unset_plugin('%s.%s' % (argv[1],full_name))
    return weechat.WEECHAT_RC_OK

def customize_bar_completion_cb(data, completion_item, buffer, completion):
    for option in OPTIONS.keys():
        option = option.split('.')
        weechat.hook_completion_list_add(completion, option[1], 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def shutdown_cb():
    # write back default options to original options, then quit...
    for option in OPTIONS.keys():
        option = option.split('.')
        default_plugin = weechat.config_get_plugin('default.%s' % option[1])
        config_pnt = weechat.config_get('weechat.bar.%s.items' % option[1])
        weechat.config_option_set(config_pnt,default_plugin,1)
    return weechat.WEECHAT_RC_OK
# ================================[ config ]===============================
def init_options():
    # check out if a default item bar exists
    for option,value in OPTIONS.items():
        if not weechat.config_get_plugin(option):
            default_bar = weechat.config_string(weechat.config_get(value))# get original option
            weechat.config_set_plugin(option, default_bar)
            default_option = option.split('.')
            default_bar_value = weechat.config_string(weechat.config_get('weechat.bar.%s.items' % default_option[1]))
            DEFAULT_OPTION[default_option[1]] = default_bar_value
        else:
            default_option = option.split('.')
            default_bar_value = weechat.config_string(weechat.config_get('weechat.bar.%s.items' % default_option[1]))
            DEFAULT_OPTION[default_option[1]] = default_bar_value
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, 'shutdown_cb', ''):
        version = weechat.info_get('version_number', '') or 0
        weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
        'add <title|status|input> || del <title|status|input>',
        'add <title|status|input>: add a (default) customize bar for current buffer\n'
        'del <title|status|input>: delete customize bar for current buffer\n\n'
        'Options:\n'
        '  plugins.var.python.customize_bar.default.title : stores the default items from weechat title bar.\n'
        '  plugins.var.python.customize_bar.default.status: stores the default items from weechat status bar.\n'
        '  plugins.var.python.customize_bar.default.input : stores the default items from weechat input bar.\n'
        '  plugins.var.python.customize_bar.(title|status|input).<full_buffer_name> : stores the customize bar items for this buffer\n\n'
        'CAVE: Do not delete options \"plugins.var.python.customize_bar.default.*\" as long as script is running...\n',
        'add %(plugin_customize_bar) %-|| del %(plugin_customize_bar) %-',
        'customize_cmd_cb', '')
        init_options()
        weechat.hook_signal('buffer_switch','buffer_switch','')
        weechat.hook_completion('plugin_customize_bar', 'customize_bar_completion', 'customize_bar_completion_cb', '')
        weechat.command('','/window refresh')