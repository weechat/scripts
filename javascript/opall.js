name = "opall";
author = "gagz@riseup.net";
version = "0.2";
license = "wtfpl";
description = "op people using chanserv instead of /mode";
shutdown_function = "";
charset = "";

weechat.register(name, author, version, license, description, shutdown_function, charset);

weechat.hook_command("opall", "OP everybody on the channel, using chanserv instead of /mode", "", "", "", "chanserv_op_all", "");

function chanserv_op_all() {
        var buffer = weechat.current_buffer()
        var chan = weechat.buffer_get_string(buffer, "localvar_channel")

        // we must be sure to be on an IRC buffer
        if( weechat.buffer_get_string(buffer, "plugin") != "irc" ) {
                weechat.print("", "Works only on IRC channels")
                return weechat.WEECHAT_RC_ERROR
        }

        // lets get the nicklist of the current buffer
        var nicklist = weechat.infolist_get("nicklist", buffer, "");
        // and walk through it
        while( weechat.infolist_next(nicklist) ) {
                var type = weechat.infolist_string(nicklist, "type");
                var visible = weechat.infolist_integer(nicklist, "visible");
                var prefix = weechat.infolist_string(nicklist, "prefix");

                // we are only interested in actual non-op visible nicks
		// TODO: find a more reliable way to op non-op users (ie. prefix
		// can be changed in the settings and might not be "@")
		// TODO: check the IRC server/services version to talk with
		// chanserv correctly. This works with charybdis/atheme.
                if( type == "nick" && visible == 1 && prefix != "@") {
                        var nick = weechat.infolist_string(nicklist, "name");
                        var command = "/msg chanserv op " + chan + " " + nick;
                        weechat.print("", command);
                        weechat.command(buffer, command);
                }
        }
        weechat.infolist_free(nicklist);
        return weechat.WEECHAT_RC_OK;
}
