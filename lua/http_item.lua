-- HTTP bar item, using lua patterns to get content
--
-- Copyright 2013 Tor Hveem <xt@bash.no>
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

--
-- Usage: put [http_item] in your status bar items.  (Or any other bar to your liking)
-- "/set weechat.bar.status.items".
--

local w = weechat


SCRIPT_NAME    = "http_item"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with HTTP source, using lua patterns to match content"
BAR_ITEM_NAME  = SCRIPT_NAME

-- Settings
settings = {
    url               = 'http://weechat.org/info/stable/',
    pattern           = '(%d+%.%d+%.%d+)',
    message_prefix    = 'Latest WeeChat: ',
    message_postfix   = '',
    message_color     = 'default',
    interval          = '5', -- poll every 5 minutes
}
-- other globals
ITEM_TEXT = nil

function http_bi_cb(data, item, window)
    -- Return the bar item string
    if ITEM_TEXT then
        return string.format('%s%s%s%s',
                w.config_get_plugin('message_prefix'),
                w.color(w.config_get_plugin('message_color')),
                ITEM_TEXT,
                w.config_get_plugin('message_postfix')
                )
    end
    return ''
end

function http_bi_update()
    -- Function to manually update the bar item
    w.bar_item_update(BAR_ITEM_NAME)
    return w.WEECHAT_RC_OK
end

function debug(buf, str)
    -- helper function for debugging
    local debug = false
    if debug and str then
        w.print(buf, SCRIPT_NAME .. ': ' .. str)
    end
    return w.WEECHAT_RC_OK
end

function init_config()
    -- Set defaults
    for option, default_value in pairs(settings) do
        if w.config_is_set_plugin(option) == 0 then
            w.config_set_plugin(option, default_value)
        end
    end
    -- read options from weechat into our lua table
    for option, default_value in pairs(settings) do
        settings[option] = w.config_get_plugin(option)
    end
    return w.WEECHAT_RC_OK
end

function start_fetch()
    -- Get URL using weechat API for URL
    local url = w.config_get_plugin('url')
    -- 30 seconds timeout
    local timeout = 30*1000
    debug('', url)
    w.hook_process('url:'..url, timeout, 'http_fetch_cb', '')
    return w.WEECHAT_RC_OK
end

function http_fetch_cb(data, command, return_code, out, err)
    if #out > 0 then
        out = out:match(w.config_get_plugin('pattern'))
        ITEM_TEXT = out
        debug('', ITEM_TEXT)
        -- Update bar item since we got new data
        w.bar_item_update(BAR_ITEM_NAME)
    end
    return w.WEECHAT_RC_OK
end

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '') then
    init_config()

    -- create the bar item
    w.bar_item_new(BAR_ITEM_NAME, 'http_bi_cb', '')

    -- Initial fetch
    start_fetch()

    -- hook the fetch timer
    w.hook_timer( w.config_get_plugin('interval')*60*1000, 0, 0, 'start_fetch', '')
end
