# Author: Benedikt 'linopolus' Mueller <linopolus@xssn.at>
# File: mpdspam.rb
#   weechat script to print the played song from mpd in the format '/me ♫ <artist> — <titel> (<album>)
# 
# ------------------------------------------------------------------------
# Copyright (c) 2009, Benedikt 'linopolus' Mueller <linopolus@xssn.at>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY Benedikt Mueller ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------
#

def weechat_init
  Weechat.register('mpdspam', 'linopolus', '1.0', 'BSD', 'print the played song from mpd in the format /me ♫ <artist> — <titel> (<album>)', '', '')
  Weechat.hook_command('mpdspam', 'display the currently played song of mpd', '', '', '', 'mpdspam', '')
  return Weechat::WEECHAT_RC_OK
end
def mpdspam(data, buffer, args)
  Weechat.command(Weechat.current_buffer, '/me ♫ ' + `mpc -p 23454 -f \'%artist% — %title% (%album%)\' | head -n 1`)

end
