--[[
-- pastebuf
--
-- A script for viewing the content of a pastebin inside Weechat buffer.
--
-- Usage:
--    /pastebuf <pastebin-url> [<optional-syntax-language>]
--
-- To use syntax highlighting, set plugins.var.lua.pastebuf.syntax_highlighter to
-- an external command that will highlight the text. If the command contains
-- $lang, it will be replaced by the name of syntax language specified with
-- /pastebuf command. For example, to use pygmentize as syntax highlighter:
--
--     /set plugins.var.lua.pastebuf.syntax_highlighter "pygmentize -l $lang"
--
-- See g.defaults for other options.
--
-- Author: tomoe-mami <rumia.youkai.of.dusk@gmail.com>
-- License: WTFPL
-- Requires: Weechat 0.4.3+
-- URL: https://github.com/tomoe-mami/weechat-scripts
--
--]]

local w = weechat
local g = {
   script = {
      name = "pastebuf",
      author = "tomoe-mami <rumia.youkai.of.dusk@gmail.com>",
      version = "0.1",
      license = "WTFPL",
      description = "View text from various pastebin sites inside a buffer."
   },
   config = {},
   defaults = {
      fetch_timeout = {
         value = 5 * 1000,
         type = "number",
         description = "Timeout for fetching URL"
      },
      highlighter_timeout = {
         value = 3 * 1000,
         type = "number",
         description = "Timeout for syntax highlighter"
      },
      color_line_number = {
         value = "default,darkgray",
         type = "string",
         description = "Color for line number"
      },
      color_line = {
         value = "default,default",
         type = "string",
         description = "Color for line content"
      },
      syntax_highlighter = {
         value = "",
         type = "string",
         description =
            "External command that will be used as syntax highlighter. " ..
            "$lang will be replaced by the name of syntax language"
      }
   },
   sites = {
      ["bpaste.net"] = {
         pattern = "http://bpaste.net/show/(%w+)",
         raw = "http://bpaste.net/raw/%s/"
      },
      ["dpaste.com"] = {
         pattern = "http://dpaste.com/(%w+)",
         raw = "http://dpaste.com/%s/plain/"
      },
      ["dpaste.de"] = {
         pattern = "https://dpaste.de/(%w+)",
         raw = "https://dpaste.de/%s/raw"
      },
      ["gist.github.com"] = {
         pattern = "https://gist.github.com/([^/]+/[^/]+)",
         raw = "https://gist.github.com/%s/raw" -- default raw url for first file
                                                -- in a gist
      },
      ["sprunge.us"] = {
         pattern = "http://sprunge.us/(%w+)",
         raw = "http://sprunge.us/%s"
      },
      ["paste.debian.net"] = {
         pattern = "http://paste.debian.net/(%d+)",
         raw = "http://paste.debian.net/plain/%s"
      },
      ["pastebin.ca"] = {
         pattern = "http://pastebin.ca/(%w+)",
         raw = "http://pastebin.ca/raw/%s"
      },
      ["pastebin.com"] = {
         pattern = "http://pastebin.com/(%w+)",
         raw = "http://pastebin.com/raw.php?i=%s"
      },
      ["pastie.org"] = {
         pattern = "http://pastie.org/pastes/(%w+)",
         raw = "http://pastie.org/pastes/%s/download"
      }
   },
   keys = {
      ["meta2-A"]    = "/window scroll_up",           -- arrow up
      ["meta2-B"]    = "/window scroll_down",         -- arrow down
      ["meta2-C"]    = "/window scroll_horiz 1",      -- arrow right
      ["meta2-D"]    = "/window scroll_horiz -1",     -- arrow left
      ["meta2-1~"]   = "/window scroll_top",          -- home
      ["meta2-4~"]   = "/window scroll_bottom"        -- end
   },
   buffers = {},
   sgr = {
      attributes = {
         [1] = "*", -- bold
         [3] = "/", -- italic
         [4] = "_", -- underline
         [7] = "!"  -- inverse
      },
      colors = {
         [ 0] = "black",
         [ 1] = "red",
         [ 2] = "green",
         [ 3] = "yellow",
         [ 4] = "blue",
         [ 5] = "magenta",
         [ 6] = "cyan",
         [ 7] = "gray",

         [ 8] = "darkgray",
         [ 9] = "lightred",
         [10] = "lightgreen",
         [11] = "brown",
         [12] = "lightblue",
         [13] = "lightmagenta",
         [14] = "lightcyan",
         [15] = "white"
      }
   }
}

