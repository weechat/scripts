#
# Copyright (9) 2024 Jesse McDowell <jessemcd1@gmail.com>
#
# Add IRCCloud avatar image link to WHOIS output
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <https://www.gnu.org/licenses/>.
#
# 2024-08-25: Jesse McDowell
#     version 1.0: Initial release


try:
    import weechat
    from weechat import WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print('This script must be run under WeeChat.')
    import_ok = False

import re

def whois311_cb(data, signal, signal_data):
    buffer = weechat.info_get("irc_buffer", signal.split(",")[0])

    userid_text = signal_data.split(" ")[5 if signal_data[0] == "@" else 4]

    userid_match = userid_expression.match(userid_text)
    if userid_match is not None:
        weechat.prnt(buffer, "Avatar image: https://static.irccloud-cdn.com/avatar-redirect/%s" % userid_match.groups()[0])

    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    weechat.register("irccloud_avatar_link", "Jesse McDowell", "1.0", "GPL3", "Add IRCCloud avatar image link to WHOIS details", "", "")
    userid_expression = re.compile("^[us]id([0-9]+)$")

    weechat.hook_signal("*,irc_in2_311", "whois311_cb", "")
