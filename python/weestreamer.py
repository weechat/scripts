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

# History:
# 2026-03-04, Ferus (feruscastor@proton.me)
#   0.5.0: Update syntax from py2 to py3
#          Make player configurable
#          Add toggle for displaying cli output in buffer

settings = {
    "player": ("streamlink -p /usr/bin/mpv", "Full command for player"),
    "output": ("true", "Display player output in buffer"),
}

import weechat

weechat.register("weestreamer", "Miblo", "0.5.0", "GPL3", "Streamlink companion for WeeChat", "", "")

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
        weechat.prnt(weechat.current_buffer(), "{}Too many arguments ({!s}). Please see /help weestreamer"
            .format(weechat.prefix("error"), len(input)))
        return weechat.WEECHAT_RC_ERROR

    # NOTE(matt): https://streamlink.github.io/plugin_matrix.html
    servers = {"afreeca":"https://play.afreeca.com/{channel}"
            ,"hitbox":"https://www.hitbox.tv/{channel}"
            ,"twitch":"https://www.twitch.tv/{channel}"
            ,"ustream":"https://www.ustream.tv/{channel}"
        }

    streamurl = ""
    for key in servers.keys():
        if key in server:
            streamurl = servers[key]
    if not streamurl:
        weechat.prnt(weechat.current_buffer(), "{}Unsupported server: {}"
                .format(weechat.prefix("error"), server))
        weechat.prnt(weechat.current_buffer(), "Currently supported servers:")
        for key in sorted(servers.keys()):
            weechat.prnt(weechat.current_buffer(), "    {}".format(key))
        return weechat.WEECHAT_RC_ERROR

    streamurl = streamurl.format(channel=channel)

    if server == "ustream":
        streamurl = streamurl.replace("-", "")

    comm = weechat.config_get_plugin("player")
    command = "{} {} {}".format(comm, streamurl, quality)

    weechat.prnt(weechat.current_buffer(), "{}LAUNCHING: {}"
                 .format(weechat.prefix("action"), command))
    weechat.hook_process(command, 0, "handle_output", "")
    return weechat.WEECHAT_RC_OK

def handle_output(data, command, rc, out, err):
    global process_output
    process_output = ""
    if out != "":
        process_output += out
    if int(rc) >= 0 and weechat.config_string_to_boolean(weechat.config_get_plugin("output")):
        weechat.prnt(weechat.current_buffer(), process_output)
    return weechat.WEECHAT_RC_OK


for option, value in settings.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, value[0])
    if int(weechat.info_get("version_number", "")) >= 0x00030500:
        weechat.config_set_desc_plugin(
            option, '{} (default: "{}")'.format(value[1], value[0])
        )

weechat.hook_command("weestreamer", "Streamlink companion for WeeChat",
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
        "   afreeca\n"
        "   hitbox\n"
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
        "afreeca"
        " || hitbox"
        " || twitch"
        " || ustream",
        "stream", "")
