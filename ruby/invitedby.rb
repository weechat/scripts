# Copyright (c) 2013, JC Denton <jc+weechat@gamersconflict.com>
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

# Redirects "invitedby" responses to their appropriate buffer.

SCRIPT_NAME    = "invitedby"
SCRIPT_AUTHOR  = "JC Denton <jc+weechat@gamersconflict.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display invitedby messages in their own channel"

def weechat_init
    Weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")
    Weechat.hook_modifier('irc_in_345', 'invitedby_modifier_cb', '')
    return Weechat::WEECHAT_RC_OK
end

def invitedby_modifier_cb(data, modifier, modifier_data, string)
    buffer = Weechat.info_get("irc_buffer", "#{modifier_data},#{string.split(/ /)[2]}")
    Weechat.print(buffer, Weechat.prefix("network") + string.split(/:/)[-1])
    return ""
end
