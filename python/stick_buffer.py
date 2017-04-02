# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2017 by nils_2 <weechatter@arcor.de>
# Copyright (c) 2015 by Damien Bargiacchi <icymidnight@gmail.com>
#
# stick buffer to a window, irssi like
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
# idea by shad0VV@freenode.#weechat
#
# 2017-04-02: nils_2, (freenode.#weechat)
#       0.5 : support of "/input jump_smart" and "/buffer +/-" (reported: squigz)
#
# 2017-03-25: nils_2, (freenode.#weechat)
#       0.4 : script did not work with /go script and buffer names (reported: squigz)
#
# 2015-05-12: Damien Bargiacchi <icymidnight@gmail.com>
#       0.3 : Stop script from truncating localvar lookup to first character of the buffer number
#           : Clean up destination buffer number logic
#
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.2 : make script compatible with Python 3.x
#           : smaller improvements
#
# 2013-01-21: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.6
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat, sys

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "stick_buffer"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.5"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "Stick buffers to particular windows, like irssi"

# ======================================[      config      ]====================================== #
SW_CONFIG_DEFAULTS = {
    'default_stick_window' : ('', 'The default window to stick a buffer to if no localvar '
                                  'stick_buffer_to_window is set'),
}

sw_config = {}

def init_config():
    for option, (default_value, description) in SW_CONFIG_DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)
            sw_config[option] = default_value
        else:
            sw_config[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (description, default_value))

    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'update_config', '')


def update_config(pointer, name, value):
    global sw_config
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]
    sw_config[option] = value
    return weechat.WEECHAT_RC_OK

def get_default_stick_window_number():
    if sw_config['default_stick_window'] and sw_config['default_stick_window'].isdigit():
        return int(sw_config['default_stick_window'])
    return None

# ======================================[   buffer utils   ]====================================== #
def infolist_get_buffer_name_and_ptr_by_number(str_buffer_number):
    infolist = weechat.infolist_get('buffer', '', '')
    full_name = ''
    ptr_buffer = ''
    if infolist:
        while weechat.infolist_next(infolist):
            if int(str_buffer_number) == weechat.infolist_integer(infolist, 'number'):
                full_name = weechat.infolist_string(infolist, 'full_name')
                ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
                break
        weechat.infolist_free(infolist)
    return full_name, ptr_buffer

def infolist_get_buffer_name_and_ptr_by_name(str_buffer_name):
    infolist = weechat.infolist_get('buffer', '', '*%s*' % str_buffer_name)
    full_name = ''
    ptr_buffer = ''
    if infolist:
        while weechat.infolist_next(infolist):
            full_name = weechat.infolist_string(infolist, 'full_name')
            ptr_buffer = weechat.infolist_pointer(infolist, 'pointer')
            break
        weechat.infolist_free(infolist)
    return full_name, ptr_buffer

def infolist_get_first_entry_from_hotlist():
    infolist = weechat.infolist_get('hotlist', '', '')
    if infolist:
        weechat.infolist_next(infolist)         # go to first entry in hotlist
        buffer_name = weechat.infolist_string(infolist, 'buffer_name')
        buffer_number = weechat.infolist_integer(infolist, 'buffer_number')
        ptr_buffer = weechat.infolist_pointer(infolist, 'buffer_pointer')
        weechat.infolist_free(infolist)
    return buffer_name, ptr_buffer, buffer_number

def get_current_buffer_number():
    ptr_buffer = weechat.window_get_pointer(weechat.current_window(), 'buffer')
    return weechat.buffer_get_integer(ptr_buffer, 'number')

def get_destination_buffer_number(arg):
    mod = None
    num_str = arg
    if arg[0] in '+-*':
        num_str = arg[1:]
        mod = arg[0]
    if not num_str.isdigit():
        return None
    num = int(num_str)

    if not mod or mod == '*':
        return num

    current_buffer = get_current_buffer_number()
    if not current_buffer:
        return None
    if mod == '+':
        return current_buffer + num
    else: # mod == '-'
        return current_buffer - num

