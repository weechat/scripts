# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2012 ArZa <arza@arza.us>
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
# Contextual command line help for WeeChat.
# (this script requires WeeChat 0.3.5 or newer)
#
# History:
#
# 2012-01-04, ArZa <arza@arza.us>:
#     version 0.4: settings for right align and space before help
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: make script compatible with Python 3.x
# 2011-05-18, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add options for aliases, start on load, list of commands to
#                  ignore; add default value in help of script options
# 2011-05-15, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'cmd_help'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '0.4'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Contextual command line help'

SCRIPT_COMMAND = 'cmd_help'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import re
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

cmdhelp_hooks = { 'modifier'   : '',
                  'timer'      : '',
                  'command_run': '' }
cmdhelp_option_infolist = ''
cmdhelp_option_infolist_fields = {}

# script options
cmdhelp_settings_default = {
    'display_no_help'  : ['on',         'display "No help" when command is not found'],
    'start_on_load'    : ['off',        'auto start help when script is loaded'],
    'stop_on_enter'    : ['on',         'enter key stop help'],
    'timer'            : ['0',          'number of seconds help is displayed (0 = display until help is toggled)'],
    'prefix'           : ['[',          'string displayed before help'],
    'suffix'           : [']',          'string displayed after help'],
    'format_option'    : ['(${white:type}) ${description_nls}', 'format of help for options: free text with identifiers using format: ${name} or ${color:name}: color is a WeeChat color (optional), name is a field of infolist "option"'],
    'max_options'      : ['5',          'max number of options displayed in list'],
    'ignore_commands'  : ['map,me,die,restart', 'comma-separated list of commands (without leading "/") to ignore'],
    'color_alias'      : ['white',      'color for text "Alias"'],
    'color_alias_name' : ['green',      'color for alias name'],
    'color_alias_value': ['green',      'color for alias value'],
    'color_delimiters' : ['lightgreen', 'color for delimiters'],
    'color_no_help'    : ['red',        'color for text "No help"'],
    'color_list_count' : ['white',      'color for number of commands/options in list found'],
    'color_list'       : ['green',      'color for list of commands/options'],
    'color_arguments'  : ['cyan',       'color for command arguments'],
    'color_option_name': ['yellow',     'color for name of option found (by adding "*" to option name)'],
    'color_option_help': ['brown',      'color for help on option'],
    'right_align'      : ['off',        'align help to right'],
    'right_padding'    : ['15',         'padding to right when aligned to right'],
    'space'            : ['2',          'minimum space before help'],
}
cmdhelp_settings = {}

def unhook(hooks):
    """Unhook something hooked by this script."""
    global cmdhelp_hooks
    for hook in hooks:
        if cmdhelp_hooks[hook]:
            weechat.unhook(cmdhelp_hooks[hook])
            cmdhelp_hooks[hook] = ''

def config_cb(data, option, value):
    """Called when a script option is changed."""
    global cmdhelp_settings, cmdhelp_hooks
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in cmdhelp_settings:
            cmdhelp_settings[name] = value
            if name == 'stop_on_enter':
                if value == 'on' and not cmdhelp_hooks['command_run']:
                    cmdhelp_hooks['command_run'] = weechat.hook_command_run('/input return',
                                                                            'command_run_cb', '')
                elif value != 'on' and cmdhelp_hooks['command_run']:
                    unhook(('command_run',))
    return weechat.WEECHAT_RC_OK

def command_run_cb(data, buffer, command):
    """Callback for "command_run" hook."""
    global cmdhelp_hooks, cmdhelp_settings
    if cmdhelp_hooks['modifier'] and cmdhelp_settings['stop_on_enter'] == 'on':
        unhook(('timer', 'modifier'))
    return weechat.WEECHAT_RC_OK

def format_option(match):
    """Replace ${xxx} by its value in option format."""
    global cmdhelp_settings, cmdhelp_option_infolist, cmdhelp_option_infolist_fields
    string = match.group()
    end = string.find('}')
    if end < 0:
        return string
    field = string[2:end]
    color1 = ''
    color2 = ''
    pos = field.find(':')
    if pos:
        color1 = field[0:pos]
        field = field[pos+1:]
    if color1:
        color1 = weechat.color(color1)
        color2 = weechat.color(cmdhelp_settings['color_option_help'])
    fieldtype = cmdhelp_option_infolist_fields.get(field, '')
    if fieldtype == 'i':
        string = str(weechat.infolist_integer(cmdhelp_option_infolist, field))
    elif fieldtype == 's':
        string = weechat.infolist_string(cmdhelp_option_infolist, field)
    elif fieldtype == 'p':
        string = weechat.infolist_pointer(cmdhelp_option_infolist, field)
    elif fieldtype == 't':
        string = weechat.infolist_time(cmdhelp_option_infolist, field)
    return '%s%s%s' % (color1, string, color2)

