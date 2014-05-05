#Copyright (c) 2014 Rylee Fowler <rylee@rylee.me>
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.


def weechat_init
  Weechat.register 'countdown', 'Rylee', '0.0.2', 'MIT',
    'Countdown script for personal use', '', ''

  Weechat.hook_command 'countdown', 'Make a new countdown with the given time in the current buffer',
    'countdown [time] [say_after]',
    'countdown [time] [say_after] - default for say_after is "Play!" - duration is time in seconds to count down from -- don\'t overdo it!',
    'countdown ',
    'countdown_cmd_callback',
    ''

  Weechat::WEECHAT_RC_OK
end

def countdown_cmd_callback data, buf, args
  return Weechat::WEECHAT_RC_ERROR if args.empty?
  return Weechat::WEECHAT_RC_ERROR if args.to_i.zero?
  duration, aftersay = args.split /\s+/, 2
  aftersay ||= 'Play!'
  Weechat.command buf, duration
  Weechat.hook_timer 1000, 0, duration.to_i, 'timer_cb', [aftersay, Weechat.buffer_get_string(buf, 'full_name')].pack('mm')
  Weechat::WEECHAT_RC_OK
end

def timer_cb data, remaining_calls
  aftersay, destination = data.unpack('mm')
  plugin, name = destination.split '.', 2
  buf = Weechat.buffer_search plugin, name
  return Weechat::WEECHAT_RC_ERROR if buf.empty?
  if remaining_calls.to_i.zero?
    out = aftersay
  else
    out = remaining_calls.to_s
  end
  Weechat.command buf, out
  Weechat::WEECHAT_RC_OK
end
