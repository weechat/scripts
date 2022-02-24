use strict;
use warnings;

# pv_info.pl – a WeeChat script that attach a new bar in query windows showing
# formatted `whois` information of chat partners and keep them updated using a timer.
# Copyright (C) 2018 Max Wölfing <ff0x@infr.io>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# TODO
# - Read/store user defined variables in configuration
# - Extend missing WHOIS informations and beautify output
# - Better sorting mechanism for WHOIS informations (see: FIXME_SORTING)
# - Maybe switch to WeeChat API for WHOIS (infolist/irc_nick)

# KNOWN BUGS
# - 'init_bar_item' is called 4 times, but only one time directly by this script, probably a bug in WeeChat.

# -- Config --
my $bar_name = 'pv_info_bar';
my $bar_item_name = 'whois';
my $bar_item_refresh = 120;

# -- Internal --
use constant DEBUG => (0);
use if DEBUG, 'Data::Dumper';
my $script_name = 'pv_info';
my $script_version = '0.0.6';
my $script_description = 'Attach a new bar in query windows, showing `whois` information of chat partners';
my (%whois, %hooks);

# -- Init --
weechat::register($script_name, 'Max Woelfing <ff0x@infr.io>',
                  $script_version,'GPL3', $script_description,'unload_cb', '');

