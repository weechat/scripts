# Written by Sid Vicious (Trashlord) <dornenreich666@gmail.com>
# Released under GPL3

use warnings;
use strict;
use diagnostics;

weechat::register("Cmus", "Sid", "0.1", "GPL3", "Cmus status display", "", "");
weechat::hook_command("cmus", "", "", "", "", "cmd_cmus", "");

sub cmd_cmus {
	#We'll fix the god damn vim syntax highlighting problem later
	open CMUS, '<', '/tmp/cmus-status' or return weechat::WEECHAT_RC_ERROR;
	my $line = <CMUS>;
	close CMUS;
	my $buffer = weechat::current_buffer;
	if ($line && $buffer) { 
		weechat::command($buffer, "$line");
		return weechat::WEECHAT_RC_OK;
	}
	else { return weechat::WEECHAT_RC_ERROR; }
}
