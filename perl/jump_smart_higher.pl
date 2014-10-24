# jump_smart_higher.pl for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>

# Jump to a higher buffer with activity, similar to /input smart_jump (alt-a) but jump to a buffer with higher number if possible

# Changelog:
# 2013-10-22 0.1 initial release
# 2014-10-23 0.2 don't try to change to current buffer

weechat::register('jump_smart_higher', 'arza <arza@arza.us>', '0.2', 'GPL3', 'Jump to a higher buffer with activity', '', '');
weechat::hook_command('jump_smart_higher', 'Jump to a higher buffer with activity', '',
'Jump to the buffer that
 1. has the highest activity level
 2. is after current buffer if possible
 3. has the lowest number',
'', 'command', '');

sub command { my $buffer=$_[1];
	my $max_priority = 0;
	my $min_number = 1000000;
	my $current_number = weechat::buffer_get_integer($buffer, 'number');
	my $number = 0;
	my $priority = 0;
	my $infolist = weechat::infolist_get('hotlist', '', '');
	while(weechat::infolist_next($infolist)){
		$number = weechat::infolist_integer($infolist, 'buffer_number');
		if($number == $current_number){ next; }
		$priority = weechat::infolist_integer($infolist, 'priority');
		if($priority > $max_priority){ $max_priority = $priority; $min_number = 1000000; }
		elsif($priority < $max_priority){ next; }
		if($number < $current_number){ $number += 10000; }
		if($number < $min_number){ $min_number = $number; }
	}
	weechat::infolist_free($infolist);

	weechat::command($buffer, "/buffer " . $min_number % 10000);
}
