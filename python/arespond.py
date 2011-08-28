# Copyright (c) 2011 by Stephan Huebner <shuebnerfun01@gmx.org>
#
# Intended use:
#
#     Send an autorespond-message once somebody sends a message in a query, but
#     only send it every n minutes
#
# TODO: make the text appear on highlights only?
#       make the script work for chats too (if own nick is mentioned)?
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# History:
#
#  - Sample History-Entry

SCR_NAME    = "arespond"
SCR_AUTHOR  = "Stephan Huebner <shuebnerfun01@gmx.org>"
SCR_VERSION = "0.1.0"
SCR_LICENSE = "GPL3"
SCR_DESC    = "An autoresponder (sending a notice on other users' messages)"
SCR_COMMAND = "arespond"

import_ok = True

try:
   import weechat as w
except:
   print "Script must be run under weechat. http://www.weechat.org"
   import_ok = False

import time

settings = {
   "responderText" : "Hello. %s isn't available at the moment. This message " +
                     "won't appear anymore for the next %d minutes.",
   "respondAfterMinutes" : "10",
   "muted" :      "off"
}

def errMsg(myMsg):
   alert("ERR: " + myMsg)
   return

def fn_privmsg(data, bufferp, tm, tags, display, is_hilight, prefix, msg):
   global settings
   servername = (w.buffer_get_string(bufferp, "name").split("."))[0]
   ownNick = w.info_get("irc_nick", servername)
   if prefix != ownNick and settings["muted"] != "off":
      # alert("messagetags: " + tags)
      if w.buffer_get_string(bufferp, "localvar_type") == "private":
         oldTime = w.buffer_get_string(bufferp, "localvar_btime")
         rmdTxt = settings["responderText"].replace("%s", ownNick)
         rmdTxt = rmdTxt.replace("%d", settings["respondAfterMinutes"])
         if oldTime != "":
            nowTime = time.time()
            tdelta = int(nowTime)-int(oldTime)
            if int(settings["respondAfterMinutes"])*60 <= tdelta:
               w.command("", "/notice " + prefix + " " + rmdTxt)
               w.buffer_set(bufferp, "localvar_set_btime", str(int(nowTime)))
         else:
            w.buffer_set(bufferp, "localvar_set_btime", str(int(time.time())))
            w.command("", "/notice " + prefix + " " + rmdTxt)
   return w.WEECHAT_RC_OK

def fn_command(data, buffer, args):
   # args being something like "on 15 SomeText"
   args = args.split()
   for listIndex in range(len(args)):
      if "on" in args[listIndex] or "off" in args[listIndex]:
         w.config_set_plugin("muted", args[listIndex])
      else:
         try:
            myMinutes = float(args[listIndex])
            w.config_set_plugin("respondAfterMinutes", args[listIndex])
         except ValueError:
            w.config_set_plugin("responderText", " ".join(args[listIndex:]))
            break
   return w.WEECHAT_RC_OK

def alert(myString):
	w.prnt("", myString)
	return

def fn_configchange(data, option, value):
   global settings
   fields = option.split(".")
   myOption = fields[-1]
   try:
      settings[myOption] = value
      alert("Option {0} is now {1}".format(myOption, settings[myOption]))
   except KeyError:
      errMsg("There is no option named %s" %myOption)
   return w.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
   if w.register(SCR_NAME, SCR_AUTHOR, SCR_VERSION, SCR_LICENSE,
                 SCR_DESC, "", ""):
      # synchronize weechat- and scriptsettings
      for option, default_value in settings.items():
         if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
         else:
            settings[option] = w.config_get_plugin(option)
      w.hook_print("", "", "", 1, "fn_privmsg", "") # catch prvmsg
      w.hook_config("plugins.var.python." + SCR_NAME + ".*",
                    "fn_configchange", "") # catch configchanges
      w.hook_command(SCR_COMMAND, SCR_DESC, "[muted] [n] [text]",
"""
Available options are:
- muted:               can be "on" or "off"
- respondAfterMinutes: integer (in minutes), after which responderText is
                       sent again
- responderText:       Text to be shown when necessary conditions are met.
                       Attention: The text always has to be the last parameter.
                       It does not need to be in quotes of any kind. It can also
                       contain %s and %d. These are placeholders for your own
                       nick and the minutes set in preferences.
""",
         "", "fn_command", ""
      )
