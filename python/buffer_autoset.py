# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Sebastien Helleu <flashcode@flashtux.org>
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
# Auto-set buffer properties when a buffer is opened.
# (this script requires WeeChat 0.3.2 or newer)
#
# History:
#
# 2015-04-05, Nils Görs <freenode@#weechat>:
#     version 0.7: increase priority of hook_signal('buffer_opened')
# 2012-12-09, Nils Görs <freenode@#weechat>:
#     version 0.6: add support of core buffer
# 2012-03-09, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: fix reload of config file
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: make script compatible with Python 3.x
# 2010-12-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: "no_highlight_nicks" replaced by "hotlist_max_level_nicks"
# 2010-10-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add example in /help autosetbuffer with new buffer
#                  property "no_highlight_nicks"
# 2010-04-19, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = "buffer_autoset"
SCRIPT_AUTHOR  = "Sebastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.7"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto-set buffer properties when a buffer is opened"

SCRIPT_COMMAND = "autosetbuffer"

import_ok = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

CONFIG_FILE_NAME = "buffer_autoset"

# config file
bas_config_file = ""

# =================================[ config ]=================================

def bas_config_init():
    """
    Initialization of configuration file.
    Sections: buffer.
    """
    global bas_config_file
    bas_config_file = weechat.config_new(CONFIG_FILE_NAME,
                                         "bas_config_reload_cb", "")
    if bas_config_file == "":
        return

    # section "buffer"
    section_buffer = weechat.config_new_section(
        bas_config_file, "buffer", 1, 1, "", "", "", "", "", "",
        "bas_config_buffer_create_option_cb", "", "", "")
    if section_buffer == "":
        weechat.config_free(bas_config_file)
        return

def bas_config_buffer_create_option_cb(data, config_file, section, option_name, value):
    option = weechat.config_search_option(config_file, section, option_name)
    if option:
        return weechat.config_option_set (option, value, 1)
    else:
        option = weechat.config_new_option (config_file, section, option_name, "string",
                                            "", "", 0, 0, "", value, 0,
                                            "", "", "", "", "", "")
        if not option:
            return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
        return weechat.WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE

def bas_config_reload_cb(data, config_file):
    """ Reload configuration file. """
    return weechat.config_reload(config_file)

def bas_config_read():
    """ Read configuration file. """
    global bas_config_file
    return weechat.config_read(bas_config_file)

def bas_config_write():
    """ Write configuration file. """
    global bas_config_file
    return weechat.config_write(bas_config_file)

# ================================[ command ]=================================

def bas_cmd(data, buffer, args):
    """ Callback for /autosetbuffer command. """
    args = args.strip()
    if args == "":
        weechat.command("", "/set %s.buffer.*" % CONFIG_FILE_NAME)
        return weechat.WEECHAT_RC_OK
    argv = args.split(None, 3)
    if len(argv) > 0:
        if argv[0] == "add":
            if len(argv) < 4:
                weechat.command("", "/help %s" % SCRIPT_COMMAND)
                return weechat.WEECHAT_RC_OK
            weechat.command("", "/set %s.buffer.%s.%s \"%s\""
                            % (CONFIG_FILE_NAME, argv[1], argv[2], argv[3]))
        elif argv[0] == "del":
            if len(argv) < 2:
                weechat.command("", "/help %s" % SCRIPT_COMMAND)
                return weechat.WEECHAT_RC_OK
            weechat.command("", "/unset %s.buffer.%s"
                            % (CONFIG_FILE_NAME, argv[1]))
        else:
            weechat.command("", "/help %s" % SCRIPT_COMMAND)
            return weechat.WEECHAT_RC_OK
    return weechat.WEECHAT_RC_OK

def bas_completion_current_buffer_cb(data, completion_item, buffer, completion):
    """ Complete with current buffer name (plugin.name), for command '/autosetbuffer'. """
    name = "%s.%s" % (weechat.buffer_get_string(buffer, "plugin"),
                      weechat.buffer_get_string(buffer, "name"))
    weechat.hook_completion_list_add(completion, name,
                                     0, weechat.WEECHAT_LIST_POS_BEGINNING)
    return weechat.WEECHAT_RC_OK

