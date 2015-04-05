# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2015 by nils_2 <weechatter@arcor.de>
#
# save and restore global and/or buffer command history
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
# 2015-04-05: nils_2 (freenode.#weechat)
#       0.5 : change priority of hook_signal('buffer_opened') to 100
#
# 2013-01-25: nils_2 (freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
#
# 2013-01-20: nils_2, (freenode.#weechat)
#       0.3: fix wrong command argument in help-text
#
# 2012-12-21: nils_2, (freenode.#weechat)
#       0.2 : fix UnicodeEncodeError
#
# 2012-12-09: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# thanks to nestib for help with regex and for the rmodifier idea
#
# requires: WeeChat version 0.4.0
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

try:
    import weechat,re,os

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = 'histman'
SCRIPT_AUTHOR   = 'nils_2 <weechatter@arcor.de>'
SCRIPT_VERSION  = '0.5'
SCRIPT_LICENSE  = 'GPL'
SCRIPT_DESC     = 'save and restore global and/or buffer command history'

OPTIONS         = { 'number'       : ('0','number of history commands/text to save. A positive number will save from oldest to latest, a negative number will save from latest to oldest. 0 = save whole history (e.g. -10 will save the last 10 history entries'),
                    'pattern'      : ('(.*password|.*nickserv|/quit)','a simple regex to ignore commands/text. Empty value disable pattern matching'),
                    'skip_double'  : ('on','skip lines that already exists (case sensitive)'),
                    'save'         : ('all','define what should be save from history. Possible values are \"command\", \"text\", \"all\". This is a fallback option (see /help ' + SCRIPT_NAME +')'),
                    'history_dir'  : ('%h/history','locale cache directory for history files (\"%h\" will be replaced by WeeChat home, \"~/.weechat\" by default)'),
                    'save_global'  : ('off','save global history, possible values are \"command\", \"text\", \"all\" or \"off\"(default: off)'),
                    'min_length'   : ('2','minimum length of command/text (default: 2)'),
                    'rmodifier'    : ('off','use rmodifier options to ignore commands/text (default:off)'),
                    'buffer_close' : ('off','save command history, when buffer will be closed (default: off)'),
                  }

filename_global_history = 'global_history'
possible_save_options = ['command', 'text', 'all']

history_list = []

# =================================[ save/restore buffer history ]================================
def save_history():
    global history_list

    # get buffers
    ptr_infolist_buffer = weechat.infolist_get('buffer','','')

    while weechat.infolist_next(ptr_infolist_buffer):
        ptr_buffer = weechat.infolist_pointer(ptr_infolist_buffer,'pointer')

        # check for localvar_save_history
        if not weechat.buffer_get_string(ptr_buffer, 'localvar_save_history'):
            continue

        plugin = weechat.buffer_get_string(ptr_buffer, 'localvar_plugin')
        name = weechat.buffer_get_string(ptr_buffer, 'localvar_name')
        filename = get_filename_with_path('%s.%s' % (plugin,name))

        get_buffer_history(ptr_buffer)
        if len(history_list):
            write_history(filename)

    weechat.infolist_free(ptr_infolist_buffer)

    # global history
    if OPTIONS['save_global'].lower() != 'off':
        get_buffer_history('')
        if len(history_list):
            write_history(filename_global_history)

def get_buffer_history(ptr_buffer):
    global history_list

    history_list = []
    ptr_buffer_history = weechat.infolist_get('history',ptr_buffer,'')

    if not ptr_buffer_history:
        return

    while weechat.infolist_next(ptr_buffer_history):
        line = weechat.infolist_string(ptr_buffer_history, 'text')

        if add_buffer_line(line,ptr_buffer):
            history_list.insert(0,line)

    weechat.infolist_free(ptr_buffer_history)

