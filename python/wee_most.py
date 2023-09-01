# Copyright (c) 2022 Damien Tardy-Panis <damien.dev@tardypad.me>
# Released under the GNU GPLv3 license.
# Forked from wee_matter, inspired by wee_slack

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import weechat

from collections import namedtuple
from functools import wraps
from ssl import SSLWantReadError
from websocket import (create_connection, WebSocketConnectionClosedException,
                       WebSocketTimeoutException, ABNF)

class Config:

    def __init__(self):
        self.file = None
        self.sections = {}
        self.options = {}

    def get_value(self, section, name):
        option = self.options.get("{}.{}".format(section, name), None)
        if not option:
            return ""

        # weechat_config_option_get_string function is not available for scripting
        # so we need to store it in the option structure
        if option["type"] == "boolean":
            return weechat.config_boolean(option["pointer"])
        elif option["type"] == "integer":
            return weechat.config_integer(option["pointer"])
        elif option["type"] == "string":
            return weechat.config_string(option["pointer"])
        elif option["type"] == "color":
            return weechat.config_color(option["pointer"])
        elif option["type"] == "list": # custom type
            value = weechat.config_string(option["pointer"])
            return list(filter(None, value.split(",")))

        return ""

    def get_server_value(self, server_id, name):
        value = self.get_value("server", "{}.{}".format(server_id, name))

        if name == "password":
            # used for evaluation of ${sec.data.name} for example
            return weechat.string_eval_expression(value, {}, {}, {})

        return value

    def is_server_valid(self, server_id):
        return "server.{}.url".format(server_id) in self.options

    def read(self):
        weechat.config_read(self.file)

    def add_server_options(self, server_id):
        self.options["server.{}.command_2fa".format(server_id)] = { "pointer": weechat.config_new_option(self.file,
            self.sections["server"], "{}.command_2fa".format(server_id), "string",
            "Shell command to retrieve the 2FA token of {} server".format(server_id),
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["server.{}.password".format(server_id)] = { "pointer": weechat.config_new_option(self.file,
            self.sections["server"], "{}.password".format(server_id), "string",
            "Password for authentication to {} server".format(server_id),
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["server.{}.url".format(server_id)] = { "pointer": weechat.config_new_option(self.file,
            self.sections["server"], "{}.url".format(server_id), "string",
            "URL of {} server".format(server_id),
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["server.{}.username".format(server_id)] = { "pointer": weechat.config_new_option(self.file,
            self.sections["server"], "{}.username".format(server_id), "string",
            "Username for authentication to {} server".format(server_id),
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "string" }

    def setup(self):
        self.file = weechat.config_new("wee_most", "", "")

        # look
        self.sections["look"] = weechat.config_new_section(self.file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "")
        self.options["look.bot_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "bot_suffix", "string",
            "The suffix for bot names",
            "", 0, 0, " [BOT]", " [BOT]", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.buflist_color_away_nick"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "buflist_color_away_nick", "boolean",
            "Use nicklist_away color for direct messages channels name in buflist if user is not online",
            "", 0, 0, "on", "on", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.channel_loading_indicator"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_loading_indicator", "string",
            "Indicator for channels being loaded with content",
            "", 0, 0, "…", "…", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_direct_away"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_direct_away", "string",
            "The prefix of buffer names for direct messages channels if user status is \"away\"",
            "", 0, 0, "-", "-", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_direct_dnd"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_direct_dnd", "string",
            "The prefix of buffer names for direct messages channels if user status is \"do not disturb\"",
            "", 0, 0, "@", "@", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_direct_offline"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_direct_offline", "string",
            "The prefix of buffer names for direct messages channels if user status is \"offline\"",
            "", 0, 0, " ", " ", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_direct_online"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_direct_online", "string",
            "The prefix of buffer names for direct messages channels if user status is \"online\"",
            "", 0, 0, "+", "+", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_group"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_group", "string",
            "The prefix of buffer names for group channels",
            "", 0, 0, "&", "&", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_private"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_private", "string",
            "The prefix of buffer names for private channels",
            "", 0, 0, "%", "%", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.channel_prefix_public"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "channel_prefix_public", "string",
            "The prefix of buffer names for public channels",
            "", 0, 0, "#", "#", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.deleted_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "deleted_suffix", "string",
            "The suffix for deleted posts",
            "", 0, 0, "(deleted)", "(deleted)", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.edited_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "edited_suffix", "string",
            "The suffix for edited posts",
            "", 0, 0, "(edited)", "(edited)", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.file_downloaded_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "file_downloaded_suffix", "string",
            "The suffix for downloaded files",
            "", 0, 0, "(downloaded)", "(downloaded)", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["look.nick_full_name"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "nick_full_name", "boolean",
            "Use full name instead of username as nick",
            "", 0, 0, "off", "off", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.reaction_group"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "reaction_group", "boolean",
            "Group reactions by emoji",
            "", 0, 0, "on", "on", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.reaction_nick_colorize"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "reaction_nick_colorize", "boolean",
            "Colorize the reaction nick with the user color",
            "", 0, 0, "on", "on", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.reaction_nick_show"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "reaction_nick_show", "boolean",
            "Display the nick of the user(s) alongside the reaction",
            "", 0, 0, "off", "off", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.thread_prefix_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "thread_prefix_suffix", "string",
            "String displayed after the thread prefix, if empty uses value from weechat.look.prefix_suffix",
            "", 0, 0, None, None, 1, "", "", "", "", "", ""), "type": "string" }
        self.options["look.thread_prefix_user_color"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "thread_prefix_user_color", "boolean",
            "Use root post user color for the thread prefix",
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "boolean" }
        self.options["look.truncated_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["look"], "truncated_suffix", "string",
            "The suffix for truncated edited posts",
            "", 0, 0, "[...]", "[...]", 0, "", "", "", "", "", ""), "type": "string" }

        # format
        self.sections["format"] = weechat.config_new_section(self.file, "format", 0, 0, "", "", "", "", "", "", "", "", "", "")
        self.options["format.file_name"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["format"], "file_name", "string",
            "Format for the display of a file name, {} is replaced by name",
            "", 0, 0, "[{}]", "[{}]", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["format.file_url"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["format"], "file_url", "string",
            "Format for the display of a file URL, {} is replaced by URL",
            "", 0, 0, "({})", "({})", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["format.thread_prefix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["format"], "thread_prefix", "string",
            "Format for the thread prefix of a post, {} is replaced by id",
            "", 0, 0, " {} ", " {} ", 0, "", "", "", "", "", ""), "type": "string" }
        self.options["format.thread_prefix_root"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["format"], "thread_prefix_root", "string",
            "Format for the thread prefix of a root post, {} is replaced by id",
            "", 0, 0, "[{}]", "[{}]", 0, "", "", "", "", "", ""), "type": "string" }

        # color
        self.sections["color"] = weechat.config_new_section(self.file, "color", 0, 0, "", "", "", "", "", "", "", "", "", "")
        self.options["color.attachment_field"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "attachment_field", "color",
            "Color for the message attachment fields",
            "", 0, 0, "default", "default", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.attachment_field"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "attachment_field", "color",
            "Color for the message attachment fields",
            "", 0, 0, "default", "default", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.attachment_title"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "attachment_title", "color",
            "Color for the message attachment title",
            "", 0, 0, "*default", "*default", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.bot_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "bot_suffix", "color",
            "Color for the bot suffix in message attachments",
            "", 0, 0, "darkgray", "darkgray", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.channel_muted"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "channel_muted", "color",
            "Color for the muted channels in the buflist",
            "", 0, 0, "darkgray", "darkgray", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.deleted"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "deleted", "color",
            "Color for deleted messages",
            "", 0, 0, "red", "red", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.edited_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "edited_suffix", "color",
            "Color for edited suffix on edited posts",
            "", 0, 0, "magenta", "magenta", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.file_downloaded_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "file_downloaded_suffix", "color",
            "Color for the suffix of downloaded files",
            "", 0, 0, "green", "green", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.file_name"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "file_name", "color",
            "Color for the name part of a file",
            "", 0, 0, "*default", "*default", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.file_url"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "file_url", "color",
            "Color for the URL part of a file",
            "", 0, 0, "default", "default", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.reaction"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "reaction", "color",
            "Color for the messages reactions",
            "", 0, 0, "darkgray", "darkgray", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.reaction_own"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "reaction_own", "color",
            "Color for the messages reactions you have added",
            "", 0, 0, "gray", "gray", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.reference_link"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "reference_link", "color",
            "Color for the reference-style links",
            "", 0, 0, "/gray", "/gray", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.thread_prefix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "thread_prefix", "color",
            "Color for the thread prefix of a post (see also wee_most.look.thread_prefix_user_color)",
            "", 0, 0, "blue", "blue", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.thread_prefix_root"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "thread_prefix_root", "color",
            "Color for the thread prefix of a root post (see also wee_most.look.thread_prefix_user_color)",
            "", 0, 0, "blue", "blue", 0, "", "", "", "", "", ""), "type": "color" }
        self.options["color.thread_prefix_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "thread_prefix_suffix", "color",
            "Color for the thread prefix suffix, if empty uses value from weechat.color.chat_prefix_suffix",
            "", 0, 0, None, None, 1, "", "", "", "", "", ""), "type": "color" }
        self.options["color.truncated_suffix"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["color"], "truncated_suffix", "color",
            "Color for truncated suffix on edited posts",
            "", 0, 0, "yellow", "yellow", 0, "", "", "", "", "", ""), "type": "color" }

        # file
        self.sections["file"] = weechat.config_new_section(self.file, "file", 0, 0, "", "", "", "", "", "", "", "", "", "")
        download_dir = os.environ.get("XDG_DOWNLOAD_DIR", "~/Downloads") + "/wee_most"
        self.options["file.download_location"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["file"], "download_location", "string",
            "Location for storing downloaded files",
            "", 0, 0, download_dir, download_dir, 0, "", "", "", "", "", ""), "type": "string" }

        # server (user can add options)
        self.sections["server"] = weechat.config_new_section(self.file, "server", 1, 0, "", "", "", "", "", "", "create_server_option_cb", "", "", "")
        self.options["server.autoconnect"] = { "pointer": weechat.config_new_option(self.file,
            self.sections["server"], "autoconnect", "string",
            "Comma separated list of server names to automatically connect to at start",
            "", 0, 0, "", "", 0, "", "", "", "", "", ""), "type": "list" }

def create_server_option_cb(data, config_file, section, option_name, value):
    if not re.match('^[a-z]+\.(command_2fa|password|url|username)$', option_name):
        return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR

    global config
    config.options["server.{}".format(option_name)] = { "pointer": weechat.config_new_option(config_file,
        section, option_name, "string", "",
        "", 0, 0, value, value, 0, "", "", "", "", "", ""), "type": "string" }

    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

def load_default_emojis():
    emojis_file_path = weechat.info_get("weechat_data_dir", "") + "/wee_most_emojis"
    try:
        with open(emojis_file_path, "r") as emojis_file:
            for emoji in emojis_file:
                default_emojis.append(emoji.rstrip())
    except:
        pass

def channel_completion_cb(data, completion_item, current_buffer, completion):
    for server in servers.values():
        weechat.hook_completion_list_add(completion, server.id, 0, weechat.WEECHAT_LIST_POS_SORT)
        for team in server.teams.values():
            for channel in team.channels.values():
                buffer_name = weechat.buffer_get_string(channel.buffer, "short_name")
                weechat.hook_completion_list_add(completion, buffer_name, 0, weechat.WEECHAT_LIST_POS_SORT)

    return weechat.WEECHAT_RC_OK

def private_completion_cb(data, completion_item, current_buffer, completion):
    for server in servers.values():
        for channel in server.channels.values():
            buffer_name = weechat.buffer_get_string(channel.buffer, "short_name")
            weechat.hook_completion_list_add(completion, buffer_name, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


def server_completion_cb(data, completion_item, current_buffer, completion):
    for server_id in servers:
        weechat.hook_completion_list_add(completion, server_id, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def slash_command_completion_cb(data, completion_item, current_buffer, completion):
    slash_commands = [ "away", "code", "collapse", "dnd", "echo", "expand", "groupmsg", "header",
                       "help", "invite", "invite_people", "join", "kick", "leave", "logout", "me",
                       "msg", "mute", "offline", "online", "purpose", "rename", "search", "settings",
                       "shortcuts", "shrug", "status" ]

    for slash_command in slash_commands:
        weechat.hook_completion_list_add(completion, slash_command, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def nick_completion_cb(data, completion_item, current_buffer, completion):
    server = get_server_from_buffer(current_buffer)
    if not server:
        return weechat.WEECHAT_RC_OK

    channel = server.get_channel_from_buffer(current_buffer)
    if not channel:
        return weechat.WEECHAT_RC_OK

    for user in channel.users.values():
        weechat.completion_list_add(completion, user.username, 1, weechat.WEECHAT_LIST_POS_SORT)
        weechat.completion_list_add(completion, "@{}".format(user.username), 1, weechat.WEECHAT_LIST_POS_SORT)

    return weechat.WEECHAT_RC_OK

def emoji_completion_cb(data, completion_item, current_buffer, completion):
    server = get_server_from_buffer(current_buffer)
    if not server:
        return weechat.WEECHAT_RC_OK

    for emoji in default_emojis:
        weechat.completion_list_add(completion, ":{}:".format(emoji), 0, weechat.WEECHAT_LIST_POS_SORT)

    for emoji in server.custom_emojis:
        weechat.completion_list_add(completion, ":{}:".format(emoji), 0, weechat.WEECHAT_LIST_POS_SORT)

    return weechat.WEECHAT_RC_OK

def mention_completion_cb(data, completion_item, current_buffer, completion):
    server = get_server_from_buffer(current_buffer)
    if not server:
        return weechat.WEECHAT_RC_OK

    for mention in mentions:
        weechat.completion_list_add(completion, mention, 0, weechat.WEECHAT_LIST_POS_SORT)

    return weechat.WEECHAT_RC_OK

Command = namedtuple("Command", ["name", "args", "description", "completion"])

commands = [
    Command(
        name = "server add",
        args = "<server-name>",
        description = "add a server",
        completion = "",
    ),
    Command(
        name = "connect",
        args = "<server-name>",
        description = "connect to a server",
        completion = "",
    ),
    Command(
        name = "disconnect",
        args = "<server-name>",
        description = "disconnect from a server",
        completion = "%(mattermost_server_commands)",
    ),
    Command(
        name = "slash",
        args = "<mattermost-command>",
        description = "send a plain slash command",
        completion = "%(mattermost_slash_commands)",
    ),
    Command(
        name = "reply",
        args = "<post-id> <message>",
        description = "reply to a post",
        completion = "",
    ),
    Command(
        name = "react",
        args = "<post-id> <emoji-name>",
        description = "react to a post",
        completion = "",
    ),
    Command(
        name = "unreact",
        args = "<post-id> <emoji-name>",
        description = "remove a reaction to a post",
        completion = "",
    ),
    Command(
        name = "delete",
        args = "<post-id>",
        description = "delete a post",
        completion = "",
    ),
]

def mattermost_channel_buffer_required(f):
    @wraps(f)
    def wrapper(args, buffer):
        buffer_name = weechat.buffer_get_string(buffer, "name")
        buffer_type = weechat.buffer_get_string(buffer, "localvar_type")
        if not buffer_name.startswith("wee_most.") or buffer_type == "server":
            command_name = f.__name__.replace("command_", "", 1)
            weechat.prnt("", '{}wee_most: command "{}" must be executed on a Mattermost channel buffer'.format(weechat.prefix("error"), command_name))
            return weechat.WEECHAT_RC_ERROR

        return f(args, buffer)

    return wrapper


def command_server_add(args, buffer):
    if 1 != len(args.split()):
        write_command_error("server add {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    config.add_server_options(args)

    weechat.prnt("", 'Server "{}" added. You should now configure it.'.format(args))
    weechat.prnt("", "/set wee_most.server.{}.*".format(args))

    return weechat.WEECHAT_RC_OK

def command_connect(args, buffer):
    if 1 != len(args.split()):
        write_command_error("connect {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR
    return connect_server(args)

def command_disconnect(args, buffer):
    if 1 != len(args.split()):
        write_command_error("disconnect {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR
    return disconnect_server(args)

def command_server(args, buffer):
    if 0 == len(args.split()):
        write_command_error("server {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    command, _, args = args.partition(" ")

    if command == "add":
        return command_server_add(args, buffer)

    write_command_error("server {} {}".format(command, args), "Invalid server subcommand")
    return weechat.WEECHAT_RC_ERROR

@mattermost_channel_buffer_required
def command_slash(args, buffer):
    if 0 == len(args.split()):
        write_command_error("slash {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    server = get_server_from_buffer(buffer)
    channel = server.get_channel_from_buffer(buffer)

    if hasattr(channel, 'team'):
        team_id = channel.team.id
    else:
        team_id = list(server.teams.keys())[0]

    run_post_command(team_id, channel.id, "/{}".format(args), server, "singularity_cb", buffer)

    return weechat.WEECHAT_RC_OK

def mattermost_command_cb(data, buffer, command):
    if 0 == len(command.split()):
        write_command_error("", "Missing subcommand")
        return weechat.WEECHAT_RC_ERROR

    prefix, _, args = command.partition(" ")
    command_function_name = "command_{}".format(prefix)

    if command_function_name not in globals():
        write_command_error(command, "Invalid subcommand")
        return weechat.WEECHAT_RC_ERROR

    return globals()[command_function_name](args, buffer)

@mattermost_channel_buffer_required
def command_reply(args, buffer):
    if 2 != len(args.split(" ", 1)):
        write_command_error("reply {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    post_id, _, message = args.partition(" ")

    server = get_server_from_buffer(buffer)
    channel = server.get_channel_from_buffer(buffer)
    post = channel.posts.get(post_id, None)

    if not post:
        server.print_error('Cannot find post id "{}"'.format(post_id))
        return weechat.WEECHAT_RC_ERROR

    new_post = {
        "channel_id": channel.id,
        "message": message,
        "root_id": post.root_id or post.id,
    }

    run_post_post(new_post, server, "post_post_cb", buffer)

    return weechat.WEECHAT_RC_OK

@mattermost_channel_buffer_required
def command_react(args, buffer):
    if 2 != len(args.split()):
        write_command_error("react {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    post_id, _, emoji_name = args.partition(" ")
    emoji_name = emoji_name.strip(":")

    server = get_server_from_buffer(buffer)

    run_post_reaction(emoji_name, post_id, server, "singularity_cb", buffer)

    return weechat.WEECHAT_RC_OK

@mattermost_channel_buffer_required
def command_unreact(args, buffer):
    if 2 != len(args.split()):
        write_command_error("unreact {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    post_id, _, emoji_name = args.partition(" ")
    emoji_name = emoji_name.strip(":")

    server = get_server_from_buffer(buffer)

    run_delete_reaction(emoji_name, post_id, server, "singularity_cb", buffer)

    return weechat.WEECHAT_RC_OK

@mattermost_channel_buffer_required
def command_delete(args, buffer):
    if 1 != len(args.split()):
        write_command_error("delete {}".format(args), "Error with subcommand arguments")
        return weechat.WEECHAT_RC_ERROR

    server = get_server_from_buffer(buffer)

    run_delete_post(args, server, "singularity_cb", buffer)

    return weechat.WEECHAT_RC_OK

def write_command_error(args, message):
    weechat.prnt("", weechat.prefix("error") + message + ' "/mattermost ' + args + '" (help on command: /help mattermost)')

class File:
    dir_path_tmp = tempfile.mkdtemp()

    def __init__(self, server, post, **kwargs):
        self.id = kwargs["id"]
        self.name = kwargs["name"]
        self.extension = kwargs["extension"]
        self.server = server
        self.post = post
        self.url = server.url + "/api/v4/files/{}".format(self.id)
        self.dir_path = os.path.expanduser(config.get_value("file", "download_location"))

    def render(self):
        name = colorize(config.get_value("format", "file_name").format(self.name), config.get_value("color", "file_name"))
        url = colorize(config.get_value("format", "file_url").format(self.url), config.get_value("color", "file_url"))

        text = "{}{}".format(name, url)

        if self._is_downloaded():
            text += " {}".format(colorize(config.get_value("look", "file_downloaded_suffix"), config.get_value("color", "file_downloaded_suffix")))

        return text

    def _path(self, temporary=False):
        if temporary:
            return "{}/{}.{}".format(self.dir_path_tmp, self.id, self.extension)

        return "{}/{}".format(self.dir_path, self.name)

    def _is_downloaded(self):
        return os.path.isfile(self._path())

    def download(self, temporary=False, open=False):
        file_path = self._path(temporary)

        if open and os.path.isfile(file_path):
            File.open(file_path)
            return

        if not temporary and not os.path.exists(self.dir_path):
            try:
                os.makedirs(self.dir_path)
            except:
                self.server.print_error("Failed to create directory for downloads: {}".format(self.dir_path))
                return

        cb_data = "{}|{}|{}|{}|{}".format(self.server.id, self.post.channel.id, self.post.id, file_path, int(open))
        run_get_file(self.id, file_path, self.server, "file_get_cb", cb_data)

    @staticmethod
    def open(path):
        weechat.hook_process('xdg-open "{}"'.format(path), 0, "", "")

def file_get_cb(data, command, rc, out, err):
    server_id, channel_id, post_id, file_path, open = data.split("|")
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while downloading file")
        return weechat.WEECHAT_RC_ERROR

    if open == "1":
        File.open(file_path)
    else:
        channel = server.get_channel(channel_id)
        post = channel.posts[post_id]
        channel.update_post(post)

    return weechat.WEECHAT_RC_OK

class Post:
    def __init__(self, server, **kwargs):
        self.id = kwargs["id"]
        self.root_id = kwargs["root_id"]
        self.channel = server.get_channel(kwargs["channel_id"])
        self.message = kwargs["message"]
        self.type = kwargs["type"]
        self.created_at = kwargs["create_at"]
        self.edited = kwargs["edit_at"] != 0
        self.thread_root = False

        self.user = server.users[kwargs["user_id"]]

        self.files = {}
        if "metadata" in kwargs and "files" in kwargs["metadata"]:
            for file_data in kwargs["metadata"]["files"]:
                file = File(server, self, **file_data)
                self.files[file.id] = file

        self.reactions = {}
        if "metadata" in kwargs and "reactions" in kwargs["metadata"]:
            for reaction_data in kwargs["metadata"]["reactions"]:
                reaction = Reaction(server, **reaction_data)
                self.reactions[reaction.id] = reaction

        self.attachments = []
        if "attachments" in kwargs["props"] and kwargs["props"]["attachments"] is not None:
            for attachment_data in kwargs["props"]["attachments"]:
                self.attachments.append(Attachment(**attachment_data))

        self.from_bot = kwargs["props"].get("from_bot", False) or kwargs["props"].get("from_webhook", False)
        self.username_override = kwargs["props"].get("override_username")

    @property
    def read(self):
        return self.created_at <= self.channel.last_viewed_at

    def render_nick(self):
        prefix_string = weechat.config_string(weechat.config_get("weechat.look.nick_prefix"))
        prefix_color = weechat.config_string(weechat.config_get("weechat.color.chat_nick_prefix"))
        prefix = colorize(prefix_string, prefix_color)

        suffix_string = weechat.config_string(weechat.config_get("weechat.look.nick_suffix"))
        suffix_color = weechat.config_string(weechat.config_get("weechat.color.chat_nick_suffix"))
        suffix = colorize(suffix_string, suffix_color)

        nick = self.username_override or self.user.nick
        nick = colorize(nick, self.user.color)

        if self.from_bot:
            nick += colorize(config.get_value("look", "bot_suffix"), config.get_value("color", "bot_suffix"))

        return "{}{}{}".format(prefix, nick, suffix)

    # we assume lines_count is big enough to contains the files and attachments lines
    # it is only used when editing a post and those items can't be modified
    # so there should at least be space for them from the initial write
    def render_message(self, lines_count=None):
        # remove tabs to prevent display issue on multiline messages
        # where 2 tabs at the beginning of a line results in no alignment
        tab_width = weechat.config_integer(weechat.config_get("weechat.look.tab_width"))
        main_text = self.message.replace("\t", " " * tab_width)

        main_text = main_text.strip('\n')
        main_text = format_markdown_links(main_text)

        attachments_text = "\n\n".join([ a.render() for a in self.attachments ])
        files_text = "\n".join([ f.render() for f in self.files.values() ])

        if lines_count:
            main_text_lines_count = lines_count
            main_text_lines_count -= len(attachments_text.split("\n")) if attachments_text else 0
            main_text_lines_count -= len(files_text.split("\n")) if files_text else 0
            main_text_lines_count -= 1 if attachments_text and main_text else 0 # extra empty line separator

            lines = main_text.split("\n") if main_text else []
            if len(lines) > main_text_lines_count:
                # new message is longer, truncate from max line
                lines = lines[0: main_text_lines_count]
                lines[-1] += " {}".format(colorize(config.get_value("look", "truncated_suffix"), config.get_value("color", "truncated_suffix")))
            elif len(lines) < main_text_lines_count:
                # new message is shorter, just add blank lines to keep files tags on the same line
                lines += [""] * (main_text_lines_count - len(lines))
            main_text = "\n".join(lines)

        if self.edited and main_text:
            main_text += " {}".format(colorize(config.get_value("look", "edited_suffix"), config.get_value("color", "edited_suffix")))

        full_text = main_text
        full_text += "\n\n" if attachments_text and full_text else ""
        full_text += attachments_text
        full_text += "\n" if files_text and full_text else ""
        full_text += files_text

        if self.edited and not main_text:
            full_text += " {}".format(colorize(config.get_value("look", "edited_suffix"), config.get_value("color", "edited_suffix")))

        return format_style(full_text)

    def add_reaction(self, reaction):
        self.reactions[reaction.id] = reaction

    def remove_reaction(self, reaction):
        del self.reactions[reaction.id]

    def render_reactions(self):
        if not self.reactions:
            return ""

        my_username = self.channel.server.me.username

        reactions_string = []

        if config.get_value("look", "reaction_group"):
            reactions_groups = {}
            for r in self.reactions.values():
                if r.emoji_name in reactions_groups:
                    reactions_groups[r.emoji_name].append(r.user)
                else:
                    reactions_groups[r.emoji_name] = [ r.user ]

            for name, users in reactions_groups.items():
                colorized_name = colorize(name, config.get_value("color", "reaction"))
                for u in users:
                    if u.username == my_username:
                        colorized_name = colorize(name, config.get_value("color", "reaction_own"))
                        break

                if config.get_value("look", "reaction_nick_show"):
                    users_string = []
                    for u in users:
                        user_string = u.nick
                        if config.get_value("look", "reaction_nick_colorize"):
                            user_string = colorize(user_string, u.color)
                        users_string.append(user_string)

                    reaction_string = ":{}:({})".format(colorized_name, ",".join(users_string))
                else:
                    reaction_string = ":{}:{}".format(colorized_name, len(users))

                reactions_string.append(reaction_string)

        else:
            for r in self.reactions.values():
                if r.user.username == my_username:
                    colorized_name = colorize(r.emoji_name, config.get_value("color", "reaction_own"))
                else:
                    colorized_name = colorize(r.emoji_name, config.get_value("color", "reaction"))

                if config.get_value("look", "reaction_nick_show"):
                    user_string = u.nick
                    if config.get_value("look", "reaction_nick_colorize"):
                        user_string = colorize(user_string, r.user.color)

                    reaction_string = ":{}:({})".format(colorized_name, user_string)
                else:
                    reaction_string = ":{}:".format(colorized_name)

                reactions_string.append(reaction_string)

        return " [{}]".format(" ".join(reactions_string))

    def open(self):
        if hasattr(self.channel, 'team'):
            team_name = self.channel.team.name
        else:
            team_name = list(self.channel.server.teams.values())[0].name

        url = self.channel.server.url + "/{}/pl/{}".format(team_name, self.id)
        weechat.hook_process('xdg-open "{}"'.format(url), 0, "", "")

class Reaction:
    def __init__(self, server, **kwargs):
        self.user = server.users[kwargs["user_id"]]
        self.emoji_name = kwargs["emoji_name"]
        self.id = "{}_{}".format(self.user, self.emoji_name)

class Attachment:
    def __init__(self, **kwargs):
        self.pretext = kwargs.get("pretext")
        self.author = kwargs.get("author_name")
        self.title = kwargs.get("title")
        self.title_link = kwargs.get("title_link")
        self.text = kwargs.get("text")
        self.footer = kwargs.get("footer")
        self.fields = kwargs.get("fields")

    def render(self):
        att = []

        if self.pretext:
            att.append(self.pretext)

        if self.author:
            att.append(self.author)

        title = ""
        # write link as markdown link for later generic formatting
        if self.title and self.title_link:
            title = "{} []({})".format(self.title, self.title_link)
        elif self.title:
            title = self.title
        elif self.title_link:
            title = "[]({})".format(self.title_link)

        if title:
            att.append(colorize(format_style(title), config.get_value("color", "attachment_title")))

        if self.text:
            att.append(self.text)

        if self.fields:
            for field in self.fields:
                field_text = ""
                if field["title"] and field["value"]:
                    field_text = "{}: {}".format(field["title"], field["value"])
                elif field["title"]:
                    field_text = "{}: ".format(field["title"])
                elif field["value"]:
                    field_text = field["value"]

                if field_text:
                    att.append(colorize(format_style(field_text), config.get_value("color", "attachment_field")))

        if self.footer:
            att.append(self.footer)

        return format_markdown_links("\n".join(att))

def post_post_cb(buffer, command, rc, out, err):
    server = get_server_from_buffer(buffer)

    if rc != 0:
        server.print_error("Cannot send post")
        return weechat.WEECHAT_RC_ERROR

    return weechat.WEECHAT_RC_OK

def colorize(sentence, color):
    return "{}{}{}".format(weechat.color(color), sentence, weechat.color("reset"))

# needs to be called on uncolored text
def format_style(text):
    text = re.sub(
            r"(^| |\")(?:\*\*\*|___)([^*\n`]+)(?:\*\*\*|___)(?=[^\w]|$)",
            r"\1{}{}\2{}{}".format(
                weechat.color("bold"), weechat.color("italic"), weechat.color("-bold"), weechat.color("-italic")
                ),
            text,
            flags=re.MULTILINE,
            )
    text = re.sub(
            r"(^| |\")(?:\*\*|__)([^*\n`]+)(?:\*\*|__)(?=[^\w]|$)",
            r"\1{}\2{}".format(
                weechat.color("bold"), weechat.color("-bold")
                ),
            text,
            flags=re.MULTILINE,
            )
    text = re.sub(
            r"(^| |\")(?:\*|_)([^*\n`]+)(?:\*|_)(?=[^\w]|$)",
            r"\1{}\2{}".format(
                weechat.color("italic"), weechat.color("-italic")
                ),
            text,
            flags=re.MULTILINE,
            )
    return text

def format_markdown_links(text):
    links = []

    def link_repl(match):
        nonlocal links
        text, url = match.groups()
        if text == url:
            return text
        counter = len(links) + 1
        links.append(colorize("[{}]: {}".format(counter, url), config.get_value("color", "reference_link")))
        if text:
            return "[{}] [{}]".format(text, counter)
        return "[{}]".format(counter)

    p = re.compile('\[([^]]*)\]\(([^\)*]*)\)')
    new_text = p.sub(link_repl, text)

    if links:
        return "{}\n{}".format(new_text, "\n".join(links))

    return new_text

def get_line_data_tags(line_data):
    tags = []

    tags_count = weechat.hdata_integer(weechat.hdata_get("line_data"), line_data, "tags_count")
    for i in range(tags_count):
        tag = weechat.hdata_string(weechat.hdata_get("line_data"), line_data, "{}|tags_array".format(i))
        tags.append(tag)

    return tags

def is_post_line_data(line_data, post_id):
    post_id_tag = "post_id_{}".format(post_id)
    tags = get_line_data_tags(line_data)

    for tag in tags:
        if tag.startswith(post_id_tag):
            return True

def find_buffer_last_post_line_data(buffer, post_id):
    lines = weechat.hdata_pointer(weechat.hdata_get("buffer"), buffer, "lines")
    line = weechat.hdata_pointer(weechat.hdata_get("lines"), lines, "last_line")

    line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")
    while True:
        if is_post_line_data(line_data, post_id):
            return line_data
        line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
        if "" == line:
            return None
        line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

def find_buffer_first_post_line_data(buffer, post_id):
    lines = weechat.hdata_pointer(weechat.hdata_get("buffer"), buffer, "lines")
    line = weechat.hdata_pointer(weechat.hdata_get("lines"), lines, "first_line")

    line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")
    while True:
        if is_post_line_data(line_data, post_id):
            return line_data
        line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "next_line")
        if "" == line:
            return None
        line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

CHANNEL_TYPES = {
    "D": "direct",
    "G": "group",
    "O": "public", # ordinary
    "P": "private",
}

NICK_GROUPS = {
    "away": "1|Away",
    "dnd": "2|Do not disturb",
    "offline": "3|Offline",
    "online": "0|Online",
    "unknown": "9|Unknown",
}

class ChannelBase:
    def __init__(self, server, **kwargs):
        self.id = kwargs["id"]
        self.type = CHANNEL_TYPES.get(kwargs["type"])
        self.title = kwargs["header"]
        self.server = server
        self.name = self._format_name(kwargs["display_name"], kwargs["name"])
        self.buffer = None
        self.posts = {}
        self.users = {}
        self._is_loading = False
        self._is_muted = None
        self.last_post_id = None
        self.last_read_post_id = None
        self.last_viewed_at = 0

        self._create_buffer()

    def _create_buffer(self):
        buffer_name = self._format_buffer_name()
        self.buffer = weechat.buffer_new(buffer_name, "channel_input_cb", "", "", "")

        weechat.buffer_set(self.buffer, "short_name", self.name)
        weechat.buffer_set(self.buffer, "title", self.title)

        weechat.buffer_set(self.buffer, "localvar_set_server_id", self.server.id)
        weechat.buffer_set(self.buffer, "localvar_set_channel_id", self.id)
        weechat.buffer_set(self.buffer, "localvar_set_type", "channel")

        weechat.buffer_set(self.buffer, "nicklist", "1")

        weechat.buffer_set(self.buffer, "highlight_words", ",".join(self.server.highlight_words))
        weechat.buffer_set(self.buffer, "localvar_set_nick", self.server.me.nick)

    def _update_buffer_name(self):
        prefix = ""
        if self._is_loading:
            prefix += config.get_value("look", "channel_loading_indicator")

        color = ""
        if self._is_muted:
            color = weechat.color(config.get_value("color", "channel_muted"))

        weechat.buffer_set(self.buffer, "short_name", color + prefix + self.name)

    # expects muted status to be set beforehand to notify loading posts accordingly
    def load(self):
        self.set_loading(True)

        EVENTROUTER.enqueue_request(
            "run_get_channel_posts_around_oldest_unread",
            self.id, self.server, "hydrate_channel_posts_cb", self.buffer
        )

        EVENTROUTER.enqueue_request(
            "run_get_channel_members",
            self.id, self.server, 0, "hydrate_channel_users_cb", "{}|{}|0".format(self.server.id, self.id)
        )

    def update_properties(self, channel_data):
        self.name = self._format_name(channel_data["display_name"], channel_data["name"])
        self.title = channel_data["header"]
        weechat.buffer_set(self.buffer, "short_name", self.name)
        weechat.buffer_set(self.buffer, "title", self.title)

    def _update_file_tags(self, post_id):
        if post_id not in self.posts:
            return

        post = self.posts[post_id]
        if not post.files:
            return

        lines = weechat.hdata_pointer(weechat.hdata_get("buffer"), self.buffer, "lines")
        line = weechat.hdata_pointer(weechat.hdata_get("lines"), lines, "last_line")
        line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

        # find last line of this post
        while line and not is_post_line_data(line_data, post_id):
            line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

        for file_id in reversed(post.files.keys()):
            tags = get_line_data_tags(line_data)
            tags.append("file_id_{}".format(file_id))
            weechat.hdata_update(weechat.hdata_get("line_data"), line_data, {"tags_array": ",".join(tags)})

            line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

            if not line or not is_post_line_data(line_data, post.id): # safeguard
                break

    def _prefix_thread_message(self, message, post_id, root):
        prefix_format = config.get_value("format", "thread_prefix_root") if root else config.get_value("format", "thread_prefix")
        prefix_color = config.get_value("color", "thread_prefix_root") if root else config.get_value("color", "thread_prefix")

        if config.get_value("look", "thread_prefix_user_color"):
            if post_id in self.posts:
                prefix_color = self.posts[post_id].user.color
            else:
                prefix_color = "default"

        suffix_string = config.get_value("look", "thread_prefix_suffix") or weechat.config_string(weechat.config_get("weechat.look.prefix_suffix"))
        suffix_color = config.get_value("color", "thread_prefix_suffix") or weechat.config_string(weechat.config_get("weechat.color.chat_prefix_suffix"))
        suffix = colorize(suffix_string, suffix_color)

        prefix = prefix_format.format(post_id[:3])
        prefix_empty = "{} {} ".format(" " * len(prefix), suffix)
        prefix = colorize(prefix, prefix_color)
        prefix_full = "{} {} ".format(prefix, suffix)

        lines = message.split("\n")
        lines = [ prefix_full + lines[0] ] + [ prefix_empty + l for l in lines[1:] ]

        return "\n".join(lines)

    def remove_post(self, post_id):
        del self.posts[post_id]

        pointers = self._get_lines_pointers(post_id)
        if not pointers:
            return

        lines = [""] * len(pointers)
        lines[0] = colorize(config.get_value("look", "deleted_suffix"), config.get_value("color", "deleted"))

        for pointer, line in zip(pointers, lines):
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), pointer, "data")
            weechat.hdata_update(weechat.hdata_get("line_data"), line_data, {"message": line, "tags_array":""})

    def edit_post(self, post):
        post.edited = True
        self.posts[post.id] = post
        self.update_post(post)

    def update_post(self, post):
        pointers = self._get_lines_pointers(post.id)
        if not pointers:
            return

        message = post.render_message(lines_count=len(pointers)) + post.render_reactions()

        if post.root_id:
            message = self._prefix_thread_message(message, post.root_id, root=False)
        elif post.thread_root:
            message = self._prefix_thread_message(message, post.id, root=True)

        lines = message.split("\n")

        for pointer, line in zip(pointers, lines):
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), pointer, "data")
            weechat.hdata_update(weechat.hdata_get("line_data"), line_data, {"message": line})

    def _get_lines_pointers(self, post_id):
        lines = weechat.hdata_pointer(weechat.hdata_get("buffer"), self.buffer, "lines")
        line = weechat.hdata_pointer(weechat.hdata_get("lines"), lines, "last_line")
        line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

        # find last line of this post
        while line and not is_post_line_data(line_data, post_id):
            line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")

        # find all lines of this post
        pointers = []
        while line and is_post_line_data(line_data, post_id):
            pointers.append(line)
            line = weechat.hdata_pointer(weechat.hdata_get("line"), line, "prev_line")
            line_data = weechat.hdata_pointer(weechat.hdata_get("line"), line, "data")
        pointers.reverse()

        return pointers

    def write_post(self, post):
        self.posts[post.id] = post

        tags = "post_id_{}".format(post.id)

        root_post = self.posts.get(post.root_id)
        if root_post:
            root_post.thread_root = True
            self.update_post(root_post)

        if post.read:
            tags += ",notify_none"
        elif root_post and root_post.user == self.server.me and root_post.user != post.user and self.type != 'direct':
            # if somebody (not us) reply to our post (not in a DM channel)
            tags += ",notify_highlight"
        elif self.type in ['direct', 'group']:
            tags += ",notify_private"
        else:
            tags += ",notify_message"

        if post.user == self.server.me:
            tags += ",no_highlight"

        prefix = "{}\t".format(post.render_nick())
        if post.type in [ "system_join_channel", "system_join_team" ]:
            prefix = weechat.prefix("join")
        elif post.type in [ "system_leave_channel", "system_leave_team" ]:
            prefix = weechat.prefix("quit")

        message = post.render_message() + post.render_reactions()
        if post.root_id:
            message = self._prefix_thread_message(message, post.root_id, root=False)

        date = int(post.created_at / 1000)

        weechat.prnt_date_tags(self.buffer, date, tags, prefix + message)

        self._update_file_tags(post.id)

        self.last_post_id = post.id

    def mark_as_read(self):
        if self.last_post_id and self.last_post_id == self.last_read_post_id: # prevent spamming on buffer switch
            return

        run_post_channel_view(self.id, self.server, "singularity_cb", self.buffer)

    def add_user(self, user_id):
        if user_id not in self.server.users:
            return

        user = self.server.users[user_id]

        if user.deleted:
            return

        self.users[user_id] = user

        color = ""
        if weechat.config_string_to_boolean(weechat.config_string(weechat.config_get("irc.look.color_nicks_in_nicklist"))):
            color = user.color

        weechat.nicklist_add_nick(self.buffer, "", user.nick, color, "", color, 1)

    def remove_user(self, user_id):
        user = self.users.pop(user_id, None)
        if user:
            nick = weechat.nicklist_search_nick(self.buffer, "", user.nick)
            weechat.nicklist_remove_nick(self.buffer, nick)

    def update_nicklist(self):
        for user in self.users.values():
            self.update_nicklist_user(user)

        self.remove_empty_nick_groups()

    def update_nicklist_user(self, user):
        group = self._get_nick_group(user.status)
        color = ""

        nick = weechat.nicklist_search_nick(self.buffer, "", user.nick)
        weechat.nicklist_remove_nick(self.buffer, nick)

        if weechat.config_string_to_boolean(weechat.config_string(weechat.config_get("irc.look.color_nicks_in_nicklist"))):
            if user.status == "online":
                color = user.color
            else:
                color = weechat.config_string(weechat.config_get("weechat.color.nicklist_away"))

        weechat.nicklist_add_nick(self.buffer, group, user.nick, color, "", color, 1)

    def remove_empty_nick_groups(self):
        root = weechat.hdata_pointer(weechat.hdata_get("buffer"), self.buffer, "nicklist_root")
        group = weechat.hdata_pointer(weechat.hdata_get("nick_group"), root, "children")

        while group:
            if not weechat.hdata_pointer(weechat.hdata_get("nick_group"), group, "last_nick"):
                # tried deleting or marking group as not visible via hdata_update but it doesn't seem to work
                name = weechat.hdata_string(weechat.hdata_get("nick_group"), group, "name")
                g = weechat.nicklist_search_group(self.buffer, "", name)
                weechat.nicklist_remove_group(self.buffer, g)

            group = weechat.hdata_pointer(weechat.hdata_get("nick_group"), group, "next_group")

    def set_loading(self, loading):
        self._is_loading = loading
        self._update_buffer_name()

    def is_loading(self):
        return self._is_loading

    def mute(self):
        self._is_muted = True
        self._update_buffer_name()

        weechat.buffer_set(self.buffer, "notify", "1") # highlight only

    def unmute(self):
        self._is_muted = False
        self._update_buffer_name()

        # using "/buffer notify reset" doesn't seem to do the trick
        buffer_full_name = weechat.buffer_get_string(self.buffer, "full_name")
        weechat.command(self.buffer, "/mute /unset weechat.notify.{}".format(buffer_full_name))

    def _get_nick_group(self, status):
        name = NICK_GROUPS.get(status)
        if not name:
            name = NICK_GROUPS.get("unknown")

        group = weechat.nicklist_search_group(self.buffer, "", name)
        if not group:
            group = weechat.nicklist_add_group(self.buffer, "", name, "weechat.color.nicklist_group", 1)

        return group

    def _format_buffer_name(self):
        parent_buffer_name = weechat.buffer_get_string(self.server.buffer, "name")
        # use "!" character so that the buffer gets sorted just after the server buffer and before all teams buffers
        return "{}.!.{}".format(parent_buffer_name[:-1], self.name)

    def _format_name(self, display_name, name):
        final_name = display_name

        name_override = config.get_value("look", "channel.{}".format(name))

        if name_override:
            final_name = name_override

        return config.get_value("look", "channel_prefix_{}".format(self.type)) + final_name

    def unload(self):
        weechat.buffer_close(self.buffer)
        self.buffer = None

class DirectMessagesChannel(ChannelBase):
    def __init__(self, server, **kwargs):
        super(DirectMessagesChannel, self).__init__(server, **kwargs)
        self.user = self._get_user(kwargs["name"])
        self._status = None

    def set_status(self, status):
        self._status = status
        self._update_buffer_name()

    def _update_buffer_name(self):
        prefix = ""
        if self._is_loading:
            prefix += config.get_value("look", "channel_loading_indicator")

        if NICK_GROUPS.get(self._status):
            prefix += config.get_value("look", "channel_prefix_direct_{}".format(self._status))
        else:
            prefix += "?"

        color = ""
        if self._is_muted:
            color = weechat.color(config.get_value("color", "channel_muted"))
        if self._status != "online" and config.get_value("look", "buflist_color_away_nick"):
            color += weechat.color("|" + weechat.config_string(weechat.config_get("weechat.color.nicklist_away")))

        weechat.buffer_set(self.buffer, "short_name", color + prefix + self.name)

    def _format_name(self, display_name, name):
        return self._get_user(name).nick

    def _get_user(self, name):
        match = re.match("(\w+)__(\w+)", name)

        user = self.server.users[match.group(1)]
        if user == self.server.me:
            user = self.server.users[match.group(2)]

        return user

class GroupChannel(ChannelBase):
    def __init__(self, server, **kwargs):
        super(GroupChannel, self).__init__(server, **kwargs)

class PrivateChannel(ChannelBase):
    def __init__(self, team, **kwargs):
        self.team = team
        super(PrivateChannel, self).__init__(team.server, **kwargs)

    def _format_buffer_name(self):
        parent_buffer_name = weechat.buffer_get_string(self.team.buffer, "name")
        return "{}.{}".format(parent_buffer_name[:-1], self.name)

class PublicChannel(ChannelBase):
    def __init__(self, team, **kwargs):
        self.team = team
        super(PublicChannel, self).__init__(team.server, **kwargs)

    def _format_buffer_name(self):
        parent_buffer_name = weechat.buffer_get_string(self.team.buffer, "name")
        return "{}.{}".format(parent_buffer_name[:-1], self.name)

def channel_input_cb(data, buffer, input_data):
    server = get_server_from_buffer(buffer)

    post = {
        "channel_id": weechat.buffer_get_string(buffer, "localvar_channel_id"),
        "message": input_data,
    }

    run_post_post(post, server, "post_post_cb", buffer)

    return weechat.WEECHAT_RC_OK

def hydrate_channel_posts_cb(buffer, command, rc, out, err):
    server = get_server_from_buffer(buffer)

    if rc != 0:
        server.print_error("An error occurred while hydrating channel")
        return weechat.WEECHAT_RC_ERROR

    channel = server.get_channel_from_buffer(buffer)

    response = json.loads(out)

    if not response["order"]:
        channel.set_loading(False)
        return weechat.WEECHAT_RC_OK

    for post_id in reversed(response["order"]):
        builded_post = Post(server, **response["posts"][post_id])
        channel.write_post(builded_post)

    if "" != response["next_post_id"]:
        EVENTROUTER.enqueue_request(
            "run_get_channel_posts_after",
            builded_post.id, channel.id, server, "hydrate_channel_posts_cb", buffer
        )
    else:
        channel.set_loading(False)

    return weechat.WEECHAT_RC_OK

def hydrate_channel_users_cb(data, command, rc, out, err):
    server_id, channel_id, page = data.split("|")
    page = int(page)
    server = servers[server_id]
    channel = server.get_channel(channel_id)

    if rc != 0:
        server.print_error("An error occurred while hydrating channel users")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    if len(response) == 200:
        EVENTROUTER.enqueue_request(
            "run_get_channel_members",
            channel.id, server, page+1, "hydrate_channel_users_cb", "{}|{}|{}".format(server_id, channel_id, page+1)
        )

    for user_data in response:
        channel.add_user(user_data["user_id"])

    return weechat.WEECHAT_RC_OK

def load_channels_cb(data, command, rc, out, err):
    server_id, page = data.split("|")
    page = int(page)
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while updating channel mute status")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    if len(response) == 100:
        EVENTROUTER.enqueue_request(
            "run_get_user_channel_members",
            server, page+1, "load_channels_cb", "{}|{}".format(server_id, page+1)
        )

    for member_data in response:
        channel = server.get_channel(member_data["channel_id"])
        if channel:
            channel.last_viewed_at = member_data["last_viewed_at"]

            if member_data["notify_props"]["mark_unread"] == "all":
                channel.unmute()
            else:
                channel.mute()

            channel.load()

    return weechat.WEECHAT_RC_OK

def hydrate_channel_users_status_cb(data, command, rc, out, err):
    server_id, channel_id = data.split("|")
    server = servers[server_id]
    channel = server.get_channel(channel_id)

    if rc != 0:
        server.print_error("An error occurred while hydrating channel users status")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    for user_data in response:
        user_id = user_data["user_id"]
        if user_id not in channel.users:
            continue
        user = channel.users[user_id]
        user.status = user_data["status"]

    channel.update_nicklist()

    return weechat.WEECHAT_RC_OK

def update_direct_message_channels_name(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while updating direct message channels name")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    for user_data in response:
        channel = server.get_direct_messages_channel(user_data["user_id"])
        if channel:
            channel.set_status(user_data["status"])

    return weechat.WEECHAT_RC_OK

def update_custom_emojis(data, command, rc, out, err):
    server_id, page = data.split("|")
    page = int(page)
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while updating custom emojis")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    for emoji in response:
        server.custom_emojis.append(emoji["name"])

    if len(response) == 150:
        EVENTROUTER.enqueue_request(
            "run_get_custom_emojis",
            server, page+1, "update_custom_emojis", "{}|{}".format(server.id, page+1)
        )

    return weechat.WEECHAT_RC_OK

def create_channel_from_channel_data(channel_data, server):
    if channel_data["type"] == "D":
        match = re.match("(\w+)__(\w+)", channel_data["name"])
        user_1_id, user_2_id = match.group(1), match.group(2)
        if user_1_id in server.closed_channels:
            server.closed_channels[user_1_id] = channel_data["id"]
            return
        if user_2_id in server.closed_channels:
            server.closed_channels[user_2_id] = channel_data["id"]
            return
        if server.users[user_1_id].deleted or server.users[user_2_id].deleted:
            return

        channel = DirectMessagesChannel(server, **channel_data)
        server.channels[channel.id] = channel
    elif channel_data["type"] == "G":
        if channel_data["id"] in server.closed_channels:
            return

        channel = GroupChannel(server, **channel_data)
        server.channels[channel.id] = channel
    else:
        team = server.teams[channel_data["team_id"]]

        if channel_data["type"] == "P":
            channel = PrivateChannel(team, **channel_data)
        elif channel_data["type"] == "O":
            channel = PublicChannel(team, **channel_data)
        else:
            server.print_error("Unknown channel type {}".format(channel_data["type"]))
            channel = PublicChannel(team, **channel_data)

        team.channels[channel.id] = channel

    return channel

def buffer_switch_cb(data, signal, buffer):
    for server in servers.values():
        channel = server.get_channel_from_buffer(buffer)
        if channel and channel.users:
            channel.mark_as_read()
            EVENTROUTER.enqueue_request(
                "run_post_users_status_ids",
                list(channel.users.keys()), server, "hydrate_channel_users_status_cb", "{}|{}".format(server.id, channel.id)
            )
            break

    return weechat.WEECHAT_RC_OK

def chat_line_event_cb(data, signal, hashtable):
    tags = hashtable["_chat_line_tags"].split(",")

    for tag in tags:
        if tag.startswith("post_id_"):
            post_id = tag[8:]
            break
    else:
        return weechat.WEECHAT_RC_OK

    buffer = hashtable["_buffer"]

    if data == "insert_post_id":
        weechat.command(buffer, "/input insert \\x20{}\\x20".format(post_id))
    elif data == "delete":
        weechat.command(buffer, "/input send /mattermost delete {}".format(post_id))
    elif data == "reply":
        weechat.command(buffer, "/cursor stop")
        weechat.command(buffer, "/input delete_line")
        weechat.command(buffer, "/input insert /mattermost reply {}\\x20".format(post_id))
    elif data == "react":
        weechat.command(buffer, "/cursor stop")
        weechat.command(buffer, "/input delete_line")
        weechat.command(buffer, "/input insert /mattermost react {} :".format(post_id))
    elif data == "unreact":
        weechat.command(buffer, "/cursor stop")
        weechat.command(buffer, "/input delete_line")
        weechat.command(buffer, "/input insert /mattermost unreact {} :".format(post_id))
    elif data == "post_open":
        weechat.command(buffer, "/cursor stop")

        server = get_server_from_buffer(buffer)
        channel = server.get_channel_from_buffer(buffer)
        post = channel.posts[post_id]
        post.open()

    elif data.startswith("file_"):
        for tag in tags:
            if tag.startswith("file_id_"):
                file_id = tag[8:]
                break
        else:
            return weechat.WEECHAT_RC_OK

        server = get_server_from_buffer(buffer)
        channel = server.get_channel_from_buffer(buffer)
        post = channel.posts[post_id]
        file = post.files[file_id]

        if data == "file_download":
            file.download()
        elif data == "file_open":
            file.download(temporary=True, open=True)

    return weechat.WEECHAT_RC_OK

def handle_multiline_message_cb(data, modifier, buffer, string):
    for server in servers.values():
        if server.get_channel_from_buffer(buffer):
            if "\n" in string and not string[0] == "/":
                channel_input_cb(data, buffer, string)
                return ""
            return string

    return string

class User:
    def __init__(self, **kwargs):
        self.id = kwargs["id"]
        self.username = kwargs["username"]
        self.first_name = kwargs["first_name"]
        self.last_name = kwargs["last_name"]
        self.status = None
        self.deleted = kwargs["delete_at"] != 0
        self.color = weechat.info_get("nick_color_name", self.username)

    @property
    def nick(self):
        nick = self.username

        if config.get_value("look", "nick_full_name") and self.first_name and self.last_name:
            nick = "{} {}".format(self.first_name, self.last_name)

        return nick

class Server:
    def __init__(self, id):
        self.id = id

        if not config.is_server_valid(id):
            raise ValueError("Invalid server id {}".format(id))

        self.url = config.get_server_value(id, "url").strip("/")
        self.username = config.get_server_value(id, "username")
        self.password = config.get_server_value(id, "password")
        self.command_2fa = config.get_server_value(id, "command_2fa")

        if not self.url or not self.username or not self.password:
            raise ValueError("Server {} is not fully configured".format(id))

        self.token = ""
        self.me = None
        self.highlight_words = []
        self.users = {}
        self.teams = {}
        self.buffer = None
        self.channels = {}
        self.worker = None
        self.reconnection_loop_hook = ""
        self.closed_channels = {}
        self.custom_emojis = []

        self._create_buffer()

    def _create_buffer(self):
        # use "*" character so that the buffer is unique and gets sorted before all server buffers
        buffer_name = "wee_most.{}*".format(self.id)
        self.buffer = weechat.buffer_new(buffer_name, "", "", "", "")
        weechat.buffer_set(self.buffer, "short_name", self.id)
        weechat.buffer_set(self.buffer, "localvar_set_server_id", self.id)
        weechat.buffer_set(self.buffer, "localvar_set_type", "server")

        buffer_merge(self.buffer)

    def init_me(self, **kwargs):
        self.me = User(**kwargs)
        self.me.color = weechat.config_string(weechat.config_get("weechat.color.chat_nick_self"))

        if kwargs["notify_props"]["first_name"] == "true":
            self.highlight_words.append(kwargs["first_name"])

        if kwargs["notify_props"]["channel"] == "true":
            self.highlight_words.extend(mentions)

        if kwargs["notify_props"]["mention_keys"]:
            self.highlight_words.extend(kwargs["notify_props"]["mention_keys"].split(","))

    def print(self, message):
        weechat.prnt(self.buffer, message)

    def print_error(self, message):
        weechat.prnt(self.buffer, weechat.prefix("error") + message)

    def get_channel(self, channel_id):
        if channel_id in self.channels:
            return self.channels[channel_id]

        for team in self.teams.values():
            if channel_id in team.channels:
                return team.channels[channel_id]

        return None

    def get_channel_from_buffer(self, buffer):
        channel_id = weechat.buffer_get_string(buffer, "localvar_channel_id")

        if not channel_id:
            return None

        if channel_id in self.channels:
            return self.channels[channel_id]

        for team in self.teams.values():
            if channel_id in team.channels:
                return team.channels[channel_id]

        return None

    def remove_channel(self, channel_id):
        if channel_id in self.channels:
            del self.channels[channel_id]
            return

        for team in self.teams.values():
            if channel_id in team.channels:
                del team.channels[channel_id]
                return

    def get_direct_messages_channels(self):
        channels = []

        for channel in self.channels.values():
            if isinstance(channel, DirectMessagesChannel):
                channels.append(channel)

        return channels

    def get_direct_messages_channel(self, user_id):
        for channel in self.channels.values():
            if isinstance(channel, DirectMessagesChannel) and channel.user.id == user_id:
                return channel

    def fetch_direct_message_channels_user_status(self, channel=None):
        user_ids = []

        if channel:
            user_ids.append(channel.user.id)
        else:
            for channel in self.get_direct_messages_channels():
                user_ids.append(channel.user.id)

        EVENTROUTER.enqueue_request(
            "run_post_users_status_ids",
            user_ids, self, "update_direct_message_channels_name", self.id
        )

    def get_post(self, post_id):
        for channel in self.channels.values():
            if post_id in channel.posts:
                return channel.posts[post_id]

        for team in self.teams.values():
            for channel in team.channels.values():
                if post_id in channel.posts:
                    return channel.posts[post_id]

        return None

    def is_connected(self):
        return self.worker

    def add_team(self, team):
        self.teams[team.id] = team

    def retrieve_2fa_token(self):
        try:
            out = subprocess.check_output(self.command_2fa, shell=True)
        except (subprocess.CalledProcessError):
            self.print_error("Failed to retrieve 2FA token")
            return ""

        return out.decode("utf-8")

    def unload(self):
        self.print("Unloading server")

        if self.worker:
            close_worker(self.worker)
        if self.reconnection_loop_hook:
            weechat.unhook(self.reconnection_loop_hook)

        for channel in self.channels.values():
            channel.unload()
        for team in self.teams.values():
            team.unload()
        weechat.buffer_close(self.buffer)
        self.buffer = None
        self.channels = {}
        self.teams = {}

class Team:
    def __init__(self, server, **kwargs):
        self.server = server
        self.id = kwargs["id"]
        self.name = kwargs["name"]
        self.display_name= kwargs["display_name"]
        self.buffer = None
        self.channels = {}

        self._create_buffer()

    def _create_buffer(self):
        parent_buffer_name = weechat.buffer_get_string(self.server.buffer, "name")[:-1]
        # use "*" character so that the buffer is unique and gets sorted before all team buffers
        buffer_name = "{}.{}*".format(parent_buffer_name, self.display_name)
        self.buffer = weechat.buffer_new(buffer_name, "", "", "", "")

        weechat.buffer_set(self.buffer, "short_name", self.display_name)
        weechat.buffer_set(self.buffer, "localvar_set_server_id", self.server.id)
        weechat.buffer_set(self.buffer, "localvar_set_type", "server")

        buffer_merge(self.buffer)

    def unload(self):
        for channel in self.channels.values():
            channel.unload()
        weechat.buffer_close(self.buffer)
        self.channels = {}
        self.buffer = None

def buffer_merge(buffer):
    if weechat.config_string(weechat.config_get("irc.look.server_buffer")) == "merge_with_core":
        weechat.buffer_merge(buffer, weechat.buffer_search_main())
    else:
        weechat.buffer_unmerge(buffer, 0)

def config_server_buffer_cb(data, key, value):
    for server in servers.values():
        buffer_merge(server.buffer)
        for team in server.teams.values():
            buffer_merge(team.buffer)
    return weechat.WEECHAT_RC_OK

def get_server_from_buffer(buffer):
    server_id = weechat.buffer_get_string(buffer, "localvar_server_id")

    if not server_id:
        return None

    return servers[server_id]

def get_buffer_user_status_cb(data, remaining_calls):
    buffer = weechat.current_buffer()

    for server in servers.values():
        channel = server.get_channel_from_buffer(buffer)
        if channel and channel.users:
            EVENTROUTER.enqueue_request(
                "run_post_users_status_ids",
                list(channel.users.keys()), server, "hydrate_channel_users_status_cb", "{}|{}".format(server.id, channel.id)
            )
            break

    return weechat.WEECHAT_RC_OK

def get_direct_message_channels_user_status_cb(data, remaining_calls):
    for server in servers.values():
        server.fetch_direct_message_channels_user_status()

    return weechat.WEECHAT_RC_OK

def connect_server_team_channel(channel_id, server):
    EVENTROUTER.enqueue_request(
        "run_get_channel",
        channel_id, server, "connect_server_team_channel_cb", server.id
    )

def connect_server_team_channel_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting team channel")
        return weechat.WEECHAT_RC_ERROR

    channel_data = json.loads(out)
    if server.get_channel(channel_data["id"]):
        return weechat.WEECHAT_RC_OK
    channel = create_channel_from_channel_data(channel_data, server)

    if isinstance(channel, DirectMessagesChannel):
        server.fetch_direct_message_channels_user_status(channel)

    # this is only used for channel appearing so shouldn't be muted immediately
    channel.load()

    return weechat.WEECHAT_RC_OK

def connect_server_team_channels_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting team channels")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)
    for channel_data in response:
        if server.get_channel(channel_data["id"]):
            continue
        create_channel_from_channel_data(channel_data, server)

    server.fetch_direct_message_channels_user_status()

    EVENTROUTER.enqueue_request(
        "run_get_user_channel_members",
        server, 0, "load_channels_cb", "{}|0".format(server.id)
    )

    return weechat.WEECHAT_RC_OK

def connect_server_users_cb(data, command, rc, out, err):
    server_id, page = data.split("|")
    page = int(page)
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting users")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)
    for user in response:
        if user["id"] == server.me.id:
            server.users[user["id"]] = server.me
        else:
            server.users[user["id"]] = User(**user)

    if len(response) == 200:
        EVENTROUTER.enqueue_request(
            "run_get_users",
            server, page+1, "connect_server_users_cb", "{}|{}".format(server.id, page+1)
        )
    else:
        EVENTROUTER.enqueue_request(
            "run_get_user_teams",
            server, "connect_server_teams_cb", server.id
        )

    return weechat.WEECHAT_RC_OK

def connect_server_preferences_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting preferences")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    for pref in response:
        if pref["category"] in ["direct_channel_show", "group_channel_show"] and pref["value"] == "false":
            server.closed_channels[pref["name"]] = None # will contain channel id if encountered later

    return weechat.WEECHAT_RC_OK

def connect_server_teams_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting teams")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)

    for team_data in response:
        team = Team(server, **team_data)
        server.add_team(team)

        EVENTROUTER.enqueue_request(
            "run_get_user_team_channels",
            team.id, server, "connect_server_team_channels_cb", server.id
        )

    return weechat.WEECHAT_RC_OK

def connect_server_team_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting team")
        return weechat.WEECHAT_RC_ERROR

    team_data = json.loads(out)

    team = Team(server, **team_data)
    server.add_team(team)

    EVENTROUTER.enqueue_request(
        "run_get_user_team_channels",
        team.id, server, "connect_server_team_channels_cb", server.id
    )

    return weechat.WEECHAT_RC_OK

def new_user_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while adding a new user")
        return weechat.WEECHAT_RC_ERROR

    response = json.loads(out)
    server.users[response["id"]] = User(**response)

    return weechat.WEECHAT_RC_OK

def connect_server_cb(server_id, command, rc, out, err):
    server = servers[server_id]

    if rc != 0:
        server.print_error("An error occurred while connecting")
        return weechat.WEECHAT_RC_ERROR

    token_search = re.search("[tT]oken: (\w*)", out)

    out = out.splitlines()[-1] # we remove the headers line
    response = json.loads(out)

    server.token = token_search.group(1)
    server.init_me(**response)

    try:
        worker = Worker(server)
    except:
        server.print_error("An error occurred while creating the websocket worker")
        return weechat.WEECHAT_RC_ERROR

    reconnection_loop_hook = weechat.hook_timer(5 * 1000, 0, 0, "reconnection_loop_cb", server.id)

    server.worker = worker
    server.reconnection_loop_hook = reconnection_loop_hook

    server.print("Connected to {}".format(server_id))

    EVENTROUTER.enqueue_request(
        "run_get_custom_emojis",
        server, 0, "update_custom_emojis", "{}|0".format(server.id)
    )

    EVENTROUTER.enqueue_request(
        "run_get_users",
        server, 0, "connect_server_users_cb", "{}|0".format(server.id)
    )

    EVENTROUTER.enqueue_request(
        "run_get_preferences",
        server, "connect_server_preferences_cb", server.id
    )

    return weechat.WEECHAT_RC_OK

def connect_server(server_id):
    if server_id in servers:
        server = servers[server_id]

        if server != None and server.is_connected():
            server.print_error("Already connected")
            return weechat.WEECHAT_RC_ERROR

        if server != None:
            server.unload()
            servers.pop(server_id)

    try:
        server = Server(server_id)
    except ValueError as ve:
        weechat.prnt("", weechat.prefix("error") + str(ve))
        return weechat.WEECHAT_RC_ERROR

    server.print("Connecting to {}".format(server_id))

    servers[server_id] = server

    EVENTROUTER.enqueue_request(
        "run_user_login",
        server, "connect_server_cb", server.id
    )

    return weechat.WEECHAT_RC_OK

def disconnect_server(server_id):
    server = servers[server_id]

    if not server.is_connected():
        server.print_error("Not connected")
        return weechat.WEECHAT_RC_ERROR

    rc = logout_user(server)

    if rc == weechat.WEECHAT_RC_OK:
        server.unload()
        servers.pop(server_id)

    return rc

def singularity_cb(buffer, command, rc, out, err):
    server = get_server_from_buffer(buffer)

    if rc != 0:
        server.print_error("An error occurred while performing a request")
        return weechat.WEECHAT_RC_ERROR

    return weechat.WEECHAT_RC_OK

def build_buffer_cb_data(url, cb, cb_data):
    return "{}|{}|{}".format(url, cb, cb_data)

class EventRouter:
    def __init__(self):
        self.enqueued_requests = []
        self.response_buffers = {}

    def enqueue_request(self, method, *params):
        self.enqueued_requests.append([method, params])

    def handle_next(self):
        if not self.enqueued_requests:
            return

        request = self.enqueued_requests.pop(0)
        eval(request[0])(*request[1])

    def buffered_response_cb(self, data, command, rc, out, err):
        arg_search = re.search("([^\|]*)\|([^\|]*)\|(.*)", data)
        response_buffer_name = arg_search.group(1)
        real_cb = arg_search.group(2)
        real_data = arg_search.group(3)

        if not response_buffer_name in self.response_buffers:
            self.response_buffers[response_buffer_name] = ""

        if rc == weechat.WEECHAT_HOOK_PROCESS_RUNNING:
            self.response_buffers[response_buffer_name] += out
            return weechat.WEECHAT_RC_OK

        response = self.response_buffers[response_buffer_name] + out
        del self.response_buffers[response_buffer_name]

        return eval(real_cb)(real_data, command, rc, response, err)

def handle_queued_request_cb(data, remaining_calls):
    EVENTROUTER.handle_next()
    return weechat.WEECHAT_RC_OK

def run_get_user_teams(server, cb, cb_data):
    url = server.url + "/api/v4/users/me/teams"
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_team(team_id, server, cb, cb_data):
    url = server.url + "/api/v4/teams/{}".format(team_id)
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_users(server, page, cb, cb_data):
    url = server.url + "/api/v4/users?per_page=200&page={}".format(str(page))
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_user(server, user_id, cb, cb_data):
    url = server.url + "/api/v4/users/{}".format(user_id)
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_custom_emojis(server, page, cb, cb_data):
    url = server.url + "/api/v4/emoji?per_page=150&page={}".format(str(page))
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

# Logging out synchronously for usage in shutdown function
def logout_user(server):
    url = server.url + "/api/v4/users/logout"
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + server.token)

    try:
        urllib.request.urlopen(req, b'', 10 * 1000)
    except:
        server.print_error("An error occurred while disconnecting")
        return weechat.WEECHAT_RC_ERROR

    server.print("Disconnected")
    return weechat.WEECHAT_RC_OK

def run_user_login(server, cb, cb_data):
    url = server.url + "/api/v4/users/login"
    params = {
        "login_id": server.username,
        "password": server.password,
    }

    if server.command_2fa:
        token = server.retrieve_2fa_token()
        if not token:
            return weechat.WEECHAT_RC_ERROR
        params["token"] = token

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "postfields": json.dumps(params),
            "header": "1",
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_channel(channel_id, server, cb, cb_data):
    url = server.url + "/api/v4/channels/{}".format(channel_id)
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_user_team_channels(team_id, server, cb, cb_data):
    url = server.url + "/api/v4/users/me/teams/{}/channels".format(team_id)
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_post_post(post, server, cb, cb_data):
    url = server.url + "/api/v4/posts"
    params = {
        "channel_id": post["channel_id"],
        "message": post["message"],
    }

    if "root_id" in post:
        params["root_id"] = post["root_id"]

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
            "postfields": json.dumps(params),
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_post_command(team_id, channel_id, command, server, cb, cb_data):
    url = server.url + "/api/v4/commands/execute"
    params = {
        "channel_id": channel_id,
        "team_id": team_id,
        "command": command,
    }

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
            "postfields": json.dumps(params),
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_channel_posts_around_oldest_unread(channel_id, server, cb, cb_data):
    url = server.url + "/api/v4/users/me/channels/{}/posts/unread".format(channel_id)
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_channel_posts_after(post_id, channel_id, server, cb, cb_data):
    if post_id:
        url = server.url + "/api/v4/channels/{}/posts?after={}".format(channel_id, post_id)
    else:
        url = server.url + "/api/v4/channels/{}/posts".format(channel_id)

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_channel_members(channel_id, server, page, cb, cb_data):
    url = server.url + "/api/v4/channels/{}/members?per_page=200&page={}".format(channel_id, str(page))
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_user_channel_members(server, page, cb, cb_data):
    url = server.url + "/api/v4/users/me/channel_members?pageSize=100&page={}".format(str(page))
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_post_users_status_ids(user_ids, server, cb, cb_data):
    url = server.url + "/api/v4/users/status/ids"
    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "postfields": json.dumps(user_ids),
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_post_channel_view(channel_id, server, cb, cb_data):
    url = server.url + "/api/v4/channels/members/me/view"
    params = {
        "channel_id": channel_id,
    }

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "postfields": json.dumps(params),
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_post_reaction(emoji_name, post_id, server, cb, cb_data):
    url = server.url + "/api/v4/reactions"
    params = {
        "user_id": server.me.id,
        "post_id": post_id,
        "emoji_name": emoji_name,
        "create_at": int(time.time() * 1000),
    }

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "postfields": json.dumps(params),
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_delete_reaction(emoji_name, post_id, server, cb, cb_data):
    url = server.url + "/api/v4/users/me/posts/{}/reactions/{}".format(post_id, emoji_name)

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "customrequest": "DELETE",
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_delete_post(post_id, server, cb, cb_data):
    url = server.url + "/api/v4/posts/{}".format(post_id)

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "customrequest": "DELETE",
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_file(file_id, file_out_path, server, cb, cb_data):
    url = server.url + "/api/v4/files/{}".format(file_id)

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "file_out": file_out_path,
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

def run_get_preferences(server, cb, cb_data):
    url = server.url + "/api/v4/users/me/preferences"

    weechat.hook_process_hashtable(
        "url:" + url,
        {
            "failonerror": "1",
            "httpheader": "Authorization: Bearer " + server.token,
        },
        REQUEST_TIMEOUT_MS,
        "buffered_response_cb",
        build_buffer_cb_data(url, cb, cb_data)
    )

class Worker:
    def __init__(self, server):
        self.last_ping_time = 0
        self.last_pong_time = 0

        url = server.url.replace("http", "ws", 1) + "/api/v4/websocket"
        self.ws = create_connection(url)
        self.ws.sock.setblocking(0)

        params = {
            "seq": 1,
            "action": "authentication_challenge",
            "data": {
                "token": server.token,
            }
        }

        self.hook_data_read = weechat.hook_fd(self.ws.sock.fileno(), 1, 0, 0, "receive_ws_callback", server.id)
        self.ws.send(json.dumps(params))

        self.hook_ping = weechat.hook_timer(5 * 1000, 0, 0, "ws_ping_cb", server.id)

def rehydrate_server_buffer(server, buffer):
    channel = server.get_channel_from_buffer(buffer)
    if not channel:
        return
    channel.set_loading(True)

    EVENTROUTER.enqueue_request(
        "run_get_channel_posts_after",
        channel.last_post_id, channel.id, server, "hydrate_channel_posts_cb", buffer
    )

def rehydrate_server_buffers(server):
    server.print("Syncing...")
    for channel in server.channels.values():
        rehydrate_server_buffer(server, channel.buffer)
    for team in server.teams.values():
        for channel in team.channels.values():
            rehydrate_server_buffer(server, channel.buffer)

def reconnection_loop_cb(server_id, remaining_calls):
    server = servers[server_id]
    if server != None and server.is_connected():
        return weechat.WEECHAT_RC_OK

    server.print("Reconnecting...")

    try:
        new_worker = Worker(server)
    except:
        server.print_error("Reconnection issue. Trying again in a few seconds...")
        return weechat.WEECHAT_RC_ERROR

    server.worker = new_worker
    server.print("Reconnected.")
    rehydrate_server_buffers(server)
    return weechat.WEECHAT_RC_OK

def close_worker(worker):
    weechat.unhook(worker.hook_data_read)
    weechat.unhook(worker.hook_ping)
    worker.ws.close()

def handle_lost_connection(server):
    server.print("Connection lost.")
    close_worker(server.worker)
    server.worker = None

def ws_ping_cb(server_id, remaining_calls):
    server = servers[server_id]
    worker = server.worker

    if worker.last_pong_time < worker.last_ping_time:
        handle_lost_connection(server)
        return weechat.WEECHAT_RC_OK

    try:
        worker.ws.ping()
        worker.last_ping_time = time.time()
        server.worker = worker
    except (WebSocketConnectionClosedException, socket.error) as e:
        handle_lost_connection(server)

    return weechat.WEECHAT_RC_OK

def handle_posted_message(server, data, broadcast):
    post = json.loads(data["post"])

    if data["team_id"] and data["team_id"] not in server.teams:
        return

    channel = server.get_channel(broadcast["channel_id"])
    if not channel or channel.is_loading():
        return

    post = Post(server, **post)
    channel.write_post(post)

    if channel.buffer == weechat.current_buffer():
        post.channel.mark_as_read()

def handle_reaction_added_message(server, data, broadcast):
    reaction_data = json.loads(data["reaction"])

    channel = server.get_channel(broadcast["channel_id"])
    if not channel or reaction_data["post_id"] not in channel.posts:
        return

    post = channel.posts[reaction_data["post_id"]]
    post.add_reaction(Reaction(server, **reaction_data))
    channel.update_post(post)

def handle_reaction_removed_message(server, data, broadcast):
    reaction_data = json.loads(data["reaction"])

    channel = server.get_channel(broadcast["channel_id"])
    if not channel or reaction_data["post_id"] not in channel.posts:
        return

    post = channel.posts[reaction_data["post_id"]]
    post.remove_reaction(Reaction(server, **reaction_data))
    channel.update_post(post)

def handle_post_edited_message(server, data, broadcast):
    post_data = json.loads(data["post"])
    post = Post(server, **post_data)
    if server.get_post(post.id) is not None:
        post.channel.edit_post(post)

def handle_post_deleted_message(server, data, broadcast):
    post_data = json.loads(data["post"])
    post = Post(server, **post_data)
    if server.get_post(post.id) is not None:
        post.channel.remove_post(post.id)

def handle_channel_created_message(server, data, broadcast):
    connect_server_team_channel(broadcast["channel_id"], server)

def handle_channel_member_updated_message(server, data, broadcast):
    channel_member_data = json.loads(data["channelMember"])
    if channel_member_data["user_id"] == server.me.id:
        channel = server.get_channel(channel_member_data["channel_id"])
        if channel:
            if channel_member_data["notify_props"]["mark_unread"] == "all":
                channel.unmute()
            else:
                channel.mute()

def handle_channel_updated_message(server, data, broadcast):
    channel_data = json.loads(data["channel"])
    channel = server.get_channel(channel_data["id"])
    if not channel:
        return
    channel.update_properties(channel_data)

def handle_channel_viewed_message(server, data, broadcast):
    channel = server.get_channel(data["channel_id"])

    if channel:
        weechat.buffer_set(channel.buffer, "unread", "-")
        weechat.buffer_set(channel.buffer, "hotlist", "-1")

        channel.last_read_post_id = channel.last_post_id
        channel.last_viewed_at = int(time.time() * 1000)

def handle_user_added_message(server, data, broadcast):
    if data["user_id"] == server.me.id: # we are geing invited
        connect_server_team_channel(broadcast["channel_id"], server)
    else:
        channel = server.get_channel(broadcast["channel_id"])
        if channel:
            channel.add_user(data["user_id"])

def handle_direct_added_message(server, data, broadcast):
    connect_server_team_channel(broadcast["channel_id"], server)

def handle_group_added_message(server, data, broadcast):
    connect_server_team_channel(broadcast["channel_id"], server)

def handle_new_user_message(server, data, broadcast):
    EVENTROUTER.enqueue_request(
        "run_get_user",
        server, data["user_id"], "new_user_cb", server.id
    )

def handle_user_removed_message(server, data, broadcast):
    if "channel_id" in data: # when we leave
        channel = server.get_channel(data["channel_id"])
        user_id = broadcast["user_id"]
    else: # when someone else leaves
        channel = server.get_channel(broadcast["channel_id"])
        user_id = data["user_id"]

    if user_id == server.me.id: # we are leaving the channel
        channel.unload()
        server.remove_channel(channel.id)
    else:
        channel.remove_user(user_id)

def handle_added_to_team_message(server, data, broadcast):
    # cannot test but probably this event is only triggered on own user
    EVENTROUTER.enqueue_request(
        "run_get_team",
        data["team_id"], server, "connect_server_team_cb", server.id
    )

def handle_leave_team_message(server, data, broadcast):
    # cannot test but probably this event is only triggered on own user
    team = server.teams.pop(data["team_id"])
    team.unload()

def handle_status_change_message(server, data, broadcast):
    # this event seems only to be triggered on own user
    user_id = data["user_id"]

    if user_id not in server.users:
        return

    user = server.users[user_id]
    user.status = data["status"]

    buffer = weechat.current_buffer()
    channel = server.get_channel_from_buffer(buffer)
    if channel and user_id in channel.users:
        channel.update_nicklist_user(user)
        channel.remove_empty_nick_groups()

    user_dm_channel = server.get_direct_messages_channel(user.id)
    if user_dm_channel:
        user_dm_channel.set_status(user.status)

def handle_preferences_changed_message(server, data, broadcast):
    prefs = json.loads(data["preferences"])

    for pref in prefs:
        if pref["category"] in ["direct_channel_show", "group_channel_show"]:
            if pref["value"] == "false":
                if pref["category"] == "direct_channel_show":
                    channel = server.get_direct_messages_channel(pref["name"])
                else:
                    channel = server.get_channel(pref["name"])
                if channel:
                    channel.unload()
                    server.remove_channel(channel.id)
                server.closed_channels[pref["name"]] = channel.id if channel else None
            else:
                if pref["category"] == "direct_channel_show":
                    channel_id = server.closed_channels.get(pref["name"])
                else:
                    channel_id = pref["name"]
                if channel_id:
                    connect_server_team_channel(channel_id, server)
                if pref["name"] in server.closed_channels:
                    del server.closed_channels[pref["name"]]

def receive_ws_callback(server_id, data):
    server = servers[server_id]
    worker = server.worker

    while True:
        try:
            opcode, data = worker.ws.recv_data(control_frame=True)
        except SSLWantReadError:
            return weechat.WEECHAT_RC_OK
        except (WebSocketConnectionClosedException, socket.error) as e:
            return weechat.WEECHAT_RC_OK

        if opcode == ABNF.OPCODE_PONG:
            worker.last_pong_time = time.time()
            server.worker = worker
            return weechat.WEECHAT_RC_OK

        if data:
            message = json.loads(data.decode("utf-8"))
            if "event" in message:
                handler_function_name = "handle_{}_message".format(message["event"])
                if handler_function_name not in globals():
                    return weechat.WEECHAT_RC_OK
                globals()[handler_function_name](server, message["data"], message["broadcast"])

    return weechat.WEECHAT_RC_OK

EVENTROUTER = EventRouter()

buffered_response_cb = EVENTROUTER.buffered_response_cb

config = Config()

servers = {}

default_emojis = []

REQUEST_TIMEOUT_MS = 30 * 1000

mentions = ["@here", "@channel", "@all"]

WEECHAT_SCRIPT_NAME = "wee_most"
WEECHAT_SCRIPT_DESCRIPTION = "Mattermost integration"
WEECHAT_SCRIPT_AUTHOR = "Damien Tardy-Panis <damien.dev@tardypad.me>"
WEECHAT_SCRIPT_VERSION = "0.3.0"
WEECHAT_SCRIPT_LICENSE = "GPL3"

weechat.register(
    WEECHAT_SCRIPT_NAME,
    WEECHAT_SCRIPT_AUTHOR,
    WEECHAT_SCRIPT_VERSION,
    WEECHAT_SCRIPT_LICENSE,
    WEECHAT_SCRIPT_DESCRIPTION,
    "shutdown_cb",
    ""
)

load_default_emojis()
config.setup()
config.read()

if weechat.info_get("auto_connect", "") == '1':
    for server_id in config.get_value("server", "autoconnect"):
        connect_server(server_id)

weechat.hook_command(
    "mattermost",
    "Mattermost commands",
    "||".join(["{} {}".format(c.name, c.args) for c in commands]),
    "\n".join(["{}: {}".format(c.name.rjust(10), c.description) for c in commands]),
    "||".join(["{} {}".format(c.name, c.completion) for c in commands]),
    "mattermost_command_cb",
    ""
)

weechat.hook_completion("irc_channels", "complete channels for Mattermost", "channel_completion_cb", "")
weechat.hook_completion("irc_privates", "complete dms/mpdms for Mattermost", "private_completion_cb", "")
weechat.hook_completion("mattermost_server_commands", "complete server names for Mattermost", "server_completion_cb", "")
weechat.hook_completion("mattermost_slash_commands", "complete Mattermost slash commands", "slash_command_completion_cb", "")
weechat.hook_completion("nicks", "complete @-nicks for Mattermost", "nick_completion_cb", "")
weechat.hook_completion("emojis", "complete :emojis: for Mattermost", "emoji_completion_cb", "")
weechat.hook_completion("mentions", "complete @-mentions for Mattermost", "mention_completion_cb", "")

weechat.hook_modifier("input_text_for_buffer", "handle_multiline_message_cb", "")
weechat.hook_signal("buffer_switch", "buffer_switch_cb", "")
weechat.hook_timer(int(0.2 * 1000), 0, 0, "handle_queued_request_cb", "")
weechat.hook_timer(60 * 1000, 0, 0, "get_buffer_user_status_cb", "")
weechat.hook_timer(60 * 1000, 0, 0, "get_direct_message_channels_user_status_cb", "")
weechat.hook_config("irc.look.server_buffer", "config_server_buffer_cb", "")

weechat.hook_hsignal("mattermost_cursor_insert_post_id", "chat_line_event_cb", "insert_post_id")
weechat.hook_hsignal("mattermost_cursor_delete", "chat_line_event_cb", "delete")
weechat.hook_hsignal("mattermost_cursor_reply", "chat_line_event_cb", "reply")
weechat.hook_hsignal("mattermost_cursor_react", "chat_line_event_cb", "react")
weechat.hook_hsignal("mattermost_cursor_unreact", "chat_line_event_cb", "unreact")
weechat.hook_hsignal("mattermost_cursor_file_download", "chat_line_event_cb", "file_download")
weechat.hook_hsignal("mattermost_cursor_file_open", "chat_line_event_cb", "file_open")
weechat.hook_hsignal("mattermost_cursor_post_open", "chat_line_event_cb", "post_open")

weechat.key_bind("cursor", {
    "@chat(python.wee_most.*):d": "hsignal:mattermost_cursor_delete",
    "@chat(python.wee_most.*):t": "hsignal:mattermost_cursor_reply",
    "@chat(python.wee_most.*):r": "hsignal:mattermost_cursor_react",
    "@chat(python.wee_most.*):u": "hsignal:mattermost_cursor_unreact",
    "@chat(python.wee_most.*):F": "hsignal:mattermost_cursor_file_download",
    "@chat(python.wee_most.*):f": "hsignal:mattermost_cursor_file_open",
    "@chat(python.wee_most.*):o": "hsignal:mattermost_cursor_post_open",
})

def shutdown_cb():
    for server_id in servers.copy():
        disconnect_server(server_id)

    try:
        shutil.rmtree(File.dir_path_tmp)
    except:
        weechat.prnt("", weechat.prefix("error") + "Failed to remove temporary directory for files")

    return weechat.WEECHAT_RC_OK
