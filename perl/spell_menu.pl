use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;

# spell_menu.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

# to read the following docs, you can use "perldoc spell_menu.pl"

=head1 NAME

spell_menu - popup menu for the weechat spell checker (weechat edition)

=head1 USAGE

type the tab key on a misspelt word to bring up the correction
pop-up. make sure you have set

  aspell.check.enabled on
  aspell.check.suggestions >-1

and a dictionary set, e.g in

  aspell.check.default_dict

you also need to have a menu script, if you don't have it yet:

  /script install menu.pl

hint: if it breaks your tab completion, you can toggle the spell
checker (default key in weechat is Alt+S)

=cut

use constant SCRIPT_NAME => 'spell_menu';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.2', 'GPL3', 'spell checker menu', '', '') || return;

weechat::hook_command_run('/input complete_next', 'spell_menu', '');
weechat::hook_command(SCRIPT_NAME, 'open the spell menu', '', '', '', 'spell_menu', '');

sub spell_menu {
	Encode::_utf8_on(my $sugs = weechat::buffer_get_string($_[1], 'localvar_aspell_suggest'));
	return weechat::WEECHAT_RC_OK unless $sugs;
	my $fix = $_[2] =~ /^fix (\d+)/ ? $1 : undef;
	my $badword;
	($badword, $sugs) = split ':', $sugs, 2;
	weechat::command('', '/mute /unset menu.var.spell.*');
	Encode::_utf8_on(my $q = weechat::buffer_get_string($_[1], 'input'));
	my $pos = weechat::buffer_get_integer($_[1], 'input_pos');
	my $rpos = index $q, $badword;
	if ($fix) {
		for (my $f = $rpos; $f >= 0 && $f < $pos; $f = index $q, $badword, $f+1) {
			$rpos = $f;
		}
		my $goodword = (split '[,/]', $sugs)[$fix-1];
		(substr $q, $rpos, length $badword) = $goodword;
		weechat::buffer_set($_[1], 'input', $q);
		weechat::buffer_set($_[1], 'input_pos', $rpos + length $goodword);
	}
	else {
		return weechat::WEECHAT_RC_OK unless weechat::config_boolean(weechat::config_get('aspell.check.enabled'));
		return weechat::WEECHAT_RC_OK unless $pos >= $rpos;
		my ($i, $j) = (0, 0);
		my %seen;
		my @shortcut = (undef, 1..9, 0, 'a'..'z');
		for my $sug (split '[,/]', $sugs) {
			++$i;
			next if $seen{$sug}++;
			$j = sprintf '%02d', $j + 1;
			last if $j >= @shortcut;
			weechat::command('', "/mute /set menu.var.spell.$j.command /@{[SCRIPT_NAME]} fix $i");
			weechat::command('', "/mute /set menu.var.spell.$j.name &$shortcut[$j] $sug");
		}
		weechat::command('', '/mute /set menu.var.spell.9.command /aspell addword $0');
		weechat::command('', "/mute /set menu.var.spell.9.name ADD $badword");
		weechat::command($_[1], "/menu spell $badword");
	}
	$_[2] =~ /^\// ? weechat::WEECHAT_RC_OK_EAT : weechat::WEECHAT_RC_OK
}
