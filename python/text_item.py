# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2019 by nils_2 <weechatter@arcor.de>
#
# add a plain text or evaluated content to item bar
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
# 2019-05-23: FlashCode, (freenode.#weechat)
#       0.9 : fix eval_expression() for split windows
#
# 2018-08-18: nils_2, (freenode.#weechat)
#       0.8 : add new option "interval"
#
# 2017-08-23: nils_2, (freenode.#weechat)
#     0.7.1 : improve /help text
#
# 2017-08-19: nils_2, (freenode.#weechat)
#       0.7 : add type "!all", internal changes
#
# 2016-12-12: nils_2, (freenode.#weechat)
#       0.6 : fix problem with multiple windows (reported by Ram-Z)
#
# 2016-09-15: nils_2, (freenode.#weechat)
#       0.5 : add /help text (suggested by gb)
#
# 2014-05-19: nils_2, (freenode.#weechat)
#       0.4 : evaluate content of item (suggested by FlashCode)
#
# 2013-06-27: nils_2, (freenode.#weechat)
#       0.3 : fix: bug with root bar
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.2 : make script compatible with Python 3.x
#
# 2012-12-23: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.0
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

# TODO
# plugins.var.python.text_item.<item_name>.enabled
# plugins.var.python.text_item.<item_name>.type
# plugins.var.python.text_item.<item_name>.signal
# plugins.var.python.text_item.<item_name>.text
# plugins.var.python.text_item.<item_name>.interval

try:
    import weechat,re

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "text_item"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.9"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "add a plain text or evaluated content to item bar"

# regexp to match ${color} tags
regex_color=re.compile('\$\{([^\{\}]+)\}')

hooks = {}
TIMER = None

settings = {
        'interval': ('0', 'How often (in seconds) to force an update of all items. 0 means deactivated'),
}
# ================================[ hooks ]===============================
def add_hook(signal, item):
    global hooks
    # signal already exists?
    if signal in hooks:
        return
    hooks[item] = weechat.hook_signal(signal, "bar_item_update_cb", "")

def unhook(hook):
    global hooks
    if hook in hooks:
        weechat.unhook(hooks[hook])
        del hooks[hook]

def toggle_refresh_cb(pointer, name, value):
    option_name = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]      # get optionname

    # check for timer hook
    if name.endswith(".interval"):
        set_timer()
        return weechat.WEECHAT_RC_OK

    # option was removed? remove bar_item from struct
    if not weechat.config_get_plugin(option_name):
        ptr_bar = weechat.bar_item_search(option_name)
        if ptr_bar:
            weechat.bar_item_remove(ptr_bar)
        return weechat.WEECHAT_RC_OK

    # check if option is new or changed
    if not weechat.bar_item_search(option_name):
        weechat.bar_item_new(option_name,'update_item',option_name)

    weechat.bar_item_update(option_name)
    return weechat.WEECHAT_RC_OK

def set_timer():
    # Update timer hook with new interval. 0 means deactivated
    global TIMER
    if TIMER:
        weechat.unhook(TIMER)
    if int(weechat.config_get_plugin('interval')) >= 1:
        TIMER = weechat.hook_timer(int(weechat.config_get_plugin('interval')) * 1000,0, 0, "timer_dummy_cb", '')

def timer_dummy_cb(data, remaining_calls):
    # hook_timer() has two arguments, hook_signal() needs three arguments
    bar_item_update_cb("","","")
    return weechat.WEECHAT_RC_OK

# ================================[ items ]===============================
def create_bar_items():
    ptr_infolist_option = weechat.infolist_get('option','','plugins.var.python.' + SCRIPT_NAME + '.*')

    if not ptr_infolist_option:
        return

    while weechat.infolist_next(ptr_infolist_option):
        option_full_name = weechat.infolist_string(ptr_infolist_option, 'full_name')
        option_name = option_full_name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]      # get optionname

        if weechat.bar_item_search(option_name):
            weechat.bar_item_update(option_name)
        else:
            weechat.bar_item_new(option_name,'update_item',option_name)
        weechat.bar_item_update(option_name)

    weechat.infolist_free(ptr_infolist_option)

def update_item (data, item, window):
    if not data:
        return ""

    # window empty? root bar!
    if not window:
        window = weechat.current_window()

    value = weechat.config_get_plugin(data)
    if not value:
        return ""

    value = check_buffer_type(window, data, value)

    return substitute_colors(value,window)

