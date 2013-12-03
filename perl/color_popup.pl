use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;
use utf8;

# to read the following docs, you can use "perldoc color_popup.pl"

=head1 NAME

color_popup - show mirc colors when needed

=head1 SYNOPSIS

the color numbers will be shown when a color control code is
present.

=cut

use constant SCRIPT_NAME => 'color_popup';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.3', 'GPL3', 'show mirc color codes', '', '') || return;

my %ones = map { $_ => 1 } 0, 8, 14, 15;
my $popup =
	(join '',
	 map {
		 "\03" . ($ones{0+$_} // 0) . ',' . (sprintf "%02d", $_)x2
	 } 0..15
	) . "\03"
	;

weechat::hook_modifier('input_text_display_with_cursor', 'color_popup', '');

## color_popup -- show mirc colors
## () - modifier handler
## $_[2] - buffer pointer
## $_[3] - input string
## returns modified input string
sub color_popup {
	Encode::_utf8_on($_[3]);
	my $cc = qr/(?:\03(?:\d{1,2}(?:,(?:\d{1,2})?)?)?|\02|\x1d|\x0f|\x12|\x15|\x16|\x1f)/;
	my ($p1, $x, $p2) = split /((?:$cc)?\x19b#)/, $_[3], 2;
	for ($p1, $p2) {
		s/($cc)/$1■/g if weechat::config_string_to_boolean(weechat::config_get_plugin('reveal'));
		Encode::_utf8_on($_ = weechat::hook_modifier_exec(irc_color_decode => 1, weechat::hook_modifier_exec(irc_color_encode => 1, $_)));
	}
	$x .= ' ' . weechat::hook_modifier_exec(
		irc_color_decode => 1, $popup
	   ) if $x =~ /^\03/ and weechat::current_buffer() eq $_[2];
	"$p1$x$p2"
}
