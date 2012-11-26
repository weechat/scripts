import weechat as w

SCRIPT_NAME    = "noirccolors"
SCRIPT_AUTHOR  = "Fredrick Brennan <fredrick.brennan1@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "Public domain"
SCRIPT_DESC    = "Remove IRC colors from buffers with the localvar 'noirccolors' set. To disable IRC colors in the current buffer, type /buffer set localvar_noirccolors true. You can also set this with autosetbuffer. :)"

w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')


def my_modifier_cb(data, modifier, modifier_data, string):
    if w.buffer_get_string(w.buffer_search('irc',modifier_data.split(";")[1]),"localvar_noirccolors") == "true":
        try:
            nick, message = string.split("\t")
        except ValueError, e:
            return string
        return "%s\t%s" % (nick, w.string_remove_color(message,""))
    else:
        return string

hook = w.hook_modifier("weechat_print", "my_modifier_cb", "")
