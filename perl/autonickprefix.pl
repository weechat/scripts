use strict;
use Encode qw(encode_utf8);

weechat::register(
    'autonickprefix',
    'Juerd <#####@juerd.nl>',
    '1.00',
    'PD',
    "Change 'nick: ' prefix if the nick is changed while you're still editing.",
    '',
    ''
);

# This is a port of the Irssi script autonickprefix.pl, the main difference
# being that WeeChat has an input *per buffer*, so the script needs to iterate
# over the buffers instead of just the current one, because there could be
# multiple messages waiting to be sent.

sub nick_changed {
    my (undef, $server, $args) = @_;

    $server = (split /,/, $server)[0];

    my ($oldnick, $newnick) = $args =~ /\:(.*)\!(?:.*)\:(.*)/
        or return weechat::WEECHAT_RC_OK;

    my $hdata = weechat::hdata_get("buffer");
    my $buffer = weechat::hdata_get_list($hdata, "gui_buffers");
    my $char = weechat::config_get('completion.nick_completer');

    while ($buffer) {
        weechat::buffer_get_string($buffer,'localvar_server') eq $server
            or next;

        my $pos = weechat::buffer_get_integer($buffer, 'input_pos');
        my $input = weechat::buffer_get_string($buffer, 'input');
        $pos >= length("$oldnick$char") or next;

        $input =~ s/^\Q$oldnick$char/$newnick$char/ or next;
        my $delta = length($newnick) - length($oldnick);

        weechat::buffer_set($buffer, "input", $input);
        weechat::buffer_set($buffer, "input_pos", $pos + $delta);
    } continue {
        $buffer = weechat::hdata_pointer($hdata, $buffer, "next_buffer");
    }

    return weechat::WEECHAT_RC_OK;
}

weechat::hook_signal("*,irc_in_nick", "nick_changed", "");
