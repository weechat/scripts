#!/usr/bin/perl -w
# -----------------------------------------------------------------------------
# Copyright (c) 2010 by rettub <rettub@gmx.net>
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
# -----------------------------------------------------------------------------
# filter_ext.pl for weechat version 0.3.0 or later
#
# Quick help against spam, extend /filter with prefixes for following args: del, enable, disable, list
# Listens for highlights and sends them to a bar.
#
# Usage:
#   install srcipt and do /help filter_ext
#
# Configuration:
#   none
#
# -----------------------------------------------------------------------------
# Changelog:
#
# Version 0.01 2010-01-17
# initial version

use 5.006;

#use Carp;	    # don't use die in modules
#use Carp::Clan;    # or better use this

use strict;
use warnings;

my $Version = 0.01;

sub version {
    $Version;
}

my $SCRIPT      = "filter_ext";
my $AUTHOR      = "rettub";
my $LICENCE     = "GPL3";
my $DESCRIPTION = "Quick help against spam, extend /filter with prefixes for following args: del, enable, disable, list";
my $COMMAND     = "filter_ext";             # new command name
my $COMPLETITION  = "del|enable|disable|list";
my $CALLBACK      = $COMMAND;
my $ARGS_HELP   = "list regex | del regex | enable regex | disable regex";
my $CMD_HELP    = <<EO_HELP;

Quick access to filters on spam invasion via prefixes for filter-names.

First you should define an alias like
  /alias /f /filter add SPAM\$1 irc. * \$1

With this alias you can simply add filters for spam with copy and paste. 
  /f copy_and_pasted_string

With the alias /f, defined above, filters like

  [SPAMcopy_and_pasted_string] buffer: irc. / tags: * / regex: copy_and_pasted_string

will be created.

Now you can simply list/disable/enable or delete them at once like

  /filter_ext del SPAM

Keep in mind 'SPAM' is handled as a perl regex, so all filternames containing 'SPAM' will be deleted. If you want del filter-names beginning with 'SPAM' use

  /filter_ext del ^SPAM

instead. (for perl regular expressions, look at: perldoc perlre)

To be more quick define aliases like:
  /alias /fddel  /filter_ext del ^SPAM
  /alias /fl     /filter_ext list SPAM
  /alias /fd     /filter_ext disable SPAM
  /alias /fe     /filter_ext enable SPAM

EO_HELP

my $DEBUG=0;
sub DEBUG {weechat::print('', "***\t" . $SCRIPT . ": $_[0]") if $DEBUG;}
sub wprint {weechat::print('', "\t $_[0]");}
sub werror {weechat::print('', weechat::prefix("error")."$COMMAND: $_[0]");}

my $Input_buffer;

use constant {
    ENABLED => 1,
    DISABLED =>0,
};

sub list {
    my $regex = shift;

    my $infolist = weechat::infolist_get( "filter", "", "" );

    my $i = 0;
    while ( weechat::infolist_next($infolist) ) {

        my $fname = weechat::infolist_string( $infolist, "name" );


        if ( $fname =~ /$regex/ ) {
        wprint("Message filters with regex '$regex':") if $i == 0;
        $i++;
            my $regex  = weechat::infolist_string( $infolist, "regex" );
            my $plugin = weechat::infolist_string( $infolist, "plugin_name" );
            my $buffer = weechat::infolist_string( $infolist, "buffer_name" );
            my $tags   = weechat::infolist_string( $infolist, "tags" );
            DEBUG("filer_regex: $regex");
            my $enabled = weechat::infolist_integer( $infolist, "enabled" );
            DEBUG("filer_enaled: $enabled");
            wprint( " "
                  . weechat::color("green") . "["
                  . weechat::color("reset")
                  . $fname
                  . weechat::color("green") . "]"
                  . weechat::color("reset")
                  . "   plugin.(buffer): "
                  . weechat::color("red")
                  . "$plugin"
                  . weechat::color("reset") . "."
                  . ( $buffer ? $buffer : "all_buffers" )
                  . " / tags: $tags"
                  . " /  regex: $regex" . " /  "
                  . ( $enabled ? 'enabled  ' : 'disabled' ) );
        }
    }
}

sub toggle {
    my ( $regex, $cmd, $flag ) = @_;

    my $infolist = weechat::infolist_get( "filter", "", "" );

    while ( weechat::infolist_next($infolist) ) {

        my $fname = weechat::infolist_string( $infolist, "name" );
        if ( $fname =~ /$regex/ ) {
            next
              unless weechat::infolist_integer( $infolist, "enabled" ) == $flag;
            weechat::command( "", "/filter $cmd $fname" );
        }
    }
}

sub del {
    my ($regex) = @_;

    my $infolist = weechat::infolist_get( "filter", "", "" );

    while ( weechat::infolist_next($infolist) ) {

        my $fname = weechat::infolist_string( $infolist, "name" );
        if ( $fname =~ /$regex/ ) {
            weechat::command( "", "/filter del $fname" );
        }
    }
}

sub filter_ext {
    #my ( undef, undef, $_cmd ) = @_;
    my ($_cmd, $args) = split(/ /, $_[2], 2);

        DEBUG($_cmd);
        DEBUG($args);

        if ( not defined $args ) {
            werror("no regex defined see /help $SCRIPT" );
    return weechat::WEECHAT_RC_OK;
        }
    if ( $_cmd eq 'list' ) {
        list($args);
    } elsif ($_cmd eq 'disable' ) {
        toggle($args, $_cmd, ENABLED);
    } elsif ($_cmd eq 'enable' ) {
        toggle($args, $_cmd, DISABLED);
    } elsif ($_cmd eq 'del' ) {
        del($args);
    }


    return weechat::WEECHAT_RC_OK;
}

# init script
if ( weechat::register(  $SCRIPT,  $AUTHOR, $Version, $LICENCE, $DESCRIPTION, "", "" ) ) {

    weechat::hook_command( $COMMAND,  $DESCRIPTION,  $ARGS_HELP, $CMD_HELP, $COMPLETITION, $CALLBACK, "" );
}

# vim: ai ts=4 sts=4 et sw=4 foldmethod=marker :
