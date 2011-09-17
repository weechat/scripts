#
# Copyright (C) 2011 by stfn <stfnmd@googlemail.com>
# Copyright (c) 2011 by Nils Görs <weechatter@arcor.de>
#
# Edit channel topics by perl regular expressions or in input-line
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

use strict;
my $PRGNAME     = "topicsed";
my $VERSION     = "0.1";
my $AUTHOR      = "Nils Görs <weechatter\@arcor.de>";
my $LICENCE     = "GPL3";
my $DESCR       = "Edit channel topics by perl regular expressions or in input-line";

# ------------------------------[ internal ]-----------------------------------
my %Hooks               = ();                                   # space for my hooks
my $old_topic           = "";
my $new_topic           = "";
my $saved_input         = "";
my $weechat_version     = "";
# default values
my %options = ("color_message"  => "green",
               "message"        => "edit Topic: ",

);
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

sub toggle_config_by_set{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.$PRGNAME."), length($name));
    $options{$name} = $value;
# insert a refresh here
    return weechat::WEECHAT_RC_OK;
}


# -----------------------------[ main ]-----------------------------------
sub hook_all{
my $buffer = weechat::current_buffer();

my $saved_input = weechat::buffer_get_string($buffer, "input");                         # save current input

my $buf_title = "";
my $plugin_name = "";
my $name = "";

  my $infolist = weechat::infolist_get("buffer",$buffer,"");
  weechat::infolist_next($infolist);
  $buf_title = weechat::infolist_string($infolist,"title");
  $plugin_name = weechat::infolist_string($infolist,"plugin_name");
  ( $name, undef ) = split(/\./,weechat::infolist_string($infolist,"name") );
  weechat::infolist_free($infolist);
  $old_topic = $buf_title;                                                              # save old Topic

if ( $plugin_name eq "irc" and $name ne "server" ){
  $Hooks{command} = weechat::hook_command_run("/input *","command_run_input_cb","");
  $Hooks{buffer} =  weechat::hook_command_run("/buffer *","command_run_buffer_cb","");
  $Hooks{window} =  weechat::hook_command_run("/window *","command_run_window_cb","");
  $Hooks{modifier} =   weechat::hook_modifier("input_text_display_with_cursor", "input_modifier", "");
  weechat::buffer_set($buffer, "input", "");                                              # clear input
  weechat::command($buffer,"/input insert $buf_title");
}

}

sub unhook_all{
  if ( defined $Hooks{command} ){
    weechat::unhook($Hooks{command}); 
    delete $Hooks{command};
  }
  if (defined $Hooks{modifier}){
    weechat::unhook($Hooks{modifier});
    delete $Hooks{modifier};
  }
  if ( defined $Hooks{buffer} ){
    weechat::unhook($Hooks{buffer}); 
    delete $Hooks{buffer};
  }
  if ( defined $Hooks{window} ){
    weechat::unhook($Hooks{window}); 
    delete $Hooks{window};
  }
}

sub command_run_input_cb{
my ($data, $buffer, $command) = @_;

    if ( $command eq "/input search_text" or index($command, "/input jump",0) != -1 ){
        # search text or jump to another buffer is forbidden now
        return weechat::WEECHAT_RC_OK_EAT;
    }elsif( $command eq "/input return" ){
        shut_down();
        weechat::buffer_set($buffer, "input", $saved_input);
        weechat::command($buffer, "/topic " . $new_topic) if ( $old_topic ne $new_topic );      # old and new Topic are not equal!
        $new_topic = "";
        return weechat::WEECHAT_RC_OK_EAT;
    }
return weechat::WEECHAT_RC_OK;
}

sub command_run_buffer_cb{
        return weechat::WEECHAT_RC_OK_EAT;
}

sub command_run_window_cb{
        # window commands are forbidden now
        return weechat::WEECHAT_RC_OK_EAT;
}

sub input_modifier{
my ($data, $modifier, $modifier_data, $string) = @_;
    return "" if ( $modifier_data ne weechat::current_buffer() );
    $new_topic = weechat::string_remove_color($string, "");

return weechat::color($options{color_message}). $options{message} . weechat::color("reset") . $string;
}

sub shut_down{
    unhook_all();
    return weechat::WEECHAT_RC_OK;
}

sub my_command_cb{
my ($getargs) = ($_[2]);

my @args=split(/ /, $getargs);

$args[0] = lc ($args[0]);


if ( not defined $args[0] or $args[0] eq "-e"  or $args[0] eq "-edit" or $args[0] eq ""){
  if ( not defined $Hooks{modifier} ){
    hook_all();
  }else{
    unhook_all();
  }
}else{
    my $buffer = weechat::current_buffer();
    topicsed($buffer, $getargs);
}


return weechat::WEECHAT_RC_OK;
}

# topicsed Copyright (C) 2011 by stfn <stfnmd@googlemail.com>
sub topicsed{
        my ($buffer, $args) = @_;
        my $topic = weechat::buffer_get_string($buffer, "title");
        my $x = $topic;
        my $preview = 0;
        my $regex = $args;

        if ($regex =~ /^-p(review|) ?/) {
                $preview = 1;
                $regex =~ s/^-p\w* ?//;
        }

        {
                local $SIG{__WARN__} = sub {};
                local $SIG{__DIE__} = sub {};
                eval "\$x =~ $regex";
                if ($@) {
                        weechat::print($buffer, weechat::prefix("error") . "$PRGNAME: An error occurred with your regex.");
                        return weechat::WEECHAT_RC_OK;
                }
        }

        if ($x eq $topic) {
                weechat::print($buffer, weechat::prefix("error") . "$PRGNAME: The topic wouldn't be changed.");
                return weechat::WEECHAT_RC_OK;
        } elsif ($x eq "") {
                weechat::print($buffer, weechat::prefix("error") . "$PRGNAME: Edited topic is empty; try '/topic -delete' instead.");
                return weechat::WEECHAT_RC_OK;
        }

        if ($preview) {
                weechat::print($buffer, "$PRGNAME: Edited topic preview: $x");
        } else {
                weechat::command($buffer, "/topic $x");
        }
}

# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($PRGNAME, $AUTHOR, $VERSION,
                  $LICENCE, $DESCR, "", "");

weechat::hook_command($PRGNAME, $DESCR,
                "[-e[dit]]||[-p[review]] <regex>",
                "   -edit        : starts the input-line editor\n".
                "-preview <regex>: show a preview of new Topic\n".
                "\n".
                "To quit input-line editor just press <return> without any changes.\n".
                "\n".
                "Example:\n".
                " show a preview of changed topic\n".
                "   /topicsed -p s/apple/banana/\n".
                " change word \"apple\" to word \"banana\"\n".
                "  /topicsed s/apple/banana/\n".
                " bind command to a key, to start the input-line editor\n".
                "  /key bind meta-E /$PRGNAME\n".
                "",
                "-preview %-||".
                "-edit %-||",
                "my_command_cb", "");
weechat::hook_config("plugins.var.perl.$PRGNAME.*", "toggle_config_by_set", "");

$weechat_version = weechat::info_get("version_number", "");

init_config();
