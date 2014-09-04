--[[

urlselect - A script for interactively select URL and perform an action on it

To activate, run /urlselect. View the README at
https://github.com/tomoe-mami/weechat-scripts/tree/master/urlselect for more
information.

Author: tomoe-mami/singalaut <rumia.youkai.of.dusk@gmail.com>
License: WTFPL
Requires: Weechat 1.0+

]]

local w = weechat
local g = {
   script = {
      name = "urlselect",
      version = "0.4",
      author = "tomoe-mami <rumia.youkai.of.dusk@gmail.com>",
      license = "WTFPL",
      description = "Interactively select URL"
   },
   defaults = {
      scan_merged_buffers = {
         type = "boolean",
         value = "0",
         description =
            "Scan URLs from buffers that are merged with the current one"
      },
      tags = {
         type = "list",
         value = "notify_message,notify_private,notify_highlight",
         description =
            "Comma separated list of tags. If not empty, script will only " ..
            "scan URLs from messages with any of these tags"
      },
      time_format = {
         type = "string",
         value = "%H:%M:%S",
         description = "Format of time"
      },
      status_timeout = {
         type = "number",
         value = "1300",
         description =
            "Timeout for displaying status notification (in milliseconds)"
      },
      buffer_name = {
         type = "string",
         value = "normal",
         description =
            "Type of name to use inside urlselect_buffer_name item. " ..
            "Valid values are \"full\", \"normal\", and \"short\""
      },
      use_simple_matching = {
         type = "boolean",
         value = "0",
         description = "Use simple pattern matching when scanning for URLs"
      },
      url_color = {
         type = "string",
         value = "_lightblue",
         description = "Color for URL"
      },
      nick_color = {
         type = "string",
         value = "",
         description =
            "Color for nickname. Leave empty to use Weechat's nick color"
      },
      highlight_color = {
         type = "string",
         value =
            "${weechat.color.chat_highlight},${weechat.color.chat_highlight_bg}",
         description = "Nickname color for highlighted message"
      },
      index_color = {
         type = "string",
         value = "brown",
         description = "Color for URL index"
      },
      message_color = {
         type = "string",
         value = "default",
         description = "Color for message text"
      },
      time_color = {
         type = "string",
         value = "default",
         description = "Color for time"
      },
      title_color = {
         type = "string",
         value = "default",
         description = "Color for bar title"
      },
      key_color = {
         type = "string",
         value = "cyan",
         description = "Color for list of keys"
      },
      buffer_number_color = {
         type = "string",
         value = "brown",
         description = "Color for buffer number"
      },
      buffer_name_color = {
         type = "string",
         value = "green",
         description = "Color for buffer name"
      },
      help_color = {
         type = "string",
         value = "default",
         description = "Color for help text"
      },
      status_color = {
         type = "string",
         value = "black,green",
         description = "Color for status notification"
      },
      search_scope = {
         type = "string",
         value = "url",
         valid_values = {
            url = true, msg = true,
            nick = true, ["nick+msg"] = true
         },
         description =
            "Default search scope. Valid values are: url, msg, nick or nick+msg"
      },
      search_prompt_color = {
         type = "string",
         value = "default",
         description = "Color for search prompt"
      },
      search_scope_color = {
         type = "string",
         value = "green",
         description = "Color for current search scope"
      }
   },
   config = {},
   active = false,
   list = "",
   bar_items = { 
      list = { "index", "nick", "url", "time", "duplicate",
               "message", "buffer_name", "buffer_number"},
      extra = { "title", "help", "status", "search"}
   },
   custom_commands = {},
   hooks = {},
   current_status = "",
   enable_help = false,
   last_index = 0,
   enable_search = false,
   search_scope = 1,
   scope_list = {"url", "msg", "nick", "nick+msg"}
}

g.bar = {
   main = { name = g.script.name },
   search = { name = g.script.name .. "_search" },
   help = { name = g.script.name .. "_help" }
}

g.keys = {
   normal = {
      ["meta2-B"]    = "navigate next",
      ["meta2-A"]    = "navigate previous",
      ["meta2-1~"]   = "navigate last",
      ["meta2-4~"]   = "navigate first",
      ["ctrl-P"]     = "navigate previous-highlight",
      ["ctrl-N"]     = "navigate next-highlight",
      ["ctrl-S"]     = "hsignal",
      ["ctrl-C"]     = "deactivate",
      ["ctrl-F"]     = "search",
      ["meta-OP"]    = "help",
      ["meta2-11~"]  = "help"
    },
   search = {
      ["ctrl-I"]     = "scope next",
      ["meta2-Z"]    = "scope previous",
      ["ctrl-N"]     = "scope nick",
      ["ctrl-T"]     = "scope msg",
      ["ctrl-U"]     = "scope url",
      ["ctrl-B"]     = "scope nick+msg"
   }
}

function unload_cb()
   if g.search_scope and g.scope_list[g.search_scope] then
      w.config_set_plugin("search_scope", g.scope_list[g.search_scope])
   end
end

function set_default_open_command_cb(_, cmd, ret, out, err)
   if ret == w.WEECHAT_HOOK_PROCESS_ERROR or ret >= 0 then
      local open_cmd = "xdg-open"
      if out and out:match("^([^%s]+)") == "Darwin" then
         open_cmd = "open"
      end
      w.config_set_plugin("cmd.o", "/exec -bg -nosh " .. open_cmd .. " ${url}")
      w.config_set_plugin("label.o", open_cmd)
   end
