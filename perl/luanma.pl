use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
use Encode;
eval { local $SIG{__DIE__}; # silence weechat die handler
	   require Encode::HanExtra }; # more chinese
eval { local $SIG{__DIE__};
	   require Encode::JIS2K }; # more japanese
use Time::Local;

# luanma.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

# to read the following docs, you can use "perldoc luanma.pl"

=head1 NAME

luanma - store more info about encoding of message, and change it with update (weechat edition)

=head1 SYNOPSIS

more help for charset troubles

command is called /lma

see "/help lma" for usage

=head1 DESCRIPTION

luanma will allow you to view received messages as they would appear
when decoded using different charsets. you might know this feature
from your webbrowser. it is useful if you need to understand a message
that was received, but it looks garbled because the sender used
different charset than you.

as usual, a list of charsets can be defined that will be tried in
consecution until a successful decode is made.

the charset can be choosen differently for different times in the past
and based on nick and weechat buffer. furthermore, you can use /debug
tags to see which charset was used to decode a message.

a table of charset rules will be saved to luanma.conf and can be
edited with /lma set command.

=head1 CAVEATS

=over

=item *

the automatic encoding of outgoing notices is visible on display and
no assessment of success is given, because weechat does not set the
appropriate tag on outgoing notices

=item *

in order to not convert all messages as raw, only high bit data
(extended ascii) is encoded. that means the script works fine for
latin variants and utf8, but B<not> for any 7bit-clean encoding or for
national EBCDIC

=item *

colours might get mixed up with colorize_nicks script when there is a
nick with the same name as a 2-hex-character encoding (example:
"b2"). One possible workaround is to turn off greedy_matching in
colorize_nicks

=item *

no encoding is done when outgoing charset is specified as 'utf8'

=back

=head1 BUGS

=over

=item *

splitting of messages is not supported, so if byte-length of message
in utf8 exceeds 510, it will get split by weechat. result is that only
the first part is encoded properly.

if byte-length of B<encoded> message exceeds 510, then it will usually
get cut off (exact behaviour depends on IRC server)

=item *

the prefix on ACTION messages ('/me') gets recoded for messages that
you send yourself. this will cause problems with utf8 nicknames where
supported

=back

=head1 SETTINGS

the settings are usually found in the

  plugins.var.perl.luanma

namespace, that is, type

  /set plugins.var.perl.luanma.*

to see them and

  /set plugins.var.perl.luanma.SETTINGNAME VALUE

to change a setting C<SETTINGNAME> to a new value C<VALUE>. Finally,

  /unset plugins.var.perl.luanma.SETTINGNAME

will reset a setting to its default value.

the following settings are available:

=head2 tags

white-space separated list of irc_(in_) tags to store raw messages of
(only those can be recoded). see /debug tags

=head2 encode_warn

add a warning message into the line displayed on your buffer, when
encoding of outgoing messages fails/is lossy

=head2 parser

parser to use for line parsing. valid options: ondemand, async,
full. ondemand will parse lines when displayed on screen (needs parse
on every buffer switch, but fast on load). async and full do not need
to parse lines when switching buffers, but WILL FREEZE your weechat on
/script (re)load and /upgrade. be careful.

async uses timers to do the parsing which should make it less likely
for you to drop network connection. full will do the parse in one
swipe, so it is faster and the freeze is of shorter duration.

=cut

use constant SCRIPT_NAME => 'luanma';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.2', 'GPL3',
				  'more flexibility with incoming charset', 'stop_luanma', '') || return;
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

sub fu8on(@) {
	Encode::_utf8_on($_) for @_; wantarray ? @_ : shift
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

1
}

use constant CMD_NAME => 'lma';

our @nags;
our $nag_tag;
our %nag_modifiers;

our $CFG_FILE_NAME = weechat::info_get('weechat_dir', '').weechat::info_get('dir_separator', '').SCRIPT_NAME.'.conf';

our (@CFG_TABLE, @CFG_TABLE_2);
our @STO = (\(our (%BYTE_MSGS, %ESC_MSG, %MSG_TIME, %MSG_BUF, %MSG_NICK, %MSG_ENC, %MSG_FLT, %MSG_COLOR)));
our (@ENCODE_TABLE, @ENCODE_TABLE2);
our %DEC;
our $GC_COUNT;

our $GC_LIMIT = 10_000;
our $PARSE_STATS = 987;

our $ASYNC_PARSE = $PARSE_STATS;
our %ASYNC_BUF;
our $ASYNC_TIMER;

our @mon = qw(jan feb mar apr may jun jul aug sep oct nov dec);
our %mon = do { my $i = 0; map { $_ => $i++ } @mon };
our $mon_re = join '|', @mon;

## esc1 -- escape all endangered characters
## @_ - strings to modify
sub esc1 {
	for (@_) {
		# need to fix up escape here, weechat kills it
		# see grep { weechat::string_remove_color(chr $_, "") ne chr $_ } (000..0177)
		# our escape bracket is 020
		s/([^\000-\017\021-\030\035-\175\177])/sprintf "\020%x\020", ord $1/ge;
	}
}

## esc_only -- message needs no recode
## $_[0] - message string to check
## returns bool
sub esc_only {
	$_[0] !~ /[^\000-\032\034-\175\177]/
}

init_luanma();

weechat::hook_config('plugins.var.perl.'.SCRIPT_NAME.'.*', 'default_options', '');
weechat::hook_signal('buffer_line_added', 'line_sig', '');
weechat::hook_signal('upgrade', 'restore_lines', '');
weechat::hook_modifier('input_text_for_buffer', 'auto_encode_mod', '');
weechat::hook_command(CMD_NAME, 'a better /charset',
					  (join ' || ', 'list',
					   'set <ts> <buffer> <nick> [<encodings...>] [-out <encoding>]',
					   'set -out <buffer> <pattern> <encoding>',
					   'del <ts> <buffer> <nick> [-g]',
					   'del -out <buffer> <pattern> [-g]',
					   'save',
					   'reload',
					   'list_rules',
					   'gc',
					   'forget -yes',
				   ), (join "\n",
					   'without arguments, the list of keys is displayed',
					   '',
					   '      list: show list of current recode rules',
					   '       set: adds or modifies a recode rule',
					   '       del: delete one or many recode rules',
					   '      save: save rules to config file',
					   '    reload: reload rules from config file',
					   'list_rules: list internal rules and pointers (for debug and /debug tags)',
					   '        gc: remove raw lines from cache that are no longer valid in weechat (this is also done autoatically)',
					   "    forget: forget everything about messages, forget all raw and all ESC messages. be careful, /@{[CMD_NAME]} cannot be used anymore after youx do this!",
					   '',
					   '        ts: timestamp at which the rule starts to become effective',
					   '    the following time specifications are supported:',
					   '      1357986420: unix timestamp as output by `date +%s\' (used by weechat internally)',
					   '     -59  | -59m: relative time, 59 seconds/minutes /',
					   '     -23h |  -1d: 23 hours / 1 day ago',
					   '       HH:MM:SS : time (hour:minutes:seconds)',
					   '          Jan01 : date (format: MonDD)',
					   '     Jan0100:00:00 = midnight on January 1st.',
					   '               1: from the beginning on',
					   '               0: starting from now',
					   '    the "del" command additionally supports these specifiers:',
					   '         *: any time',
					   '       >ts: rule effective after ts',
					   '       <ts: rule effective before ts',
					   '     ts-ts: rule effective between ts1 and ts2',
					   '',
					   '    buffer: buffer name in the format network.#channel or network.nick',
					   '            * is allowed as wildcard',
					   '',
					   '      nick: additionally nick tag to match',
					   '            * is allowed as wildcard',
					   '            if nick ends with "+", buffer is more important when selecting rule',
					   '            when unclear about the order in which rules apply, you can verify with "list_rules"',
					   '',
					   '   pattern: pattern which is matched on input line to decide automatic encoding',
					   '            * is allowed as wildcard, use ** to break space boundaries',
					   '',
					   '      -out: edit the output encoding list instead of decoding rules list',
					   '',
					   '        -g: when used after the "del" command, wildcards are used on the settings list to mass-delete matching entries. otherwise, wildcards match the rule that has this exact wildcard',
					   '',
					   ' encodings: list of whitespace separated encodings to try, in order, to decode incoming message',
					   '            see `man Encode::Supported\' for a list of supported encodings',
					   '            special encoding "x" means do not decode',
					   '            an "!" can be added after utf8 to signify that partial decoding is acceptable',
					   '            (for example invalid utf8 resulting by last character cut short)',
				   ), (join ' || ', 'list %-',
					   'set %- %(buffers_names) %(nick)',
					   'del %- %(buffers_names) %(nick) -g %-',
					   'save %-',
					   'reload %-',
					   'list_rules %-',
					   'gc %-',
					   'forget %-',
				   ), 'lma_cmd', '');
