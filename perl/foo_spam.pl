#! /usr/bin/env perl
#
# foo_spam - Prints the currently playing song from foobar2000.
# 
# Copyright (c) 2009-2010, Diogo Franco <diogomfranco@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

use warnings;
use strict;
use utf8;
use Encode;

use Net::Telnet;
use File::Path;
use Time::HiRes qw(usleep);

BEGIN {
	*HAVE_XCHAT = Xchat->can('register') ? sub {1} : sub {0};
	*HAVE_IRSSI = Irssi->can('command_bind') ? sub{1} : sub{0};
	*HAVE_WEECH = weechat->can('register') ? sub {1} : sub {0};
}

my $ver = '0.6.1';
my %info = (
	author      => 'Kovensky',
	contact     => '#shameimaru@irc.rizon.net',
	url         => 'http://repo.or.cz/w/foo_spam.git',
	name        => 'foo_spam',
	description => 'Prints the currently playing song from foobar2000.',
	license     => 'ISC'
);

if (HAVE_IRSSI) {
	our $VERSION = $ver;
	our %IRSSI = %info;
}

Xchat::register($info{name}, $ver, $info{description}, \&close_telnet) if HAVE_XCHAT;
weechat::register($info{name}, $info{author}, $ver, $info{license}, $info{description}, 'close_telnet', 'UTF-8') if HAVE_WEECH;
# ChangeLog:
# 0.6.1 - Added weechat support.
# 0.6   - Backwards incompatible version. Changes the format syntax, documents functions, implement some others.
# 0.5.2 - Added discnumber and totaldiscs tags. Changed default format. Silences a warning when a function ends on ",)". Fixed two warnings in the $if family.
# 0.5.1 - Fixed $if, $if2, $and, $or and $xor behavior on certain strings.
# 0.5   - Support subfunctions and tags with underlines. Changed some other details.
# 0.4   - Fixed UTF-8 corruption issues. Allow the user to specify a comment when using /aud by giving it as an argument. Document build_output.
# 0.3.2 - Change the method used to read foobar2000's response. The previous method would hang once in a while.
# 0.3.1 - Change default settings to avoid breakage if a track has | on one of the tags. Update documentation.
# 0.3   - Allow customization of the format string. Changed method of desync handling.
# 0.2.2 - Fix desync issues if foobar takes "too long" to respond. Added codec and bitrate to the output.
# 0.2.1 - Forgot to handle one error case on the telnet connection.
# 0.2   - Changed the recommended string and output. Fixed my wrong XChat API usage. Changed the way the telnet connection is handled.
# 0.1   - First version

# Known Bugs:
# Doesn't support tags that are equal to "?" (foo_controlserver limitation).

# TODO:
# Replace the current format syntax by foobar2000's title format

