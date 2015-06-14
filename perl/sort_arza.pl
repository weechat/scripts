# Channel sorter for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>

# Sorts channels inside networks, with a command.
#
# I have:
# - server buffers merged in buffer 1
# - a special order of networks
#
# I want:
# - a command to sort channels inside every network, preserving the order of networks
# - ##-channels sorted like #-channels
# - queries and script buffers in the end

weechat::register('sort_arza', 'arza <arza@arza.us>', '1', 'GPL3', 'Sort channels inside networks.', '', '');
weechat::hook_command('sort_arza', 'Sort channels inside networks', '[-test]', '-test: dry run', '-test', 'command', '');

sub command { my $arg = $_[2];
	my @servers;
	my %old; # %old -> $server -> $channel -> $buffer_pointer

	my $infolist = weechat::infolist_get('buffer', '', '');
	while(weechat::infolist_next($infolist)){ # loop buffers
		my $buffer_pointer = weechat::infolist_pointer($infolist, 'pointer');
		if(weechat::buffer_get_string($buffer_pointer, 'localvar_type') ne 'channel' || weechat::infolist_integer($infolist, 'active') eq 0){ next; } # skip non-channel and non-active (in merged buffers)
		my $server_name = weechat::buffer_get_string($buffer_pointer, 'localvar_server');
		my $buffer_short_name = weechat::infolist_string($infolist, 'short_name');

		push(@servers, $server_name) unless grep { $_ eq $server_name } @servers; # push the server to the list if it isn't there already
		$buffer_short_name =~ s/^[#&+]+|^![A-Z0-9]{5}/#/; # make all channel prefixes '#'
		$old{$server_name}{$buffer_short_name} = $buffer_pointer;
	}
	weechat::infolist_free($infolist);

	my $new_number=2;
	for my $server (@servers){ # sort and move
		for my $channel (sort { lc $a cmp lc $b } keys %{$old{$server}}){
			if($arg){ weechat::print('', sprintf("%2d", $new_number).": $server.$channel (".weechat::buffer_get_integer($old{$server}{$channel}, 'number').")"); } # dry run
			else{ weechat::buffer_set($old{$server}{$channel}, 'number', $new_number); } # move the buffer
			$new_number++;
		}
	}

	return weechat::WEECHAT_RC_OK;
}