# return 1; line will be saved
# return 0; line won't be saved
def add_buffer_line(line, ptr_buffer):
    global history_list

    # min_length reached?
    if len(line) < int(OPTIONS['min_length']):
        return 0

    add_line = 0

    if ptr_buffer: # buffer history
        save_history = weechat.buffer_get_string(ptr_buffer, 'localvar_save_history')
        if not save_history.lower() in possible_save_options:
            save_history = OPTIONS['save']
    else:       # global history
        if not OPTIONS['save_global'].lower() in possible_save_options:
            save_history = OPTIONS['save']

    # no save option given? save nothing
    if save_history == '':
        return 0

    if save_history.lower() == 'command':
        command_chars = weechat.config_string(weechat.config_get('weechat.look.command_chars')) + '/'
        # a valid command must have at least two chars and first and second char are not equal!
        if len(line) > 1 and line[0] in command_chars and line[0] != line[1]:
            add_line = 1
        else:
            return 0
    elif save_history.lower() == 'text':
        command_chars = weechat.config_string(weechat.config_get('weechat.look.command_chars')) + '/'
        # test for "//" = text
        if line[0] == line[1] and line[0] in command_chars:
            add_line = 1
        # test for "/n" = command
        elif line[0] != line[1] and line[0] in command_chars:
            return 0
        else:
            add_line = 1
    elif save_history.lower() == 'all':
        add_line = 1
    else: # not one of given values. save nothing!
        return 0

    # lines already exist?
    if OPTIONS['skip_double'].lower() == 'on':
        history_list2 = []
        history_list2 = [element.lower() for element in history_list]
        if line.lower() in history_list2:
            return 0
        else:
            add_line = 1
    else:
        add_line = 1

    if add_line == 0:
        return 0

    pattern_matching = 0
    # pattern matching for user option and rmodifier options
    if OPTIONS['pattern'] != '':
        filter_re=re.compile(OPTIONS['pattern'], re.I)
        # pattern matched
        if filter_re.match(line):
            pattern_matching = 1

    if OPTIONS['rmodifier'].lower() == 'on' and pattern_matching == 0:
        ptr_infolist_options = weechat.infolist_get('option','','rmodifier.modifier.*')
        if ptr_infolist_options:
            while weechat.infolist_next(ptr_infolist_options):
                value = weechat.infolist_string(ptr_infolist_options,'value')
                pattern = re.findall(r";(.*);", value)

                filter_re=re.compile(pattern[0], re.I)
                # pattern matched
                if filter_re.match(line):
                   pattern_matching = 1
                   break
            weechat.infolist_free(ptr_infolist_options)

    if add_line == 1 and pattern_matching == 0:
        return 1
    return 0

# =================================[ read/write history to file ]=================================
def read_history(filename,ptr_buffer):
    global_history = 0

    # global history does not use buffer pointers!
    if filename == filename_global_history:
        global_history = 1

    filename = get_filename_with_path(filename)

    # filename exists?
    if not os.path.isfile(filename):
        return

    # check for global history
    if global_history == 0:
        # localvar_save_history exists for buffer?
        if not ptr_buffer or not weechat.buffer_get_string(ptr_buffer, 'localvar_save_history'):
            return

    hdata = weechat.hdata_get('history')
    if not hdata:
        return

    try:
        f = open(filename, 'r')
#        for line in f.xreadlines():    # old python 2.x
        for line in f:                  # should also work with python 2.x
#            line = line.decode('utf-8')
            line = str(line.strip())
            if ptr_buffer:
                # add to buffer history
                weechat.hdata_update(hdata, '', { 'buffer': ptr_buffer, 'text': line })
            else:
                # add to global history
                weechat.hdata_update(hdata, '', { 'text': line })
        f.close()
    except:
        if global_history == 1:
            weechat.prnt('','%s%s: Error loading global history from "%s"' % (weechat.prefix('error'), SCRIPT_NAME, filename))
        else:
            name = weechat.buffer_get_string(ptr_buffer, 'localvar_name')
            weechat.prnt('','%s%s: Error loading buffer history for buffer "%s" from "%s"' % (weechat.prefix('error'), SCRIPT_NAME, name, filename))
        raise

def write_history(filename):
    global history_list

    filename = get_filename_with_path(filename)

    if OPTIONS['number'] != '' and OPTIONS['number'].isdigit():
        if int(OPTIONS['number']) < 0:
            save_from_position = len(history_list) - abs(int(OPTIONS['number']))
            if save_from_position == len(history_list) or save_from_position < 0:
                save_from_position = 0
        elif int(OPTIONS['number']) > 0:
            save_to_position = int(OPTIONS['number'])
            if save_to_position > len(history_list):
                save_to_position = len(history_list)
        else:
            save_from_position = 0
    try:
        f = open(filename, 'w')

        if int(OPTIONS['number']) <= 0:
            i = save_from_position
            # for i in range(len(a)):
            while i < len(history_list):
                f.write('%s\n' % history_list[i])
                i = i + 1
        if int(OPTIONS['number']) > 0:
            i = 0
            while i < save_to_position:
                f.write('%s\n' % history_list[i])
                i = i + 1
        f.close()

    except:
        weechat.prnt('','%s%s: Error writing history to "%s"' % (weechat.prefix('error'),SCRIPT_NAME,filename))
        raise

def get_filename_with_path(filename):
    path = OPTIONS['history_dir'].replace("%h",weechat.info_get("weechat_dir", ""))
    return os.path.join(path,filename)

def config_create_dir():
    dir = OPTIONS['history_dir'].replace("%h",weechat.info_get("weechat_dir", ""))
    if not os.path.isdir(dir):
        os.makedirs(dir, mode=0o700)

# ===========================================[ Hooks() ]==========================================
def create_hooks():
    # create hooks
    weechat.hook_signal('quit', 'quit_signal_cb', '')
    weechat.hook_signal('upgrade_ended', 'upgrade_ended_cb', '')
    # low priority for hook_signal('buffer_opened') to ensure that buffer_autoset hook_signal() runs first
    weechat.hook_signal('100|buffer_opened', 'buffer_opened_cb', '')
    weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
    weechat.hook_signal('buffer_closing', 'buffer_closing_cb', '')