if ((weechat::info_get('version_number', '') // 0) < 0x00040000) {
  weechat::print('', "WeeChat version >= 0.4.0 is required to run $script_name");
} else {
  if (weechat::config_string(weechat::config_get('weechat.bar.title.conditions')) !~ m/\$\{type\} != private/)  {
    weechat::print('','To disable the (unnecessary) '.weechat::color('yellow').'title bar'.weechat::color('default').
                   ' in private buffers, set: '.weechat::color('bold').'weechat.bar.title.conditions'.weechat::color('default').
                   ' to '.weechat::color('bold').'"${type} != private"');
  }

  weechat::bar_item_new($bar_item_name, 'init_bar_item', '');
  if ((weechat::info_get('version_number', '') // 0) >= 0x02090000) {
      weechat::bar_new($bar_name, 'off', '500', 'window', '${type} == private', 'top',
                       'vertical', 'horizontal', '0', '0', 'default', 'default', 'default', 'default',
                       'on', $bar_item_name);
  } else {
      weechat::bar_new($bar_name, 'off', '500', 'window', '${type} == private', 'top',
                       'vertical', 'horizontal', '0', '0', 'default', 'default', 'default',
                       'on', $bar_item_name);
  }

  # -- Hooks --
  $hooks{'sigwhois'}    = weechat::hook_hsignal('irc_redirection_sigwhois_whois', 'sigwhois_cb', '');
  $hooks{'timer'}       = weechat::hook_timer($bar_item_refresh * 1000, 60, 0, 'trigger_update', '');
  $hooks{'pv_opened'}   = weechat::hook_signal('irc_pv_opened', 'sigwhois_send', '');
  $hooks{'buf_switch'}  = weechat::hook_signal('buffer_switch', 'sigwhois_send', '');
  $hooks{'buf_closing'} = weechat::hook_signal('buffer_closing', 'buf_closing_cb', '');

  weechat::print('', "$script_name loaded!");
}

sub init_bar_item {
  my ($data, $bar_item, $window) = @_;
  my $buffer = weechat::window_get_pointer($window, 'buffer');
  my $server = weechat::buffer_get_string($buffer, 'localvar_server');

  if (weechat::buffer_get_string($buffer, 'localvar_type') eq 'private') {
    my $nick = weechat::buffer_get_string($buffer, 'localvar_channel');
    my $mask = "$nick\@$server";

    if (weechat::info_get('irc_is_nick', $nick) eq '') {
      weechat::print('', weechat::prefix('network').'No nick for window found') if DEBUG;

      return '';
    }

    # TODO: Get /whois info from weechat API

    weechat::print('', weechat::prefix('network')."bar_item initialised for Nick = $nick, Mask = $mask") if DEBUG;

    my $user = weechat::color('default').weechat::color('bold').'['.weechat::color('darkgray').$nick.weechat::color('default').weechat::color('bold').']';
    my $str = '';

    # FIXME_SORTING
    # Sort output of 'whois' command by name of 'whois message' (number prefix)
    for my $whois_msg (sort {lc $a cmp lc $b} keys %{$whois{$mask}}) {
      $str .= "$user $whois{$mask}{$whois_msg}" . "\n";
    }

    # Remove spaces and/or linefeed at the end
    $str =~ s/\s+$//;
    chomp($str);

    # If empty, set to [$nick]
    if (length($str) == 0) {
      $str = "$user";
    }

    return $str;
  }
}

sub sigwhois_send {
  my ($data, $signal, $signal_data) = @_;

  my $buffer;
  if ($signal eq 'triggered_by_timer') {
    $buffer = $signal_data;
  } else {
    $buffer = weechat::current_buffer();
  }
  my $server = weechat::buffer_get_string($buffer, 'localvar_server');

  if (weechat::buffer_get_string($buffer, 'localvar_type') eq 'private') {
    my $nick = weechat::buffer_get_string($buffer, 'localvar_channel');

    if (weechat::info_get('irc_is_nick', $nick) eq '') {
      return weechat::WEECHAT_RC_ERROR;
    }

    my $mask = "$nick\@$server";
    if ($whois{$mask}) {
      weechat::print('', weechat::prefix('network')."Deleting old WHOIS info for user: $mask") if DEBUG;
      delete $whois{$mask};
    }

    weechat::print('', weechat::prefix('network').'Sending whois signal..') if DEBUG;
    weechat::hook_hsignal_send('irc_redirect_command', { 'server' => $server, 'pattern' => 'whois', 'signal' => 'sigwhois' });
    weechat::hook_signal_send('irc_input_send', weechat::WEECHAT_HOOK_SIGNAL_STRING, "$server;;1;;/whois $nick $nick");
  }

  return weechat::WEECHAT_RC_OK;
}

sub sigwhois_cb {
  my ($data, $signal, $signal_data) = @_;
  my %hashtable = %{$signal_data};

  weechat::print('', weechat::prefix('network').'We got an whois reply..') if DEBUG;

  # Sometimes IRC:311 is not the first WHOIS response and so we cannot set $mask on it, in that case we fill a generic user table,
  # and merge it later, but first we have to clean the room..
  my $mask = '__undefined__';
  if ($whois{$mask}) {
    delete $whois{$mask};
  }
  my $server = $hashtable{'server'};
  my $bee_user = 0;
  if ($server eq "bitlbee") {
    $bee_user = 1;
  }
  foreach my $line ($hashtable{'output'}) {
    weechat::print('', weechat::prefix('network')."+--------------------------------------------------------------------------------------------------+\n".$line."\n".
                       weechat::prefix('network').'+--------------------------------------------------------------------------------------------------+') if DEBUG;

    # 275 - whois (secure connection)
    if ($line =~ /275 (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'HHH_secure_connection'} = weechat::color('default').$3;
    }

    # 276 - whois (certificate fingerprint)
    if ($line =~ /276 (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'III_cert_fingerprint'} = weechat::color('default').$3;
    }

    # 301 - whois (away)
    if ($line =~ /301 (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'BBB_away'} = weechat::color('bold')."Away status: ".weechat::color('darkgray').$3;
    }

    # 307 - whois (registered nick)
    if ($line =~ /307 (.*) :user (.*)/) {
      $whois{$mask}{'MMM_registered'} = weechat::color('default').$2;
    }

    # 310 - whois (help mode)

    # 311 - whois (user)
    if ($line =~ /311 (\S+) (\S+) (\S+) (\S+) (.*) :(.*)/) {
      $mask = "$2\@$server";
      weechat::print('', weechat::prefix('network')."Using '$mask' as '\$whois{\$mask}'") if DEBUG;
      $whois{$mask}{'AAA_user'} = weechat::color('white').$6. " ".weechat::color('darkgray')."(".weechat::color('88')."$2\@$4".weechat::color('darkgray').")";
    }

    # 312 - whois (server)
    if ($line =~ /312 (\S+) (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'EEE_server'} = weechat::color('default').$3." ".weechat::color('default')."(".weechat::color('bold').$4.weechat::color('default').")";
    }

    # 313 - whois (operator)

    # 317 - whois (idle)
    if ($line =~ /317 (\S+) (\S+) (\d+) (\d+) (.*)/) {
      my $idle_time;
      my @idle_time_parts;
      if ($3 != 0) {
        @idle_time_parts = gmtime($3);
        $idle_time = sprintf("%d days, %d hours, %d minutes, %d seconds",@idle_time_parts[7,2,1,0]);
      } else {
        $idle_time = "No";
      }
      my $signon = scalar localtime $4;
      $whois{$mask}{'LLL_idle'} = weechat::color('bold')."idle: ".weechat::color('darkgray').$idle_time.weechat::color('default').", ".weechat::color('bold')."signon at: ".weechat::color('darkgray').$signon;
    }

    # 318 - whois (end)

    # 319 - whois (channels)
    if ($line =~ /319 (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'DDD_channels'} = weechat::color('darkgray').$3;
    }

    # 320 - whois (identified user)
    # FIXME
    if ($line =~ /320 (\S+) (\S+) :(.*)/) {
      my $away_msg = $3;
      if (length($away_msg) >= 20) {
        if ($away_msg =~ /^(\S+) .* as a result .* (\d* min)/) {
          $away_msg = "$1 (As a result of being idle more than $2)";
        }
      }
      $whois{$mask}{'CCC_identified_user'} = weechat::color('bold')."Away / Status message: ".weechat::color('darkgray').$away_msg;
    }

    # 326 - whois (has oper privs)
    # 327 - whois (host)

    # 330 - whois (logged in as)
    if ($line =~ /330 (\S+) (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'JJJ_logged_in_as'} = weechat::color('default').$4." ".weechat::color('bold').$3;
    }

    # 335 - whois (is a bot on)

    # 338 - whois (host)
    if ($line =~ /338 (\S+) (\S+) (\S+) (\S+) :.*/) {
      $whois{$mask}{'KKK_host'} = weechat::color('bold')."Actual user\@host: ".weechat::color('darkgray').$3.weechat::color('default').", ".weechat::color('bold')."Actual IP: ".weechat::color('darkgray').$4;
    }

    # 343 - whois (is opered as)

    # 378 - whois (connecting from)
    if ($line =~ /378 (\S+) (\S+) (\S+) (.*)/) {
      $whois{$mask}{'FFF_connecting_from'} = weechat::color('default').$4;
    }

    # 379 - whois (using modes)
    # 401 - no such nick/channel
    # 402 - no such server

    # 671 - whois (secure connection)
    if ($line =~ /671 (\S+) (\S+) :(.*)/) {
      $whois{$mask}{'GGG_secure_connection'} = weechat::color('default').$3;
    }
  }

  # Add a custom informations for BitlBee user
  if ($bee_user == 1) {
    $whois{$mask}{'ZZZ_bitlbee'} = "is connected by ".weechat::color('yellow').weechat::color('bold')."BitlBee";
  }

  # If we have some data in $whois{'__undefined__'} merge it
  if ($mask ne '__undefined__' && $whois{'__undefined__'}) {
    weechat::print('', weechat::prefix('network')."We have data in __undefined__, need to merge it with \$whois{'$mask'}..") if DEBUG;
    foreach my $key (keys %{$whois{'__undefined__'}}) {
      $whois{$mask}{$key} = $whois{'__undefined__'}{$key};
    }
    delete $whois{'__undefined__'};
  }

  weechat::print('', weechat::prefix('network').'Got new informations, updating bar_item..') if DEBUG;
  weechat::bar_item_update($bar_item_name);

  return weechat::WEECHAT_RC_OK;
}

sub trigger_update {
  my $buffer = weechat::current_buffer();

  if (weechat::buffer_get_string($buffer, 'localvar_type') ne "private") {
    return weechat::WEECHAT_RC_OK;
  }

  weechat::print('', weechat::prefix('network').'Updating the current private buffer using the trigger..') if DEBUG;
  sigwhois_send('', 'triggered_by_timer', $buffer);

  return weechat::WEECHAT_RC_OK;
}

sub buf_closing_cb {
  my ($data, $signal, $buffer) = @_;

  if (weechat::buffer_get_string($buffer, 'localvar_type') ne "private") {
    return weechat::WEECHAT_RC_OK;
  }

  my $nick = weechat::buffer_get_string($buffer, 'localvar_channel');
  return weechat::WEECHAT_RC_OK if (weechat::info_get('irc_is_nick', $nick) eq '');

  if ($whois{$nick}) {
    delete $whois{$nick};
  }

  return weechat::WEECHAT_RC_OK;
}

sub unload_cb {
  for my $hook (keys %hooks) {
    weechat::unhook($hooks{$hook});
  }
  weechat::bar_remove(weechat::bar_search($bar_name));
  weechat::bar_item_remove(weechat::bar_item_search($bar_item_name));
}