def get_option_list_and_desc(option, displayname):
    """Get list of options and description for option(s)."""
    global cmdhelp_settings, cmdhelp_option_infolist, cmdhelp_option_infolist_fields
    options = []
    description = ''
    cmdhelp_option_infolist = weechat.infolist_get('option', '', option)
    if cmdhelp_option_infolist:
        cmdhelp_option_infolist_fields = {}
        while weechat.infolist_next(cmdhelp_option_infolist):
            options.append(weechat.infolist_string(cmdhelp_option_infolist, 'full_name'))
            if not description:
                fields = weechat.infolist_fields(cmdhelp_option_infolist)
                for field in fields.split(','):
                    items = field.split(':', 1)
                    if len(items) == 2:
                        cmdhelp_option_infolist_fields[items[1]] = items[0]
                description = re.compile(r'\$\{[^\}]+\}').sub(format_option, cmdhelp_settings['format_option'])
                if displayname:
                    description = '%s%s%s: %s' % (
                        weechat.color(cmdhelp_settings['color_option_name']),
                        weechat.infolist_string(cmdhelp_option_infolist, 'full_name'),
                        weechat.color(cmdhelp_settings['color_option_help']),
                        description)
        weechat.infolist_free(cmdhelp_option_infolist)
        cmdhelp_option_infolist = ''
        cmdhelp_option_infolist_fields = {}
    return options, description

def get_help_option(input_args):
    """Get help about option or values authorized for option."""
    global cmdhelp_settings, cmdhelp_option_infolist, cmdhelp_option_infolist_fields
    pos = input_args.find(' ')
    if pos > 0:
        option = input_args[0:pos]
    else:
        option = input_args
    options, description = get_option_list_and_desc(option, False)
    if not options and not description:
        options, description = get_option_list_and_desc('%s*' % option, True)
    if len(options) > 1:
        try:
            max_options = int(cmdhelp_settings['max_options'])
        except:
            max_options = 5
        if len(options) > max_options:
            text = '%s...' % ', '.join(options[0:max_options])
        else:
            text = ', '.join(options)
        return '%s%d options: %s%s' % (
            weechat.color(cmdhelp_settings['color_list_count']),
            len(options),
            weechat.color(cmdhelp_settings['color_list']),
            text)
    if description:
        return '%s%s' % (weechat.color(cmdhelp_settings['color_option_help']), description)
    return '%sNo help for option %s' % (weechat.color(cmdhelp_settings['color_no_help']), option)

def get_command_arguments(input_args, cmd_args):
    """Get command arguments according to command arguments given in input."""
    partial = ''
    input_firstarg = input_args.split(' ', 1)[0].lower()
    items = cmd_args.split('||')
    for item in items:
        item = item.strip()
        firstword = item.split(' ')[0]
        items2 = firstword.split('|')
        for item2 in items2:
            item2 = item2.strip().lower()
            if item2 == input_firstarg:
                return item
            if not partial and item2.startswith(input_firstarg):
                partial = item
    if partial:
        return partial
    return cmd_args

def get_help_command(plugin, input_cmd, input_args):
    """Get help for command in input."""
    global cmdhelp_settings
    if input_cmd == 'set' and input_args:
        return get_help_option(input_args)
    infolist = weechat.infolist_get('hook', '', 'command,%s' % input_cmd)
    cmd_plugin_name = ''
    cmd_command = ''
    cmd_args = ''
    cmd_desc = ''
    while weechat.infolist_next(infolist):
        cmd_plugin_name = weechat.infolist_string(infolist, 'plugin_name') or 'core'
        cmd_command = weechat.infolist_string(infolist, 'command')
        cmd_args = weechat.infolist_string(infolist, 'args_nls')
        cmd_desc = weechat.infolist_string(infolist, 'description')
        if weechat.infolist_pointer(infolist, 'plugin') == plugin:
            break
    weechat.infolist_free(infolist)
    if cmd_plugin_name == 'alias':
        return '%sAlias %s%s%s => %s%s' % (weechat.color(cmdhelp_settings['color_alias']),
                                           weechat.color(cmdhelp_settings['color_alias_name']),
                                           cmd_command,
                                           weechat.color(cmdhelp_settings['color_alias']),
                                           weechat.color(cmdhelp_settings['color_alias_value']),
                                           cmd_desc)
    if input_args:
        cmd_args = get_command_arguments(input_args, cmd_args)
    if not cmd_args:
        return None
    return '%s%s' % (weechat.color(cmdhelp_settings['color_arguments']), cmd_args)

def get_list_commands(plugin, input_cmd, input_args):
    """Get list of commands (beginning with current input)."""
    global cmdhelp_settings
    infolist = weechat.infolist_get('hook', '', 'command,%s*' % input_cmd)
    commands = []
    plugin_names = []
    while weechat.infolist_next(infolist):
        commands.append(weechat.infolist_string(infolist, 'command'))
        plugin_names.append(weechat.infolist_string(infolist, 'plugin_name') or 'core')
    weechat.infolist_free(infolist)
    if commands:
        if len(commands) > 1 or commands[0].lower() != input_cmd.lower():
            commands2 = []
            for index, command in enumerate(commands):
                if commands.count(command) > 1:
                    commands2.append('%s(%s)' % (command, plugin_names[index]))
                else:
                    commands2.append(command)
            return '%s%d commands: %s%s' % (
                weechat.color(cmdhelp_settings['color_list_count']),
                len(commands2),
                weechat.color(cmdhelp_settings['color_list']),
                ', '.join(commands2))
    return None