function load_config()
   for opt_name, info in pairs(g.defaults) do
      if w.config_is_set_plugin(opt_name) == 0 then
         local val = info.value or ""
         w.config_set_plugin(opt_name, val)
         w.config_set_desc_plugin(opt_name, info.description or "")
         g.config[opt_name] = val
      else
         local val = w.config_get_plugin(opt_name)
         if info.type == "number" then
            val = tonumber(val)
         end
         g.config[opt_name] = val
      end
   end
end

function config_cb(_, opt_name, opt_value)
   local name = opt_name:match("^plugins%.var%.lua%." .. g.script.name .. "%.(.+)$")
   if name and g.defaults[name] then
      if g.defaults[name].type == "number" then
         opt_value = tonumber(opt_value)
      end
      g.config[name] = opt_value
   end
end

function split_args(s)
   local t = {}
   for v in s:gmatch("%S+") do
      table.insert(t, v)
   end
   return t
end

-- crude converter from csi sgr colors to weechat color
function convert_csi_sgr(text)
   local shift_param = function(s)
      if s then
         local p1, p2, chunk = s:find("^(%d+);?")
         if p1 then
            return chunk, s:sub(p2 + 1)
         end
      end
   end

   local convert_cb = function(code)
      local fg, bg, attr = "", "", ""

      local chunk, code = shift_param(code)
      while chunk do
         chunk = tonumber(chunk)
         if g.sgr.attributes[chunk] then
            attr = g.sgr.attributes[chunk]
         elseif chunk >= 30 and chunk <= 37 then
            fg = g.sgr.colors[ chunk - 30 ]
         elseif chunk == 38 then
            local c2, code = shift_param(code)
            fg, c2 = "default", tonumber(c2)
            if c2 == 5 then
               local c3, code = shift_param(code)
               if c3 then
                  fg = tonumber(c3)
               end
            end
         elseif chunk == 39 then
            fg = "default"
         elseif chunk >= 40 and chunk <= 47 then
            bg = g.sgr.colors[ chunk - 40 ]
         elseif chunk == 48 then
            local c2, code = shift_param(code)
            bg, c2 = "default", tonumber(c2)
            if c2 == 5 then
               local c3, code = shift_param(code)
               if c3 then
                  bg = tonumber(c3)
               end
            end
         elseif chunk == 49 then
            bg = "default"
         elseif chunk >= 90 and chunk <= 97 then
            fg = g.sgr.colors[ chunk - 82 ]
         elseif chunk >= 100 and chunk <= 107 then
            bg = g.sgr.colors[ chunk - 92 ]
         end
         chunk, code = shift_param(code)
      end
      local result = attr .. fg
      if bg and bg ~= "" then
         result = result .. "," .. bg
      end
      return w.color(result)
   end

   return text:gsub("\27%[([%d;]*)m", convert_cb)
end

function get_total_lines(s)
   local _, n = string.gsub(s .. "\n", ".-\n[^\n]*", "")
   return n
end

function message(s)
   w.print("", g.script.name .. "\t" .. s)
end

function get_site_config(u)
   local host = u:match("^https?://([^/]+)")
   if host then
      if host:match("^www%.") then
         host = host:sub(5)
      end
      if g.sites[host] then
         local site = g.sites[host]
         if site.handler then
            site.url = u
            return site
         else
            local id = u:match(site.pattern)
            if id then
               site.host = host
               site.id = id
               site.url = u
               return site
            end
         end
      end
   end
