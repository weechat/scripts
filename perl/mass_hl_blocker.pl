# Mass highlight blocker for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>

weechat::register('mass_hl_blocker', 'arza <arza\@arza.us>', '0.1', 'GPL3', 'Block mass highlights', '', '');

my $version=weechat::info_get('version_number', '') || 0;

my $limit=5;

if(weechat::config_is_set_plugin('limit')){ $limit=weechat::config_get_plugin('limit'); }
else{ weechat::config_set_plugin('limit', $limit); }

if($version>=0x00030500){ weechat::config_set_desc_plugin('limit', 'minimum amount of nicks in line to disable highlight (default: 5)'); }

weechat::hook_config('plugins.var.perl.mass_highlight_block.limit', 'set_limit', '');
weechat::hook_modifier('2000|weechat_print', 'block', '');

sub block { my $message=$_[3];

	$_[2]=~/(\S+);(\S+)\.(\S+);(\S+)/ || return $message;
	my ($plugin, $server, $channel, $tags) = ($1, $2, $3, $4);
	index($message, weechat::info_get('irc_nick', $server)) != -1 && index($tags, 'notify_message') != -1 && index($tags, 'no_highlight') == -1 || return $message;

	my $count=0;
	foreach my $word (split(' ', $message)){
		my $infolist=weechat::infolist_get('irc_nick', '', "$server,$channel,$word");
		if($infolist){ $count++; }
		weechat::infolist_free($infolist);
	}

	if($count>=$limit){
		weechat::print_date_tags(weechat::buffer_search($plugin, "$server.$channel"), 0, "$tags,no_highlight", $message);
		return '';
	}

	return $message;
}

sub set_limit {
	$limit=$_[2];
	return weechat::WEECHAT_RC_OK;
}
