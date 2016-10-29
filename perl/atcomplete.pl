# Copyright 2015 by David A. Golden. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# ABOUT
#
# atcomplete.pl
#
# Adds nick completion when prefixed with '@' for use with IRC gateways
# for Slack, Flowdock, etc. as these require the '@' to highlight users
#
# CONFIG
#
# /set plugins.var.perl.atcomplete.enabled
#
# HISTORY
#
# 0.001 -- xdg, 2016-04-06
#
#   - initial release
#
# REPOSITORY
#
# https://github.com/xdg/weechat-atcomplete

use strict;
use warnings;
my $SCRIPT_NAME = "atcomplete";
my $VERSION = "0.001";

my %options_default = (
    'enabled' => ['on', 'enable completion of nicks starting with @'],
);
my %options = ();

weechat::register($SCRIPT_NAME, "David A. Golden", $VERSION,
                  "Apache2", "atcomplete - do nick completion following @", "", "");
init_config();

weechat::hook_config("plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "");
weechat::hook_completion("nicks", "Add @ prefix to nick completion", "complete_at_nicks", "");

sub complete_at_nicks {
    my ($data, $completion_item, $buffer, $completion ) = @_;
    return weechat::WEECHAT_RC_OK() unless $options{enabled} eq 'on';

    my $nicklist = weechat::infolist_get("nicklist", weechat::current_buffer(), "");

    if ($nicklist ne "") {
        while (weechat::infolist_next($nicklist)) {
            next unless weechat::infolist_string($nicklist, "type") eq "nick";
            my $nick = weechat::infolist_string($nicklist, "name");
            weechat::hook_completion_list_add($completion, "\@$nick", 1, weechat::WEECHAT_LIST_POS_SORT());
        }
    }

    weechat::infolist_free($nicklist);

    return weechat::WEECHAT_RC_OK();
}

sub toggle_config_by_set {
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".$SCRIPT_NAME."."), length($name));
    $options{$name} = $value;
    return weechat::WEECHAT_RC_OK();
}

sub init_config {
    my $version = weechat::info_get("version_number", "") || 0;
    foreach my $option (keys %options_default)
    {
        if (!weechat::config_is_set_plugin($option))
        {
            weechat::config_set_plugin($option, $options_default{$option}[0]);
            $options{$option} = $options_default{$option}[0];
        }
        else
        {
            $options{$option} = weechat::config_get_plugin($option);
        }
        if ($version >= 0x00030500)
        {
            weechat::config_set_desc_plugin($option, $options_default{$option}[1]." (default: \"".$options_default{$option}[0]."\")");
        }
    }
}
