# Al-Caveman <toraboracaveman@gmail.com>
# Licensed under GPL3
# https://github.com/Al-Caveman/commorkers

use warnings;
use strict;

# register script
weechat::register("commorkers", "Al-Caveman", "0.2", "GPL3", "Suppose that you have joined C many channels, then this script notifies you in each buffer about the movement of lurkers around you across all the C many channels.", "", "");

# option help
my $opt_ignore_nick = "ignore_nicks";
my $opt_ignore_all_triggered_notices = "ignore_all_triggered_notices";
my $opt_ignore_nick_triggered_notices = "ignore_nicks_triggered_notices";
unless (weechat::config_is_set_plugin($opt_ignore_nick)) {
    weechat::config_set_plugin($opt_ignore_nick, "");
}
unless (weechat::config_is_set_plugin($opt_ignore_all_triggered_notices)) {
    weechat::config_set_plugin($opt_ignore_all_triggered_notices, "off");
}
unless (weechat::config_is_set_plugin($opt_ignore_nick_triggered_notices)) {
    weechat::config_set_plugin($opt_ignore_nick_triggered_notices, "");
}

# colors
my $c_channel = weechat::color("chat_channel");
my $c_chat = weechat::color("chat");
my $c_chat_join = weechat::color("chat_prefix_join");
my $c_chat_quit = weechat::color("chat_prefix_quit");
my $c_emph = weechat::color("chat_prefix_error");