def quit_signal_cb(data, signal, signal_data):
    # create dir, if not exist
    config_create_dir()
    save_history()
    return weechat.WEECHAT_RC_OK

def buffer_opened_cb(data, signal, signal_data):
    plugin = weechat.buffer_get_string(signal_data, 'localvar_plugin')
    name = weechat.buffer_get_string(signal_data, 'localvar_name')
    filename = get_filename_with_path('%s.%s' % (plugin,name))

    read_history(filename,signal_data)
    return weechat.WEECHAT_RC_OK

def buffer_closing_cb(data, signal, signal_data):
    if OPTIONS['buffer_close'].lower() == 'on' and signal_data:
        # check for localvar_save_history
        if not weechat.buffer_get_string(signal_data, 'localvar_save_history'):
            return weechat.WEECHAT_RC_OK

        plugin = weechat.buffer_get_string(signal_data, 'localvar_plugin')
        name = weechat.buffer_get_string(signal_data, 'localvar_name')
        filename = get_filename_with_path('%s.%s' % (plugin,name))
        get_buffer_history(signal_data)

        if len(history_list):
            write_history(filename)
    return weechat.WEECHAT_RC_OK

def upgrade_ended_cb(data, signal, signal_data):
    weechat.buffer_set(weechat.buffer_search_main(), 'localvar_set_histman', 'on')
    return weechat.WEECHAT_RC_OK

def histman_cmd_cb(data, buffer, args):
    if args == '':
        weechat.command('', '/help %s' % SCRIPT_NAME)
        return weechat.WEECHAT_RC_OK

    argv = args.strip().split(' ', 1)
    if len(argv) == 0:
        return weechat.WEECHAT_RC_OK

    if argv[0].lower() == 'save':
        quit_signal_cb('', '', '')
    elif argv[0].lower() == 'list':
        weechat.command('','/set *.localvar_set_save_history')
    else:
        weechat.command('', '/help %s' % SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK

# ================================[ weechat options & description ]===============================
def init_options():
    for option,value in list(OPTIONS.items()):
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                            # save new value
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get('version_number', '') or 0

        weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, '[save] || [list]',
                            '  save: force to save command history:\n'
                            '  list: list local buffer variable(s)\n'
                            '\n'
                            'If you \"/quit\" WeeChat, the script will automatically save the command history to file.\n'
                            'You can also force the script to save command history, when a buffer will be closed.\n'
                            'If you restart WeeChat again the command history will be restored, when buffer opens again.\n'
                            'To save and restore \"global\" command history, use option \"save_global\".\n'
                            '\n'
                            'The command history of a buffer will be saved \"only\", if the the local variable \"save_history\" is set.\n'
                            'You will need script \"buffer_autoset.py\" to make local variabe persistent (see examples, below)!!\n'
                            '\n'
                            'You can use following values for local variable:\n'
                            '  command: save commands only\n'
                            '     text: save text only (text sent to a channel buffer)\n'
                            '      all: save commands and text\n'
                            '\n'
                            'Examples:\n'
                            ' save the command history manually (for example with /cron script):\n'
                            '   /' + SCRIPT_NAME + ' save\n'
                            ' save and restore command history for buffer #weechat on freenode (text only):\n'
                            '   /autosetbuffer add irc.freenode.#weechat localvar_set_save_history text\n'
                            ' save and restore command history for weechat core buffer (commands only):\n'
                            '   /autosetbuffer add core.weechat localvar_set_save_history command\n',
                            'save %-'
                            '|| list %-',
                            'histman_cmd_cb', '')

        if int(version) >= 0x00040000:
            if weechat.buffer_get_string(weechat.buffer_search_main(),'localvar_histman') == 'on':
                init_options()
                create_hooks()
                weechat.prnt('','%s%s: do not start this script two times. command history was already restored, during this session!' % (weechat.prefix('error'),SCRIPT_NAME))
            else:
                init_options()
                # create dir, if not exist
                config_create_dir()

                # look for global_history
                if OPTIONS['save_global'].lower() != 'off':
                    read_history(filename_global_history,'')

                # core buffer is already open on script startup. Check manually!
                filename = get_filename_with_path('core.weechat')
                read_history('core.weechat',weechat.buffer_search_main())

                create_hooks()

                # set localvar, to start script only once!
                weechat.buffer_set(weechat.buffer_search_main(), 'localvar_set_histman', 'on')
        else:
            weechat.prnt('','%s%s: needs version 0.4.0 or higher' % (weechat.prefix('error'),SCRIPT_NAME))
            weechat.command('','/wait 1ms /python unload %s' % SCRIPT_NAME)
