use strict;
use warnings;

# cmdind.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

=head1 NAME

cmdind - Indicator for input line if you are inputting a command or text

=head1 DESCRIPTION

cmdind will put a big fat banner onto the input line, telling you
whether you are inputting WeeChat commands or text that is sent to the
buffer. This is for stupid people like me ;-) that accidentally send
commands to channel.

=head1 USAGE

just load the script and it is ready. Appearance can be configured
through a number of settings.

=head1 SETTINGS

You must type

  /set plugins.var.perl.cmdind.SETTINGNAME VALUE

to change a setting C<SETTINGNAME> to a new value C<VALUE>.

  /unset plugins.var.perl.cmdind.SETTINGNAME

will reset a setting to its default value.

the following settings are available:

=head2 command_item

the indicator shown when inputting a command (starting with /)

=head2 esc_text_item

the indicator shown when inputting text for the buffer, which is an
escaped command (starting with //)

=head2 text_item

the indicator that should be shown when inputting text for the buffer

=head2 right

this is a boolean value whether to tack the indicator to the left or
right of the input text

=cut

use constant SCRIPT_NAME => 'cmdind';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.1', 'GPL3', 'make /commands more visible', '', '') || return;
weechat::hook_modifier('500|input_text_display_with_cursor' => 'cmdind', '');
my $weechat_string_remove_color = qr{(?^:(?^:(?^:\x19)(?:(?^:[FB](?^:(?^:\@(?^:[*!/_|]*)(?:.{5})?)|(?^:(?^:[*!/_|]*)(?^:(?:.{2})?))))|(?^:\*(?^:(?^:\@(?^:[*!/_|]*)(?:.{5})?)|(?^:(?^:[*!/_|]*)(?^:(?:.{2})?)))(?:,(?^:(?^:\@(?:.{5})?)|(?^:(?:.{2})?)))?)|(?^:\@(?:.{5})?)|(?^:[E])|(?^:b[FBD_#il-]?)|(?^:\x1c)|(?^:(?:.{2})?))?)|(?^:(?:\x1a|\x1b).?)|(?^:\x1c))};
sub _get_setting_eval {
    weechat::string_eval_expression(
	weechat::config_is_set_plugin($_[0]) ?
		weechat::config_get_plugin($_[0]) :
			$_[1], {}, {}, {}) }
sub _get_setting_bool {
    0 + (weechat::config_is_set_plugin('right') &&
	    weechat::config_string_to_boolean(weechat::config_get_plugin('right'))) }
sub cmdind {
    my ($cmd, $text, $esc_text, $right);
    my @il = $1 if $_[3] =~ s/\A( )\r//;
    join "\r", @il, map {
	my $str = $_ =~ s/\x19b#//r;
	my $tmpl;
	my $input_str = weechat::string_input_for_buffer($str);
	unless (length $str) { $tmpl = '' }
	elsif (!length $input_str) {
	    $tmpl = $cmd //= _get_setting_eval('command_item', '${color:*red}[COMMAND]${color:-bold} ');
	}
	elsif ($str ne $input_str) {
	    $tmpl = $esc_text //= _get_setting_eval('esc_text_item', '${color:*brown}[INPUT]${color:reset} ');
	}
	else {
	    $tmpl = $text //= _get_setting_eval('text_item', '${color:*green}[INPUT]${color:reset} ');
	}
	if ($right //= _get_setting_bool('right')) {
	    my $right_color = join '', $tmpl =~ /($weechat_string_remove_color)/g;
	    $tmpl =~ s/(\s*)$//; $right_color . $_ . $1 . $tmpl
	}
	else {
	    $tmpl . $_
	}
    } split "\r", $_[3], -1;
}
