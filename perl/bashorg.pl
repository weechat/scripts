# BashOrg: Retrieve quotes from bash.org
# Written by Trashlord <dornenreich666@gmail.com>
# This script is in the public domain

# Commands:
# /bash [-o] [quote number]
# If quote number is specified, will retrieve said quote. If no parameter is specified, will retrieve a random quote

# History:
# 17/12/10, Trashlord:
# version 0.1: script creation
# 03/01/11, Trashlord:
# version 0.2: removed the (obsolete) timers and some code cleanup

use strict;
use warnings;

my $script_name = "bashorg";
my $author = "Trashlord";
my $version = "0.2";
my $license = "Public domain";
my $description = "BashOrg: Retrieve quotes from bash.org";

# Register.
weechat::register($script_name, $author, $version, $license, $description, "", "");
# Is WWW::BashOrg installed? Lets find out!
eval { use WWW::BashOrg; }; 
# If not installed, weechat will print out a perl-error, saying it cannot find the module
# and loading the script will fail.

# Hook command
my $args_help = "If number is specified, will retrieve said quote. If no parameter is specified, will retrieve random quote\nIf -o is specified, will send the quote as a message to the current buffer.";
my $command_desc = "Retrieve quotes from bash.org";
my $number; # Quote number
my $bold = chr(2);
my $buffer = ""; # Buffer to output

weechat::hook_command("bash", $command_desc, "[-o] [quote number]", $args_help, "", "bashorg_callback", "");

sub bashorg_callback {
	my (undef, $buffer, $args) = @_;
	my $output_to_channel = 0;
	$number = "random";
	if ($args =~ /^-o/i) { $output_to_channel = 1; }
	if ($args =~ /(\d+)$/) { $number = $1; }
	# Hook the process
	my $hook = weechat::hook_process(
		bashorg_get_quote(),
		10000,
	   	"bashorg_process_callback",
	   	$output_to_channel
	);
	return weechat::WEECHAT_RC_OK;
}

sub bashorg_get_quote {
	if ($number eq "random") {
		qq(perl -e 'use WWW::BashOrg; print WWW::BashOrg->new->random;');
	}
	else { 
		qq(perl -e 'use WWW::BashOrg; print WWW::BashOrg->new->get_quote(\'$number\');');
	}
}

sub bashorg_process_callback {
	my ($output, $command, $returncode, $out, $err) = @_;
	$buffer = weechat::current_buffer;
	if ($returncode == weechat::WEECHAT_HOOK_PROCESS_ERROR) {
		weechat::print($buffer, "Error retrieving quote from bash.org");
	}
	if ($out) {
		# I assume will require splitting by \n
		my $message_to_channel;
		if ($number eq "random") { $message_to_channel = "random bash.org quote:"; }
		else { $message_to_channel = "bash.org quote $number:"; }
		# Print the stuff
		weechat_print_lines($output, $bold.$message_to_channel);
		weechat_print_lines($output, $_) for(split(/\n/, $out));
		weechat_print_lines($output, $bold."--");
	}
	else { weechat::print($buffer, "Sorry, no such quote"); }
	return weechat::WEECHAT_RC_OK;
}

sub weechat_print_lines {
	# Determine if we're messaging to the channel or printing locally
	my ($output, $line) = @_;
	if ($output) { weechat::command($buffer, $line); }
	else { weechat::print($buffer, $line); }
}

