#
# Copyright (c) 2011/12 by Nils Görs <weechatter@arcor.de>
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
#  2012-02-11: nils_2 <weechatter@arcor.de>:
# version 1.1: fix: rephrase of text output
#  2012-02-06: nils_2 <weechatter@arcor.de>:
# version 1.0: complete rewrite of script.
#            : add: multi-script capability
#  2012-01-29: nils_2 <weechatter@arcor.de>:
# version 0.7: add; confirmation for auto(un)load option and error messages added
#            : fix: not installed script was loaded using option "unload"
#            : fix: script with full pathname wasn't loaded from a different path than homepath
#  2012-01-17: nils_2 <weechatter@arcor.de>:
# version 0.6: fix: a error message appeared when "autoload" was used with already installed script
#  2011-11-05: nils_2 <weechatter@arcor.de>:
# version 0.5: added: support for guile script
#            : added: option "force_reload" (default: off)
#  2011-09-08: Banton <fbesser@gmail.com> & nils_2:
# version 0.4: added: auto(un)load (by Banton)
#            : added: options autoload_load and autounload_unload
#            : added: plugin description
#            : WeeChat error message occurs twice when a script was loaded
#            : invalid command will be catched.
#  2011-09-08: nils_2 <weechatter@arcor.de>:
# version 0.3: added: command force_reload (idea by FiXato)
#            : script extension in function "list" added (idea by FlashCode)
#  2011-09-06: Banton@freenode.#weechat:
# version 0.2: added: completion for "/script load"
#  2011-08-21: nils_2 <weechatter@arcor.de>:
# version 0.1: proof-of-concept
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

use strict;
use File::Basename;

my $PRGNAME     = "script";
my $VERSION     = "1.1";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENCE     = "GPL3";
my $DESCR       = "to load/reload/unload script (language independent) and also to create/remove symlink";

# internal values
my $weechat_version = "";
my $home_dir        = "";
my %script_suffix = (
                    "python_script"    => ".py",
                    "perl_script"      => ".pl",
                    "ruby_script"      => ".rb",
                    "tcl_script"       => ".tcl",
                    "lua_script"       => ".lua",
                    "guile_script"     => ".scm",
);
my %script_counter= (
                    "python_script"    => 0,
                    "perl_script"      => 0,
                    "ruby_script"      => 0,
                    "tcl_script"       => 0,
                    "lua_script"       => 0,
                    "guile_script"     => 0,
);

# default values
my %options = ("autoload_load"          => ["off","load script after a symlink was created (default: off)"],
               "autounload_unload"      => ["off","unload script after a symlink was removed (default: off)"],
               "force_reload"           => ["off","load the given script, if script is not installed and command \"reload\" is used (default: off)"],
);


# -----------------------------[ main commands ]-----------------------------------
sub list_scripts
{
    my $str = "";
    my $color1 = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_buffer")));
    my $color_reset = weechat::color("reset");
    foreach my $script_suffix (keys %script_suffix){
        $script_counter{$script_suffix} = 0;
        my $infolist = weechat::infolist_get($script_suffix,"","");
        while (weechat::infolist_next($infolist))
        {
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
     while (my ($script,$count) = each (%script_counter))
     {
         $total = $total + $count;
         $str .= $color1 . $script . ": " . $color_reset . $count . ", ";
     }
     weechat::print("","\n" . $str . $color1 . "total: " . $color_reset . $total);
}

sub load_script
{
    my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);

    my $short_script_name = check_if_script_is_installed($script);
    if ( $short_script_name eq "" )                                       # script not installed!
    {
        my $execute_command = script_loader($command,$script,$mute,$all);
        if  ( $execute_command eq "" )
        {
            weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script with name \"$script\" not found.") if ($mute ne "-mute");
            return;
        }
        weechat::command("","/wait 1ms $execute_command");
    }else
    {
        weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script with name \"$short_script_name\" already installed. use: /$PRGNAME reload $short_script_name") if ($mute ne "-mute");
    }
}

sub reload_script
{
    my ($command,$script,$mute,$all,$force) = ($_[0],$_[1],$_[2],$_[3],$_[4]);

    if ( $script eq "-all" or $all eq "-all")
    {
        script_re_unload_cb($command,"",$mute,$all);
        return;
    }

    my $short_script_name = check_if_script_is_installed($script);
    if ( $short_script_name eq "" )                                             # script not installed!
    {
        if ( $options{force_reload}[0] eq "on" or $force eq "-force")           # use force_reload ??
        {
            $command = "load";
            my $execute_command = script_loader($command,$script,$mute,$all);
            if  ( $execute_command ne "" )
            {
#                weechat::print("","command: $command   script: $script   exe: $execute_command");
                weechat::command("","/wait 1ms $execute_command");
            }else
            {
                $short_script_name = $script if ( $short_script_name eq "" );
                weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script with name \"$short_script_name\" not found.");
            }
        }else
        {
            weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script \"$script\" not loaded. You should either use \"/$PRGNAME load $script\" or use the \"-force\" argument.");
        }
    }else                                                                       # reload script!
    {
        my $execute_command = script_re_unload_cb($command,$short_script_name,$mute,$all);
        if  ( $execute_command ne "" )
        {
#            weechat::print("","command_reload: $command   script: $script   exe: $execute_command");
            weechat::command("","/wait 1ms $execute_command");
        }
    }
}

