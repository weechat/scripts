# weechat ruby plugin to respond to /roll command and return a 
# randomly-generated number within the specified range
#
# see http://weechat.flashtux.org/doc/en/ch04s04s03.html for plugin API info
#
# this code is licensed under the GPL v2 yadda yadda
# contact me at: ledgekindred@gmail.com
# the latest version is always at:
# https://code.launchpad.net/~dglidden/+junk/weechat
#
# 2009.01.14
#   added default 1..100 if no number value is present
#   added support for "3d6 + 1" type number format
#
# example syntax:
#
# input:              result:
#
# /roll                display help text
# /roll hello          "[1d100] hello"
# /roll 10             "[1d10]"
# /roll 10 subway      "[1d10] subway"
# /roll 1d6            "[1d6]"
# /roll 2d20 to save   "[2d20] to save"
# /roll 10 + 2         "[1d10] + 2"
# /roll 1d6 + 2        "[1d6+2]"
# /roll 1d6+2 to hit   "[1d6+2] to hit"
#
# you can use a negative modifier to the dice roll (e.g. 1d6-4)
# if you do so, the lowest it will return is 1

@helptext = "Usage: /roll (dice to roll e.g. 50 (implied 1d50), 1d6, 3d8+4, no leading integer defaults to 1d100) [text]"

# weechat_init is called to set up the callback handlers
def weechat_init
  Weechat.register("roll", "1.0", "deinit", @helptext)
  Weechat.add_command_handler("roll", "roll_handler", @helptext)
  Weechat.add_message_handler("privmsg", "roll_msg")
  return Weechat::PLUGIN_RC_OK
end

def deinit
    return Weechat::PLUGIN_RC_OK
end

def debug(txt)
  Weechat.print(txt)
end

def output(txt)
  Weechat.command(txt)
end

def d(dicecount, sides)
  roll = 0
  for i in 1..dicecount
    roll += rand(sides) + 1
  end
  
  return roll
end

# we rolls our dice and returns our reults
def roll(args, nick)
  if(!args || args.empty?)
    return @helptext
  end
  
  if args =~ /^(\d+)/
    # starts with an integer we can use to roll
    @count = $1.to_i
    @text = $'.strip
    if @text =~ /^d(\d+)/
      # we also have a type of dice to roll
      @sides = $1.to_i
      @text = $'.strip
      if @text =~ /^\s*([+-])\s*(\d+)/
        # we also have a number to add to the result
        @add = $2.to_i
        @roll = "d(#{@count}, #{@sides})#{$1}#{@add}"
        @src = "#{@count}d#{@sides}#{$1}#{@add}"
        # the rest is our text
        @text = $'.strip
      else
        # we don't have a plus to the roll
        @roll = "d(#{@count}, #{@sides})"
        @src = "#{@count}d#{@sides}"        
      end
    else
      # We don't have a type, just a number, so we go 1..@count
      @roll = "d(1, #{@count})"
      @src = "1d#{@count}"
    end
  else
    # we didn't even start with a number, so we roll 1..100
    @roll = "d(1, 100)"
    @src = "1d100"
    @text = args
  end
  
  # debug("#{@roll}")
  @val = eval @roll
  if(@val < 1)
    @val = 1
  end
  return "#{nick} rolled #{@val} (#{@src}) #{@text}"
end

# respond to messages received from server
def roll_msg(server, args)
  if (args.empty?)
    output(@helptext)
    return Weechat::PLUGIN_RC_OK
  end

  null,info,msg = args.split(":",3)
  mask,type,chan = info.split(" ")
  nick,login = mask.split("!")

  cmd = msg.split(" ")
  
  # only respond to '/roll'
  if (cmd[0] == "/roll")
    result = roll(cmd[1..-1].join(" "), nick)
    Weechat.command(result, chan, server)
  end

  return Weechat::PLUGIN_RC_OK
end

# respond to commands entered locally
def roll_handler(server, args)
  if (args.empty?)
    output(@helptext)
    return Weechat::PLUGIN_RC_OK
  end

  cmd = " /roll #{args}"
  result = roll(args, Weechat.get_info("nick", server))
  output(result)
  output(cmd)
end