my $prefix = "$c_emph+++\t$c_emph";
my $notice = '';
my %notice_buffer;
sub common_lurkers {
    # get args
    my $data = shift;
    my $signal = shift;
    my $signal_data = shift;

    # process args
    my $weechat_signal_nick = weechat::info_get("irc_nick_from_host", $signal_data);
    my $weechat_signal_server;
    my $weechat_signal_channel;

    #weechat::print("", "data: $data");
    #weechat::print("", "signal: $signal");
    #weechat::print("", "signal_data: $signal_data");
    #weechat::print("", "    ".$weechat_signal_nick);

    if (($data eq 'j') || ($data eq 'p') || ($data eq 'q')) {
        $weechat_signal_server = (split(/,/, $signal))[0];
        #weechat::print("", "    server:".$weechat_signal_server);
        if (($data eq 'j') || ($data eq 'p')) {
            $weechat_signal_channel = (split(/ /, $signal_data))[2];
            #weechat::print("", "    channel:".$weechat_signal_channel);
        }
    }

    # get list of nicks to ignore their triggered notices
    my %ignore_nicks_trig_notice;
    if (weechat::config_is_set_plugin($opt_ignore_nick_triggered_notices)) {
        my $option_str = weechat::config_get_plugin($opt_ignore_nick_triggered_notices);
        $option_str =~ s/ //g;
        $ignore_nicks_trig_notice{lc $_} = 1 for grep {$_ !~ m/^ *$/} split(/,/, $option_str);
    }

    # see if triggered notices, as a whole, are disabled
    my $trig_notice_enabled = 1;
    if (weechat::config_is_set_plugin($opt_ignore_all_triggered_notices)) {
        my $option_str = weechat::config_get_plugin($opt_ignore_all_triggered_notices);
        $option_str =~ s/ //g;
        $trig_notice_enabled = 0 if $option_str =~ m/^on$/i;
    }

    # get current buffer
    my $buffer_current = weechat::current_buffer();
    my $buffer_current_name = weechat::buffer_get_string($buffer_current, "name");

    # get list of all buffers and nicks within them
    my %buffernicks;
    init_buffernicks(\%buffernicks);

    # print a masterlist of all common lurkers of the current buffer
    if (($data eq 'i')) {
        if ($buffer_current ne '') {
            my $commorkers_found = 0;
            if ($signal_data) {
                my @nick_buffers = sort grep {(defined $buffernicks{$_}{$signal_data}) && ($_ ne $buffer_current_name)} keys %buffernicks;
                if (scalar @nick_buffers) {
                    my $notice_tmp = "$prefix".weechat::color(weechat::nicklist_nick_get_string($buffer_current, weechat::nicklist_search_nick($buffer_current, "", $signal_data, "color")))."$signal_data$c_emph also lurks in: ".join(", ", map {$c_channel.$_.$c_emph} @nick_buffers);
                    $commorkers_found = 1;
                    weechat::print($buffer_current, $notice_tmp);
                }
            } else {
                # get nicklist of the current buffer
                my @buffer_current_nick_name_list = sort keys %{$buffernicks{$buffer_current_name}};

                # find which of the nicks in the current buffer also exist in other buffers
                for my $buffer_name (grep {$_ ne $buffer_current_name} sort keys %buffernicks) {
                    my @buffer_name_common_lurkers;
                    for my $buffer_current_nick_name (@buffer_current_nick_name_list) {
                        if (defined $buffernicks{$buffer_name}{$buffer_current_nick_name}) {
                            push @buffer_name_common_lurkers, $buffer_current_nick_name;
                        }
                    }
                    if (scalar @buffer_name_common_lurkers) {
                        my $notice_tmp = $prefix."common lurkers from $c_channel$buffer_name$c_chat$c_emph:\n".join(", ", map {weechat::color(weechat::nicklist_nick_get_string($buffer_current, weechat::nicklist_search_nick($buffer_current, "", $_), "color")).$_.$c_chat} @buffer_name_common_lurkers)."\n";
                        $commorkers_found = 1;
                        weechat::print($buffer_current, $notice_tmp);
                    }
                }
            }

            # no common lurkers found at all?
            if ($commorkers_found == 0) {
                    my $notice_tmp = $prefix."no common lurkage found";
                    $commorkers_found = 1;
                    $notice .= $notice_tmp;
                    weechat::print($buffer_current, $notice_tmp);
            }
        } else {
            my $notice_tmp = $prefix."must execute /commorkers in a channel";
            weechat::print($buffer_current, $notice_tmp);
        }
    }

    # handle a join/part event by printing all channels the joining nick is lurking
    # in
    if ((($data eq 'j') || ($data eq 'p')) && $trig_notice_enabled) {
        # get the buffer where the event occurred
        my $buffer_event_name = "$weechat_signal_server.$weechat_signal_channel";
        my $buffer_event = weechat::buffer_search("irc", $buffer_event_name);

        # find channels where the subject nick is lurking in
        my @lurker_common_buffers;
        for my $buffer_name (grep {$_ ne $buffer_event_name} sort keys %buffernicks) {
            if ((defined $buffernicks{$buffer_name}{$weechat_signal_nick}) && !(defined $ignore_nicks_trig_notice{$weechat_signal_nick})) {
                push @lurker_common_buffers, $buffer_name;
            }
        }

        # print notice in the channel where the join/part occurred
        if (scalar @lurker_common_buffers) {
            my $notice_tmp = join(", ", sort map {$c_channel.$_.$c_emph} @lurker_common_buffers)."\n";
            $notice .= $prefix."a lurker from: $notice_tmp";
            #weechat::print($buffer_event, $notice);

            # also print an incremental notification to all buffers were said
            # nick is lurking in
            for my $buffer_nickexists_name (@lurker_common_buffers) {
                my $buffer_nickexists = weechat::buffer_search("", $buffer_nickexists_name);
                my $c_lurker_nick = weechat::color(weechat::nicklist_nick_get_string($buffer_nickexists, weechat::nicklist_search_nick($buffer_nickexists, "", $weechat_signal_nick), "color"));
                my $event_phrase = $c_chat_join."extended$c_emph lurkage to";
                $event_phrase = $c_chat_quit."ceased$c_emph lurkage from" if $data eq 'p';
                weechat::print($buffer_nickexists, $prefix."$c_lurker_nick$weechat_signal_nick$c_emph has $event_phrase: $c_channel$weechat_signal_channel$c_chat");
            }
        }

    }

    # handle a quit event by printing all channels the joining nick is lurking
    # in
    if (($data eq 'q') && $trig_notice_enabled) {
        for my $buffer_event_name (sort grep {defined $buffernicks{$_}{$weechat_signal_nick}} keys %buffernicks) {
            # get the buffer where the event occurred
            my $buffer_event = weechat::buffer_search("irc", $buffer_event_name);

            # find channels where the subject nick is lurking in
            my @lurker_common_buffers;
            for my $buffer_name (grep {$_ ne $buffer_event_name} sort keys %buffernicks) {
                if ((defined $buffernicks{$buffer_name}{$weechat_signal_nick}) && !(defined $ignore_nicks_trig_notice{$weechat_signal_nick})) {
                    push @lurker_common_buffers, $buffer_name;
                }
            }

            # print notice in the channel where the quit occurred
            if (scalar @lurker_common_buffers) {
                my $notice_tmp = $prefix."also lurked in: ".join(", ", sort map {$c_channel.$_.$c_emph} @lurker_common_buffers)."\n";
                $notice_buffer{$buffer_event} = $notice_tmp;
                #weechat::print($buffer_event, $notice_tmp);
            }
        }
    }

    return weechat::WEECHAT_RC_OK;
}

