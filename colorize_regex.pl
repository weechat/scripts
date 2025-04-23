# SPDX-FileCopyrightText: 2025 ryoskzypu <ryoskzypu@proton.me>
#
# SPDX-License-Identifier: MIT-0
#
# colorize_regex.pl — colorize highlight regex matches in chat messages
#
# Description:
#   Colorize regex matches in chat messages from 'weechat.look.highlight_regex'
#   option or the 'highlight_regex' buffer property, to make validation of matches
#   easier.
#
#   Commands:
#     /dbgcolor
#       Debug weechat's strings color codes. Similar to '/debug unicode', but
#       specific to colors, and output is a standard hex dump. Can be used to
#       debug other scripts.
#       See '/help dbgcolor' for usage.
#
#     /rset
#       Fast set the script options and regexes. Similar to /fset.
#       See '/help rset' for usage.
#
# Bugs:
#   https://github.com/ryoskzypu/weechat_scripts
#
# History:
#   2025-03-26, ryoskzypu <ryoskzypu@proton.me>:
#     version 1.0: initial release

use strict;
use warnings;

# Debug data structures.
#use Data::Dumper qw< Dumper >;
#$Data::Dumper::Terse = 1;
#$Data::Dumper::Useqq = 1;

# Global variables

my %script = (
    prog    => 'colorize_regex',
    version => '1.0',
    author  => 'ryoskzypu <ryoskzypu@proton.me>',
    licence => 'MIT-0',
    desc    => 'Colorize highlight regex matches in chat messages',
);
my $prog = $script{'prog'};

# Config
my %conf;
my $conf_file;

# Script buffer
my $prog_buff;

# Return codes
my $ok  = weechat::WEECHAT_RC_OK;
my $err = weechat::WEECHAT_RC_ERROR;

# highlight_regex
my $regex_opt = 'weechat.look.highlight_regex';  # Option
my $re_opt_pat;                                  # Pattern

# Colors
my $color_match;
my $color_reset = wcolor('reset');

# Regexes
my $colors_rgx = qr/
                     \o{031}
                     (?>
                         \d{2}+                     # Fixed 'weechat.color.chat.*' codes
                         |
                         (?>                        # Foreground
                             [F*]
                             [*!\/_%.|]?+
                             \d{2}+                 # IRC colors (00–15)
                             |
                             (?> F@ | \*@ )
                             [*!\/_%.|]?+
                             \d{5}+                 # IRC colors (16–99) and WeeChat colors (16–255)
                         )
                         (?>                        # Background
                             ~
                             (?> \d{2}+ | @\d{5}+)
                         )?+
                     )
                 /x;
my $attr_rgx   = qr/
                     (?> \o{032} | \o{033})
                     [\o{001}-\o{006}]
                     |
                     \o{031}\o{034}                 # Reset color and keep attributes
                 /x;
my $reset_rgx  = qr/\o{034}/;
my $split_rgx  = qr/
                     ($colors_rgx)                  # Colors
                     |
                     ($attr_rgx)                    # Attributes
                     |
                     ($reset_rgx)                   # Reset all
                     |
                                                    # Bytes
                 /x;

# Space hex code.
my $space = "\x{20}";

# Utils

# Get string value of option pointer.
sub wstr
{
    my ($opt) = @_;
    return weechat::config_string($opt);
}

# Get weechat's colors.
sub wcolor
{
    my $code  = shift;
    my $color = weechat::color($code);

    if ($color eq '') {
        chkbuff(1);
        wprint('', "wcolor\tfailed to get '${code}' color code");
    }

    return $color;
}

# Print string on the specific buffer.
sub wprint
{
    my ($buff, $str) = @_;

    # Assign buffer pointer to the script's if conditions met.
    if ($buff eq '' && defined $prog_buff) {
        $buff = $prog_buff;
    }

    return weechat::print($buff, $str);
}

# Create a dedicated buffer for the script messages.
# Note that all highlights are disabled to avoid duplicated highlights.
sub set_buffer
{
    my $buff_props = {
        'title'                   => "${prog}.pl — colorize highlight regex matches in chat messages",
        'highlight_disable_regex' => '.+',
    };
    my $new_buff = weechat::buffer_new_props($prog, $buff_props, '', '', '', '');
    wprint('', "${prog}\tfailed to create '${prog}' buffer") if $new_buff eq '';

    return $new_buff;
}

# Create the script buffer if not opened, then optionally jump to it.
sub chkbuff
{
    my $jump = shift;

    if (weechat::buffer_search('perl', $prog) eq '') {
        $prog_buff = set_buffer();
        return if $prog_buff eq '';
    }

    if (defined $jump && $jump == 1) {
        if (weechat::command('', "/buffer perl.$prog") == $err) {
            wprint('', "chkbuff\tfailed to jump in the buffer");
            return $err;
        }
    }
}

# Check the format (od/xxd) that is set, before dumping it.
sub chkdump
{
    my ($buff, $arg, $arg_dump) = @_;

    if ($arg eq 'od') {
        sim_od($buff, $arg_dump);
    }
    elsif ($arg eq 'xxd') {
        sim_xxd($buff, $arg_dump);
    }
}

