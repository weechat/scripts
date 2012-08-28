--[[
--    mpdbitl
--
--    Script that automatically change bitlbee status message into current MPD
--    track.
--
--    Author: rumia <rumia.youkai.of.dusk@gmail.com>
--    License: WTFPL
--
--    TODO:
--
--       - Filter out the replies from bitlbot to us without intercepting replies
--         for manual command sent by user.
--]]

require "socket"

mpdbitl_config =
{
   enable         = true,
   hostname       = "localhost",
   port           = 6600,
   password       = nil,
   timeout        = 1,
   network        = "localhost",
   channel        = "&bitlbee",
   bitlbot        = "root",
   accounts       = "",
   format_playing = "",
   format_paused  = "",
   format_stopped = "",
   format_none    = ""
}

mpdbitl_sock               = nil
mpdbitl_song_id            = nil
mpdbitl_error              = {}
mpdbitl_config_file        = nil
mpdbitl_current_state      = "stop"
mpdbitl_config_file_name   = "mpdbitl"
mpdbitl_status_text        = ""
mpdbitl_timer              = nil

-- 1: bitlbot, 2: account id/tag, 3: status message
mpdbitl_status_command_normal = "/mute -all msg %s account %s set status %s"

-- 1: nick/handle, 2: status message
mpdbitl_status_command_alternate = "/mute -all msg %s %s"

function mpdbitl_config_init()

   mpdbitl_config_file =
      weechat.config_new(mpdbitl_config_file_name, "mpdbitl_config_reload", "")

   if mpdbitl_config_file == "" then
      return
   end

   local general_section =
      weechat.config_new_section(
         mpdbitl_config_file, "general",
         0, 0,
         "", "", "", "", "", "", "", "", "", "")

   if general_section == "" then
      weechat.config_free(mpdbitl_config_file)
      return
   end

   mpdbitl_config.enable =
      weechat.config_new_option(
         mpdbitl_config_file, general_section,
         "enable", "boolean",
         "Enable mpdbitl",
         "", 0, 0,
         "on", "on",
         0, "", "", "", "", "", "")

   local section_mpd =
      weechat.config_new_section(
         mpdbitl_config_file, "mpd",
         0, 0,
         "", "", "", "", "", "", "", "", "", "")

   if section_mpd == "" then
      weechat.config_free(mpdbitl_config_file)
      return
   end

   mpdbitl_config.hostname =
      weechat.config_new_option(
         mpdbitl_config_file, section_mpd,
         "hostname", "string",
         "Hostname of MPD server",
         "", 0, 0,
         "localhost", "localhost",
         0, "", "", "", "", "", "")

   mpdbitl_config.port =
      weechat.config_new_option(
         mpdbitl_config_file, section_mpd,
         "port", "integer", "Port used by MPD server",
         "", 1, 65535,
         6600, 6600, 0,
         "", "", "", "", "", "")

   mpdbitl_config.password =
      weechat.config_new_option(
         mpdbitl_config_file, section_mpd,
         "password", "string",
         "Password used to authenticate to MPD server",
         "", 0, 0,
         "", "", 1,
         "", "", "", "", "", "")

   mpdbitl_config.timeout =
      weechat.config_new_option(
         mpdbitl_config_file, section_mpd,
         "timeout", "integer", "Connection timeout (in seconds)",
         "", 1, 65535,
         1, 1, 0,
         "", "", "", "", "", "")

   local section_bitlbee =
      weechat.config_new_section(
         mpdbitl_config_file,
         "bitlbee",
         0, 0, "", "", "", "", "", "", "", "", "", "")

   if section_bitlbee == "" then
      weechat.config_free(mpdbitl_config_file)
      return
   end

   mpdbitl_config.network =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "network", "string", "Network ID for Bitlbee server",
         "", 0, 0,
         "localhost", "localhost", 0,
         "", "", "", "", "", "")

   mpdbitl_config.channel =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "channel", "string", "Bitlbee main channel",
         "", 0, 0,
         "&bitlbee", "&bitlbee", 0,
         "", "", "", "", "", "")

   mpdbitl_config.accounts =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "accounts", "string",
         "Comma separated list of Bitlbee account IDs/tags/handles. " ..
         "To specify a handle, prefix the entry with @",
         "", 0, 0,
         "0", "0", 0,
         "", "", "", "", "", "")

   mpdbitl_config.bitlbot =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "bitlbot", "string", "Bitlbee bot handle name",
         "", 0, 0,
         "root", "root", 0,
         "", "", "", "", "", "")

   mpdbitl_config.format_playing =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "format_playing", "string", "Status format when MPD is playing a song",
         "", 0, 0,
         "mpdbitl: {{artist}} - {{title}}",
         "mpdbitl: {{artist}} - {{title}}",
         0,
         "", "", "", "", "", "")

   mpdbitl_config.format_paused =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "format_paused", "string", "Status format when MPD is paused",
         "", 0, 0,
         "mpdbitl (paused): {{artist}} - {{title}}",
         "mpdbitl (paused): {{artist}} - {{title}}",
         0,
         "", "", "", "", "", "")

   mpdbitl_config.format_stopped =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "format_stopped", "string", "Status format when MPD is stopped",
         "", 0, 0,
         "mpdbitl (stopped): {{artist}} - {{title}}",
         "mpdbitl (stopped): {{artist}} - {{title}}",
         0,
         "", "", "", "", "", "")

   mpdbitl_config.format_none =
      weechat.config_new_option(
         mpdbitl_config_file, section_bitlbee,
         "format_none", "string",
         "Status format when MPD playlist is empty or MPD has reached the " ..
         "end of playlist and there's nothing else to play",
         "", 0, 0,
         "mpdbitl (not playing)",
         "mpdbitl (not playing)",
         0,
         "", "", "", "", "", "")
