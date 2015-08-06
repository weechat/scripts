-- Copyright 2013 xt <xt@bash.no>
--
-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.
--


--[[

This script will try to prevent you from posting URLs to a buffer that was recently posted, as recently as your weechat will remember lines.

Usage:
    To get notice when trying to send old URL you will have to add a new item to
    your input bar. To override the default setting please run this command:

    /set weechat.bar.input.items "[input_prompt]+(away),[input_search],[input_paste],[input_olds],input_text"

    If you already have customized this setting, you will have to edit your own setting and add input_olds where you want it to be displayed.



    Changelog:
        version 2.1, 2015-08-06, boyska
            * FIX urls interpreted as patterns
        version 2, 2013-09-21, xt
            * Use hdata instead of infolines to improve performance
        version 1, 2013-09-15, xt
            * initial version
--]]

SCRIPT_NAME     = "oldswarner"
SCRIPT_AUTHOR   = "xt <xt@bash.no>"
SCRIPT_VERSION  = "2.1"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Warn user if about to paste URL already existing in buffer"

ITEM_NAME = 'input_olds'
ITEM_TEXT = ''

local w = weechat

local patterns = {
    -- X://Y url
    "^(https?://%S+)",
    "^<URL:(https?://%S+)>",
    "^<URL: (https?://%S+)>",
    "^<(https?://%S+)>",
    "^(https?://%S+)>",
    "%f[%S](https?://%S+)",
    -- www.X.Y url
    "^(www%.[%w_-%%]+%.%S+)",
    "%f[%S](www%.[%w_-%%]+%.%S+)",
}

-- return a table containing all urls in a message
function findURLs(message)
    local urls = {}

    local index = 1
    for split in message:gmatch('%S+') do
        for i=1, #patterns do
            local _, count = split:gsub(patterns[i], function(url)
                table.insert(urls, url)
            end)
            if(count > 0) then
                index = index + 1
                break
            end
        end
    end
    return urls
end

function is_url_in_buffer(buffer, url)
    lines = weechat.hdata_pointer(weechat.hdata_get('buffer'), buffer, 'own_lines')
    line = weechat.hdata_pointer(weechat.hdata_get('lines'), lines, 'first_line')
    hdata_line = weechat.hdata_get('line')
    hdata_line_data = weechat.hdata_get('line_data')
    while #line > 0 do
        data = weechat.hdata_pointer(hdata_line, line, 'data')
        message = weechat.hdata_string(hdata_line_data, data, 'message')
        if message:find(url, 1, true) ~= nil then
            return true
        end
        line = weechat.hdata_move(hdata_line, line, 1)
    end
    return false
end

function oldschecker(data, buffer, command)
    saved_input = weechat.buffer_get_string(buffer, "input")

    for _,url in pairs(findURLs(saved_input)) do
        if is_url_in_buffer(buffer, url) and not is_being_warned() then
            set_item_text()
            return weechat.WEECHAT_RC_OK_EAT
        end
    end
    clear_item_text()
    return w.WEECHAT_RC_OK
end

function set_item_text()
    message = 'URL already in buffer. Press enter again if you are sure'
    color = w.color(w.config_color(w.config_get('weechat.color.input_actions')))
    ITEM_TEXT = string.format('%s%s%s', color, message, w.color('reset'))
    w.bar_item_update(ITEM_NAME)
end

function clear_item_text()
    ITEM_TEXT = ''
    w.bar_item_update(ITEM_NAME)
end

function input_olds_cb(data, item, window)
    return ITEM_TEXT
end

function is_being_warned()
    if ITEM_TEXT == '' then
        return false
    end
    return true
end

function p_init()
    if w.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        '',
        '') then
        w.hook_command_run('/input return', 'oldschecker', '')

        -- create the bar item
        w.bar_item_new(ITEM_NAME, 'input_olds_cb', '')
    end
end

p_init()
