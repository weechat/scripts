# listsort.pl by ArZa <arza@arza.us>: Sort the output of /list command by user count

# This program is free software: you can modify/redistribute it under the terms of
# GNU General Public License by Free Software Foundation, either version 3 or later
# which you can get from <http://www.gnu.org/licenses/>. 
# This program is distributed in the hope that it will be useful, but without any warranty.

# Todo: support for /list -re

weechat::register("listsort", "ArZa <arza\@arza.us>", "0.1", "GPL3", "Sort the output of /list command by user count", "", "");
weechat::config_set_plugin("max_size", 100) unless weechat::config_is_set_plugin("max_size");


if(weechat::info_get("version_number", "") >= 0x00030400){ # version >= 0.3.4


weechat::hook_command_run("/list", "list_run", "");
weechat::hook_modifier("irc_color_decode", "list_handle", "");
weechat::hook_hsignal("irc_redirection_siglist_list", "list_get", "");

weechat::config_set_desc_plugin("max_size", "maximum size of /list output in kilobytes to be handled") if weechat::info_get("version_number", "") >= 0x00030500;

our $server;

sub list_run { # when running /list
  my ($data, $buffer, $command) = @_;
  $server=weechat::buffer_get_string($buffer, "localvar_server"); # current server
  weechat::hook_hsignal_send("irc_redirect_command", { "server" => "$server", "pattern" => "list", "signal" => "siglist", "cmd_start" => "321:1", "cmd_stop" => "323:1,416:1,263:1" }); # redirection
  weechat::hook_signal_send("irc_input_send", weechat::WEECHAT_HOOK_SIGNAL_STRING, "$server;;2;;$command"); # send the command
  return weechat::WEECHAT_RC_OK_EAT; # eat the regular output
}

sub list_get { # get the output of /list
  my %hashtable=%{$_[2]};
  if(length($hashtable{"output"})>weechat::config_get_plugin("max_size")*1024){ # too long list
    weechat::print("", "Too long list. Increase plugins.var.perl.listsort.max_size to handle it.");
    return weechat::WEECHAT_RC_ERROR;
  }
  weechat::hook_modifier_exec("irc_color_decode", 1, $hashtable{"output"}); # show irc colors
  return weechat::WEECHAT_RC_OK;
}

sub list_handle { # handle the output of /list
  my @list=split(/\n/, $_[3]); # split to lines
  my $buffer=weechat::buffer_search("irc", "server.$server"); # output buffer
  shift(@list); # cut the start
  pop(@list); # and end
  @list = sort { ($b=~/(?:\S+ ){4}(\S+)/)[0] <=> ($a=~/(?:\S+ ){4}(\S+)/)[0] } @list; # sort the list by users count
  weechat::print($buffer, weechat::prefix("network")."Users Channel Topic");
  foreach my $line (@list) {
    if($line=~/(?:\S+ ){3}(\S+) (\S+) :(.*)/){ # print the list
      weechat::print($buffer, weechat::prefix("network").weechat::color("bold")."$2 ".weechat::color("darkgray")."$1".weechat::color("default")." $3");
    }
  }
  weechat::print($buffer, weechat::prefix("network")."End of /LIST");
}


} else { ### End of script for version >= 0.3.4 ### Below for version <= 0.3.3 ###


weechat::hook_signal("*,irc_in_321", "list_start", "");
weechat::hook_modifier("irc_color_decode", "color", "");
weechat::hook_modifier("irc_in_322", "list_chan", "");
weechat::hook_signal("*,irc_in_323", "list_end", "");

our @list;

sub list_start { @list=(); }

sub color { push(@list, $_[3]); }

sub list_chan {
  weechat::hook_modifier_exec("irc_color_decode", 1, $_[3]);
  return "";
}

sub list_end {
  if(@list>weechat::config_get_plugin("max_size")){
    weechat::print("", "Too long list. Increase plugins.var.perl.listsort.max_size to handle it.");
    return weechat::WEECHAT_RC_ERROR;
  }
  my $server=$_[1];
  $server=~s/,.*//;
  my $buffer=weechat::buffer_search("irc", "server.$server");
  @list = sort { ($b=~/(?:\S+ ){4}(\S+)/)[0] <=> ($a=~/(?:\S+ ){4}(\S+)/)[0] } @list;
  foreach my $line (@list) {
    if($line=~/(?:\S+ ){3}(\S+) (\S+) :(.*)/){ # print the list
      weechat::print($buffer, weechat::prefix("network").weechat::color("bold")."$2 ".weechat::color("darkgray")."$1".weechat::color("default")." $3");
    }
  }
  @list=();
}


}