def bas_completion_options_cb(data, completion_item, buffer, completion):
    """ Complete with config options, for command '/autosetbuffer'. """
    options = weechat.infolist_get("option", "", "%s.buffer.*" % CONFIG_FILE_NAME)
    if options:
        while weechat.infolist_next(options):
            weechat.hook_completion_list_add(completion,
                                             weechat.infolist_string(options, "option_name"),
                                             0, weechat.WEECHAT_LIST_POS_SORT)
        weechat.infolist_free(options)
    return weechat.WEECHAT_RC_OK

# =================================[ signal ]=================================

def bas_signal_buffer_opened_cb(data, signal, signal_data):
    buffer = signal_data
    name = "%s.%s" % (weechat.buffer_get_string(buffer, "plugin"),
                      weechat.buffer_get_string(buffer, "name"))
    options = weechat.infolist_get("option", "", "%s.buffer.*" % CONFIG_FILE_NAME)
    if options:
        while weechat.infolist_next(options):
            option = weechat.infolist_string(options, "option_name")
            value = weechat.infolist_string(options, "value")
            if option:
                pos = option.rfind(".")
                if pos > 0:
                    buffer_mask = option[0:pos]
                    property = option[pos+1:]
                    if buffer_mask and property:
                        if weechat.string_match(name, buffer_mask, 1):
                            weechat.buffer_set(buffer, property, value)
        weechat.infolist_free(options)
    return weechat.WEECHAT_RC_OK

# ==================================[ main ]==================================

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "bas_unload_script", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00030200:
            weechat.prnt("", "%s%s: WeeChat 0.3.2 is required for this script."
                         % (weechat.prefix("error"), SCRIPT_NAME))
        else:
            bas_config_init()
            bas_config_read()
            weechat.hook_command(SCRIPT_COMMAND,
                                 "Auto-set buffer properties when a buffer is opened",
                                 "[add buffer property value] | [del option]",
                                 "     add: add a buffer/property/value in configuration file\n"
                                 "     del: delete an option from configuration file\n"
                                 "  buffer: name of a buffer (can start or end with \"*\" as wildcard)\n"
                                 "property: buffer property\n"
                                 "   value: value for property\n"
                                 "  option: name of option from configuration file\n\n"
                                 "Examples:\n"
                                 "  disable timestamp on channel #weechat:\n"
                                 "    /" + SCRIPT_COMMAND + " add irc.freenode.#weechat time_for_each_line 0\n"
                                 "  add word \"weechat\" in highlight list on channel #savannah:\n"
                                 "    /" + SCRIPT_COMMAND + " add irc.freenode.#savannah highlight_words_add weechat\n"
                                 "  disable highlights from nick \"mike\" on freenode server, channel #weechat (requires WeeChat >= 0.3.4):\n"
                                 "    /" + SCRIPT_COMMAND + " add irc.freenode.#weechat hotlist_max_level_nicks_add mike:2\n"
                                 "  disable hotlist changes for nick \"bot\" on freenode server (all channels) (requires WeeChat >= 0.3.4):\n"
                                 "    /" + SCRIPT_COMMAND + " add irc.freenode.* hotlist_max_level_nicks_add bot:-1",
                                 "add %(buffers_plugins_names)|%(buffer_autoset_current_buffer) %(buffer_properties_set)"
                                 " || del %(buffer_autoset_options)",
                                 "bas_cmd", "")
            weechat.hook_completion("buffer_autoset_current_buffer", "current buffer name for buffer_autoset",
                                    "bas_completion_current_buffer_cb", "")
            weechat.hook_completion("buffer_autoset_options", "list of options for buffer_autoset",
                                    "bas_completion_options_cb", "")
            weechat.hook_signal("9000|buffer_opened", "bas_signal_buffer_opened_cb", "")

            # core buffer is already open on script startup, check manually!
            bas_signal_buffer_opened_cb("", "", weechat.buffer_search_main())
# ==================================[ end ]===================================

def bas_unload_script():
    """ Function called when script is unloaded. """
    global bas_config_file

    if bas_config_file:
        bas_config_write()
    return weechat.WEECHAT_RC_OK