end

function setup()
   assert(
      w.register(
         g.script.name,
         g.script.author,
         g.script.version,
         g.script.license,
         g.script.description,
         "unload_cb", ""),
      "Unable to register script. Perhaps it's already loaded before?")

   local wee_ver = tonumber(w.info_get("version_number", "") or 0)
   if wee_ver < 0x01000000 then
      error("This script requires WeeChat v1.0 or higher")
   end

   local first_run, total_cmd = init_config()
   setup_hooks()
   if total_cmd == 0 and first_run then
      print("No custom commands configured. Adding default custom command...")
      w.hook_process("uname -s", 5000, "set_default_open_command_cb", "")
      w.config_set_plugin("cmd.i", "/input insert ${url}\\x20")
      w.config_set_plugin("label.i", "insert into input bar")
   end
   setup_bar()

   if g.config.search_scope then
      cmd_action_search_scope(nil, g.config.search_scope)
   end
end

function print(msg, param)
   if not param or type(param) ~= "table" then
      param = {}
   end
   param.script_name = g.script.name
   if not param.no_eval then
      msg = w.string_eval_expression(msg, {}, param, {})
   end
   local prefix = g.script.name
   if param.prefix_type then
      prefix = w.color("chat_prefix_" .. param.prefix_type) .. prefix
   end
   w.print("", prefix .. "\t" .. msg)
end

function get_or_set_option(name, info, value)
   local is_set = true
   if not value then
      if w.config_is_set_plugin(name) ~= 1 then
         is_set = false
         if info.type == "string" then
            value = w.string_eval_expression(info.value, {}, {}, {})
         else
            value = info.value
         end
         w.config_set_plugin(name, value)
         if info.description then
            w.config_set_desc_plugin(name, info.description)
         end
      else
         value = w.config_get_plugin(name)
      end
   end
   if info.type == "list" then
      local list = {}
      for item in value:gmatch("([^,]+)") do
         table.insert(list, item:lower())
      end
      value = list
   elseif info.type == "string" and info.valid_values then
      if not info.valid_values[value] then
         value = info.value
      end
   elseif info.type == "boolean" or info.type == "number" then
      value = tonumber(value)
      if info.type == "boolean" then
         value = value and value ~= 0
      end
   end
   return value, is_set
end