weechat::hook_command_run('/save', 'lma_wee_save', 'save');
weechat::hook_command_run('/reload', 'lma_wee_save', 'reload');

## irc_in_mod -- replace high bits (before charset decode)
## () - modifier handler
## $_[1] - modifier
## $_[3] - content
## returns modified content
sub irc_in_mod {
	my ($p, $x, $s) = split '( :)', $_[3], 2;
	return $_[3] unless defined $s;
	esc1($s);
	"$p$x$s"
}

## irc_out_mod -- encode utf8 to local charset on send
## () - modifier handler
## $_[1] - modifier
## $_[3] - content
## returns modified content
sub irc_out_mod {
	my ($p, $x, $s) = split '( :)', $_[3], 2;
	return $_[3] unless defined $s;
	Encode::_utf8_on($s);
	my $codecs = join '|', map { quotemeta } sort { length $b <=> length $a } keys %DEC;
	if ($s =~ s/^\02010\020/\020/) {}
	elsif ($s =~ s/^\020($codecs)\020//) {
		$s = $DEC{$1}->encode($s, Encode::FB_DEFAULT); # must make best effort here
	}
	elsif ($p =~ /^PRIVMSG/ && $s =~ /^(\01ACTION )\020($codecs)\020(.*)(\01)$/) { # /me
		$s = "\01ACTION ".$DEC{$2}->encode($3, Encode::FB_DEFAULT)."\01"; # avoid upgrade
	}
	else {
		return $_[3]
	}
	"$p$x$s"
}

## auto_encode_mod -- add encoding prefixes to buffer input line
## () - modifier handler
## $_[1] - modifier
## $_[3] - content of line before sending
sub auto_encode_mod {
	# XXX should do the splitting
	my $in = Nlib::fu8on(weechat::string_input_for_buffer($_[3]));
	return $_[3] unless $in; # pass through commands
	return $_[3] unless exists $nag_modifiers{privmsg};
	return $_[3] if $in =~ /^\020/; # already marked

	my $buf = Nlib::hdh($_[2], 'buffer', 'name');

	my ($r) =
	grep { $buf =~ $_->{buf_re} && $in =~ $_->{pat_re} } @ENCODE_TABLE2;

	return $_[3] unless $r;
	return $_[3] if $r->{_}{charset} eq 'utf8'; # XXX
	"\020${$r}{_}{charset}\020$in"
}

