#
# Copyright (c) 2016-2019 Mitescu George Dan <mitescugd@gmail.com>
# Copyright (c) 2019 Silvan Mosberger <infinisil@icloud.com>
# Copyright (c) 2016 Berechet Mihai <mihaibereket9954@gmail.com>
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

my $SCRIPT_NAME = "notifym";
my $VERSION = "1.2";

# use Data::Dumper;

weechat::register($SCRIPT_NAME, "dmitescu", $VERSION, "GPL3", 
		  "Script which uses libnotify to alert the user about certain events.",
		  "", "");

my %options_def = ( 'notify_pv'         => ['on',
					    'Notify on private message.'],
		    'notify_mentions'    => ['on',
					    'Notify on mention in all channel.'],
		    'notify_channels'   => ['off',
					    'Notify all messages from whitelisted channels.'],
		    'notify_servers'    => ['off',
					    'Notify all messages from whitelisted servers.'],
		    'channel_whitelist' => ['.*',
					    'Channel white-list. (perl regex required)'],
		    'server_whitelist'  => ['.*',
					    'Server white-list. (perl regex required)']
    );

my %options = ();

# Initiates options if non-existent and loads them
sub init {
    foreach my $opt (keys %options_def) {
	if (!weechat::config_is_set_plugin($opt)) {
	    weechat::config_set_plugin($opt, $options_def{$opt}[0]);
	}
	$options{$opt} = weechat::config_get_plugin($opt);
	weechat::config_set_desc_plugin($opt, $options_def{$opt}[1]
					. " (default: \"" . $options_def{$opt}[0]
					. "\")");
    }
}

# On update option, load it into the hash
sub update_config_handler {
    my ($data, $option, $value) = @_;
    $name = substr($option, 
		   length("plugins.var.perl.".$SCRIPT_NAME."."), 
		   length($option));
    $options{$name} = $value;
    # weechat::print("", $name . " is now " . $value . "!");
    return weechat::WEECHAT_RC_OK;
}

# Function to send notification
sub send_notification {
    my ($urgency, $summary, $body) = @_;
    my $retval = system("notify-send", "-u", $urgency, $summary, $body);
}

# Verify matching options
sub opt_match {
	my ($str, $option) = @_;
	return $str =~ /$options{$option}/;
}

# Handlers for signals :
# Private message

sub message_handler {
    my ($data, $signal, $signal_data) = @_;
    # my @pta = split(":", $signal_data);
    # weechat::print("", Dumper(\%options));
    my ($server, $command) = $signal =~ /(.*),irc_in_(.*)/;
    if ($command eq 'PRIVMSG') {
	my $hash_in = {"message" => $signal_data};
	my $hash_data = weechat::info_get_hashtable("irc_message_parse", $hash_in);

	my $nick = $hash_data->{"nick"};
	my $text = $hash_data->{"text"};
	my $chan = $hash_data->{"channel"};
	
	if (($options{'notify_servers'} eq 'on') && 
	    opt_match($server, 'server_whitelist')) {
	    # Server match
	    send_notification("normal", "$nick:", "$text");
	} elsif (($options{'notify_channels'} eq 'on') &&
		 opt_match($chan, 'channel_whitelist')){
	    # Channel match
	    send_notification("normal", "$nick:", "$text");
	} elsif ($options{'notify_pv'} eq 'on') {
	    # Private message match
	    my $mynick = weechat::info_get("irc_nick", $server);
	    if ($chan eq $mynick) {
		send_notification("critical", "$nick says:", "$text");
	    }
	} else {
	}
	
	# Mention match
	my $mynick = weechat::info_get("irc_nick", $server);
	if (index($text, $mynick) != -1) {
	    send_notification("critical", "$nick mentioned you!", "");
	}	
	# weechat::print("", Dumper($hash_data));
    }
    return weechat::WEECHAT_RC_OK;
}

# Main execution point

init();
send_notification("critical",
		  "Starting NotifyM plugin, version " . $VERSION . "!",
		  "");
weechat::hook_config("plugins.var.perl." . $SCRIPT_NAME . ".*",
		     "update_config_handler", "");
weechat::hook_signal("*,irc_in_*", "message_handler", "");