function init_config()
   local total_cmd, not_set, first_run = 0
   for name, info in pairs(g.defaults) do
      g.config[name], is_set = get_or_set_option(name, info)
      if first_run == nil and not is_set then
         first_run = true
      end
   end

   local prefix = "plugins.var.lua." .. g.script.name .. ".cmd."
   local cfg = w.infolist_get("option", "", prefix .. "*")
   if cfg and cfg ~= "" then
      while w.infolist_next(cfg) == 1 do
         local opt_name = w.infolist_string(cfg, "full_name")
         local opt_value = w.infolist_string(cfg, "value")
         local key = opt_name:sub(#prefix + 1)
         if key then
            local label = w.config_get_plugin("label." .. key)
            if set_custom_command(key, opt_value, label, true) then
               total_cmd = total_cmd + 1
            end
         end
      end
      w.infolist_free(cfg)
   end
   return first_run, total_cmd
end

function set_custom_command(key, cmd, label, silent)
   if not key or not key:match("^[0-9a-z]$") then
      w.config_unset_plugin("cmd." .. key)
      if not silent then
         print(
            "You can only bind 1 character for custom command. " ..
            "Valid type of character are digit (0-9) and lowercase " ..
            "alphabet (a-z) ",
            { prefix_type = "error" })
      end
      return false
   else
      local key_code = "meta-" .. key
      if not cmd or cmd == "" then
         if g.keys.normal[key_code] then g.keys.normal[key_code] = nil end
         if g.custom_commands[key] then g.custom_commands[key] = nil end
         if not silent then
            print("Key ${color:bold}${key}${color:-bold} removed", { key = key })
         end
      else
         g.keys.normal[key_code] = "run " .. key
         g.custom_commands[key] = { command = cmd }
         if not label then
            label = w.config_get_plugin("label." .. key)
         end
         if label and label ~= "" then
            g.custom_commands[key].label = label
         end
         if not silent then
            print(
               "Key ${color:bold}alt-${key}${color:-bold} bound to command: " ..
               "${color:bold}${cmd}${color:-bold}",
               { key = key, cmd = cmd })
         end
      end
      return true
   end
end

function set_custom_label(key, label)
   if key and key ~= "" and g.custom_commands[key] then
      if not label or label == "" then
         g.custom_commands[key].label = nil
      else
         g.custom_commands[key].label = label
      end
   end
end

function setup_hooks()
   w.hook_config("plugins.var.lua." .. g.script.name .. ".*", "config_cb", "")
   w.hook_command(
      g.script.name,
      "Control urlselect script",
      "[activate [current|merged]] " ..
      "|| bind [-label <label>] <key> <command> " ..
      "|| unbind <key> [<key> ...]" ..
      "|| list-commands " ..
      "|| deactivate " ..
      "|| navigate <direction> " ..
      "|| run <key> " ..
      "|| search " ..
      "|| scope <new-scope> " ..
      "|| hsignal " ..
      "|| help",
[[
      activate: Activate the URL selection bar (default action). The optional
                parameter `current` and `merged` can be used to force script to
                scan only on current buffer or all currently merged buffers.
          bind: Bind a key to a Weechat command. You can use optional parameter
                -label to specify the text that will be shown in help bar.
        unbind: Unbind key.
 list-commands: List all custom commands and their keys.
         <key>: A single digit character (0-9) or one lowercase alphabet (a-z).
     <command>: Weechat command. You can specify multiple commands by using ; as
                separator. To use literal semicolon, prepend it with a backslash.
                Inside a command the following variables will be replaced with
                their corresponding values from the currently selected URL:
                ${url}, ${nick}, ${time}, ${message}, ${index}, ${buffer_name},
                ${buffer_full_name}, ${buffer_short_name}, ${buffer_number}

The following actions are only available when the selection bar is active and
already bound to keys (see KEY BINDINGS below). You'll never need to use these
manually:

    deactivate: Deactivate URL selection bar.
      navigate: Navigate within the list of URLs.
           run: Run the command bound to a key.
        search: Toggle search bar.
         scope: Change search scope.
       hsignal: Send a "urlselect_current" hsignal with data from currently
                selected URL.
          help: Toggle help bar.
   <new-scope>: New search scope. Valid values are: next, previous, url, nick,
                msg, nick+msg
   <direction>: Direction of movement.
                Valid values are: next, previous, first, last,
                next-highlight, previous-highlight.

KEY BINDINGS
--------------------------------------------------------------
       Ctrl-C: Close/deactivate URL selection bar.
       Ctrl-F: Toggle search bar
           Up: Move to previous (older) URL.
         Down: Move to next (newer) URL.
         Home: Move to oldest URL.
          End: Move to newest URL.
       Ctrl-P: Move to previous URL that contains highlight.
       Ctrl-N: Move to next URL that contains highlight.
       Ctrl-S: Send hsignal.
 Alt-[0-9a-z]: Run custom command.
           F1: Toggle help bar.

The keys below are only available if search bar is active

          Tab: Switch to next scope
    Shift-Tab: Switch to previous scope
       Ctrl-N: Search only in nicknames
       Ctrl-T: Search only in messages
       Ctrl-U: Search only in URLs
       Ctrl-B: Search both in nicknames and messages

]],
      "activate current|merged || bind -label || unbind || list-commands ||" ..
      "deactivate || run || search || help ||" ..
      "navigate next|previous|first|last|previous-highlight|next-highlight ||" ..
      "scope next|previous|url|nick|msg|nick+msg",
      "command_cb",
      "")
end

function set_keys(buffer, key_type, flag)
   local prefix = flag and "key_bind_" or "key_unbind_"
   local cmd
   for key, val in pairs(g.keys[key_type]) do
      if not flag then
         cmd = ""
      elseif val:sub(1, 1) == "/" then
         cmd = val
      else
         cmd = string.format("/%s %s", g.script.name, val)
      end
      w.buffer_set(buffer, prefix .. key, cmd)
   end
end

function set_bar(key, flag)
   if g.bar[key].ptr and g.bar[key].ptr ~= "" then
      if not flag then
         w.bar_set(g.bar[key].ptr, "hidden", "on")
      else
         w.bar_set(g.bar[key].ptr, "hidden", "off")
      end
   end
end

function extract_nick_from_tags(tags)
   tags = "," .. tags .. ","
   local nick = tags:match(",nick_([^,]+),")
   return nick, tags
end

function split(text, delim)
   local s, c = text .. delim
   local start, p1, p2 = 1, 1, 0
   local e = "\\" .. delim:gsub("([^%w])", "%%%1")

   return function ()
      while p1 do
         p1, p2 = s:find(delim, start, true)
         if not p1 then
            return nil
         else
            local o = p1 - 1
            if s:sub(o, o) ~= "\\" then
               c = s:sub(1, o):gsub(e, delim)
               s = s:sub(p2 + 1)
               start = 1
               break
            else
               start = p2 + 1
            end
         end
      end
      return c, s
   end
end

function find_tag(tag_string, tag_list)
   tag_string = "," .. tag_string:lower() .. ","
   for _, tag in ipairs(tag_list) do
      local p = tag_string:find("," .. tag:lower() .. ",", 1, true)
      if p then
         return tag
      end
   end
end

function new_line_cb(buffer, evbuf, date, tags,
                     displayed, highlighted, prefix, message)
   if displayed == 1 and g.list and g.list ~= "" then
      if g.config.scan_merged_buffers then
         local evbuf_num = w.buffer_get_integer(evbuf, "number")
         local buf_num = w.buffer_get_integer(buffer, "number")
         if evbuf_num ~= buf_num then
            return
         end
      elseif buffer ~= evbuf then
         return
      end

      if g.config.tags and
         #g.config.tags > 0 and
         not find_tag(tags, g.config.tags) then
         return
      end

      local data, indexes = {}, {}
      data.nick = extract_nick_from_tags(tags)
      data.prefix = w.string_remove_color(prefix, "")
      data.message = message
      data.time = tonumber(date)
      data.highlighted = highlighted
      data.buffer_full_name = w.buffer_get_string(evbuf, "full_name")
      data.buffer_name = w.buffer_get_string(evbuf, "name")
      data.buffer_short_name = w.buffer_get_string(evbuf, "short_name")
      data.buffer_number = w.buffer_get_integer(evbuf, "number")

      process_urls_in_message(data.message, function (url, msg)
         data.message = msg
         data.index = g.last_index + 1
         g.last_index = data.index
         table.insert(indexes, data.index)

         data.url = url
         create_new_url_entry(g.list, data)
      end)

      if #indexes > 0 then
         set_status("New URL added at index: " .. table.concat(indexes, ", "))
      end
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_activate(buffer, args)
   if not g.active then
      g.scan_mode = nil
      if args then
         g.scan_mode = args:match("([^%s]*)")
         if g.scan_mode ~= "current" and g.scan_mode ~= "merged" then
            g.scan_mode = nil
         end
      end
      if not g.scan_mode then
         g.scan_mode = g.config.scan_merged_buffers and "merged" or "current"
      end

      g.list, g.duplicates = collect_urls(buffer, g.scan_mode)
      if g.list and g.list ~= "" then

         g.hooks.switch = w.hook_signal(
            "buffer_switch",
            "buffer_deactivated_cb",
            buffer)

         g.hooks.close = w.hook_signal(
            "buffer_closing",
            "buffer_deactivated_cb",
            buffer)

         g.hooks.print = w.hook_print(
            "",
            "", "://", 1,
            "new_line_cb",
            buffer)

         g.hooks.win_switch = w.hook_signal(
            "window_switch",
            "buffer_deactivated_cb",
            buffer)

         g.active = true
         set_bar("main", true)
         cmd_action_navigate(buffer, "previous")
         set_keys(buffer, "normal", true)
         w.bar_item_update(g.script.name .. "_title")
      end
   else
      cmd_action_deactivate(buffer, "")
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_deactivate(buffer)
   if g.active then
      g.active, g.enable_help, g.last_index = false, false, 0
      set_bar("main", false)
      set_bar("help", false)
      deactivate_search(buffer)
      set_keys(buffer, "normal", false)
      set_status()
      g.duplicates = nil
      if g.list and g.list ~= "" then
         w.infolist_free(g.list)
         g.list = nil
      end
      for name, ptr in pairs(g.hooks) do
         w.unhook(ptr)
      end
      g.hooks = {}
   end
   return w.WEECHAT_RC_OK
end

function move_cursor_normal(list, dir)
   local func
   if dir == "next" or dir == "last" then
      func = w.infolist_next
   elseif dir == "previous" or dir == "first" then
      func = w.infolist_prev
   end
   if dir == "first" or dir == "last" then
      w.infolist_reset_item_cursor(list)
   end
   local status = func(list)
   if status == 0 then
      w.infolist_reset_item_cursor(list)
      status = func(list)
   end
   return status == 1
end

function move_cursor_highlight(list, dir)
   local func, alt
   if dir == "next-highlight" then
      func = w.infolist_next
      alt = w.infolist_prev
   elseif dir == "previous-highlight" then
      func = w.infolist_prev
      alt = w.infolist_next
   else
      return false
   end

   local steps = 0
   while func(list) == 1 do
      steps = steps + 1
      if w.infolist_integer(list, "highlighted") == 1 then
         return true
      end
   end
   for i = 0, steps do
      alt(list)
   end
   set_status("No URL with highlight found")
   return false
end

function search_check_current_entry(list, keyword)
   keyword = keyword:lower()
   local check_msg = function ()
      local msg = w.string_remove_color(w.infolist_string(list, "message"), "")
      return msg:lower():find(keyword, 1, true)
   end

   local check_nick = function ()
      local nick = w.infolist_string(list, "nick")
      return nick:lower():find(keyword, 1, true)
   end

   local check_url = function ()
      local url = w.infolist_string(list, "url")
      return url:lower():find(keyword, 1, true)
   end

   if g.search_scope == 1 then
      return check_url()
   elseif g.search_scope == 2 then
      return check_msg()
   elseif g.search_scope == 3 then
      return check_nick()
   elseif g.search_scope == 4 then
      local r = check_msg()
      if not r then
         r = check_nick()
      end
      return r
   end
end

function move_cursor_search(list, keyword, dir)
   local func, alt
   if dir == "next" then
      func = w.infolist_next
      alt = w.infolist_prev
   elseif dir == "previous" then
      func = w.infolist_prev
      alt = w.infolist_next
   else
      return false
   end
   local steps = 0
   while func(list) == 1 do
      steps = steps + 1
      if search_check_current_entry(list, keyword) then
         return true
      end
   end
   for i = 0, steps do
      alt(list)
   end
   local msg
   set_status(string.format(
      "Reached %s of list. No URL found.",
      dir == "previous" and "start" or "end"))
   return false
end

function cmd_action_navigate(buffer, args, keyword)
   if g.active and g.list and g.list ~= "" then
      if args == "next" or
         args == "previous" or
         args == "first" or
         args == "last" then
         if g.enable_search and (args == "next" or args == "previous") then
            if not keyword then
               keyword = w.buffer_get_string(buffer, "input")
            end
            if not keyword or keyword == "" then
               move_cursor_normal(g.list, args)
            else
               move_cursor_search(g.list, keyword, args)
            end
         else
            move_cursor_normal(g.list, args)
         end
      elseif args == "next-highlight" or
         args == "previous-highlight" then
         move_cursor_highlight(g.list, args)
      end
      update_list_items()
   end
   return w.WEECHAT_RC_OK
end

function set_all_input_bars(flag)
   if flag then
      if g._forced_bar and #g._forced_bar > 0 then
         for _, name in ipairs(g._forced_bar) do
            w.bar_set(w.bar_search(name), "hidden", "off")
         end
         g._forced_bar = nil
      end
   else
      local list = w.infolist_get("bar", "", "")
      if list and list ~= "" then
         g._forced_bar = {}
         while w.infolist_next(list) == 1 do
            local name = w.infolist_string(list, "name")
            local hidden = w.infolist_integer(list, "hidden")
            local items = w.infolist_string(list, "items") or ""
            items = "," .. items:gsub("[^_%w]+", ",") .. ","
            if name ~= g.bar.main.name and
               name ~= g.bar.search.name and
               name ~= g.bar.help.name and
               items:match(",input_text,") and
               hidden == 0 then
               w.bar_set(w.bar_search(name), "hidden", "on")
               table.insert(g._forced_bar, name)
            end
         end
         w.infolist_free(list)
      end
   end
end

function search_input_cb(buffer, _, evbuffer)
   if buffer == evbuffer then
      local keyword = w.buffer_get_string(buffer, "input")
      if not search_check_current_entry(g.list, keyword) then
         cmd_action_navigate(buffer, "previous", keyword)
      end
   end
   return w.WEECHAT_RC_OK
end

function enter_cb()
   return w.WEECHAT_RC_OK_EAT
end

function activate_search(buffer)
   g.enable_search = true
   set_all_input_bars(false)
   set_bar("search", true)
   g._original_input_text = w.buffer_get_string(buffer, "input")
   g._original_input_pos = w.buffer_get_integer(buffer, "input_pos")
   w.buffer_set(buffer, "input", "")
   g.hooks.enter = w.hook_command_run("/input return", "enter_cb", "")
   g.hooks.search =
      w.hook_signal("input_text_changed", "search_input_cb", buffer)
   set_keys(buffer, "search", true)
end

function deactivate_search(buffer)
   g.enable_search = false
   set_bar("search", false)
   set_all_input_bars(true)
   set_keys(buffer, "search", false)
   if g.hooks.enter then
      w.unhook(g.hooks.enter)
      g.hooks.enter = nil
   end
   if g.hooks.search then
      w.unhook(g.hooks.search)
      g.hooks.search = nil
   end
   if g._original_input_text then
      w.buffer_set(buffer, "input", g._original_input_text)
      w.buffer_set(buffer, "input_pos", g._original_input_pos or 0)
      g._original_input_text = nil
      g._original_input_pos = nil
   end
end

function cmd_action_search(buffer, args)
   if g.active and g.list and g.list ~= "" then
      if not g.enable_search then
         activate_search(buffer)
      else
         deactivate_search(buffer)
      end
      w.bar_item_update(g.script.name .. "_help")
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_search_scope(buffer, args)
   if not g.search_scope then
      return
   end
   if args == "next" then
      if g.search_scope == #g.scope_list then
         g.search_scope = 1
      else
         g.search_scope = g.search_scope + 1
      end
   elseif args == "previous" then
      if g.search_scope == 1 then
         g.search_scope = #g.scope_list
      else
         g.search_scope = g.search_scope - 1
      end
   else
      local found_scope
      for i, name in ipairs(g.scope_list) do
         if name == args then
            g.search_scope = i
            found_scope = true
            break
         end
      end
      if not found_scope then
         print(
            "Unknown scope: ${color:bold}${scope}${color:-bold}. See " ..
            "${color:bold}/help ${script_name}${color:-bold} for usage info.",
            { scope = args, prefix_type = "error"})
         return w.WEECHAT_RC_OK
      end
   end
   w.bar_item_update(g.script.name .. "_search")
   if buffer then
      search_input_cb(buffer, _, buffer)
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_bind(buffer, args)
   local s1, s2 = args:match("^([^%s]+)%s+(.+)")
   local label, key, command
   if s1 and s2 then
      if s1 == "-label" then
         if s2:sub(1, 1) == '"' then
            for p, r in split(s2:sub(2), '"') do
               label = p
               s2 = r:sub(1, #r - 1)
               break
            end
            key, command = s2:match("^%s*([^%s]+)%s+(.+)")
         else
            label, key, command = s2:match("^([^%s]+)%s+([^%s]+)%s+(.+)")
         end
      else
         key = s1
         command = s2
      end
      if key and command then
         w.config_set_plugin("cmd." .. key, command)
         if label and label ~= "" then
            w.config_set_plugin("label." .. key, label)
         end
      end
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_unbind(buffer, args)
   for key in args:gmatch("([^%s]+)") do
      w.config_unset_plugin("cmd." .. key)
      w.config_unset_plugin("label." .. key)
   end
   return w.WEECHAT_RC_OK
end

function get_current_hashtable(raw_timestamp)
   local tm = w.infolist_integer(g.list, "time")
   if not raw_timestamp then
      tm = os.date(g.config.time_format, tm)
   end

   return {
      url = w.infolist_string(g.list, "url"),
      nick = w.infolist_string(g.list, "nick"),
      time = tm,
      message = w.infolist_string(g.list, "message"),
      index = w.infolist_integer(g.list, "index"),
      buffer_number = w.infolist_integer(g.list, "buffer_number"),
      buffer_name = w.infolist_string(g.list, "buffer_name"),
      buffer_short_name = w.infolist_string(g.list, "buffer_short_name"),
      buffer_full_name = w.infolist_string(g.list, "buffer_full_name")
   }
end

function eval_current_entry(text)
   return w.string_eval_expression(text, {}, get_current_hashtable(), {})
end

function cmd_action_hsignal(buffer, args)
   if g.list and g.list ~= "" then
      w.hook_hsignal_send(
         g.script.name .. "_current",
         get_current_hashtable(true))
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_run(buffer, args)
   if g.list and g.list ~= "" then
      local entry = g.custom_commands[args]
      if entry then
         set_status("Running cmd " .. (entry.label or args))
         for cmd in split(entry.command, ";") do
            cmd = eval_current_entry(cmd)
            w.command(buffer, cmd)
         end
      end
   end
   return w.WEECHAT_RC_OK
end

function cmd_action_list_commands(buffer, args)
   print("KEYS    COMMANDS")
   print("===============================================")
   local fmt, opt = "Alt-%s    %s", { no_eval = true }
   for k = 0, 9 do
      local c = tostring(k)
      if g.custom_commands[c] then
         print(string.format(fmt, c, g.custom_commands[c].command), opt)
      end
   end
   for k = string.byte('a'), string.byte('z') do
      local c = string.char(k)
      if g.custom_commands[c] then
         print(string.format(fmt, c, g.custom_commands[c].command), opt)
      end
   end
end

function buffer_deactivated_cb(buffer)
   cmd_action_deactivate(buffer)
   return w.WEECHAT_RC_OK
end

function cmd_action_help(buffer, args)
   g.enable_help = not g.enable_help
   set_bar("help", g.enable_help)
   w.bar_item_update(g.script.name .. "_help")
   return w.WEECHAT_RC_OK
end

function command_cb(_, buffer, param)
   local action, args = param:match("^([^%s]+)%s*(.*)$")
   local callbacks = {
      activate          = cmd_action_activate,
      deactivate        = cmd_action_deactivate,
      navigate          = cmd_action_navigate,
      bind              = cmd_action_bind,
      unbind            = cmd_action_unbind,
      run               = cmd_action_run,
      hsignal           = cmd_action_hsignal,
      help              = cmd_action_help,
      search            = cmd_action_search,
      scope             = cmd_action_search_scope,
      ["list-commands"] = cmd_action_list_commands
   }

   if not action then
      action = "activate"
   end

   if not callbacks[action] then
      print(
         "Unknown action: ${color:bold}${action}${color:-bold}. " ..
         "See ${color:bold}/help ${script_name}${color:-bold} for usage info.",
         { action = action, prefix_type = "error" })
      return w.WEECHAT_RC_OK
   else
      return callbacks[action](buffer, args)
   end
end

function remove_delimiter(x1, x2, url, msg)
   local end_char, remove_last_char = url:sub(-1), false
   if end_char:match("[%.,;:]") then
      remove_last_char = true
   elseif x1 > 1 and end_char:match("[%)%]%>%}`\"\']") then
      local pos = x1 - 1
      local pre_char = msg:sub(pos, pos)
      if (pre_char == "(" and end_char == ")") or
         (pre_char == "[" and end_char == "]") or
         (pre_char == "<" and end_char == ">") or
         (pre_char == "{" and end_char == "}") or
         (pre_char == "`" and end_char == "`") or
         (pre_char == "'" and end_char == "'") or
         (pre_char == "\"" and end_char == "\"") then
         remove_last_char = true
      end
   end
   if remove_last_char then
      x2 = x2 - 1
      url = url:sub(1, #url - 1)
   end
   return x1, x2, url
end

function process_urls_in_message(msg, callback)
   local pattern
   if g.config.use_simple_matching then
      pattern = "([%w%+%.%-]+://[%w:!/#_~@&=,;%+%?%[%]%.%%%(%)%-]+)"
   else
      pattern = "([%w%+%.%-]+://[^%s]+)"
   end

   msg = w.string_remove_color(msg, "")
   local x1, x2, count = 1, 0, 0
   while x1 and x2 do
      x1, x2, url = msg:find(pattern, x2 + 1)
      if x1 and x2 and url then
         if not g.config.use_simple_matching then
            x1, x2, url = remove_delimiter(x1, x2, url, msg)
         end
         count = count + 1
         local msg2
         if g.config.url_color then
            local left, right = "", ""
            if x1 > 1 then
               left = msg:sub(1, x1 - 1)
            end
            if x2 < #msg then
               right = msg:sub(x2 + 1)
            end
            msg2 =
               left ..
               w.color(g.config.url_color) ..
               url ..
               w.color("reset") ..
               right
         end
         callback(url, msg2)
      end
   end
   return count
end

function create_new_url_entry(list, data)
   local item = w.infolist_new_item(list)
   w.infolist_new_var_string(item, "message", data.message or "")
   w.infolist_new_var_string(item, "nick", data.nick or "")
   w.infolist_new_var_string(item, "prefix", data.prefix or "")
   w.infolist_new_var_integer(item, "time", data.time or 0)
   w.infolist_new_var_string(item, "url", data.url or "")
   w.infolist_new_var_integer(item, "index", data.index or 0)
   w.infolist_new_var_integer(item, "highlighted", data.highlighted or 0)
   w.infolist_new_var_string(item, "buffer_full_name", data.buffer_full_name)
   w.infolist_new_var_string(item, "buffer_name", data.buffer_name)
   w.infolist_new_var_string(item, "buffer_short_name", data.buffer_short_name)
   w.infolist_new_var_integer(item, "buffer_number", data.buffer_number or 0)
   return item
end

function convert_datetime_into_timestamp(time_string)
   local year, month, day, hour, minute, second =
      time_string:match("^(%d+)-(%d+)-(%d+) (%d+):(%d+):(%d+)$")

   return os.time({
      year  = tonumber(year or 0),
      month = tonumber(month or 0),
      day   = tonumber(day or 0),
      hour  = tonumber(hour or 0),
      min   = tonumber(minute or 0),
      sec   = tonumber(second or 0)
   })
end


function collect_urls(buffer, mode)
   local source_name = "own_lines"
   if mode == "merged" then
      source_name = "lines"
   end
   local h_buf = w.hdata_get("buffer")
   local source = w.hdata_pointer(h_buf, buffer, source_name)
   if not source or source == "" then
      return
   end

   local index, info, duplicates = 0, {}, {}
   local list = w.infolist_new()
   local line = w.hdata_pointer(w.hdata_get("lines"), source, "first_line")
   local h_line = w.hdata_get("line")
   local h_line_data = w.hdata_get("line_data")

   local add_cb = function (url, msg)
      if not duplicates[url] then
         duplicates[url] = {}
      end
      index = index + 1
      table.insert(duplicates[url], index)
      info.index = index
      info.url = url
      info.message = msg
      create_new_url_entry(list, info)
   end

   local get_info_from_current_line = function (data)
      local info, tags = {}

      info.prefix = w.hdata_string(h_line_data, data, "prefix")

      local tag_required = (g.config.tags and #g.config.tags > 0)
      local tag_count =
         w.hdata_get_var_array_size(h_line_data, data, "tags_array")

      if tag_required then
         if not tag_count or tag_count < 1 then
            return
         end
         tags = "," .. string.lower(table.concat(g.config.tags, ",")) .. ","
      end

      if tag_count > 0 then
         local found_match = false
         for i = 0, tag_count - 1 do
            local tag = w.hdata_string(h_line_data, data, i .. "|tags_array")
            if tag:sub(1, 5) == "nick_" then
               info.nick = tag:sub(6)
            elseif tag == "logger_backlog" then
               info.prefix = "backlog: " .. info.prefix
            end
            if tag_required and not found_match then
               local p = tags:find("," .. tag:lower() .. ",", 1, true)
               if p then
                  found_match = true
               end
            end
         end
         if tag_required and not found_match then
            return
         end
      end

      local buffer = w.hdata_pointer(h_line_data, data, "buffer")
      info.buffer_full_name = w.hdata_string(h_buf, buffer, "full_name")
      info.buffer_name = w.hdata_string(h_buf, buffer, "name")
      info.buffer_short_name = w.hdata_string(h_buf, buffer, "short_name")
      info.buffer_number = w.hdata_integer(h_buf, buffer, "number")

      info.prefix = w.string_remove_color(info.prefix, "")
      info.highlighted = w.hdata_char(h_line_data, data, "highlighted")
      info.message = w.hdata_string(h_line_data, data, "message")
      info.time = tonumber(w.hdata_time(h_line_data, data, "date") or 0)

      return info
   end

   while line and line ~= "" do
      local data = w.hdata_pointer(h_line, line, "data")
      if data and data ~= "" then
         local displayed = w.hdata_char(h_line_data, data, "displayed")
         if displayed == 1 then
            info = get_info_from_current_line(data)
            if info then
               process_urls_in_message(info.message, add_cb)
            end
         end
      end
      line = w.hdata_move(h_line, line, 1)
   end
   if index == 0 then
      w.infolist_free(list)
      list = nil
   else
      g.last_index = index
   end
   return list, duplicates
end

function default_item_handler(name, color_key)
   if not g.list or g.list == "" then
      return ""
   else
      local func
      if name == "index" or name == "buffer_number" then
         func = w.infolist_integer
      else
         func = w.infolist_string
      end
      local s = func(g.list, name)
      if not color_key then
         color_key = name .. "_color"
      end
      if g.config[color_key] then
         s = w.color(g.config[color_key]) .. s
      end
      return s
   end
end

function item_buffer_number_cb()
   return default_item_handler("buffer_number")
end

function item_buffer_name_cb()
   local key
   if g.config.buffer_name == "full" then
      key = "buffer_full_name"
   elseif g.config.buffer_name == "short" then
      key = "buffer_short_name"
   else
      key = "buffer_name"
   end
   return default_item_handler(key, "buffer_name_color")
end

function item_duplicate_cb()
   local result = ""
   if g.duplicates then
      local url = w.infolist_string(g.list, "url")
      local index = w.infolist_integer(g.list, "index")
      if g.duplicates[url] then
         local t = {}
         for _, v in ipairs(g.duplicates[url]) do
            if v ~= index then
               table.insert(t, v)
            end
         end
         result = table.concat(t, ",")
      end
   end
   return result
end

function item_message_cb()
   return default_item_handler("message")
end

function item_url_cb()
   return default_item_handler("url")
end

function item_time_cb()
   if not g.list or g.list == "" then
      return ""
   else
      local tm = w.infolist_integer(g.list, "time")
      return w.color(g.config.time_color) ..
             os.date(g.config.time_format, tm)
   end
end

function item_index_cb()
   return default_item_handler("index")
end

function item_nick_cb()
   if not g.list or g.list == "" then
      return ""
   else
      local color = g.config.nick_color
      local text = w.infolist_string(g.list, "nick")
      if w.infolist_integer(g.list, "highlighted") == 1 and
         g.config.highlight_color ~= "" then
         color = g.config.highlight_color
      elseif g.config.nick_color ~= "" then
         color = g.config.nick_color
      elseif text and text ~= "" then
         color = w.info_get("irc_nick_color_name", text)
      else
         color = "default"
      end
      if not text or text == "" then
         text = w.infolist_string(g.list, "prefix")
      end
      return w.color(color) .. text .. w.color("reset")
   end
end

function item_title_cb()
   return string.format(
      "%s%s: %s<F1>%s toggle help",
      w.color(g.config.title_color),
      g.script.name,
      w.color(g.config.key_color),
      w.color(g.config.title_color))
end

function item_help_cb()
   if not g.enable_help then
      return ""
   else
      local key_color = w.color(g.config.key_color)
      local help_color = w.color(g.config.help_color)
      local param = {
         kc = key_color,
         hc = help_color,
         search_keys = ""
      }

      if g.enable_search then
         param.search_keys = w.string_eval_expression([[

      ${kc}<tab>${hc} next scope
${kc}<shift-tab>${hc} prev scope
   ${kc}<ctrl-n>${hc} search nick
   ${kc}<ctrl-t>${hc} search message
   ${kc}<ctrl-u>${hc} search url
   ${kc}<ctrl-b>${hc} search nick+message
]],
         {}, param, {})
      end

      local help_text = w.string_eval_expression([[
   ${kc}<ctrl-c>${hc} close
   ${kc}<ctrl-f>${hc} search
       ${kc}<up>${hc} prev
     ${kc}<down>${hc} next${search_keys}
     ${kc}<home>${hc} first
      ${kc}<end>${hc} last
   ${kc}<ctrl-p>${hc} prev highlight
   ${kc}<ctrl-n>${hc} next highlight
   ${kc}<ctrl-s>${hc} send hsignal
]],
      {}, param, {})

      local fmt = "    %s<alt-%s>%s %s\n"
      for k = 0, 9 do
         local c = tostring(k)
         if g.custom_commands[c] then
            local cmd = g.custom_commands[c]
            local label = cmd.label or cmd.command
            help_text =
               help_text ..
               string.format(fmt, key_color, c, help_color, label)
         end
      end
      for k = string.byte('a'), string.byte('z') do
         local c = string.char(k)
         if g.custom_commands[c] then
            local cmd = g.custom_commands[c]
            local label = cmd.label or cmd.command
            help_text =
               help_text ..
               string.format(fmt, key_color, c, help_color, label)
         end
      end
      return help_text
   end
end

function item_search_cb()
   if not g.enable_search then
      return ""
   else
      local param = {
         pc = w.color(g.config.search_prompt_color),
         mc = w.color(g.config.search_scope_color),
         scope = g.scope_list[g.search_scope]
      }

      return w.string_eval_expression(
         "${pc}search (${mc}${scope}${pc}) >",
         {}, param, {})
   end
end

function set_status(message)
   g.current_status = message
   w.bar_item_update(g.script.name .. "_status")
end

function item_status_cb()
   if not g.current_status or g.current_status == "" then
      return ""
   else
      local s = " " .. g.current_status .. " "
      if g.config.status_color then
         s = w.color(g.config.status_color) .. s
      end
      if g.config.status_timeout and g.config.status_timeout > 0 then
         if g.hooks.timer then
            w.unhook(g.hooks.timer)
         end
         g.hooks.timer =
            w.hook_timer(g.config.status_timeout, 0, 1, "set_status", "")
      end
      return s
   end
end

function update_list_items()
   for _, name in ipairs(g.bar_items.list) do
      w.bar_item_update(g.script.name .. "_" .. name)
   end
end

function config_cb(_, opt_name, opt_value)
   local prefix = "plugins.var.lua." .. g.script.name .. "."
   local name = opt_name:sub(#prefix + 1)

   if g.defaults[name] then
      g.config[name] = get_or_set_option(name, g.defaults[name], opt_value)
   elseif name:sub(1, 4) == "cmd." then
      set_custom_command(name:sub(5), opt_value)
   elseif name:sub(1, 6) == "label." then
      set_custom_label(name:sub(7), opt_value)
   end
end

function setup_bar()
   for _, name in ipairs(g.bar_items.list) do
      w.bar_item_new(g.script.name .. "_" .. name, "item_" .. name .. "_cb", "")
   end

   for _, name in ipairs(g.bar_items.extra) do
      w.bar_item_new(g.script.name .. "_" .. name, "item_" .. name .. "_cb", "")
   end

   local settings = {
      main = {
         priority = 3000,
         filling_tb = "horizontal",
         max_size = 2,
         items = w.string_eval_expression(
            "[${s}_title],#${s}_index,(${s}_duplicate),[${s}_buffer_name]," ..
            "<${s}_nick>,${s}_message,${s}_status",
            {}, { s = g.script.name }, {})
      },
      search = {
         priority = 2999,
         filling_tb = "horizontal",
         max_size = 1,
         items = g.script.name .. "_search,input_text"
      },
      help = {
         priority = 2998,
         filling_tb = "columns_horizontal",
         max_size = 6,
         items = g.script.name .. "_help"
      }
   }

   for key, info in pairs(g.bar) do
      local bar = w.bar_search(info.name)
      if not bar or bar == "" then
         bar = w.bar_new(
            info.name,                 -- name
            "on",                      -- hidden?
            settings[key].priority,    -- priority
            "root",                    -- type
            "active",                  -- condition
            "top",                     -- position
            settings[key].filling_tb,  -- filling top/bottom
            "vertical",                -- filling left/right
            0,                         -- size
            settings[key].max_size,    -- max size
            "default",                 -- text fg
            "cyan",                    -- delim fg
            "default",                 -- bar bg
            "on",                      -- separator
            settings[key].items)       -- items
      end
      g.bar[key].ptr = bar
   end
end

setup()