end

function buffer_close_cb(_, buffer)
   local short_name = w.buffer_get_string(buffer, "short_name")
   if g.buffers[short_name] then
      if g.buffers[short_name].hook and g.buffers[short_name].hook ~= "" then
         w.unhook(g.buffers[short_name].hook)
      end
      g.buffers[short_name] = nil
   end
end

function create_buffer(site)
   local short_name = string.format("%s:%s", site.host, site.id)
   if g.buffers[short_name] then
      local buffer = g.buffers[short_name]
      if not buffer.hook then
         w.buffer_clear(buffer.pointer)
         w.buffer_set(buffer, "localvar_del_paste", "")
         w.buffer_set(buffer, "localvar_del_highlight", "")
      end
      w.buffer_set(buffer.pointer, "display", "1")
      return buffer, short_name
   else
      local name = g.script.name .. ":" .. short_name
      local buffer = w.buffer_new(name, "", "", "buffer_close_cb", "")

      if buffer and buffer ~= "" then
         local title = string.format("%s: Fetching %s", g.script.name, site.url)

         w.buffer_set(buffer, "type", "free")
         w.buffer_set(buffer, "title", title)
         w.buffer_set(buffer, "short_name", short_name)
         w.buffer_set(buffer, "display", "1")

         for key, cmd in pairs(g.keys) do
            w.buffer_set(buffer, "key_bind_" .. key, cmd)
         end

         g.buffers[short_name] = { pointer = buffer }
         return g.buffers[short_name], short_name
      end
   end
end

function request_raw_paste(raw_url, short_name)
   g.buffers[short_name].hook = w.hook_process_hashtable(
      "url:" .. raw_url,
      { useragent = g.useragent },
      g.config.fetch_timeout,
      "receive_response_cb",
      short_name)
end

function receive_response_cb(short_name, request_url, status, response, err)
   if g.buffers[short_name] then
      local buffer = g.buffers[short_name]
      local is_complete = (status == 0)

      if is_complete or status == w.WEECHAT_HOOK_PROCESS_RUNNING then
         w.buffer_set(
            buffer.pointer,
            "localvar_set_paste",
            w.buffer_get_string(buffer.pointer, "localvar_paste") .. response)

         if is_complete then
            display_paste(buffer.pointer, true)
            w.buffer_set(
               buffer.pointer,
               "title",
               string.format(
                  "%s: %s",
                  g.script.name,
                  w.buffer_get_string(buffer.pointer, "localvar_url")))

            if g.buffers[short_name].hook then
               g.buffers[short_name].hook = nil
            end
         end
         return w.WEECHAT_RC_OK
      elseif status >= 1 or status == w.WEECHAT_HOOK_PROCESS_ERROR then
         if not err or err == "" then
            err = "Unable to fetch raw paste"
         end
         message(string.format("Error %d: %s", status, err))
         w.buffer_close(buffer.pointer)
         return w.WEECHAT_RC_ERROR
      end
   end
end

function print_line(buffer, y, num_width, content)
   local line = string.format(
         "%s %" .. num_width .. "d %s %s",
         w.color(g.config.color_line_number),
         y + 1,
         w.color(g.config.color_line),
         content)
   w.print_y(buffer, y, line)
end

function syntax_highlight_cb(buffer, cmd, status, output, err)
   local is_complete = (status == 0)
   if is_complete or status == w.WEECHAT_HOOK_PROCESS_RUNNING then
      w.buffer_set(
         buffer,
         "localvar_set_highlight",
         w.buffer_get_string(buffer, "localvar_highlight") .. output)

      if is_complete then
         local highlighted = w.buffer_get_string(buffer, "localvar_highlight")
         highlighted = convert_csi_sgr(highlighted)

         w.buffer_set(buffer, "localvar_set_paste", highlighted)
         w.buffer_set(buffer, "localvar_del_highlight", "")
         display_paste(buffer, false)
      end
      return w.WEECHAT_RC_OK
   elseif status >= 1 or status == w.WEECHAT_HOOK_PROCESS_ERROR then
      if not err or err == "" then
         err = "Unable to run syntax highlighter"
      end
      message(string.format("Error %d: %s", status, err))
      return w.WEECHAT_RC_ERROR
   end
