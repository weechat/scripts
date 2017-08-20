# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2017 by nils_2 <weechatter@arcor.de>
#                         and nesthib <nesthib@gmail.com>
#
# scroll indicator; displaying number of lines below last line, overall lines in buffer, number of current line and percent displayed
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

try:
    import weechat, re

except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME     = "bufsize"
SCRIPT_AUTHOR   = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION  = "0.8"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "scroll indicator; displaying number of lines below last line, overall lines in buffer, number of current line and percent displayed"

OPTIONS         = { 'format'            : ('${color:yellow}%P${color:default}⋅%{${color:yellow}%A${color:default}⇵${color:yellow}%C${color:default}/}${color:yellow}%L',
                                           'format for items to display in bar, possible items: %P = percent indicator, %A = number of lines below last line, %L = lines counter, %C = current line %F = number of filtered lines (note: using WeeChat >= 0.4.2, content is evaluated, so you can use colors with format \"${color:xxx}\", see /help eval)'),
                    'count_filtered_lines': ('on',
                                           'filtered lines will be count in item.'),
                    'show_scroll':('on','always show the scroll indicator number,even if its 0 (item %A), if option is off the scroll indicator will be hidden like the item "scroll"'),
                   }
# ================================[ weechat item ]===============================
# regexp to match ${color} tags
regex_color=re.compile('\$\{([^\{\}]+)\}')

# regexp to match ${optional string} tags
regex_optional_tags=re.compile('%\{[^\{\}]+\}')

filter_status = 0

def show_item (data, item, window):
    # check for root input bar!
    if not window:
       window = weechat.current_window()

    ptr_buffer = weechat.window_get_pointer(window,'buffer')
    if ptr_buffer == '':
        return ''

    if weechat.buffer_get_string(ptr_buffer,'name') != 'weechat':                         # not weechat core buffer
        if weechat.buffer_get_string(ptr_buffer,'localvar_type') == '':                   # buffer with free content?
          return ''

    lines_after, lines_count, percent, current_line, filtered, filtered_before, filtered_after = count_lines(window,ptr_buffer)
    lines_after_bak = lines_after

    if lines_count == 0:                                                                  # buffer empty?
        return ''

    if filtered == 0:
        filtered = ''

    if lines_after == 0 and (OPTIONS['show_scroll'].lower() == 'off'):
        lines_after = ''

    tags = {'%C': str(current_line),
            '%A': str(lines_after),
            '%F': str(filtered),
            '%L': str(lines_count),
            '%P': str(percent)+'%'}

    bufsize_item = substitute_colors(OPTIONS['format'])

    # replace mandatory tags
    for tag in list(tags.keys()):
#    for tag in tags.keys():
        bufsize_item = bufsize_item.replace(tag, tags[tag])

    # replace optional tags
    # %{…} only if lines after (e.g. %A > 0)
    if lines_after_bak > 0:
        for regex_tag in regex_optional_tags.findall(bufsize_item):
            bufsize_item = bufsize_item.replace(regex_tag, regex_tag.lstrip('%{').rstrip('}'))
    else:
        bufsize_item = regex_optional_tags.sub('', bufsize_item)

    return bufsize_item

def substitute_colors(text):
    if int(version) >= 0x00040200:
        return weechat.string_eval_expression(text,{},{},{})
    # substitute colors in output
    return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

def count_lines(ptr_window,ptr_buffer):
    global filter_status

    hdata_buf = weechat.hdata_get('buffer')
    hdata_lines = weechat.hdata_get('lines')
    lines = weechat.hdata_pointer(hdata_buf, ptr_buffer, 'lines') # own_lines, mixed_lines
    lines_count = weechat.hdata_integer(hdata_lines, lines, 'lines_count')

    hdata_window = weechat.hdata_get('window')
    hdata_winscroll = weechat.hdata_get('window_scroll')
    window_scroll = weechat.hdata_pointer(hdata_window, ptr_window, 'scroll')
    lines_after = weechat.hdata_integer(hdata_winscroll, window_scroll, 'lines_after')
    window_height = weechat.window_get_integer(weechat.current_window(), 'win_chat_height')

    filtered = 0
    filtered_before = 0
    filtered_after = 0
    # if filter is disabled, don't count.
    if (OPTIONS['count_filtered_lines'].lower() == 'off') and filter_status == 1:
        filtered, filtered_before,filtered_after = count_filtered_lines(ptr_buffer,lines_count,lines_after)
        lines_count = lines_count - filtered
#        lines_after = lines_after - filtered_after

    if lines_count > window_height:
        differential = lines_count - window_height
        percent = max(int(round(100. * (differential - lines_after) / differential)), 0)
    else:
        percent = 100

    # get current position
    current_line = lines_count - lines_after

    return lines_after,lines_count,percent,current_line, filtered, filtered_before, filtered_after

def count_filtered_lines(ptr_buffer,lines_count,lines_after):
    filtered_before = 0
    filtered_after = 0
    filtered = 0

    lines = weechat.hdata_pointer(weechat.hdata_get('buffer'), ptr_buffer, 'own_lines')
    counter = 0
    current_position = lines_count - lines_after

    if lines:
        line = weechat.hdata_pointer(weechat.hdata_get('lines'), lines, 'first_line')
        hdata_line = weechat.hdata_get('line')
        hdata_line_data = weechat.hdata_get('line_data')

        while line:
            data = weechat.hdata_pointer(hdata_line, line, 'data')
            if data:
#                message = weechat.hdata_string(hdata_line_data, data, 'message')
                displayed = weechat.hdata_char(hdata_line_data, data, 'displayed')
                if displayed == 0:
#                    weechat.prnt('','%d - %s - %s' % (counter, displayed, message))
                    if counter < current_position:
                        filtered_before += 1
                    else:
                        filtered_after += 1
            counter += 1
            line = weechat.hdata_move(hdata_line, line, 1)

    filtered = filtered_before + filtered_after
    return filtered,filtered_before,filtered_after

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
    for option,value in OPTIONS.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, value[0])
            OPTIONS[option] = value[0]
        else:
            OPTIONS[option] = weechat.config_get_plugin(option)
        weechat.config_set_desc_plugin(option, "%s (default: '%s')" % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK
# ================================[ main ]===============================
if __name__ == "__main__":
#    global filter_status
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0

        if int(version) >= 0x00030600:
            filter_status = int(weechat.info_get('filters_enabled',''))
            bar_item = weechat.bar_item_new(SCRIPT_NAME, 'show_item','')
            weechat.bar_item_update(SCRIPT_NAME)
            weechat.hook_signal('buffer_line_added','update_cb','')
            weechat.hook_signal('window_scrolled','update_cb','')
            weechat.hook_signal('buffer_switch','update_cb','')
            weechat.hook_signal('*filters*','filtered_update_cb','')
            weechat.hook_command_run('/buffer clear*','update_cb','')
            weechat.hook_command_run('/window page*','update_cb','')
            weechat.hook_command_run('/input zoom_merged_buffer','update_cb','')
            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
            init_options()
        else:
            weechat.prnt('','%s%s %s' % (weechat.prefix('error'),SCRIPT_NAME,': needs version 0.3.6 or higher'))