end

function mpdbitl_config_reload(data, config_file)
   return weechat.config_reload(config_file)
end

function mpdbitl_config_read()
   return weechat.config_read(mpdbitl_config_file)
end

function mpdbitl_config_write()
   return weechat.config_write(mpdbitl_config_file)
end

function mpdbitl_msg(...)
   if arg and #arg > 0 then

      local format = ""
      if arg[0] then format = arg[0] end

      arg[0] = "mpdbitl\t" .. format
      weechat.print("", string.format(unpack(arg)))

   end
end

function mpdbitl_connect()

   mpdbitl_sock = socket.tcp()
   mpdbitl_sock:settimeout(weechat.config_integer(mpdbitl_config.timeout), "t")

   local hostname = weechat.config_string(mpdbitl_config.hostname)
   local port     = weechat.config_integer(mpdbitl_config.port)

   if not mpdbitl_sock:connect(hostname, port) then
      mpdbitl_msg("Could not connect to %s:%d", hostname, port)
      return false
   end

   local line = mpdbitl_sock:receive("*l")
   if not line then
      mpdbitl_msg("No response from MPD")
      return false
   end

   if not line:match("^OK MPD") then
      mpdbitl_msg("Unknown welcome message: %s", line)
      return false
   else
      local password = weechat.config_string(mpdbitl_config.password)
      if password and #password > 0 then

         local command = "password " .. mpdbitl_escape_mpd_command_arg(password)

         if mpdbitl_send_command(command) then
            local response = mpdbitl_fetch_all_responses()
            if mpdbitl_error.message then
               mpdbitl_msg("MPD error: %s", mpdbitl_error.message)
               return false
            end
         end

      end
      return true
   end
end


-- Escape arguments of MPD server's command. Do not use this for escaping
-- arguments of Bitlbee's command.
function mpdbitl_escape_mpd_command_arg(arg)
   if type(arg) == "number" then
      return arg
   elseif type(arg) == "string" then
      arg = arg:gsub('"', '\\"')
      arg = arg:gsub('\\', '\\\\')
      return '"' .. arg .. '"'
   else
      return ""
   end
