# Copyright (c) 2009-2018 by Nils Görs <weechatter@arcor.de>
#
# waiting for hotlist to change and then execute a user specified command
# or writes the hotlist to screen title.
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
# I am using this script to display the hotlist with STDIN plasmoid on
# KDE desktop.
# http://www.kde-look.org/content/show.php/STDIN+Plasmoid?content=92309
#
# Script inspirated and tested by LaoLang_cool
#
# 0.9   : add eval_expression() for format options
# 0.8	: escape special characters in hotlist (arza)
# 0.7	: using %h for weechat-dir instead of hardcoded path in script (flashcode)
# 0.6	: new option "use_title" to print hotlist in screen title.
# 0.5	: lot of internal changes
# 0.4	: highlight_char can be set as often as you want
#	: merged buffer will be displayed once
#	: more than one metachar-highlight produced a perl error
# 0.3	: usersettings won't be loaded, sorry! :-(
#	: added a more complex sort routine (from important to unimportant and also numeric)
#	: added options: "delimiter", "priority_remove" and "hotlist_remove_format"

use strict;
my $SCRIPT_NAME         = "hotlist2extern";
my $SCRIPT_VERSION      = "0.9";
my $SCRIPT_DESC         = "Give hotlist to an external file/program/screen title";
my $SCRIPT_AUTHOR       = "Nils Görs <weechatter\@arcor.de>";

# default values
my %options = (
                "hotlist_format"                    =>  "%H%N:%S",
                "hotlist_remove_format"             =>  ":%S",
                "external_command_hotlist"          =>  "echo WeeChat Act: %X >%h/hotlist_output.txt",
                "external_command_hotlist_empty"    =>  "echo \'WeeChat: no activity \' >%h/hotlist_output.txt",
                "highlight_char"                    =>  "*",
                "lowest_priority"                   =>  "0",
                "priority_remove"                   =>  "0",
                "delimiter"                         =>  ",",
                "use_title"                         =>  "on",
);

my $weechat_dir		= "";
my $res 		= "";
my $res2 		= "";
my $priority		= 0;
my @table		= ();
my $table		= "";

sub hotlist_changed{
my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);			# save callback from hook_signal
@table		= ();
$table		= "";

  my $current_buffer = weechat::current_buffer;				# get current buffer
  my $hotlist = weechat::infolist_get("hotlist","","");			# Pointer to Infolist

   while (weechat::infolist_next($hotlist))
    {
        $priority = weechat::infolist_integer($hotlist, "priority");
	  $res = $options{hotlist_format};							# save hotlist format
	  $res2 = $options{external_command_hotlist};						# save external_hotlist format

	    my $plugin_name = weechat::infolist_string($hotlist,"plugin_name");
	    my $buffer_name = weechat::infolist_string($hotlist,"buffer_name");
	    my $buffer_number = weechat::infolist_integer($hotlist,"buffer_number");	# get number of buffer
	    my $buffer_pointer = weechat::infolist_pointer($hotlist, "buffer_pointer");	# Pointer to buffer
	    my $short_name = weechat::buffer_get_string($buffer_pointer, "short_name");	# get short_name of buffer

	unless ($priority < $options{lowest_priority}){
	  create_output($buffer_number, $short_name);
	}
    }
  weechat::infolist_free($hotlist);
	    $table = @table;
	    if ($table eq 0){
	      unless ($options{external_command_hotlist_empty} eq ""){				# does we have a command for empty string?
		if ($options{use_title} eq "on"){
		  weechat::window_set_title(eval_expression($options{external_command_hotlist_empty}));
		}else{
		if (grep (/\%h/,$options{external_command_hotlist_empty})){			# does %h is in string?
		  $options{external_command_hotlist_empty} =~ s/%h/$weechat_dir/;		# add weechat-dir
		}
		  system(eval_expression($options{external_command_hotlist_empty}));
		}
	      }
	    }
  return weechat::WEECHAT_RC_OK;
}