# Debug the colorize_cb() split messages arrays.
sub sdbg
{
    my ($prefix, $var, $array) = @_;

    return if wstr($conf{'debug_mode'}) eq 'off';

    if (wstr($conf{'debug_mode'}) eq 'on' && defined $array) {
        my $count = scalar $array->@*;

        chkbuff();

        wprint('', "${prefix}\@$var count: ${count}\n");
        wprint('', "\@$var = " . Dumper $array);

        foreach my $i ($array->@*) {
            chkdump('', wstr($conf{'debug_fmt'}), $i);
            wprint('', '');
        }
    }
}

# Print debug weechat's strings.
sub pdbg
{
    my ($prefix, $var_msg, $hex, $str) = @_;

    return if wstr($conf{'debug_mode'}) eq 'off';

    if (wstr($conf{'debug_mode'}) eq 'on' && defined $str) {
        chkbuff();
        wprint('', "${prefix}${var_msg}:\n '${str}${color_reset}'\n");

        # Convert message to hex. Useful to decode the string and copy it to some tool.
        if ($hex == 1) {
            my $hex_str = unpack 'H*', $str;
            wprint('', "\$hex_str:\n '${hex_str}'\n");
        }

        chkdump('', wstr($conf{'debug_fmt'}), $str);
    }
}

# Decode IRC colors from string.
sub decode_arg
{
    my ($arg) = @_;
    my $decoded = weechat::hook_modifier_exec('irc_color_decode', 1, $arg);

    if ($decoded eq '') {
        chkbuff(1);
        wprint('', "decode_arg\tfailed to decode '${arg}' argument");
    }

    return $decoded;
}

# Evaluate weechat's expressions from string.
sub eval_arg
{
    my ($arg) = @_;
    my $evaled = weechat::string_eval_expression($arg, {}, {}, {});

    if ($evaled eq '') {
        chkbuff(1);
        wprint('', "eval_arg\tfailed to decode '${arg}' argument");
    }

    return $evaled;
}

# Colorize and/or convert bytes to a dot '.'.
#
# See:
#   ascii(7)
#   https://github.com/vim/vim/blob/master/src/xxd/xxd.c#L235
#   https://github.com/vim/vim/blob/master/src/xxd/xxd.c#L615
sub xxd_conv_bytes
{
    my ($type, $byte) = @_;
    my $byte_orig = $byte;
    my $dot       = '.';

    if ($type eq 'hex') {
        $byte = pack 'H*', $byte;  # Convert hex byte to a char.
        $dot  = $byte_orig;        # Do not convert the hexes to a dot.
    }

    my %colors = (
        'red'    => wcolor('*red'),
        'green'  => wcolor('*green'),
        'yellow' => wcolor('*yellow'),
        'blue'   => wcolor('*blue'),
        'white'  => wcolor('*white'),
    );

    # ASCII printable (7-bit)
    if ($byte =~ /\A[\x{20}-\x{7e}]\z/) {
        return "$colors{'green'}${byte_orig}$color_reset";
    }
    # '\t' (tab), '\n' (newline), '\r' (carriage return)
    elsif ($byte =~ /\A[\x{0a}\x{10}\x{0d}]\z/) {
        return "$colors{'yellow'}${dot}$color_reset";
    }
    # '\0' (null)
    elsif ($byte =~/\A\x{00}\z/) {
        return "$colors{'white'}${dot}$color_reset";
    }
    # 255 (decimal)
    elsif ($byte =~/\A\x{ff}\z/) {
        return "$colors{'blue'}${dot}$color_reset";
    }
    # non-printable ASCII and non-ASCII
    else {
        return "$colors{'red'}${dot}$color_reset";
    }
}

# Construct xxd's hexes and bytes rows.
sub xxd_get_rows
{
    my ($len_pad, $arr) = @_;
    my $len_arr = scalar $arr->@* - 1;
    my $pad     = $space;
    my @rows;
    my $row;

    for (my $i = 0; $i <= $len_arr; $i++) {
        $row .= sprintf '%*s', $len_pad, $arr->[$i];

        # Fold and capture row if at the 16th byte.
        if (($i + 1) % 16 == 0) {
            if ($len_pad == 0 && $i != $len_arr) {  # bytes array
                $row .= "\n";
            } else {
                $row .= $pad x 2;
            }

            push @rows, $row;
            $row = '';
        }
        # Align hex row to the right if at last index.
        elsif ($i == $len_arr) {
            if ($len_pad == 9) {  # hex array
                $row .= sprintf '%*s', (16 - ($i + 1) % 16) * 3 + 2, $pad;
            } else {
                $row .= "\n";
            }

            push @rows, $row;
        }
    }

    return @rows;
}

# Print xxd's table.
sub xxd_print
{
    my ($buff, $hex_rows, $byte_rows) = @_;
    my $rows_len = scalar $hex_rows->@* - 1;
    my $prefix   = "xxd\t";
    my $out;

    for (my $i = 0; $i <= $rows_len; $i++) {
        $out .= "$hex_rows->[$i]$byte_rows->[$i]";
    }

    wprint($buff, "${prefix}$out");
}

# Simulate 'xxd -g1 -R always' output.
sub sim_xxd
{
    my ($buff, $str) = @_;
    my @bytes = split //, $str;
    my @hexes = map { unpack 'H*', $_ } @bytes;
    my @byte_rows;
    my @hex_rows;

    @hexes = map { xxd_conv_bytes('hex', $_) } @hexes;
    @bytes = map { xxd_conv_bytes('',    $_) } @bytes;

    @hex_rows  = xxd_get_rows('9', \@hexes);  # 9 length because of the weechat's colors.
    @byte_rows = xxd_get_rows('0', \@bytes);

    xxd_print($buff, \@hex_rows, \@byte_rows);
}

