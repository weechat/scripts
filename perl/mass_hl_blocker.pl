# Mass highlight blocker for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>
# History:
# 2020-07-02, Pascal Poitras Dubois <pascalpoitras@gmail.com>:
#	v0.3:	-add: add a tag, mass_hl, to the message
#		-change: remove leading channel membership prefixes (~&@%+)

weechat::register('mass_hl_blocker', 'arza <arza\@arza.us>', '0.3', 'GPL3', 'Block mass highlights', '', '');

my $version=weechat::info_get('version_number', '') || 0;

my $limit=5;

if(weechat::config_is_set_plugin('limit')){ $limit=weechat::config_get_plugin('limit'); }
else{ weechat::config_set_plugin('limit', $limit); }

if($version>=0x00030500){ weechat::config_set_desc_plugin('limit', 'minimum amount of nicks in line to disable highlight (default: 5)'); }

weechat::hook_config('plugins.var.perl.mass_highlight_block.limit', 'set_limit', '');
weechat::hook_modifier('2000|weechat_print', 'block', '');

sub block { my $message=$_[3];

        my $buffer = "";
        my $tags = "";
        if ($_[2] =~ /0x/)
        {
                # WeeChat >= 2.9
                $_[2] =~ m/([^;]*);(.*)/;
                $buffer = $1;
                $tags = $2;
        }
        else
        {
                # WeeChat <= 2.8
                $_[2] =~ m/([^;]*);([^;]*);(.*)/;
                $buffer = weechat::buffer_search($1, $2);
                $tags = $3;
        }
        my $plugin = weechat::buffer_get_string($buffer, "plugin");
        my $server = weechat::buffer_get_string($buffer, "localvar_server");
        my $channel = weechat::buffer_get_string($buffer, "localvar_channel");

        return $message if ($server eq "" or $channel eq "");

	index($message, weechat::info_get('irc_nick', $server)) != -1 && index($tags, 'notify_message') != -1 && index($tags, 'no_highlight') == -1 || return $message;

	my $count=0;
	foreach my $word (split(' ', $message)){
		$word =~ s/^[~&@%+]//;
		my $infolist=weechat::infolist_get('irc_nick', '', "$server,$channel,$word");
		if($infolist){ $count++; }
		weechat::infolist_free($infolist);
	}

	if($count>=$limit){
		weechat::print_date_tags(weechat::buffer_search($plugin, "$server.$channel"), 0, "$tags,no_highlight,mass_hl", $message);
		return '';
	}

	return $message;
}

sub set_limit {
	$limit=$_[2];
	return weechat::WEECHAT_RC_OK;
}
