#
# Copyright (c) 2008-2009 by FlashCode <flashcode@flashtux.org>
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
# 2009-12-17, FlashCode <flashcode@flashtux.org>:
#     version 0.7: add levels, fix bugs with pause
# 2009-12-16, drubin <drubin [@] smartcube [dot] co[dot]za>:
#     version 0.6: add key for pause, basic doc and auto jump to buffer
# 2009-06-21, FlashCode <flashcode@flashtux.org>:
#     version 0.5: fix bug with weetris buffer after /upgrade
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.4: sync with last API changes, fix problem with key alt-n
# 2008-11-14, FlashCode <flashcode@flashtux.org>:
#     version 0.3: minor code cleanup
# 2008-11-12, FlashCode <flashcode@flashtux.org>:
#     version 0.2: hook timer only when weetris buffer is open
# 2008-11-05, FlashCode <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-04-30, FlashCode <flashcode@flashtux.org>:
#     script creation

use strict;

my $version = "0.7";

my $weetris_buffer = "";
my $timer = "";
my $level = 1;
my $max_level = 10;

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
my $paused = 0;
my $lines = 0;
my ($item_x, $item_y) = (0, 0);
my $item_number = 0;
my $item_form = 0;
my $title = "WeeTris.pl $version - enjoy!  |  Keys: arrows: move/rotate, alt-N: new game, alt-P: pause";


sub buffer_close
{
    $weetris_buffer = "";
    if ($timer ne "")
    {
        weechat::unhook($timer);
        $timer = "";
    }
    
    weechat::print("", "Thank you for playing WeeTris!");
    return weechat::WEECHAT_RC_OK;
}

sub display_line
{
    my $y = $_[0];
    my $str = " │";
    if ($paused eq 1)
    {
        if ($y == $nby / 2)
        {
            my $paused = "  " x $nbx;
            my $index = (($nbx * 2) - 6) / 2;
            substr($paused, $index, 6) = "PAUSED";
            $str .= $paused;
        }
        else
        {
            $str .= "  " x $nbx;
        }
    }
    else
    {
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
    }
    $str .= weechat::color(",default")."│";
    weechat::print_y($weetris_buffer, $start_y + $y + 1, $str);
}

sub display_level_lines
{
    my $plural = "";
    $plural = "s" if ($lines > 1);
    my $str = sprintf(" Level %-3d %6d line%s", $level, $lines, $plural);
    weechat::print_y($weetris_buffer, $start_y + $nby + 2, $str);
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
    weechat::print_y($weetris_buffer, $start_y, " ┌".("──" x $nbx)."┐");
    
    # middle
    for (my $y = 0; $y < $nby; $y++)
    {
        display_line($y);
    }
    
    # bottom bar
    weechat::print_y($weetris_buffer, $start_y + $nby + 1, " └".("──" x $nbx)."┘");
    
    apply_item(0);
}

sub new_form
{
    $item_number = int(rand($#items + 1));
    $item_form = $items[$item_number];
    $item_x = ($nbx / 2) - 2;
    $item_y = 0;
}

sub init_timer
{
    weechat::unhook($timer) if ($timer ne "");
    my $delay = 700 - (($level - 1) * 60);
    $delay = 100 if ($delay < 100);
    $timer = weechat::hook_timer($delay, 0, 0, "weetris_timer", "");
}

sub new_game
{
    weechat::print_y($weetris_buffer, $start_y + $nby + 2, "");
    for (my $y = 0; $y < $nby; $y++)
    {
        $matrix[$y] = " " x $nbx;
    }
    new_form();
    $playing = 1;
    $paused = 0;
    $lines = 0;
    $level = 1;
    init_timer();
    display_all();
    display_level_lines();
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
        my $new_level = int(($lines / 10) + 1);
        $new_level = $max_level if ($new_level > $max_level);
        if ($new_level != $level)
        {
            $level = $new_level;
            init_timer();
        }
        display_level_lines();
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
        $paused = 0;
        weechat::print_y($weetris_buffer, $start_y + $nby + 2, ">> End of game, score: $lines lines, level $level (alt-N to restart) <<");
    }
}

sub weetris_init
{
    $weetris_buffer = weechat::buffer_search("perl", "weetris");
    if ($weetris_buffer eq "")
    {
        $weetris_buffer = weechat::buffer_new("weetris", "", "", "buffer_close", "");
    }
    if ($weetris_buffer ne "")
    {
        weechat::buffer_set($weetris_buffer, "type", "free");
        weechat::buffer_set($weetris_buffer, "title", $title);
        weechat::buffer_set($weetris_buffer, "key_bind_meta2-A", "/weetris up");
        weechat::buffer_set($weetris_buffer, "key_bind_meta2-B", "/weetris down");
        weechat::buffer_set($weetris_buffer, "key_bind_meta2-D", "/weetris left");
        weechat::buffer_set($weetris_buffer, "key_bind_meta2-C", "/weetris right");
        weechat::buffer_set($weetris_buffer, "key_bind_meta-n", "/weetris new_game");
        weechat::buffer_set($weetris_buffer, "key_bind_meta-p", "/weetris pause");
        new_game();
        weechat::buffer_set($weetris_buffer, "display", "1");
    }
}

sub weetris
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    if ($weetris_buffer ne "")
    {
        weechat::buffer_set($weetris_buffer, "display", "1");
    }
    if ($weetris_buffer eq "")
    {
        weetris_init();
    }
    
    if ($args eq "new_game")
    {
        new_game();
    }
    
    if ($args eq "pause")
    {
        if ($playing eq 1)
        {
            $paused ^= 1;
            display_all();
        }
    }
    
    if (($playing eq 1) && ($paused eq 0))
    {
        if ($args eq "up")
        {
            my $new_form = rotation($item_form);
            if (is_possible($item_x, $item_y, $new_form))
            {
                $item_form = $new_form;
                display_all();
            }
        }
        if ($args eq "down")
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
        if ($args eq "left")
        {
            if (is_possible($item_x - 1, $item_y, $item_form))
            {
                $item_x--;
                display_all();
            }
        }
        if ($args eq "right")
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
    if (($weetris_buffer ne "") && ($playing eq 1) && ($paused eq 0))
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
weechat::hook_command("weetris", "Run WeeTris", "", 
                      "Keys:\n".
                      "   arrow up: rotate current item\n".
                      " arrow left: move item to the left\n".
                      "arrow right: move item to the right\n".
                      "      alt+n: restart the game\n".
                      "      alt+p: pause current game", 
                      "", "weetris", "");
$weetris_buffer = weechat::buffer_search("perl", "weetris");
if ($weetris_buffer ne "")
{
    weetris_init();
}
