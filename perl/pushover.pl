#
# Copyright (C) 2013-2017  stfn <stfnmd@gmail.com>
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

my %SCRIPT = (
	name => 'pushover',
	author => 'stfn <stfnmd@gmail.com>',
	version => '2.0',
	license => 'GPL3',
	desc => 'Send push notifications to your mobile devices using Pushover',
	opt => 'plugins.var.perl',
);
my %OPTIONS_DEFAULT = (
	'enabled' => ['on', "Turn script on or off"],
	'token' => ['ajEX9RWhxs6NgeXFJxSK2jmpY54C9S', 'pushover API token/key (You may feel free to use your own token, so you get your own monthly quota of messages without being affected by other users. See also: https://pushover.net/faq#overview-distribution )'],
	'user' => ['', "pushover user key"],
	'sound' => ['', "Sound (empty for default)"],
	'priority' => ['', "priority (empty for default)"],
	'show_highlights' => ['on', 'Notify on highlights'],
	'show_priv_msg' => ['on', 'Notify on private messages'],
	'redact_priv_msg' => ['off', 'When receiving private message notifications, hide the actual message text'],
	'only_if_away' => ['off', 'Notify only if away status is active'],
	'only_if_inactive' => ['off', 'Notify only if buffer is not the active (current) buffer'],
	'blacklist' => ['', 'Comma separated list of buffers (full name) to blacklist for notifications (wildcard "*" is allowed, name beginning with "!" is excluded)'],
	'verbose' => ['1', 'Verbosity level (0 = silently ignore any errors, 1 = display brief error, 2 = display full server response)'],
	'rate_limit' => ['0', 'Rate limit in seconds (0 = unlimited), will send a maximum of 1 notification per time limit'],
	'short_name' => ['off', 'Use short buffer name in notification'],
);
my %OPTIONS = ();
my $TIMEOUT = 30 * 1000;
my $WEECHAT_VERSION;

# Enable for debugging
my $DEBUG = 0;

# Rate limit flag
my $RATE_LIMIT_OK = 1;

# Register script and initialize config
weechat::register($SCRIPT{"name"}, $SCRIPT{"author"}, $SCRIPT{"version"}, $SCRIPT{"license"}, $SCRIPT{"desc"}, "", "");
init_config();

# Setup hooks
weechat::hook_print("", "notify_message,notify_private,notify_highlight", "", 1, "print_cb", "");
weechat::hook_command($SCRIPT{"name"}, "send notification",
	"<text>",
	"text: notification text to send\n" .
	"\n" .
	"Don't forget to configure your own Pushover user and token.\n" .
	"\n" .
	"You can also setup custom notifications (for any other services etc.) by using a /trigger on the hsignal \"pushover\".\n\nExamples:\n" .
	"\n" .
	"pushover.net using curl:\n" .
	"/trigger add mynotify hsignal pushover \"\" \"\" \"/exec -bg curl -s --form-string 'token=abc123' --form-string 'user=user123' --form-string 'message=\${message_stripped}' https://api.pushover.net/1/messages.json\"\n" .
	"\n" .
	"free-mobile.fr using curl:\n" .
	"/trigger add mynotify hsignal pushover \"\" \"\" \"/exec -bg curl -s 'https://smsapi.free-mobile.fr/sendmsg?user=USER&pass=TOKEN&msg=\${message_escaped}'\"\n",
	"", "pushover_cmd_cb", "");

