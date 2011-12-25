# snake.pl by ArZa <arza@arza.us>: Snake game

# This program is free software: you can modify/redistribute it under the terms of
# GNU General Public License by Free Software Foundation, either version 3 or later
# which you can get from <http://www.gnu.org/licenses/>.
# This program is distributed in the hope that it will be useful, but without any warranty.

weechat::register("snake", "ArZa <arza\@arza.us>", "0.1", "GPL3", "Snake game", "", "");
weechat::hook_command("snake",
"Snake game\n
Keys:
 Arrow keys to move
 n: new game
 p: pause
 q: quit
\nNo walls", "", "", "", "snake_cmd", "");

my ($buffer,$hook,$dir,$r,$c,$speed,$score,$prevdir,$pause,$level,@tail,@table,@coords);
my ($rows,$cols,$length)=(24,38,9);

my $b=weechat::color("bold");
my $n=weechat::color("reset");
my $v=weechat::color("lightblue,blue");

my $food=weechat::color("green")."<>".$n;
my $empty="  ";

my $head=weechat::color("lightgreen,lightblue")."`´".$n;
my $dead=weechat::color("lightgreen,lightblue")."><".$n;

$tail[1]="${v}══${n}";
$tail[2]="${v}║║${n}";

$tail[3]="${v}╔╔${n}";
$tail[5]="${v}╗╗${n}";
$tail[7]="${v}╚╚${n}";
$tail[9]="${v}╝╝${n}";

sub print_line { my $add = $_[1] || ""; # print a specific line
  weechat::print_y($buffer, $_[0]+1, "│".join("", @{$table[$_[0]]})."│ $add");
}

sub redraw { # redraw the whole screen
  weechat::print_y($buffer, 0, "┌" . "─" x (2*$cols+2) . "┐");
  for(my $i=0; $i<=$#table; $i++){ print_line($i); }
  weechat::print_y($buffer, $rows+2, "└" . "─" x (2*$cols+2) . "┘");
  weechat::print_y($buffer, $rows+3, " Score: $score $level");
}

sub hook { # 0 -> stop,  1 -> rehook (speed changed)
  weechat::unhook($hook) if $hook;
  $hook = $_[0] ? weechat::hook_timer($speed, 0, 0, "move", "") : undef;
  return weechat::WEECHAT_RC_OK;
}

sub tail { # direction -> print the right type of tail for the previous spot (yanetut)
  if($dir==$prevdir){ $table[$coords[-2]][$coords[-1]]=$tail[abs($dir)]; } # going straight
  else{ $table[$coords[-2]][$coords[-1]]=$tail[$prevdir-$dir+6]; } # turned
  print_line($coords[-2]);
}

sub init_snake { # (re)start
  
  @coords=(); # reset
  $speed=140;
  $score=0;
  $r=5;
  $c=$length;
  $pause=0;
  $level="";
  $dir=$prevdir=1;
  
  for my $i (0..$rows){ # empty table
    for my $j (0..$cols){
      $table[$i][$j]=$empty;
    }
  }
  
  for my $i (0..$length){ # add the snake
    $table[5][$i]=$tail[1];
    push(@coords, (5,$i));
  }
  
  $table[5][$length]=$head;
  $table[12][19]=$food; # first food
  redraw();
  hook(1);
  
}

sub snake_cmd { # /snake
  $buffer=weechat::buffer_search("perl", "snake"); # find the buffer
  if(!$buffer){ # if not found
    $buffer=weechat::buffer_new("snake", "", "", "hook", ""); # create it
    weechat::buffer_set($buffer, "title", "Snake | Keys: arrows, ${b}n${n}ew, ${b}p${n}ause, ${b}q${n}uit | No walls"); # set title
    weechat::buffer_set($buffer, "time_for_each_line", "0"); # no timestamps
    weechat::buffer_set($buffer, "display", 1); # switch to it
    weechat::buffer_set($buffer, "type", "free"); # free content
    weechat::buffer_set($buffer, "key_bind_meta2-A", "/snake -2"); # up
    weechat::buffer_set($buffer, "key_bind_meta2-B", "/snake +2"); # down
    weechat::buffer_set($buffer, "key_bind_meta2-D", "/snake -1"); # left
    weechat::buffer_set($buffer, "key_bind_meta2-C", "/snake +1"); # right
    weechat::buffer_set($buffer, "key_bind_n", "/snake new");
    weechat::buffer_set($buffer, "key_bind_p", "/snake pause");
    weechat::buffer_set($buffer, "key_bind_q", "/snake quit");
    init_snake();
  }elsif($_[2] eq "pause"){ # toggle pause
    if($pause){
      $pause=0;
      hook(1);
      move();
      redraw();
    }elsif($hook){
      $pause=1;
      weechat::buffer_clear($buffer);
      hook(0);
      weechat::print_y($buffer, 11, " " x 35 . "S n a k e");
      weechat::print_y($buffer, 12, " " x 34 . "p a u s e d");
      weechat::print_y($buffer, 14, " " x 31 . "Press p to resume");
      return weechat::WEECHAT_RC_OK;
    }
  }elsif($_[2] eq "new"){
    init_snake();
  }elsif($_[2] eq "quit"){
    weechat::buffer_close($buffer);
  }elsif($_[2] && $hook){
    $dir=$_[2];
    hook(1);
    move();
  }
  return weechat::WEECHAT_RC_OK;
} 

sub move {
  
  if($dir+$prevdir==0){ $dir=$prevdir; } # don't go backwards
  
  if($dir==1){ $c++; } # new head position
  elsif($dir==2){ $r++; }
  elsif($dir==-1){ $c--; }
  elsif($dir==-2){ $r--; }
  
  $r%=$rows+1; # edges
  $c%=$cols+1;
  
  if($table[$r][$c] eq $food){ # eat
    
    $score++;
    if($score==50){ $level="Cool!"; $speed*=0.95; }
    elsif($score==100){ $level="Awesome!"; $speed*=0.92; }
    elsif($score==120){ $level="OMG!"; $speed*=0.9; }
    elsif($score==150){ $level="OMG!! INSANE!!!"; $speed*=0.7; }
    weechat::print_y($buffer, $rows+3, " Score: $score $level");
    
    for my $i (0..10000){
      my $randr=rand($rows+1);
      my $randc=rand($cols+1);
      if($table[$randr][$randc] eq $empty){ # new food
        $table[$randr][$randc]=$food;
        print_line($randr);
        $speed*=0.993; # speed up
        if($speed<1){ $speed=1; }
        hook(1);
        last;
      }
      if($i==10000){ hook(0); $table[$r][$c]=$tail[0]; print_line($r); weechat::print_y($buffer, $rows+3, " Score: $score $level YOU WON THE GAME!"); return weechat::WEECHAT_RC_OK; } # not really necessary...
    }
    
  }else{
    
    my ($remr,$remc)=(shift(@coords),shift(@coords));
    $table[$remr][$remc]=$empty; # remove the last coordinates
    print_line($remr);
    
    if($table[$r][$c] ne $empty){ # die
      $table[$r][$c]=$dead;
      tail();
      print_line($r, "You died :( Press n for new game");
      hook(0);
      return weechat::WEECHAT_RC_OK;
    }
    
  }
  
  $table[$r][$c]=$head; # snake to new coordinates
  print_line($r);
  tail();
  
  push(@coords, ($r,$c)); # push the new coordinates to @coords array
  $prevdir=$dir;
  
}
