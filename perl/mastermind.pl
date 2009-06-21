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

# Mastermind game for WeeChat.
#
# History:
# 2009-06-21, FlashCode <flashcode@flashtux.org>:
#     version 0.3: fix bug with mastermind buffer after /upgrade
# 2009-05-02, FlashCode <flashcode@flashtux.org>:
#     version 0.2: sync with last API changes, fix problem with keys
# 2008-11-14, FlashCode <flashcode@flashtux.org>:
#     version 0.1: first official version
# 2008-11-13, FlashCode <flashcode@flashtux.org>:
#     script creation

use strict;

my $version = "0.3";

my $mm_buffer = "";

# number of pegs by line
my $nbx = 4;
# number of lines
my $nby = 12;
# peg colors
my @peg_color = ("red", "white", "yellow", "green",
                 "blue", "lightcyan", "magenta", "lightmagenta");

my $start_y = 0;
my @matrix = ();
my @matrix_result = ();
my $pattern = "";
my $playing = 0;
my $current_line = 0;
my $column_selected = 0;
my $color_selected = 0;
my $display_solution = 0;
my $message_end = "";

sub buffer_close
{
    $mm_buffer = "";
    
    weechat::print("", "Thank you for playing Mastermind!");
    return weechat::WEECHAT_RC_OK;
}

sub mastermind_init
{
    $mm_buffer = weechat::buffer_search("perl", "mastermind");
    if ($mm_buffer eq "")
    {
        $mm_buffer = weechat::buffer_new("mastermind", "", "", "buffer_close", "");
    }
    if ($mm_buffer ne "")
    {
        weechat::buffer_set($mm_buffer, "type", "free");
        weechat::buffer_set($mm_buffer, "title", "mastermind.pl script - enjoy!");
        weechat::buffer_set($mm_buffer, "key_bind_meta2-A",     "/mastermind up");
        weechat::buffer_set($mm_buffer, "key_bind_meta2-B",     "/mastermind down");
        weechat::buffer_set($mm_buffer, "key_bind_meta2-D",     "/mastermind left");
        weechat::buffer_set($mm_buffer, "key_bind_meta2-C",     "/mastermind right");
        weechat::buffer_set($mm_buffer, "key_bind_meta-n",      "/mastermind new_game");
        weechat::buffer_set($mm_buffer, "key_bind_meta-q",      "/mastermind set");
        weechat::buffer_set($mm_buffer, "key_bind_meta-ctrl-M", "/mastermind check_pattern");
        # if you want to cheat and see solution, uncomment that or just issue
        # command: /mastermind toggle_solution
        # (shame on you if you do that!)
        #weechat::buffer_set($mm_buffer, "key_bind_meta-Z",      "/mastermind toggle_solution");
        
        new_game();
        display_all();
        weechat::buffer_set($mm_buffer, "display", "1");
    }
}

sub get_line_for_display
{
    my $line = $_[0];
    my $selected = $_[1];
    my $str = "";
    for (my $x = 0; $x < $nbx; $x++)
    {
        my $char = substr($line, $x, 1);
        $str .= ($selected && ($x == $column_selected)) ?
            weechat::color("white")."»" : weechat::color("default")." ";
        $str .= ($char eq " ") ?
            weechat::color("cyan").".." : weechat::color($peg_color[$char])."██";
        $str .= ($selected && ($x == $column_selected)) ?
            weechat::color("white")."«" : weechat::color("default")." ";
    }
    return $str;
}

