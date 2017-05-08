# -*- coding: utf-8 -*-
=begin
cleanbuffer.rb, a script that tells znc to flush the current buffer
Copyright (C) 2016  Ewa Baumgarten <vivec@manavortex.de>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see [http://www.gnu.org/licenses/].
=end


SCRIPT_NAME    = 'cleanbuffer'
SCRIPT_AUTHOR  = 'manavortex'
SCRIPT_DESC    = 'Clears the current buffer, both in weechat and on the znc bouncer'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_ARGS    = "[znc|weechat|all]"
ARGUMENTS_DESC = <<-EOD
call with /clean or /clean znc to clean buffer on znc, call /clean buffer to clean both
EOD

def weechat_init

  Weechat.register SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''

  Weechat.hook_command 'clean', 'cleans the current buffer, on znc or weechat',
    ' znc | weechat | all ',
    [ 'znc: cleans the content of the current buffer with the znc bouncer',
      'weechat: cleans the content of the current buffer locally',
      'all: purges buffer',
    ].join("\n"),
    [
      'znc',
      'weechat',
      'all'
    ].join(' || '),
    'clean_callback', ''

  return Weechat::WEECHAT_RC_OK

end

def clean_callback data, buffer, cmd
  case cmd.downcase
  when 'znc'
    znc_clean_buffer(buffer, false)
  when 'weechat'
    clean_local_buffer(buffer)
  when 'all'
    znc_clean_buffer(buffer, true)
  else
    Weechat::WEECHAT_RC_ERROR
  end
end

def znc_clean_buffer(buffer, wipe)
 
  buffername = Weechat.buffer_get_string(buffer, "name")
  Weechat.command("", ("/msg *status ClearBuffer " << buffername))
  
  if wipe then 
    clean_local_buffer(buffer)
  end 

  #Weechat.command("", ('buffer ' << buffername << ' successfully cleaned!'))
  return Weechat::WEECHAT_RC_OK
end  

def clean_local_buffer(buffer)
  Weechat.command("", "/buffer clear")
end

