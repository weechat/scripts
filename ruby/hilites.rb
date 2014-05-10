#
#		HILITES
#		ruby script to display Weechat hilights in dzen.
#		also beeps
#

#
#		Author: Christian Brassat, aka. crshd
#		Email: christian@crshd.cc
#

#
# Copyright (c) 2011 Christian Brassat
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
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

#
# USAGE:
# First you need to create a FIFO file for the script to write to with
# mkfifo $HOME/.weechat/pipe
#
# Then you can start dzen with something like this:
# tail -f /home/crshd/.weechat/pipe | \
# dzen2 -ta l -tw 145 -h 17 -l 6 -y 1280 -bg "#151515" -fn "Pragmata:size=8"
#


SCRIPT_NAME = 'hilites'
SCRIPT_AUTHOR = 'Christian Brassat <christian@crshd.cc>'
SCRIPT_DESC = 'Send highlights in channels to a named pipe'
SCRIPT_VERSION = '0.2'
SCRIPT_LICENSE = 'MIT'

DEFAULTS = {
	'pipe_path'				=> "#{ENV['HOME']}/.weechat/pipe",
	'beep_on_hilight'	=> "false",
	'beep_on_private' => "true",
	'beep_file'				=> "#{ENV['HOME']}/.weechat/beep.ogg",
	'color1'					=> "435d65",
	'color2'					=> "6e98a4",
	'color3'					=> "2554a4",
	'color4'					=> "909090",
	'color5'					=> "606060",
	'color6'					=> "d92918"
}

def weechat_init
  Weechat.register SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
  DEFAULTS.each_pair { |option, def_value|
    cur_value = Weechat.config_get_plugin(option)
    if cur_value.nil? || cur_value.empty?
      Weechat.config_set_plugin(option, def_value)
    end
  }
	Weechat.hook_print("", "notify_message", "", 1, "hilite", "")
  Weechat.hook_print("", "notify_private", "", 1, "private", "")

	return Weechat::WEECHAT_RC_OK
end

def beep
	IO.popen("mplayer #{Weechat.config_get_plugin("beep_file")}")
end

def hilite( data, buffer, date, tags, visible, highlight, prefix, message )

	if ! highlight.to_i.zero?

		data = {}
		%w[ away type channel server ].each do |meta|
			data[ meta.to_sym ] = Weechat.buffer_get_string( buffer, "localvar_#{meta}" );
		end
		data[:away] = data[:away].empty? ? false : true

		if data[:type] == "channel"
			timestamp = Time.at(date.to_i).strftime("%H:%M")

			pipe = open( Weechat.config_get_plugin('pipe_path'), "w")
			pipe.printf("^tw()^fg(#%s) %s ^fg(#%s) %s \n %s ^fg(#%s)< %s > ^fg(#%s) %s ^fg(#%s) %s\n",
				Weechat.config_get_plugin("color1"),
				timestamp,
				Weechat.config_get_plugin("color2"),
				data[:channel],
				timestamp,
				Weechat.config_get_plugin("color3"),
				prefix,
				Weechat.config_get_plugin("color4"),
				data[:channel],
				Weechat.config_get_plugin("color5"),
				message )
			pipe.close

			beep if Weechat.config_get_plugin("beep_on_hilight") == "true"
		end
	end

	return Weechat::WEECHAT_RC_OK
end

def private( data, buffer, date, tags, visible, highlight, prefix, message )

	data = {}
	%w[ away type channel server ].each do |meta|
		data[ meta.to_sym ] = Weechat.buffer_get_string( buffer, "localvar_#{meta}" );
	end
	data[:away] = data[:away].empty? ? false : true

	unless data[:channel] == data[:server]
		timestamp = Time.at(date.to_i).strftime("%H:%M")

		pipe = open( Weechat.config_get_plugin('pipe_path'), "w")
		pipe.printf("^tw()^fg(#%s) %s ^fg(#%s) %s \n %s ^fg(#%s)< %s > ^fg(#%s) %s ^fg(#%s) %s\n",
			Weechat.config_get_plugin("color1"),
			timestamp,
			Weechat.config_get_plugin("color6"),
			data[:channel],
			timestamp,
			Weechat.config_get_plugin("color6"),
			data[:channel],
			Weechat.config_get_plugin("color4"),
			"Private Message",
			Weechat.config_get_plugin("color5"),
			message )
		pipe.close

		beep if Weechat.config_get_plugin("beep_on_private") == "true"
	end

	return Weechat::WEECHAT_RC_OK
end
#  vim: set ts=2 sw=2 tw=0 :
