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
	version => '0.8',
	license => 'GPL3',
	desc => 'Send push notifications to your mobile devices using Pushover, NMA or Pushbullet',
	opt => 'plugins.var.perl',
);
my %OPTIONS_DEFAULT = (
	'enabled' => ['on', "Turn script on or off"],
	'service' => ['pushover', 'Notification service to use. Multiple services may be supplied as comma separated list. (supported services: pushover, nma, pushbullet)'],
	'token' => ['ajEX9RWhxs6NgeXFJxSK2jmpY54C9S', 'pushover API token/key (You may feel free to use your own token, so you get your own monthly quota of messages without being affected by other users. See also: https://pushover.net/faq#overview-distribution )'],
	'user' => ['', "pushover user key"],
	'nma_apikey' => ['', "nma API key"],
	'pb_apikey' => ['', "Pushbullet API key"],
	'pb_device_iden' => ['', "Device Iden of pushbullet device"],
	'sound' => ['', "Sound (empty for default)"],
	'priority' => ['', "priority (empty for default)"],
	'show_highlights' => ['on', 'Notify on highlights'],
	'show_priv_msg' => ['on', 'Notify on private messages'],
	'only_if_away' => ['off', 'Notify only if away status is active'],
	'only_if_inactive' => ['off', 'Notify only if buffer is not the active (current) buffer'],
	'blacklist' => ['', 'Comma separated list of buffers (full name or short name) to blacklist for notifications'],
	'verbose' => ['2', 'Verbosity level (0 = silently ignore any errors, 1 = display brief error, 2 = display full server response)'],
);
my %OPTIONS = ();
my $DEBUG = 0;
my $TIMEOUT = 30 * 1000;

# Register script and setup hooks
weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
weechat::hook_print("", "notify_message,notify_private,notify_highlight", "", 1, "print_cb", "");
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
# Case insensitive search for element in comma separated list
#
sub grep_list($$)
{
	my ($str, $list) = @_;
	my @array = split(/,/, $list);
	return grep(/^\Q$str\E$/i, @array) ? 1 : 0;
}

#
# Catch printed messages
#
sub print_cb
{
	my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message) = @_;

	my $buffer_type = weechat::buffer_get_string($buffer, "localvar_type");
	my $buffer_short_name = weechat::buffer_get_string($buffer, "short_name");
	my $buffer_full_name = weechat::buffer_get_string($buffer, "full_name");
	my $away_msg = weechat::buffer_get_string($buffer, "localvar_away");
	my $away = ($away_msg && length($away_msg) > 0) ? 1 : 0;

	if ($OPTIONS{enabled} ne "on" ||
	    $displayed == 0 ||
	    ($OPTIONS{only_if_away} eq "on" && $away == 0) ||
	    ($OPTIONS{only_if_inactive} eq "on" && $buffer eq weechat::current_buffer()) ||
	    (grep_list($buffer_full_name, $OPTIONS{blacklist}) || grep_list($buffer_short_name, $OPTIONS{blacklist}))) {
		return weechat::WEECHAT_RC_OK;
	}

	my $msg = "[$buffer_full_name] <$prefix> $message";

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
	my $msg = "[$SCRIPT{name}] Error: ";

	# Check verbosity level
	if ($OPTIONS{verbose} == 0) {
		return weechat::WEECHAT_RC_OK; # Don't display anything
	} elsif ($OPTIONS{verbose} == 1) {
		$msg .= "API call failed. (Most likely the service is having trouble.)";

	} elsif ($OPTIONS{verbose} == 2) {
		$msg .= "@_";
	}

	# Check server response and display error message if NOT successful
	if ($command =~ /pushover/ && $return_code == 0 && !($out =~ /\"status\":1/)) {
		weechat::print("", $msg);
	} elsif ($command =~ /notifymyandroid/ && $return_code == 0 && !($out =~ /success code=\"200\"/)) {
		weechat::print("", $msg);
	} elsif ($command =~ /pushbullet/ && $return_code == 0 && !($out =~ /notification_id/)) {
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

	# Notify services
	if (grep_list("pushover", $OPTIONS{service})) {
		notify_pushover($OPTIONS{token}, $OPTIONS{user}, $message, "weechat", $OPTIONS{priority}, $OPTIONS{sound});
	}
	if (grep_list("nma", $OPTIONS{service})) {
		notify_nma($OPTIONS{nma_apikey}, "weechat", "$SCRIPT{name}.pl", $message, $OPTIONS{priority});
	}
	if (grep_list("pushbullet", $OPTIONS{service})) {
		notify_pushbullet($OPTIONS{pb_apikey}, $OPTIONS{pb_device_iden}, "weechat", $message);
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

#
# https://www.pushbullet.com/api
#
sub notify_pushbullet($$$$)
{
	my ($apikey, $device_iden, $title, $body) = @_;

	# Required API arguments
	my $apiurl = "https://$apikey:\@api.pushbullet.com/api/pushes";
	my @post = (
		"device_iden=" . CGI::escape($device_iden),
		"type=note",
	);

	# Optional API arguments
	push(@post, "title=" . CGI::escape($title)) if ($title && length($title) > 0);
	push(@post, "body=" . CGI::escape($body)) if ($body && length($body) > 0);

	# Send HTTP POST
	my $hash = { "post"  => 1, "postfields" => join("&", @post) };
	if ($DEBUG) {
		weechat::print("", "$apiurl [$SCRIPT{name}] Debug: msg -> `$body' HTTP POST -> @post");
	} else {
		weechat::hook_process_hashtable("url:$apiurl", $hash, $TIMEOUT, "url_cb", "");
	}

	return weechat::WEECHAT_RC_OK;
}