# update item from weechat.hook_signal()
def bar_item_update_cb(signal, callback, callback_data):
    ptr_infolist_option = weechat.infolist_get('option','','plugins.var.python.' + SCRIPT_NAME + '.*')

    if not ptr_infolist_option:
        return

    while weechat.infolist_next(ptr_infolist_option):
        option_full_name = weechat.infolist_string(ptr_infolist_option, 'full_name')
        option_name = option_full_name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]      # get optionname
        if option_name == "interval":
            continue

        # check if item exists in a bar and if we have a hook for it
        if weechat.bar_item_search(option_name) and option_name in hooks:
            weechat.bar_item_update(option_name)

    weechat.infolist_free(ptr_infolist_option)

    return weechat.WEECHAT_RC_OK


# ================================[ subroutines ]===============================
def substitute_colors(text,window):
    if int(version) >= 0x00040200:
        bufpointer = weechat.window_get_pointer(window,"buffer")
        return weechat.string_eval_expression(text, {"window": window, "buffer": bufpointer}, {}, {})
    # substitute colors in output
    return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

def check_buffer_type(window, data, value):
    bufpointer = weechat.window_get_pointer(window,"buffer")
    if bufpointer == "":
        return ""

    value = value.split(' ', 1)
    if len(value) <= 1:
        return ""

    # format is : buffer_type (channel,server,private,all) | signal (e.g: buffer_switch)
    channel_type_and_signal = value[0]
    if channel_type_and_signal.find('|') >= 0:
        channel_type = channel_type_and_signal[0:channel_type_and_signal.find("|")]
        signal_type = channel_type_and_signal[channel_type_and_signal.find("|")+1:]
        unhook(data)
        add_hook(signal_type, data)
    else:
        channel_type = value[0]

    value = value[1]

    if channel_type == 'all' or weechat.buffer_get_string(bufpointer,'localvar_type') == channel_type:
        return value
    if channel_type == '!all':
        a = ["channel","server","private"]
        if weechat.buffer_get_string(bufpointer,'localvar_type') in a:
            return value
    return ""

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,'',''):
            weechat.hook_command(SCRIPT_NAME,SCRIPT_DESC,
                        '',
                        'How to use:\n'
                        '===========\n'
                        'Template:\n'
                        '/set plugins.var.python.text_item.<item_name> <type>|<signal> <${color:name/number}><text>\n\n'
                        '   type : channel, server, private, all (all kind of buffers e.g. /color, /fset...) and !all (channel, server and private buffer)\n'
                        '   (see: /buffer localvar)\n\n'
                        '   signal (eg.): buffer_switch, buffer_closing, print, mouse_enabled\n'
                        '   (for a list of all possible signals, see API doc weechat_hook_signal())\n'
                        '\n'
                        'You can activate a timer hook() to force an upgrade of all items in a given period of time, for example using an item that have to be\n'
                        'updated every second (e.g. watch)\n'
                        '\n'
                        'Examples:\n'
                        'creates an option for a text item named "nick_text". The item will be created for "channel" buffers. '
                        'The text displayed in the status-bar is "Nicks:" (yellow colored!):\n'
                        '   /set plugins.var.python.text_item.nick_text "channel ${color:yellow}Nicks:"\n\n'
                        'now you have to add the item "nick_text" to the bar.items (use auto-completion or iset.pl!)\n'
                        '   /set weechat.bar.status.items nick_text\n\n'
                        'creates an option to display the terminal width and height in an item bar. item will be updated on signal "signal_sigwinch":\n'
                        '   /set plugins.var.python.text_item.dimension "all|signal_sigwinch width: ${info:term_width} height: ${info:term_height}"\n'
                        'creates an option to display the status from "/filter toggle" and "/filter toggle @" command, item name is "filter_item":\n'
                        '   /set plugins.var.python.text_item.filter_item "!all|*filters* ${if:${info:filters_enabled}==1?${color:yellow}F:${color:243}F}${if:${buffer.filter}==1?${color:yellow}@:${color:243}@}"\n',
                        '',
                        '',
                        '')
            version = weechat.info_get("version_number", "") or 0

            for option, default_desc in settings.items():
                if not weechat.config_is_set_plugin(option):
                    weechat.config_set_plugin(option, default_desc[0])
                if int(version) >= 0x00030500:
                    weechat.config_set_desc_plugin(option, default_desc[1])

            set_timer()
            create_bar_items()

            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh_cb', '' )
