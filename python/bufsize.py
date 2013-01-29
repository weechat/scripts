# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2013 by nils_2 <weechatter@arcor.de>
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
SCRIPT_VERSION  = "0.3"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "scroll indicator; displaying number of lines below last line, overall lines in buffer, number of current line and percent displayed"

OPTIONS         = { 'format'            : ('${yellow}%P${default}⋅%{${yellow}%A${default}⇵${yellow}%C${default}/}${yellow}%L',
                                           'format for items to display in bar, possible items: %P = percent indicator, %A = number of lines below last line, %L = lines counter, %C = current line'),                                           # %P = percent, %A = lines_after, %L = lines_count, %C = current
                   }
# ================================[ weechat item ]===============================
# regexp to match ${color} tags
regex_color=re.compile('\$\{([^\{\}]+)\}')

# regexp to match ${optional string} tags
regex_optional_tags=re.compile('%\{[^\{\}]+\}')

def show_item (data, item, window):
    bufpointer = weechat.window_get_pointer(window,"buffer")
    if bufpointer == "":
        return ""

    if weechat.buffer_get_string(bufpointer,'name') != 'weechat':                         # not weechat core buffer
        if weechat.buffer_get_string(bufpointer,'localvar_type') == '':                   # buffer with free content?
          return ""

    lines_after, lines_count, percent, current_line = count_lines(window,bufpointer)

    if lines_count == 0:                                                                  # buffer empty?
        return ""

    tags = {'%C': str(current_line),
            '%A': str(lines_after),
            '%L': str(lines_count),
            '%P': str(percent)+"%"}

    bufsize_item = substitute_colors(OPTIONS['format'])

    # replace mandatory tags
    for tag in list(tags.keys()):
#    for tag in tags.keys():
        bufsize_item = bufsize_item.replace(tag, tags[tag])

    # replace optional tags
    # %{…} only if lines after (e.g. %A > 0)
    if lines_after > 0:
        for regex_tag in regex_optional_tags.findall(bufsize_item):
            bufsize_item = bufsize_item.replace(regex_tag, regex_tag.lstrip('%{').rstrip('}'))
    else:
        bufsize_item = regex_optional_tags.sub('', bufsize_item)

    return bufsize_item

def substitute_colors(text):
    # substitute colors in output
    return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

def count_lines(winpointer,bufpointer):

    hdata_buf = weechat.hdata_get('buffer')
    hdata_lines = weechat.hdata_get('lines')
    lines = weechat.hdata_pointer(hdata_buf, bufpointer, 'lines') # own_lines, mixed_lines
    lines_count = weechat.hdata_integer(hdata_lines, lines, 'lines_count')

    hdata_window = weechat.hdata_get('window')
    hdata_winscroll = weechat.hdata_get('window_scroll')
    window_scroll = weechat.hdata_pointer(hdata_window, winpointer, 'scroll')
    lines_after = weechat.hdata_integer(hdata_winscroll, window_scroll, 'lines_after')
    window_height = weechat.window_get_integer(weechat.current_window(), 'win_chat_height')

    if lines_count > window_height:
        differential = lines_count - window_height
        percent = max(int(round(100. * (differential - lines_after) / differential)), 0)
    else:
        percent = 100
    #weechat.prnt('', " : lines_count "+str(lines_count)+" window_height "+str(window_height)+" lines after "+str(lines_after))
    current_line = lines_count - lines_after
    return lines_after,lines_count,percent, current_line

def update_cb(data, signal, signal_data):
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK

# ================================[ weechat options and description ]===============================
def init_options():
    for option,value in list(OPTIONS.items()):
        if not weechat.config_get_plugin(option):
          weechat.config_set_plugin(option, value[0])
    else:
        OPTIONS[option] = weechat.config_get_plugin(option)
    weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
    global OPTIONS
    option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
    OPTIONS[option] = value                                               # save new value
    weechat.bar_item_update(SCRIPT_NAME)
    return weechat.WEECHAT_RC_OK
# ================================[ main ]===============================
if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        version = weechat.info_get("version_number", "") or 0

        if int(version) >= 0x00030600:
            bar_item = weechat.bar_item_new(SCRIPT_NAME, 'show_item','')
            weechat.bar_item_update(SCRIPT_NAME)
            weechat.hook_signal("buffer_line_added","update_cb","")
            weechat.hook_signal("window_scrolled","update_cb","")
            weechat.hook_signal("buffer_switch","update_cb","")
            weechat.hook_command_run("/buffer clear*","update_cb","")
            weechat.hook_command_run("/window page*","update_cb","")
            weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
            init_options()
        else:
            weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.6 or higher"))