sub create_output{
        my ($buffer_number, $short_name) = @_;
	  $res = eval_expression($options{hotlist_format});                            # save hotlist format
	  $res2 = eval_expression($options{external_command_hotlist});                 # save external_hotlist format

	    if ($priority == 3){							# priority is highlight
	      if (grep (/\%H/,$options{hotlist_format})){				# check with original!!!
		$res =~ s/\%H/$options{highlight_char}/g;
	      }
	    }else{									# priority != 3
		$res =~ s/\%H//g;							# remove all %H
	    }
   if ($priority <= $options{priority_remove}){
	      $res =~ s/$options{hotlist_remove_format}//;				# remove hotlist_remove_format
	    if (grep (/\%S/,$options{hotlist_format})){					# does %S is in string? (check with original!!!)
		  $res =~ s/%S/$short_name/;						# add short_name
	    }
            if (grep (/\%N/,$options{hotlist_format})){
	      $res =~ s/%N/$buffer_number/;						# add buffer_number
	    }
   }else{
	    if (grep (/\%S/,$options{hotlist_format})){					# does %S is in string? (check with original!!!)
		  $res =~ s/%S/$short_name/;						# add short_name
	    }
            if (grep (/\%N/,$options{hotlist_format})){
	      $res =~ s/%N/$buffer_number/;						# add buffer_number
	    }
    }
	    if ($res ne $options{hotlist_format} and $res ne ""){			# did $res changed?
		my $res2 = $res;							# save search string.
		$res2=qq(\Q$res2);							# kill metachars, for searching first
		unless (grep /^$res2$/, @table){					# does we have added $res to @table?
		push (@table, $res);							# No, then add it to @table
	      }
	    }

	    $res=qq(\Q$res);								# kill metachars first
	    if (grep /^$res$/, @table){							# does we have added $res to @table?
	      my $export = join("$options{delimiter}", sort_routine(@table));
	      $export = qq(\Q$export);							# escape special characters
	      if (grep (/\%X/,$options{external_command_hotlist})){			# check for %X option.
		$res2 =~ s/%X/$export/;

		if (grep (/\%h/,$options{external_command_hotlist})){			# does %h is in string?
		  $res2 =~ s/%h/$weechat_dir/;						# add weechat-dir
		}

		if ($options{use_title} eq "on"){
		  weechat::window_set_title($res2);
		}else{
	    	system($res2);
		}

	      }
	    }
}

# first sort channels with highlight, then channels with
# action and the rest will be placed at the end of list
sub sort_routine {
  my @zeilen = @_;
  my @sortiert = map { $_->[0] }
  map { [$_,(split (/\*/,$_))[1]] } @zeilen ;
  sort { $a->[0] cmp $b->[0] }		#sort{$a<=>$b}(@zeilen);
return @sortiert;
}

sub _extern{
  my ($data) = ($_[0]);
	system($data) unless($data eq "");
  return weechat::WEECHAT_RC_OK;
}

sub eval_expression{
    my ( $string ) = @_;
    $string = weechat::string_eval_expression($string, {}, {},{});
    return $string;
}

sub init_config{
    foreach my $option(keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option});
        }
        else{
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
}

sub toggle_config_by_set{
    my ( $pointer, $name, $value ) = @_;
    $name = substr($name,length("plugins.var.perl.$SCRIPT_NAME."),length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

# first function called by a WeeChat-script.
weechat::register($SCRIPT_NAME, $SCRIPT_AUTHOR, $SCRIPT_VERSION,
                  "GPL3", $SCRIPT_DESC, "", "");

weechat::hook_command($SCRIPT_NAME, $SCRIPT_DESC,
                        "",
                        "This script allows you to export the hotlist to a file or screen title.\n".
                        "use the following intern variables for the hotlist_format:\n".
                        " %h = weechat-dir (~/.weechat), better use \${info:weechat_dir}\n".
                        " %H = replaces with highlight_char, if a highlight message was received. For example: *\n".
                        " %N = replaces with buffer number: 1 2 3 ....\n".
                        " %S = replaces with short name of channel: #weechat\n".
                        " %X = export the whole hotlist_format to your external command.\n".
                        "\n".
                        "configure script with: /fset plugins.var.perl.hotlist2extern\n".
                        "print hotlist to screen title: plugins.var.perl.hotlist2extern.use_title\n".
                        "delimiter to use             : plugins.var.perl.hotlist2extern.delimiter\n".
                        "charset for highlight message: plugins.var.perl.hotlist2extern.highlight_char\n".
                        "message priority for hotlist_remove_format (-1 means off): plugins.var.perl.hotlist2extern.priority_remove\n".
                        "display messages level       : plugins.var.perl.hotlist2extern.lowest_priority\n".
                        "following options are evaluated:\n".
                        "template for display         : plugins.var.perl.hotlist2extern.hotlist_format\n".
                        "template for low priority    : plugins.var.perl.hotlist2extern.hotlist_remove_format\n".
                        "Output format                : plugins.var.perl.hotlist2extern.external_command_hotlist\n".
                        "Output format 'no activity'  : plugins.var.perl.hotlist2extern.external_command_hotlist_empty\n".
                        "",
                        "", "", "");


init_config();  # /set
$weechat_dir = weechat::info_get("weechat_dir", "");
weechat::hook_signal("hotlist_changed", "hotlist_changed", "");
weechat::hook_config( "plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "" );
