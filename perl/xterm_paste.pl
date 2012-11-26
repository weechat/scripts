use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;

# xterm_paste.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

our $XTERM_COMPATIBLE = 'rxvt-uni';

use MIME::Base64;

use constant SCRIPT_NAME => 'xterm_paste';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.1', 'GPL3', 'Bind Xterm paste to command', 'stop_paste', '') || return;
sub SCRIPT_FILE() {
	my $infolistptr = weechat::infolist_get('perl_script', '', SCRIPT_NAME);
	my $filename = weechat::infolist_string($infolistptr, 'filename') if weechat::infolist_next($infolistptr);
	weechat::infolist_free($infolistptr);
	return $filename unless @_;
}

{
package Nlib;
# this is a weechat perl library
use strict; use warnings;

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

					my $code = qq{
						local \$[=1;
						\$list{"\Q$key\E"}$idx = \$r
					};
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

1
}

weechat::hook_command(SCRIPT_NAME, 'get xterm clipboard', '', '', '', 'paste_cmd', '');

our $PASTE_REPLY = '';
our $ORIG_KEY_CMD = undef;
our $PASTE_TIMEOUT;

sub request_clip {
	my ($stor) = @_;
	$stor = '' unless $stor;
	my $xterm_osc = "\e]52;$stor;?\a";
	my $compatible_terms = join '|', map { split /[,;]/ } split ' ',
		$XTERM_COMPATIBLE;
	print STDERR $xterm_osc if $ENV{'TERM'} =~ /^xterm|$compatible_terms/;
	if ($ENV{'TMUX'}) {
		chomp(my @tmux_clients = `tmux lsc`);
		my $active_term;
		my $last_time = 0;
		for (@tmux_clients) {
			my ($path, $rest) = split ':', $_;
			next unless $rest =~ / (?:xterm|$compatible_terms)/;
			my $atime = -A $path;
			if ($last_time >= $atime) {
				$last_time = $atime;
				$active_term = $path;
			}
		}
		if ($active_term) {
			open my $pty, '>>', $active_term;
			print $pty $xterm_osc;
		}
	}
}

sub paste_cmd {
	my (undef, undef, $args) = @_;
	if ($args =~ /accept/) { insert_paste() }
	else { get_paste() }
}

sub get_paste {
	$PASTE_TIMEOUT = weechat::hook_timer(1000, 0, 1, 'paste_input_stop', '');
	weechat::hook_signal_send('input_flow_free', weechat::WEECHAT_HOOK_SIGNAL_INT, 1);
	Nlib::hook_dynamic('modifier', 'input_text_content', 'paste_evt2', '');
	($ORIG_KEY_CMD) = map { $_->{command} } grep { $_->{key} eq 'ctrl-G' }
		Nlib::i2h('key');
	weechat::command('', "/mute /key bind ctrl-G /@{[SCRIPT_NAME]} accept");
	request_clip();
	weechat::WEECHAT_RC_OK
}

sub insert_paste {
	my $paste;
	($paste, $PASTE_REPLY) = ($PASTE_REPLY, '');
	paste_input_stop();
	$paste =~ s/\]?52;.*;$// ||
	$paste =~ s/.*;//;
	my $decode = decode_base64($paste); $decode =~ s/\n/\\x0a/g;
	weechat::command(weechat::current_buffer(), "/input insert $decode");
	weechat::WEECHAT_RC_OK
}

sub paste_input_stop {
	my $leftover;
	($leftover, $PASTE_REPLY) = ($PASTE_REPLY, '');
	if ($PASTE_TIMEOUT) {
		weechat::unhook($PASTE_TIMEOUT);
		$PASTE_TIMEOUT = undef;
	}
	if ($ORIG_KEY_CMD) { weechat::command('', "/mute /key bind ctrl-G $ORIG_KEY_CMD"); }
	else { weechat::command('', '/mute /key reset ctrl-G'); }
	$ORIG_KEY_CMD = undef;
	Nlib::unhook_dynamic('input_text_content', 'paste_evt2');
	if (length $leftover) {
		$leftover =~ s/\\/\\\\/g;
		weechat::command(weechat::current_buffer(), "/input insert $leftover");
	}
	weechat::hook_signal_send('input_flow_free', weechat::WEECHAT_HOOK_SIGNAL_INT, 0);
	weechat::WEECHAT_RC_OK
}

sub paste_evt2 {
	Encode::_utf8_on($_[3]);
	my $buf = weechat::current_buffer();
	my $npos = weechat::buffer_get_integer($buf, 'input_pos')-1;
	$PASTE_REPLY .= substr $_[3], $npos, 1, '';
	weechat::buffer_set($buf, 'input_pos', $npos);
	$_[3]
}

sub stop_paste {
	paste_input_stop() if $PASTE_TIMEOUT;
	weechat::WEECHAT_RC_OK
}