# Convert non-printable chars to their escaped or octal representation.
# See ascii(7).
sub od_conv_chars
{
    my $char = shift;

    # Decimal to escaped chars table
    my %esc_chars = (
        '0'  => '\0',
        '7'  => '\a',
        '8'  => '\b',
        '9'  => '\t',
        '10' => '\n',
        '11' => '\v',
        '12' => '\f',
        '13' => '\r',
    );

    # Escaped
    if ($char =~ /\A[\x{00}\x{07}-\x{0d}]\z/) {
        return sprintf '%s', $esc_chars{ord $char};
    }
    # Non-printable ASCII and non-ASCII
    elsif ($char =~  /\A[^\x{20}-\x{7e}]\z/) {
        return sprintf "%03o", ord $char;  # Octal
    }
    # Printable ASCII (7-bit)
    else {
        return $char;
    }
}

# Construct od's hexes and bytes rows.
sub od_get_rows
{
    my ($arr) = @_;
    my $len_arr = scalar $arr->@* - 1;
    my @rows;
    my $row;

    for (my $i = 0; $i <= $len_arr; $i++) {
        $row .= sprintf '%4s', $arr->[$i];

        # Fold and capture row if at the 16th byte or last index.
        if (($i + 1) % 16 == 0 || $i == $len_arr) {
            $row .= "\n";
            push @rows, $row;
            $row = '';
        }
    }

    return @rows;
}

# Print od's table.
sub od_print
{
    my ($buff, $hex_rows, $byte_rows) = @_;
    my $rows_len = scalar $hex_rows->@* - 1;
    my $prefix   = "od\t";
    my $color    = wcolor('darkgray');
    my $out;

    for (my $i = 0; $i <= $rows_len; $i++) {
        $out .= $hex_rows->[$i];

        # Colorize escapes.
        $out .= $byte_rows->[$i] =~ s/(?> |^)\K03[1-5](?= |$)/${color}${&}$color_reset/gr;
    }

    wprint($buff, "${prefix}$out");
}

# Simulate 'od -An -tx1c' output.
sub sim_od
{
    my ($buff, $str) = @_;
    my @bytes = split //, $str;
    my @hexes = map { unpack 'H*', $_ } @bytes;
    my @byte_rows;
    my @hex_rows;

    @bytes = map { od_conv_chars($_) } @bytes;

    @hex_rows  = od_get_rows(\@hexes);
    @byte_rows = od_get_rows(\@bytes);

    od_print($buff, \@hex_rows, \@byte_rows);
}

# Insert command in weechat's input.
sub set_input
{
    my ($is_option, $arg)  = @_;
    my $command = "/command -s /fset ${arg}; /fset -set";
    my $close   = 0;

    # Buffer property
    if (! $is_option) {
        $arg =~ s/\\/\\$&/g;  # Avoid /input interpretation of backslashes.
        $command = qq{/input insert /buffer setauto highlight_regex "${arg}"};
    }

    # Option
    if ($is_option) {
        $close = 1 if weechat::buffer_search('', 'fset') eq '';

        # /fset commands jump to its buffer, so if current buffer is different,
        # jump back to it.
        if (weechat::buffer_get_string(weechat::current_buffer(), 'name') ne 'fset') {
            $command .= '; /buffer jump last_displayed';

            # Close the 'fset' buffer if it was not already opened.
            $command .= '; /buffer close fset' if $close;
        }
    }

    # Insert
    if (weechat::command('', $command) == $err) {
        chkbuff(1);
        wprint('', "set_input\tfailed to insert command in weechat's input");

        return $err;
    }
}

# Format /dbgcolor and /rset commands descriptions.
sub fmt_desc
{
    # dbgcolor

    my $pad = $space x 34;

    my $dbg_fmt = <<~"END";
        [-buffer <name>] od [-eval|-no] <string>
        ${pad}[-buffer <name>] xxd [-eval|-no] <string>
        END

    my $dbg_arg = <<~'END';
        -buffer: show hex dump on this buffer
             od: hex dump string in 'od -An -tx1c' format
            xxd: "                  'xxd -g1 -R always' format
          -eval: evaluate string before dumping it (see /help eval)
            -no: do not decode IRC colors

        Without argument, 'od' format is used unless '*.debug.fmt' option is set to 'xxd'.
        IRC colors are decoded from string unless -eval or -no is set.
        Hex dump is shown on script buffer unless -buffer is set.

        Examples:
          dump string 'hi <3 WeeChat' in italic and '<3' in bold red (Ctrl = ^C):
            /dbgcolor ^Cihi ^Ci^Cb^Cc05<3 ^Cc^CbWeeChat

          dump string 'hello' underlined in xxd format:
            /dbgcolor xxd ^C_hello

          dump string 'hello' in bold blue with weechat colors:
            /dbgcolor -eval ${color:*blue}hello
        END

    # rset
    my $hl_arg = <<~"END";
           fmt: ${prog}.debug.fmt
         debug: "             .debug.mode
            fg: "             .color.match_fg
            bg: "             .color.match_bg
        filter: "             .look.colorize_filter
         regex: $regex_opt
          prop: weechat.buffer.plugin.server.#channel.highlight_regex

         Without argument, all options and regexes are shown.

         Examples:
           insert '/set $regex_opt "regex"' on weechat's input:
             /rset regex

            insert '/buffer setauto highlight_regex "regex"':
              /rset prop
        END

    return $dbg_fmt, $dbg_arg, $hl_arg;
}

