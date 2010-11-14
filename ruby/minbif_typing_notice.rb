# This script is inspired by "im_typing_notice" for irssi.
# It creates a new bar item displaying when contacts are typing on supported protocol in minbif
# It sends a notice to your contacts when you're typing a message.
#
# Author: CissWit cisswit at 6-8 dot fr
# Version 1.0.1
#
# Changelog :
#
# * 1.0.1
#   Ignore the user "request" (no need to tell it we are typing)
#
# * 1.0
#   Original version
#
# Licence GPL3

$h_typing = Hash.new
$h_sending = Hash.new

def weechat_init
    Weechat.register(
      "minbif_typing_notice",
      "CissWit",
      "1.0.1",
      "GPL3",
      "For minbif - displays when someone is typing a message to you, and notice them when you do.",
      "",
      ""
    )
    Weechat.bar_item_new("typing_notice", "draw_typing", "")
    Weechat.hook_modifier("irc_in_privmsg", "modifier_ctcp", "")
    Weechat.hook_signal("input_text_changed", "input_changed", "")
    if Weechat.config_is_set_plugin("minbif_server") == 0
        Weechat.config_set_plugin("minbif_server", "minbif")
    end
    Weechat.print("", "typing_notice: minbif typing notice")
    Weechat.print("", "typing_notice: Put [typing_notice] in your status bar (or the one you prefer) to show when contacts are typing message to you.")
    return Weechat::WEECHAT_RC_OK
end

def input_changed(data,signal,type_data)
    buffer = Weechat.current_buffer
    buffer_name = Weechat.buffer_get_string buffer, "name"

    if buffer_name =~ /^#{Weechat.config_get_plugin("minbif_server")}\.(.*)/
        nick = $1
	if nick == "request"
	    return Weechat::WEECHAT_RC_OK
	end

        buffer_text = Weechat.buffer_get_string(buffer,"input")
        if(buffer_text == "" or buffer_text =~ /^\//)
            if $h_sending.key?(buffer)
                Weechat.command(buffer,"/mute all ctcp #{nick} TYPING 0")
                Weechat.unhook($h_sending[buffer]["timer"])
                $h_sending.delete(buffer)
            end
            return Weechat::WEECHAT_RC_OK
        end
            
        return Weechat::WEECHAT_RC_OK unless !$h_sending.key?(buffer)
        Weechat.command(buffer,"/mute -all ctcp #{nick} TYPING 1")
        if $h_sending.key?(buffer)
            Weechat.unhook($h_sending[buffer]["timer"])
        else
            $h_sending[buffer] = Hash.new
        end
        $h_sending[buffer]["timer"] = Weechat.hook_timer(7000,0,1,"sending_timeout",buffer)
        $h_sending[buffer]["time"] = Time.new
    end
    return Weechat::WEECHAT_RC_OK
end

def sending_timeout(buffer,n)
    if $h_sending.key?(buffer)
        buffer_name = Weechat.buffer_get_string buffer, "name"
        if buffer_name =~ /^#{Weechat.config_get_plugin("minbif_server")}\.(.*)/
            Weechat.command(buffer,"/mute -all ctcp #{$1} TYPING 0")
            Weechat.unhook($h_sending[buffer]["timer"])
            $h_sending.delete(buffer)
        end
    end
    return Weechat::WEECHAT_RC_OK
end

def draw_typing(osefa,osefb,osefc)
    buffer = Weechat.current_buffer
    if $h_typing.key?(buffer)
        return "TYPING"
    end
    return ""
end

def typing_timeout(buffer,n)
    if $h_typing.key?(buffer)
        Weechat.unhook($h_typing[buffer])
        $h_typing.delete(buffer)
    end
    Weechat.bar_item_update("typing_notice")
end

def modifier_ctcp(data, modifier, modifier_data, string)
    if string =~ /:([^!]*)!([^\s]*)\sPRIVMSG\s([^\s]*)\s:\01TYPING\s([0-9])\01/
        buffer = Weechat.buffer_search("irc", modifier_data + "." + $1)
        if $h_typing.key?(buffer)
            Weechat.unhook($h_typing[buffer])
        end
        if $4 == "1"
            $h_typing[buffer] = Weechat.hook_timer(7000,0,1,"typing_timeout",buffer)
        elsif $4 == "0"
            if $h_typing.key?(buffer)
                $h_typing.delete(buffer)
            end
        elsif $4 == "2"
            Weechat.print("","- #{$4} - #{$1} - #{buffer} - is typing")
        end
        Weechat.bar_item_update("typing_notice")
        return ""
    end
    return string
end
