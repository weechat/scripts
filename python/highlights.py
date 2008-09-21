""" 
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


    Author: Jason Whaley 
    Website: http://www.jasonwhaley.com
    Email:  "".join(["jasonwhaley", "@", "gmail", ".", "com"])
"""

import weechat
import time 

_function = "cmd_dispatcher"
_description = "Highlight Aggregator" 
_arguments = "all | recent | previous N | clear " 
_arguments_description = "Lines in any channels that were triggered by a " + \
     "nick highlight are internally stored.\n\n" + \
     "  all:       displays all currently stored messages \n" + \
     "  recent:    displays all messages collected since the last display \n"+\
     "  previous:  displays the last N messages, where N is an integer \n" +\
     "  clear:     empties the message storage \n\n" + \
     "If no arguments are provided, then recent is called."


_last_index = 0
_messages = []

def set_last_index():
  '''
  Sets the _last_index global to the current tail index of the messages.
  Establishes the point in which recent messages are displayed.
  '''
  global _last_index, messages 
  _last_index = len(_messages)

def unload():
  '''
  Called when the plugin is unloaded by weechat.
  '''
  global _last_index, _messages 
  weechat.prnt("Unloading highlights")
  return weechat.PLUGIN_RC_OK
  
def clear():
  '''
  Clears all messages stored.
  '''
  global _last_index, _messages 

  _messages = []
  _last_index = 0

  return weechat.PLUGIN_RC_OK 

def print_all():
  '''
  Print all messages that have been collected since
  the plugin was loaded or since clear was called.
  '''
  global _last_index, _messages 

  for message in _messages:
    weechat.prnt(message)
  set_last_index()

  return weechat.PLUGIN_RC_OK 

def print_since_last():
  '''
  Prints to the server buffer all messages collected
  since the last time any messages were printed out. 
  '''
  global _last_index, _messages 

  for message in _messages[_last_index:]:
    weechat.prnt(message)
  set_last_index()

  return weechat.PLUGIN_RC_OK 

def print_previous(args):
  '''
  Prints to the server buffer the latest N number of 
  highlighted messages collected.
  '''
  global _last_index, _messages 
  
  try:
    number = int(args)
  except ValueError:
    weechat.prnt("Error: Argument to previous must be a single integer")
    return weechat.PLUGIN_RC_OK
  
  if number >= len(_messages):
    print_all() 
  else:
    for message in _messages[-number:]:
      weechat.prnt(message)
  set_last_index()
  
  return weechat.PLUGIN_RC_OK 
  
def add_message(server, args):
  '''
  Captures a message that resulted from a nick highlight.
  If the message occured in a channel and not a private
  message window, it is added to the cached list of 
  highlighted messages.
  '''
  global _last_index, _messages 

  null, context, message = args.split(":",2)
  sender, msgtype, channel = context.strip().split(" ")
  nick = sender.split("!")[0]

  if channel.startswith("#"):
    message = format_message(server, channel, nick, message)
    _messages.append(message)

  return weechat.PLUGIN_RC_OK

def format_message(server, channel, nick, message):
  '''
  Formats messages as (server: #channel) nick | message"
  '''
  return nick + " | " + message + "   (" +  server + ": " + channel + " | " + time.strftime("%x %X",time.localtime()) + ")" 

def cmd_dispatcher(server, args):
  '''
  Captures a message that resulted from a nick highlight.
  If the message occured in a channel and not a private
  message window, it is added to the cached list of 
  highlighted messages.
  '''
  global _arguments 

  cmd = args.strip().split(" ")[0]
  cmd_args = args.replace(cmd,"",1)

  if cmd == "all":
    return print_all()
  if cmd == "recent" or cmd == "":
    return print_since_last()
  if cmd == "previous":
    return print_previous(cmd_args)
  if cmd == "clear":
    return clear()
 
  weechat.prnt("Error:  Invalid arguments. Use /help to see valid arguments") 
  
  return weechat.PLUGIN_RC_KO


weechat.register("highlights", "0.1.1", "unload", "WeeChat python script")
weechat.add_message_handler("weechat_highlight","add_message")
weechat.add_command_handler(
  "highlights",
  _function,
  _description,
  _arguments,
  _arguments_description)
weechat.add_command_handler(
  "hls",
  _function,
  _description,
  _arguments,
  _arguments_description)
