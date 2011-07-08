# echo.pl by ArZa <arza@arza.us>: Print a line and additionally set activity level

# This program is free software: you can modify/redistribute it under the terms of
# GNU General Public License by Free Software Foundation, either version 3 or later
# which you can get from <http://www.gnu.org/licenses/>.
# This program is distributed in the hope that it will be useful, but without any warranty.

weechat::register("echo", "ArZa <arza\@arza.us>", "0.1", "GPL3", "Print a line and additionally set activity level", "", "");
weechat::hook_command(
  "echo",
  "Print a line and additionally set activity level. Local variables are expanded when starting with \$ and can be escaped with \\.",
  "[ -p/-plugin <plugin> ] [ -b/-buffer <buffer name/number> | -c/-core ] [ -l/-level <level>] [text]", 
"-plugin: plugin where printed, default: current plugin
-buffer: buffer where printed, default: current buffer, e.g. #weechat or freenode.#weechat)
  -core: print to the core buffer
 -level: number of the activity level, default: low:
         0=low, 1=message, 2=private, 3=highlight
Examples:
  /echo This is a test message
  /echo -b freenode.#weechat -level 3 Highlight!
  /echo -core This goes to the core buffer
  /echo -buffer #weechat -l 1 My variable \\\$name is \$name on \$channel",
  "-buffer %(buffer_names) || -core || -level 1|2|3 || -plugin %(plugins_names)", "echo", ""

);

sub echo {
  
  my @args=split(/ /, $_[2]);
  my $i=0;
  my ($plugin, $buffer, $level) = ("", "", "");
  
  while($i<=$#args){ # go through command options
    if($args[$i] eq "-b" || $args[$i] eq "-buffer"){
      $i++;
      $buffer=$args[$i] if $args[$i];
    }elsif($args[$i] eq "-p" || $args[$i] eq "-plugin"){
      $i++;
      $plugin=$args[$i] if $args[$i];
    }elsif($args[$i] eq "-c" || $args[$i] eq "-core"){
      $buffer=weechat::buffer_search_main();
    }elsif($args[$i] eq "-l" || $args[$i] eq "-level"){
      $i++;
      $level=$args[$i] if $args[$i];
    }else{
      last;
    }
    $i++;
  }
  
  if($plugin ne ""){ # use specific plugin if set
    $buffer=weechat::buffer_search($plugin, $buffer);
  }elsif($buffer ne ""){
    if($buffer=~/^\d+$/){ # if got a number
      my $infolist = weechat::infolist_get("buffer", "", "");
      while(weechat::infolist_next($infolist)){ # find the buffer for the number
        if(weechat::infolist_integer($infolist, "number") eq $buffer){
          $buffer=weechat::buffer_search( weechat::infolist_string($infolist, "plugin"), weechat::infolist_string($infolist, "name") );
          last;
        }
      }
      weechat::infolist_free($infolist);
	}elsif(  weechat::buffer_search ( weechat::buffer_get_string( weechat::current_buffer(), "plugin" ), $buffer )  ){ # if buffer found in current plugin
      $buffer=weechat::buffer_search ( weechat::buffer_get_string( weechat::current_buffer(), "plugin" ), $buffer );
    }else{ # search even more to find the correct buffer
      my $infolist = weechat::infolist_get("buffer", "", "");
      while(weechat::infolist_next($infolist)){ # find the buffer for a short_name
        if(lc(weechat::infolist_string($infolist, "short_name")) eq lc($buffer)){
          $buffer=weechat::buffer_search( weechat::infolist_string($infolist, "plugin"), weechat::infolist_string($infolist, "name") );
          last;
        }
      }
      weechat::infolist_free($infolist);
    }
  }
  $buffer=weechat::current_buffer() if $buffer eq "" || $buffer eq $args[$i-1]; # otherwise use the current buffer
  
  my $j=$i;
  $args[$j]=~s/^\\\-/-/ if $args[$j]; # "\-" -> "-" in the beginning
  while($j<=$#args){ # go through text
    if($args[$j]=~/^\$/){ # replace variables
      $args[$j]=weechat::buffer_string_replace_local_var($buffer, $args[$j]);
    }elsif($args[$j]=~/^\\[\$\\]/){ # escape variables
      $args[$j]=~s/^\\//;
    }
    $j++;
  }
  
  weechat::print($buffer, join(' ', @args[$i..$#args])); # print the text
  weechat::buffer_set($buffer, "hotlist", $level); # set hotlist level
  
}
