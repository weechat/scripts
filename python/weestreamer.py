# Copyright (c) 2015 by Miblo <miblodelcarpio@gmail.com>
# All rights reserved
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

import weechat

weechat.register("weestreamer", "Miblo", "0.4", "GPL3", "Livestreamer companion for WeeChat", "", "")

def stream(data, buffer, args):
    bufserver = weechat.buffer_get_string(weechat.current_buffer(), "localvar_server")
    bufchannel = weechat.buffer_get_string(weechat.current_buffer(), "localvar_channel").lstrip("#")
    quality = "best"

    input = args.split()
    if not input:
        server = bufserver
        channel = bufchannel
    elif len(input) == 1:
        server = bufserver
        channel = input[0]
    elif len(input) == 2:
        server = input[0]
        channel = input[1]
    else:
        weechat.prnt(weechat.current_buffer(), "%sToo many arguments (%s). Please see /help weestreamer"
                % (weechat.prefix("error"),(len(input))))
        return weechat.WEECHAT_RC_ERROR

    # NOTE(matt): http://docs.livestreamer.io/plugin_matrix.html
    servers = {"twitch":"http://www.twitch.tv/%s" % (channel),
                "ustream":"http://www.ustream.tv/%s" % (channel.replace("-", ""))}

    streamurl = ""
    for key in servers.keys():
        if key in server:
            streamurl = servers[key]
    if not streamurl:
        weechat.prnt(weechat.current_buffer(), "%sUnsupported server: %s"
                % (weechat.prefix("error"), server))
        weechat.prnt(weechat.current_buffer(), "Currently supported servers:")
        for key in sorted(servers.keys()):
            weechat.prnt(weechat.current_buffer(), "    %s" % key)
        return weechat.WEECHAT_RC_ERROR

    command = "livestreamer %s %s" % (streamurl, quality)

    weechat.prnt(weechat.current_buffer(), "%sLAUNCHING: %s" % (weechat.prefix("action"), command))
    weechat.hook_process("%s" % (command), 0, "handle_output", "")
    return weechat.WEECHAT_RC_OK

def handle_output(data, command, rc, out, err):
    global process_output
    process_output = ""
    if out != "":
        process_output += out
    if int(rc) >= 0:
        weechat.prnt(weechat.current_buffer(), process_output)
    return weechat.WEECHAT_RC_OK

weechat.hook_command("weestreamer", "Livestreamer companion for WeeChat",
        "server channel",

        "Run /weestreamer without any arguments while in a channel on a supported irc\n"
        "server to launch the stream associated with that channel.\n"
        "\n"
        "You may optionally pass the server and / or channel (in that order) to launch\n"
        "the required stream from any channel, e.g.:\n"
        "    /weestreamer twitch handmade_hero\n"
        "    /weestreamer handmade_hero\n"
        "\n"
        "Currently supported servers:\n"
        "   twitch\n"
        "   ustream\n"
        "\n"
        "\n"
        "Troubleshooting: If you expect that your current server should be supported but\n"
        "weestreamer keeps erroring, please check the name of the server by running:\n"
        "\n"
        "    /buffer localvar\n"
        "\n"
        "If you have named the server such that it doesn't contain the string in\n"
        "\"Currently supported servers\" (above), weestreamer will not recognise it.",

        # NOTE(matt): list of valid parameters
        "twitch"
        " || ustream",
        "stream", "")