end

function mpdbitl_disconnect()
   mpdbitl_send_command("close")
   mpdbitl_sock:close()
end

function mpdbitl_send_command(line)
   line = line .. "\n"
   local sent = mpdbitl_sock:send(line)
   return sent == #line
end

function mpdbitl_receive_single_response()
   local complete, key, value, _
   local error = {}

   local line = mpdbitl_sock:receive("*l")

   if line then
      if line:match("^OK$") then
         complete = true
      elseif line:match("^ACK") then
         error.code,
         error.index,
         error.command,
         error.message =
            line:find("^ACK %[(%d+)@(%d+)%] {([^}]+)\} (.+)")

         complete = true
      else
         _, _, key, value = line:find("^([^:]+):%s(.+)")
         if key then
            key = string.gsub(key:lower(), "-", "_")
         end
      end
   end

   return key, value, complete, error
end

function mpdbitl_fetch_all_responses()
   local result = {}
   local complete, key, value
   repeat
      key, value, complete, mpdbitl_error = mpdbitl_receive_single_response()
      if key then
         result[key] = value
      end
   until complete

   if mpdbitl_error.message then
      mpdbitl_msg(
         "MPD Error %s (%s @ %u): %s",
         mpdbitl_error.code,
         mpdbitl_error.command,
         mpdbitl_error.index,
         mpdbitl_error.message)
   end

   return result
end

function mpdbitl_get_server_status()
   if mpdbitl_send_command("status") then
      return mpdbitl_fetch_all_responses()
   else
      return false
   end
end

function mpdbitl_get_current_song()
   if mpdbitl_send_command("currentsong") then
      local song = mpdbitl_fetch_all_responses()
      if song.time then
         local duration = tonumber(song.time)
         local hours    = math.floor(duration / 3600) % 24
         local minutes  = math.floor(duration / 60) % 60
         local seconds  = duration % 60

         song.time = string.format("%02d:%02d", minutes, seconds)
         if hours > 0 then
            song.time = string.format("%02d:%s", hours, song.time)
         end
      end

      return song
   else
      return false
   end
end

function mpdbitl_format_status_text(text, replacement)
   if not text or not replacement or #text < 1 or type(replacement) ~= "table" then
      return ""
   end

   return text:gsub("{{([^}]+)}}", function (key)
         if replacement[key] then
            return replacement[key]
         else
            return ""
         end
      end)
end

function mpdbitl_bar_item(data, item, window)
   return mpdbitl_status_text
end

function mpdbitl_escape_bitlbee_command_arg(arg)
   if type(arg) == 'number' then
      return arg
   elseif type(arg) == 'string' then
      return "'" .. arg:gsub("'", "\\'") .. "'"
   else
      return "''"
   end
end

