--###################################
--#									#
--#		Quick Respond				#
--#									#
--###################################

--env
--__debug=true
if __debug then	
  function print(x) weechat.print(debug_buffer,x)end
end

--hook #hook table contain
hook={}
r_name={}

function recordname(data, signal, signal_data)
  nick = weechat.info_get("irc_nick_from_host", signal_data)
  server = string.match(signal,"(.-),")
  channel = string.match(signal_data,"(#[^ ]+)")
  local mynick = weechat.info_get("irc_nick", server)
  --if __debug then	weechat.print(debug_buffer,mynick) end
  if not channel then	return weechat.WEECHAT_RC_OK end
  ma_nick=string.match(signal_data,"[^ ]+ [^ ]+ #[^ ]+ :([^:]+):")
  if __debug then	if ma_nick~=mynick then	print(ma_nick) return end
  end
  buffer = weechat.info_get("irc_buffer",server..","..channel)
  if buffer then	r_name[buffer]=nick end
  if __debug then	weechat.print(debug_buffer,"name table add "..buffer.." "..nick) end
end

function respond(data,buffer,args)
  lastname=r_name[buffer]
  if not lastname then	weechat.print(buffer,"You got no friend!haha") return weechat.WEECHAT_RC_OK end
  weechat.command(buffer,"/say "..lastname..":"..args)

  return weechat.WEECHAT_RC_OK
end

--debug#for debug
function buffer_input_cb(data,buffer,input_data)
  weechat.print(buffer,input_data)
  local tmp=load(input_data)
  if tmp then	tmp() end
  return weechat.WEECHAT_RC_OK
end
function buffer_close_cb(data,buffer)
  return weechat.WEECHAT_RC_OK
end

--Register
weechat.register("Respond","acoret@126.com","1.0","GPL","respond the last talk to you","","UTF-8")
hook.respond = weechat.hook_command("r","use /r will replace the /r to the lastname talk with you\nExample:Stranger say You:how are you\n/r im fine == you say Stranger: im fine","/r msg","msg is what you want to say","","respond","")
weechat.hook_signal("*,irc_in2_privmsg", "recordname","")
if __debug then
  debug_buffer=weechat.buffer_new("debug_respond", "buffer_input_cb","","buffer_close_cb","")
  weechat.buffer_set(debug_buffer,"title","debug for respond")
  weechat.buffer_set(debug_buffer, "localvar_set_no_log", "1")
end
