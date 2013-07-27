# Copyright (C) 2012-2013 Stefan Wold <ratler@stderr.eu>
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
# Source available on GitHUB: https://github.com/Ratler/join2fast
#
#
# Automatically queue and join channels on UnderNET that get throttled due to "Target change too fast".

use 5.010;
use POSIX qw/strftime/;
use strict;
use warnings;

my $SCRIPT_NAME = "join2fast";
my $VERSION = "0.8";
my %timers;
my %next_join;
my %channel_list;
my %default_options = ('timer_delay'    => ['4', 'default delay in seconds added to the timer before trying to join the next channel in the list'],
                       'date_format'    => ['%H:%M:%S', 'date and time format for time of the next join. Used by join2fast bar item.'],
                       'hide_event_msg' => ['on', 'hide target change too fast message']);
my %options = ();


# Register script
weechat::register($SCRIPT_NAME, "Ratler <ratler\@stderr.eu>", $VERSION, "GPL3",
                  "Automatically join channels on UnderNET that get throttled due to \"Target change too fast\"", "clear_all_on_script_unload", "");

my $weechat_version = weechat::info_get("version_number", "") || 0;
if ($weechat_version < 0x00030200) {
  weechat::print("", weechat::prefix("error") . "$SCRIPT_NAME: requires weechat >= v0.3.2");
  weechat::command("", "/wait 1ms /perl unload $SCRIPT_NAME");
}

# Initialize config
init_config();

# Hook command /j2f
weechat::hook_command("j2f",
                      "list/clear join2fast queue",
                      "[list] | [clear [server]]",
                      "   list: list current queues\n".
                      "   clear [server]: clear all queues or the queue for a specific server",
                      "list || clear %(irc_servers)",
                      "j2f_command_cb", "");

# Hook server disconnect to clear active queue
weechat::hook_signal("irc_server_disconnected", "clear_queue_on_disconnect", "");

# Callback for "Target change too fast" events
weechat::hook_modifier("irc_in_439", "event_439_cb", "");

# Setup bar item
weechat::bar_item_new($SCRIPT_NAME, "bar_cb", "");

sub event_439_cb {
  my ($data, $modifier, $server, $string) = @_;
  # $string - the message (:server 439 nick #channel :Target change too fast. Please wait 17 seconds.)
  my $channel = (split " ", $string)[3];
  my $delay = (split " ", $string)[10];

  # Return if target is not a channel
  # TODO: Add option to allow queueing private messages
  return $string unless $channel =~ /^(#|&)/;

  # Check if channel has been already added or add it
  if (!exists($channel_list{$server}) or ((ref $channel_list{$server} eq 'ARRAY') and !($channel ~~ @{$channel_list{$server}}))) {
    push @{$channel_list{$server}}, $channel;
  }

  # Reset timer to the last delay received
  weechat::unhook($timers{$server}) if exists($timers{$server});

  $next_join{$server} = {timestamp => time() + $delay + 2};
  $timers{$server} = weechat::hook_timer(($delay + 2) * 1000, 0, 1, "join_channel_cb", $server);

  # Update bar
  weechat::bar_item_update($SCRIPT_NAME);

  return $string if lc($options{hide_event_msg}) eq 'off';
  return "";
}

sub clear_queue_on_disconnect {
  my $server = $_[2];

  if (exists($channel_list{$server})) {
    delete $channel_list{$server};
    delete $next_join{$server};
    weechat::bar_item_update($SCRIPT_NAME);
  }

  return weechat::WEECHAT_RC_OK;
}

sub clear_all_on_script_unload {
  foreach my $server (keys %timers) {
    weechat::unhook($timers{$server});
  }
  undef %channel_list;
  undef %next_join;

  return weechat::WEECHAT_RC_OK;
}

sub join_channel_cb {
  my $server = shift;

  if ((ref $channel_list{$server} eq 'ARRAY') and scalar @{$channel_list{$server}} > 0) {
    my $channel = pop @{$channel_list{$server}};

    if ($weechat_version >= 0x00040000) {
      weechat::command("", "/join -noswitch -server $server $channel");
    } else {
      # Save current buffer
      my $buffer_ptr = weechat::current_buffer();
      my $buffer_name = weechat::buffer_get_string($buffer_ptr, "name");

      weechat::command("", "/join -server $server $channel");

      # Switch back to the old buffer (a bit flakey) - disabled when irc.look.buffer_switch_join is set to off
      my $option = weechat::config_get("irc.look.buffer_switch_join");
      if (weechat::config_boolean($option)) {
        weechat::command("", "/wait 1s /buffer $buffer_name");
      }
    }

    # Setup a new timer
    if ((ref $channel_list{$server} eq 'ARRAY') and scalar @{$channel_list{$server}} > 0) {
      $timers{$server} = weechat::hook_timer($options{timer_delay} * 1000, 0, 1, "join_channel_cb", $server);
      $next_join{$server} = {timestamp => time() + $options{timer_delay}};
    } else {
      delete $channel_list{$server};
      delete $next_join{$server};
    }
  }

  # Update bar
  weechat::bar_item_update($SCRIPT_NAME);

  return weechat::WEECHAT_RC_OK;
}

sub bar_cb {
  my $queue_size = 0;

  foreach my $server (keys %channel_list) {
    $queue_size += scalar @{$channel_list{$server}};
  }

  if ($queue_size > 0) {
    return "Q: $queue_size N: " . get_next_join_time();
  }

  return "";
}

sub get_next_join_time {
  my $key = (sort {$next_join{$a}->{timestamp} <=> $next_join{$b}->{timestamp}} keys (%next_join))[0];
  return strftime($options{date_format}, localtime($next_join{$key}{timestamp}));
}

sub j2f_command_cb {
  my ($data, $buffer, $args) = @_;
  my ($option, $arg) = split " ", $args;

  if ($option eq 'list') {
    if (scalar (keys %channel_list) > 0) {
      foreach my $server (keys %channel_list) {
        weechat::print("", "$SCRIPT_NAME: Throttled channels on '$server': " . join(', ', @{$channel_list{$server}}));
      }
    } else {
      weechat::print("", "$SCRIPT_NAME: no channels currently queued.");
    }
  } elsif ($option eq 'clear') {
    if (defined($arg)) {
      if (exists($timers{$arg})) {
        weechat::unhook($timers{$arg});
        delete $timers{$arg};
      }
      delete $channel_list{$arg};
      delete $next_join{$arg};
    } else {
      foreach my $server (keys %channel_list) {
        if (exists($timers{$server})) {
          weechat::unhook($timers{$server});
          delete $timers{$server};
        }
        delete $channel_list{$server};
        delete $next_join{$server};
      }
    }
    weechat::bar_item_update($SCRIPT_NAME);
  }
  return weechat::WEECHAT_RC_OK;
}

sub init_config {
  foreach my $option (keys %default_options) {
    if (!weechat::config_is_set_plugin($option)) {
      weechat::config_set_plugin($option, $default_options{$option}[0]);
      $options{$option} = $default_options{$option}[0];
    } else {
      $options{$option} = weechat::config_get_plugin($option);
    }
    weechat::config_set_desc_plugin($option, $default_options{$option}[1] . " (default: " . $default_options{$option}[0] . ")") if ($weechat_version >= 0x00030500);
  }
}
