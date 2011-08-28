#
# Copyright (c) 2011 by Nils Görs <weechatter@arcor.de>
#
# irc-buffers will be sorted alphabetically or in reverse order
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
# 2011-04-14, nils_2:
#     version 0.1: initial release

use strict;

my $PRGNAME     = "sort_buffers";
my $VERSION     = "0.1";
my $DESCR       = "irc-buffers will be sorted alphabetically or in reverse order";

my %buffer_struct      = ();                                                           # to store servername and buffername
my $default_start_after_position = 2;
my $i = 0;
my $args_all = 0;
my $args_reverse = 0;


sub get_buffer_list{
my $buffer_pnt = weechat::infolist_get("buffer","","");

  my $buffer_name = "";
  my $buffer_short_name = "";
  my $buffer_plugin_name = "";
  my $server_name = "";
  my $buffer_number = "";

  while ( weechat::infolist_next($buffer_pnt) ){
    $buffer_plugin_name = weechat::infolist_string($buffer_pnt,"plugin_name");          # get plugin_name of buffer
    $buffer_name = weechat::infolist_string($buffer_pnt,"name");                        # get name of buffer
    $buffer_number = weechat::infolist_integer($buffer_pnt,"number");                   # get number of buffer
    $buffer_short_name = weechat::infolist_string($buffer_pnt,"short_name");            # get short_name of buffer

    if ( $buffer_plugin_name eq "irc" ){
      $buffer_name =~ /(.+?)\.(.*)/;                                                    # strip at first dot ( servername dot #buffername )
      $server_name = $1;
      if ( $server_name eq "server") {
        next;
      }
      if ( $args_all == 1){
        $buffer_struct{"all_in_one"}{$buffer_name}{buffer_short_name}=$buffer_short_name;
      }else{
        $buffer_struct{$server_name}{$buffer_short_name}{buffer_number}=$buffer_number;
      }
    }
  }

weechat::infolist_free($buffer_pnt);
}

# sort z-a
sub reverse_sort{
    if ( $args_all == 1 ){
      foreach my $s ( reverse sort keys %buffer_struct ) {
        foreach my $n ( sort { $buffer_struct{$s}{$b}->{buffer_short_name} cmp $buffer_struct{$s}{$a}->{buffer_short_name}} keys %{$buffer_struct{$s}} ) {
          buffer_movement($n);
        }
      }
    }else{
      foreach my $s ( reverse sort keys %buffer_struct ) {
        foreach my $n ( reverse sort keys %{$buffer_struct{$s}} ) {
          buffer_movement($n);
        }
      }
    }
}

# sort a-z
sub normal_sort{
    if ( $args_all == 1 ){
      foreach my $s ( sort keys %buffer_struct ) {
        foreach my $n ( sort { $buffer_struct{$s}{$a}->{buffer_short_name} cmp $buffer_struct{$s}{$b}->{buffer_short_name}} keys %{$buffer_struct{$s}} ) {
          buffer_movement($n);
        }
      }
    }else{
      foreach my $s ( sort keys %buffer_struct ) {
        foreach my $n ( sort keys %{$buffer_struct{$s}} ) {
          buffer_movement($n);
        }
      }
    }
}
sub buffer_movement{
    my $n = $_[0];
    weechat::command("","/buffer " . $n);
    weechat::command("","/buffer move " . $i);
    $i++;
}
sub sort_buffers_cmd{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);

my $from_buffer_called = weechat::buffer_get_string($buffer,"name");    # save buffer command was executed from

# set variables to default value
    %buffer_struct      = ();
    $args_reverse = 0;
    $args_all = 0;
    $i = $default_start_after_position;

    if ( $args eq "" ){                                                 # no args! use standard settings
      get_buffer_list();
      normal_sort();
    }else{                                                              # arguments given
      my @args_array=split(/ /,$args);
      $i = $args_array[0] if ( $args_array[0]  =~ /^\d*$/ );

      if (grep(m/reverse/, @args_array)){
        $args_reverse = 1;
      }
      if (grep(m/all/, @args_array)){
        $args_all = 1;
      }
        get_buffer_list();
        if ( $args_reverse == 0 ){
          normal_sort();
        }else{
          reverse_sort();
        }
    }
    weechat::command("","/buffer " . $from_buffer_called);              # go back to buffer command was executed from
    return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($PRGNAME, "Nils Görs <weechatter\@arcor.de>", $VERSION,
                  "GPL3", $DESCR, "", "");
weechat::hook_command($PRGNAME, $DESCR, "<position> || reverse || all",
                      "<position>: start at position n (default: 2)\n".
                      "all       : sort irc-buffers server-wide\n".
                      "reverse   : sort irc-buffers in reverse order\n".
                      "\n".
                      "Examples:\n".
                      "  Sort irc-buffers alphabetically, server by server\n".
                      "    /$PRGNAME\n".
                      "  Sort irc-buffers alphabetically, server-wide\n".
                      "    /$PRGNAME all\n".
                      "  Sort all irc-buffers in reverse order. Buffers will be pointed beginning from position 1\n".
                      "    /$PRGNAME 1 all reverse\n",
                      "all|reverse|%*", "sort_buffers_cmd", "");