sub init_buffernicks {
    # get args
    my $buffernicks_ref = shift;

    # what are the nicks to ignore?
    my %ignore_nicks;
    if (weechat::config_is_set_plugin($opt_ignore_nick)) {
        my $option_str = weechat::config_get_plugin($opt_ignore_nick);
        $option_str =~ s/ //g;
        $ignore_nicks{lc $_} = 1 for grep {$_ !~ m/^ *$/} split(/,/, $option_str);
    }

    # populate it with new entries
    my $list_buffer = weechat::infolist_get("buffer", "", "");
    if ($list_buffer) {
        while (weechat::infolist_next($list_buffer)) {
            # print buffer name
            my $buffer = weechat::infolist_pointer($list_buffer, "pointer");
            my $buffer_name = weechat::infolist_string($list_buffer, "name");
            my $buffer_name_channel = weechat::buffer_get_string($buffer, "localvar_channel");
            my $buffer_name_server = weechat::buffer_get_string($buffer, "localvar_server");
            my $buffer_mynick = weechat::buffer_get_string($buffer, "localvar_nick");

            # get list of nicks for the buffer at hand
            my $list_nicks = weechat::infolist_get("irc_nick", "", "$buffer_name_server,$buffer_name_channel");
            if ($list_nicks) {
                while (weechat::infolist_next($list_nicks)) {
                    my $nick_name = weechat::infolist_string($list_nicks, "name");
                    if (($nick_name ne $buffer_mynick) && !(defined $ignore_nicks{lc $nick_name})) {
                        ${$buffernicks_ref}{$buffer_name}{$nick_name} = $buffer;
                    }
                }
            }
            weechat::infolist_free($list_nicks);
        }
    }
    weechat::infolist_free($list_buffer);
}

sub print_notice {
    # get args
    my $data = shift;
    my $signal = shift;
    my $signal_data = shift;

    # process args
    my $weechat_signal_nick = weechat::info_get("irc_nick_from_host", $signal_data);
    my $weechat_signal_server;
    my $weechat_signal_channel;

    #weechat::print("", "data: $data");
    #weechat::print("", "signal: $signal");
    #weechat::print("", "signal_data: $signal_data");
    #weechat::print("", "    ".$weechat_signal_nick);

    if (($data eq 'j') || ($data eq 'p') || ($data eq 'q')) {
        $weechat_signal_server = (split(/,/, $signal))[0];
        #weechat::print("", "    server:".$weechat_signal_server);
        if (($data eq 'j') || ($data eq 'p')) {
            $weechat_signal_channel = (split(/ /, $signal_data))[2];
            #weechat::print("", "    channel:".$weechat_signal_channel);
        }
    }

    if ($data eq 'q') {
        for my $buffer_event (keys %notice_buffer) {
            weechat::print($buffer_event, $notice_buffer{$buffer_event});
        }
        %notice_buffer = ();

    } else {
        if ($notice ne '') {
            # get the buffer where the event occurred
            my $buffer_event_name = "$weechat_signal_server.$weechat_signal_channel";
            my $buffer_event = weechat::buffer_search("irc", $buffer_event_name);

            # print notice
            weechat::print($buffer_event, $notice) if ($buffer_event ne '');
            $notice = '';
        }
    }

    return weechat::WEECHAT_RC_OK;
}

# command and signal hooks
weechat::hook_command("commorkers", "Finds common lurkers across different channels", "[NICK]", "NICK: find channels that overlap with NICK (optional argument)", "", "common_lurkers","i");
weechat::hook_signal('*,irc_in_join', "common_lurkers", "j");
weechat::hook_signal('*,irc_in_part', "common_lurkers", "p");
weechat::hook_signal('*,irc_in_quit', "common_lurkers", "q");
weechat::hook_signal('*,irc_in2_join', "print_notice", "j");
weechat::hook_signal('*,irc_in2_part', "print_notice", "p");
weechat::hook_signal('*,irc_in2_quit', "print_notice", "q");