## auto_encode_cmd -- add tag to command for encode marker
## () - command_run handler
## $_[0] - forward to which command
## $_[1] - buffer pointer
## $_[2] - command
sub auto_encode_cmd {
	# XXX should do the splitting
	Encode::_utf8_on($_[2]);
	#my @args = split ' ', $_[2];
	my ($pre, $in, $buf);
	if ($_[0] eq 'me' && $_[2] =~ /^(\S+\s)(.*)$/i) {
		($pre, $in) = ($1, $2);
		$buf = weechat::buffer_get_string($_[1], 'name');
	}
	elsif ($_[0] eq 'msg' && $_[2] =~ /^(\S+(?:\s+-server\s+(\S+))?\s+(\S+) )(.*)$/i) {
		my ($srv, $targ) = ($2, $3);
		($pre, $in) = ($1, $4);
		$srv //= weechat::buffer_get_string($_[1], 'localvar_server');
		$buf = $targ ne '*' ? "$srv.$targ" : weechat::buffer_get_string($_[1], 'name');
	}
	elsif ($_[0] eq 'query' && $_[2] =~ /^(\S+(?:\s+-server\s+(\S+))?\s+(\S+) )(\s*\S.*)$/i) {
		my ($srv, $targ) = ($2, $3);
		($pre, $in) = ($1, $4);
		$srv //= weechat::buffer_get_string($_[1], 'localvar_server');
		$buf = "$srv.$targ";
	}
	elsif ($_[0] eq 'wallchops' && $_[2] =~ /^(\S+(?:\s+([#&]\S+))? )(.*)$/i) {
		my $targ = $2;
		($pre, $in) = ($1, $3);
		$buf = $targ ? weechat::buffer_get_string($_[1], 'localvar_server').'.'.$targ :
			weechat::buffer_get_string($_[1], 'name');
	}
	elsif ($_[0] eq 'topic' && $_[2] !~ /\s-delete\s*$/i && $_[2] =~ /^(\S+(?:\s+([#&\S+]))? )(.*)$/i) {
		my $targ = $2;
		($pre, $in) = ($1, $3);
		$buf = $targ ? weechat::buffer_get_string($_[1], 'localvar_server').'.'.$targ :
			weechat::buffer_get_string($_[1], 'name');
	}
	else {
		return weechat::WEECHAT_RC_OK
	}

	return weechat::WEECHAT_RC_OK if $in =~ /^\020/; # already marked

	my ($r) =
	grep { $buf =~ $_->{buf_re} && $in =~ $_->{pat_re} } @ENCODE_TABLE2;

	return weechat::WEECHAT_RC_OK unless $r;
	return weechat::WEECHAT_RC_OK if $r->{_}{charset} eq 'utf8'; # XXX
	weechat::command($_[1], "$pre\020${$r}{_}{charset}\020$in");
	return weechat::WEECHAT_RC_OK_EAT
}


## find_rule -- find rule to recode this line
## $time - timestamp of line
## $buf - buffer name
## $nick - nick
## returns rule if found or undef
sub find_rule {
	my ($time, $buf, $nick) = @_;
	my ($r) =
	grep { $_->{_}{time} <= $time && $buf =~ $_->{buf_re} && $nick =~ $_->{nick_re} } @CFG_TABLE_2;
	$r
}

## apply_recode -- recode a line, looking up its rule first
## $lp - pointer to 'line' hdata
sub apply_recode {
	my $lp = shift;
	my $rule = find_rule($MSG_TIME{$lp}, $MSG_BUF{$lp}, $MSG_NICK{$lp})//\undef;
	return if $rule == $MSG_FLT{$lp};
	my ($s, $e);
	for my $enc ((($rule == \undef) ? () : @{$rule->{_}{charsets}}), 'x') {
		$s = $BYTE_MSGS{$lp};
		if ($enc eq 'x') {
			esc1($s);
			$e = $enc;
			last;
		}
		else {
			my $enc2 = $enc;
			my $partial = $enc2 =~ s/!$//;
			next if $enc2 eq 'hz' && $s =~ /[^\000-\177]/; # hack for hz
			# put further hacks here...

			my $t = $DEC{$enc2}->decode($s, Encode::FB_QUIET); # FB_CROAK not reliable
			#$t =~ s/[[:cntrl:]]//g;
			if (length $t && !length $s) { # decoding succeeds
				$s = $t;
				$e = $enc2;
				last;
			}
			elsif (length $t && $partial) {
				esc1($s);
				$s = $t . '<?>' . $s;
				$e = $enc2 . '_loss';
				last;
			}
		}
	}
	if ($MSG_ENC{$lp} ne $e) {
		my @line_data = Nlib::hdh((sprintf '0x%x', $lp), 'line', 'data');
		my @tags = grep { !/^lma_/ } map { Nlib::hdh(@line_data, "$_|tags_array") }
			0 .. Nlib::hdh(@line_data, 'tags_count')-1;

		my @ctrl_res = split "\0", $MSG_COLOR{$lp}, -1;
		my $c = 1;
		$s =~ s/\01+/$ctrl_res[$c++]/g;

		Nlib::hdh(@line_data, +{
			message => $s,
			tags_array => (join ',', (($e eq 'x') ? () : ("lma_$e", (sprintf 'lma_0x%x', $rule))), @tags),
		});
		$MSG_ENC{$lp} = $e;
	}
	$MSG_FLT{$lp} = $rule;
}

## line_sig -- decode charset previously replaced and fix up outgoing msgs
## () - signal handler
## $_[2] - line ptr
sub line_sig {
	my @line_data = Nlib::hdh($_[2], 'line', 'data');
	my $lp = oct $_[2];
	$ASYNC_BUF{$lp} = undef if $ASYNC_TIMER; # we are still in async reread loop, mark this line as seen
	return weechat::WEECHAT_RC_OK unless Nlib::hdh(@line_data, 'buffer', 'plugin', 'name') eq 'irc';
	my @tags = map { Nlib::hdh(@line_data, "$_|tags_array") }
		0 .. Nlib::hdh(@line_data, 'tags_count')-1;
	return weechat::WEECHAT_RC_OK unless grep /$nag_tag/i, @tags;

	my $message_c = Nlib::hdh(@line_data, 'message');
	return weechat::WEECHAT_RC_OK unless $message_c =~ /\020/;

	my $message = my $message_nc = weechat::string_remove_color($message_c, "\1");

	if (defined $_[0] && grep { $_ eq 'no_highlight' } @tags) { # might be own msg, $_[0] == undef on history parsing
		my $action_pfx_re = qr//;
		if (grep { $_ eq 'irc_action' } @tags) {
			# XXX might erroneously recode the in-line prefix (utf8 nicks anyone? ircx?!)
			$action_pfx_re = qr/\S+ \K/;
		}
		my $codecs = join '|', map { quotemeta } sort { length $b <=> length $a } keys %DEC;
		if ($message =~ /^\02010\020/) {} # fall through
		elsif ($message =~ s/^$action_pfx_re\020($codecs)\020//) {
			my $dec = $1;

			my @ctrl_res;
			if ($message_nc =~ /\01/) {
				my $id_control = quotemeta $message_nc;
				$id_control =~ s/(\\\01)+/(.+?)/g;
				@ctrl_res = $message_c =~ /^()$id_control()$/;
			}

			$message_nc =~ s/^$action_pfx_re\020\Q$dec\E\020//;
			Encode::_utf8_on($message);
			my $s = $DEC{$dec}->decode($DEC{$dec}->encode($message, Encode::FB_DEFAULT), Encode::FB_DEFAULT);
			my $not_equal = $s ne $message;

			my $c = 1;
			$s =~ s/\01+/$ctrl_res[$c++]/g;

			if ($not_equal && weechat::config_string_to_boolean(weechat::config_get_plugin('encode_warn'))) {
				$s .= ' '.weechat::color('chat_prefix_error').'[warning: lossy encode]';
			}

			Nlib::hdh(@line_data, +{
				message => $s,
				tags_array => (join ',', "lmaout_$dec", ($not_equal ? "lmaout_loss" : ()), @tags),
			});

			return weechat::WEECHAT_RC_OK
		}
	}

	# XXX bad hack: \01* might be sprinkled from colorize_nicks, but will mess up later on color restore
	$message =~ s/\020\01*([[:xdigit:]]+)\01*\020/chr hex $1/ge || return weechat::WEECHAT_RC_OK;

	my @ctrl_res;
	if ($message_nc =~ /\01/) {
		my $id_control = quotemeta $message_nc;
		$id_control =~ s/(\\\01)+/(.+?)/g;
		@ctrl_res = $message_c =~ /^()$id_control()$/;
	}

	if (esc_only($message)) {
		my $c = 1;
		$message =~ s/\01+/$ctrl_res[$c++]/g;
		Nlib::hdh(@line_data, +{ message => $message });
		$ESC_MSG{$lp} = undef;
		return weechat::WEECHAT_RC_OK
	}

	$BYTE_MSGS{$lp} = $message;
	$MSG_COLOR{$lp} = join "\0", @ctrl_res;
	 $MSG_TIME{$lp}	= 0+Nlib::hdh(@line_data, 'date');
	  $MSG_BUF{$lp}	= Nlib::hdh(@line_data, 'buffer', 'name');
	 my ($nick_tag)	= grep s/^nick_//, @tags;
	 $MSG_NICK{$lp}	= $nick_tag//'';
	  $MSG_ENC{$lp}	= 'x';
	  $MSG_FLT{$lp}	= \undef;

	apply_recode($lp);

	if (defined $GC_LIMIT && ++$GC_COUNT > $GC_LIMIT) {
		gc_lines('int');
		$GC_COUNT = 0;
	}

	weechat::WEECHAT_RC_OK
}

## hook_encode_commands -- hook irc commands needed to add encode prefix
## - tag name
sub hook_encode_commands {
	if ($_[0] eq 'privmsg') {
		(weechat::hook_command_run('/me', 'auto_encode_cmd', 'me'),
		 weechat::hook_command_run('/msg', 'auto_encode_cmd', 'msg'),
		 weechat::hook_command_run('/query', 'auto_encode_cmd', 'query'),
		)
	}
	elsif ($_[0] eq 'notice') {
		(weechat::hook_command_run('/notice', 'auto_encode_cmd', 'query'),
		 weechat::hook_command_run('/wallchops', 'auto_encode_cmd', 'wallchops'),
		)
	}
	elsif ($_[0] eq 'topic') {
		(weechat::hook_command_run('/topic', 'auto_encode_cmd', 'topic'),
		)
	}
	elsif ($_[0] eq 'part') {
		(weechat::hook_command_run('/part', 'auto_encode_cmd', 'wallchops'),
		 weechat::hook_command_run('/cycle', 'auto_encode_cmd', 'wallchops'),
		)
	}
	else {
		()
	}
}

# /lma set <time> <network.buffer|*> <nick|*|+> <encodings...>

# 0 network.* iso-user iso
# 0 network.#channel * utf8 --> iso-user always gets iso

# 0 network.* iso-user iso
# 0 network.#channel + utf8 --> iso-user gets utf8 in #channel

## load_config -- unconditionally try to pipe config file to /lma set
sub load_config {
	weechat::mkdir_home('', 0755);
	if (-e $CFG_FILE_NAME) {
		open my $lfh, '<:utf8', $CFG_FILE_NAME || die $!;
		while (<$lfh>) {
			chomp;
			lma_set('conf', $., split ' ', $_)
		}
	}
	weechat::WEECHAT_RC_OK
}

## save_config -- unconditionally try to save config
sub save_config {
	weechat::mkdir_home('', 0755);
	open my $sfh, '>:utf8', $CFG_FILE_NAME || die $!;
	local $, = ' '; local $\ = "\n";
	for (@CFG_TABLE) {
		print $sfh @{$_}{qw(time buf nick)}, @{$_->{charsets}};
	}
	for (@ENCODE_TABLE) {
		print $sfh '-out', $_->{buf}, @{$_->{pat}}, $_->{charset};
	}
	weechat::WEECHAT_RC_OK
}

## display_time -- pretty print time
## $now - current time
## $time - time to display
## returns s/m/h or HH:MM or mm/dd
sub display_time {
	my ($now, $time) = @_;
	my $d = $now - $time;
	if  ($d < 0) {
		"+"
	}
	elsif ($d < 60) {
		"-${d}s"
	}
	elsif ($d < 60 * 60) {
		"-@{[int($d/60)]}m"
	}
	elsif ($d < 60 * 60 * 24) {
		my @lt = localtime $time;
		sprintf '%02d:%02d', $lt[2], $lt[1]
	}
	elsif ($d < 31_556_926) {
		my @lt = localtime $time;
		sprintf '%3s%2d', ucfirst $mon[$lt[4]], $lt[3]
	}
	else {
		'-'
	}
}

## lma_list -- list decode configuration
## () - forwarded command handler
sub lma_list {
	if (@_ > 2) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]} list\" command: $_[2]");
		return weechat::WEECHAT_RC_OK
	}
	my %lengths;
	my $now = time;
	my %header = ( time => (sprintf '%*s', (length $now), 'ts'), buf => 'buf', nick => 'nick', charsets => ['charsets']);
	for my $ent (\%header, @CFG_TABLE) {
		for (qw(time buf nick)) {
			my $len = length $ent->{$_};
			$lengths{$_} = $len unless ($lengths{$_}//0) >= $len
		}
		my $cs_len = length join ' ', @{$ent->{charsets}};
		$lengths{charsets} = $cs_len unless ($lengths{charsets}//0) >= $cs_len;
	}
	my $hdr = sprintf '%*s(%*s)%*s %*s %*s', -$lengths{time}, $header{time}, 5, 'when', (map { -$lengths{$_}, $header{$_} } qw(buf nick)), -$lengths{charsets}, @{$header{charsets}};
	weechat::print('', $hdr);
	weechat::print('', '-'x(length $hdr));
	for my $ent (@CFG_TABLE) {
		weechat::print('', sprintf '%*s %*s %*s %*s'.(' %s'x@{$ent->{charsets}}),
					   $lengths{time}, $ent->{time}, 5, display_time($now, $ent->{time}), (map { -$lengths{$_}, $ent->{$_} } qw(buf nick)), @{$ent->{charsets}});
	}
	if (@CFG_TABLE && @ENCODE_TABLE) {
		weechat::print('', '-'x(length $hdr));
	}

	return weechat::WEECHAT_RC_OK unless @ENCODE_TABLE;

	my %enc_lengths;
	my %enc_header = (buf => 'buf', pat => ['pattern'], charset => 'charset');
	for my $ent (\%enc_header, @ENCODE_TABLE) {
		for (qw(buf charset)) {
			my $len = length $ent->{$_};
			$enc_lengths{$_} = $len unless ($enc_lengths{$_}//0) >= $len
		}
		my $pat_len = length join ' ', @{$ent->{pat}};
		$enc_lengths{pat} = $pat_len unless ($enc_lengths{pat}//0) >= $pat_len;
	}
	my $enc_hdr = sprintf '%*s %*s %*s %*s', -$lengths{time}-6, 'output encodings', -$enc_lengths{buf}, $enc_header{buf}, -$enc_lengths{pat}, @{$enc_header{pat}}, -$enc_lengths{charset}, $enc_header{charset};
	weechat::print('', $enc_hdr);
	weechat::print('', '-'x(length $enc_hdr));
	for my $ent (@ENCODE_TABLE) {
		weechat::print('', sprintf '%*s %*s %*s %*s',
					   -$lengths{time}-6, '', -$enc_lengths{buf}, $ent->{buf}, -$enc_lengths{pat}, (join ' ', @{$ent->{pat}}), -$enc_lengths{charset}, $ent->{charset});
	}
	weechat::WEECHAT_RC_OK
}

## rel_time -- replace m/h/d postfix to negative time with no. of seconds
## $now - current time
## $_[1..$#_] - string to modify
sub rel_time {
	my %td = (m => 60, h => 60 * 60, d => 60 * 60 * 24);
	my $now = shift;
	for (@_) {
		my ($from, $to) = split /(?<!^)-/, $_, 2;
		if (defined $to) {
			rel_time($now, $from, $to);
			$_ = "$from-$to";
		}
		else {
			my @lt = localtime $now;
			s{^([><])?(?:($mon_re)([0-2][1-9]|3[01]))?(?:(?:([01]?[0-9]|2[0-3]):([0-5][0-9]))(?::([0-5][0-9]))?)?$}{
				my ($pfx, $mon, $day, $hr, $min, $sec) = ($1//'', $mon{lc $2}//$lt[4], $3//$lt[3], $4//$lt[2], $5//$lt[1], $6//$lt[0]);
				my $yr = $lt[5];
				my $day_back;
				if ($mon > $lt[4] || ($mon == $lt[4] && $day > $lt[3])) { --$yr }
				elsif ($mon == $lt[4] && $day == $lt[3] &&
						   ($hr > $lt[2] ||
								($hr == $lt[2] && ($min > $lt[1] ||
													   ($min == $lt[1] && $sec > $lt[0]))))) { $day_back = 1 }
				my $lt = timelocal($sec, $min, $hr, $day, $mon, $yr);
				$lt -= 60 * 60 * 24 if $day_back;
				$pfx.$lt
			}ie ||
			s/(?<!-)-(\d+)([mhd])/-($1 * $td{$2})/eg;			
		}
	}
}

## lma_print_fmt -- print line of rule table with display_time and message prefix
## $now - time to use as base for calculations
## $msg - message prefix to show
## $time - timestamp of rule
## @rest - other string fields to print
sub lma_print_fmt {
	my ($now, $msg, $time, @rest) = @_;
	weechat::print('', join ' ', "$msg:", $time, "(@{[display_time($now, $time)]})", @rest)
}

## update_table2 -- create rule table from settings table
sub update_table2 {
	@CFG_TABLE_2 =
	sort {
		$b->{prio} <=> $a->{prio} ||
			($a->{prio} && $b->prio ? (
				$b->{buf_len} <=> $a->{buf_len} ||
				$a->{_}{buf} cmp $b->{_}{buf} ||
				$b->{nick_len} <=> $a->{nick_len} ||
				$a->{_}{nick} cmp $b->{_}{nick}) : (
					$b->{nick_len} <=> $a->{nick_len} ||
					$a->{_}{nick} cmp $b->{_}{nick} ||
					$b->{buf_len} <=> $a->{buf_len} ||
					$a->{_}{buf} cmp $b->{_}{buf})) ||
						$b->{_}{time} <=> $a->{_}{time}
	}
	map {
		+{
			buf_len => (2 * (length $_->{buf}) - 3 * ($_->{buf} =~ y/*//)),
			nick_len => (2 * (length $_->{nick}) - 3 * ($_->{nick} =~ y/*//) - ($_->{nick} =~ /\+$/)),
			prio => !!($_->{nick} =~ /\+$/),
			buf_re => do {
				my $buf = $_->{buf};
				wildcard_to_re($buf);
				qr/^$buf$/i },
			nick_re => do {
				my $nick = $_->{nick};
				$nick =~ s/\+$//;
				$nick = '*' unless length $nick;
				wildcard_to_re($nick);
				qr/^$nick$/i },
			'_' => $_,
		}
	} @CFG_TABLE
}

## lma_del_out -- delete output encoding
## $_[0] - 'int' if internal
## $buf - target specification
## $glob - set if last param starts with -g XXX
## @pat - match pattern
sub lma_del_out {
	my (undef, $buf, $glob, @pat) = @_;
	my $internal = $_[0] eq 'int';
	if ($glob) {
		wildcard_to_re($buf, @pat);
	}
	else {
		$_ = quotemeta for $buf, @pat;
	}
	my $pat_re = join '\s+', @pat;
	my $num_cfg = @ENCODE_TABLE;
	@ENCODE_TABLE = sort { $a->{buf} cmp $b->{buf} || (join ' ', @{$a->{pat}}) cmp (join ' ', @{$b->{pat}}) }
		grep {
			!(
				$_->{buf} =~ /^\s*$buf\s*$/i && (join ' ', @{$_->{pat}}) =~ /^\s*$pat_re\s*$/i)
		}
		grep { length $_->{charset} }
			@ENCODE_TABLE;
	update_enc_table();
	weechat::print('', "Removed @{[$num_cfg-@ENCODE_TABLE]} entries from @{[SCRIPT_NAME]} list") unless $internal;
	weechat::WEECHAT_RC_OK
}

sub update_enc_table {
	@ENCODE_TABLE2 =
	sort {
		$b->{buf_len} <=> $a->{buf_len} ||
		$a->{_}{buf} cmp $b->{_}{buf} ||
		$b->{pat_len} <=> $a->{pat_len} ||
		$a->{pat} cmp $b->{pat}
	}
	map {
		my $pat = join ' ', @{$_->{pat}};
		+{
			pat => $pat,
			buf_len => (2 * (length $_->{buf}) - 3 * ($_->{buf} =~ y/*//)),
			pat_len => (2 * (length $pat)      - 3 * ($pat =~ y/*//)),
			buf_re => do {
				my $buf = $_->{buf};
				wildcard_to_re($buf);
				qr/^$buf$/i },
			pat_re => do {
				my @pat = @{$_->{pat}};
				wildcard_to_re(@pat);
				for (@pat) {
					s/\.\*/\\S*/g unless $_ eq '.*'; # wasn't *
					s/(?:\\S\*){2,}/.*/g; # reverse with **
				}
				my $pat_re = join '\s+', @pat;
				qr/^$pat_re$/i },
			'_' => $_,
		}
	} @ENCODE_TABLE
}

## lma_set_out -- modify output encoding
## $_[0] - 'conf' if called from config
## $cs - charset
## $buf - target specification
## @pat - match pattern
sub lma_set_out {
	my (undef, $cs, $buf, @pat) = @_;
	my $conf = ($_[0]//'') eq 'conf';
	$cs//='';
	lma_del('int', undef, '-out', $buf, @pat);
	push @ENCODE_TABLE, +{ buf => $buf, pat => \@pat, charset => $cs };
	my $msg = length $cs ? 'added' : 'removed';
	weechat::print('', join ' ', "$msg:", '-out', $buf, @pat, $cs) unless $conf;

	@ENCODE_TABLE = sort { $a->{buf} cmp $b->{buf} || (join ' ', @{$a->{pat}}) cmp (join ' ', @{$b->{pat}}) }
		grep { length $_->{charset} }
			@ENCODE_TABLE;
	update_enc_table();
	weechat::WEECHAT_RC_OK
}

## lma_set -- add or modify a rule entry
## () - forwarded command handler
## $_[0] - 'conf' if called from config load
## $time - timestamp
## $buf - buffer
## $nick - nick
## @charsets - list of charsets to try in order
sub lma_set {
	my (undef, undef, $time, $buf, $nick, @charsets) = @_;
	my $conf = ($_[0]//'') eq 'conf';
	my $conf_err = ($conf ? ", @{[SCRIPT_NAME]}.conf line $_[1]" : '');
	unless (defined $nick) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."@{[SCRIPT_NAME]}: too few arguments for \"@{[CMD_NAME]} set\" command$conf_err");
		return weechat::WEECHAT_RC_OK
	}
	my $now = time;
	rel_time($now, $time);
	my ($out_p, $recode_p);
	if (lc $time eq '-out') {
		$out_p = 1;
	}
	elsif ($time !~ /^-?\d+$/) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: incorrect number: $time in \"@{[CMD_NAME]} set\" command$conf_err");
		return weechat::WEECHAT_RC_OK
	}
	else {
		$recode_p = 1;
		$time += $now unless $time > 0;
	}

	my @out_pattern;
	if ($out_p) {
		my $cs = pop @charsets;
		@out_pattern = ($nick, @charsets);
		@charsets = $cs//();
	}
	else {
		my $nick_p = $nick;
		$nick_p =~ s/\+$//;
		$nick_p = '*' unless length $nick_p;
		@out_pattern = (($nick_p ne '*' ? $nick_p.Nlib::fu8on(weechat::config_string(weechat::config_get('weechat.completion.nick_completer'))) : ()), '*');
	}
	my ($out_next, $out_charset);
	my %enc_seen;
	@charsets = grep { defined }
		map {
			if (!$out_p && lc $_ eq '-out') {
				if (defined $out_next) {
					weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: multiple -out flags in \"@{[CMD_NAME]} set\" command$conf_err");
					return weechat::WEECHAT_RC_OK;
				}
				elsif (grep { $_->{buf} eq $buf && $_->{nick} eq $nick && $_->{time} > $time } @CFG_TABLE) {
					weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: -out flag not allowed for recodes in the past in \"@{[CMD_NAME]} set\" command$conf_err");
					return weechat::WEECHAT_RC_OK;
					
				}
				$out_next = 1;
				undef
			}
			else {
				my $partial_decode;
				if ($_ ne 'x') {
					$partial_decode = s/!$//;
					my $dec = Encode::find_encoding($_);
					unless (defined $dec) {
						weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown encoding: $_ in \"@{[CMD_NAME]} set\" command$conf_err");
						return weechat::WEECHAT_RC_OK;
					}
					$_ = $dec->name;
					$DEC{$_} //= $dec;
				}
				$out_charset = $_ if $out_p || $out_next;
				$out_next = 0 if $out_next;
				$partial_decode and $_ .= '!';
				$enc_seen{$_}++ ? undef : $_
			}
		} @charsets;
	if ($out_next) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: -out flag without encoding in \"@{[CMD_NAME]} set\" command$conf_err");
		return weechat::WEECHAT_RC_OK;
	}
	elsif ($out_p) { # only setting out charset, not decode table
		return lma_set_out($_[0], $out_charset, $buf, @out_pattern);
	}
	lma_del('int', undef, $time, $buf, $nick);
	my (@ent) = sort { $b->{time} <=> $a->{time} } grep { $_->{buf} eq $buf && $_->{nick} eq $nick } @CFG_TABLE;
	my ($ent_before) = grep { $_->{time} < $time } @ent;
	my ($ent_after) = grep { $_->{time} > $time } reverse @ent;
	if ($ent_before && (join ' ', @{$ent_before->{charsets}}) eq (join ' ', @charsets)) {
		lma_print_fmt($now, 'already existing', @{$ent_before}{qw(time buf nick)}, @{$ent_before->{charsets}}) unless $conf;
		return weechat::WEECHAT_RC_OK
	}
	my $msg = 'added';
	if ($ent_after && (join ' ', @{$ent_after->{charsets}}) eq (join ' ', @charsets)) {
		lma_del('int', undef, @{$ent_after}{qw(time buf nick)});
		$msg = 'moved';
	}
	$msg = 'removed' unless @charsets;

	push @CFG_TABLE, +{ time => $time, buf => $buf, nick => $nick, charsets => \@charsets };
	lma_print_fmt($now, $msg, $time, $buf, $nick, @charsets) unless $conf;

	@CFG_TABLE = sort { $a->{buf} cmp $b->{buf} || $a->{nick} cmp $b->{nick} || $a->{time} <=> $b->{time} }
		grep { @{$_->{charsets}} }
			@CFG_TABLE;
	if ($out_charset) {
		lma_set_out($_[0], $out_charset, $buf, @out_pattern);
	}
	update_table2();
	update_all_lines() unless $conf;
	weechat::WEECHAT_RC_OK
}

# /lma del >time * *

## wildcard_to_re -- convert * to .* and quotemeta everything else
## @_ - list of strings to modify (inplace)
sub wildcard_to_re {
	for (@_) {
		$_ = join '', map {
			if ($_ eq '*') { '.*' }
			else {
				my $s = $_;
				$s =~ s/\\([*\\])/$1/g;
				quotemeta $s
			}
		} split /((?<!\\)[*])/, $_;
	}
}

## lma_del -- delete entry from list
## () - forwarded command handler
## $_[0] - if 'int', be quiet
## $time - timestamp
## $buf - buffer name
## $nick - nick
## $glob - enable wildcards if '-g'
sub lma_del {
	my (undef, undef, $time, $buf, $nick, $glob, $invalid) = @_;
	my $internal = $_[0] eq 'int';
	unless (defined $nick) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."@{[SCRIPT_NAME]}: too few arguments for \"@{[CMD_NAME]} del\" command");
		return weechat::WEECHAT_RC_OK
	}
	elsif (lc $time eq '-out') {
		return lma_del_out($_[0], $buf, (!$internal && @_ > 5 && $_[-1] =~ /^-g/i ? pop : undef), @_[4..$#_]);
	}
	elsif (defined $invalid) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."@{[SCRIPT_NAME]}: too many arguments for \"@{[CMD_NAME]} del\" command");
		return weechat::WEECHAT_RC_OK
	}
	my $globs = defined $glob;
	if ($globs && $glob !~ /^-g/i) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]} del\" command: $glob");
		return weechat::WEECHAT_RC_OK
	}
	my $now = time;
	rel_time($now, $time) unless $internal;
	if ($time !~ /^(?:[><]?-?\d+|[*]|-?\d+--?\d+)$/) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: incorrect number: $time in \"@{[CMD_NAME]} set\" command");
		return weechat::WEECHAT_RC_OK
	}
	my ($time_gt, $time_lt, $time_all, $time_range, $time_from, $time_to);
	if ($time =~ s/^>//) {
		$time_gt = 1
	}
	elsif ($time =~ s/^<//) {
		$time_lt = 1
	}
	elsif ($time eq '*') {
		$time_all = 1;
		$time = 0
	}
	elsif (($time_from, $time_to) = $time =~ /^(.*\d)-(.*\d)$/) {
		$time_range = 1;
		$time = 0;
	}
	for ($time, $time_from, $time_to) {
		$_ += $now unless !defined || $_ > 0;
	}
	if ($globs) {
		wildcard_to_re($buf, $nick);
	}
	else {
		$_ = quotemeta for $buf, $nick;
	}
	my $num_cfg = @CFG_TABLE;
	@CFG_TABLE = sort { $a->{buf} cmp $b->{buf} || $a->{nick} cmp $b->{nick} || $a->{time} <=> $b->{time} }
		grep {
			!(
				($time_all ||
				($time_gt && $_->{time} >= $time) ||
				($time_lt && $_->{time} <= $time) ||
				($time_range && $_->{time} >= $time_from && $_->{time} <= $time_to) ||
				 $_->{time} == $time) &&
					 $_->{buf} =~ /^\s*$buf\s*$/i && $_->{nick} =~ /^\s*$nick\s*$/i)
		}
		grep { @{$_->{charsets}} }
			@CFG_TABLE;
	update_table2();
	weechat::print('', "Removed @{[$num_cfg-@CFG_TABLE]} entries from @{[SCRIPT_NAME]} list") unless $internal;
	update_all_lines() unless $internal;
	weechat::WEECHAT_RC_OK
}

