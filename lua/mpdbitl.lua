--[[
--    mpdbitl
--
--    Script that automatically change bitlbee status message into current MPD
--    track. Requires Weechat 0.3.5 or higher.
--
--    Author: rumia <rumia.youkai.of.dusk@gmail.com>
--    License: WTFPL
--]]

require "socket"

mpdbitl_config = {
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
mpdbitl_caught_messages    = 0
mpdbitl_msg_hook           = nil

-- 1: bitlbot, 2: account id/tag, 3: status message
mpdbitl_status_command_normal = "/mute -all msg %s account %s set status %s"

-- 1: nick/handle, 2: status message
mpdbitl_status_command_alternate = "/mute -all msg %s %s"

function mpdbitl_config_init()

   local structure = {
      general = {
         enable = {
            description = "Enable mpdbitl",
            default = true
         }
      },
      mpd = {
         hostname = {
            description = "Hostname of MPD server",
            default = "localhost"
         },
         port = {
            description = "Port used by MPD server",
            default = 6600,
            min = 1,
            max= 65535
         },
         password = {
            description = "Password used to authenticate to MPD server",
            default = ""
         },
         timeout = {
            description = "Connection timeout (in seconds)",
            default = 3,
            min = 1,
            max = 65535
         }
      },
      bitlbee = {
         network = {
            description = "Network ID for Bitlbee server",
            default = "localhost"
         },
         channel = {
            description = "Bitlbee main channel",
            default = "&bitlbee"
         },
         accounts = {
            description =
               "Comma separated list of Bitlbee account IDs/tags/handles. " ..
               "To specify a handle, prefix the entry with @",
            default = {0}
         },
         bitlbot = {
            description = "Bitlbee bot handle name",
            default = "root"
         },
         format_playing = {
            description = "Status format when MPD is playing a song",
            default = "mpdbitl: {{artist}} — {{title}}"
         },
         format_paused = {
            description = "Status format when MPD is paused",
            default = "mpdbitl (paused): {{artist}} — {{title}}"
         },
         format_stopped = {
            description = "Status format when MPD is stoppedsong",
            default = "mpdbitl (stopped): {{artist}} — {{title}}"
         },
         format_none = {
            description =
               "Status format when MPD is playlist is empty or MPD has reached " ..
               "the end of playlist and there's nothing else to play",
            default = "mpdbitl (not playing)"
         }
      }
   }

   mpdbitl_config_file =
      weechat.config_new(mpdbitl_config_file_name, "mpdbitl_config_reload", "")

   if mpdbitl_config_file == "" then
      return
   end

   for section_name, section_options in pairs(structure) do
      local section = weechat.config_new_section(
         mpdbitl_config_file, section_name,
         0, 0,
         "", "", "", "", "", "", "", "", "", "")

      if section == "" then
         weechat.config_free(mpdbitl_config_file)
         return
      end

      for option, definition in pairs(section_options) do
         local lua_type = type(definition.default)

         if lua_type == "number" then
            mpdbitl_config[option] =
               weechat.config_new_option(
                  mpdbitl_config_file,
                  section,
                  option,
                  "integer",
                  definition.description,
                  "",
                  (definition.min and definition.min or 0),
                  (definition.max and definition.max or 0),
                  definition.default,
                  definition.default,
                  0,
                  "", "", "", "", "", "")
         elseif lua_type == "boolean" then
            local default = definition.default and "on" or "off"
            mpdbitl_config[option] =
               weechat.config_new_option(
                  mpdbitl_config_file,
                  section,
                  option,
                  "boolean",
                  definition.description,
                  "",
                  0,
                  0,
                  default,
                  default,
                  0,
                  "", "", "", "", "", "")
         elseif lua_type == "table" or lua_type == "string" then
            local default = definition.default
            if lua_type == "table" then
               default = table.concat(
                           definition.default,
                           (definition.separator and definition.separator or ","))
            end

            mpdbitl_config[option] =
               weechat.config_new_option(
                  mpdbitl_config_file,
                  section,
                  option,
                  "string",
                  definition.description,
                  "",
                  0,
                  0,
                  default,
                  default,
                  0,
                  "", "", "", "", "", "")
         end
      end
   end
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
         password = password:gsub('\\', '\\\\')
         password = password:gsub('"', '\\"')
         local command = 'password "' .. password .. '"'

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
         _, _,
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

function mpdbitl_catch_bitlbot_response(total_msg, modifier, msg_network, string)
   if not total_msg or total_msg == "" then return string end
   if type(total_msg) == "string" then total_msg = tonumber(total_msg) end
   if total_msg < 1 or mpdbitl_caught_messages >= total_msg then
      return string
   end

   local network = weechat.config_string(mpdbitl_config.network)
   if network ~= msg_network then return string end

   local parsed = weechat.info_get_hashtable(
      "irc_message_parse",
      {message = string})

   if not parsed or type(parsed) ~= "table" then return string end

   local bitlbot = weechat.config_string(mpdbitl_config.bitlbot)
   if bitlbot ~= parsed.nick then return string end

   local expected_arg = string.format(
      "%s :status = `%s'",
      parsed.channel,
      mpdbitl_status_text)

   if parsed.arguments == expected_arg then
      mpdbitl_caught_messages = mpdbitl_caught_messages + 1
      if mpdbitl_caught_messages >= total_msg then
         if mpdbitl_msg_hook and mpdbitl_msg_hook ~= "" then
            weechat.unhook(mpdbitl_msg_hook)
         end
      end

      return ""
   else
      return string
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
   if weechat.nicklist_search_nick(buffer, "", bitlbot) == "" then
      mpdbitl_msg("No such nick: %s", bitlbot)
      return weechat.WEECHAT_RC_ERROR
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
         local command_for_bitlbot = {}

         for account in accounts:gmatch("[^,]+") do
            local _, _, target = account:find("^@(.+)")

            if not target then
               command_for_bitlbot[#command_for_bitlbot + 1] =
                  string.format(
                     mpdbitl_status_command_normal,
                     bitlbot,
                     mpdbitl_escape_bitlbee_command_arg(account),
                     mpdbitl_escape_bitlbee_command_arg(mpdbitl_status_text))
            else
               weechat.command(
                  buffer,
                  string.format(
                     mpdbitl_status_command_alternate,
                     target,
                     mpdbitl_status_text))
            end
         end

         weechat.bar_item_update("mpdbitl_track")
         if #command_for_bitlbot > 0 then
            mpdbitl_caught_messages = 0
            mpdbitl_msg_hook = weechat.hook_modifier(
               "irc_in2_PRIVMSG",
               "mpdbitl_catch_bitlbot_response",
               #command_for_bitlbot)

            for _, cmd in ipairs(command_for_bitlbot) do
               weechat.command(buffer, cmd)
            end
         end
      end

      return weechat.WEECHAT_RC_OK
   else
      return weechat.WEECHAT_RC_ERROR
   end
end

function mpdbitl_toggle()
   local current = weechat.config_boolean(mpdbitl_config.enable)
   local new_value = (current == 0 and 1 or 0)

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
      "1.2",
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