# Callbacks

# Regex set callback
#
# Quickly check the script options and regexes, and edit by inserting them in the
# weechat's input.
# Note that it depends on the 'fset' plugin.
sub regex_set_cb
{
    my ($data, $buff, $args) = @_;
    my $prefix = "rset\t";
    my $is_opt = 1;

    # Options
    my $fmt_opt     = "${prog}.debug.fmt";
    my $dbg_opt     = "${prog}.debug.mode";
    my $fg_opt      = "${prog}.color.match_fg";
    my $bg_opt      = "${prog}.color.match_bg";
    my $filter_opt  = "${prog}.look.colorize_filter";

    # Values
    my $fmt         = wstr($conf{'debug_fmt'});
    my $debug       = wstr($conf{'debug_mode'});
    my $fg          = wstr($conf{'color_match_fg'});
    my $bg          = wstr($conf{'color_match_bg'});
    my $filter      = wstr($conf{'colorize_filter'});

    # Buffer property

    my $bufname     = weechat::buffer_get_string($buff, 'full_name');
    my $re_prop_pat = weechat::buffer_get_string($buff, 'highlight_regex');
    my $buf_opt     = "weechat.buffer.${bufname}.highlight_regex";
    my $is_opt_set  = weechat::config_get("$buf_opt");
    my $buf_prop    = qq{$buf_opt "${re_prop_pat}"};

    # The buffer property was set with '/buffer set', meaning it is not saved in
    # configuration and will not show in /fset.
    # Thus replace /fset command with '/buffer setauto' in set_input().
    if ($is_opt_set eq '') {
        $buf_prop = qq{$bufname "${re_prop_pat}"};
        $buf_opt = $re_prop_pat;
        $is_opt  = 0;
    }

    # Just show the options.
    if ($args eq '') {
        my $opts = <<~"END";
            fmt
              $fmt_opt "${fmt}"

            debug
              $dbg_opt "${debug}"

            fg
              $fg_opt "${fg}"

            bg
              $bg_opt "${bg}"

            filter
              $filter_opt "${filter}"

            regex
              $regex_opt "${re_opt_pat}"

            prop
              $buf_prop
            END

        chkbuff(1);
        wprint('', "${prefix}$opts");

        return $ok;
    }

    # Check if 'fset' plugin is loaded.
    if (weechat::info_get('plugin_loaded', 'fset') eq '') {
        chkbuff(1);
        wprint('', "${prefix}fset plugin is not loaded");

        return $ok;
    }

    # Set options
    if ($args eq 'fmt') {
        set_input(1, $fmt_opt);
    }
    elsif ($args eq 'debug') {
        set_input(1, $dbg_opt);
    }
    elsif ($args eq 'fg') {
        set_input(1, $fg_opt);
    }
    elsif ($args eq 'bg') {
        set_input(1, $bg_opt);
    }
    elsif ($args eq 'filter') {
        set_input(1, $filter_opt);
    }
    elsif ($args eq 'regex') {
        set_input(1, $regex_opt);
    }
    # Set regex buffer property.
    elsif ($args eq 'prop') {
        set_input($is_opt, $buf_opt);
    }
    else {
        chkbuff(1);
        wprint('', "${prefix}wrong '${args}' argument");

        return $err;
    }

    return $ok;
}

