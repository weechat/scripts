#
# Copyright (C) 2013-2014  stfn <stfnmd@gmail.com>
# https://github.com/stfnm/weechat-scripts
#
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

use strict;
use warnings;
use CGI;

my %SCRIPT = (
	name => 'pushover',
	author => 'stfn <stfnmd@gmail.com>',
	version => '0.5',
	license => 'GPL3',
	desc => 'Send push notifications to your mobile devices using Pushover or NMA',
	opt => 'plugins.var.perl',
);
my %OPTIONS_DEFAULT = (
	'enabled' => ['on', "Turn script on or off"],
	'service' => ['pushover', 'Notification service to use (supported services: pushover, nma)'],
	'token' => ['ajEX9RWhxs6NgeXFJxSK2jmpY54C9S', 'pushover API token/key'],
	'user' => ['', "pushover user key"],
	'nma_apikey' => ['', "nma API key"],
	'sound' => ['', "Sound (empty for default)"],
	'priority' => ['', "priority (empty for default)"],
	'show_highlights' => ['on', 'Notify on highlights'],
	'show_priv_msg' => ['on', 'Notify on private messages'],
	'only_if_away' => ['off', 'Notify only if away status is active'],
	'blacklist' => ['', 'Comma separated list of buffers to blacklist for notifications'],
);
my %OPTIONS = ();
my $DEBUG = 0;
my $TIMEOUT = 30 * 1000;

# Register script and setup hooks
weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
weechat::hook_print("", "", "", 1, "print_cb", "");
init_config();

#
# Handle config stuff
#
sub init_config
{
	weechat::hook_config("$SCRIPT{'opt'}.$SCRIPT{'name'}.*", "config_cb", "");
	my $version = weechat::info_get("version_number", "") || 0;
	foreach my $option (keys %OPTIONS_DEFAULT) {
		if (!weechat::config_is_set_plugin($option)) {
			weechat::config_set_plugin($option, $OPTIONS_DEFAULT{$option}[0]);
			$OPTIONS{$option} = $OPTIONS_DEFAULT{$option}[0];
		} else {
			$OPTIONS{$option} = weechat::config_get_plugin($option);
		}
		if ($version >= 0x00030500) {
			weechat::config_set_desc_plugin($option, $OPTIONS_DEFAULT{$option}[1]." (default: \"".$OPTIONS_DEFAULT{$option}[0]."\")");
		}
	}
}
sub config_cb
{
	my ($pointer, $name, $value) = @_;
	$name = substr($name, length("$SCRIPT{opt}.$SCRIPT{name}."), length($name));
	$OPTIONS{$name} = $value;
	return weechat::WEECHAT_RC_OK;
}

#
# Case insensitive search for array element
#
sub grep_array($$)
{
	my ($str, $array_ref) = @_;
	my @array = @{$array_ref};
	return (grep {$_ =~ /^\Q$str\E$/i} @array) ? 1 : 0;
}

#
# Catch printed messages
#
sub print_cb
{
	my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message) = @_;

	my $buffer_plugin_name = weechat::buffer_get_string($buffer, "localvar_plugin");
	my $buffer_type = weechat::buffer_get_string($buffer, "localvar_type");
	my $buffer_name = weechat::buffer_get_string($buffer, "name");
	my $buffer_short_name = weechat::buffer_get_string($buffer, "short_name");
	my $away_msg = weechat::buffer_get_string($buffer, "localvar_away");
	my $away = ($away_msg && length($away_msg) > 0) ? 1 : 0;
	my @blacklist = split(/,/, $OPTIONS{blacklist});

	if ($OPTIONS{enabled} ne "on" ||
	    $displayed == 0 ||
	    ($OPTIONS{only_if_away} eq "on" && $away == 0) ||
	    (grep_array($buffer_name, \@blacklist) || grep_array($buffer_short_name, \@blacklist))) {
		return weechat::WEECHAT_RC_OK;
	}

	my $msg = "[$buffer_plugin_name] [$buffer_name] <$prefix> $message";

	# Notify!
	if ($OPTIONS{show_highlights} eq "on" && $highlight == 1) {
		# Message with highlight
		notify($msg);
	} elsif ($OPTIONS{show_priv_msg} eq "on" && $buffer_type eq "private") {
		# Private message
		notify($msg);
	}

	return weechat::WEECHAT_RC_OK;
}

#
# Catch API responses
#
sub url_cb
{
	my ($data, $command, $return_code, $out, $err) = @_;
	my $msg = "[$SCRIPT{name}] Error: @_";

	if ($OPTIONS{service} eq "pushover" && $return_code == 0 && !($out =~ /\"status\":1/)) {
		weechat::print("", $msg);
	} elsif ($OPTIONS{service} eq "nma" && $return_code == 0 && !($out =~ /success code=\"200\"/)) {
		weechat::print("", $msg);
	}

	return weechat::WEECHAT_RC_OK;
}

#
# Notify wrapper (decides which service to use)
#
sub notify($)
{
	my $message = $_[0];

	# Notify service
	if ($OPTIONS{service} eq "pushover") {
		notify_pushover($OPTIONS{token}, $OPTIONS{user}, $message, "weechat", $OPTIONS{priority}, $OPTIONS{sound});
	} elsif ($OPTIONS{service} eq "nma") {
		notify_nma($OPTIONS{nma_apikey}, "weechat", "notification", $message, $OPTIONS{priority});
	}
}

#
# https://pushover.net/api
#
sub notify_pushover($$$$$$)
{
	my ($token, $user, $message, $title, $priority, $sound) = @_;

	# Required API arguments
	my @post = (
		"token=" . CGI::escape($token),
		"user=" . CGI::escape($user),
		"message=" . CGI::escape($message),
	);

	# Optional API arguments
	push(@post, "title=" . CGI::escape($title)) if ($title && length($title) > 0);
	push(@post, "priority=" . CGI::escape($priority)) if ($priority && length($priority) > 0);
	push(@post, "sound=" . CGI::escape($sound)) if ($sound && length($sound) > 0);

	# Send HTTP POST
	my $hash = { "post"  => 1, "postfields" => join(";", @post) };
	if ($DEBUG) {
		weechat::print("", "[$SCRIPT{name}] Debug: msg -> `$message' HTTP POST -> @post");
	} else {
		weechat::hook_process_hashtable("url:https://api.pushover.net/1/messages.json", $hash, $TIMEOUT, "url_cb", "");
	}

	return weechat::WEECHAT_RC_OK;
}

#
# https://www.notifymyandroid.com/api.jsp
#
sub notify_nma($$$$$)
{
	my ($apikey, $application, $event, $description, $priority) = @_;

	# Required API arguments
	my @post = (
		"apikey=" . CGI::escape($apikey),
		"application=" . CGI::escape($application),
		"event=" . CGI::escape($event),
		"description=" . CGI::escape($description),
	);

	# Optional API arguments
	push(@post, "priority=" . CGI::escape($priority)) if ($priority && length($priority) > 0);

	# Send HTTP POST
	my $hash = { "post"  => 1, "postfields" => join("&", @post) };
	if ($DEBUG) {
		weechat::print("", "[$SCRIPT{name}] Debug: msg -> `$description' HTTP POST -> @post");
	} else {
		weechat::hook_process_hashtable("url:https://www.notifymyandroid.com/publicapi/notify", $hash, $TIMEOUT, "url_cb", "");
	}

	return weechat::WEECHAT_RC_OK;
}
