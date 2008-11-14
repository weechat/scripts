#
# Copyright (c) 2008 by FlashCode <flashcode@flashtux.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Tetris game for WeeChat.
#
# History:
# 2008-11-14, FlashCode <flashcode@flashtux.org>:
#     version 0.3: minor code cleanup
# 2008-11-12, FlashCode <flashcode@flashtux.org>:
#     version 0.2: hook timer only when weetris buffer is open
# 2008-11-05, FlashCode <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-04-30, FlashCode <flashcode@flashtux.org>:
#     script creation

use strict;

my $version = "0.3";

my $buffer = "";
my $timer = "";

my ($nbx, $nby) = (10, 20);
my $start_y = 0;
my @matrix = ();

# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# |32768|16384| 8192| 4096|          |  8  | 128 | 2048|32768|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# | 2048| 1024| 512 | 256 |          |  4  |  64 | 1024|16384|
# |     |     |     |     |  after   |     |     |     |     |
# -------------------------  rotate  -------------------------
# |     |     |     |     |   ===>   |     |     |     |     |
# | 128 |  64 |  32 |  16 |          |  2  |  32 | 512 | 8192|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------
# |     |     |     |     |          |     |     |     |     |
# |  8  |  4  |  2  |  1  |          |  1  |  16 | 256 | 4096|
# |     |     |     |     |          |     |     |     |     |
# -------------------------          -------------------------

my @items = (1024+512+64+32,    # O
             2048+1024+512+256, # I
             2048+1024+512+64,  # T
             2048+1024+512+128, # L
             2048+1024+512+32,  # J
             1024+512+128+64,   # S
             2048+1024+64+32,   # Z
             );
my @item_color = ("red", "blue", "brown", "green", "brown", "cyan", "magenta");
my @item_x_inc = (3, 2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0);
my @item_y_inc = (3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0);
my @item_rotation = (4096, 256, 16, 1, 8192, 512, 32, 2, 16384, 1024, 64, 4, 32768, 2048, 128, 8); 

my $playing = 0;
my $lines = 0;
my ($item_x, $item_y) = (0, 0);
my $item_number = 0;
my $item_form = 0;

sub buffer_close
{
    $buffer = "";
    if ($timer ne "")
    {
        weechat::unhook($timer);
        $timer = "";
    }
    
    weechat::print("", "Thank you for playing WeeTris!");
    return weechat::WEECHAT_RC_OK;
}

sub weetris_init
{
    $buffer = weechat::buffer_new("weetris", "", "buffer_close");
    if ($buffer ne "")
    {
        weechat::buffer_set($buffer, "type", "free");
        weechat::buffer_set($buffer, "title", "WeeTris.pl script - enjoy!");
        weechat::buffer_set($buffer, "key_bind_meta2-A", "/weetris up");
        weechat::buffer_set($buffer, "key_bind_meta2-B", "/weetris down");
        weechat::buffer_set($buffer, "key_bind_meta2-D", "/weetris left");
        weechat::buffer_set($buffer, "key_bind_meta2-C", "/weetris right");
        weechat::buffer_set($buffer, "key_bind_meta-N", "/weetris new_game");
        if ($timer eq "")
        {
            $timer = weechat::hook_timer(700, 0, 0, "weetris_timer");
        }
    }
}

sub display_line
{
    my $y = $_[0];
    my $str = " │";
    for (my $x = 0; $x < $nbx; $x++)
    {
        my $char = substr($matrix[$y], $x, 1);
        if ($char eq " ")
        {
            $str .= weechat::color(",default");
        }
        else
        {
            $str .= weechat::color(",".$item_color[$char]);
        }
        $str .= "  ";
    }
    $str .= weechat::color(",default")."│";
    weechat::print_y($buffer, $start_y + $y + 1, $str);
}

sub apply_item
{
    my $char = " ";
    $char = $item_number if ($_[0] eq 1);
    for (my $i = 0; $i < 16; $i++)
    {
        if (($item_form & (1 << $i)) > 0)
        {
            substr($matrix[$item_y + $item_y_inc[$i]], $item_x + $item_x_inc[$i], 1) = $char;
        }
    }
}

sub display_all
{
    apply_item(1);
    
    # bar on top
    weechat::print_y($buffer, $start_y, " ┌".("──" x $nbx)."┐");
    
    # middle
    for (my $y = 0; $y < $nby; $y++)
    {
        display_line($y);
    }
    
    # bottom bar
    weechat::print_y($buffer, $start_y + $nby + 1, " └".("──" x $nbx)."┘");
    
    apply_item(0);
}