# Debug color callback
#
# References:
#   https://weechat.org/files/doc/weechat/stable/weechat_user.en.html#colors_support
#   https://weechat.org/files/doc/stable/weechat_user.en.html#command_line_colors
#   https://weechat.org/files/doc/weechat/stable/weechat_user.en.html#colors
#   https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_color
#   https://github.com/weechat/weechat/blob/main/src/gui/gui-color.h
#   https://github.com/weechat/weechat/blob/main/src/gui/gui-color.c
#   https://github.com/weechat/weechat/blob/main/src/plugins/irc/irc-color.h
#   https://github.com/weechat/weechat/blob/main/src/plugins/irc/irc-color.c
#
# Notes:
#   - WeeChat supports 256 colors with 32767 color pairs (fg,bg combinations).
#   - IRC input color (Ctrl+c+c+color) is limited to 100 colors.
#     Also it sets the 'keep attributes' pipe '|' by default and can use RGB hex colors.
#     Plain Ctr+c+c resets colors while keepping the attributes.
#     It seems it cannot set blink, dim, and emphasis attributes.
#
#   - IRC input attributes (Ctrl+c+attr) can be removed when repeated.
#     The emphasis attribute overrides the normal colors and only its code resets
#     itself, so it should not be used.
#
#   - Most of 'weechat.color.chat.*' color codes are fixed (e.g. \03127 is 'chat_nick'
#     and \03128 is 'chat_delimiters'), that is, its code never changes when modifying
#     the color option.
#     Some tags like irc_join/part/quit use these codes.
#
# WeeChat's color codes patterns:
#
#   WeeChat color codes sequences start with the \031 escape, followed by a F,
#   optional attributes codes (*, !, /, _, %, ., |), and 2 to 5 digits (color codes).
#   E.g.
#     \031F|00             default color + past attributes
#
#   The F is replaced by a * if there is a background color, and a ~ separator
#   appears separating the fg,bg colors.
#   E.g.
#     \031*_08~09          underlined yellow on blue
#
#   If an IRC color between 16–98 is inserted with the Ctrl+c+c keys or a RGB hex
#   color is inserted with the Ctrl+c+d keys, the colors are prefixed with @.
#
#   E.g.
#     \031F@|00009         red color (FF0000)
#     \031*|01~@00127      IRC 01 color on IRC 50 color
#     \031*@|00005~@00014  purple (800080) on cyan (00FFFF)
#
#   Attributes:
#     \032\001             *  bold
#     \032\002             !  reverse
#     \032\003             /  italic
#     \032\004             _  underline
#     \032\005             %  blink
#     \032\006             .  dim
#                          |  keep attributes
#
#     \033\001             remove bold
#     \033\002             "      reverse
#     \033\003             "      italic
#     \033\004             "      underline
#     \033\005             "      blink
#     \033\006             "      dim
#
#     \031\034             reset color and keep attributes
#     \034                 reset color and attributes
#
#     \031E                emphasis
sub debug_color_cb
{
    my ($data, $buffer, $args) = @_;
    my $prefix = "dbgcolor\t";

    if ($args eq '') {
        chkbuff(1);
        wprint('', "${prefix}missing argument");

        return $err;
    }

    # Parse /dbgcolor arguments by first occurrence.

    my @args     = split / /, $args;
    my $len_args = scalar @args - 1;
    my $buff     = '';
    my $args_action;

    for (my $i = 0; $i <= $len_args; $i++) {
        # Get buffer.
        if ($i == 0 && $args[$i] eq '-buffer') {
            # Name
            if (defined $args[$i + 1]) {
                ++$i;
                $buff = weechat::buffer_search ('==', "$args[$i]");

                if ($buff eq '') {
                    chkbuff(1);
                    wprint($buff, "${prefix}failed to get '${args[$i]}' buffer name");

                    return $err;
                }
                # od/xxd
                if (! defined $args[$i + 1]) {
                    chkbuff(1) if $buff eq '';
                    wprint($buff, "${prefix}missing format argument");

                    return $err;
                }

                next;
            }
            else {
                chkbuff(1);
                wprint($buff, "${prefix}missing buffer argument");

                return $err;
            }
        }
        # od/xxd
        elsif ($args[$i] =~ /\A(?> od | xxd)\z/x) {
            my $fmt = $args[$i];

            # -eval/no
            if (defined $args[$i + 1]) {
                ++$i;

                if ($args[$i] =~ /\A-(?> (eval) | (no))\z/x) {
                    if (defined $args[$i + 1]) {
                        ++$i;

                        # Evaluate string.
                        if (defined $1) {
                            $args_action = eval_arg("@args[$i .. $len_args]");
                        }
                        # Do not decode IRC colors.
                        else {
                            $args_action = "@args[$i .. $len_args]";
                        }
                    }
                    else {
                        chkbuff(1) if $buff eq '';
                        wprint($buff, "${prefix}missing string argument");

                        return $err;
                    }
                }
                # Decode IRC colors.
                else {
                    $args_action = decode_arg("@args[$i .. $len_args]");
                }

                # Run command.
                chkbuff(1) if $buff eq '';
                wprint($buff, "${prefix}'${args_action}${color_reset}'");
                chkdump($buff, $fmt, $args_action);
            }
            else {
                chkbuff(1) if $buff eq '';
                wprint($buff, "${prefix}missing string argument");

                return $err;
            }

            last;
        }
        # Config format (od/xxd)
        else {
            if ($buff ne '') {
                wprint($buff, "${prefix}wrong format argument");
                return $err;
            }

            my $args_decode = decode_arg("@args[$i .. $len_args]");

            # Run command.
            chkbuff(1) if $buff eq '';
            wprint($buff, "${prefix}'${args_decode}${color_reset}'");
            chkdump($buff, wstr($conf{'debug_fmt'}), $args_decode);

            last;
        }
    }

    return $ok;
}

# Completion callbacks

sub comp_fmt_cb
{
    my ($data, $comp_item, $buff, $comp) = @_;

    weechat::completion_list_add($comp, 'od', 0,  weechat::WEECHAT_LIST_POS_SORT);
    weechat::completion_list_add($comp, 'xxd', 0, weechat::WEECHAT_LIST_POS_SORT);

    return $ok
}

sub comp_action_cb
{
    my ($data, $comp_item, $buff, $comp) = @_;

    weechat::completion_list_add($comp, '-eval', 0, weechat::WEECHAT_LIST_POS_SORT);
    weechat::completion_list_add($comp, '-no', 0,   weechat::WEECHAT_LIST_POS_SORT);

    return $ok
}

# Notify callback
#
# Get a message notification (brown) in the script buffer when there is a print
# (only useful in debug mode).
sub notify_cb
{
    my ($data, $hashref) = @_;

    $hashref->{'notify_level'} = 1;  # Message
    return $hashref;
}

