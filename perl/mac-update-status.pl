# mac-update-status.pl -- Update status messages in various Mac IM programs
# Copyright (c) 2007 Zak B. Elep <zakame@spunge.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

use strict;

use Mac::Glue;

my $version = '0.2';
weechat::register 'mac-update-status', $version, '',
	'Update status messages in various Mac IM programs';
weechat::add_modifier 'irc_user', 'privmsg', 'update';

my %messengers = (
	Adium => 'my_status_message',
	iChat => 'status_message',
	Skype => undef,
);

my %updater;
for my $im (keys %messengers){
	$updater{$im} = sub
	{
		my $glue = new Mac::Glue $im;
		my $prop = prop $glue $messengers{$im};
		set $glue $prop, to => +shift;
	};
}
$updater{Skype} = sub
{
	my $skype = new Mac::Glue 'Skype';
	$skype->send(
		command => "SET PROFILE MOOD_TEXT $_[0]",
		script_name => 'WeeChat (mac-update-status)',
	);
};

sub update
{
	my $message = $_[1];
	(my $status = $message) =~ s#^/me\s+##;
	return $message if $status eq $message;

	my $sysevent = new Mac::Glue 'System Events';
	my $prop = prop $sysevent qw(name of processes);
	my %seen = map { $_ => 1 } get $sysevent $prop;
	for my $im (keys %messengers){
		$updater{$im}->($status) if $seen{$im};
	}
	return $message;
}

__END__

=head1 NAME

mac-update-status.pl -- Update status messages in various Mac IM programs

=head1 SYNOPSIS

	# First, make sure you have Mac::Glue and the glues to the IMs
	$ cpan Mac::Glue
	$ gluemac /Applications/Adium.app
	$ gluemac /Applications/iChat.app
	$ gluemac /Applications/Skype.app

	# Then in WeeChat load mac-update-status.pl
	/perl load /path/to/mac-update-status.pl

	# Or put script in .weechat/perl/autoload

=head1 DESCRIPTION

mac-update-status is a script plugin for WeeChat that enables CTCP ACTION
messages (aka C</me> actions) to be sent as status line updates to other
Instant Messenger programs running on a Mac.

Currently, this script supports updating to Adium, iChat, and Skype,
through the use of the L<Mac::Glue> module to interact with AppleScript
events.

=head1 SEE ALSO

C<weeter.pl>, L<Mac::Glue>, L<http://weechat.flashtux.org>

=head1 AUTHORS

Zak B. Elep, C<< zakame at spunge.org >>

=cut
