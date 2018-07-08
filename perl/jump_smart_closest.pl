# jump_smart_closest.pl for WeeChat by arza <arza@arza.us>, distributed freely and without any warranty, licensed under GPL3 <http://www.gnu.org/licenses/gpl.html>

# Jump to the numerically closest buffer with the highest activity, similar to /input jump_smart (alt-a) but jump to the buffer that has the highest activity level and is next/previous buffer by number regardless of weechat.look.hotlist_sort

# Changelog:
# 2013-10-22 0.1 initial release
# 2014-10-23 0.2 don't try to change to current buffer
# 2018-07-07 0.3 reverse direction jumping, new commands /jump_smart_previous and /jump_smart_next, renamed from jump_smart_higher.pl to jump_smart_closest.pl

weechat::register('jump_smart_closest', 'arza <arza@arza.us>', '0.3', 'GPL3', 'Jump to next/previous buffer with highest activity', '', '');

weechat::hook_command('jump_smart_higher', 'See jump_smart_next and jump_smart_previous', '', '', '', 'command_next', ''); # compatibility

weechat::hook_command('jump_smart_previous', 'Jump to previous buffer with highest activity', '',
'Jump to the buffer that
 1. has the highest activity level
 2. is before current buffer if possible
 3. has the highest number',
'', 'command_previous', '');

weechat::hook_command('jump_smart_next', 'Jump to next buffer with activity', '',
'Jump to the buffer that
 1. has the highest activity level
 2. is after current buffer if possible
 3. has the lowest number',
'', 'command_next', '');


sub command_previous { my $buffer=$_[1];
	my $max_priority = 0;
	my $max_number = -1000000;
	my $current_number = weechat::buffer_get_integer($buffer, 'number');
	my $number = 0;
	my $priority = 0;
	my $infolist = weechat::infolist_get('hotlist', '', '');
	while(weechat::infolist_next($infolist)){
		$number = weechat::infolist_integer($infolist, 'buffer_number');
		if($number == $current_number){ next; }
		$priority = weechat::infolist_integer($infolist, 'priority');
		if($priority > $max_priority){ $max_priority = $priority; $max_number = -1000000; }
		elsif($priority < $max_priority){ next; }
		if($number > $current_number){ $number -= 10000; }
		if($number > $max_number){ $max_number = $number; }
	}
	weechat::infolist_free($infolist);

	weechat::command($buffer, "/buffer " . $max_number % 10000);
}

sub command_next { my $buffer=$_[1];
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
