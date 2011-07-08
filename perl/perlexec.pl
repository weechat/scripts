# perlexec.pl by ArZa <arza@arza.us>: Execute perl code

# This program is free software: you can modify/redistribute it under the terms of
# GNU General Public License by Free Software Foundation, either version 3 or later
# which you can get from <http://www.gnu.org/licenses/>.
# This program is distributed in the hope that it will be useful, but without any warranty.

weechat::register("perlexec", "ArZa <arza\@arza.us>", "0.1", "GPL3", "Execute perl code", "", "");
weechat::hook_command("perlexec", "Execute perl code", "[code]",
                      "Executes perl code given as an argument or creates a buffer for execution if not given an argument.\n\n".
                      "Code is anything like in a weechat perl script, executed in one block.\n\n".
                      "\$buffer is predefined as a pointer for the buffer where this command is executed.\n\n".
                      "For example, close current buffer if it's a query:\n".
                      "  /perlexec weechat::buffer_close(\$buffer) if weechat::buffer_get_string(\$buffer, \"localvar_type\") eq \"private\";",
                      "", "perlexec", "");

sub perlexec { # the command
  if($_[2]){ # if got an argument
    my $buffer=$_[1];
    eval($_[2]); # execute
  }else{
    my $buffer=weechat::buffer_search("perl", "perlexec"); # find the buffer
    if(!$buffer){ # if not found
      $buffer=weechat::buffer_new("perlexec", "buffer_input", "", "", ""); # create it
      weechat::buffer_set($buffer, "title", "Perl execution buffer"); # set title
    }
    if(weechat::current_buffer() eq $buffer){ weechat::buffer_close($buffer); } # if we already are in the buffer, close it
    else{ weechat::buffer_set($buffer, "display", 1); } # otherwise, switch to it
  }
  return weechat::WEECHAT_RC_OK;
}

sub buffer_input { # input in the buffer
  my $buffer=$_[1];
  weechat::print($buffer, "> ".$_[2]); # print
  eval($_[2]); # execute
  return weechat::WEECHAT_RC_OK;
}
