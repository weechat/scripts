-- Copyright 2010 Vaughan Newton <balkrah@gmail.com>
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

SCRIPT_NAME		= "text_effects"
SCRIPT_AUTHOR	= "Vaughan Newton <balkrah@gmail.com>"
SCRIPT_VERSION	= "1.1"
SCRIPT_LICENSE	= "GPL3"
SCRIPT_DESC		= "Adds effects to words surrounded by certain characters"

local w = weechat

w.register(
	SCRIPT_NAME,
	SCRIPT_AUTHOR,
	SCRIPT_VERSION,
	SCRIPT_LICENSE,
	SCRIPT_DESC,
	"", ""
)

-- Effects
effects = {
	["*"] = "bold",
	["_"] = "underline",
}

-- printf function
function printf(buffer, fmt, ...)
	w.print(buffer, string.format(fmt, unpack(arg)))
end

-- Easy callback handling
local nextCallbackID = 0
function callback(f)
	local name = "__callback_" .. nextCallbackID
	nextCallbackID = nextCallbackID + 1
	_G[name] = f
	return name
end

-- Config
config = { data = {} }
setmetatable(config, {
	__index = function (tab, key)
		return w.config_string(tab.data[key])
	end,
})
-- Load config
do
	config.file = w.config_new("text_effects", callback(function(data, file)
		return w.config_reload(file)
	end), "")
	if not config.file then return end
	config.look = w.config_new_section(
			config.file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "")

	local c = config.data
	
	c.show_chars = w.config_new_option(
			config.file, config.look,
			"show_chars", "boolean", "Whether to show surrounding characters or not",
			"", 0, 0, "on", "on", 0, "", "", "", "", "", "")
	
	w.config_read(config.file)
end

-- Register modifier
w.hook_modifier("weechat_print", callback(function(_, _, info, str)

	-- Add spaces to help pattern matching
	str = " " .. str .. " "

	local pattern = "(%s)(["
	for char, effect in pairs(effects) do
		pattern = pattern .. "%"..char
	end
	pattern = pattern .. "])([%w_]+)%2(%s)"

	str = str:gsub(pattern, function(sp1, char, word, sp2)
		local effect = effects[char]
		local c = (config.show_chars == "on") and char or ""
		return sp1 .. w.color(effect) .. c .. word .. c ..
				w.color("-"..effect) .. sp2
	end)

	-- Remove spaces
	str = str:sub(2, -2)

	return str
	
end), "")

