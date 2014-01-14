# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Wil Clouser <clouserw@micropipes.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Passive aggressively auto-replies to private messages which say only the word
# 'ping' thus escalating the unwinnable war of people pinging without saying anything
# else.
#
# History:
#
#   2013-01-11, Wil Clouser <wclouser@mozilla.com>:
#       v0.1: Initial release

SCRIPT_NAME    = "autopong"
SCRIPT_AUTHOR  = "Wil Clouser <clouserw@micropipes.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC    = "Auto-replies to 'ping' queries"

import_ok = True

try:
   import weechat as w
except:
   print "Script must be run under weechat. http://www.weechat.org"
   import_ok = False

def privmsg(data, buffer, date, tags, displayed, is_hilight, prefix, msg):
  if w.buffer_get_string(buffer, "localvar_type") == "private":
     if msg == "ping":
         w.command(buffer, "pong")
  return w.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
   if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                 SCRIPT_DESC, "", ""):
      w.hook_print("", "", "", 1, "privmsg", "")