def input_modifier_cb(data, modifier, modifier_data, string):
    """Modifier that will add help on command line (for display only)."""
    global cmdhelp_settings
    line = weechat.string_remove_color(string, '')
    if line == '':
        return string
    command = ''
    arguments = ''
    if weechat.string_input_for_buffer(line) != '':
        return string
    items = line.split(' ', 1)
    if len(items) > 0:
        command = items[0]
        if len(command) < 2:
            return string
        if len(items) > 1:
            arguments = items[1]
    if command[1:].lower() in cmdhelp_settings['ignore_commands'].split(','):
        return string
    current_buffer = weechat.current_buffer()
    current_window = weechat.current_window()
    plugin = weechat.buffer_get_pointer(current_buffer, 'plugin')
    msg_help = get_help_command(plugin, command[1:], arguments) or get_list_commands(plugin, command[1:], arguments)
    if not msg_help:
        if cmdhelp_settings['display_no_help'] != 'on':
            return string
        msg_help = weechat.color(cmdhelp_settings['color_no_help'])
        if command:
            msg_help += 'No help for command %s' % command
        else:
            msg_help += 'No help'

    if cmdhelp_settings['right_align'] == 'on':
        win_width = weechat.window_get_integer(current_window, 'win_width')
        input_length = weechat.buffer_get_integer(current_buffer, 'input_length')
        help_length = len(weechat.string_remove_color(msg_help, ""))
        min_space = int(cmdhelp_settings['space'])
        padding = int(cmdhelp_settings['right_padding'])
        space = win_width - input_length - help_length - padding
        if space < min_space:
            space = min_space
    else:
        space = int(cmdhelp_settings['space'])

    color_delimiters = cmdhelp_settings['color_delimiters']
    return '%s%s%s%s%s%s%s' % (string,
                               space * ' ',
                               weechat.color(color_delimiters),
                               cmdhelp_settings['prefix'],
                               msg_help,
                               weechat.color(color_delimiters),
                               cmdhelp_settings['suffix'])

def timer_cb(data, remaining_calls):
    """Timer callback."""
    global cmdhelp_hooks
    if cmdhelp_hooks['modifier']:
        unhook(('modifier',))
        weechat.bar_item_update('input_text')
    return weechat.WEECHAT_RC_OK

def cmd_help_toggle():
    """Toggle help on/off."""
    global cmdhelp_hooks, cmdhelp_settings
    if cmdhelp_hooks['modifier']:
        unhook(('timer', 'modifier'))
    else:
        cmdhelp_hooks['modifier'] = weechat.hook_modifier('input_text_display_with_cursor',
                                                          'input_modifier_cb', '')
        timer = cmdhelp_settings['timer']
        if timer and timer != '0':
            try:
                value = float(timer)
                if value > 0:
                    weechat.hook_timer(value * 1000, 0, 1, 'timer_cb', '')
            except:
                pass
    weechat.bar_item_update('input_text')

def cmd_help_cb(data, buffer, args):
    """Callback for /cmd_help command."""
    cmd_help_toggle()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, '', ''):
        # set allowed fields in option "format_option"
        fields = []
        infolist = weechat.infolist_get('option', '', 'weechat.plugin.*')
        if infolist:
            if weechat.infolist_next(infolist):
                strfields = weechat.infolist_fields(infolist)
                for field in strfields.split(','):
                    items = field.split(':', 1)
                    if len(items) == 2:
                        fields.append(items[1])
            weechat.infolist_free(infolist)
        if fields:
            cmdhelp_settings_default['format_option'][1] += ': %s' % ', '.join(fields)

        # set default settings
        version = weechat.info_get("version_number", "") or 0
        for option, value in cmdhelp_settings_default.items():
            if weechat.config_is_set_plugin(option):
                cmdhelp_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                cmdhelp_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'config_cb', '')

        # add hook to catch "enter" key
        if cmdhelp_settings['stop_on_enter'] == 'on':
            cmdhelp_hooks['command_run'] = weechat.hook_command_run('/input return',
                                                                    'command_run_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND,
                             'Contextual command line help.',
                             '',
                             'This comand toggles help on command line.\n\n'
                             'It is recommended to bind this command on a key, for example F1:\n'
                             '  /key bind <press alt-k> <press F1> /cmd_help\n'
                             'which will give, according to your terminal something like:\n'
                             '      /key bind meta-OP /cmd_help\n'
                             '    or:\n'
                             '      /key bind meta2-11~ /cmd_help\n\n'
                             'To try: type "/server" (without pressing enter) and press F1 '
                             '(then you can add arguments and enjoy dynamic help!)',
                             '', 'cmd_help_cb', '')

        # auto start help
        if cmdhelp_settings['start_on_load'] == 'on':
            cmd_help_toggle()