# Colorize callback
#
# Notes:
#   - WeeChat regexes are case insensitive by default, so the script's regexes
#     must set the /i modifier.
#     Also they can be set to case sensitive with (?-i) at the start of the pattern
#     *only*, otherwise the regex will fail.
#
#   - WeeChat sets word boundaries by default in 'weechat.look.word_chars_highlight'
#     option, so it has to be empty for strings such as -WeeChat- to match correctly
#     in regex word boundaries, or substrings i.e. textWeeChat.
#
#     Note that editing 'word_chars_highlight' option affects the user's IRC $nick
#     mentions in channel/private/server buffers (see irc.look.highlight_{channel,pv,server}).
#
#   - To avoid mismatches, the 'highlight_regex' from buffer property has a higher
#     priority than the global option.
#
# Testing the 'preserve colors' algorithm:
#   1. Set debug mode to 'on':
#     /rset debug
#
#   2. Set highlight_regex option to '\bweechat\b':
#     /rset regex
#
#   3. Open another weechat instance, connect it to the same server and send this
#      private message to the first instance nick, so it can be highlighted:
#        /input insert /msg nick \x0305<\x03043 \x02\x0307WeeChat is awesome\x02 \x0314[0 user] \x0399\x1fhttps://github.com/\x0305w\x0355e\x0384e\x0302c\x0f\x0392h\x0309a\x0338t/weechat/ https\x1f\x16://weechat.org/
#
#      The string is inspired by ##hntop messages and modified to cover some corner
#      cases. It should colorize the matches and preserve all colors.
sub colorize_cb
{
    my ($data, $hashref) = @_;

    my $prefix    = "colorize_cb\t";
    my $buffer    = $hashref->{'buffer'};
    my $filtered  = $hashref->{'displayed'};
    my $highlight = $hashref->{'highlight'};
    my $message   = $hashref->{'message'};
    my $msg_nocolor;

    # Do not colorize when a message is filtered.
    return $hashref if $filtered eq '0' && wstr($conf{'colorize_filter'}) eq 'off';

    # Remove any color codes from message in order to match and colorize the
    # strings correctly.
    $msg_nocolor = weechat::string_remove_color($message, '');

    # Assert that the message string has any match from 'highlight_regex' option.
    my $hl_opt = weechat::string_has_highlight_regex($msg_nocolor, $re_opt_pat);

    # Get 'highlight_regex' pattern from buffer property and assert that there is
    # a match in the message.
    my $re_prop_pat = weechat::buffer_get_string($buffer, 'highlight_regex');
    my $hl_prop     = weechat::string_has_highlight_regex($msg_nocolor, $re_prop_pat);

    # Start processing if the message has a highlight.
    if ($highlight eq '1') {
        # and has a regex match.
        return $hashref if ! $hl_opt && ! $hl_prop;

        my $bufname = $hashref->{'buffer_name'};
        my $tags    = $hashref->{'tags'};
        my ($nick)  = $tags =~ /,nick_([^,]++),/;
        my $new_msg;

        my $info = <<~_;
            ${prefix}buffer: $bufname
            nick:   $nick
            _

        # Print buffer and nick information in debug mode.
        if (wstr($conf{'debug_mode'}) eq 'on') {
            chkbuff();
            wprint('', $info);
        }

        # Debug the pre-colorized messages.
        pdbg($prefix, '$message',     1, $message);
        pdbg($prefix, '$msg_nocolor', 1, $msg_nocolor);

        # Preserve colors
        #
        # If the line string is already colored, capture every color code before
        # the regex match, for restoration after regex colorizing. Otherwise string
        # colors after the match are reset.

        # Check if message has any color codes.
        if ($message =~ /$colors_rgx | $attr_rgx/x) {
            my $color_codes = '';
            my $idx         = 0;
            my $match       = 0;
            my $uniq_esc    = "\o{035}";

            # Mark the uncolored message with unique escapes to idenfity the matches
            # positions.
            $msg_nocolor =~ s/$re_opt_pat/${uniq_esc}${&}$uniq_esc/gi  if ! $hl_prop && $hl_opt;
            $msg_nocolor =~ s/$re_prop_pat/${uniq_esc}${&}$uniq_esc/gi if $hl_prop;

            # Remove double sequence of unique escapes from sequential matches.
            $msg_nocolor =~ s/${uniq_esc}{2}+//g;
            pdbg($prefix, '$msg_nocolor', 1, $msg_nocolor);

            # Split all color codes and bytes from the messages.
            my @split_msg    = grep { defined $_ && $_ ne '' } split /$split_rgx/, $message;
            my @split_msg_nc = grep { defined $_ && $_ ne '' } split /$split_rgx/, $msg_nocolor;

            # Debug the split arrays.
            #sdbg($prefix, 'split_msg',    \@split_msg);
            #sdbg($prefix, 'split_msg_nc', \@split_msg_nc);

            # Iterate through the original split array, comparing every byte against
            # the uncolored array; while reconstructing the new message with saved
            # color codes.
            foreach my $i (@split_msg) {
                #pdbg($prefix, '$i', 0, $i);
                #pdbg($prefix, "\$split_msg_nc[$idx]", 0, $split_msg_nc[$idx]);
                #wprint('', '');

                # It is a color code, so append its codes to be restored.
                if ($i =~ /\A(?> $colors_rgx | $attr_rgx)\z/x) {
                    $color_codes .= $i;
                    #pdbg($prefix, '$color_codes', 0, $color_codes);

                    # Append the codes if not inside a regex match.
                    $new_msg .= $i unless $match;

                    next;
                }
                # Remove saved codes if a reset code is found.
                elsif ($i eq $color_reset) {
                    $new_msg     .= $i unless $match;
                    $color_codes  = '';

                    next;
                }
                elsif (defined $split_msg_nc[$idx]) {
                    # It is a char, so compare it against the uncolored's char.
                    if ($i eq $split_msg_nc[$idx]) {
                        $new_msg .= $i;
                        ++$idx;

                        next;
                    }
                    # If the char is in a regex match and uncolored's is a unique
                    # escape, restore the saved codes, then advance the index.
                    elsif ($match && $split_msg_nc[$idx] eq $uniq_esc) {
                        #pdbg($prefix, "\$split_msg_nc[$idx + 1]", 0, $split_msg_nc[$idx + 1]);

                        # If the chars match, advance the index.
                        if ($split_msg_nc[$idx + 1] eq $i) {
                            $new_msg .= "${color_reset}${color_codes}${i}";
                            $idx     += 2;
                            $match    = 0;

                            next;
                        }
                    }
                    # It is the start of a colorized regex match (\035), so colorize
                    # the new msg, then advance uncolored's index to the current char.
                    elsif ($split_msg_nc[$idx] eq $uniq_esc) {
                        #pdbg($prefix, "\$split_msg_nc[$idx + 1]", 0, $split_msg_nc[$idx + 1]);

                        ++$idx;
                        $new_msg .= "${color_reset}$color_match" . $split_msg_nc[$idx];
                        $match    = 1;

                        # If the chars match, advance the index.
                        if ($i eq $split_msg_nc[$idx]) {
                            ++$idx;
                            next;
                        }
                    }
                }
            }
        }
        # Uncolored message, so colorize it normally.
        else {
            $msg_nocolor =~ s/$re_opt_pat/${color_match}${&}$color_reset/gi  if ! $hl_prop && $hl_opt;
            $msg_nocolor =~ s/$re_prop_pat/${color_match}${&}$color_reset/gi if $hl_prop;

            $new_msg = $msg_nocolor;
        }

        # Debug the colorized message.
        pdbg($prefix, '$new_msg', 1, $new_msg);

        # Update the hashtable.
        $hashref->{'message'} = $new_msg;
    }

    # Debug the hashtable.
    #wprint('', "${prefix}\$hashref = " . Dumper $hashref);

    return $hashref;
}

