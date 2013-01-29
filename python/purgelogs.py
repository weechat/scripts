# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2013 by nils_2 <weechatter@arcor.de>
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
# This script deletes weechatlog-files by age or size
# YOU ARE USING THIS SCRIPT AT YOUR OWN RISK!
#
# Usage:
#
# It is recommended to use this script with cron.py script:
# following command will check each 1th day of a month for logfiles older than 100 days and delete them 
# /cron add * * 1 * * * core.weechat command /purgelogs age 100 delete
#
# Options:
# do not delete #weechat, #weechat-fr and nils_2 (query) logfiles
# /set plugins.var.python.purgelogs.blacklist "#weechat,#weechat-fr,nils_2"
#
# History:
# 2013-01-25: nils_2, (freenode.#weechat)
#       0.4 : make script compatible with Python 3.x
# 2011-09-18: nils_2, (freenode.#weechat)
#     0.3.1 : code optimization
# 2011-09-17: nils_2, (freenode.#weechat)
#       0.3 : added: search for log-files smaller than age/size (new functions: age_ls and size_ls)
# 2011-03-11: nils_2, (freenode.#weechat)
#       0.2 : added blacklist option
# 2011-02-18: nils_2, (freenode.#weechat)
#       0.1 : initial release
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# TODO: waiting for "/logger disable all" and "/logger enable all"

try:
    import weechat as w
    import os, os.path, stat, time
    from datetime import date, timedelta
    
except Exception:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    quit()

SCRIPT_NAME    = "purgelogs"
SCRIPT_AUTHOR  = "nils_2 <weechatter@arcor.de>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "delete weechatlog-files by age or size (YOU ARE USING THIS SCRIPT AT YOUR OWN RISK!)"

purgelogs_commands = {
    "delete" : "argument for security reasons",
    "size"   : "greater than <Kib> for log-files to purge",
    "size_ls": "less than <Kib> for log-files to purge",
    "age"    : "older than <days> for log-files to purge (maximum value: 9999)",
    "age_ls" : "younger than <days> for log-files to purge",
}
purgelogs_options = {
    "blacklist": ""            # comma separated list of buffers (short name)
}
blacklist = []
# ================================[ weechat functions ]===============================
def purgelogs_cb(data, buffer, args):
  global basedir,purgelogs_commands,check_only, i
  basedir = get_path()
  if basedir == "":
    return w.WEECHAT_RC_OK
  argv = args.split(None, 2)
  """ argument "check" is set? """
  if len(argv) == 0:                    # no arguments given
    w.command("","/help purgelogs")     # print help page
    return w.WEECHAT_RC_OK

  if len(argv) == 1:
    if argv[0] not in purgelogs_commands:
      w.prnt("", "%s%s: unknown keyword \"%s\""
                         % (w.prefix("error"), SCRIPT_NAME, argv[0]))
      return w.WEECHAT_RC_OK
  if len(argv) < 2:
    w.prnt("", "%s%s: no value given"
                         % (w.prefix("error"), SCRIPT_NAME))
    return w.WEECHAT_RC_OK
  if is_number(argv[1]) is False:
    w.prnt("", "%s%s: wrong value \"%s\""
                         % (w.prefix("error"), SCRIPT_NAME, argv[1]))
    return w.WEECHAT_RC_OK

  if len(argv) == 3:
    if argv[2] == "delete":
      check_only = False      # delete
      w.command("","/mute /plugin unload logger")
  else:
    w.prnt("", "weechat-logs:")
    check_only = True         # show only

  if argv[0] in ["", "age_ls"]:
    i = 0
    getdirs(basedir,int(argv[1]),"ls_age")
  if argv[0] in ["", "size_ls"]:
    i = 0
    getdirs(basedir,int(argv[1]),"ls_size")
  if argv[0] in ["", "age"]:
    i = 0
    getdirs(basedir,int(argv[1]),"by_age")
  if argv[0] in ["", "size"]:
    i = 0
    getdirs(basedir,int(argv[1]),"by_size")
  if check_only is False:
    w.command("","/mute /plugin load logger")
  return w.WEECHAT_RC_OK

def get_path():
    """ get logger path """
    return w.config_string(w.config_get("logger.file.path")).replace("%h", w.info_get("weechat_dir", ""))

def is_number(s): 
    """ check if value is a number """
    try: 
        float(s) 
        return True 
    except ValueError: 
        return False 

# ================================[ os functions ]===============================
def getdirs(basedir, value, search):
    global i
    for root, dirs, files in os.walk(basedir):
        found = 1
        for file in files:
          if "by_age" in search:
            if value > 9999:
              return
            found_file = datecheck("by_age",root, file, value)
          elif "by_size" in search:
            found_file = sizecheck("by_size",root, file, value)
          elif "ls_age" in search:
            if value < 0:
              return
            found_file = datecheck("ls_age",root, file, value)
          elif "ls_size" in search:
            found_file = sizecheck("ls_size",root, file, value)
    if i == 0:
      w.prnt("", "no log-files matched.")

