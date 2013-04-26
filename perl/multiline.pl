use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;
use utf8;

# multiline.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

# to read the following docs, you can use "perldoc multiline.pl"

=head1 NAME

multiline - Multi-line edit box for WeeChat (weechat edition)

=head1 DESCRIPTION

multiline will draw a multi-line edit box to your WeeChat window so
that when you hit the return key, you can first compose a complete
multi-line message before sending it all at once.

Furthermore, if you have multi-line pastes then you can edit them
before sending out all the lines.

=head1 USAGE

make a key binding to send the finished message:

    /key bind meta-s /input return

then you can send the multi-line message with Alt+S

=head1 SETTINGS

the settings are usually found in the

  plugins.var.perl.multiline

namespace, that is, type

  /set plugins.var.perl.multiline.*

to see them and

  /set plugins.var.perl.multiline.SETTINGNAME VALUE

to change a setting C<SETTINGNAME> to a new value C<VALUE>. Finally,

  /unset plugins.var.perl.multiline.SETTINGNAME

will reset a setting to its default value.

the following settings are available:

=head2 char

character(s) which should be displayed to indicate end of line

=head2 tab

character(s) which should be displayed instead of Tab key character

=head2 lead_linebreak

if turned on, multi-line messages always start on a new line

=head2 modify_keys

if turned on, cursor keys are modified so that they respect line
boundaries instead of treating the whole multi-line message as a
single line

=head2 magic

indicator displayed when message will be sent soon

=head2 magic_enter_time

delay after pressing enter before sending automatically (in ms), or 0
to disable

=head2 magic_paste_only

only use multi-line messages for multi-line pastes (multi-line on
enter is disabled by this)

=head2 paste_lock

time-out to detect pastes (disable the weechat built-in paste
detection if you want to use this)

=head2 send_empty

set to on to automatically disregard enter key on empty line

=head2 hide_magic_nl

whether the new line inserted by magic enter key will be hidden

=head2 weechat_paste_fix

disable ctrl-J binding when paste is detected to stop silly weechat
sending out pastes without allowing to edit them

=head2 ipl

this setting controls override of ctrl-M (enter key) by script. Turn
it off if you don't want multiline.pl to set and re-set the key binding.

=head1 FUNCTION DESCRIPTION

