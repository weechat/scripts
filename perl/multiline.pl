use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;
use utf8;

# multiline.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

use constant SCRIPT_NAME => 'multiline';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.1', 'GPL3', 'Multi-line edit box', 'stop_multiline', '') || return;

weechat::hook_modifier('input_text_display_with_cursor', 'multiline_display', '');
init_multiline();
our $COMPLETE_HOOK;
hook_complete();

sub multiline_display {
	Encode::_utf8_on($_[3]);
	Encode::_utf8_on(my $nl = weechat::config_get_plugin('char') || ' ');
	Encode::_utf8_on(my $tab = weechat::config_get_plugin('tab'));
	$_[3] =~ s/\x0a/$nl\x0d/g;
	$_[3] =~ s/\x09/$tab/g if $tab;
	$_[3]
}

sub multiline_complete_fix {
	weechat::unhook($COMPLETE_HOOK);
	Encode::_utf8_on(my $input = weechat::buffer_get_string($_[1], 'input'));
	my $pos = weechat::buffer_get_integer($_[1], 'input_pos');
	my @lines = split /\x0a/, (substr $input, 0, $pos), -1;
	my $after = substr $input, $pos;
	weechat::buffer_set($_[1], 'input', $lines[-1]);
	weechat::buffer_set($_[1], 'input_pos', length $lines[-1]);
	weechat::command($_[1], $_[2]);
	Encode::_utf8_on($lines[-1] = weechat::buffer_get_string($_[1], 'input'));
	my $before = join "\x0a", @lines;
	weechat::buffer_set($_[1], 'input', $before.$after);
	weechat::buffer_set($_[1], 'input_pos', length $before);
	hook_complete();
	weechat::WEECHAT_RC_OK_EAT
}

sub hook_complete {
	$COMPLETE_HOOK = weechat::hook_command_run('/input complete*', 'multiline_complete_fix', '');
	weechat::WEECHAT_RC_OK
}

sub init_multiline {
	weechat::command('', '/key bind ctrl-M /input insert \x0a');
	unless (weechat::config_is_set_plugin('ipl') && weechat::config_string_to_boolean(weechat::config_get_plugin('ipl'))) {
		my $bar = weechat::bar_search('input');
		if ($bar) {
			weechat::bar_set($bar, $_, '0') for 'size', 'size_max';
		}
		weechat::config_set_plugin('char', '↩');
		weechat::config_set_plugin('tab', '──▶▏');
		weechat::command('', '/mute /key bind ctrl-M /input insert \x0a');
		weechat::config_set_plugin('ipl', '1');
	}
	weechat::WEECHAT_RC_OK
}

sub stop_multiline {
	weechat::command('', '/key reset ctrl-M');
	weechat::WEECHAT_RC_OK
}