## lma_wee_save -- handle weechat /save or /reload
## () - command_run handler
## $_[0] - forward to which command
## $_[1] - buffer pointer
## $_[2] - command
sub lma_wee_save {
	if ($_[2] =~ s/\s+luanma(?:\s+|$)/ /i) {
		weechat::command($_[1], $_[2]) unless $_[2] =~ /\/$_[0]\s*$/i;	
		{ no strict 'refs'; &{"lma_$_[0]"}(); }
		weechat::WEECHAT_RC_OK_EAT
	}
	elsif ($_[2] =~ /\/$_[0]\s*$/i) {
		weechat::command($_[1], $_[2]);
		{ no strict 'refs'; &{"lma_$_[0]"}(); }
		weechat::WEECHAT_RC_OK_EAT
	}
	else {
		weechat::WEECHAT_RC_OK
	}
}

## lma_save -- command handler to save config
## () - command handler
sub lma_save {
	if (@_ > 2) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]} save\" command: $_[2]");
		return weechat::WEECHAT_RC_OK
	}
	save_config();
	weechat::print('', "Options saved to @{[SCRIPT_NAME]}.conf");
	weechat::WEECHAT_RC_OK
}

## lma_reload -- reload config file
## () - command handler
sub lma_reload {
	if (@_ > 2) {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]} reload\" command: $_[2]");
		return weechat::WEECHAT_RC_OK
	}
	@CFG_TABLE = @CFG_TABLE_2 = ();
	load_config();
	update_all_lines(); # load_config doesn't do this for us
	weechat::print('', "Options reloaded from @{[SCRIPT_NAME]}.conf");
	weechat::WEECHAT_RC_OK
}