sub display_line
{
    my $y = $_[0];
    my $str = " │";
    $str .= ($y == $current_line) ? weechat::color("lightgreen").">  ".weechat::color("default") : "   ";
    $str .= get_line_for_display($matrix[$y], ($y == $current_line));
    $str .= " │ ";
    $str .= get_line_for_display($matrix_result[$y], 0);
    $str .= ($y == $current_line) ? weechat::color("lightgreen")."<".weechat::color("default") : " ";
    $str .= "│";
    if ($y <= $#peg_color)
    {
        $str .= "  ".weechat::color("white")
            .(($y == $color_selected) ? "»" : " ")
            .weechat::color($peg_color[$y])."██"
            .weechat::color("white").(($y == $color_selected) ? "«" : " ");
    }
    weechat::print_y($mm_buffer, $start_y + 2 + ($y * 2), $str);
}

sub display_all
{
    # info line
    weechat::print_y($mm_buffer, $start_y,
                     weechat::color("cyan")."Keys: "
                     .weechat::color("lightcyan")."alt-N"
                     .weechat::color("cyan").": new game -- "
                     .weechat::color("lightcyan")."arrows"
                     .weechat::color("cyan").": select row/color -- "
                     .weechat::color("lightcyan")."alt-Q"
                     .weechat::color("cyan").": set color -- "
                     .weechat::color("lightcyan")."alt-Ret"
                     .weechat::color("cyan").": check pattern");
    
    # bar on top
    weechat::print_y($mm_buffer, $start_y + 1,
                     " ┌───".("────" x $nbx)."───".("────" x $nbx)."─┐");
    
    # middle
    for (my $y = 0; $y < $nby; $y++)
    {
        display_line($y);
        if ($y < $nby - 1)
        {
            weechat::print_y($mm_buffer, $start_y + 2 + ($y * 2) + 1,
                             " │   ".("    " x $nbx)." │ ".("    " x $nbx)." │");
        }
    }
    
    # bottom bar
    weechat::print_y($mm_buffer, $start_y + 2 + (($nby - 1) * 2) + 1,
                     " └───".("────" x $nbx)."───".("────" x $nbx)."─┘");
    
    # display solution and message
    weechat::print_y($mm_buffer, $start_y + 2 + (($nby - 1) * 2) + 3,
                     ($display_solution) ? 
                     "     ".get_line_for_display($pattern, 0)
                     .weechat::color("default")."  ".$message_end
                     : "");
}

sub random_pattern
{
    $pattern = " " x $nbx;
    for (my $i = 0; $i < $nbx; $i++)
    {
        substr($pattern, $i, 1) = rand($#peg_color);
    }
}

sub new_game
{
    for (my $y = 0; $y < $nby; $y++)
    {
        $matrix[$y] = " " x $nbx;
        $matrix_result[$y] = " " x $nbx;
    }
    random_pattern();
    $playing = 1;
    $current_line = 0;
    $column_selected = 0;
    $color_selected = 0;
    $display_solution = 0;
    $message_end = "";
}

sub set_color_in_matrix
{
    my ($x, $y, $color) = ($_[0], $_[1], $_[2]);
    my $char = " ";
    $char = $color if ($color >= 0);
    substr($matrix[$y], $x, 1) = $char;
}

sub check_pattern
{
    my $temp_guess = $matrix[$current_line];
    my $temp_pattern = $pattern;
    my $good_position = 0;
    my $bad_position = 0;
    
    # check for pegs at good position
    for (my $i = 0; $i < $nbx; $i++)
    {
        if (substr($temp_guess, $i, 1) eq substr($temp_pattern, $i, 1))
        {
            $good_position++;
            substr($temp_guess, $i, 1) = " ";
            substr($temp_pattern, $i, 1) = " ";
        }
    }
    # check for pegs at wrong position
    for (my $i = 0; $i < $nbx; $i++)
    {
        my $char_user = substr($temp_guess, $i, 1);
        if ($char_user ne " ")
        {
            my $found = 0;
            for (my $j = 0; $j < $nbx; $j++)
            {
                if (!$found && ($j != $i) && (substr($temp_pattern, $j, 1) eq $char_user))
                {
                    substr($temp_pattern, $j, 1) = " ";
                    $found = 1;
                }
            }
            $bad_position++ if ($found);
        }
    }
    
    # build result string
    my $result = " " x $nbx;
    for (my $i = 0; $i < $good_position; $i++)
    {
        substr($result, $i, 1) = 0;
    }
    for (my $i = 0; $i < $bad_position; $i++)
    {
        substr($result, $good_position + $i, 1) = 1;
    }
    $matrix_result[$current_line] = $result;
    if ($good_position == $nbx)
    {
        # player wins!
        $message_end = weechat::color("lightgreen")."  << Congratulations! >>";
        $display_solution = 1;
        $playing = 0;
    }
    else
    {
        if ($current_line == ($nby - 1))
        {
            # player looses!
            $message_end = weechat::color("lightred")."  >> You loose... <<";
            $display_solution = 1;
            $playing = 0;
        }
        else
        {
            $current_line++;
            $matrix[$current_line] = $matrix[$current_line - 1];
        }
    }
    display_all();
}

sub mastermind
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    
    if ($mm_buffer eq "")
    {
        mastermind_init();
    }
    
    if ($args eq "new_game")
    {
        new_game();
        display_all();
    }
    
    if ($playing eq 1)
    {
        if ($args eq "up")
        {
            if ($color_selected > 0)
            {
                $color_selected--;
                display_all();
            }
        }
        if ($args eq "down")
        {
            if ($color_selected < $#peg_color)
            {
                $color_selected++;
                display_all();
            }
        }
        if ($args eq "left")
        {
            if ($column_selected > 0)
            {
                $column_selected--;
                display_all();
            }
        }
        if ($args eq "right")
        {
            if ($column_selected < $nbx - 1)
            {
                $column_selected++;
                display_all();
            }
        }
        if ($args eq "set")
        {
            set_color_in_matrix($column_selected, $current_line,
                                $color_selected);
            $column_selected++;
            $column_selected = 0 if ($column_selected >= $nbx);
            display_all();
        }
        if ($args eq "check_pattern")
        {
            if (!($matrix[$current_line] =~ " "))
            {
                check_pattern();
            }
        }
        if ($args eq "toggle_solution")
        {
            $display_solution ^= 1;
            display_all();
        }
    }
    
    return weechat::WEECHAT_RC_OK;
}

weechat::register("mastermind", "FlashCode <flashcode\@flashtux.org>",
                  $version, "GPL3", "Mastermind game for WeeChat, yeah!", "", "");
weechat::hook_command("mastermind", "Run Mastermind", "", "", "", "mastermind", "");
$mm_buffer = weechat::buffer_search("perl", "mastermind");
if ($mm_buffer ne "")
{
    mastermind_init();
}
