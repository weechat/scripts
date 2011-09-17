#
# Copyright (c) 2011 by Nils Görs <weechatter@arcor.de>
#
# will load/reload/unload script (language independent)
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
# History:
# 2011-09-08: nils_2 <weechatter@arcor.de>:
# version 0.3: force_reload option added (idea by FiXato)
#            : script extension in function "list" added (idea by FlashCode)
# 2011-09-06: Banton@freenode.#weechat:
# version 0.2: added: completion for "/script load"
#  2011-08-21: nils_2 <weechatter@arcor.de>:
# version 0.1: proof-of-concept
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

use strict;
use File::Basename;
my $PRGNAME     = "script";
my $VERSION     = "0.3";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENCE     = "GPL3";
my $DESCR       = "to load/reload/unload script (language independent)";

# internal values
my $weechat_version = "";
my $home_dir        = "";
my $fifo_filename   = "";
my %script_suffix = (
                    "python_script"    => ".py",
                    "perl_script"      => ".pl",
                    "ruby_script"      => ".rb",
                    "tcl_script"       => ".tcl",
                    "lua_script"       => ".lua",
);
my %script_counter= (
                    "python_script"    => 0,
                    "perl_script"      => 0,
                    "ruby_script"      => 0,
                    "tcl_script"       => 0,
                    "lua_script"       => 0,
);

# default values
my %options = ("my_option_1"       => "on",
               "my_option_2"       => "on",

    );


# -----------------------------[ programm ]-----------------------------------
sub my_command_cb{
my ($getargs) = ($_[2]);
my $execute_command = "";
my $hit = 0;
return weechat::WEECHAT_RC_OK if ($getargs eq "");

my @args=split(/ /, $getargs);

if ($args[0] eq "list"){
my $str = "";
my $color1 = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_buffer")));
my $color_reset = weechat::color("reset");
    foreach my $script_suffix (keys %script_suffix){
        $script_counter{$script_suffix} = 0;
      my $infolist = weechat::infolist_get($script_suffix,"","");
     while (weechat::infolist_next($infolist)){
          my $name = weechat::infolist_string($infolist, "name");
          my $version = weechat::infolist_string($infolist, "version");
          my $description = weechat::infolist_string($infolist, "description");
          my $output = sprintf("%s %s%s %s %s - %s",$color1,$name,$script_suffix{$script_suffix},$color_reset,$version,$description);
          $script_counter{$script_suffix} ++;
          weechat::print("",$output);
      }
      weechat::infolist_free($infolist);
    }
    my $total = 0;
    while (my ($script,$count) = each (%script_counter)){
      $total = $total + $count;
      $str .= $color1 . $script . ": " . $color_reset . $count . ", ";
    }
      weechat::print("","\n" . $str . $color1 . "total: " . $color_reset . $total);

return weechat::WEECHAT_RC_OK;
}


  if ( $args[0] eq "load" or $args[0] eq "reload" or $args[0] eq "unload" ){
      my $args_m = "";
      my $args_a = "";
      $args_m = "-mute"  if ( grep /^-mute$/i, @args );
      $args_a = "-all"  if ( grep /^-all$/i, @args );
      $execute_command = load_reload_script($args[0],$args[1],$args_m,$args_a); # command,scriptname,mute,all
  }elsif( $args[0] eq "force_reload" ){
    ($execute_command,$hit) = reunload_script_cb($args[0],$args[1],"","");      # command,scriptname,mute,all
    $execute_command =~ s/$args[0]/reload/ if ( $execute_command ne "" );        # reload
    ($execute_command,$hit) = load_script_cb($args[0],$args[1],"","") if ( $execute_command eq "" );
    $execute_command =~ s/$args[0]/load/ if ( $execute_command ne "" );          # reload
  }

weechat::command("","/wait 1ms $execute_command") if ( $execute_command ne "");

return weechat::WEECHAT_RC_OK;
}

sub load_reload_script{
my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
my $hit = 0;
my $execute_command = "";
  return "" if ( not defined $script or $script eq "" );

  $script =~ s/\.[^.]+$//;                                      # delete suffix if given

  if ( $command eq "reload" or $command eq "unload"){
    ($execute_command,$hit) = reunload_script_cb($command,$script,$mute,$all);
  }elsif ( $command eq "load"){
    ($execute_command,$hit) = load_script_cb($command,$script,$mute,$all);
  }
      
weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script with name \"$script\" not found") if ( $hit == 0);
$execute_command = "" if ( $hit == 2);
return $execute_command;
}