function mpdbitl_change_bitlbee_status(data, remaining_calls)

   local network  = weechat.config_string(mpdbitl_config.network)
   local channel  = weechat.config_string(mpdbitl_config.channel)
   local buf_id   = network .. "." .. channel
   local buffer   = weechat.buffer_search("irc", buf_id)

   if buffer == "" then
      mpdbitl_msg("No buffer for %s", buf_id)
      return weechat.WEECHAT_RC_OK
   end

   local bitlbot = weechat.config_string(mpdbitl_config.bitlbot)
   if weechat.info_get("irc_is_nick", bitlbot) ~= "1" then
      mpdbitl_msg("Invalid bitlbot handler: %s", bitlbot)
      return weechat.WEECHAT_RC_OK
   end

   local change_status = false
   if mpdbitl_connect() then
      local server_status  = mpdbitl_get_server_status()

      if server_status.state ~= mpdbitl_current_state or server_status.songid ~= mpdbitl_song_id then
         local format = ""

         if server_status.state == "play" then
            format = mpdbitl_config.format_playing
         elseif server_status.state == "pause" then
            format = mpdbitl_config.format_paused
         elseif server_status.state == "stop" then
            if not server_status.songid then
               format = mpdbitl_config.format_none
            else
               format = mpdbitl_config.format_stopped
            end
         else
            mpdbitl_msg("Unknown state: %s", server_status.state)
            mpdbitl_disconnect()
            return weechat.WEECHAT_RC_ERROR
         end

         change_status           = true
         mpdbitl_current_state   = server_status.state
         mpdbitl_song_id         = server_status.songid
         mpdbitl_status_text     = mpdbitl_format_status_text(
                                    weechat.config_string(format),
                                    mpdbitl_get_current_song())
      end

      mpdbitl_disconnect()

      if change_status then
         local accounts = weechat.config_string(mpdbitl_config.accounts)

         for account in accounts:gmatch("[^,]+") do
            local _, _, target = account:find("^@(.+)")
            local irc_command

            if not target then
               irc_command =
                  string.format(
                     mpdbitl_status_command_normal,
                     bitlbot,
                     mpdbitl_escape_bitlbee_command_arg(account),
                     mpdbitl_escape_bitlbee_command_arg(mpdbitl_status_text))
            else
               irc_command =
                  string.format(
                  mpdbitl_status_command_alternate,
                  target,
                  mpdbitl_status_text)
            end

            weechat.command(buffer, irc_command)
         end

         weechat.bar_item_update("mpdbitl_track")
      end

      return weechat.WEECHAT_RC_OK
   else
      return weechat.WEECHAT_RC_ERROR
   end
end

function mpdbitl_toggle()
   local current = weechat.config_boolean(mpdbitl_config.enable)
   local new_value

   if current == 1 then
      new_value = 0
   else
      new_value = 1
   end

   local result = weechat.config_option_set(mpdbitl_config.enable, new_value, 1)
   if new_value == 1 then
      mpdbitl_set_timer()
   else
      mpdbitl_unset_timer()
   end

   return weechat.WEECHAT_RC_OK
end

function mpdbitl_set_timer()
   if not mpdbitl_timer then
      mpdbitl_timer = weechat.hook_timer(
                        60 * 1000, 60, 0,
                        "mpdbitl_change_bitlbee_status", "")
   end
end

function mpdbitl_unset_timer()
   if mpdbitl_timer then
      weechat.unhook(mpdbitl_timer)
   end
end

function mpdbitl_command(data, buffer, arg_string)
   local args = {}

   arg_string:gsub("([^ \t]+)", function (s) args[#args + 1] = s end)

   if #args < 1 then
      return weechat.WEECHAT_RC_OK
   end

   if args[1] == "toggle" then
      return mpdbitl_toggle()
   elseif args[1] == "change" then
      return mpdbitl_change_bitlbee_status()
   else
      mpdbitl_msg("Unknown command: %s", args[1])
      return weechat.WEECHAT_RC_ERROR
   end
end

function mpdbitl_unload()
   mpdbitl_config_write()
   return weechat.WEECHAT_RC_OK
end

function mpdbitl_initialize()
    weechat.register(
      "mpdbitl",
      "rumia <https://github.com/rumia>",
      "1.1",
      "WTFPL",
      "Automatically change bitlbee status message into current MPD track",
      "mpdbitl_unload",
      "")

   mpdbitl_config_init()
   mpdbitl_config_read()

   weechat.bar_item_new("mpdbitl_track", "mpdbitl_bar_item", "")

   weechat.hook_command(
      "mpdbitl",
      "Change bitlbee status message into current MPD track",
      "toggle|change",
      "toggle: enable/disable script\n" ..
      "change: change bitlbee status immediately\n",
      "toggle || change",
      "mpdbitl_command",
      "")

   local enabled = weechat.config_boolean(mpdbitl_config.enable)
   if enabled == 1 then
      mpdbitl_set_timer()
   end
end

mpdbitl_initialize()