sub new_form
{
    $item_number = int(rand($#items + 1));
    $item_form = $items[$item_number];
    $item_x = ($nbx / 2) - 2;
    $item_y = 0;
}

sub new_game
{
    weechat::print_y($buffer, $start_y + $nby + 2, "");
    for (my $y = 0; $y < $nby; $y++)
    {
        $matrix[$y] = " " x $nbx;
    }
    new_form();
    $playing = 1;
    $lines = 0;
}

sub rotation
{
    my $form = $_[0];
    my $new_form = 0;
    for (my $i = 0; $i < 16; $i++)
    {
        if (($form & (1 << $i)) > 0)
        {
            $new_form = $new_form | $item_rotation[$i];
        }
    }
    return $new_form;
}

sub is_possible
{
    my ($new_x, $new_y, $new_form) = ($_[0], $_[1], $_[2]);
    for (my $i = 0; $i < 16; $i++)
    {
        if (($new_form & (1 << $i)) > 0)
        {
            return 0 if (($new_x + $item_x_inc[$i] < 0)
                         || ($new_x + $item_x_inc[$i] >= $nbx)
                         || ($new_y + $item_y_inc[$i] < 0)
                         || ($new_y + $item_y_inc[$i] >= $nby)
                         || (substr($matrix[$new_y + $item_y_inc[$i]], $new_x + $item_x_inc[$i], 1) ne " "));
        }
    }
    return 1;
}

sub remove_completed_lines
{
    my $y = $nby - 1;
    my $lines_removed = 0;
    while ($y >= 0)
    {
        if (index($matrix[$y], " ") == -1)
        {
            for (my $i = $y; $i >= 0; $i--)
            {
                if ($i == 0)
                {
                    $matrix[$i] = " " x $nbx;
                }
                else
                {
                    $matrix[$i] = $matrix[$i - 1];
                }
            }
            $lines++;
            $lines_removed = 1;
        }
        else
        {
            $y--;
        }
    }
    if ($lines_removed)
    {
        my $plural = "";
        $plural = "s" if ($lines > 1);
        my $str = sprintf("%7d line%s", $lines, $plural);
        weechat::print_y($buffer, $start_y + $nby + 2, $str);
    }
}

sub end_of_item
{
    apply_item(1);
    new_form();
    if (is_possible($item_x, $item_y, $item_form))
    {
        remove_completed_lines();
    }
    else
    {
        $item_form = 0;
        $playing = 0;
        weechat::print_y($buffer, $start_y + $nby + 2, ">> End of game, score: $lines lines (alt-N to restart) <<");
    }
}

sub weetris
{
    if ($buffer eq "")
    {
        weetris_init();
        new_game();
        apply_item(1);
        display_all();
        weechat::buffer_set($buffer, "display", "1");
    }
    
    if ($_[1] eq "new_game")
    {
        new_game();
        display_all();
    }
    
    if ($playing eq 1)
    {
        if ($_[1] eq "up")
        {
            my $new_form = rotation($item_form);
            if (is_possible($item_x, $item_y, $new_form))
            {
                $item_form = $new_form;
                display_all();
            }
        }
        if ($_[1] eq "down")
        {
            if (is_possible($item_x, $item_y + 1, $item_form))
            {
                $item_y++;
                display_all();
            }
            else
            {
                end_of_item();
            }
        }
        if ($_[1] eq "left")
        {
            if (is_possible($item_x - 1, $item_y, $item_form))
            {
                $item_x--;
                display_all();
            }
        }
        if ($_[1] eq "right")
        {
            if (is_possible($item_x + 1, $item_y, $item_form))
            {
                $item_x++;
                display_all();
            }
        }
    }
    
    return weechat::WEECHAT_RC_OK;
}

sub weetris_timer
{
    if (($buffer ne "") && ($playing eq 1))
    {
        if (is_possible($item_x, $item_y + 1, $item_form))
        {
            $item_y++;
        }
        else
        {
            end_of_item();
        }
        display_all();
    }
    return weechat::WEECHAT_RC_OK;
}

weechat::register("weetris", "FlashCode <flashcode\@flashtux.org>",
                  $version, "GPL3", "Tetris game for WeeChat, yeah!", "", "");
weechat::hook_command("weetris", "Run WeeTris", "", "", "", "weetris");
