# Copyright (C) 2012 Stefan Wold <ratler@stderr.eu>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#
# Automatically join channels on UnderNET that get throttled due to "Target change too fast".

use strict;
use warnings;

my $SCRIPT_NAME = "join2fast";
my $VERSION = "0.5";
my $weechat_version = "";
my %timers;
my %channel_list;


# Register script
weechat::register($SCRIPT_NAME, "Ratler <ratler\@stderr.eu>", $VERSION, "GPL3",
                  "Automatically join channels on UnderNET that get throttled due to \"Target change too fast\"", "", "");

$weechat_version = weechat::info_get("version_number", "");
if ($weechat_version < 0x00030200) {
  weechat::print("", weechat::prefix("error") . "$SCRIPT_NAME: requires weechat >= v0.3.2");
  weechat::command("", "/wait 1ms /perl unload $SCRIPT_NAME");
}

# Callback for "Target changed too fast" events
weechat::hook_signal("*,irc_raw_in_439", "event_439_cb", "");

sub event_439_cb {
  # $_[1] - name of the event
  # $_[2] - the message (:server 439 nick #channel :Target change too fast. Please wait 17 seconds.)

  my $server = (split ",", $_[1])[0];
  my @msg = split " ", $_[2];
  my $channel = $msg[3];
  my $delay = $msg[10];

  # Check if channel has been already added or add it
  if (!exists($channel_list{$server}) or ((ref $channel_list{$server} eq 'ARRAY') and !($channel ~~ @{$channel_list{$server}}))) {
    push @{$channel_list{$server}}, $channel;
  }

  # Reset timer to the last delay received
  weechat::unhook($timers{$server}) if $timers{$server};
  $timers{$server} = weechat::hook_timer(($delay + 2) * 1000, 0, 1, "join_channel_cb", $server);

  return weechat::WEECHAT_RC_OK;
}

sub join_channel_cb {
  my $server = shift;

  if ((ref $channel_list{$server} eq 'ARRAY') and scalar @{$channel_list{$server}} > 0) {
    my $channel = pop @{$channel_list{$server}};

    # Save current buffer
    my $buffer_ptr = weechat::current_buffer();
    my $buffer_name = weechat::buffer_get_string($buffer_ptr, "name");

    if ($weechat_version >= 0x00040000) {
      weechat::command("", "/join -noswitch -server $server $channel");
    } else {
      weechat::command("", "/join -server $server $channel");
    }

    # Switch back to the old buffer (a bit flakey) - disabled when irc.look.buffer_switch_join is set to off
    # or weechat version >= 0.4.0
    my $option = weechat::config_get("irc.look.buffer_switch_join");
    if (($weechat_version < 0x00040000) and weechat::config_boolean($option)) {
      weechat::command("", "/wait 1s /buffer $buffer_name");
    }

    # Setup a new timer
    if ((ref $channel_list{$server} eq 'ARRAY') and scalar @{$channel_list{$server}} > 0) {
      $timers{$server} = weechat::hook_timer(4 * 1000, 0, 1, "join_channel_cb", $server);
    } else {
      delete $channel_list{$server};
    }
  }

  return weechat::WEECHAT_RC_OK;
}