# ======================================[    callbacks     ]====================================== #
def buffer_switch_cb(data, buffer, command):
#    weechat.prnt("","data: %s   buffer: %s  command: %s" % (data,buffer,command))
    # command exist?
    if command == '':
        return weechat.WEECHAT_RC_OK

    # get command without leading command char!
    cmd = command[1:].strip().split(' ',)[0:1]
    # get number from command /buffer
    args = command.strip().split(' ',)[1:]
    ptr_buffer = ''

    if "input" in cmd and "jump_smart" in args:
        buffer_name, ptr_buffer, buffer_number = infolist_get_first_entry_from_hotlist()

    if "buffer" in cmd:
        if len(args) != 1:
            return weechat.WEECHAT_RC_OK

        # check if argument is a buffer "number"
        destination_buffer = get_destination_buffer_number(args[0])
        if destination_buffer:
            if destination_buffer < 1:
                destination_buffer = 1
            buffer_name, ptr_buffer = infolist_get_buffer_name_and_ptr_by_number(destination_buffer)
        else:
            # search for buffer name
            buffer_name, ptr_buffer = infolist_get_buffer_name_and_ptr_by_name(args[0])

    if not ptr_buffer:
        return weechat.WEECHAT_RC_OK

    if ptr_buffer == weechat.window_get_pointer(weechat.current_window(), 'buffer'):
        return weechat.WEECHAT_RC_OK
    window_number = weechat.buffer_get_string(ptr_buffer, 'localvar_stick_buffer_to_window')
    if not window_number:
        window_number = get_default_stick_window_number()
    if window_number:
        weechat.command('', '/window %s' % window_number)
        weechat.command('', '/buffer %s' % buffer_name)
        return weechat.WEECHAT_RC_OK_EAT
    else:
        return weechat.WEECHAT_RC_OK

def cmd_cb(data, buffer, args):
    args = args.strip().lower().split(' ')

    if args[0] == 'list':
        weechat.command('', '/set *.localvar_set_stick_buffer_to_window')
    elif args[0] in ['', 'help']:
        show_help()
    else:
        print_error('Unrecognized command %s\n' % ' '.join(args))
        show_help()

    return weechat.WEECHAT_RC_OK

# ======================================[       util       ]====================================== #

def show_help():
    weechat.command('', '/help %s' % SCRIPT_NAME)

def print_error(message):
    weechat.prnt('', '%s%s: %s' % (weechat.prefix("error"), SCRIPT_NAME, message))

# ======================================[       main       ]====================================== #

def main():
        version = weechat.info_get('version_number', '') or 0

        if int(version) < 0x00030600:
            print_error('script needs version 0.3.6 or higher')
            weechat.command('', "/wait 1ms /python unload %s" % SCRIPT_NAME)
            return

        init_config()

        description = """
{script_name} can make sure that when switching to a buffer it appears only in a particular window.
To trigger this behaviour set the localvar 'stick_buffer_to_window' to the desired window number.

You will need the script 'buffer_autoset.py' installed to make local variables persistent; see the
examples below.

Examples:
 Temporarily stick the current buffer to window 3:
   /buffer set localvar_set_stick_buffer_to_window 3
 Stick buffer #weechat to window 2:
   /buffer #weechat
   /buffer set localvar_set_stick_buffer_to_window 2
   /autosetbuffer add irc.freenode.#weechat stick_buffer_to_window 2
 Set the default stick-to window to window 5:
   /set plugins.var.python.{script_name}.default_stick_window 5
 List buffers with persistent stickiness:
   /{script_name} list
 Show this help:
   /{script_name} help
 Display local variables for current buffer:
   /buffer localvar
""".format(script_name = SCRIPT_NAME)

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, 'list', description, 'list %-', 'cmd_cb', '')

        weechat.hook_command_run('/buffer *', 'buffer_switch_cb', '')
        weechat.hook_command_run('/input jump_smart', 'buffer_switch_cb', '')

if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
                        '', ''):
        main()
