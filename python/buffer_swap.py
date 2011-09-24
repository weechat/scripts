# -*- coding: utf-8 -*-
#
# buffer_swap, version 0.3 for WeeChat version 0.3
# Latest development version: https://github.com/FiXato/weechat_scripts
#
#   Swaps given 2 buffers. Requested by kakazza
#
## Example:
#  Swaps buffers 3 and 5
#   /swap 3 5
#
#  Swaps current buffer with the #weechat buffer
#   /swap #weechat
#
## History:
### 2011-09-18: FiXato:
# 
# * version 0.1: initial release.
#     * Allow switching 2 given buffers
#
# * version 0.2: cleanup
#     * Made the command example more clear that it requires 2 buffer *numbers*
#     * After switching, now switches back to your original buffer.
#
# * version 0.3: current buffer support
#     * If you only specify 1 buffer, the current buffer will be used
#
## Acknowledgements:
# * Sebastien "Flashcode" Helleu, for developing the kick-ass chat/IRC
#    client WeeChat
#
## TODO: 
#   - Check if given buffers exist.
#
## Copyright (c) 2011 Filip H.F. "FiXato" Slagter,
#   <FiXato [at] Gmail [dot] com>
#   http://google.com/profiles/FiXato
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
SCRIPT_NAME     = "buffer_swap"
SCRIPT_AUTHOR   = "Filip H.F. 'FiXato' Slagter <fixato [at] gmail [dot] com>"
SCRIPT_VERSION  = "0.3"
SCRIPT_LICENSE  = "MIT"
SCRIPT_DESC     = "Swaps given 2 buffers"
SCRIPT_COMMAND  = "swap"
SCRIPT_CLOSE_CB = "close_cb"

import_ok = True

try:
  import weechat
except ImportError:
  print "This script must be run under WeeChat."
  import_ok = False

def close_cb(*kwargs):
  return weechat.WEECHAT_RC_OK

def command_main(data, buffer, args):
  args = args.split()
  curr_buffer = weechat.current_buffer()
  curr_buffer_number = weechat.buffer_get_integer(curr_buffer, "number")

  if len(args) != 1 and len(args) != 2:
    weechat.prnt("", "You need to specify 1 or 2 buffers")
    return weechat.WEECHAT_RC_ERROR

  if len(args) == 2:
    weechat.command("", "/buffer %s" % args[0])
    first_buffer = weechat.current_buffer()
    first_buffer_number = weechat.buffer_get_integer(first_buffer, "number")

    weechat.command("", "/buffer %s" % args[1])
    second_buffer = weechat.current_buffer()
    second_buffer_number = weechat.buffer_get_integer(second_buffer, "number")
  else:
    first_buffer = weechat.current_buffer()
    first_buffer_number = weechat.buffer_get_integer(first_buffer, "number")

    weechat.command("", "/buffer %s" % args[0])
    second_buffer = weechat.current_buffer()
    second_buffer_number = weechat.buffer_get_integer(second_buffer, "number")
  
  weechat.buffer_set(first_buffer, "number", str(second_buffer_number))
  weechat.buffer_set(second_buffer, "number", str(first_buffer_number))

  weechat.command("", "/buffer %s" % str(curr_buffer_number))
  
  return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                      SCRIPT_LICENSE, SCRIPT_DESC, SCRIPT_CLOSE_CB, ""):
    #        # Set default settings
    #        for option, default_value in cs_settings.iteritems():
    #            if not weechat.config_is_set_plugin(option):
    #                weechat.config_set_plugin(option, default_value)

    weechat.hook_command(SCRIPT_COMMAND, 
                          SCRIPT_DESC,
                          "[buffer] <buffer to swap with>",
                          "Swaps given buffers: \n"
                          "the /swap command accepts anything that /buffer would accept for switching buffers\n"
                          "/swap 3 10\n"
                          "would swap buffer 3 and 10 of place\n"
                          "/swap 3\n"
                          "would swap current buffer with buffer number 10\n"
                          "/swap 3 #weechat\n"
                          "would swap buffer 3 and the #weechat buffer of place\n"
                          "/swap #weechat\n"
                          "would swap current buffer with the #weechat buffer",

                          "",

                          "command_main", "")


