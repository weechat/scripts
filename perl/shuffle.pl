# This is a text shuffler
# This script is public domain
# Author: Sid Vicious (Trashlord) <dornenreich666@gmail.com>

use warnings;
use strict;

weechat::register("shuffle", "Trashlord", "0.1", "Public domain", "Simple text shuffler", "", "");
weechat::hook_command("shuffle", "<msg>", "<msg> - message to shuffle", "", "", "cmd_shuffle", "");

#Text shuffler
sub cmd_shuffle {
	my ($data, $buffer, $text) = (shift, shift, shift);
	my $final;
	for(split(" ", $text)) { #We're splitted here, so we can keep the spaces in order, and words in order. we just shuffle letters
		my $len = length $_;
		my $out;
		while ($len > 0) {
			my $rand = int(rand($len)); 
			my $letter = substr($_, $rand, 1); 
			$len--;
			substr($_, $rand, 1, "");
	        	$out .= $letter;
		}
        	$final .= $out." ";
	}
	weechat::command($buffer, $final);
}