sub unload_script
{
    my ($command,$script,$mute,$all,$force) = ($_[0],$_[1],$_[2],$_[3],$_[4]);

    if ( $script eq "-all" or $all eq "-all")
    {
        script_re_unload_cb($command,"",$mute,$all);
        return;
    }
    my $short_script_name = check_if_script_is_installed($script);
    if ( $short_script_name eq "" )                                             # script not installed!
    {
        weechat::print("",weechat::prefix("error")."$PRGNAME: \"$command\" error. script \"$script\" not installed.") if ($mute ne "-mute");
    }else
    {
        my $execute_command = script_re_unload_cb($command,$short_script_name,$mute,$all);
        if  ( $execute_command ne "" )
        {
#            weechat::print("","command_unload: $command   script: $script   exe: $execute_command");
            weechat::command("","/wait 1ms $execute_command");
        }
    }
}

sub autoload_script
{
    my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
    my @files = get_all_scripts("autoload");
    unless ( grep m/\/$script(.pl|.py|.rb|.tcl|.lua|.scm)$/ig, @files)
    {
        weechat::print("",weechat::prefix("error") . "$PRGNAME: \"$script\" not found.") if ($mute ne "-mute");
        return;
    }
    foreach my $filename (@files)
    {
        if ($filename =~ /\/$script(.pl|.py|.rb|.tcl|.lua|.scm)/)
        {
            if ( $command eq "autoload" )
            {
                my $suffix = ($filename =~ m{([^.]+)$} )[0];                                            # get suffix
                $suffix = ($filename =~ m{.*Logger$})[0] unless($suffix);
                my (undef,$path) = fileparse $filename;                                                 # remove path
                # if symlink don't exists, create one.
                unless (-e $path . "/autoload/" . $script . "." . $suffix)
                {
                    weechat::print("",weechat::prefix("error") . "script: \"$script\" will be auto loaded.") if ($mute ne "-mute");
                    symlink($filename , $path . "/autoload/" . $script . "." . $suffix)
                }
                if ( $options{autoload_load}[0] eq "on" )
                {
                    my $execute_command = "";
                    my $short_script_name = check_if_script_is_installed($script);
                    if ( $short_script_name eq "" )                                                 # script not installed!
                    {
                        $execute_command = script_loader("load",$script,$mute,$all);
                    }
                    if  ( $execute_command ne "" )
                    {
                        weechat::command("","/wait 1ms $execute_command");
                    }
                }
            }
        }
    }
}

sub autounload_script
{
    my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
    my @files = get_all_scripts("autounload");
    unless ( grep m/\/$script(.pl|.py|.rb|.tcl|.lua|.scm)$/ig, @files)
    {
        weechat::print("",weechat::prefix("error") . "$PRGNAME: symlink for \"$script\" not found.") if ($mute ne "-mute");
        return;
    }
    foreach my $filename (@files)
    {
        if ($filename =~ /\/$script(.pl|.py|.rb|.tcl|.lua|.scm)/)
        {
            if ( $command eq "autounload" )
            {
                my $suffix = ($filename =~ m{([^.]+)$} )[0];                                            # get suffix
                $suffix = ($filename =~ m{.*Logger$})[0] unless($suffix);
                my (undef,$path) = fileparse $filename;                                                 # remove path
                # if symlink exists, delete it.
                if (-e $path . $script . "." . $suffix)
                {
                    unlink $path . $script . "." . $suffix;
                    weechat::print("",weechat::prefix("error") . "script \"$script\" will no longer be auto loaded.") if ($mute ne "-mute");
                }
                if ( $options{autounload_unload}[0] eq "on" )
                {
                    my $execute_command = "";
                    my $short_script_name = check_if_script_is_installed($script);
                    if ( $short_script_name ne "" )                                                     # script installed!
                    {
                        unload_script("unload",$script,$mute,$all);                                     # unload script
                    }
                }
            }
        }
    }
}
# -----------------------------[ subroutines ]-----------------------------------
sub get_all_scripts
{
    my $command = $_[0];

    my $path;
    my @files;

    while (my ($plugin,$suffix) = each (%script_suffix))
    {
        ($plugin,undef) = split(/_/,$plugin);
        $path = $home_dir . "/" . $plugin . "/*" .$suffix if ($command eq "autoload");
        $path = $home_dir . "/" . $plugin . "/autoload" . "/*" .$suffix if ($command eq "autounload");
        my @files_glob = glob($path);
        if (@files_glob ne "")
        {
            foreach my $filename (@files_glob)
            {
                push(@files,$filename);
            }
        }
    }
    return @files;
}

