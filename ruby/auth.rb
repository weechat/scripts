# Copyright (c) 2013 Shawn Smith <ShawnSmith0828@gmail.com>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.


def weechat_init
	# Register our plugin with WeeChat
	Weechat.register("auth",
		"Shawn Smith",
		"0.3",
		"GPL3",
		"Automatically authenticate with NickServ using your sasl_username and sasl_password.",
		"",
		"")

	Weechat.hook_command("auth",
		"Automatically authenticate with NickServ using your sasl_username and sasl_password.",
		"list [server]",
		"list: Displays your sasl_username and sasl_password",
		"",
		"auth_command_cb",
		"")

	# Grab the hook for notices.
	Weechat.hook_signal("*,irc_in_notice", "auth_notice_cb", "")

	return Weechat::WEECHAT_RC_OK
end

# The auth command
def auth_command_cb(data, buffer, args)
	server = buffer.split(',')[0]
	arg = args.split(' ')

	# Check to make sure we were given a valid option.
	if arg[0] == "list" && arg[1]
		server = arg[1]

		# Grab the pointers from the config
		sasl_username = Weechat.config_get("irc.server.#{server}.sasl_username")
		sasl_password = Weechat.config_get("irc.server.#{server}.sasl_password")

		# Print the usernames/passwords
		Weechat.print("", "[Auth]: sasl_username: #{Weechat.string_eval_expression("#{wee_string(sasl_username)}", {}, {}, {})}")
		Weechat.print("", "[Auth]: sasl_password: #{Weechat.string_eval_expression("#{wee_string(sasl_password)}", {}, {}, {})}")
	else
		Weechat.command("", "/help auth")
	end

	return Weechat::WEECHAT_RC_OK
end

# The incoming notice.
def auth_notice_cb(data, buffer, args)
	# Notice should come from nickserv, otherwise we ignore it.
	if /^:NickServ!.+:This nickname is registered/i =~ args
		# Get the server that we're on.
		server = buffer.split(',')[0]

		# Grab the username/passwords if we have them.
		sasl_username = Weechat.config_get("irc.server.#{server}.sasl_username")
		sasl_password = Weechat.config_get("irc.server.#{server}.sasl_password")

		# Prevents us from sending empty passwords.
		if sasl_password != nil
			Weechat.command("", "/quote -server #{server} PRIVMSG NickServ IDENTIFY #{Weechat.string_eval_expression("#{wee_string(sasl_username)}", {}, {}, {})} #{Weechat.string_eval_expression("#{wee_string(sasl_password)}", {}, {}, {})}")

			# Backwards compatibility hack for shitty servers that don't let you use [nick pass]
			Weechat.command("", "/quote -server #{server} PRIVMSG NickServ IDENTIFY #{Weechat.string_eval_expression("#{wee_string(sasl_password)}", {}, {}, {})}")
                end
	end

	return Weechat::WEECHAT_RC_OK
end

def wee_string(input)
	return Weechat.config_string(input)
end
