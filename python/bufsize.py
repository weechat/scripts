#
# SPDX-FileCopyrightText: 2012-2026 nils_2 <libera.#weechat>
# SPDX-FileCopyrightText: 2012-2017 nesthib <nesthib@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# scroll indicator; displaying number of lines below last line, overall lines in buffer, number of current line and percent displayed
#
# 2026-09-30: nils_2 (libera.#weechat)
#      0.9.1: fix: use the window being drawn (not the current one) for chat height
#           : fix: load options before bar item and hooks are registered
#           : fix: use the same line list (lines) for total and filtered count (merged buffers)
#           : fix: optional tags %{...} are stripped by slicing instead of lstrip/rstrip
#           : fix: /unset of an option restores the default value
#           : fix: only ImportError is caught on import, use sys.exit()
#           : internal: remove dead code, skip filtered counting when filters are disabled
#           : add SPDX copyright and license tags
#
# 2026-05-23: nils_2 (libera.#weechat)
#        0.9: fix: two SyntaxWarning
# 2017-08-17: nils_2 (freenode.#weechat)
#        0.8: add support for buffer_filters_enabled and buffer_filters_disabled (WeeChat ≥ 2.0)
# 2016-12-16: nils_2 (freenode.#weechat)
#        0.7: add option show_scroll (idea by earnestly)
# 2016-04-23: wdbw <tuturu@tutanota.com>
#     0.6.2 : fix: type of filters_enabled
# 2014-02-24: nesthib (freenode.#weechat)
#     0.6.1 : fix: color tags for default format
# 2013-11-19: nils_2 (freenode.#weechat)
#       0.6 : fix: stdout/stderr warning
# 2013-11-02: nils_2 (freenode.#weechat)
#       0.5 : fix refresh on (un)zoomed buffer
#           : add option 'count_filtered_lines' and format item "%F"
# 2013-10-15: nils_2 (freenode.#weechat)
#       0.4 : fix bug with root-bar
#           : add support of eval_expression (weechat >= 0.4.2)
# 2013-01-25: nils_2 (freenode.#weechat)
#       0.3 : make script compatible with Python 3.x
#           : internal changes
# 2012-07-09: nils_2 (freenode.#weechat)
#       0.2 : fix: display bug with more than one window
#           : hide item when buffer empty
# 2012-07-08: obiwahn
#     0.1.1 : add hook for switch_buffer
# 2012-01-11: nils_2, nesthib (freenode.#weechat)
#       0.1 : initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

import re
import sys

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    sys.exit(1)

SCRIPT_NAME     = "bufsize"
SCRIPT_AUTHOR   = "nils_2 <libera.#weechat>"
SCRIPT_VERSION  = "0.9.1"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "scroll indicator; displaying number of lines below last line, overall lines in buffer, number of current line and percent displayed"

DEFAULTS        = { 'format'            : ('${color:yellow}%P${color:default}⋅%{${color:yellow}%A${color:default}⇵${color:yellow}%C${color:default}/}${color:yellow}%L',
                                           'format for items to display in bar, possible items: %P = percent indicator, %A = number of lines below last line, %L = lines counter, %C = current line %F = number of filtered lines (note: using WeeChat >= 0.4.2, content is evaluated, so you can use colors with format \"${color:xxx}\", see /help eval)'),
                    'count_filtered_lines': ('on',
                                           'filtered lines will be count in item.'),
                    'show_scroll':          ('on',
                                           'always show the scroll indicator number,even if its 0 (item %A), if option is off the scroll indicator will be hidden like the item "scroll"'),
                   }

# current option values (plain strings), filled by init_options()
OPTIONS         = {option: value[0] for option, value in DEFAULTS.items()}

# WeeChat version as number, set in main
VERSION         = 0

# ================================[ weechat item ]===============================
# regexp to match ${color} tags
regex_color = re.compile(r'\$\{([^\{\}]+)\}')

# regexp to match %{optional string} tags
regex_optional_tags = re.compile(r'%\{[^\{\}]+\}')

filter_status = 0

OFF_VALUES = ('off', '0', 'false', 'no')

def option_is_off(name):
    return OPTIONS[name].strip().lower() in OFF_VALUES