def datecheck(mode,root, file, age):
    basedate = date.today() - timedelta(days=age)
    fname = os.path.join(root, file)
    used = os.stat(fname).st_mtime                                # st_mtime=modified, st_atime=accessed
    year, day, month = time.localtime(used)[:3]
    lastused = date(year, day, month)
    if mode == "by_age":
      if lastused < basedate:                                     # get files older than age days
        file_action(root,file,"by_age")                           # return age
      return                                                      # Not old enough
    elif mode == "ls_age":
      if lastused > basedate:                                     # get files younger than age days
        file_action(root,file,"by_age")                           # return age
      return

def sizecheck(mode,root, file, size):
    filesize = 0
    filesize = int(os.path.getsize(os.path.join(root, file)))     # filesize in bytes
    size = size * 1024                                            # user option (KiB) to bytes
    if mode == "by_size":
      if filesize >= size:                                        # get files greater than size
        file_action(root,file,filesize)                           # return file size
      return                                                      # not large enough
    elif mode == "ls_size":
      if filesize <= size:                                        # get files smaller than size
        file_action(root,file,filesize)                           # return file size
      return                                                      # not large enough

def file_action(root, file, size):
  global check_only, mode_mute,i
  fname=os.path.join(root, file)
  if check_only is True:
    if size == "by_age":                                          # by age?
      i = i + 1
      bufname = file.split('.',1)                                 # get buffer name from file
      if bufname[0] in blacklist:
              w.prnt("", "  %s[%s%03d%s]%s %s %s[%sblacklisted%s]"
              % (w.color("chat_delimiters"), w.color("chat"),
              i,
              w.color("chat_delimiters"), w.color("chat"),
              fname,
              w.color("chat_delimiters"),
              w.color("chat_channel"),
              w.color("chat_delimiters"),
              ))
      else:
        w.prnt("", "  %s[%s%03d%s]%s %s"
        % (w.color("chat_delimiters"), w.color("chat"),
        i,
        w.color("chat_delimiters"), w.color("chat"),
        fname))
    else:
      i = i + 1
      bufname = file.split('.',1)                                 # get buffer name from file
      if bufname[0] in blacklist:
        w.prnt("", "  %s[%s%03d%s]%s %s\n        size: %s KiB %s[%sblacklisted%s]"
        % (w.color("chat_delimiters"), w.color("chat"),
        i,
        w.color("chat_delimiters"), w.color("chat"),
        fname,size/1024,
        w.color("chat_delimiters"),
        w.color("chat_channel"),
        w.color("chat_delimiters"),
        ))
      else:
        w.prnt("", "  %s[%s%03d%s]%s %s\n        size: %s KiB"
        % (w.color("chat_delimiters"), w.color("chat"),
        i,
        w.color("chat_delimiters"), w.color("chat"),
        fname,size/1024))
  elif check_only is False:                                       # delete logfiles!
      i = i + 1
      bufname = file.split('.',1)                                 # get buffer name from file
      if bufname[0] in blacklist:
        return

      os.remove(fname)
#      w.prnt("","delete: %s" % (fname))

def update_blacklist(*args):
    global blacklist
    if w.config_get_plugin('blacklist'):
        blacklist = w.config_get_plugin('blacklist').split(',')
    return w.WEECHAT_RC_OK

# ================================[ main ]===============================
if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                  SCRIPT_DESC, "", ""):
#        str_commands = ""
#        for cmd in (purgelogs_commands.keys()):
#          str_commands += "   " + cmd + ": " + purgelogs_commands[cmd] + "\n";
        w.hook_command("purgelogs",
                             "delete weechatlog-files by date or size",
                             "[age|age_ls] <days> || [size|size_ls] <in KiB> || [delete]",
                             "       size : greater than <Kib> for log-files to purge\n"
                             "    size_ls : less than <Kib> for log-files to purge\n"
                             "        age : older than <days> for log-files to purge (maximum value: 9999)\n"
                             "     age_ls : younger than <days> for log-files to purge\n"
                             "     delete : argument for security reasons\n"
                             "\n"
#                             str_commands + "\n"
                             "Examples:\n"
                             "  show log-files older than 100 days\n"
                             "    /" + SCRIPT_NAME + " age 100\n"
                             "  purge log-files older than 100 days\n"
                             "    /" + SCRIPT_NAME + " age 100 delete\n"
                             "  show log-files younger than 10 days\n"
                             "    /" + SCRIPT_NAME + " age_ls 10\n"
                             "  purge log-files younger than 10 days\n"
                             "    /" + SCRIPT_NAME + " age_ls 10 delete\n"
                             "  show log-files greater than 100 KiB\n"
                             "    /" + SCRIPT_NAME + " size 100\n"
                             "  purge log-files greater than 100 KiB\n"
                             "    /" + SCRIPT_NAME + " size 100 delete\n",
                             "age|age_ls|size|size_ls %-",
                             "purgelogs_cb", "")
    w.hook_config('plugins.var.python.%s.blacklist' %SCRIPT_NAME, 'update_blacklist', '')

    for option, default_value in purgelogs_options.items():
#    for option, default_value in purgelogs_options.iteritems():
      if w.config_get_plugin(option) == "":
        w.config_set_plugin(option, default_value)
      else:
        blacklist = w.config_get_plugin('blacklist').split(',')