## lma_forget -- forget everything about messages, forget all raw and all esc messages
## () - forwarded command handler
sub lma_forget {
	unless (@_ == 3 && lc $_[2] eq '-yes') {
		weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]} forget\" command");
		return weechat::WEECHAT_RC_OK
	}
	%$_ = () for @STO;
	weechat::print('', 'forgotten');
	weechat::WEECHAT_RC_OK
}

## lma_list_rules -- list internal rules and pointers (for debug and /debug tags)
## () - command handler
sub lma_list_rules {
	my $now = time;
	for (@CFG_TABLE_2) {
		lma_print_fmt($now, (sprintf '0x%x', $_), @{$_->{_}}{qw(time buf nick)}, @{$_->{_}{charsets}});
	}
	for (@ENCODE_TABLE2) {
		weechat::print('', join ' ', ' 'x10, '-out', $_->{_}{buf}, @{$_->{_}{pat}}, $_->{_}{charset});
	}
	weechat::WEECHAT_RC_OK
}

## lma_cmd -- main command handler and dispatcher
## () - command handler
## $_[2] - arguments
sub lma_cmd {
	Encode::_utf8_on($_[2]);
	my @args = split ' ', $_[2];

	my %disp = (
		set    => \&lma_set,
		add    => \&lma_set,
		list   => \&lma_list,
		save   => \&lma_save,
		reload => \&lma_reload,
		del    => \&lma_del,
##
		forget 	   => \&lma_forget,
		list_rules => \&lma_list_rules,
		gc 		   => \&gc_lines,
	   );

	@args = 'list' unless @args;
	my $cmd = lc $args[0];

	return $disp{$cmd}(@_[0..1], @args[1..$#args])
		if exists $disp{$cmd};

	weechat::print('', Nlib::fu8on(weechat::prefix('error'))."Error: unknown option for \"@{[CMD_NAME]}\" command: $args[0]");
	return weechat::WEECHAT_RC_OK;
}

sub sew_and_back {
	my $msg = join ' ', " [@{[SCRIPT_NAME]}]", @_;
	print STDERR $msg, "\b"x length $msg;
}

## for_all_lines -- do something for all lines
## $_[0] - sub routine
sub for_all_lines(&) {
AO:	for (my @buffers = Nlib::hdh('gui_buffers', 'buffer');
		 $buffers[0];
		 @buffers = Nlib::hdh(@buffers, '!var_next')) {
		for (my @lines = Nlib::hdh(@buffers, 'own_lines', 'first_line');
			 $lines[0];
			 @lines = Nlib::hdh(@lines, '!var_next')) {
			my $lp = oct $lines[0];
			$_[0]($lp, @lines);
		}
	}
}

## FAnext -- next for_all_lines
sub FAnext() {
	no warnings 'exiting';
	next
}

## FAlast -- last for_all_lines
sub FAlast() {
	no warnings 'exiting';
	last AO
}

## async_reread_lines -- reread lines asynchronously
## () - timer handler
sub async_reread_lines {
	sew_and_back('PARSING LINES');
	my $i = $ASYNC_PARSE;
	local $GC_LIMIT;
	for_all_lines {
		my ($lp, @lines) = @_;
		FAnext if exists $ASYNC_BUF{$lp};
		line_sig(undef, undef, @lines);
		FAlast unless --$i;
	};
	if ($i) { # finished, still $i left
		weechat::unhook($ASYNC_TIMER);
		$ASYNC_TIMER = undef;
		%ASYNC_BUF = ();
	}
	weechat::command('', '/wait 200ms /window refresh');
	weechat::WEECHAT_RC_OK
}

## reread_lines -- pipe all lines in weechat through line_sig (used on load)
sub reread_lines {
	sew_and_back('PARSING LINES');
	my $i = 1;
	local $GC_LIMIT;
	for_all_lines {
		my (undef, @lines) = @_;
		sew_and_back('PARSING LINES', $i) unless ++$i % $PARSE_STATS;
		line_sig(undef, undef, @lines)
	};
	weechat::command('', '/window refresh');
}

## update_all_lines -- loop over all lines in weechat and apply new ruleset
sub update_all_lines {
	if ($ASYNC_TIMER && $ASYNC_TIMER == 1) { # ondemand parser
		delete @ASYNC_BUF{keys %BYTE_MSGS};
		ondemand_buffers();
	}
	else {
		sew_and_back('PARSING LINES');
		for_all_lines {
			my $lp = shift;
			apply_recode($lp)
				if exists $BYTE_MSGS{$lp};
		};
		weechat::command('', '/window refresh');
	}
}

# buffer lines last_line prev_line|data
# window scroll buffer
# window scroll start_line next_line|data
# window win_chat_height

## ondemand_window -- signal handler that gets called on window
## $_[2] - window that changed
sub ondemand_window {
	my @window = Nlib::hdh($_[2], 'window');
	my @scroll = Nlib::hdh(@window, 'scroll');
	my @buffer = Nlib::hdh(@scroll, 'buffer');
	my $dir;
	my @lines = Nlib::hdh(@scroll, 'start_line');
	if ($lines[0]) {
		$dir = '!var_next';
	}
	else {
		@lines = Nlib::hdh(@scroll, 'buffer', 'lines', 'last_line');
		$dir = '!var_prev';
	}
	my $max = Nlib::hdh(@window, 'win_chat_height'); # rough approx. of lines that need processing
	for (;
		 $lines[0];
		 @lines = Nlib::hdh(@lines, $dir)) {
		next unless Nlib::hdh(@lines, 'data', 'displayed');
		my $lp = oct $lines[0];
		if (exists $BYTE_MSGS{$lp} && !exists $ASYNC_BUF{$lp}) {
			apply_recode($lp);
			$ASYNC_BUF{$lp} = undef;
		}
		elsif (!exists $ASYNC_BUF{$lp}) {	
			line_sig(undef, undef, @lines);
		}
		last unless --$max;
	}
	weechat::WEECHAT_RC_OK
}

## ondemand_buffers -- signal handler that gets called on all buffers
## $_[2] - buffer that changed, or all windows if undef
sub ondemand_buffers {
	for (my @windows = Nlib::hdh('gui_windows', 'window');
		 $windows[0];
		 @windows = Nlib::hdh(@windows, '!var_next')) {
		my @buffer = Nlib::hdh(@windows, 'scroll', 'buffer');
		next if defined $_[2] && $buffer[0] ne $_[2];
		ondemand_window(undef, undef, $windows[0]);
	}
	weechat::WEECHAT_RC_OK
}

## ondemand_commands_hook -- redraw buffers after certain command
## () - command_run handler
## $_[1] - buffer
## $_[2] - command
sub ondemand_commands_hook {
	weechat::command($_[1], $_[2]);
	ondemand_buffers();
	weechat::WEECHAT_RC_OK_EAT
}

## parse_ondemand_init -- initialize on-demand parser
sub parse_ondemand_init {
	Nlib::hook_dynamic(signal => buffer_lines_hidden => 'ondemand_buffers', ''); #called for all affected buffers?
	Nlib::hook_dynamic(signal => buffer_switch       => 'ondemand_buffers', ''); #buffer switched to
	Nlib::hook_dynamic(signal => window_scrolled     => 'ondemand_window', ''); #
	Nlib::hook_dynamic(signal => window_zoomed       => 'ondemand_window', '');
	Nlib::hook_dynamic(command_run => "/window $_" => 'ondemand_commands_hook', '')
			for qw(split* resize* balance merge* refresh);
	ondemand_buffers();
}

## parse_ondemand_deinit -- stop on-demand parser
sub parse_ondemand_deinit {
	Nlib::unhook_dynamic("/window $_" => 'ondemand_commands_hook')
			for qw(split* resize* balance merge* refresh);
	Nlib::unhook_dynamic(window_zoomed       => 'ondemand_window');
	Nlib::unhook_dynamic(window_scrolled     => 'ondemand_window');
	Nlib::unhook_dynamic(buffer_switch       => 'ondemand_buffers');
	Nlib::unhook_dynamic(buffer_lines_hidden => 'ondemand_buffers');
	@ASYNC_BUF{keys %BYTE_MSGS} = ();
}

## gc_lines -- remove raw lines from cache that are no longer valid in weechat
## () - can be forwarded command handler
## $_[0] - quiet if 'int'
sub gc_lines {
	my %lines_seen;
	@lines_seen{keys %BYTE_MSGS} = ();
	for_all_lines {
		my $lp = shift;
		delete $lines_seen{$lp};
	};
	delete @{$_}{keys %lines_seen} for @STO;
	weechat::print('', "gc'd @{[scalar keys %lines_seen]} lps") unless $_[0] eq 'int';
	weechat::WEECHAT_RC_OK
}

## restore_lines -- put back all lines to their raw form (before unloading)
sub restore_lines {
	sew_and_back('PARSING LINES');
	local (@CFG_TABLE, @CFG_TABLE_2);
	for_all_lines {
		my ($lp, @lines) = @_;
		if (exists $BYTE_MSGS{$lp}) {
			apply_recode($lp);
		}
		elsif (exists $ESC_MSG{$lp}) {
			my @line_data = Nlib::hdh(@lines, 'data');
			my $s = Nlib::hdh(@line_data, 'message');
			$s =~ s/\020/\02010\020/g;
			Nlib::hdh(@line_data, +{ message => $s });
		}
	};
	weechat::command('', '/window refresh');
}

## default_options -- set up default option values on start and when unset
## () - config handler if @_ is set
sub default_options {
	my %defaults = (
		tags => 'notice privmsg topic 332',
		parser => 'ondemand', # async, full
		encode_warn => 'on',
	);
	for (keys %defaults) {
		weechat::config_set_plugin($_, $defaults{$_})
			unless weechat::config_is_set_plugin($_);
	}
	@nags = split ' ', lc weechat::config_get_plugin('tags');
	$nag_tag = '^' .(join '|', map { quotemeta }
						 map { "irc_$_" }
							 sort { length $b <=> length $a }
								 @nags). '$';
	my %new_nag_modifiers;
	for (@nags) {
		if (exists $nag_modifiers{$_}) {
			$new_nag_modifiers{$_} = delete $nag_modifiers{$_};
		}
		else {
			$new_nag_modifiers{$_} = [
				weechat::hook_modifier("irc_in_$_", 'irc_in_mod', ''),
				weechat::hook_modifier("irc_out_$_", 'irc_out_mod', ''),
				hook_encode_commands($_),
			   ];
		}
	}
	for (keys %nag_modifiers) {
		weechat::unhook($_) for @{delete $nag_modifiers{$_}};
	}
	%nag_modifiers = %new_nag_modifiers;
	my $last_parser = defined $ASYNC_TIMER ? $ASYNC_TIMER ? $ASYNC_TIMER == 1 ? 'ondemand'
											: 'async_in_progress'
							: 'loading'
					: 'full_or_finished';
	my $new_parser = lc weechat::config_get_plugin('parser');
	if ($last_parser eq 'async_in_progress' && $new_parser ne 'async') {
		weechat::unhook($ASYNC_TIMER);
	}
	elsif ($last_parser eq 'full_or_finished' && $new_parser eq 'ondemand') {
		for_all_lines {
			my $lp = shift;
			$ASYNC_BUF{$lp} = undef;
		};
	}
	elsif ($last_parser eq 'ondemand' && $new_parser ne 'ondemand') {
		parse_ondemand_deinit();
	}
	if ($new_parser eq 'ondemand') {
		unless ($last_parser eq 'ondemand') {
			$ASYNC_TIMER = 1;
			parse_ondemand_init();
		}
	}
	elsif ($new_parser eq 'async') {
		unless ($last_parser eq 'async_in_progress' || $last_parser eq 'full_or_finished') {
			$ASYNC_TIMER = weechat::hook_timer(100, 0, 0, 'async_reread_lines', '');
		}
	}
	else {
		if ($last_parser ne 'full_or_finished') {
			$ASYNC_TIMER = undef;
			%ASYNC_BUF = ();
			reread_lines();
		}
	}
	weechat::WEECHAT_RC_OK
}

sub init_luanma {
	$GC_COUNT = 0;
	load_config();
	$DEC{utf8} = Encode::find_encoding('utf8');
	$ASYNC_TIMER = 0;
	default_options();
	my $sf = SCRIPT_FILE;
	for (Nlib::get_settings_from_pod($sf)) {
		weechat::config_set_desc_plugin($_, Nlib::get_desc_from_pod($sf, $_));
	}
	weechat::WEECHAT_RC_OK
}

sub stop_luanma {
	lma_save()
		if weechat::config_boolean(weechat::config_get('weechat.plugin.save_config_on_unload'));
	restore_lines();
	weechat::WEECHAT_RC_OK
}