def show_item(data, item, window):
    # check for root input bar!
    if not window:
        window = weechat.current_window()

    ptr_buffer = weechat.window_get_pointer(window, 'buffer')
    if ptr_buffer == '':
        return ''

    if weechat.buffer_get_string(ptr_buffer, 'name') != 'weechat':                        # not weechat core buffer
        if weechat.buffer_get_string(ptr_buffer, 'localvar_type') == '':                  # buffer with free content?
            return ''

    lines_after, lines_count, percent, current_line, filtered = count_lines(window, ptr_buffer)
    lines_after_bak = lines_after

    if lines_count == 0:                                                                  # buffer empty?
        return ''

    if filtered == 0:
        filtered = ''

    if lines_after == 0 and option_is_off('show_scroll'):
        lines_after = ''

    tags = {'%C': str(current_line),
            '%A': str(lines_after),
            '%F': str(filtered),
            '%L': str(lines_count),
            '%P': str(percent) + '%'}

    bufsize_item = substitute_colors(OPTIONS['format'])

    # replace mandatory tags
    for tag, value in tags.items():
        bufsize_item = bufsize_item.replace(tag, value)

    # optional tags %{...}: keep content only if there are lines below (%A > 0)
    if lines_after_bak > 0:
        bufsize_item = regex_optional_tags.sub(lambda m: m.group(0)[2:-1], bufsize_item)
    else:
        bufsize_item = regex_optional_tags.sub('', bufsize_item)

    return bufsize_item

def substitute_colors(text):
    if VERSION >= 0x00040200:
        return weechat.string_eval_expression(text, {}, {}, {})
    # substitute colors in output
    return regex_color.sub(lambda match: weechat.color(match.group(1)), text)

def count_lines(ptr_window, ptr_buffer):
    hdata_buf = weechat.hdata_get('buffer')
    hdata_lines = weechat.hdata_get('lines')
    # 'lines' points to own_lines, or to mixed_lines for merged buffers
    lines = weechat.hdata_pointer(hdata_buf, ptr_buffer, 'lines')
    lines_count = weechat.hdata_integer(hdata_lines, lines, 'lines_count')

    hdata_window = weechat.hdata_get('window')
    hdata_winscroll = weechat.hdata_get('window_scroll')
    window_scroll = weechat.hdata_pointer(hdata_window, ptr_window, 'scroll')
    lines_after = weechat.hdata_integer(hdata_winscroll, window_scroll, 'lines_after')
    window_height = weechat.window_get_integer(ptr_window, 'win_chat_height')

    filtered = 0
    # only count if option is off and filters are enabled
    if option_is_off('count_filtered_lines') and filter_status == 1:
        filtered = count_filtered_lines(lines)
        lines_count = lines_count - filtered

    if lines_count > window_height:
        differential = lines_count - window_height
        percent = max(int(round(100. * (differential - lines_after) / differential)), 0)
    else:
        percent = 100

    # get current position
    current_line = lines_count - lines_after

    return lines_after, lines_count, percent, current_line, filtered

def count_filtered_lines(lines):
    """Count lines that are currently hidden by filters in the given lines list."""
    filtered = 0
    if not lines:
        return filtered

    hdata_line = weechat.hdata_get('line')
    hdata_line_data = weechat.hdata_get('line_data')

    line = weechat.hdata_pointer(weechat.hdata_get('lines'), lines, 'first_line')
    while line:
        data = weechat.hdata_pointer(hdata_line, line, 'data')
        if data and weechat.hdata_char(hdata_line_data, data, 'displayed') == 0:
            filtered += 1
        line = weechat.hdata_move(hdata_line, line, 1)

    return filtered

def update_cb(data, signal, signal_data):
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

def filtered_update_cb(data, signal, signal_data):
    global filter_status
    if signal == 'filters_disabled':
        filter_status = 0
    if signal == 'filters_enabled':
        filter_status = 1
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ weechat options and description ]===============================
def init_options():
    for option, value in DEFAULTS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, "%s (default: '%s')" % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    if option in DEFAULTS:
        if weechat.config_is_set_plugin(option):
            OPTIONS[option] = value                                       # save new value
        else:
            OPTIONS[option] = DEFAULTS[option][0]                         # option was unset: back to default
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        try:
            VERSION = int(weechat.info_get("version_number", "") or 0)
        except ValueError:
            VERSION = 0

        if VERSION >= 0x00030600:
            init_options()                                                # options first, then item and hooks
            filter_status = int(weechat.info_get('filters_enabled', '') or 0)
            weechat.bar_item_new(SCRIPT_NAME, 'show_item', '')
            weechat.hook_signal('buffer_line_added', 'update_cb', '')
            weechat.hook_signal('window_scrolled', 'update_cb', '')
            weechat.hook_signal('buffer_switch', 'update_cb', '')
            weechat.hook_signal('*filters*', 'filtered_update_cb', '')
            weechat.hook_command_run('/buffer clear*', 'update_cb', '')
            weechat.hook_command_run('/window page*', 'update_cb', '')
            weechat.hook_command_run('/input zoom_merged_buffer', 'update_cb', '')
            weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '')
            weechat.bar_item_update(SCRIPT_NAME)
        else:
            weechat.prnt('', '%s%s %s' % (weechat.prefix('error'), SCRIPT_NAME, ': needs version 0.3.6 or higher'))