#
# Handle config stuff
#
sub init_config
{
	weechat::hook_config("$SCRIPT{'opt'}.$SCRIPT{'name'}.*", "config_cb", "");
	$WEECHAT_VERSION = weechat::info_get("version_number", "") || 0;
	foreach my $option (keys %OPTIONS_DEFAULT) {
		if (!weechat::config_is_set_plugin($option)) {
			weechat::config_set_plugin($option, $OPTIONS_DEFAULT{$option}[0]);
			$OPTIONS{$option} = $OPTIONS_DEFAULT{$option}[0];
		} else {
			$OPTIONS{$option} = weechat::config_get_plugin($option);
		}
		if ($WEECHAT_VERSION >= 0x00030500) {
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
# URL escape (percent encoding)
#
sub url_escape($)
{
	my $toencode = $_[0];
	return undef unless (defined($toencode));
	utf8::encode($toencode) if (utf8::is_utf8($toencode));
	$toencode =~ s/([^a-zA-Z0-9_.~-])/uc sprintf("%%%02x",ord($1))/eg;
	return $toencode;
}

#
# Evaluate expression (used for /secure support)
#
sub eval_expr($)
{
	my $value = $_[0];
	if ($WEECHAT_VERSION >= 0x00040200) {
		my $eval_expression = weechat::string_eval_expression($value, {}, {}, {});
		return $eval_expression if ($eval_expression ne "");
	}
	return $value;
}

#
# Flip rate_limit flag back to OK
#
sub rate_limit_cb
{
	$RATE_LIMIT_OK = 1;
	if ($DEBUG) {
		weechat::print("", "[$SCRIPT{name}] Rate Limit Deactivated");
	}
}

#
# Catch printed messages
#
sub print_cb
{
	my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message) = @_;

	my $buffer_type = weechat::buffer_get_string($buffer, "localvar_type");
	my $buffer_full_name = "";
	# check for long or short name
	if ($OPTIONS{short_name} eq 'on') {
		$buffer_full_name = weechat::buffer_get_string($buffer, "short_name");
	} else {
		$buffer_full_name = weechat::buffer_get_string($buffer, "full_name");
	}
	my $away_msg = weechat::buffer_get_string($buffer, "localvar_away");
	my $away = ($away_msg && length($away_msg) > 0) ? 1 : 0;

	if ($OPTIONS{enabled} ne "on" ||
	    $displayed == 0 ||
	    ($OPTIONS{only_if_away} eq "on" && $away == 0) ||
	    ($OPTIONS{only_if_inactive} eq "on" && $buffer eq weechat::current_buffer()) ||
	    weechat::buffer_match_list($buffer, $OPTIONS{blacklist})) {
		return weechat::WEECHAT_RC_OK;
	}

	if ($RATE_LIMIT_OK == 0) {
		if ($DEBUG) {
			weechat::print("", "[$SCRIPT{name}] No Notification - Rate Limited.");
		}
		return weechat::WEECHAT_RC_OK;
	}

	my $msg = "[$buffer_full_name] <$prefix> ";

	if ($buffer_type eq "private" && $OPTIONS{redact_priv_msg} eq "on") {
		$msg .= "...";
	} else {
		$msg .= "$message";
	}

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
# /pushover
#
sub pushover_cmd_cb
{
	my ($data, $buffer, $args) = @_;

	if (length($args) > 0) {
		notify($args);
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

	# Check if server response reported success
	if ($command =~ /pushover/ && $return_code == 0 && $out =~ /\"status\":1/) {
		return weechat::WEECHAT_RC_OK;
	}

	# Otherwise display error message
	weechat::print("", $msg);

	return weechat::WEECHAT_RC_OK;
}

#
# Notify wrapper
#
sub notify($)
{
	my $message = $_[0];

	# Start timer
	if ($OPTIONS{rate_limit}) {
		my $timer = $OPTIONS{rate_limit} * 1000;

		if ($DEBUG) {
			weechat::print("", "[$SCRIPT{name}] Rate Limit Activated. Timer: $timer");
		}

		$RATE_LIMIT_OK = 0;
		weechat::hook_timer($timer, 0, 1, "rate_limit_cb", "");
	}

	# Notify service
	if ($OPTIONS{token} ne "" && $OPTIONS{user} ne "") {
		notify_pushover(eval_expr($OPTIONS{token}), eval_expr($OPTIONS{user}), $message, "weechat", $OPTIONS{priority}, $OPTIONS{sound});
	}

	# Send hsignal (so triggers can pick up on it)
	notify_hsignal($message);
}

#
# https://pushover.net/api
#
sub notify_pushover($$$$$$)
{
	my ($token, $user, $message, $title, $priority, $sound) = @_;

	# Required API arguments
	my @post = (
		"token=" . url_escape($token),
		"user=" . url_escape($user),
		"message=" . url_escape($message),
	);

	# Optional API arguments
	push(@post, "title=" . url_escape($title)) if ($title && length($title) > 0);
	push(@post, "priority=" . url_escape($priority)) if ($priority && length($priority) > 0);
	push(@post, "sound=" . url_escape($sound)) if ($sound && length($sound) > 0);

	# Send HTTP POST
	my $hash = { "post"  => 1, "postfields" => join("&", @post) };
	if ($DEBUG) {
		weechat::print("", "[$SCRIPT{name}] Debug: msg -> `$message' HTTP POST -> @post");
	} else {
		weechat::hook_process_hashtable("url:https://api.pushover.net/1/messages.json", $hash, $TIMEOUT, "url_cb", "");
	}

	return weechat::WEECHAT_RC_OK;
}

#
# hsignal to use with /trigger
#
sub notify_hsignal($)
{
	my $message = $_[0];
	my $message_escaped = url_escape($message);
	my $message_stripped = $message;
	$message_stripped =~ s/'//gi; # strip apostrophe

	weechat::hook_hsignal_send($SCRIPT{name}, { "message" => $message, "message_escaped" => $message_escaped, "message_stripped" => $message_stripped });
}