end

function run_syntax_highlighter(buffer, lang)
   local cmd = w.buffer_string_replace_local_var(buffer, g.config.syntax_highlighter)
   local hook = w.hook_process_hashtable(
      cmd,
      { stdin = "1" },
      g.config.highlighter_timeout,
      "syntax_highlight_cb",
      buffer)

   if hook and hook ~= "" then
      w.hook_set(hook, "stdin", w.buffer_get_string(buffer, "localvar_paste"))
      w.hook_set(hook, "stdin_close", "")
   end
end

function display_paste(buffer, run_highlighter)
   local lang = w.buffer_get_string(buffer, "localvar_lang")
   if g.config.syntax_highlighter and
      g.config.syntax_highlighter ~= "" and
      run_highlighter and
      lang and lang ~= "" then
      run_syntax_highlighter(buffer, lang)
   end

   local text = w.buffer_get_string(buffer, "localvar_paste")
   local total_lines = w.buffer_get_string(buffer, "localvar_total_lines")
   if not total_lines or total_lines == "" then
      total_lines = tostring(get_total_lines(text))
      w.buffer_set(buffer, "localvar_set_total_lines", total_lines)
   end
   local num_width = #total_lines

   local y = 0
   for line in text:gmatch("(.-)\n") do
      print_line(buffer, y, num_width, line)
      y = y + 1
   end

   if not run_highlighter then
      w.buffer_set(buffer, "localvar_del_paste", "")
      w.buffer_set(buffer, "localvar_del_total_lines", "")
   end
end

function command_cb(_, current_buffer, param)
   param = param:gsub("^%s+", ""):gsub("%s+$", "")
   if param == "" then
      message(string.format("Usage: /%s <pastebin-url> [syntax]", g.script.name))
      return w.WEECHAT_RC_ERROR
   end

   param = split_args(param)
   local url, lang = param[1], param[2]
   local site = get_site_config(url)
   if not site then
      message("Unsupported site: " .. url)
      return w.WEECHAT_RC_ERROR
   end

   local buffer, short_name = create_buffer(site)
   if buffer then
      if not buffer.hook then
         local raw_url = string.format(site.raw, site.id)
         w.buffer_set(buffer.pointer, "localvar_set_url", url)
         w.buffer_set(buffer.pointer, "localvar_set_host", site.host)
         w.buffer_set(buffer.pointer, "localvar_set_id", site.id)

         if lang and lang ~= "" then
            w.buffer_set(buffer.pointer, "localvar_set_lang", lang)
         end

         request_raw_paste(raw_url, short_name)
      end
   end
   return w.WEECHAT_RC_OK
end

function setup()

   w.register(
      g.script.name,
      g.script.author,
      g.script.version,
      g.script.license,
      g.script.description,
      "", "")

   load_config()
   w.hook_config("plugins.var.lua." .. g.script.name .. ".*", "config_cb", "")
   g.useragent = string.format("%s v%s", g.script.name, g.script.version)

   local sites = {}
   for name,_ in pairs(g.sites) do
      table.insert(sites, name)
   end

   local supported_sites = ""
   if #sites > 0 then
      supported_sites = "\nSupported sites: " .. table.concat(sites, ", ")
   end

   w.hook_command(
      g.script.name,
      "Open a buffer and view the content of a paste" .. supported_sites,
      "paste-url [syntax-language]",

      "paste-url:       URL of the paste\n" ..
      "syntax-language: Optional language for syntax highlighting\n",
      "",
      "command_cb",
      "")
end

setup()
