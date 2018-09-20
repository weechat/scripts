use strict;
use Encode qw(encode_utf8);
weechat::register(
    'ctrl_w',
    'Juerd <#####@juerd.nl>',
    '1.00',
    'PD',
    'Implement readline-like ^W',
    '',
    ''
);

sub ctrl_w {
    my ($data, $buffer, $args) = @_;

    my $pos = weechat::buffer_get_integer($buffer, 'input_pos');
    my $input = weechat::buffer_get_string($buffer, 'input');

    utf8::decode($input);
    substr($input, 0, $pos) =~ s/(\S+\s*)\z// and $pos -= length $1;
    utf8::encode($input);

    weechat::buffer_set($buffer, "input", $input);
    weechat::buffer_set($buffer, "input_pos", $pos);

    return weechat::WEECHAT_RC_OK;
}

weechat::hook_command("ctrl_w", "Delete previous word like readline ^W", "", "", "", "ctrl_w", "");

# Print helpful message if ctrl-W is still bound to the default function.
my $i = weechat::infolist_get("key", "", "default");
weechat::infolist_reset_item_cursor($i);
while (weechat::infolist_next($i)) {
    my $k = weechat::infolist_string($i, "key");
    my $c = weechat::infolist_string($i, "command");
    $k =~ m[^ctrl-w$]i or next;
    $c =~ m[^/input delete_previous_word]i or next;

    weechat::print("", "$k is still bound to $c; to use the ctrl_w script, use /key bind $k /ctrl_w");
    last;
}
