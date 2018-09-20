use strict;
use Encode qw(encode_utf8);
weechat::register(
    'foo',
    'Juerd <#####@juerd.nl>',
    '3.00',
    'PD',
    'Rot n+i encryption and decryption',
    '',
    ''
);

# This is a port of the irssi script foo.pl that has existed since 2001.
# It was originally written as a simple scripting example, but is still
# sometimes used for fun.


# Didn't port the non-ascii stuff to weechat, because it assumes Windows-1252
# or latin1, which nobody uses anymore. Some UTF-8 thing would be better.
#my $char1 = "\xC0-\xCF\xD2-\xD6\xD8-\xDD";
#my $char2 = "\xE0-\xF6\xF8-\xFF";

sub rot {
    my ($dir, $rotABC, $rot123, $rotshift, $msg) = @_;
    my $i = 0;
    for (0 .. length $msg) {
        my $char = \substr $msg, $_, 1;
        $i += $rotshift;
        $$char =~ tr/a-zA-Z/b-zaB-ZA/ for 1..abs $dir *26 - ($rotABC + $i) % 26;
        $$char =~ tr/0-9/1-90/        for 1..abs $dir *10 - ($rot123 + $i) % 10;
    }
    return $msg;
}

# weechat encodes ^O, ^B, and ^_ differently.
my $O = "\x1c";
my $B = "(?:[\x1a\x1b]\x01)";  # \x1a is on, \x1b is off.
my $U = "(?:[\x1a\x1b]\x04)";

sub hook_print_cb {
    my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $msg) = @_;
    return weechat::WEECHAT_RC_OK unless $msg =~ s/^$O($B+)$O($B+)$O($O*)//;
    $msg = rot 1, length($1)/2, length($2)/2, length $3, $msg;

    weechat::print_date_tags($buffer, $date, $tags, "$prefix\t\x1a\x01$msg");
    return weechat::WEECHAT_RC_OK;
}

sub hook_cmd_rot_cb {
    my ($data, $buffer, $args) = @_;

    my $rotABC   = 1 +     int rand 13;
    my $rot123   = 1 + 2 * int rand 4;
    my $rotshift = 1 +     int rand 10;
    weechat::command(
        $buffer,
        encode_utf8(sprintf "/say \cO%s\cO%s\cO%s%s",
            "\cB" x $rotABC,
            "\cB" x $rot123,
            "\cO" x $rotshift,
            rot 0, $rotABC, $rot123, $rotshift, $args
        )
    );
}


# Yuck, symbolic references to subs instead of actual CODE refs...
weechat::hook_print("", "notify_none,notify_message,notify_private,notify_highlight", "", 0, "hook_print_cb", "");
weechat::hook_command("rot", "Sends via UeberRot", "", "", "", "hook_cmd_rot_cb", "");
