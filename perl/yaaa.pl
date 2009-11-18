# YaAA: Yet Another Auto Away Script written in Perl
# Copyright (c) 2009 by jnbek <jnbek@yahoo.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#Configuration Options:
#/set plugins.var.perl.yaaa.autoaway 10
#/set plugins.var.perl.yaaa.interval 5
#/set plugins.var.perl.yaaa.message AFK
#/set plugins.var.perl.yaaa.status on
#/set plugins.var.perl.yaaa.debug on
# Changelog:
#  0.1: first version
#  0.2: bug with toggle removed (nils <weechatter@arcor.de>)
#  0.2.1: Check configuration options for changes and apply them..
#  0.3: Fixed more config bugs. Fully Tested.
# TODO: Add a nick changer.

my $version  = '0.3';
my $interval = 5;         # Seconds between checks
my $autoaway = 10;        # Minutes til away
my $message  = "AFK";
my $status   = "on";
my $debug    = "off";
my $description = "YaAA: Set your away status based on inactivity.";
my $help        = "Toggles On/Off status";
weechat::register( "YaAA", "jnbek", $version, "GPL3", $description, "", "" );
weechat::hook_command( "yaaa", $help, "", "", "", "switch_up", "" );
weechat::hook_timer( $interval * 1000, 60, 0, "chk_timer", "" );

sub chk_conf {
    my ( $self, $buffer, $args ) = @_;

    #Check if config exists and write it if it doesn't
    if ( !weechat::config_get_plugin('interval') ) {
        weechat::config_set_plugin( 'interval',, $interval );
    }
    else {
        $interval = weechat::config_get_plugin('interval');
    }
    if ( !weechat::config_get_plugin('autoaway') ) {
        weechat::config_set_plugin( 'autoaway', $autoaway );
    }
    else {
        $autoaway = weechat::config_get_plugin('autoaway');
    }
    if ( !weechat::config_get_plugin('message') ) {
        weechat::config_set_plugin( 'message', $message );
    }
    else {
        $message = weechat::config_get_plugin('message');
    }
    if ( !weechat::config_get_plugin('status') && $status ne 'away') {
        weechat::config_set_plugin( 'status', $status );
    }
    else {
        if ($status ne 'away'){
            $status = weechat::config_get_plugin('status');
        }
    }
    if ( !weechat::config_get_plugin('debug') ) {
        weechat::config_set_plugin( 'debug', $debug );
    }
    else {
        $debug = weechat::config_get_plugin('debug');
    }
    return weechat::WEECHAT_RC_OK;
}

sub switch_up {
    my ( $self, $buffer, $args ) = @_;

    #Check status and set accordingly
    if ( weechat::config_get_plugin("status") eq "on" ) {
        $status = "off";
        weechat::config_set_plugin( "status", $status );
        weechat::print( $buffer, "YaAA: Yet Another AutoAway is now $status" );
    }
    elsif ( weechat::config_get_plugin("status") eq "off" ) {
        $status = "on";
        weechat::config_set_plugin( "status", $status );
        weechat::print( $buffer, "YaAA: Yet Another AutoAway is now $status" );
    }
    return weechat::WEECHAT_RC_OK;
}

sub chk_timer {
    my ( $self, $buffer, $args ) = @_;
    if ( $debug eq 'on' ) {
        weechat::print( $buffer,
            "Inactivity: " . weechat::info_get( "inactivity", "" ) );
        weechat::print( $buffer, "Interval: $interval" );
        weechat::print( $buffer, "Autoaway: $autoaway" );
        weechat::print( $buffer, "Message: $message" );
        weechat::print( $buffer, "Status: $status" );
        weechat::print( $buffer, "Debug: $debug" );
    }
    &chk_conf;
    return weechat::WEECHAT_RC_OK if $status eq 'off';
    if ( weechat::info_get( "inactivity", "" ) >= $autoaway * 60
        && $status ne "away" )
    {
        weechat::command( $buffer, "/away -all $message" );
        $status = "away";
    }
    elsif ( weechat::info_get( "inactivity", "" ) <= $autoaway * 60
        && $status eq "away" )
    {
        weechat::command( $buffer, "/away -all" );
        $status = "unaway";
    }
    return weechat::WEECHAT_RC_OK;
}
