--[[
Author: singalaut <rumia.youkai.of.dusk@gmail.com>
License: WTFPL
URL: https://github.com/tomoe-mami/weechat-scripts/tree/master/nick_complete_wrapper

A script for adding custom prefix and/or suffix when doing nick completion.
Originally written to make nick completion in Bitlbee #twitter_* channels
prepended with '@'.

To use this script, set local variable `ncw_prefix` and/or `ncw_suffix` in the
buffer you want with `/buffer set` command. For example:

    /buffer set localvar_set_ncw_prefix @
    /buffer set localvar_set_ncw_suffix >

To delete those variables, replace `localvar_set` with `localvar_del`.
For example:

    /buffer set localvar_del_ncw_suffix 1

The '1' in the example above is just a dummy arg. Weechat requires 2 args
after `/buffer set `.

---------------------------------------------------------------------------------

For Lua < 5.3, luautf8 (https://luarocks.org/modules/xavier-wang/luautf8) module
is an optional (but recommended) dependency. In Lua 5.3, the script doesn't
have any dependency.
--]]

w, script_name = weechat, "nick_complete_wrapper"
config, hooks = {}, {}

function main()
   local reg = w.register(
      script_name, "singalaut <https://github.com/tomoe-mami>", "0.1", "WTFPL",
      "Wraps nick completion with prefix and/or suffix",
      "", "")
   if reg then
      check_utf8_support()
      config.nick_add_space = w.config_get("weechat.completion.nick_add_space")
      w.hook_command_run("9000|/input complete_*", "complete_cb", "")
   end
end

function check_utf8_support()
   if utf8 and type(utf8.len) == "function" then
      -- lua 5.3 with builtin utf8 support
      string_length = utf8.len
   else
      -- lua < 5.3 with [lua-]utf8 module
      local pkgs = { "lua-utf8", "utf8" }
      for _, searcher in ipairs(package.searchers or package.loaders) do
         for _, pkg_name in ipairs(pkgs) do
            local loader = searcher(pkg_name)
            if type(loader) == "function" then
               package.preload[pkg_name] = loader
               utf8 = require(pkg_name)
               if type(utf8.len) == "function" then
                  string_length = utf8.len
                  return
               end
            end
         end
      end
   end
   if not string_length then
      string_length = w.strlen_screen
   end
end

function get_completion(ptr_buffer)
   local t = {}
   local ptr_comp = w.hdata_pointer(w.hdata_get("buffer"), ptr_buffer, "completion")
   if ptr_comp and ptr_comp ~= "" then
      local h_comp = w.hdata_get("completion")
      t.start_pos = w.hdata_integer(h_comp, ptr_comp, "position_replace")
      t.word_found = w.hdata_string(h_comp, ptr_comp, "word_found")
      t.is_nick = w.hdata_integer(h_comp, ptr_comp, "word_found_is_nick") == 1
      t.is_command = w.hdata_string(h_comp, ptr_comp, "base_command") ~= ""
      if not t.is_command and t.word_found == "" then
         local last_nick = w.buffer_get_string(ptr_buffer, "localvar_ncw_last_nick")
         if last_nick ~= "" then
            t.word_found, t.is_nick = last_nick, true
            t.start_pos = tonumber(w.buffer_get_string(ptr_buffer, "localvar_ncw_last_pos")) or 0
            w.buffer_set(ptr_buffer, "localvar_del_ncw_last_nick", "")
            w.buffer_set(ptr_buffer, "localvar_del_ncw_last_pos", "")
         end
      end
      return t
   end
end

function get_prefix_suffix(ptr_buffer)
   return {
      prefix = w.buffer_get_string(ptr_buffer, "localvar_ncw_prefix"),
      suffix = w.buffer_get_string(ptr_buffer, "localvar_ncw_suffix")
   }
end

function cleanup_previous_completion(ptr_buffer)
   local ps = get_prefix_suffix(ptr_buffer)
   if ps.prefix == "" and ps.suffix == "" then
      return w.WEECHAT_RC_OK
   end
   local comp = get_completion(ptr_buffer)
   if comp and comp.is_nick and not comp.is_command then
      local current_pos = w.buffer_get_integer(ptr_buffer, "input_pos")
      local input = w.buffer_get_string(ptr_buffer, "input")
      local space = w.config_boolean(config.nick_add_space) and " " or ""
      local str_nick = ps.prefix..comp.word_found..ps.suffix..space
      local str_before = input:sub(1, comp.start_pos)
      if string_length(str_before..str_nick) == current_pos then
         w.buffer_set(ptr_buffer, "completion_freeze", "1")
         w.buffer_set(ptr_buffer, "input", str_before..comp.word_found..input:sub(comp.start_pos + #str_nick))
         w.buffer_set(ptr_buffer, "input_pos", string_length(str_before..comp.word_found..space))
         w.buffer_set(ptr_buffer, "completion_freeze", "0")
         w.buffer_set(ptr_buffer, "localvar_set_ncw_last_nick", comp.word_found)
         w.buffer_set(ptr_buffer, "localvar_set_ncw_last_pos", comp.start_pos)
      else
         w.buffer_set(ptr_buffer, "localvar_del_ncw_last_nick", "")
         w.buffer_set(ptr_buffer, "localvar_del_ncw_last_pos", "")
      end
   end
end

function complete_cb(_, ptr_buffer)
   cleanup_previous_completion(ptr_buffer)
   hooks[ptr_buffer] = w.hook_signal("input_text_changed", "input_changed_cb", ptr_buffer)
   return w.WEECHAT_RC_OK
end

function input_changed_cb(ptr_buffer)
   if not hooks[ptr_buffer] then
      return w.WEECHAT_RC_OK
   end
   w.unhook(hooks[ptr_buffer])
   hooks[ptr_buffer] = nil

   local ps = get_prefix_suffix(ptr_buffer)
   if ps.prefix == "" and ps.suffix == "" then
      return w.WEECHAT_RC_OK
   end

   local comp = get_completion(ptr_buffer)
   if not comp or comp.is_command or not comp.is_nick then
      return w.WEECHAT_RC_OK
   end

   local str_nick = ps.prefix..comp.word_found..ps.suffix
   if str_nick ~= comp.word_found then
      local input = w.buffer_get_string(ptr_buffer, "input")
      local current_pos = w.buffer_get_integer(ptr_buffer, "input_pos")
      local str_before = input:sub(1, comp.start_pos)
      local add_space = w.config_boolean(config.nick_add_space) and 1 or 0
      local str_after = input:sub(comp.start_pos + #comp.word_found + add_space)
      w.buffer_set(ptr_buffer, "completion_freeze", "1")
      w.buffer_set(ptr_buffer, "input", str_before..str_nick..str_after)
      w.buffer_set(ptr_buffer, "input_pos", string_length(str_before..str_nick) + add_space)
      w.buffer_set(ptr_buffer, "completion_freeze", "0")
   end

   return w.WEECHAT_RC_OK
end

main()