sub load_script_cb{
my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
my $hit = 0;
my $execute_command = "";
    my @files;
    while (my ($plugin,$suffix) = each (%script_suffix)){
      my ($plugin,undef) = split(/_/,$plugin);
      @files = glob($home_dir . "/" . $plugin . "/*" .$suffix);
      foreach my $file (@files) {
          if ( index($file,$script . $suffix) ne "-1" ){
            $hit = 1;
            $execute_command = "/$plugin $command $script"."$suffix" if ($mute eq "");
            $execute_command = "/mute $plugin $command $script"."$suffix" if ($mute eq "-mute");
          }
      }
    }
return ($execute_command,$hit);  
}

sub reunload_script_cb{
my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
my $hit = 0;
my $execute_command = "";
    foreach my $script_suffix (keys %script_suffix){
      my $infolist = weechat::infolist_get($script_suffix,"","");
            while (weechat::infolist_next($infolist)){
                my $name = weechat::infolist_string($infolist, "name");
                if ( $all eq "-all"){
                  my ($plugin,undef) = split(/_/,$script_suffix);
                  $execute_command = "/$plugin $command $name" if ($mute eq "");
                  $execute_command = "/mute $plugin $command $name" if ($mute eq "-mute");
                  weechat::command("","/wait 1ms $execute_command") if ( $execute_command ne "");
                  $hit = 2;                                                                             # no more please :-)
                }elsif( lc($name) eq lc($script) ){
                  my ($plugin,undef) = split(/_/,$script_suffix);
                  $execute_command = "/$plugin $command $name" if ($mute eq "");
                  $execute_command = "/mute $plugin $command $name" if ($mute eq "-mute");
                  $hit = 1;
                  last;
                }
            }
      weechat::infolist_free($infolist);
    }
return ($execute_command,$hit);  
}


sub script_completion_cb
{
my ($data,$completion_item,$buffer,$completion) = ($_[0],$_[1],$_[2],$_[3]);
my @files;
    while (my ($plugin,$suffix) = each (%script_suffix)){
      my ($plugin,undef) = split(/_/,$plugin);
      @files = glob($home_dir . "/" . $plugin . "/*" .$suffix);
      foreach my $file (@files) {
          my $basename = basename($file, $suffix);
          weechat::hook_completion_list_add($completion, $basename, 0, weechat::WEECHAT_LIST_POS_SORT);
      }
    }
    return weechat::WEECHAT_RC_OK

}
# -----------------------------[ config ]-----------------------------------
sub init_config{
    foreach my $option (keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option});
        }
        else{
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.iset."), length($name));
    $options{$name} = $value;
# insert a refresh here
    return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($PRGNAME, $AUTHOR, $VERSION,
                  $LICENCE, $DESCR, "", "");

$weechat_version = weechat::info_get("version_number", "");
$home_dir = weechat::info_get ("weechat_dir", "");
#$fifo_filename = weechat::info_get("fifo_filename","");


weechat::hook_command($PRGNAME, $DESCR,
                "load <script> || reload <script> || unload <script> || force_reload <script> || list || -all || -mute\n",
                "         load <script> : load <script> (no suffix needed)\n".
                "       reload <script> : reload <script>\n".
                " force_reload <script> : first try to reload a script and load a script if not loaded (mainly for programmers)\n".
                "       unload <script> : unload <script>\n".
                "         -all          : unload/reload *all* scripts\n".
                "        -mute          : execute command silently\n".
                "         list          : list all installed scripts (by plugin)\n".
                "\n".
                "Example:\n".
                " reload script buddylist:\n".
                "   /$PRGNAME reload buddylist\n".
                " load script buddylist:\n".
                "   /$PRGNAME load buddylist\n".
                " force to reload/load script buddylist:\n".
                "   /$PRGNAME force_reload buddylist\n".
                "",
                "list %-||".
                "load %(all_scripts) -mute %-||".
                "reload %(python_script)|%(perl_script)|%(ruby_script)|%(tcl_script)|%(lua_script)|-all| -mute %-||".
                "unload %(python_script)|%(perl_script)|%(ruby_script)|%(tcl_script)|%(lua_script)|-all| -mute %-||".
                "force_reload %(python_script)|%(perl_script)|%(ruby_script)|%(tcl_script)|%(lua_script)|%(all_scripts) %-",
                "my_command_cb", "");
weechat::hook_completion("all_scripts", "all scripts in script directory", "script_completion_cb", "");
#init_config();
