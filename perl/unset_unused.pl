#
# Copyright (c) 2011-2013 by Nils Görs <weechatter@arcor.de>
#
# unset script option(s) from not installed scripts
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
#
# 14-10-04: 0.3: fixed: problem with unset options (reported by GermainZ)
#
# 13-07-27: 0.2 : added: support for guile_script
#
# 11-08-28: 0.1
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts

use strict;

my $PRGNAME     = "unset_unused";
my $VERSION     = "0.3";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENCE     = "GPL3";
my $DESCR       = "unset script option(s) from not installed scripts (YOU ARE USING THIS SCRIPT AT YOUR OWN RISK!)";
my $weechat_version = "";
my @option_list;
my %script_plugins = (
                    "python"    => "python_script",
                    "perl"      => "perl_script",
                    "ruby"      => "ruby_script",
                    "tcl"       => "tcl_script",
                    "lua"       => "lua_script",
                    "guile"     => "guile_script",
);

my $option_struct;
my %option_struct;
my $str;

# get installed scripts
sub get_scripts
{
    foreach my $script (values %script_plugins)
    {
        my $infolist = weechat::infolist_get($script,"","");
        while (weechat::infolist_next($infolist))
        {
            my $script_name = weechat::infolist_string($infolist, "name");
            $str .= $script_name . "|";
        }
        weechat::infolist_free($infolist);
    }
}

sub get_options
{
    # $flag: 0 = list options; 1 = unset options
    my ( $flag, $count ) = ( $_[0], $_[1] );
    my $key;
    my $number = 0;
    chop($str);

    foreach my $plugin (keys %script_plugins)
    {
        my $infolist = weechat::infolist_get("option","","plugins.var.$plugin.*");
        while (weechat::infolist_next($infolist))
        {
          my $option_name = weechat::infolist_string($infolist, "option_name");
          my $full_name = weechat::infolist_string($infolist, "full_name");
          (undef,$option_name,undef) = split(/\./, $option_name);
            $option_struct->{"full_name"} = $full_name;
            while ( my ($key,$value) = each %$option_struct )
            {
                if ( index($value, "check_license") == -1)
                {
                    if( not $value =~ m/($str)/i)
                    {
                        $number ++;
                        weechat::print("",$value) if ( $flag == 0 );    # list options
                        if ( $flag == 1 )                               # remove options
                        {
                            weechat::print("",$number . "/" . $count . " deleted... " .$value);
                            weechat::command("","/mute unset $value");
                            if ($weechat_version >= 0x00030600)
                            {
                                my $name = substr($value, length("plugins.var."), length($value));
                                weechat::command("","/mute unset plugins.desc.$name");
                            }
                        }
                    }
                }
            }
        }
      weechat::infolist_free($infolist);
    }
    return $number;
}

# delete double entries
sub del_double{
  my %all = ();
  @all{@_} = 1;
  return (keys %all);
}

sub my_command_cb{
  my ($getargs) = ($_[2]);
  return weechat::WEECHAT_RC_OK if ($getargs eq "");

  get_scripts();

  if ( $getargs eq "list")
  {
      weechat::print("","unused script options:");
      my $count = get_options(0,0);
      weechat::print("","Number of unused options: $count") if ( $count > 0 );
  }
  elsif ($getargs eq "unset")
  {
      my $count = get_options(0,0);
      get_options(1,$count);
  }
return weechat::WEECHAT_RC_OK
}
# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($PRGNAME, $AUTHOR, $VERSION,
                  $LICENCE, $DESCR, "", "");

$weechat_version = weechat::info_get("version_number", "");

weechat::hook_command($PRGNAME, $DESCR,
                "list || unset\n",
                "   list         : list all unused script options\n".
                "  unset         : reset config options (without warning!)\n\n".
                "If \"plugins.desc.\" exists, it will be removed, too.\n".
                "save your settings with \"/save plugins\" or restore settings with \"/reload plugins\"".
                "\n",
                "list %-||".
                "unset %-",
                "my_command_cb", "");
