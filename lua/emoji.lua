
--[[

Replaces :emojiname: in input with emoticon or :partial match<tab>

Copyright 2016 xt <xt@bash.no>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Changelog:
	version 6, 2025-11-2, nmz:
		* Download and use emoji db, not keep it in script itself
		* Linter: functions explicitly go to _G or are local
		* str2emoji(): simplify pattern, gsub points to table instead of function (faster)
		* use string.find in conditionals not string.match
		* tabcompletion goes to the last pattern, still buggy
	version 5, 2020-05-09, FlashCode:
		* remove obsolete comment on weechat_print modifier data
	version 4, 2017-10-12, massa1240
		* add support of :+1: and :-1:
	version 3, 2016-11-04, xt
		* add a slack specific shortcode
	version 2, 2016-10-31, xt
		* some cleanup
		* ability replace incoming
	version 1, 2016-02-29, xt
		* initial version
--]]


local SCRIPT_NAME     = "emoji"
local SCRIPT_AUTHOR   = "xt <xt@bash.no>"
local SCRIPT_VERSION  = "6"
local SCRIPT_LICENSE  = "GPL3"
local SCRIPT_DESC     = "Emoji output/input shortcode helper for WeeChat."

local filename = "emoji_shortcodes.po"
local url = "https://raw.githubusercontent.com"
	.. "/milesj/emojibase"
	.. "/refs/heads/master/po/base/shortcodes.po"

---------------------------------------------

local Exists = function (name) return os.rename(name, name) end
local ShellFormat = function (command)
	if type(command)=="table" then
		for i,v in ipairs(command) do
			command[i] = v:gsub("'","\\'")
		end
		command = "'" .. table.concat(command, "' '") .. "'"
	end
	return command
end

local function GetSize(file)
	local H = io.open(file)
	if not H then return -1 end
	local size = H:seek"end"
	H:close()
	return size
end

assert(os.execute"which curl > /dev/null", "curl not in $PATH")

local function Fetch(filepath)
	return assert(
		os.execute(
			ShellFormat{"curl","--silent", "-o", filepath, url}
		)
		, "Curl failed to fetch, url may be defunct"
	)
end

--------------------------------------------- Emojis

local emoji = {} -- { [name] = ":)" } table is at the end because its too big
	-- it must conform to str2emoji pattern below
	local cachedir = os.getenv"XDG_CACHE_HOME" or (os.getenv"HOME" .. "/.cache")
	if not Exists(cachedir) then
		assert(
			os.execute( ShellFormat{"mkdir", "-p", cachedir} )
			,"could not make cachedir"
		)
	end
	local filepath = cachedir .. "/" .. filename

	-- we check if same size, if yes download
	-- the proper method is using touch to set the same date metadata BUT
	-- lazy
	local function Download()
		local H = io.popen("curl -Is " .. url)
		local upstream_size = H:read"a":match"\ncontent%-length:%s+(%d+)"
		assert(H:close())
		upstream_size = tonumber(upstream_size) or error(
			string.format("Failed to get content-length: %s", upstream_size)
		)
		if GetSize(filepath) ~= upstream_size then -- different size, download
			return Fetch(filepath)
		end
	end

------------------------- Scanners

--[[
# COMMENT
RS=\n\n
var "text"
"" <- concatenated to the last var

but we don't care about that, only about msgctext or msgid
Which is supposed to be one line
--]]

-- This is more correct
local function ScanDataByItem(data)
	local c = 1
	local id, txt
	for v, val in data:gmatch'msg(%l+)%s+"(.-)"\n'
	do -- technically incorrect, but it works
		if id and txt then
			c = c+1
			local symbol, desc = txt:match'^EMOJI: (%S+) (.+)$'
			emoji[id] = symbol
			emoji[desc:gsub("%s","_")] = symbol
			id, txt = nil, nil
		end
		if v=="ctxt" then
			txt = val
		elseif v=="id" then
			id = val
		end
	end
end

-- Fast, but could lead to misses
local function ScanData(data)
	for moji, desc, id in data:gmatch
		'msgctxt%s+"EMOJI: (%S+) (.-)"\nmsgid%s+"(.-)"\n'
	do -- technically incorrect, but it works
		emoji[id] = moji
		emoji[desc:gsub("%s","_")] = moji
	end