# Update colors callback
sub upd_colors_cb
{
    my ($data, $option, $value) = @_;

    # Get the option name and update its new value.
    my ($prog, $section, $opt) = split /\./, $option;
    set_colors() if $opt =~ /\Amatch_[bf]g\z/;

    return $ok;
}

# Get 'highlight_regex' callback
sub get_regex_cb
{
    $re_opt_pat = wstr(weechat::config_get($regex_opt));

    if ($re_opt_pat eq '') {
        chkbuff();
        wprint('', "get_regex_cb\tfailed to get or empty '${regex_opt}' option");
        return $err;
    }

    return $ok;
}

# Init and configuration

# Set colors of the regex matches.
#
# Notes:
#   - The format is 'foreground,background' and it must be a valid weechat color.
#   - 'default' value uses the terminal colors.
sub set_colors
{
    my $fg = wstr($conf{'color_match_fg'});
    my $bg = wstr($conf{'color_match_bg'});

    $color_match = wcolor("${fg},$bg");
}

# Read config file from disk and update the $conf_file pointers.
sub config_read
{
    my $rc = weechat::config_read($conf_file);

    if ($rc != 0) {
        if ($rc == weechat::WEECHAT_CONFIG_READ_MEMORY_ERROR) {
            wprint('', "${prog}\tnot enough memory to read config file");
        }
        elsif ($rc == weechat::WEECHAT_CONFIG_READ_FILE_NOT_FOUND) {
            wprint('', "${prog}\tconfig file was not found");
        }
    }

    return $rc;
}

# Handle config errors.
sub chkconf
{
    my ($conf_ptr, $ptr, $type) = @_;

    if ($ptr eq '') {
        wprint('', "${prog}\tfailed to create config $type");

        weechat::config_free($conf_ptr) if $conf_ptr ne '';
        return 1;
    }
}

# Create config file options of a section.
sub set_opts
{
    my ($conf, $sect, $options) = @_;
    my $opt;

    foreach my $i ($options->@*) {
        $opt = $i->{'option'};

        $conf{$opt} = weechat::config_new_option(
            $conf,
            $sect,
            $i->{'name'},
            $i->{'opt_type'},
            $i->{'desc'},
            $i->{'str_val'},
            $i->{'min_val'},
            $i->{'max_val'},
            $i->{'default'},
            $i->{'value'},
            $i->{'null_val'},
            '', '', '', '', '', '',
        );
    }

    return 1 if chkconf($conf_file, $conf{$opt}, "'${opt}' option");
}

