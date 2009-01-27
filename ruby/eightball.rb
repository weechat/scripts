# implement a magic 8-Ball as a weechat plugin
# this code is licensed under the GPL v2 yadda yadda
# contact me at: ledgekindred@gmail.com
# latest version is always at:
# https://code.launchpad.net/~dglidden/+junk/weechat

@helptext = "Usage: /8ball question"
@responses = ['As I see it, yes', 'Ask again later','Better not tell you now','Cannot predict now','Concentrate and ask again',
  "Don't count on it",'It is certain','It is decidedly so','Most likely','My reply is no','My sources say no','Outlook good',
  'Outlook not so good','Reply hazy, try again','Signs point to yes','Very doubtful','Without a doubt','Yes',
  'Yes - definitely','You may rely on it']

def weechat_init
    Weechat.register("8ball", "1.0", "deinit", @helptext)
    Weechat.add_command_handler("8ball", "eightball_handler", @helptext)
    Weechat.add_message_handler("privmsg", "eightball_msg")
    return Weechat::PLUGIN_RC_OK
end

def deinit
    return Weechat::PLUGIN_RC_OK
end

def output(txt)
  # Weechat.print(txt)
  Weechat.command(txt)
end

def eightball(nick)
  result = @responses[rand(@responses.length)]
  response = "Magic Eight Ball tells #{nick}: #{result}"
  return response
end

def eightball_msg(server, args)
  if (args.empty?)
    output(@helptext)
    return Weechat::PLUGIN_RC_OK
  end

  null,info,msg = args.split(":",3)
  mask,type,chan = info.split(" ")
  nick,login = mask.split("!")

  cmd = msg.split(" ")
  if (cmd[0] == "/8ball")
    result = eightball(nick)
    Weechat.command(result, chan, server)
  end

  return Weechat::PLUGIN_RC_OK
end

def eightball_handler(server, args)
  if (args.empty?)
    output(@helptext)
    return Weechat::PLUGIN_RC_OK
  end
  
  result = eightball(Weechat.get_info("nick", server))
  output(" /8ball #{args}")
  output(result)
end
