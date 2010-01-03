# This is a rewrite of the script "Kernel" for WeeChat.
# This script is for WeeChat 0.3.0
# Written by Julien Louis <ptitlouis@sysif.net>
# Port to WeeChat 0.3.0: Sid Vicious (aka Trashlord) <dornenreich666@gmail.com>
# This script is public domain

use warnings;
use strict;
use IO::Socket;

weechat::register("kernel", "ptitlouis", "0.3", "Public domain", "Display latest stable kernel from kernel.org", "", "");
weechat::hook_command("kernel", "Display latest stable kernel from kernel.org", "", "", "", "kernel", "");

sub get_kernel {
	my $buffer = weechat::current_buffer;
	my $sock = IO::Socket::INET->new(PeerAddr => 'finger.kernel.org', PeerPort => 79, Proto => 'tcp');
	return weechat::WEECHAT_RC_ERROR unless $sock;
	$sock->autoflush(1);
	chomp(my @versions = <$sock>);
	my $stable = "";
	for(@versions) {
		#Kernel 0 is latest stable, 1 is latest prepatch, 2 is latest snapshot with git
		if ($_ =~ /^The latest stable.+:\s+(.+)/) { $stable = $1; last; }
	}
	close $sock;
        return $stable;
}
sub kernel { 
	my ($buffer, $kernel) = ($_[1], &get_kernel);
	weechat::print($buffer, "The latest stable Linux kernel is $kernel");
        return weechat::WEECHAT_RC_OK;
}