for full pod documentation, filter this script with

  perl -pE'
  (s/^## (.*?) -- (.*)/=head2 $1\n\n$2\n\n=over\n/ and $o=1) or
   s/^## (.*?) - (.*)/=item I<$1>\n\n$2\n/ or
  (s/^## (.*)/=back\n\n$1\n\n=cut\n/ and $o=0,1) or
  ($o and $o=0,1 and s/^sub /=back\n\n=cut\n\nsub /)'

=cut

use constant SCRIPT_NAME => 'multiline';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.6', 'GPL3', 'Multi-line edit box', 'stop_multiline', '') || return;
sub SCRIPT_FILE() {
	my $infolistptr = weechat::infolist_get('perl_script', '', SCRIPT_NAME);
	my $filename = weechat::infolist_string($infolistptr, 'filename') if weechat::infolist_next($infolistptr);
	weechat::infolist_free($infolistptr);
	return $filename unless @_;
}

{
package Nlib;
# this is a weechat perl library
use strict; use warnings; no warnings 'redefine';

## i2h -- copy weechat infolist content into perl hash
## $infolist - name of the infolist in weechat
## $ptr - pointer argument (infolist dependend)
## @args - arguments to the infolist (list dependend)
## $fields - string of ref type "fields" if only certain keys are needed (optional)
## returns perl list with perl hashes for each infolist entry
sub i2h {
	my %i2htm = (i => 'integer', s => 'string', p => 'pointer', b => 'buffer', t => 'time');
	local *weechat::infolist_buffer = sub { '(not implemented)' };
	my ($infolist, $ptr, @args) = @_;
	$ptr ||= "";
	my $fields = ref $args[-1] eq 'fields' ? ${ pop @args } : undef;
	my $infptr = weechat::infolist_get($infolist, $ptr, do { local $" = ','; "@args" });
	my @infolist;
	while (weechat::infolist_next($infptr)) {
		my @fields = map {
			my ($t, $v) = split ':', $_, 2;
			bless \$v, $i2htm{$t};
		}
		split ',',
			($fields || weechat::infolist_fields($infptr));
		push @infolist, +{ do {
			my (%list, %local, @local);
			map {
				my $fn = 'weechat::infolist_'.ref $_;
				my $r = do { no strict 'refs'; &$fn($infptr, $$_) };
				if ($$_ =~ /^localvar_name_(\d+)$/) {
					$local[$1] = $r;
					()
				}
				elsif ($$_ =~ /^(localvar)_value_(\d+)$/) {
					$local{$local[$2]} = $r;
					$1 => \%local
				}
				elsif ($$_ =~ /(.*?)((?:_\d+)+)$/) {
					my ($key, $idx) = ($1, $2);
					my @idx = split '_', $idx; shift @idx;
					my $target = \$list{$key};
					for my $x (@idx) {
						my $o = 1;
						if ($key eq 'key' or $key eq 'key_command') {
							$o = 0;
						}
						if ($x-$o < 0) {
							local $" = '|';
							weechat::print('',"list error: $target/$$_/$key/$x/$idx/@idx(@_)");
							$o = 0;
						}
						$target = \$$target->[$x-$o]
					}
					$$target = $r;

					$key => $list{$key}
				}
				else {
					$$_ => $r
				}
			} @fields
		} };
	}
	weechat::infolist_free($infptr);
	!wantarray && @infolist ? \@infolist : @infolist
}

## hdh -- hdata helper
## $_[0] - arg pointer or hdata list name
## $_[1] - hdata name
## $_[2..$#_] - hdata variable name
## $_[-1] - hashref with key/value to update (optional)
## returns value of hdata, and hdata name in list ctx, or number of variables updated
sub hdh {
	if (@_ > 1 && $_[0] !~ /^0x/ && $_[0] !~ /^\d+$/) {
		my $arg = shift;
		unshift @_, weechat::hdata_get_list(weechat::hdata_get($_[0]), $arg);
	}
	while (@_ > 2) {
		my ($arg, $name, $var) = splice @_, 0, 3;
		my $hdata = weechat::hdata_get($name);
		unless (ref $var eq 'HASH') {
			$var =~ s/!(.*)/weechat::hdata_get_string($hdata, $1)/e;
			(my $plain_var = $var) =~ s/^\d+\|//;
			my $type = weechat::hdata_get_var_type_string($hdata, $plain_var);
			if ($type eq 'pointer') {
				my $name = weechat::hdata_get_var_hdata($hdata, $var);
				unshift @_, $name if $name;
			}

			my $fn = "weechat::hdata_$type";
			unshift @_, do { no strict 'refs';
							 &$fn($hdata, $arg, $var) };
		}
		else {
			return weechat::hdata_update($hdata, $arg, $var);
		}
	}
	wantarray ? @_ : $_[0]
}

## hook_dynamic -- weechat::hook something and store hook reference
## $hook_call - hook type (e.g. modifier)
## $what - event type to hook (depends on $hook_call)
## $sub - subroutine name to install
## @params - parameters
sub hook_dynamic {
	my ($hook_call, $what, $sub, @params) = @_;
	my $caller_package = (caller)[0];
	eval qq{
		package $caller_package;
		no strict 'vars';
		\$DYNAMIC_HOOKS{\$what}{\$sub} =
			weechat::hook_$hook_call(\$what, \$sub, \@params)
				unless exists \$DYNAMIC_HOOKS{\$what} &&
					exists \$DYNAMIC_HOOKS{\$what}{\$sub};
	};
	die $@ if $@;
}

## unhook_dynamic -- weechat::unhook something where hook reference has been stored with hook_dynamic
## $what - event type that was hooked
## $sub - subroutine name that was installed
sub unhook_dynamic {
	my ($what, $sub) = @_;
	my $caller_package = (caller)[0];
	eval qq{
		package $caller_package;
		no strict 'vars';
		weechat::unhook(\$DYNAMIC_HOOKS{\$what}{\$sub})
			if exists \$DYNAMIC_HOOKS{\$what} &&
				exists \$DYNAMIC_HOOKS{\$what}{\$sub};
		delete \$DYNAMIC_HOOKS{\$what}{\$sub};
		delete \$DYNAMIC_HOOKS{\$what} unless \%{\$DYNAMIC_HOOKS{\$what}};
	};	
	die $@ if $@;
}

use Pod::Select qw();
use Pod::Simple::TextContent;

## get_desc_from_pod -- return setting description from pod documentation
## $file - filename with pod
## $setting - name of setting
## returns description as text
sub get_desc_from_pod {
	my $file = shift;
	return unless -s $file;
	my $setting = shift;

	open my $pod_sel, '>', \my $ss;
	Pod::Select::podselect({
	   -output => $pod_sel,
	   -sections => ["SETTINGS/$setting"]}, $file);

	my $pt = new Pod::Simple::TextContent;
	$pt->output_string(\my $ss_f);
	$pt->parse_string_document($ss);

	my ($res) = $ss_f =~ /^\s*\Q$setting\E\s+(.*)\s*/;
	$res
}

## get_settings_from_pod -- retrieve all settings in settings section of pod
## $file - file with pod
## returns list of all settings
sub get_settings_from_pod {
	my $file = shift;
	return unless -s $file;

	open my $pod_sel, '>', \my $ss;
	Pod::Select::podselect({
	   -output => $pod_sel,
	   -sections => ["SETTINGS//!.+"]}, $file);

	$ss =~ /^=head2\s+(.*)\s*$/mg
}

## mangle_man_for_wee -- turn man output into weechat codes
## @_ - list of grotty lines that should be turned into weechat attributes
## returns modified lines and modifies lines in-place
sub mangle_man_for_wee {
	for (@_) {
		s/_\x08(.)/weechat::color('underline').$1.weechat::color('-underline')/ge;
		s/(.)\x08\1/weechat::color('bold').$1.weechat::color('-bold')/ge;
	}
	wantarray ? @_ : $_[0]
}

## read_manpage -- read a man page in weechat window
## $file - file with pod
## $name - buffer name
sub read_manpage {
	my $caller_package = (caller)[0];
	my $file = shift;
	my $name = shift;

	if (my $obuf = weechat::buffer_search('perl', "man $name")) {
		eval qq{
			package $caller_package;
			weechat::buffer_close(\$obuf);
		};
	}

	my @wee_keys = Nlib::i2h('key');
	my @keys;

	my $winptr = weechat::current_window();
	my ($wininfo) = Nlib::i2h('window', $winptr);
	my $buf = weechat::buffer_new("man $name", '', '', '', '');
	return weechat::WEECHAT_RC_OK unless $buf;

	my $width = $wininfo->{'chat_width'};
	--$width if $wininfo->{'chat_width'} < $wininfo->{'width'} || ($wininfo->{'width_pct'} < 100 && (grep { $_->{'y'} == $wininfo->{'y'} } Nlib::i2h('window'))[-1]{'x'} > $wininfo->{'x'});
	$width -= 2; # when prefix is shown

	weechat::buffer_set($buf, 'time_for_each_line', 0);
	eval qq{
		package $caller_package;
		weechat::buffer_set(\$buf, 'display', 'auto');
	};
	die $@ if $@;

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_previous' ||
			   $_->{'command'} eq '/input history_global_previous' } @wee_keys;
	@keys = 'meta2-A' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll -1') for @keys;

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_next' ||
			   $_->{'command'} eq '/input history_global_next' } @wee_keys;
	@keys = 'meta2-B' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll +1') for @keys;

	weechat::buffer_set($buf, 'key_bind_ ', '/window page_down');

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input delete_previous_char' } @wee_keys;
	@keys = ('ctrl-?', 'ctrl-H') unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window page_up') for @keys;

	weechat::buffer_set($buf, 'key_bind_g', '/window scroll_top');
	weechat::buffer_set($buf, 'key_bind_G', '/window scroll_bottom');

	weechat::buffer_set($buf, 'key_bind_q', '/buffer close');

	weechat::print($buf, " \t".mangle_man_for_wee($_)) # weird bug with \t\t showing nothing?
			for `pod2man \Q$file\E 2>/dev/null | GROFF_NO_SGR=1 nroff -mandoc -rLL=${width}n -rLT=${width}n -Tutf8 2>/dev/null`;
	weechat::command($buf, '/window scroll_top');

	unless (hdh($buf, 'buffer', 'lines', 'lines_count') > 0) {
		weechat::print($buf, weechat::prefix('error').$_)
				for "Unfortunately, your @{[weechat::color('underline')]}nroff".
					"@{[weechat::color('-underline')]} command did not produce".
					" any output.",
					"Working pod2man and nroff commands are required for the ".
					"help viewer to work.",
					"In the meantime, please use the command ", '',
					"\tperldoc $file", '',
					"on your shell instead in order to read the manual.",
					"Thank you and sorry for the inconvenience."
	}
}

1
}

our $MAGIC_ENTER_TIMER;
our $MAGIC_LOCK;
our $MAGIC_LOCK_TIMER;
our $WEECHAT_PASTE_FIX_CTRLJ_CMD;
our $INPUT_CHANGED_EATER_FLAG;
our $IGNORE_INPUT_CHANGED;
our $IGNORE_INPUT_CHANGED2;

use constant KEY_RET => 'ctrl-M';
use constant INPUT_NL => '/input insert \x0a';
use constant INPUT_MAGIC => '/input magic_enter';
our $NL = "\x0a";

init_multiline();
weechat::hook_config('plugins.var.perl.'.SCRIPT_NAME.'.*', 'default_options', '');
weechat::hook_modifier('input_text_display_with_cursor', 'multiline_display', '');
weechat::hook_command_run('/help '.SCRIPT_NAME, 'help_cmd', '');
weechat::hook_command_run(INPUT_MAGIC, 'magic_enter', '');
Nlib::hook_dynamic('signal', 'input_text_*', 'magic_enter_cancel', '');
weechat::hook_signal('key_pressed', 'magic_lock_hatch', '');
# we need lower than default priority here or the first character is separated
weechat::hook_signal('500|input_text_changed', 'paste_undo_hack', '')
	# can only do this on weechat 0.4.0
	if (weechat::info_get('version_number', '') || 0) >= 0x00040000;
hook_complete('complete*', 'delete_*', 'move_*');

## multiline_display -- show multi-lines on display of input string
## () - modifier handler
## $_[2] - buffer pointer
## $_[3] - input string
## returns modified input string
sub multiline_display {
	Encode::_utf8_on($_[3]);
	Encode::_utf8_on(my $nl = weechat::config_get_plugin('char') || ' ');
	Encode::_utf8_on(my $tab = weechat::config_get_plugin('tab'));
	my $cb = weechat::current_buffer() eq $_[2] && $MAGIC_ENTER_TIMER;
	if ($cb) {
		$_[3] =~ s/$NL\x19b#/\x19b#/ if weechat::config_string_to_boolean(weechat::config_get_plugin('hide_magic_nl'));
	}
	if ($_[3] =~ s/$NL/$nl\x0d/g) {
		$_[3] =~ s/\A/ \x0d/ if weechat::config_string_to_boolean(weechat::config_get_plugin('lead_linebreak'));
	}
	$_[3] =~ s/\x09/$tab/g if $tab;
	if ($cb) {
		Encode::_utf8_on(my $magic = weechat::config_get_plugin('magic'));
		$_[3] =~ s/\Z/$magic/ if $magic;
	}
	$_[3]
}

## lock_timer_exp -- expire the magic lock timer
sub lock_timer_exp {
	if ($MAGIC_LOCK_TIMER) {
		weechat::unhook($MAGIC_LOCK_TIMER);
		$MAGIC_LOCK_TIMER = undef;
	}
	weechat::WEECHAT_RC_OK
}

## paste_undo_stop_ignore -- unset ignore2 flag
sub paste_undo_stop_ignore {
	$IGNORE_INPUT_CHANGED2 = undef;
	weechat::WEECHAT_RC_OK
}

## paste_undo_start_ignore -- set ignore2 flag when /input is received so to allow /input undo/redo
## () - command_run handler
## $_[2] - command that was called
sub paste_undo_start_ignore {
	return weechat::WEECHAT_RC_OK if $IGNORE_INPUT_CHANGED;
	return weechat::WEECHAT_RC_OK if $_[2] =~ /insert/;
	$IGNORE_INPUT_CHANGED2 = 1;
	weechat::WEECHAT_RC_OK
}

## paste_undo_hack -- fix up undo stack when paste is detected by calling /input undo
## () - signal handler
## $_[2] - buffer pointer
sub paste_undo_hack {
	return weechat::WEECHAT_RC_OK if $IGNORE_INPUT_CHANGED;
	return paste_undo_stop_ignore() if $IGNORE_INPUT_CHANGED2;
	if ($MAGIC_LOCK > 0 && get_lock_enabled()) {
		signall_ignore_input_changed(1);
		Nlib::hook_dynamic('command_run', '/input *', 'paste_undo_start_ignore', '');

		Encode::_utf8_on(my $input = weechat::buffer_get_string($_[2], 'input'));
		my $pos = weechat::buffer_get_integer($_[2], 'input_pos');

		weechat::command($_[2], '/input undo') for 1..2;

		weechat::buffer_set($_[2], 'input', $input);
		weechat::buffer_set($_[2], 'input_pos', $pos);

		Nlib::unhook_dynamic('/input *', 'paste_undo_start_ignore');
		signall_ignore_input_changed(0);
	}
	weechat::WEECHAT_RC_OK
}

## input_changed_eater -- suppress input_text_changed signal on new weechats
## () - signal handler
sub input_changed_eater {
	$INPUT_CHANGED_EATER_FLAG = undef;
	weechat::WEECHAT_RC_OK_EAT
}

## signall_ignore_input_changed -- use various methods to "ignore" input_text_changed signal
## $_[0] - start ignore or stop ignore
sub signall_ignore_input_changed {
	if ($_[0]) {
		weechat::hook_signal_send('input_flow_free', weechat::WEECHAT_HOOK_SIGNAL_INT, 1);
		Nlib::hook_dynamic('signal', '2000|input_text_changed', 'input_changed_eater', '');
		$IGNORE_INPUT_CHANGED = 1;
		weechat::buffer_set('', 'completion_freeze', '1');
	}
	else {
		weechat::buffer_set('', 'completion_freeze', '0');
		$IGNORE_INPUT_CHANGED = undef;
		Nlib::unhook_dynamic('2000|input_text_changed', 'input_changed_eater');
		weechat::hook_signal_send('input_flow_free', weechat::WEECHAT_HOOK_SIGNAL_INT, 0);
	}
}

## multiline_complete_fix -- add per line /input handling for completion, movement and deletion
## () - command_run handler
## $_[0] - original bound data
## $_[1] - buffer pointer
## $_[2] - original command
sub multiline_complete_fix {
	Nlib::unhook_dynamic('input_text_*', 'magic_enter_cancel');
	Nlib::unhook_dynamic("1500|/input $_[0]", 'multiline_complete_fix');
	if ($_[2] =~ s/_message$/_line/ || !weechat::config_string_to_boolean(weechat::config_get_plugin('modify_keys'))) {
		weechat::command($_[1], $_[2]);
	}
	else {
		signall_ignore_input_changed(1);
		Encode::_utf8_on(my $input = weechat::buffer_get_string($_[1], 'input'));
		my $pos = weechat::buffer_get_integer($_[1], 'input_pos');
		if ($pos && $_[2] =~ /(?:previous|beginning_of)_/ && (substr $input, $pos-1, 1) eq $NL) {
			substr $input, $pos-1, 1, "\0"
		}
		elsif ($pos < length $input && $_[2] =~ /(?:next|end_of)_/ && (substr $input, $pos, 1) eq $NL) {
			substr $input, $pos, 1, "\0"
		}
		my @lines = $pos ? (split /$NL/, (substr $input, 0, $pos), -1) : '';
		my @after = $pos < length $input ? (split /$NL/, (substr $input, $pos), -1) : '';
		$lines[-1] =~ s/\0$/$NL/;
		$after[0] =~ s/^\0/$NL/;
		my ($p1, $p2) = (pop @lines, shift @after);
		weechat::buffer_set($_[1], 'input', $p1.$p2);
		weechat::buffer_set($_[1], 'input_pos', length $p1);

		Nlib::hook_dynamic('signal', 'input_text_*', 'magic_enter_cancel', '');
		$INPUT_CHANGED_EATER_FLAG = 1;
		weechat::command($_[1], $_[2]);
		my $changed_later = !$INPUT_CHANGED_EATER_FLAG;
		magic_enter_cancel() if $changed_later;
		Nlib::unhook_dynamic('input_text_*', 'magic_enter_cancel');

		Encode::_utf8_on(my $p = weechat::buffer_get_string($_[1], 'input'));
		$pos = weechat::buffer_get_integer($_[1], 'input_pos');
		weechat::command($_[1], '/input undo') if @lines || @after;
		weechat::command($_[1], '/input undo');
		weechat::buffer_set($_[1], 'input', join $NL, @lines, $p, @after);
		weechat::buffer_set($_[1], 'input_pos', $pos+length join $NL, @lines, '');

		signall_ignore_input_changed(0);
		weechat::hook_signal_send('input_text_changed', weechat::WEECHAT_HOOK_SIGNAL_POINTER, $_[1]) if $changed_later;
	}
	hook_complete($_[0]);
	Nlib::hook_dynamic('signal', 'input_text_*', 'magic_enter_cancel', '');
	weechat::WEECHAT_RC_OK_EAT
}

## help_cmd -- show multi-line script documentation
## () - command_run handler
sub help_cmd {
	Nlib::read_manpage(SCRIPT_FILE, SCRIPT_NAME);
	weechat::WEECHAT_RC_OK_EAT
}

## get_lock_time -- gets timeout for paste detection according to setting
## returns timeout (at least 1)
sub get_lock_time {
	my $lock_time = weechat::config_get_plugin('paste_lock');
	$lock_time = 1 unless $lock_time =~ /^\d+$/ && $lock_time;
	$lock_time
}

## get_lock_enabled -- checks whether the paste detection lock is enabled
## returns bool
sub get_lock_enabled {
	my $lock = weechat::config_get_plugin('paste_lock');
	$lock = weechat::config_string_to_boolean($lock)
		unless $lock =~ /^\d+$/;
	$lock
}

## magic_lock_hatch -- set a timer for paste detection
## () - signal handler
sub magic_lock_hatch {
	lock_timer_exp();
	$MAGIC_LOCK_TIMER = weechat::hook_timer(get_lock_time(), 0, 1, 'lock_timer_exp', '');
	weechat::WEECHAT_RC_OK
}

## magic_unlock -- reduce the lock added by paste detection
## () - timer handler
sub magic_unlock {
	if ($MAGIC_LOCK_TIMER) {
		weechat::hook_timer(get_lock_time(), 0, 1, 'magic_unlock', '');
	}
	else {
		--$MAGIC_LOCK;
		if (!$MAGIC_LOCK && $WEECHAT_PASTE_FIX_CTRLJ_CMD) {
			do_key_bind('ctrl-J', $WEECHAT_PASTE_FIX_CTRLJ_CMD);
			$WEECHAT_PASTE_FIX_CTRLJ_CMD = undef;
		}
	}
	weechat::WEECHAT_RC_OK
}

## get_magic_enter_time -- get timeout for auto-sending messages according to config
## returns timeout
sub get_magic_enter_time {
	my $magic_enter = weechat::config_get_plugin('magic_enter_time');
	$magic_enter = 1000 * weechat::config_string_to_boolean($magic_enter)
		unless $magic_enter =~ /^\d+$/;
	$magic_enter
}

## magic_enter -- receive enter key and do magic things: set up a timer for sending the message, add newline
## () - command_run handler
## $_[1] - buffer pointer
sub magic_enter {
	Encode::_utf8_on(my $input = weechat::buffer_get_string($_[1], 'input'));
	if (!length $input && weechat::config_string_to_boolean(weechat::config_get_plugin('send_empty'))) {
		weechat::command($_[1], '/input return');
	}
	else {
		magic_enter_cancel();
		weechat::command($_[1], INPUT_NL);

		unless (get_lock_enabled() && $MAGIC_LOCK) {
			if (weechat::config_string_to_boolean(weechat::config_get_plugin('magic_paste_only')) &&
			   $input !~ /$NL/) {
				magic_enter_send($_[1]);
			}
			elsif (my $magic_enter = get_magic_enter_time()) {
				$MAGIC_ENTER_TIMER = weechat::hook_timer($magic_enter, 0, 1, 'magic_enter_send', $_[1]);
			}
		}
	}
	weechat::WEECHAT_RC_OK_EAT
}

## magic_enter_send -- actually send enter key when triggered by magic_enter, remove preceding newline
## $_[0] - buffer pointer
## sending is delayed by 1ms to circumvent crash bug in api
sub magic_enter_send {
	magic_enter_cancel();
	weechat::command($_[0], '/input delete_previous_char');
	weechat::command($_[0], '/wait 1ms /input return');
	weechat::WEECHAT_RC_OK
}

## magic_enter_cancel -- cancel the timer for automatic sending of message, for example when more text was added, increase the paste lock for paste detection when used as signal handler
## () - signal handler when @_ is set
sub magic_enter_cancel {
	if ($MAGIC_ENTER_TIMER) {
		weechat::unhook($MAGIC_ENTER_TIMER);
		$MAGIC_ENTER_TIMER = undef;
	}
	if ($MAGIC_LOCK_TIMER && @_) {
		if (!$MAGIC_LOCK && !$WEECHAT_PASTE_FIX_CTRLJ_CMD &&
				weechat::config_string_to_boolean(weechat::config_get_plugin('weechat_paste_fix'))) {
			($WEECHAT_PASTE_FIX_CTRLJ_CMD) = get_key_command('ctrl-J');
			$WEECHAT_PASTE_FIX_CTRLJ_CMD = '-' unless defined $WEECHAT_PASTE_FIX_CTRLJ_CMD;
			do_key_bind('ctrl-J', '-');
		}
		++$MAGIC_LOCK;
		weechat::hook_timer(get_lock_time(), 0, 1, 'magic_unlock', '');
	}
	weechat::WEECHAT_RC_OK
}

## hook_complete -- dynamically enable the multiline_complete_fix for per-line movement/completion
sub hook_complete {
	Nlib::hook_dynamic('command_run', "1500|/input $_", 'multiline_complete_fix', $_)
		for @_;
	weechat::WEECHAT_RC_OK
}

## need_magic_enter -- check if magic enter keybinding is needed according to config settings
## returns bool
sub need_magic_enter {
	weechat::config_string_to_boolean(weechat::config_get_plugin('send_empty')) || get_magic_enter_time() ||
			weechat::config_string_to_boolean(weechat::config_get_plugin('magic_paste_only'))
}

## do_key_bind -- mute execute a key binding, or unbind if $_[-1] is '-'
## @_ - arguments to /key bind
sub do_key_bind {
	if ($_[-1] eq '-') {
		pop;
		weechat::command('', "/mute /key unbind @_");
	}
	elsif ($_[-1] eq '!') {
		pop;
		weechat::command('', "/mute /key reset @_");
	}
	else {
		weechat::command('', "/mute /key bind @_");
	}
}

## get_key_command -- get the command bound to a key
## $_[0] - key in weechat syntax
## returns the command
sub get_key_command {
	map { $_->{command} } grep { $_->{key} eq $_[0] }
		Nlib::i2h('key')
}

## default_options -- set up default option values on start and when unset
## () - config handler if @_ is set
sub default_options {
	my %defaults = (
		char 			  => '↩',
		tab 			  => '──▶▏',
		magic 			  => '‼',
		ipl 			  => 'on',
		lead_linebreak 	  => 'on',
		modify_keys 	  => 'on',
		send_empty 		  => 'on',
		magic_enter_time  => '1000',
		paste_lock 		  => '1',
		magic_paste_only  => 'off',
		hide_magic_nl 	  => 'on',
		weechat_paste_fix => 'on',
	);
	unless (weechat::config_is_set_plugin('ipl')) {
		if (my $bar = weechat::bar_search('input')) {
			weechat::bar_set($bar, $_, '0') for 'size', 'size_max';
		}
	}
	for (keys %defaults) {
		weechat::config_set_plugin($_, $defaults{$_})
			unless weechat::config_is_set_plugin($_);
	}
	do_key_bind(KEY_RET, INPUT_NL)
		if weechat::config_string_to_boolean(weechat::config_get_plugin('ipl'));
	my ($enter_key) = get_key_command(KEY_RET);
	if (need_magic_enter()) {
		do_key_bind(KEY_RET, INPUT_MAGIC)
			if $enter_key eq INPUT_NL;
	}
	else {
		do_key_bind(KEY_RET, INPUT_NL)
			if $enter_key eq INPUT_MAGIC;
	}
	weechat::WEECHAT_RC_OK
}

sub init_multiline {
	$MAGIC_LOCK = -1;
	default_options();
	my $sf = SCRIPT_FILE;
	for (Nlib::get_settings_from_pod($sf)) {
		weechat::config_set_desc_plugin($_, Nlib::get_desc_from_pod($sf, $_));
	}
	weechat::WEECHAT_RC_OK
}

sub stop_multiline {
	magic_enter_cancel();
	if (need_magic_enter()) {
		my ($enter_key) = get_key_command(KEY_RET);
		do_key_bind(KEY_RET, INPUT_NL)
			if $enter_key eq INPUT_MAGIC;
	}
	if ($WEECHAT_PASTE_FIX_CTRLJ_CMD) {
		do_key_bind('ctrl-J', $WEECHAT_PASTE_FIX_CTRLJ_CMD);
		$WEECHAT_PASTE_FIX_CTRLJ_CMD = undef;
	}
	if (weechat::config_string_to_boolean(weechat::config_get_plugin('ipl'))) {
		do_key_bind(KEY_RET, '!');
	}
	weechat::WEECHAT_RC_OK
}
