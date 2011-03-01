# kernel.pl: display the latest stable Linux kernel from kernel.org
#
# Written by Julien Louis <ptitlouis@sysif.net>
# Port to WeeChat 0.3.x: Trashlord <dornenreich666@gmail.com>
# This script is public domain
#
# Recent history:
# v0.4: rewritten to use hook_process()

# To use this script, simply type /kernel without parameters in any buffer.

use warnings;
use strict;

my $script_name = "kernel";
my $author = "ptitlouis";
my $version = "0.4";
my $license = "Public domain";
my $description = "Display the latest stable Linux kernel from kernel.org";

weechat::register($script_name, $author, $version, $license, $description, "", "");
weechat::hook_command("kernel", "Display latest stable kernel from kernel.org", "", "", "", "kernel", "");

sub kernel { 
	# No parameters are taken here. Timeout for hook process is 10 seconds.
	my $hook = weechat::hook_process(kernel_hook_process(), 10000, "kernel_hook_callback", "");
	return weechat::WEECHAT_RC_OK;	
}

sub kernel_hook_process {
	# Use IO::Socket to get a list of kernel versions from finger.kernel.org.
	# Yes, Net::Finger exists, but it doesn't work with hook_process.
	qq(perl -e 'use IO::Socket; my \$sock = IO::Socket::INET->new(PeerAddr => "finger.kernel.org", PeerPort => 79, Proto => "tcp"); print <\$sock>; close \$sock;');
}

sub kernel_hook_callback {
	# Kernel process callback.
	my ($buffer, $command, $return_code, $out, $error) = @_;
	$buffer = weechat::current_buffer; # Where to print
	if ($return_code == weechat::WEECHAT_RC_ERROR) { weechat::print($buffer, "Error with kernel.pl script"); }
	if (!$out) { 
		weechat::print($buffer, "Could not retrieve kernel list from finger.kernel.org"); 
		return weechat::WEECHAT_RC_OK;
	}
	foreach my $kernel (split(/\n/, $out)) {
		# Do a foreach loop on the list of kernels contained in $out
		# until the first "The latest stable [...]" is encountered. That's the latest stable version available
		if ($kernel =~ /^The latest stable.*:\s*(.+)$/i) {
		    my $latest_version = $1;	
			weechat::print($buffer, "The latest stable Linux kernel is $latest_version");
			last;
		}
	}
	return weechat::WEECHAT_RC_OK;
}
