
-- cmus_announce.lua - Announce currently playing file in cmus to channel

--[[
BSD Zero Clause License

iCopyright © 2024-2024 by <khwerz+weechat@gmail.com>

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
--]]

--[[
NOTE!
	cmus-remote could hang if you don't have mpris installed giving you a warning at the beginning

Design
	A defaultFormat is passed to cmus format_print, output is absorbed and s/\n/ /
	be aware that spaces in cmus become newlines, so s/\n/ / is used
	string.sub is run to limit the output

TODO
	Probably add/support colors %{red} and so on
	defaultFormat should be more colorful, with some emojis
--]]

local defaultFormat = "%{artist} - %{album} - %{title}"
local msgLimit = 250

local
	io, string, os
	=
	io, string, os

local Gsub = string.gsub

local ShellArgS = function -- string
(
	cmdS -- string
)
	return "'" .. Gsub(cmdS, "'","'\\''") .. "'"
end

local ExistsB, Exists do
	local Rename = os.rename
	ExistsB = function(fileS)
	-- returns true/false if fileS exists
		local B, _, code = Rename(fileS,fileS)
		return B or code==13
	end

	-- returns fileS if fileS exists or falsy
	Exists = function(fileS)
		return ExistsB(fileS) and fileS
	end
end

local Getenv = os.getenv

local XDG_RUNTIME_DIR =
	Getenv"XDG_RUNTIME_DIR"
	or "/run/nmz"

local cmusSocketFile = Getenv"CMUS_SOCKET"


local IsAlive = function ()
	if cmusSocketFile then
		return ExistsB(cmusSocketFile)
	end
	cmusSocketFile = Exists(XDG_RUNTIME_DIR .. "/cmus-socket")
	return cmusSocketFile
end

-- Get Current Song
local Current = function -- string
(
	format -- string|falsy
)
	format = format or defaultFormat

	local arg = ShellArgS("format_print " .. format)
	local S
	do
		local H = io.popen("cmus-remote -C " .. arg)
		S = H:read"a"
		H:close()
	end
	return S or ""
end

-- displays filename if nothing useful returns
local Display = function -- string
(
	format -- string|nil
)
	local msg = Current(format)
	-- if Current is empty, then just print {path}
	if not msg:match"[%ul]+" then
		msg = Current"%{filename}"
	end
	msg =
		Gsub(msg or "", "%s+"," ")
		:gsub("^%s+","")
		:gsub("%s+$","")
		-- spaces turn into newlines, this reverses that
	return msg
end

if weechat then --------------------------- Weechat Section
	local w = weechat

	do local name, author, version, license, description, shutdown_function, charset
	 name		= "cmus_announce"
	 author 	= "nmz"
	 version	= "1"
	 license	= "0BSD"
	 description	= "Messages current buffer/channel the currently listened to song"
	 charset	= ""
	 shutdown_function = ""
	 w.register(name, author, version, license, description, shutdown_function, charset)
	end

	-- semi global variables
	local OK,ERR = w.WEECHAT_RC_OK, w.WEECHAT_RC_ERROR

	local Sub = string.sub

	-- data, buffer, args(string)
	function cmus_announce(d,b,a)
		if IsAlive() then
			local msg = Sub(Display(a:match"%%{%g+}" and a),1,msgLimit) -- BUG: if its utf8 this might cut the last byte
			w.command(b, "/me Is Listening To: " .. msg)
		else
			w.print("","cmus_announce.lua: cmus is not running!")
			-- return ERR
		end
		return OK
	end

	-- should be a /me
	do
		local command = "cmus_announce"
		local description = 'Announces currently playing song in current buffer'
		local args = 'format'
		local args_description =
			"passed to cmus-remote command, so look at cmus(1) for the relevant formatting"
		local completion = ""
		local callback = command
		local callback_data = ""
		w.hook_command(command, description, args, args_description, completion, callback, callback_data)
	end
	return OK
end -- weechat

-- This is also a program which you can run as well.
-- run it to test it.
if ...==nil then
	if IsAlive() then
		print(os.date())
		print(Display())
		os.exit(0)
	end

	os.exit(1)
end