our $telnet_open    = 0;
our $telnet         = undef;
our $default_format = <<'EOF';
$left(%_foobar2000_version%,10) ($replace(%_foobar2000_version%,foobar2000 ,)):
 [%album artist% ]'['[%date% ][%album%][ #[%discnumber%.]%tracknumber%[/[%totaldiscs%.]%totaltracks%]]']'
 [%track artist% - ]%title% '['%playback_time%[/%length%]']'[ %bitrate%kbps][ %codec%[ %codec_profile%]][ <-- %comment%]
EOF
$default_format =~ s/\R//g;
our $format         = $default_format;
our %heap;

our $setting_file   = undef; # Only used by Xchat

sub open_telnet {
	$telnet = new Net::Telnet(Port => 3333, Timeout => 10, Errmode => 'return') if not defined($telnet);
	$telnet_open = $telnet->open("localhost");
	unless($telnet_open) {
		irc_print("Error connecting to foobar2000! Make sure fb2k is running.");
		irc_print("Also check if foo_controlserver is properly configured.");
	}
	return $telnet_open;
}

sub close_telnet {
	if($telnet_open) {
		$telnet_open = 0;
		$telnet->put("exit\n");
		$telnet->close;
	}
}

sub get_track_info {
	return undef unless open_telnet();

	my $line = undef;

	unless (defined($telnet->print("trackinfo"))) {
		close_telnet();
		return undef unless open_telnet();
	}

	my @result = $telnet->waitfor(Match => '/11[123]\|+.+?\|+.+?\|+(?!0\.[0-5][0-9]).*/', Timeout => 5);

	$line = $result[1] if @result;
	
	close_telnet();
	
	unless($line) {
		irc_print("Error retrieving status from foobar2000!");
		return undef;
	}
	
	unless (eval { $line = decode("UTF-8", $line, Encode::FB_CROAK) }) {
		irc_print("Error: line is not valid UTF-8. Check foo_controlserver's settings.");
		return undef;
	}
	
	%heap = ();

	my @fields;

	if($line =~ /^11.\|\|\|/ and $line =~ /\|\|\|(.*?)\|\|\|$/) { # proper setting
		@fields = split(/\|\|\|/, $line);
	} else {                    # the luser didn't configure it correctly
		$line =~ s/\|\|\|/\|/g; # fix possible half-configuration
		@fields = split(/\|/, $line);
	}

	# Standard settings
	my $info = {state                  => $fields[0],
	            playback_time_seconds  => $fields[3],
	            codec                  => $fields[4],
	            bitrate                => $fields[5],
	            'album artist'         => $fields[6],
	            album                  => $fields[7],
	            date                   => $fields[8],
	            genre                  => $fields[9],
	            tracknumber            => $fields[10],
	            title                  => $fields[11]};
	if ($fields[19]) { # 
		$info->{'artist'}              = $fields[12];
		$info->{'totaltracks'}         = $fields[13];
		$info->{'playback_time'}       = $fields[14];
		$info->{'length'}              = $fields[15];
		
		$info->{'_foobar2000_version'} = $fields[16];
		
		$info->{'codec_profile'}       = $fields[17];

		$info->{'discnumber'}          = $fields[18];
		$info->{'totaldiscs'}          = $fields[19];
	}

	$info->{'isplaying'} = 1;
	$info->{'ispaused'} = 0;
	if ($info->{'state'} eq "113") {
		$info->{'ispaused'} = 1;
	} elsif ($info->{'state'} eq "112") {
		$info->{'isplaying'} = 0;
	}
	delete $info->{'state'};

	for (keys %$info) {
		delete $info->{$_} if (defined($info->{$_}) and $info->{$_} eq '?');
	}

	$info->{'album artist'} = $info->{'artist'} unless defined($info->{'album artist'});
	$info->{'track artist'} = $info->{'artist'} if (defined($info->{'artist'}) and $info->{'album artist'} ne $info->{'artist'});
	
	if (defined($info->{'length'})) {
		my ($h, $m, $s) = split(/\:/, $info->{'length'});
		if (defined $s) {
			$info->{'length_seconds'} = $s + $m * 60 + $h * 3600;
		} else {
			$info->{'length_seconds'} = $m + $h * 60;
		}
	}
	
	if ($info->{'length_seconds'} and $info->{'playback_time_seconds'}) {
		$info->{'playback_time_remaining_seconds'} = 
				$info->{'length_seconds'} - $info->{'playback_time_seconds'};
	}

	for (('playback_time', 'playback_time_remaining')) {
		unless (defined($info->{$_})) {
			my $t = $info->{"${_}_seconds"};

			my @u = (0,0);
			for (my $i = 1; $i >= 0; $i--) {
				$u[$i] = $t % 60;
				$t = int($t / 60);
			}
			$info->{$_} = sprintf("%s%02d:%02d", $t > 0 ? "$t:" : "", @u[0,1]);
		}
	}

	return $info;
}

sub parse_format {
	my ($format, $info, $sublevel) = @_;
	$sublevel = 0 if not defined $sublevel;

	my $output = "";

	$format =~ s/\R//g; # ignore line breaks
	my @chars = split(//,$format);

	# Language Definition

	# lowercasestring      <== should be parsed as a tag name, makes the expression fail if such tag is not defined
	# []                   <== brackets allow the parsing inside them to fail
	# $func(arg1,arg2,...) <== function call (see parse_subfunction for details)
	# ''                   <== string literal (ignores all parsing)
	# \(character)         <== literal character

	# Bracket Nesting

	# A bracket returns a defined value only if it has at least one tag or at least one of its embedded brackets return true.

	my @tokens = ();
	my $tagcount = 0;
	my $fail = 0;

	my $literal = 0;
	my $sub = 0;
	my $func = 0;
	my $tagmode = 0;
	my $str = "";
	my $ignore = 0;

	for(my $i = 0; $i < @chars; $i++ ) { # 1st Pass (Lexical analysis, push into @tokens)
		if($literal) { # If on literal mode
			$str .= $chars[$i]; # Simply copy everything as-is until an unescaped ' is found
			if ($chars[$i] eq "'") {
				push @tokens, $str;
				$str = "";
				$literal = 0;
			} elsif (not defined($chars[$i+1])) { # This means we ended the string with an uneven number of unescaped 's
				warn "Malformed: mismatched ': $str";
				return undef;
			}
		} elsif ($sub) { # If on subexpression mode
			$str .= $chars[$i]; # Copy everything as-is until an unescaped ] is found
			if ($chars[$i] eq "'") {
				$ignore = !$ignore;
			} elsif ($chars[$i] eq "[") { # We must copy any sub-subexpressions inside this sub-expression for recursive evaluation
				++$sub unless $ignore;
			} elsif ($chars[$i] eq "]" and !$ignore and --$sub == 0) {
				push @tokens, $str;
				$str = "";
			} elsif (not defined($chars[$i+1])) { # This means we ended the string without $sub being 0
				warn "Malformed: mismatched [: $str";
				return undef;
			}
		} elsif ($tagmode) { # If on tag mode
			$str .= $chars[$i]; # Copy tags as-is until any % character is found
			if ($chars[$i] eq '%') {
				push @tokens, $str;
				$str = "";
				$tagmode = 0;
			} elsif (not defined($chars[$i+1])) {
				warn "Malformed: mismatched %: $str";
				return undef;
			}
		} elsif ($func) { # If on function mode
			$str .= $chars[$i]; # Copy everything until an unescaped ) is found
			if ($chars[$i] eq "'") {
				$ignore = !$ignore;
			} elsif ($chars[$i] eq "(") {
				$func++ unless $ignore;
			} elsif ($chars[$i] eq ")" and !$ignore and --$func <= 1) {
				push @tokens, $str;
				$str = "";
				$func = 0;
			} elsif (not defined($chars[$i+1])) {
				warn "Malformed: mismatched (: $str";
				return undef;
			}
		} else {
			if ($chars[$i] eq "'") {
				push @tokens, "$str" if $str ne ""; # Found an opening quote
				$str = $chars[$i];
				$literal = 1; # Enter literal mode
			} elsif ($chars[$i] eq "[") {
				push @tokens, "$str" if $str ne ""; # Found a subexpression opener
				$str = $chars[$i];
				$sub = 1; # Enter subexpression mode
			} elsif ($chars[$i] eq "\$") {
				push @tokens, "$str" if $str ne "";
				$str = $chars[$i];
				$func = 1; # Enter subfunction mode
			} elsif ($chars[$i] eq "%") {
				push @tokens, "$str" if $str ne ""; # Found a tag name
				$str = $chars[$i];
				$tagmode = 1; # Enter tag mode
			} else {
				$str .= $chars[$i]; # Copy as a literal
			}
		}
	}

	push @tokens, "$str" if $str ne ""; # Make sure whatever is left from parsing is added as a literal

	foreach my $token (@tokens) { # 2nd Pass, execute tokens
		if ($token =~ /^'(.*)'$/ or $token =~ /^([^['%\$].*)$/) { # If the token is a literal, then
			$output .= $token eq "''" ? "'" : $1; # '' means a literal ', otherwise literal contents
		} elsif ($token =~ /^%(.*)%$/) { # If this is a tag
			$token = $1;
			return undef unless defined($info->{$token});
			$output .= $info->{$token}; # Copy value to output
		} elsif ($token =~ /^\[(.*)\]$/) { # If the token is a subexpression
			$token = $1;
			my $recurse = parse_format($token, $info, $sublevel+1); # Recurse
			$output .= $recurse if defined($recurse);
		} elsif ($token =~ /^\$/) { # If the token is a subfunction
			my $res = parse_subfunction($token, $info, $sublevel);
			return undef unless defined($res);
			$output .= $res;
		} else {
			warn "Parsing error: $token";
			return undef;
		}
	}

	return $output;
}

sub build_output {
	my ($format, $info, $sublevel) = @_;
	$sublevel = 0 if not defined $sublevel;

	return parse_format($format, $info, $sublevel);
}

sub parse_subfunction {
	my ($function, $info, $sublevel) = @_;

	$function =~ /^\$(.*?)\((.*)\)$/;

	my $func = $1;

	my @rawargs = split(//, $2);
	my @args = ();

	my $ignore = 0;
	my $str = "";
	for(my $i = 0; $i < @rawargs; $i++) {
		if ($rawargs[$i] eq "'") {
			$ignore = !$ignore;
		} elsif ($rawargs[$i] eq ",") {
			unless ($ignore) {
				push @args, $str;
				$str = "";
				++$i;
			}
		}
		$str .= $rawargs[$i] if defined($rawargs[$i]);
	}
	push @args, $str;

	for (my $i = 0; $i < @args; $i++) {
		$args[$i] = parse_format($args[$i], $info, $sublevel+1);
	}

	if ($func eq "len") {
		return defined $args[0] ? length($args[0]) : undef;
	} elsif ($func eq "repeat") {
		return (defined $args[0] and defined $args[1]) ? ($args[0] x $args[1]) : undef;
	} elsif ($func eq "trim") {
		my ($str) = @args;
		return undef unless defined $str;
		$str =~ /^\s*+(.*?)\s*+$/;
		return $1;
	} elsif ($func eq "put" or $func eq "puts") {
		my ($var, $val) = @args;
		return undef unless (defined $var and defined $val);
		$heap{$var} = $val;
		return ($func eq "put") ? $val : "";
	} elsif ($func eq "get") {
		my ($var) = @args;
		return undef unless defined $var;
		return exists $heap{$var} ? $heap{$var} : "";
	} elsif ($func eq "pad" or $func eq "pad_right" or $func eq "left" or $func eq "cut" or $func eq "padcut" or $func eq "padcut_right") {
		my ($str, $maxlen, $char) = @args;
		return undef unless (defined $str and $maxlen);
		
		my $pad = ($func eq "pad" or $func eq "pad_right" or $func eq "padcut" or $func eq "padcut_right");
		my $cut = ($func eq "left" or $func eq "cut" or $func eq "padcut" or $func eq "padcut_right");
		
		if ($cut) {
			$str = substr($str, 0, $maxlen);
		}
		if ($pad) {
			$char = " " unless defined $char and $char ne "";
			$char = substr($char, 0, 1);
			$str .= ($char x ($maxlen - length($str)));
		}
		return $str;
	} elsif ($func eq "right") {
		my ($str, $maxlen) = @args;
		return undef unless (defined $str and defined $maxlen);
		return substr($str, -$maxlen);
	} elsif ($func eq "insert" or $func eq "replace") {
		my ($haystack, $needle, $pos) = @args;
		return undef unless (defined($haystack) and defined($needle) and defined($pos));
		if ($func eq "insert") {
			return substr($haystack, 0, $pos) . $needle . substr($haystack, $pos);
		}
		$needle = quotemeta($needle);
		$haystack =~ s/$needle/$pos/g;
		return $haystack;
	} elsif ($func eq "if" or $func eq "if2") {
		my ($test, $iftrue, $iffalse);
		if ($func eq "if") {
			($test, $iftrue, $iffalse) = @args;
		} else {
			($test, $iffalse) = @args;
			$iftrue = $test;
		}

		if ($test) {
			return $iftrue;
		} else {
			return $iffalse;
		}
	} elsif ($func eq "if3") {
		foreach (@args) {
			return $_ if $_;
		}
		return undef;
	} elsif ($func eq "greater") {
		my ($arg1, $arg2) = @args;
		return undef unless (defined($arg1) or defined($arg2));
		return $arg1 unless defined $arg2;
		return $arg2 unless defined $arg1;
		return $arg1 if $arg1 >= $arg2;
		return $arg2;
	} elsif ($func eq "longer") {
		my ($arg1, $arg2) = @args;
		return undef unless (defined($arg1) or defined($arg2));
		return $arg1 unless defined $arg2;
		return $arg2 unless defined $arg1;
		return $arg1 if length($arg1) >= length($arg2);
		return $arg2;
	} elsif ($func eq "longest") {
		return undef unless scalar(@args);
		my $longest = $_[0];
		foreach (@args) {
			next unless defined;
			$longest = $_ if length($_) > length($longest);
		}
		return $longest;
	} elsif ($func eq "ifgreater" or $func eq "ifequal" or $func eq "iflonger") {
		my ($arg1, $arg2, $iftrue, $iffalse) = @args;

		unless (defined($arg2)) {
			return $iftrue if (defined($arg1));
			return $iffalse;
		}
		return $iffalse unless (defined($arg1));

		if ($func eq "iflonger") {
			return defined($arg1) ? $iftrue : $iffalse unless (defined($arg1) and defined($arg2));
			return $iftrue if (length($arg1) > length(" " x $arg2));
		} elsif ($func eq "ifequal") {
			# Any of the args may not be comparable, return false in that case
			return $iftrue if (defined($arg1) and defined($arg2));
			return $iffalse unless (defined($arg1) and defined($arg2));
			eval { return $iftrue if $arg1 == $arg2 };
		} else { # ifgreater
			return defined($arg1) ? $iftrue : $iffalse unless (defined($arg1) and defined($arg2));
			eval { return $iftrue if $arg1 > $arg2 };
		}
		return $iffalse;
	} elsif ($func eq "abbr") {
		my ($arg1, $arg2) = (0,0);
		$arg1 = $args[0];
		$arg2 = $args[1] if (defined($args[1]));
		return undef unless (defined $arg1 and $arg2 >= 0);

		if (length($arg1) > $arg2) {
			my $abbr = "";
			my @tokens = split(/\s+/, $arg1);
			foreach my $token (@tokens) {
				my @chars = split(//, $token);
				$abbr .= $chars[0];
			}
			return $abbr;
		}
		return $arg1;
	} elsif ($func eq "num") {
		my ($arg1, $arg2) = @args;
		return undef unless (defined($arg1) and $arg2 > 0);
		return sprintf("%0${arg2}d", $arg1);
	} elsif ($func =~ /^(add|sub|mul|div|mod|max|min)$/) {
		my ($arg1, $arg2) = @args;
		return undef unless (defined($arg1) and defined($arg2));
		# Make sure both are numbers. Better way to do this?
		return undef unless eval { $arg1 != $arg2 or $arg1 == $arg2 };
		return $arg1 + $arg2 if ($func eq "add");
		return $arg1 - $arg2 if ($func eq "sub");
		return $arg1 * $arg2 if ($func eq "mul");
		return $arg1 / $arg2 if ($func eq "div");
		return $arg1 % $arg2 if ($func eq "mod");
		return ($arg1 >= $arg2 ? $arg1 : $arg2) if ($func eq "max");
		return ($arg1 < $arg2 ? $arg1 : $arg2) if ($func eq "min");
	} elsif ($func =~ /^(and|or|xor|not)$/) {
		my ($arg1, $arg2) = @args;
		$arg1 = 0 unless defined $arg1;
		$arg2 = 0 unless defined $arg2;

		# Need to give explicit returns to avoid eating on parse_format

		return ($arg1 ? 0 : 1) if ($func eq "not");
		return (($arg1 && $arg2) ? 1 : 0) if ($func eq "and");
		return (($arg1 || $arg2) ? 1 : 0) if ($func eq "or");
		return (($arg1 && !$arg2) ? 1 : ((!$arg1 && $arg2) ? 1 : 0)) if ($func eq "xor");
	} elsif ($func eq "strcmp" or $func eq "stricmp") {
		my ($arg1, $arg2) = @args;
		return undef unless (defined($arg1) and defined($arg2));
		return ((lc($arg1) eq lc($arg2)) ? 1 : 0) if ($func eq "stricmp");
		return (($arg1 eq $arg2) ? 1 : 0);
	} elsif ($func eq "caps") {
		my ($arg1) = @args;
		return undef unless defined $arg1;
		$arg1 =~ s/\b(\S)(\S*)\b/@{[uc($1)]}@{[lc($2)]}/g;
		return $arg1;
	} elsif ($func eq "caps2") {
		my ($arg1) = @args;
		return undef unless defined $arg1;
		$arg1 =~ s/\b(\S)/@{[uc($1)]}/g;
		return $arg1;
	} elsif ($func eq "lower" or $func eq "upper") {
		my ($arg1) = @args;
		return undef unless defined $arg1;
		return lc($arg1) if $func eq "lower";
		return uc($arg1);
	} elsif ($func eq "fix_eol") {
		my ($meta, $repl) = @args;
		$repl = " (...)" unless $repl;
		return undef unless defined($meta);
		$meta =~ s/\010?\013.*//;
		return $meta;
	}

	warn "Unknown or unimplemented function: $function";
	return undef;
}

sub get_np_string {
	my $info = get_track_info();
	$info->{comment} = $_[0] if $_[0];
	if (defined($info)) {
		return build_output($format, $info);
	}
	return undef;
}

sub get_help_string {
	my $fields;
	if (HAVE_IRSSI) {
		$fields = '%%codec%%|||%%bitrate%%|||%%album artist%%|||%%album%%|||%%date%%|||%%genre%%|||%%tracknumber%%|||%%title%%|||%%artist%%|||%%totaltracks%%|||%%playback_time%%|||%%length%%|||%%_foobar2000_version%%|||%%codec_profile%%|||%%discnumber%%|||%%totaldiscs%%';
	} else {
		$fields = '%codec%|||%bitrate%|||%album artist%|||%album%|||%date%|||%genre%|||%tracknumber%|||%title%|||%artist%|||%totaltracks%|||%playback_time%|||%length%|||%_foobar2000_version%|||%codec_profile%|||%discnumber%|||%totaldiscs%';
	}
	my $help = <<EOF
Required Plugin: foo_controlserver
URL: http://www.hydrogenaudio.org/forums/index.php?showtopic=38114
Required settings: Control Server tab:
* Server Port: 3333
* UTF-8 output/input: checked
* Base delimiter: |||
Recommended setting:
* Number of Clients: Some big number like 700
* Fields: $fields

NOTE: the script only works with either the default or this custom Fields line.

This script can also work via SSH tunneling, by using -R 3333:localhost:3333.

EOF
;
	return $help;
}

sub get_intro_string {
	my $intro = <<EOF
\002-----------------------------------------------------------------
\002foo_spam - prints the currently playing track from foobar2000
\002Created by Kovensky \(irc.rizon.net #shameimaru\)
This script requires a properly configured foobar2000.
Run /foo_help for help setting foobar2000 up.
\002-----------------------------------------------------------------
Usage:
/aud        - prints the playing song as an ACTION
/np         - alias to /aud
/foo_help   - explains how to set up foobar2000
/foo_format - explains how to set up the output format
\002-----------------------------------------------------------------

EOF
;
	return $intro;
}

sub get_foo_format_help_string {
	my $help = <<EOF
Format Definition
Example: %artist% - [%album% - ]%title%

foo_spam now uses the same syntax as foobar2000 (title format), however only
a subset of it is currently implemented. To see the list of supported
tags, use /foo_tags. To see the list of supported functions, use
/foo_funcs.

To change the format, you can use:
 * Irssi: /set foo_format <new format> (use /set -default to reset)
 * X-Chat: /set_foo_format <new format> (use /set_foo_format default to reset)
 * WeeChat: /set plugins.var.foo_spam.format <new format> (use /unset to reset)
You can also edit the script and change the value of \$default_format, in case
you use an unsupported client.

Default: $default_format

EOF
;
	return $help;
}

sub get_taglist_string {
	my $list = <<EOF
List of available tags (refer to foobar2000's documentation for their meanings):
 - %isplaying%, %ispaused%, %_foobar2000_version%
 - %playback_time%, %playback_time_remaining%, %length% (plus the _seconds variants)
 - %artist%, %album artist%, %track artist%, %album%, %title%, %genre%
 - %date%, %discnumber%, %totaldiscs%, %tracknumber%, %totaltracks%
 - %codec%, %bitrate%, %codec_profile%
The %comment% tag is set by foo_spam itself and it contains all arguments that the user gives to /aud in a single string.
EOF
;
	return $list;
}

sub get_funclist_string {
	my $list = <<'EOF'
List of available functions (refer to foobar2000's documentation for their meanings):
 - $if(X,Y,Z), $if2(X,Y), $if3(X,Y,Z,...), $ifgreater(A,B,C,D), $iflonger(A,B,C,D), $ifequal(A,B,C,D)
 - $and(X,Y), $or(X,Y), $xor(X,Y), $not(X)
 - $strcmp(X,Y), $stricmp(X,Y), $len(X), $num(X,Y)
 - $greater(X,Y), $longer(X,Y), $longest(A,B,C,...)
 - $caps(X), $caps2(X), $lower(X), $upper(X)
 - $trim(A), $pad(X,Y), $pad_right(X,Y), $pad(X,Y,Z), $pad_right(X,Y,Z), $left(X,Y), $cut(X,Y), $padcut(X,Y), $padcut_right(X,Y), $right(X,Y)
 - $insert(A,B,N), $replace(A,B,C), $repeat(X,N)
 - $abbr(X), $abbr(X,Y)
 - $add(X,Y), $sub(X,Y), $mul(X,Y), $div(X,Y), $mod(X,Y), $min(X,Y), $max(X,Y)
 - $put(name,text), $puts(name,text), $get(name)
EOF
;
	return $list;
}

if (HAVE_IRSSI) {
	*print_now_playing = sub {
		my ($data, $server, $witem) = @_;
		my $str = get_np_string(decode("UTF-8", $data));
		if (defined($str)) {
			if ($witem && ($witem->{type} eq "CHANNEL" ||
				$witem->{type} eq "QUERY")) {
				$witem->command(encode_utf8("me $str"));
			}
		}
	};

	*print_foo_help = sub{
		Irssi::print(get_help_string());
	};

	*print_foo_format_help = sub {
		my $help = get_foo_format_help_string();
		$help =~ s/%/%%/g;
		Irssi::print($help);
	};

	*irc_print = sub {
		Irssi::print($_[0]);
	};

	*print_foo_tags = sub {
		my $help = get_foo_taglist_string();
		$help =~ s/%/%%/g;
		Irssi::print($help);
	};
	
	*print_foo_funcs = sub {
		Irssi::print(get_funclist_string());
	};

	Irssi::settings_add_str("foo_spam", "foo_format", $format);
	$format = Irssi::settings_get_str("foo_format");

	Irssi::command_bind('aud', 'print_now_playing');
	Irssi::command_bind('np', 'print_now_playing');
	Irssi::command_bind('foo_help', 'print_foo_help');
	Irssi::command_bind('foo_format','print_foo_format_help');
	Irssi::command_bind('foo_tags','print_foo_tags');
	Irssi::command_bind('foo_funcs','print_foo_funcs');
} elsif (HAVE_XCHAT) {
	*print_now_playing = sub {
		my $str = get_np_string($_[0][1] ? $_[1][1] : undef);
		if (defined($str)) {
			Xchat::command(encode_utf8("me $str"));
		}
		return Xchat::EAT_ALL();
	};

	*print_foo_help = sub {
		Xchat::print(get_help_string());
		return Xchat::EAT_ALL();
	};

	*irc_print = sub {
		Xchat::print(@_);
	};

	*set_foo_format = sub {
		if (defined($_[0][1])) {
			open($setting_file, ">", Xchat::get_info('xchatdir') . "/foo_spam.conf");
			if ($_[0][1] eq "default") {
				$format = $default_format;
			} else {
				$format = $_[1][1];
			}
			Xchat::print("Changed format to $format\n");
			if (defined($setting_file)) {
				print $setting_file $format;
				close($setting_file);
			} else {
				Xchat::print("Failed to save settings! Error: $!");
			}
		} else {
			Xchat::print("Current format: $format\n");
		}
		return Xchat::EAT_ALL();
	};
	if (defined(*set_foo_format)) {} # Silence a warning

	*print_foo_format_help = sub {
		Xchat::print(get_foo_format_help_string());
		return Xchat::EAT_ALL();
	};

	*print_foo_tags = sub {
		Xchat::print(get_taglist_string());
		return Xchat::EAT_ALL();
	};
	
	*print_foo_funcs = sub {
		Xchat::print(get_funclist_string());
		return Xchat::EAT_ALL();
	};

	if (open($setting_file, "<", Xchat::get_info('xchatdir') . "/foo_spam.conf")) {
		my $line = <$setting_file>;
		chomp $line;
		$format = $line if (defined($line) and $line ne "");
		close($setting_file);
	}

	Xchat::hook_command("np","print_now_playing", {help => "alias to /aud"});
	Xchat::hook_command("aud","print_now_playing", {help => "prints your currently playing song on foobar2000 on an ACTION"});
	Xchat::hook_command("foo_help","print_foo_help", {help => "explains how to set up foobar2000"});
	Xchat::hook_command("set_foo_format","set_foo_format", {help => "displays or changes the current format string"});
	Xchat::hook_command("foo_format","print_foo_format_help", {help => "explains how to configure the format string"});
	Xchat::hook_command("foo_tags","print_foo_tags", {help => "lists all available tags"});
	Xchat::hook_command('foo_funcs','print_foo_funcs', {help => "lists all available functions"});
} elsif (HAVE_WEECH) {
	*print_now_playing = sub {
		my ($data, $buffer, @args) = @_;
		$format = weechat::config_get_plugin("format");
		my $str = get_np_string($args[0] ? decode("UTF-8", join(' ', @args)) : undef);
		if (defined($str)) {
			weechat::command($buffer, encode_utf8("/me $str"));
		}
		return weechat::WEECHAT_RC_OK_EAT();
	};

	*irc_print = sub {
		weechat::print('', shift);
	};

	*print_foo_help = sub {
		irc_print(get_help_string());
		return weechat::WEECHAT_RC_OK_EAT();
	};

	*print_foo_format_help = sub {
		irc_print(get_foo_format_help_string());
		return weechat::WEECHAT_RC_OK_EAT();
	};

	*print_foo_tags = sub {
		irc_print(get_taglist_string());
		return weechat::WEECHAT_RC_OK_EAT();
	};
	
	*print_foo_funcs = sub {
		irc_print(get_funclist_string());
		return Xchat::WEECHAT_RC_OK_EAT();
	};

	unless (weechat::config_is_set_plugin("format")) {
		weechat::config_set_plugin("format", $default_format);
	}

	weechat::hook_command('np', 'alias to /aud', '', '', '%(nicks)', 'print_now_playing', '');
	weechat::hook_command('aud', 'prints your currently playing song on foobar2000 on an ACTION', '', '', '%(nicks)', 'print_now_playing', '');
	weechat::hook_command('foo_help', 'explains how to set up foobar2000', '', '', '', 'print_foo_help', '');
	weechat::hook_command('foo_format', 'explains how to configure the format string', '', '', '', 'print_foo_format_help', '');
	weechat::hook_command('foo_tags', 'lists all available tags', '', '', '', 'print_foo_tags', '');
	weechat::hook_command('foo_funcs', 'lists all available functions', '', '', '', 'print_foo_funcs', '');
} else {
	$| = 1;
	binmode (STDERR, ":encoding(utf-8)");
	binmode (STDOUT, ":encoding(utf-8)");
	*irc_print = sub {
		print (STDERR "@_\n") if @_;
	};
	$format = join(" ", @ARGV) if $ARGV[0];
	my $np = get_np_string();
	print "$np\n" if $np;
}

if (HAVE_XCHAT or HAVE_IRSSI or HAVE_WEECH) {
	irc_print(get_intro_string());
}

