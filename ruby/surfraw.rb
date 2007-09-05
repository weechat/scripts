#   WeeChat Surfraw v0.1 - An interface to surfraw in WeeChat
#   Copyright (C) 2007  Simon Ernst <se (at) netmute (dot) org>

#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

def weechat_init
	Weechat.register("surfraw", "0.1", "", "An interface to surfraw in WeeChat.")
	
	$elvi = `surfraw -elvi | sed "s/--.*//"`.split
	elvi_completion = $elvi.join("|")
	Weechat.add_command_handler("surfraw", "surfraw", "", "", "", "#{elvi_completion} %-")
	Weechat.add_command_handler("sr", "surfraw", "", "", "", "#{elvi_completion} %-")
	
	return Weechat::PLUGIN_RC_OK
end

def surfraw(server, args)
	if args.empty?
		Weechat.print("Usage: /surfraw [elvi] [search string]")
	else
		if $elvi.include?(args.split(" ", 2)[0])
			surfraw_response = `surfraw -p #{args}`
			if surfraw_response.split.size != 1
				Weechat.print("Error: Invalid surfraw response")
			else
				Weechat.command("/msg * #{surfraw_response}")
			end
		else
			Weechat.print("Unknown elvi: " + args.split(" ", 2)[0])
			Weechat.print("Available elvis are: " + $elvi.join(", "))
		end
	end
	return Weechat::PLUGIN_RC_OK
end
