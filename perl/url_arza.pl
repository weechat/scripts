# Url shortener for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>

# Why yet another url shortener script?
# - use your own shortener in a web server, for example: http://weechat.arza.us/url_arza.php
# - a key to shorten url in input line: bind to /url_arza
# - toggle short urls under long urls, not logged: /filter add url_arza * no_log ^^http://  ;  /filter toggle url_arza
# - no dependencies
# - simple

# Requires WeeChat >=0.3.6

weechat::register('url_arza', 'arza <arza@arza.us>', '0.1', 'GPL3', 'Shorten long urls in buffers and input line', '', '');
weechat::hook_print('', 'notify_message', '://', 0, 'url_in', '');
weechat::hook_command('url_arza', 'Shorten url in input line', '', '', '', 'command', '');
weechat::hook_config('plugins.var.perl.url_arza.*', 'set', '');

my %settings;

for(
	[ 'url', 'http://arza.us/s/?password=&url=', 'url for shortener, url to shorten is appended, the shortener should return the short url' ],
	[ 'url_append_command', '&id_min_length=1', 'string to append to the url when shortening in input line' ],
	[ 'url_append_incoming', '&id_min_length=2', 'string to append to the url when shortening incoming urls' ],
	[ 'min_length', 100, 'minimum length for incoming urls to shorten, after http://' ],
){ my ($name, $value, $description) = @$_;
	if(weechat::config_is_set_plugin($name)){
		$settings{$name}=weechat::config_get_plugin($name);
	}else{
		weechat::config_set_plugin($name, $value);
		weechat::config_set_desc_plugin($name, "$description (default: $value)");
	}
}

my $timeout=2000;
my $delimiter="^\t";


sub escape { my $url=$_[0];
	$url=~s/([^a-zA-Z0-9_.~-])/sprintf('%%%02x',ord($1))/eg;
	return $url;
}


sub command { my $buffer=$_[1];
	my $input=weechat::buffer_get_string($buffer, 'input');
	( my ($long) = $input=~/(https?:\/\/\S+)$/ ) || return weechat::WEECHAT_RC_OK;
	weechat::hook_process("url:$settings{url}".escape($long).$settings{'url_append_command'}, $timeout, 'command_fetch', "$buffer $long $input");
	return weechat::WEECHAT_RC_OK;
}

sub command_fetch { $_[2] && return weechat::WEECHAT_RC_ERROR;
	my ($buffer, $long, $input) = split(/ /, $_[0], 3);
	my $short=$_[3];
	my $input_pos=weechat::buffer_get_integer($buffer, 'input_pos') + length($short) - length($long);
	$input=~s/\Q$long\E$/$short/;
	weechat::buffer_set($buffer, 'input', $input);
	weechat::buffer_set($buffer, 'input_pos', $input_pos);
	return weechat::WEECHAT_RC_OK;
}


sub url_in { my ($buffer, $displayed, $prefix, $line) = ($_[1], $_[4], $_[6], $_[7]);
	$displayed && ( my ($long) = $line=~/(https?:\/\/\S{$settings{'min_length'},})/ ) || return weechat::WEECHAT_RC_OK;
	weechat::hook_process("url:$settings{url}".escape($long).$settings{'url_append_incoming'}, $timeout, 'url_in_fetch', "$buffer $prefix");
	return weechat::WEECHAT_RC_OK;
}

sub url_in_fetch { $_[2] && return weechat::WEECHAT_RC_ERROR;
	my ($buffer, $prefix) = split(/ /, $_[0], 2);
	my $short=$_[3];
	weechat::print_date_tags($buffer, 0, 'no_log', ' ' x length(weechat::string_remove_color($prefix, '')) . $delimiter . $short);
	return weechat::WEECHAT_RC_OK;
}


sub set {
	$settings{substr($_[1], length('plugins.var.perl.url_arza.'))}=$_[2];
	return weechat::WEECHAT_RC_OK;
}