sub config_init
{
    $conf_file = weechat::config_new($prog, '', '');
    return 1 if chkconf('', $conf_file, 'file');

    # Color section
    {
        my $sect       = 'color';
        my $sect_color = weechat::config_new_section($conf_file, $sect, 0, 0, '', '', '', '', '', '', '', '', '', '');
        return 1 if chkconf($conf_file, $sect_color, "'${sect}' section");

        # Options
        my @opt = (
            {
                'option'   => 'color_match_fg',
                'name'     => 'match_fg',
                'opt_type' => 'color',
                'desc'     => 'foreground WeeChat color that colorizes the regex matches',
                'str_val'  => '',
                'min_val'  => 0,
                'max_val'  => 0,
                'default'  => 'black',
                'value'    => 'black',
                'null_val' => 0,
            },
            {
                'option'   => 'color_match_bg',
                'name'     => 'match_bg',
                'opt_type' => 'color',
                'desc'     => 'background WeeChat color that colorizes the regex matches',
                'str_val'  => '',
                'min_val'  => 0,
                'max_val'  => 0,
                'default'  => '153',
                'value'    => '153',
                'null_val' => 0,
            },
        );
        return 1 if set_opts($conf_file, $sect_color, \@opt);
    }

    # Debug section
    {
        my $sect     = 'debug';
        my $sect_dbg = weechat::config_new_section($conf_file, $sect, 0, 0, '', '', '', '', '', '', '', '', '', '');
        return 1 if chkconf($conf_file, $sect_dbg, "'${sect}' section");

        # Options
        my @opt = (
            {
                'option'   => 'debug_fmt',
                'name'     => 'fmt',
                'opt_type' => 'enum',
                'desc'     => 'hex dump format used by /dbgcolor: od = simulate "od -An -tx1c", xxd = simulate "xxd -g1 -R always"',
                'str_val'  => 'od|xxd',
                'min_val'  => 0,
                'max_val'  => 0,
                'default'  => 'od',
                'value'    => 'od',
                'null_val' => 0,
            },
            {
                'option'   => 'debug_mode',
                'name'     => 'mode',
                'opt_type' => 'boolean',
                'desc'     => 'show debug information',
                'str_val'  => '',
                'min_val'  => 0,
                'max_val'  => 0,
                'default'  => 'off',
                'value'    => 'off',
                'null_val' => 0,
            }
        );
        return 1 if set_opts($conf_file, $sect_dbg, \@opt);
    }

    # Look section
    {
        my $sect       = 'look';
        my $sect_color = weechat::config_new_section($conf_file, $sect, 0, 0, '', '', '', '', '', '', '', '', '', '');
        return 1 if chkconf($conf_file, $sect_color, "'${sect}' section");

        # Options
        my @opt = (
            {
                'option'   => 'colorize_filter',
                'name'     => 'colorize_filter',
                'opt_type' => 'boolean',
                'desc'     => 'colorize regex matches in filtered messages from /filter',
                'str_val'  => '',
                'min_val'  => 0,
                'max_val'  => 0,
                'default'  => 'off',
                'value'    => 'off',
                'null_val' => 0,
            },
        );
        return 1 if set_opts($conf_file, $sect_color, \@opt);
    }

    return 0;
}

# Main
#
# Notes:
#   - The colorize_cb hook priority needs to be lower than the colorize_nicks.py
#     script, otherwise if a nick matches a highlight regex, the *_nicks.py
#     script will colorize it and replace the match colors.
#
#     Also the priority is lower than the colorize_lines.pl script, but it does
#     not matter since *_lines.pl only replaces colors after reset codes.
if (weechat::register(
        $script{'prog'},
        $script{'author'},
        $script{'version'},
        $script{'licence'},
        $script{'desc'},
        '',
        ''
    )) {
    # Initialize the script settings.
    {
        # Configuration file.
        return if config_init();
        return if config_read() != 0;

        # Set regex match colors.
        set_colors();

        # Get highlight_regex pattern.
        get_regex_cb();
    }

    # Hooks
    {
        # Update an option when it changes.
        weechat::hook_config("${prog}.color.*", 'upd_colors_cb', '');  # Regex match color
        weechat::hook_config($regex_opt, 'get_regex_cb', '');          # highlight_regex

        weechat::hook_line('400|', '', '', 'colorize_cb', '');         # Colorize
        weechat::hook_line('', "perl.$prog", '', 'notify_cb', '');     # Notify

        # Commands
        {
            # Argument completions
            weechat::hook_completion('plugin_fmt', 'fmt args completion', 'comp_fmt_cb', '');           # 'od' and 'xxd'
            weechat::hook_completion('plugin_action', 'action args completion', 'comp_action_cb', '');  # '-eval' and '-no'

            # Format commands descriptions.
            my ($dbg_fmt, $dbg_arg, $hl_arg) = fmt_desc();

            # dbgcolor
            weechat::hook_command(
                'dbgcolor',
                "debug weechat's strings color codes",
                $dbg_fmt,
                $dbg_arg,
                '%(plugin_fmt) |%(plugin_action) %(eval_variables) %-
                  || -buffer %(buffers_plugins_names) %(plugin_fmt) |%(plugin_action) %(eval_variables) %-',
                'debug_color_cb',
                ''
            );

            # rset
            weechat::hook_command(
                'rset',
                "fast set $prog options and regexes",
                '[fmt|debug|fg|bg|filter|regex|prop]',
                $hl_arg,
                'fmt %-
                  || debug  %-
                  || fg     %-
                  || bg     %-
                  || filter %-
                  || regex  %-
                  || prop   %-',
                'regex_set_cb',
                ''
            );
        }
    }
}