sub check_if_script_is_installed
{
    my ( $script ) = ($_[0]);
    my $path = "";

    if (index($script,"/") >= 0)                                                        # /path/to/script given?
    {
        ($script,$path) = fileparse $script;                                            # remove path
    }

    $script =~ s/\.[^.]+$// if (index($script,"/") == -1);                              # delete suffix from scriptname if no "/" in name
    # check if script is already installed.
    foreach my $plugin (keys %script_suffix)
    {
        my $infolist = weechat::infolist_get( $plugin, "name", $script );
        weechat::infolist_next($infolist);
        my $script_found = weechat::infolist_string( $infolist, "name" ) eq $script;
        weechat::infolist_free($infolist);
        if ( $script_found eq "1" )
        {
            return $script;
        }
    }
    return "";
}

sub script_loader{
    my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
    my $execute_command = "";
    my %script_suffix_bak = %script_suffix;
    # full script path given by user
    if (index($script,"/") >= 0)
    {
        while (my ($plugin,$suffix) = each (%script_suffix_bak))
        {
            my ($plugin,undef) = split(/_/,$plugin);
            if ( index($script,$suffix) >= 0 )
            {
                $execute_command = "/$plugin $command $script" if ($mute eq "");
                $execute_command = "/mute $plugin $command $script" if ($mute eq "-mute");
                return ($execute_command);  
            }
        }
    }else
    {
        my @files;
        $script =~ s/\.[^.]+$//;                    # delete suffix
        while (my ($plugin,$suffix) = each (%script_suffix_bak)){
            my ($plugin,undef) = split(/_/,$plugin);
            @files = glob($home_dir . "/" . $plugin . "/*" .$suffix);
            foreach my $file (@files)
            {
                if ( index($file,$script . $suffix) ne "-1" )
                {
                    $execute_command = "/$plugin $command $script"."$suffix" if ($mute eq "");
                    $execute_command = "/mute $plugin $command $script"."$suffix" if ($mute eq "-mute");
                    return ($execute_command);
                }
            }
        }
     }
return $execute_command;
}

sub script_re_unload_cb
{
    my ($command,$script,$mute,$all) = ($_[0],$_[1],$_[2],$_[3]);
    my $execute_command = "";
    foreach my $script_suffix (keys %script_suffix)
    {
        my $infolist = weechat::infolist_get($script_suffix,"","");
            while (weechat::infolist_next($infolist)){
                my $name = weechat::infolist_string($infolist, "name");
                if ( $all eq "-all"){
                  my ($plugin,undef) = split(/_/,$script_suffix);
                  $execute_command = "/$plugin $command $name" if ($mute eq "");
                  $execute_command = "/mute $plugin $command $name" if ($mute eq "-mute");
#                  weechat::print("","/wait 1ms $execute_command");
                  weechat::command("","/wait 1ms $execute_command") if ( $execute_command ne "");
                }elsif( lc($name) eq lc($script) ){
                  my ($plugin,undef) = split(/_/,$script_suffix);
                  $execute_command = "/$plugin $command $name" if ($mute eq "");
                  $execute_command = "/mute $plugin $command $name" if ($mute eq "-mute");
                  last;
                }
            }
      weechat::infolist_free($infolist);
    }
return $execute_command;
}

