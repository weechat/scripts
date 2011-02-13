# -*- coding: utf-8 -*-
#
# Copyright (c) 2009, 2011 Łukasz P. Michalik <lmi@ift.uni.wroc.pl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA.
#

#
# This plugin requires Xmms2 ruby bindings to be installed.  'format'
# configuration variable specifies how metadata is displayed.
# Default_format is a good example, but don't abuse the syntax as you
# might get garbage.  It works with any key found in medialib for a
# current ID (see `xmms2 info` for a list); non-existing keys are
# ignored.
#

require 'xmmsclient'

Default_format = "[np] ${title} - ${artist}"

$xmms = nil

def weechat_init
    Weechat.register('xmms2', 'Łukasz P. Michalik <lmi@ift.uni.wroc.pl>', '0.2', 'GPL2', 'Xmms2 interaction plugin', '', '')
    Weechat.hook_command('xmms2', 'Trigger a /me currently playing info', '', '', '', 'xmms2', '')
    if (Weechat.config_get_plugin("format").empty?)
        Weechat.config_set_plugin("format", Default_format)
    end
    return Weechat::WEECHAT_RC_OK
end

def xmms2(data, buffer, args)
    if not $xmms
        $xmms = Xmms::Client.new('weechat')

        begin
            $xmms.connect(ENV['XMMS_PATH'])
        rescue Xmms::Client::ClientError
            Weechat.print("", "Failed to connect to XMMS2 daemon.")
            return Weechat::WEECHAT_RC_ERROR
        end
    end

    begin
        id = $xmms.playback_current_id.wait.value

        if (id == 0)
            Weechat.print(buffer, "Nothing is played!")
            return Weechat::WEECHAT_RC_OK
        end
    rescue Xmms::Rescue::ValueError
        Weechat.print(buffer, "Error retrieving current ID!")
        return Weechat::WEECHAT_RC_ERROR
    end

    begin
        info = $xmms.medialib_get_info(id).wait.value.to_propdict
        reg = /\$\{(\w+)\}/
        format = Weechat.config_get_plugin("format")
        out = ""
        while m = reg.match(format)
            out << m.pre_match
            format = m.post_match
            key = m[1].intern
            if info.has_key? key
                out << info[key]
            end
        end
    rescue Xmms::Result::ValueError
        puts 'There was an error retrieving mediainfo for the current ID.'
    end

    Weechat.command(buffer, "/me #{out}")
    return Weechat::WEECHAT_RC_OK
end