end

local function ScanPOFile()
	local H = io.open(filepath)
	ScanData(H:read"a")
	H:close()
end

if not Exists(filepath) then
	Fetch(filepath)
end -- file does not exist, download

ScanPOFile()

--------------------------------------------- Emoticons

-- hardcoded emoticons for now
local emoticon = {} for k, v in pairs{
	spidermoji = [[/╲/\╭ºoꍘoº╮/\╱\]],
	invertedrocket = "╰⋃╯",
	delicious = "ლ(´ڡ`ლ)",
	idk = [[¯\_(ツ)_/¯]],
	why = "ಥ_ಥ",
	fliptable = [[(╯°□°）╯︵]],
	flippedtable = "┻━┻",
	[")"] = "•ᴗ•" ,
	success = "(•̀ᴗ•́)و",
	catmoji = "ฅ^•ﻌ•^ฅ",
	fight = " (ง ",
	waa = ".·´¯`(>▂<)´¯`·.",
	heyyou = "(☞ﾟヮﾟ)☞",
	fingers = "t(-.-'t)",
} do
	emoticon[k] = v
	emoji[k] = v
end

--------------------------------------------- Weechat

local function str2emoji(str)
	return str and str:gsub(':([%w_+-]+):', emoji) or ''
end

-- Guesses name of emoji from closest token name
local function Approximator(token)
	if emoji[token] then return emoji[token] end -- No guessing needed
	local repl
	-- Anchored search in emoji[]
	local last_nameN = 99999 -- 1/0 or inf?
	-- pairs is not sorted, so you must loop completely
	-- in order to get the biggest match
	for name, val in pairs(emoji) do
		if
			name:sub(1,#token)==token
			and #name<last_nameN
		then
			last_nameN = #name
			repl = val
		end
	end
	return repl -- string|nil
end

---------------------------------------------

-- luacheck: globals weechat
local w = weechat

if w then
	local function emoji_replace_input_string(buffer)
		-- Get input contents
		local input_s = w.buffer_get_string(buffer, 'input')
		-- Skip modification of settings
		if input_s:find('^/set ') then
			return w.WEECHAT_RC_OK
		end
		local new_input = str2emoji(input_s)
		if new_input~=input_s then
			w.buffer_set(buffer, 'input', new_input)
		end
		return w.WEECHAT_RC_OK
	end

	function _G.emoji_input_replacer(data, buffer, command)
		if command == '/input return' then
			return emoji_replace_input_string(buffer)
		end
		return w.WEECHAT_RC_OK
	end


	do --------( ALL DO THE SAME THING
		local function alias(data, modifier, modifier_data, msg)
		return str2emoji(msg)
		end
		_G.emoji_live_input_replace = alias
		_G.emoji_out_replace = alias
		_G.unshortcode_cb = alias
	end

	--[[ WARNING:
	This took me 6 hours in debugging, it was great code,
	I thought my code was buggy, I tried everything
	press tab, autocompletes last :token: from cursor position.

	But it was not to be

	whenever you have multiple emojis in the input, the cursor position is innacurate.
	Asking around, it seems its a problem of the terminal and its variable between terminals
	so no fix, this means, it cannot be done and if it is
	it will introduce a schroedingers bug/feature

	Here is the function, in case terminals are ever fixed
	(probably in the next 30 years or so?)
	the function may have bugs because I was constantly trying to find what the bug is
	THIS IS BUGGY, it was technically in a working state, but because it never worked
	I kept trying things, and now it probably doesn't
	----------------------------------------
	-- This completes when you press tab
	-- therefore you must get the last : from before the cursor position
	-- and see if it exists in the hash table
	function _G.emoji_tabcomplete_prev_cb(data, buffer, command)
		local input = w.buffer_get_string(buffer, 'input')
		local cursorp = w.buffer_get_integer(buffer, "input_pos")
		local input_before_cursor = input:sub(1, cursorp)
		local start, token = input_before_cursor:match"(.*):([%w_+-]+):$"
		if not token then
			return w.WEECHAT_RC_OK
		end

		local repl = emoji[token] or Approximator(token)
		if repl then
			local new_input = start .. repl .. input:sub(cursorp+1)
			w.buffer_set(buffer, 'input', new_input)
			return w.WEECHAT_RC_OK_EAT
		end
		return w.WEECHAT_RC_OK
	end
	--]]


	-- replaces all :tokens: finding closest matching tokens in emoji[]
	local function replace_all(data, buffer, command)
		local input = w.buffer_get_string(buffer, 'input')
		local new_input, changes = input:gsub(":([%w_+-]+):", Approximator)
		if changes>0 then
			w.buffer_set(buffer, 'input', new_input)
			return w.WEECHAT_RC_OK_EAT
		end
		return w.WEECHAT_RC_OK
	end

	-- replace last :token: finding closest matching tokens in emoji[]
	local function replace_last(data, buffer, command)
		local input = w.buffer_get_string(buffer, 'input')
		local cpos = w.buffer_get_integer(buffer, "input_pos")
		local new_input = input:gsub("(.*):([%w_+-]+):",
			function (a,b)
				local c = Approximator(b)
				if c then
					-- This is a guess, emoticons at least have more countable chars
					-- emoji's are usually 1 symbol
					cpos = (emoticon[b] and utf8.len(c) or 2) + cpos
					return a .. c
				end
				return nil
			end
			, 1
		)
		if input~=new_input then
			w.buffer_set(buffer, 'input', new_input)
			w.buffer_set(buffer, "input_pos", cpos)
			return w.WEECHAT_RC_OK_EAT
		end
		return w.WEECHAT_RC_OK
	end

	_G.emoji_tabcomplete_cb = replace_last -- Either this or replace_all

	function _G.emoji_completion_cb(data, completion_item, buffer, completion)
		for k, v in pairs(emoji) do
			w.hook_completion_list_add( -- WARNING: Due to the size of this, this might become hella slow
				completion,
				":"..k..":",
				0,
				w.WEECHAT_LIST_POS_SORT
			)
		end
		return w.WEECHAT_RC_OK
	end

	function _G.incoming_cb(data, modifier, modifier_data, msg)
		-- Only replace in incoming "messages"
		if modifier_data:find('nick_') then
			return str2emoji(msg)
		end
		return msg
	end

	if not w.register(
		SCRIPT_NAME,
		SCRIPT_AUTHOR,
		SCRIPT_VERSION,
		SCRIPT_LICENSE,
		SCRIPT_DESC,
		'',
		'')
	then
		return -- exit quickly
	end

	function _G.Update()
		if Download() then ScanPOFile() end
	end

	w.hook_command("emoji_updatedb", "Updates emoji database and reloads it"
	, "", "", "", "Update", "")

	-- Hook input enter
	w.hook_command_run('/input return', 'emoji_input_replacer', '')

	-- Hook irc out for relay clients
	-- this is gibberish, hook_signal should be used
	-- w.hook_modifier('input_text_for_buffer', 'emoji_out_replace', '')
	w.hook_modifier('irc_out1_PRIVMSG', 'emoji_out_replace', '')

	-- Replace while typing
	w.hook_modifier('input_text_display_with_cursor', 'emoji_live_input_replace', '')

	-- Hook tab complete -- Because of unknown multichar lengths, this is buggy.
	-- There is no way to know the cursor position accurately
	w.hook_command_run("/input complete_next", "emoji_tabcomplete_cb", "")

	w.hook_completion("emojis", "complete :emoji:s", "emoji_completion_cb", "")

	local settings = {
		incoming = {'on', 'Also try to replace shortcodes to emoji in incoming messages'}
	}

	-- set default settings
	local version = tonumber(w.info_get('version_number', '') or 0)
	for option, value in pairs(settings) do
		if w.config_is_set_plugin(option) ~= 1 then
			w.config_set_plugin(option, value[1])
		end
		if version >= 0x00030500 then
			w.config_set_desc_plugin(option,
				('%s (default: "%s")'):format(value[2], value[1])
			)
		end
	end

	-- Hook incoming message
	if w.config_get_plugin('incoming') == 'on' then
		w.hook_modifier("weechat_print", 'incoming_cb', '')
	end

	return true
end