# -----------------------------[ command callback ]-----------------------------------
sub my_command_cb
{
    my ($getargs) = lc($_[2]);
    my $execute_command = "";
    return weechat::WEECHAT_RC_OK if ($getargs eq "");

    my @args=split(/ /, $getargs);
    my @commands = qw(list autoload autounload load reload unload);
    my $command = (grep /^$args[0]$/ig, @commands);                                     # search for a command in first option

    # error checks...
    if  ( $command == 0 )
    {
        weechat::print("",weechat::prefix("error")."$PRGNAME: Yoda says: \"$args[0]\" is not a valid command. \“Do or do not... there is no try\”...");
        return weechat::WEECHAT_RC_OK;
    }

    if ($args[0] eq "list")
    {
        list_scripts();
        return weechat::WEECHAT_RC_OK;
    }

    if ( not defined $args[1] )
    {
        weechat::print("",weechat::prefix("error")."$PRGNAME: \"$args[0]\" error. Obi-Wan says: You did not specified a script my young padawn...");
        return weechat::WEECHAT_RC_OK;
    }

    # get additional options
    my $args_m = "";
    my $args_a = "";
    my $args_f = "";
    $args_m = "-mute"  if ( grep /^-mute$/i, @args );
    $args_a = "-all"  if ( grep /^-all$/i, @args );
    $args_f = "-force" if ( grep /^-force$/i, @args );

    my @script_array = grep !/(-all|-mute|-force)/, @args;                              # remove additional options from script list
    push @script_array, "-all" if ( $args_a eq "-all" );
    my $i = 0;
    while ($i < $#script_array)
    {
        $i++;
        $args[1] = $script_array[$i];
        $i = $#script_array if ( $args_a eq "-all" );
        # load, unload, reload, autoload, autounload
        if ( $args[0] eq "load" )
        {
            load_script($args[0],$args[1],$args_m,$args_a);
        }elsif ( $args[0] eq "reload" )
        {
            reload_script($args[0],$args[1],$args_m,$args_a,$args_f);
        }elsif ( $args[0] eq "unload" )
        {
            unload_script($args[0],$args[1],$args_m,$args_a,$args_f);
        }elsif ( $args[0] eq "autoload" )
        {
            autoload_script($args[0],$args[1],$args_m,$args_a,$args_f);
        }elsif ( $args[0] eq "autounload" )
        {
            autounload_script($args[0],$args[1],$args_m,$args_a,$args_f);
        }
    }

    return weechat::WEECHAT_RC_OK;
}
# -----------------------------[ completion callback ]-----------------------------------
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
sub init_config
{
    foreach my $option (keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option}[0]);
        }else{
            $options{$option}[0] = weechat::config_get_plugin($option);
        }
        if ( ($weechat_version ne "") && (weechat::info_get("version_number", "") >= 0x00030500) ){
            weechat::config_set_desc_plugin($option, $options{$option}[1]);
        }
    }
}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.$PRGNAME."), length($name));
    $options{$name}[0] = lc($value);
# insert a refresh here
    return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($PRGNAME, $AUTHOR, $VERSION,
                  $LICENCE, $DESCR, "", "");

$weechat_version = weechat::info_get("version_number", "");
$home_dir = weechat::info_get ("weechat_dir", "");

weechat::hook_command($PRGNAME, $DESCR,
                "load <script> || reload <script> -force || unload <script> || autoload <script> || autounload <script> || list || -all || -mute\n",
                "         list          : list all installed scripts (by plugin)\n".
                "         load <script> : load <script> (no suffix needed)\n".
                "       reload <script> : reload <script>\n".
                "                -force : tries to reload a script first and will load the script if not loaded (mainly for programmers)\n".
                "       unload <script> : unload <script>\n".
                "     autoload <script> : creates a symlink to start automatically a script at weechat startup\n".
                "   autounload <script> : remove symlink from autoload\n".
                "                  -all : unload/reload *all* scripts\n".
                "                 -mute : execute command silently\n".
                "\n".
                "$PRGNAME will only create/remove a symlink in \"~/.weechat/<language>/autoload\"\n".
                "to remove/install scripts permanently use \"weeget.py\" script (http://www.weechat.org/files/scripts/weeget.py)\n".
                "\n".
                "You can do an action on multiple scripts at once.\n".
                "\n".
                "Examples:\n".
                " reload script buddylist:\n".
                "   /$PRGNAME reload buddylist\n".
                " load several scripts at once:\n".
                "   /$PRGNAME load buddylist colorize_lines buffers\n".
                " force to reload/load script buddylist:\n".
                "   /$PRGNAME force_reload buddylist\n".
                " create symlink for script weeget\n".
                "   /$PRGNAME autoload weeget\n".
                "",
                "list %-".
                "||load %(all_scripts)|-mute|%*".
                "||reload %(python_script)|%(perl_script)|%(ruby_script)|%(tcl_script)|%(lua_script)|%(guile_script)|-all|-force|-mute|%*".
                "||unload %(python_script)|%(perl_script)|%(ruby_script)|%(tcl_script)|%(lua_script)|%(guile_script)|-all|-mute|%*".
                "||autoload %(all_scripts)|-mute|%*".
                "||autounload %(all_scripts)|-mute|%*",
                "my_command_cb", "");
weechat::hook_completion("all_scripts", "all scripts in script directory", "script_completion_cb", "");
weechat::hook_config("plugins.var.perl.$PRGNAME.*", "toggle_config_by_set", "");

init_config();
