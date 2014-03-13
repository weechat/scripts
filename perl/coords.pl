use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;

# coords.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

# to read the following docs, you can use "perldoc coords.pl"

=head1 NAME

coords - weechat script to map screen coordinates (weechat edition)

=head1 SYNOPSIS

first, copy the file to your
F<.weechat/perl> directory. Then you can type

  /script load coords.pl

in weechat to load the script. Use

  /coords

to open the coords screen, or conveniently

  /key bind meta-/ /coords /

to open it with the Alt+/ keybinding.

=head1 DESCRIPTION

coords will hilight links, allow text selection and tries to send the
selection to xterm

=head1 SETUP

if you would like urls to be copied into the selection clipboard, add

  xterm*disallowedWindowOps:20,21,SetXprop

to your F<.Xresources> file for B<xterm>.

For B<rxvt-unicode>, get the F<osc-xterm-clipboard> script from
L<http://anti.teamidiot.de/static/nei/*/Code/urxvt/>, install it to
your F<perl-lib> directory and add it to your F<.Xresources> like such:

  URxvt.perl-ext-common: default,osc-xterm-clipboard

=head1 USAGE

to open the url overlay on a window, type C</coords> or use the
keybinding you created as explained in the L</SYNOPSIS>.

=head2 Selection Mode

by default, the copy window will be in selection mode. you can move
the text cursor with the arrow keys and open a selection with the
Space key. The selection content will be transfered into clipboard.

=head2 URL Mode

to switch between selection mode and URL mode, use the C</> key or
type the command C</coords /> to directly start in URL mode.

inside the overlay, you can use Arrow-Up and Arrow-Down keys to select
URLs. This script will try to copy them into your selection clipboard
(see L</SETUP>) so you should be able to open the selected link by
clicking the middle mouse button in your browser.

once you click or hit enter, an url open signal will be sent to
WeeChat. Use an appropriate script such as F<urlopener.pl> from
L<http://anti.teamidiot.de/static/nei/*/Code/WeeChat/> if you would
like to associate this with some application (web browser etc.)

to leave the overlay, hit the C<q> key.

for mouse support, this script will listen to mouse input
signals. Another script is needed to supply these signals, such as
F<mouse.pl> which can be found in the same place as F<urlopener.pl>
and this script.

=head1 CAVEATS

=over

=item *

WeeChat does not allow for visual feedback during mouse operation
unless you patch it and use the F<mouse.pl> or F<mouse_var.pl> script
instead.

=item *

double-click word select does not work in an unpatched WeeChat for the
same reason -- unless you set a very high close_on_release timeout (with
the added inconvenience).

=item *

unfortunately, WeeChat scrolls back a buffer to the end when you
switch to any other buffer, including the copy window
overlay. F<coords.pl> will work together with the F<keepscroll.pl>
script to try and remedy this a little bit, but the perfect scrolling
position cannot be restored due to internal limitations. (no longer
the case in recent versions of WeeChat.)

=item *

whether other terminal emulators support selection storage, depends on
how well they emulate B<xterm>. Set C<xterm_compatible> to your
I<$TERM> if you think it does.

=item *

B<xterm> will not allow selection storage unless you enable it in the
Xresources as described in L</SETUP>

=item *

B<rxvt-unicode> will need a script to handle the selection operating
system control. querying the selection is only supported if the
selection is rxvt-unicodeE<apos>s (not needed for this script)

=item *

GNU B<screen> will not allow to pass through the operating system
control needed for selection storage to the underlying term, try
B<tmux> instead (L<http://tmux.sourceforge.net/>)

=item *

it would be possible to provide a remote clipboard, but that will
require a clipboard server. Also see B<xsel>, B<xclip>, command mode

=back

=head1 TODO

=over

=item *

set the text input cursor on click in the input bar

=back

=head1 BUGS

=over

=item *

my local B<xterm> exhibits a bug where the selection is only copied if
you I<click> into the xterm window first. still trying to figure this
one out...

=item *

missing handling of scroll_beyond_end feature in weechat

=item *

broken handling of Day Changed messages in newer weechat

=item *

possibly more...

=back

=head1 SETTINGS

the settings are usually found in the

  plugins.var.perl.coords

namespace, that is, type

  /set plugins.var.perl.coords.*

to see them and

  /set plugins.var.perl.coords.SETTINGNAME VALUE

to change a setting C<SETTINGNAME> to a new value C<VALUE>. Finally,

  /unset plugins.var.perl.coords.SETTINGNAME

will reset a setting to its default value.

the following settings are available:

=head2 url_regex

a regular expression to identify URLs in the text. See L<perlre> for
more information about Perl regular expressions.

=head2 url_braces

parenthesis-like characters which nest and should be excluded when
found around an URL. make sure the variable setting nests properly
when modifying this.

=head2 url_non_endings

this is matched against the end of a link and removed

=head2 hyper_nicks

make nicks to hyperlinks for menu/pm

=head2 hyper_channels

make channels to hyperlinks for join

=head2 hyper_show

set to types of hyperlinks that are shown by default

=head2 use_nick_menu

use nick menu when opening nick hyperlink (see I<hyper_nicks>,
requires menu.pl script). otherwise open private message. this setting
only applies to text mode selection, for mouse see
I<mouse.nick_2nd_click>

=head2 color.url_highlight

the weechat color and/or attribute to be used for highlighting URLs in
the copy window. seperate multiple attributes with C<.>

=head2 color.url_highlight_active

the same as I<color.url_highlight> except for the currently (using
arrow keys) selected link.

=head2 color.selection_cursor

the weechat color and/or attribute to be used for the text cursor.

=head2 color.selection

the color of the currently selected text in selection mode

=head2 copybuf_short_name

short_name to use for coords buffer. it is set to the copy sign by
default to not disturb buffers bar width, set to the empty string to
have window position and size shown

=head2 mouse.copy_on_click

set to on if it should be possible to directly click on URLs and
select text, set to off if mouse should only work in open coords
buffer

=head2 mouse.close_on_release

set to on or a delay (in ms) to autoclose coords buffer opened by
I<copy_on_click> on button release, set to off if the coords buffer
should stay open after click

=head2 mouse.click_select_pane

set to on to use the mouse to select windows

=head2 mouse.click_through_pane

set to on if I<copy_on_click> should work on inactive windows (works
only if I<click_select_pane> is set too). set to off if window needs
to be active

=head2 mouse.url_open_2nd_click

if this is set, URLs are only opened when clicked twice (in the same
incarnation of a coords buffer) instead of on first click. it can be set to
a delay (in ms) that will be added to the I<close_on_release> delay if
the script is waiting for a second click on the URL to happen

=head2 mouse.handle_scroll

set to on if coords should handle scrolling inside windows. the script
will try to guess non-chat areas to be nicklist, top to be title and
bottom to be status and scroll the respective bars if the cursor is in
that area. set to off if scrolling should be handled by the default
F<mouse.pl> script or another mouse scrolling script

=head2 mouse.scroll_inactive_pane

set to on if inactive windows should be scrolled instead of active
window if the mouse cursor is over it (requires I<handle_scroll> to be
enabled)

=head2 clipboard_command

if you set this, an external program may be executed to store the
selection or URL. begin with C<|> to pipe into program or use
parameters C<%s> for text, C<%q> for quoted text or C<%x> for quoted
escape sequence.

=head2 copywin_custom_keys

You can define custom key bindings to use inside the copywin here. syntax is:
command-letter:weechat-keycode. available commands: -+>< (up/down/left/right)
fbae (forward word/backward word/beginning/end) !@ (open/start selection)
/UNCunc (toggle highlights/urls/nicks/channels) q (close window)

=head1 FUNCTION DESCRIPTION

for full pod documentation, filter this script with

  perl -pE'
  (s/^## (.*?) -- (.*)/=head2 $1\n\n$2\n\n=over\n/ and $o=1) or
   s/^## (.*?) - (.*)/=item I<$1>\n\n$2\n/ or
  (s/^## (.*)/=back\n\n$1\n\n=cut\n/ and $o=0,1) or
  ($o and $o=0,1 and s/^sub /=back\n\n=cut\n\nsub /)'

=cut

use MIME::Base64;

use constant SCRIPT_NAME => 'coords';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.7.3.1', 'GPL3', 'copy text and urls', 'stop_coords', '') || return;
sub SCRIPT_FILE() {
	my $infolistptr = weechat::infolist_get('perl_script', '', SCRIPT_NAME);
	my $filename = weechat::infolist_string($infolistptr, 'filename') if weechat::infolist_next($infolistptr);
	weechat::infolist_free($infolistptr);
	return $filename unless @_;
}

{
package Nlib;
# this is a weechat perl library
use strict; use warnings; no warnings 'redefine';

## i2h -- copy weechat infolist content into perl hash
## $infolist - name of the infolist in weechat
## $ptr - pointer argument (infolist dependend)
## @args - arguments to the infolist (list dependend)
## $fields - string of ref type "fields" if only certain keys are needed (optional)
## returns perl list with perl hashes for each infolist entry
sub i2h {
	my %i2htm = (i => 'integer', s => 'string', p => 'pointer', b => 'buffer', t => 'time');
	local *weechat::infolist_buffer = sub { '(not implemented)' };
	my ($infolist, $ptr, @args) = @_;
	$ptr ||= "";
	my $fields = ref $args[-1] eq 'fields' ? ${ pop @args } : undef;
	my $infptr = weechat::infolist_get($infolist, $ptr, do { local $" = ','; "@args" });
	my @infolist;
	while (weechat::infolist_next($infptr)) {
		my @fields = map {
			my ($t, $v) = split ':', $_, 2;
			bless \$v, $i2htm{$t};
		}
		split ',',
			($fields || weechat::infolist_fields($infptr));
		push @infolist, +{ do {
			my (%list, %local, @local);
			map {
				my $fn = 'weechat::infolist_'.ref $_;
				my $r = do { no strict 'refs'; &$fn($infptr, $$_) };
				if ($$_ =~ /^localvar_name_(\d+)$/) {
					$local[$1] = $r;
					()
				}
				elsif ($$_ =~ /^(localvar)_value_(\d+)$/) {
					$local{$local[$2]} = $r;
					$1 => \%local
				}
				elsif ($$_ =~ /(.*?)((?:_\d+)+)$/) {
					my ($key, $idx) = ($1, $2);
					my @idx = split '_', $idx; shift @idx;
					my $target = \$list{$key};
					for my $x (@idx) {
						my $o = 1;
						if ($key eq 'key' or $key eq 'key_command') {
							$o = 0;
						}
						if ($x-$o < 0) {
							local $" = '|';
							weechat::print('',"list error: $target/$$_/$key/$x/$idx/@idx(@_)");
							$o = 0;
						}
						$target = \$$target->[$x-$o]
					}
					$$target = $r;

					my $code = qq{
						local \$[=1;
						\$list{"\Q$key\E"}$idx = \$r
					};
					$key => $list{$key}
				}
				else {
					$$_ => $r
				}
			} @fields
		} };
	}
	weechat::infolist_free($infptr);
	!wantarray && @infolist ? \@infolist : @infolist
}

## hdh -- hdata helper
sub hdh {
	if (@_ > 1 && $_[0] !~ /^0x/ && $_[0] !~ /^\d+$/) {
		my $arg = shift;
		unshift @_, weechat::hdata_get_list(weechat::hdata_get($_[0]), $arg);
	}
	while (@_ > 2) {
		my ($arg, $name, $var) = splice @_, 0, 3;
		my $hdata = weechat::hdata_get($name);

		$var =~ s/!(.*)/weechat::hdata_get_string($hdata, $1)/e;
		(my $plain_var = $var) =~ s/^\d+\|//;
		my $type = weechat::hdata_get_var_type_string($hdata, $plain_var);
		if ($type eq 'pointer') {
			my $name = weechat::hdata_get_var_hdata($hdata, $var);
			unshift @_, $name if $name;
		}
		if ($type eq 'shared_string') {
			$type =~ s/shared_//;
		}

		my $fn = "weechat::hdata_$type";
		unshift @_, do { no strict 'refs';
						 &$fn($hdata, $arg, $var) };
	}
	wantarray ? @_ : $_[0]
}

## l2l -- copy weechat list into perl list
## $ptr - weechat list pointer
## $clear - if true, clear weechat list
## returns perl list
sub l2l {
	my ($ptr, $clear) = @_;
	my $itemptr = weechat::list_get($ptr, 0);
	my @list;
	while ($itemptr) {
		push @list, weechat::list_string($itemptr);
		$itemptr = weechat::list_next($itemptr);
	}
	weechat::list_remove_all($ptr) if $clear;
	@list
}

## find_bar_window -- find the bar window where the coordinates belong to
## $row - row
## $col - column
## returns bar window infolist and bar infolist in a array ref if found
sub find_bar_window {
	my ($row, $col) = @_;

	my $barwinptr;
	my $bar_info;
	for (i2h('bar_window')) {
		return [ $_, $bar_info ] if
			$row > $_->{'y'} && $row <= $_->{'y'}+$_->{'height'} &&
				$col > $_->{'x'} && $col <= $_->{'x'}+$_->{'width'} &&
					(($bar_info)=i2h('bar', $_->{'bar'})) && !$bar_info->{'hidden'};
	}
	
}

## in_window -- check if given coordinates are in a window
## $row - row
## $col - column
## $wininfo - infolist of window to check
## returns true if in window
sub in_window {
	my ($row, $col, $wininfo) = @_;

	# in window?
	$row > $wininfo->{'y'} &&
		$row <= $wininfo->{'y'}+$wininfo->{'height'} &&
			$col > $wininfo->{'x'} &&
				$col <= $wininfo->{'x'}+$wininfo->{'width'}
}

## in_chat_window -- check if given coordinates are in the chat part of a window
## $row - row
## $col - column
## $wininfo - infolist of window to check
## returns true if in chat part of window
sub in_chat_window {
	my ($row, $col, $wininfo) = @_;

	# in chat window?
	$row > $wininfo->{'chat_y'} &&
		$row <= $wininfo->{'chat_y'}+$wininfo->{'chat_height'} &&
			$col > $wininfo->{'chat_x'} &&
				$col <= $wininfo->{'chat_x'}+$wininfo->{'chat_width'}
}

## has_true_value -- some constants for "true"
## $v - value string
## returns true if string looks like a true thing
sub has_true_value {
	my $v = shift || '';
	$v =~ /^(?:on|yes|y|true|t|1)$/i
}

## has_false_value -- some constants for "false"
## $v - value string
## returns true if string looks like a B<false> thing
sub has_false_value {
	my $v = shift || '';
	$v =~ /^(?:off|no|n|false|f|0)?$/i
}

## bar_filling -- get current filling according to position
## $bar_infos - info about bar (from find_bar_window)
## returns filling as an integer number
sub bar_filling {
	my ($bar_infos) = @_;
	($bar_infos->[-1]{'position'} <= 1 ? $bar_infos->[-1]{'filling_top_bottom'}
	 : $bar_infos->[-1]{'filling_left_right'})
}

sub fu8on(@) {
	Encode::_utf8_on($_) for @_; wantarray ? @_ : shift
}

sub screen_length($) {
	weechat::strlen_screen($_[0])
}

## bar_column_max_length -- get max item length for column based filling
## $bar_infos - info about bar (from find_bar_window)
## returns max item length
sub bar_column_max_length {
	my ($bar_infos) = @_;
	my @items;
	for (@{ $bar_infos->[0]{'items_content'} }) {
		push @items, split "\n", join "\n", @$_;
	}
	my $max_length = 0;
	for (@items) {
		my $item_length = screen_length fu8on weechat::string_remove_color($_, '');
		$max_length = $item_length if $max_length < $item_length;
	}
	$max_length;
}

## find_bar_item_pos -- get position of an item in a bar structure
## $bar_infos - instance and general info about bar (from find_bar_window)
## $search - search pattern for item name
## returns (outer position, inner position, true if found)
sub find_bar_item_pos {
	my ($bar_infos, $search) = @_;
	my $item_pos_a = 0;
	my $item_pos_b;
	for (@{ $bar_infos->[-1]{'items_array'} }) {
		$item_pos_b = 0;
		for (@$_) {
			return ($item_pos_a, $item_pos_b, 1)
				if $_ =~ $search;
			++$item_pos_b;
		}
		++$item_pos_a;
	}
	(undef, undef, undef)
}

## bar_line_wrap_horiz -- apply linebreak for horizontal bar filling
## $prefix_col_r - reference to column counter
## $prefix_y_r - reference to row counter
## $bar_infos - info about bar (from find_bar_window)
sub bar_line_wrap_horiz {
	my ($prefix_col_r, $prefix_y_r, $bar_infos) = @_;
	while ($$prefix_col_r > $bar_infos->[0]{'width'}) {
		++$$prefix_y_r;
		$$prefix_col_r -= $bar_infos->[0]{'width'};
	}
}

## bar_lines_column_vert -- count lines in column layout
## $bar_infos - info about bar (from find_bar_window)
## returns lines needed for columns_horizontal layout
sub bar_lines_column_vert {
	my ($bar_infos) = @_;
	my @items;
	for (@{ $bar_infos->[0]{'items_content'} }) {
		push @items, split "\n", join "\n", @$_;
	}
	my $max_length = bar_column_max_length($bar_infos);
	my $dummy_col = 1;
	my $lines = 1;
	for (@items) {
		if ($dummy_col+$max_length > 1+$bar_infos->[0]{'width'}) {
			++$lines;
			$dummy_col = 1;
		}
		$dummy_col += 1+$max_length;
	}
	$lines;
}

## bar_items_skip_to -- skip several bar items on search for subitem position
## $bar_infos - info about bar (from find_bar_window)
## $search - patter of item to skip to
## $col - pointer column
## $row - pointer row
sub bar_items_skip_to {
	my ($bar_infos, $search, $col, $row) = @_;
	$col += $bar_infos->[0]{'scroll_x'};
	$row += $bar_infos->[0]{'scroll_y'};
	my ($item_pos_a, $item_pos_b, $found) = 
		find_bar_item_pos($bar_infos, $search);

	return 'item position not found' unless $found;

	# extract items to skip
	my $item_join = 
		(bar_filling($bar_infos) <= 1 ? '' : "\n");
	my @prefix;
	for (my $i = 0; $i < $item_pos_a; ++$i) {
		push @prefix, split "\n", join $item_join, @{ $bar_infos->[0]{'items_content'}[$i] };
	}
	push @prefix, split "\n", join $item_join, @{ $bar_infos->[0]{'items_content'}[$item_pos_a] }[0..$item_pos_b-1] if $item_pos_b;

	# cursor
	my $prefix_col = 1;
	my $prefix_y = 1;
	my $item_max_length;
	my $col_vert_lines;

	# forward cursor
	if (!bar_filling($bar_infos)) {
		my $prefix = join ' ', @prefix;
		$prefix_col += screen_length fu8on weechat::string_remove_color($prefix, '');
		++$prefix_col if @prefix && !$item_pos_b;
		bar_line_wrap_horiz(\($prefix_col, $prefix_y), $bar_infos);
	}
	elsif (bar_filling($bar_infos) == 1) {
		$prefix_y += @prefix;
		if ($item_pos_b) {
			--$prefix_y;
			$prefix_col += screen_length fu8on weechat::string_remove_color($prefix[-1], '');
		}
	}
	elsif (bar_filling($bar_infos) == 2) {
		$item_max_length = bar_column_max_length($bar_infos);
		for (@prefix) {
			$prefix_col += 1+$item_max_length;
			if ($prefix_col+$item_max_length > 1+$bar_infos->[0]{'width'}) {
				++$prefix_y;
				$prefix_col = 1;
			}
		}
	}
	elsif (bar_filling($bar_infos) == 3) {
		$item_max_length = bar_column_max_length($bar_infos);
		$col_vert_lines = $bar_infos->[-1]{'position'} <= 1 ? bar_lines_column_vert($bar_infos) : $bar_infos->[0]{'height'};
		my $pfx_idx = 0;
		for (@prefix) {
			$prefix_y = 1+($pfx_idx % $col_vert_lines);
			$prefix_col = 1+(1+$item_max_length)*(int($pfx_idx / $col_vert_lines)+1);
			return 'in prefix'
				if ($prefix_y == $row && $prefix_col > $col);
			++$pfx_idx;
		}
		$prefix_y = 1+(@prefix % $col_vert_lines);
		$prefix_col = 1+(1+$item_max_length)*int(@prefix / $col_vert_lines);
	}

	(undef,
	 $item_pos_a, $item_pos_b,
	 $prefix_col, $prefix_y,
	 (scalar @prefix),
	 $item_max_length, $col_vert_lines)
}

## bar_item_get_subitem_at -- extract subitem from a bar item at given coords
## $bar_infos - info about bar
## $search - search pattern for item whose subitems to get
## $col - pointer column
## $row - pointer row
## returns error message, subitem index, subitem text
sub bar_item_get_subitem_at {
	my ($bar_infos, $search, $col, $row) = @_;

	my ($error,
		$item_pos_a, $item_pos_b,
		$prefix_col, $prefix_y,
		$prefix_cnt,
		$item_max_length, $col_vert_lines) = 
			bar_items_skip_to($bar_infos, $search, $col, $row);

	$col += $bar_infos->[0]{'scroll_x'};
	$row += $bar_infos->[0]{'scroll_y'};

	return $error if $error;
	
	return 'no viable position'
		unless (($row == $prefix_y  && $col >= $prefix_col) || $row > $prefix_y || bar_filling($bar_infos) >= 3);

	my @subitems = split "\n", $bar_infos->[0]{'items_content'}[$item_pos_a][$item_pos_b];
	my $idx = 0;
	for (@subitems) {
		my ($beg_col, $beg_y) = ($prefix_col, $prefix_y);
		$prefix_col += screen_length fu8on weechat::string_remove_color($_, '');
		if (!bar_filling($bar_infos)) {
			bar_line_wrap_horiz(\($prefix_col, $prefix_y), $bar_infos);
		}

		return (undef, $idx, $_, [$beg_col, $col, $prefix_col, $beg_y, $row, $prefix_y])
			if (($prefix_col > $col && $row == $prefix_y) || ($row < $prefix_y && bar_filling($bar_infos) < 3));

		++$idx;

		if (!bar_filling($bar_infos)) {
			++$prefix_col;
			return ('outside', $idx-1, $_)
				if ($prefix_y == $row && $prefix_col > $col);
		}
		elsif (bar_filling($bar_infos) == 1) {
			return ('outside', $idx-1, $_)
				if ($prefix_y == $row && $col >= $prefix_col);
			++$prefix_y;
			$prefix_col = 1;
		}
		elsif (bar_filling($bar_infos) == 2) {
			$prefix_col += 1+$item_max_length-(($prefix_col-1)%($item_max_length+1));

			return ('outside', $idx-1, $_)
				if ($prefix_y == $row && $prefix_col > $col);

			if ($prefix_col+$item_max_length > 1+$bar_infos->[0]{'width'}) {
				return ('outside item', $idx-1, $_)
					if ($prefix_y == $row && $col >= $prefix_col);
				
				++$prefix_y;
				$prefix_col = 1;
			}
		}
		elsif (bar_filling($bar_infos) == 3) {
			$prefix_col += 1+$item_max_length-(($prefix_col-1)%($item_max_length+1));
			return ('outside', $idx-1, $_)
				if ($prefix_y == $row && $prefix_col > $col);
			$prefix_y = 1+(($idx+$prefix_cnt) % $col_vert_lines);
			$prefix_col = 1+(1+$item_max_length)*int(($idx+$prefix_cnt) / $col_vert_lines);

		}
	}
	'not found';
}

use Pod::Select qw();
use Pod::Simple::TextContent;

## get_desc_from_pod -- return setting description from pod documentation
## $file - filename with pod
## $setting - name of setting
## returns description as text
sub get_desc_from_pod {
	my $file = shift;
	return unless -s $file;
	my $setting = shift;

	open my $pod_sel, '>', \my $ss;
	Pod::Select::podselect({
	   -output => $pod_sel,
	   -sections => ["SETTINGS/$setting"]}, $file);

	my $pt = new Pod::Simple::TextContent;
	$pt->output_string(\my $ss_f);
	$pt->parse_string_document($ss);

	my ($res) = $ss_f =~ /^\s*\Q$setting\E\s+(.*)\s*/;
	$res
}

## get_settings_from_pod -- retrieve all settings in settings section of pod
## $file - file with pod
## returns list of all settings
sub get_settings_from_pod {
	my $file = shift;
	return unless -s $file;

	open my $pod_sel, '>', \my $ss;
	Pod::Select::podselect({
	   -output => $pod_sel,
	   -sections => ["SETTINGS//!.+"]}, $file);

	$ss =~ /^=head2\s+(.*)\s*$/mg
}

## mangle_man_for_wee -- turn man output into weechat codes
sub mangle_man_for_wee {
	for (@_) {
		s/_\x08(.)/weechat::color('underline').$1.weechat::color('-underline')/ge;
		s/(.)\x08\1/weechat::color('bold').$1.weechat::color('-bold')/ge;
	}
	wantarray ? @_ : $_[0]
}

## read_manpage -- read a man page in weechat window
## $file - file with pod
## $name - buffer name
sub read_manpage {
	my $caller_package = (caller)[0];
	my $file = shift;
	my $name = shift;

	if (my $obuf = weechat::buffer_search('perl', "man $name")) {
		eval qq{
			package $caller_package;
			weechat::buffer_close(\$obuf);
		};
	}

	my @wee_keys = Nlib::i2h('key');
	my @keys;

	my $winptr = weechat::current_window();
	my ($wininfo) = Nlib::i2h('window', $winptr);
	my $buf = weechat::buffer_new("man $name", '', '', '', '');
	return weechat::WEECHAT_RC_OK unless $buf;

	my $width = $wininfo->{'chat_width'};
	--$width if $wininfo->{'chat_width'} < $wininfo->{'width'} || ($wininfo->{'width_pct'} < 100 && (grep { $_->{'y'} == $wininfo->{'y'} } Nlib::i2h('window'))[-1]{'x'} > $wininfo->{'x'});

	weechat::buffer_set($buf, 'time_for_each_line', 0);
	eval qq{
		package $caller_package;
		weechat::buffer_set(\$buf, 'display', 'auto');
	};
	die $@ if $@;

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_previous' ||
			   $_->{'command'} eq '/input history_global_previous' } @wee_keys;
	@keys = 'meta2-A' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll -1') for @keys;

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_next' ||
			   $_->{'command'} eq '/input history_global_next' } @wee_keys;
	@keys = 'meta2-B' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll +1') for @keys;

	weechat::buffer_set($buf, 'key_bind_ ', '/window page_down');

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input delete_previous_char' } @wee_keys;
	@keys = ('ctrl-?', 'ctrl-H') unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window page_up') for @keys;

	weechat::buffer_set($buf, 'key_bind_g', '/window scroll_top');
	weechat::buffer_set($buf, 'key_bind_G', '/window scroll_bottom');

	weechat::buffer_set($buf, 'key_bind_q', '/buffer close');

	weechat::print($buf, " \t".mangle_man_for_wee($_))
			for `pod2man \Q$file\E 2>/dev/null | GROFF_NO_SGR=1 nroff -mandoc -rLL=${width}n -rLT=${width}n -Tutf8 2>/dev/null`;
	weechat::command($buf, '/window scroll_top');

	unless (hdh($buf, 'buffer', 'lines', 'lines_count') > 0) {
		weechat::print($buf, weechat::prefix('error').$_)
				for "Unfortunately, your @{[weechat::color('underline')]}nroff".
					"@{[weechat::color('-underline')]} command did not produce".
					" any output.",
					"Working pod2man and nroff commands are required for the ".
					"help viewer to work.",
					"In the meantime, please use the command ", '',
					"\tperldoc $file", '',
					"on your shell instead in order to read the manual.",
					"Thank you and sorry for the inconvenience."
	}
}

1
}

use constant CMD_COPYWIN => SCRIPT_NAME;
weechat::hook_command(CMD_COPYWIN, 'copy active window for hyperlink operations or free selection of text',
					  '[/] || url nicks channels',
					  'if any or more arguments are given, go into hyperlink mode and set this filter.'."\n".
						  'in the title bar of opened copy window, the possible key bindings are displayed.'."\n".
							  'use '.weechat::color('bold').'/'.CMD_COPYWIN.' help'.weechat::color('-bold').
								  ' to read the manual',
					  '|| / %- || url %- || nicks %- || channels %- || url,nicks %- || url,channels %- '.
						  '|| url,nicks,channels %- || nicks,channels %- || help',
					  'copywin_cmd', '');
weechat::hook_signal('buffer_closed', 'garbage_str', '');
weechat::hook_signal('upgrade', 'close_copywin', '');
weechat::hook_config('plugins.var.perl.'.SCRIPT_NAME.'.*', 'default_options', '');
weechat::hook_signal('mouse', 'mouse_evt', '');
weechat::hook_signal('input_flow_free', 'binding_mouse_fix', '');
weechat::hook_modifier('input_text_display_with_cursor', 'input_text_hlsel', '');
# is there builtin mouse support?
weechat::hook_hsignal(SCRIPT_NAME, 'hsignal_evt', '');
weechat::key_bind('mouse', +{
	map { $_ => 'hsignal:'.SCRIPT_NAME }
	'@chat:button1*', '@chat:button1-event-*', '@chat(perl.[*):button1'
});
weechat::command('', '/alias copywin '.CMD_COPYWIN)
	if 'copywin' ne CMD_COPYWIN && !Nlib::i2h('alias', '', 'copywin') && Nlib::i2h('hook', '', 'command,alias');

# downloaded line fields
use constant TRACE => -1;
use constant LINE => 0;
use constant LAYOUT => 1;

# URLS structure fields
use constant MSG => 0;
use constant URL_S => 1;
use constant URL => 2;
use constant URL_E => 3;
use constant URL_LINE => 4;
use constant URL_INFO => 5;

# captured control codes fields
use constant RES => 0;
use constant POS_S => 1;
use constant POS_E => 2;

# trace weelist container
our $listptr;

# global storage & fields
our %STR;
use constant BUFPTR => 0;
use constant LINES => 1;
use constant WINDOWS => 2;
use constant A_LINK => 3;
use constant URLS => 4;
use constant MODE => 5;
use constant CUR => 6;
use constant MOUSE_AUTOMODE => 7;
use constant URL_TYPE_FILTER => 8;
# currently active storage key
our $ACT_STR;

our $last_mouse_seq;
our $script_old_mouse_scroll;
our $mouse_2nd_click;
our $autoclose_in_progress;
our $drag_speed_timer;
our $delayed_nick_menu_timer;

our $hsignal_mouse_down_sent;

our $input_sel;

our $LAYOUT_OK;

my @SIMPLE_MODE_KEYS = ('/', 'U', 'N', 'C', 'P', 'u', 'n', 'c', 'p');

init_coords();

## hdh_get_lineinfo -- get lineinfo from hdata
## $_[0] - line pointer
## $_[1] - 'line' (automatic when using result from Nlib::hdh)
## returns lineinfo hashref
sub hdh_get_lineinfo {
	my @line_data = Nlib::hdh(@_, 'data');
	+{
		next_line => scalar Nlib::hdh(@_, 'next_line'),
		(map { $_ => scalar Nlib::hdh(@line_data,  $_) }
			qw(displayed message prefix str_time buffer date highlight)),
		tag => [ map { Nlib::hdh(@line_data, "$_|tags_array") }
					 0 .. Nlib::hdh(@line_data, 'tags_count')-1 ]
	   }
}

sub screen_length($) {
	weechat::strlen_screen($_[0])
}

sub fu8on(@) {
	Encode::_utf8_on($_) for @_; wantarray ? @_ : shift
}

## calculate_trace -- create a trace profile witgh word splits
## $lineinfo - lineinfo with message to break into lines
## $wininfo - window info hash with chat_width
## $base_trace - ref to base trace with # fields
## $prev_lineinfo - lineinfo of previous message for prefix erasure
## returns (layoutinfo hashref, partial trace arrayref)
sub calculate_trace {
	# b : pos // break between words
	# n : pos // new line
	# x : pos // cut word
	# t : x # j // time
	# u : x # j // buffer name
	# p : x # j // prefix (nick etc.)
	# q : x # j // separator
	# q : x . line
	my ($lineinfo, $wininfo, $base_trace, $prev_lineinfo) = @_;
	my $msg = fu8on $lineinfo->{'message'};
	my $layoutinfo = +{ count => 1 };
	my @trace;
	my $show_time = $base_trace->[1];
	my $no_prefix_align;
	if ($base_trace->[-1] < 0) {
		$no_prefix_align = $base_trace->[5];
		$base_trace->[5] = $base_trace->[-1] = 0;
		my $prefix = $lineinfo->{'prefix'};
		if (defined $prefix) {
			
			my ($nick_tag) = grep { /^nick_/ } @{$lineinfo->{'tag'}||[]};
			my ($pnick_tag) = grep { /^nick_/ } @{$prev_lineinfo->{'tag'}||[]};
			if ($nick_tag && $pnick_tag && $nick_tag eq $pnick_tag && !$lineinfo->{'highlight'} &&
					(grep { /_action$/ && !/^nick_/ } @{$lineinfo->{'tag'}||[]}) == 0 &&
					$prev_lineinfo && $lineinfo->{'prefix'} eq $prev_lineinfo->{'prefix'}) {
				my $repl = weechat::config_string(weechat::config_get(
					'weechat.look.prefix_same_nick'));
				$prefix = $repl if length $repl;
				$prefix = '' if $repl eq ' ';
			}
			$base_trace->[5] = (sort { $a <=> $b } #($no_prefix_align?$no_prefix_align+1:0),
									screen_length fu8on weechat::string_remove_color($prefix, ''))[0];
		}
	}
	$base_trace->[1] = $show_time ? screen_length fu8on weechat::string_remove_color($lineinfo->{'str_time'}, '') : 0;
	for (my ($i, $pos) = (0, 0); $i < @$base_trace; $i+=2) {
		$pos += $base_trace->[$i+1] + 1 if $base_trace->[$i+1];
		push @trace, $base_trace->[$i] . ':' . $pos . '#' if $base_trace->[$i+1];
	}
	my ($ctrl, $plain_msg) = capture_color_codes($msg);
	my @words = split /(\s+)/, $plain_msg;
	my $screen = 0;
	if ($base_trace->[-1]) {
		($screen) = ((trace_cond('q', [\@trace], 0))[0] =~ /:(\d+)/);
	}
	elsif ($base_trace->[5]) {
		($screen) = ((trace_cond('p', [\@trace], 0))[0] =~ /:(\d+)/);
	}
	elsif ($base_trace->[3]) {
		($screen) = ((trace_cond('u', [\@trace], 0))[0] =~ /:(\d+)/);
	}
	elsif ($base_trace->[1]) {
		($screen) = ((trace_cond('t', [\@trace], 0))[0] =~ /:(\d+)/);
	}
	my $new_screen = 0;
	my $eol_pos = weechat::config_string(weechat::config_get('weechat.look.align_end_of_lines'));
	unless ($eol_pos eq 'time') {
		($new_screen) = ((trace_cond('t', [\@trace], 0))[0] =~ /:(\d+)/)
			if $base_trace->[1];
		unless ($eol_pos eq 'buffer') {
			($new_screen) = ((trace_cond('u', [\@trace], 0))[0] =~ /:(\d+)/)
				if $base_trace->[3];
			unless ($eol_pos eq 'prefix') {
				($new_screen) = ((trace_cond('p', [\@trace], 0))[0] =~ /:(\d+)/)
					if $base_trace->[5];
				unless ($eol_pos eq 'suffix') {
					$new_screen = $screen;
				}
			}
		}
	}
	unless ($lineinfo->{'date'}) {
		$screen = $new_screen = 0;
		@trace = ();
		if ($base_trace->[3]) {
			$screen = $base_trace->[3] + 1;
			push @trace, "u:$screen#";
		}
	}
	$base_trace->[1] = $show_time;
	if (defined $no_prefix_align) {
		$base_trace->[5] = $no_prefix_align;
		$base_trace->[-1] = -1;
	}

	# XXX missing special case:  $wininfo->{'chat_width'} - $screen < 4
	# `--> ignore all line break rules, just X every screenful
	my $pos = 0;
	my $width = $wininfo->{'chat_width'};
	--$width if $wininfo->{'chat_width'} < $wininfo->{'width'} || ($wininfo->{'width_pct'} < 100 && (grep { $_->{'y'} == $wininfo->{'y'} } Nlib::i2h('window'))[-1]{'x'} > $wininfo->{'x'});
	for (my $i = 0; $i < @words; $i+=2) {
		my $len = defined $words[$i] ? screen_length $words[$i] : 0;
		my $len2 = $i == $#words ? 0 : screen_length $words[$i+1];
		if ($len <= $width - $screen) {
			# no action needed
			$screen += $len + $len2;
		}
		elsif ($len > $width - $screen) {
			if ($len <= $width - $new_screen && $pos) { #cannot break before first word
				push @trace, 'b:'.$pos;
				push @trace, 'q:'.$new_screen.'.'.$layoutinfo->{'count'}++;
				$screen = $new_screen + $len + $len2;
			}
			else {
				my $pump = $width - $screen;
				if ($pump <= 0) {
					push @trace, 'b:'.$pos;
					push @trace, 'q:'.$new_screen.'.'.$layoutinfo->{'count'}++;
					$pump = $width - $new_screen;
				}
				if ($pump > 0) {
					my $ipos = $pos;
					while ($pump < $len) {
						my $i = 0;
						for (;;) {
							my $clen = screen_length substr $plain_msg, $ipos, 1;
							last if $i + $clen > $pump;
							$i += $clen;
							++$ipos;
						}
						push @trace, 'x:'.$ipos;
						push @trace, 'q:'.$new_screen.'.'.$layoutinfo->{'count'}++;
						$len -= $i;
						$pump = $width - $new_screen;
					}
				}
				$screen = $new_screen + $len + $len2;
			}
		}
		$pos += ($len ? length $words[$i] : 0) + ($len2 ? length $words[$i+1] : 0);
	}
	while (@{$ctrl->[POS_S]}) {
		my $ctrl_s = shift @{$ctrl->[POS_S]};
		my $ctrl_e = shift @{$ctrl->[POS_E]};
		my $ctrl_r = shift @{$ctrl->[RES]};
		for (@trace) {
			s{^([bnx]:)(\d+)}{
				$1 . ( $2 + ($2 > $ctrl_s ? length $ctrl_r : 0) )
			}ge;
		}
	}
	($layoutinfo, \@trace)
}

## download_lines -- load all (partially) visible lines & infos
## $wininfo -  hash ref with windowinfo of window to grab
## returns reference to all downloaded lines
sub download_lines {
	my ($wininfo) = @_;

	my @scroll_area = Nlib::hdh($wininfo->{'pointer'}, 'window', 'scroll');
	my @lines_in = Nlib::hdh($wininfo->{'buffer'}, 'buffer', 'lines');
	my $lineinfo =  hdh_get_lineinfo(Nlib::hdh(@lines_in, 'last_line'));

	my $show_time = Nlib::hdh($wininfo->{'buffer'}, 'buffer', 'time_for_each_line');
	my $buffer_len = (sort { $a <=> $b } Nlib::hdh(@lines_in, 'buffer_max_length'), grep { $_ > 0 } weechat::config_integer(weechat::config_get('weechat.look.prefix_buffer_align_max')))[0];
	my $prefix_len = (sort { $a <=> $b } Nlib::hdh(@lines_in, 'prefix_max_length'), grep { $_ > 0 } weechat::config_integer(weechat::config_get('weechat.look.prefix_align_max')))[0];
	my $separator_len = weechat::config_string(weechat::config_get('weechat.look.prefix_align')) eq 'none' ? -1 : screen_length fu8on weechat::config_string(weechat::config_get('weechat.look.prefix_suffix'));

	my @base_trace = (t => $show_time, u => $buffer_len, p => $prefix_len, q => $separator_len);

	my @line = Nlib::hdh(@lines_in, 'last_line');
	my $last_read_line = weechat::config_string(weechat::config_get('weechat.look.read_marker')) eq 'line'
		? Nlib::hdh(@lines_in, 'last_read_line')
			: '';
	my $read_marker_always = weechat::config_boolean(weechat::config_get('weechat.look.read_marker_always_show'));
	$last_read_line = '' if $last_read_line eq $line[0]
		&& !$read_marker_always;
	my $lp;
	my @scroll_line = Nlib::hdh(@scroll_area, 'start_line');
	if ($scroll_line[0]) {
		@line = @scroll_line;
		$lineinfo = hdh_get_lineinfo(@line);
		$wininfo->{'start_line_pos'} = Nlib::hdh
			(@scroll_area, 'start_line_pos');
	}
	else {
		$wininfo->{'start_line_pos'} = 0;
		my $total = Nlib::hdh(@lines_in, 'lines_count');
		return [] unless $total;
		my $not_last_line = 0;
		for (my ($i, $j) = (0, 0); $j < $wininfo->{'chat_height'} && $i < $total; ++$i) {

			$line[0] = Nlib::hdh(@line, 'prev_line') if $i > 0;

			if ($line[0] eq $last_read_line) {
				if ($not_last_line || $read_marker_always) {
					++$j;
				}
				else {
					$last_read_line = '';
				}
			}
			my @line_data = Nlib::hdh(@line, 'data');
			if (Nlib::hdh(@line_data, 'displayed')) {
				my $lineinfo = +{ map { $_ => Nlib::hdh(@line_data, $_) } qw(message str_time date highlight) };
				my $prev_lineinfo;
				if ($base_trace[-1] < 0 && $i + 1 < $total) {
				HAS_PREV: {
						my @prev_line = @line;
						my @prev_linedata;
						do {
							@prev_line = Nlib::hdh(@prev_line, 'prev_line');
							last HAS_PREV unless $prev_line[0];
							@prev_linedata = Nlib::hdh(@prev_line, 'data');
						} until (Nlib::hdh(@prev_linedata, 'displayed'));
						$prev_lineinfo = +{
							(map { $_ => Nlib::hdh(@prev_linedata, $_) } qw(message str_time date highlight prefix)),
							tag => [
								map { Nlib::hdh(@prev_linedata, "$_|tags_array") }
									0 .. Nlib::hdh(@prev_linedata, 'tags_count')-1 ]
						   };
						my ($prev_layoutinfo) = calculate_trace($prev_lineinfo,
																$wininfo, \@base_trace);
						my ($this_layoutinfo) = calculate_trace($lineinfo,
																$wininfo, \@base_trace);
						#$prev_lineinfo = undef if $prev_layoutinfo->{'count'} + $this_layoutinfo->{'count'} + $j > $wininfo->{'chat_height'};
					}
					$lineinfo->{'prefix'} = Nlib::hdh(@line_data, 'prefix');
					$lineinfo->{'tag'} = [
						map { Nlib::hdh(@line_data, "$_|tags_array") }
							0 .. Nlib::hdh(@line_data, 'tags_count')-1 ];
				}
				my ($layout_info) = calculate_trace($lineinfo,
													$wininfo, \@base_trace,
													$prev_lineinfo);
				$prev_lineinfo = $lineinfo;
				$j += $layout_info->{'count'};
				$not_last_line = 1 if $j;
				$wininfo->{'start_line_pos'} -= $wininfo->{'chat_height'} - $j
					if $j > $wininfo->{'chat_height'};
			}
		}
		$lineinfo = hdh_get_lineinfo(@line);
	}
	$lp = $line[0];

	my @lines;
	my $current_line = 0;
	if ($lineinfo->{'displayed'}) {
		push @lines, [+{%$lineinfo}, calculate_trace($lineinfo, $wininfo, \@base_trace)];
		$current_line = $lines[0][LAYOUT]{'count'}-$wininfo->{'start_line_pos'};
	}
	my $prev_lineinfo;
	$prev_lineinfo = $lineinfo unless $wininfo->{'start_line_pos'};
	# XXX start_line_pos is buggy under yet uncertain multi-line messages
	#$wininfo->{'start_line_pos'} = 6;

	do {
		if ($lp eq $last_read_line) {
			push @lines, [+{message=>'',prefix=>''}, +{count=>1}, []];
			++$current_line;
		}

		$lp = $lineinfo->{'next_line'};
		$lineinfo = hdh_get_lineinfo($lineinfo->{'next_line'}, 'line');
		
		if ($lineinfo->{'displayed'}) {
			push @lines, [+{%$lineinfo}, calculate_trace($lineinfo, $wininfo, \@base_trace, $prev_lineinfo)];
			$prev_lineinfo = $lineinfo;
			$current_line += $lines[-1][LAYOUT]{'count'};
		}
	}
	while ($lineinfo->{'next_line'} && $current_line < $wininfo->{'chat_height'});

	\@lines;
}

## OLD_download_lines -- load all (partially) visible lines & infos
## $wininfo -  hash ref with windowinfo of window to grab
## returns reference to all downloaded lines
sub OLD_download_lines {
	my ($wininfo) = @_;

	my @lines;

	# get first line of buffer
	return \@lines unless $wininfo->{'start_line'};
	my ($lineinfo) = Nlib::i2h('buffer_lines', @{$wininfo}{'buffer','start_line'});
	my ($layoutinfo) = Nlib::i2h('layout', $wininfo->{'pointer'}, $lineinfo->{'line'}, $listptr);
	my $current_line = $layoutinfo->{'count'}-$wininfo->{'start_line_pos'};

	push @lines, [+{%$lineinfo}, $layoutinfo, [Nlib::l2l($listptr, 1)]];

	while ($lineinfo->{'next_line'} && $current_line < $wininfo->{'chat_height'}) {
		($lineinfo) = Nlib::i2h('buffer_lines', @{$lineinfo}{'buffer','next_line'});		
		next unless $lineinfo->{'displayed'};
		my ($layoutinfo) = Nlib::i2h('layout', $wininfo->{'pointer'}, $lineinfo->{'line'}, $listptr);
		$current_line += $layoutinfo->{'count'};

		push @lines, [+{%$lineinfo}, $layoutinfo, [Nlib::l2l($listptr, 1)]];
	}

	\@lines
}

## message_splits -- extract word splits in the message from trace
## $line - one line from download_lines
## returns all split events from trace as list of [position, event]
sub message_splits {
	my ($line) = @_;
	map {
		my ($l, $d) = /(.):(\d+)/;
		#($l =~ /[bn]/ ? 1 : 0) + 
		[ $d, $l ]
	}
	grep { /^[bnx]:/ } # b: break between words, n: new line, x: cut word
	@{ $line->[TRACE] }
}

## trace_cond -- filter trace for certain condition
## $what - event to match
## $line - downloaded line (with trace section)
## $lineno - line number for event
## returns matching trace event
sub trace_cond {
	my ($what, $line, $lineno) = @_;
	my $ext = $lineno ? qr/[.]$lineno$/ : qr/#/;
	grep { /^$what:/ && /$ext/ } @{ $line->[TRACE] }
}

## to_pos -- pad string to reach a certain position
## $tr_info - trace event from trace_cond, contains position
## $c_ref - string reference where padding is added
sub to_pos {
	my ($tr_info, $c_ref) = @_;
	$tr_info =~ /:(\d+)/;
	my $pos = $1;
	my $current_length = screen_length fu8on weechat::string_remove_color($$c_ref, '');
	if ($pos-$current_length < 0) {
		chop $$c_ref while length $$c_ref && (screen_length fu8on weechat::string_remove_color($$c_ref, '')) > $pos;
	}
	else {
		$$c_ref .= ' 'x($pos-$current_length);
	}
}

## right_align -- right align some text
## $tr - trace event, contains position for right alignment
## $text_ref - text reference to right align
## $c_ref - string reference where padding is added, so that $text_ref would be right aligned
sub right_align {
	my ($tr, $text_ref, $c_ref) = @_;
	$tr =~ /:(\d+)/;
	my $pos1 = $1 -1;
	my $text_length = screen_length fu8on weechat::string_remove_color($$text_ref, '');
	my $current_length = screen_length fu8on weechat::string_remove_color($$c_ref, '');
	$$c_ref .= ' 'x($pos1-$text_length-$current_length)
}

## show_time -- output timestamp and pad to next position
## $line - downloaded line
## $c_ref - string reference on which to output
sub show_time {
	my ($line, $c_ref) = @_;
	if (my ($tr) = trace_cond('t', $line)) {
		$$c_ref .= $line->[LINE]{'str_time'};
		to_pos($tr, $c_ref);
	}
}

## show_buffername -- output buffer name and pad to next position
## $line - downloaded line
## $c_ref - string reference on which to output
sub show_buffername {
	my ($line, $c_ref) = @_;
	if (my ($tr) = trace_cond('u', $line)) {
		my $buffer = weechat::color('chat_prefix_buffer').
			         (Nlib::i2h('buffer', $line->[LINE]{'buffer'}))[0]{'short_name'}.
				     weechat::color('reset');
		if (weechat::config_string(weechat::config_get(
		   'weechat.look.prefix_buffer_align')) =~ /right/) {
			right_align($tr, \$buffer, $c_ref);
		}
		$$c_ref .= $buffer;
		to_pos($tr, $c_ref);
	}
}

## show_prefix -- output prefix and pad to next position
## $line - downloaded line
## $c_ref - string reference on which to output
sub show_prefix {
	my ($line, $c_ref, $prev_line) = @_;
	if (my ($tr) = trace_cond('p', $line)) {
		my $prefix = fu8on $line->[LINE]{'prefix'};
		my ($nick_tag) = grep { /^nick_/ } @{$line->[LINE]{'tag'}||[]};
		my ($pnick_tag) = grep { /^nick_/ } @{$prev_line->[LINE]{'tag'}||[]};
		if ($nick_tag && $pnick_tag && $nick_tag eq $pnick_tag && !$line->[LINE]{'highlight'} &&
				(grep { /_action$/ && !/^nick_/ } @{$line->[LINE]{'tag'}||[]}) == 0 &&
				$prev_line && $line->[LINE]{'prefix'} eq $prev_line->[LINE]{'prefix'}) {
			my $repl = fu8on weechat::config_string(weechat::config_get(
					'weechat.look.prefix_same_nick'));
			$prefix = repeat_control_codes($prefix) . $repl if $repl;
		}
		if (weechat::config_string(weechat::config_get(
		   'weechat.look.prefix_align')) =~ /right/) {
			right_align($tr, \$prefix, $c_ref);
		}
		$$c_ref .= $prefix;
		to_pos($tr, $c_ref);
	}
}

## show_separator -- output separator and pad to next position
## $line - downloaded line
## $c_ref - string reference on which to output
sub show_separator {
	my ($line, $c_ref, $lineno) = @_;
	if (my ($tr) = trace_cond('q', $line, $lineno)) {
		my $separator = fu8on weechat::color('chat_prefix_suffix').
			            weechat::config_string(weechat::config_get('weechat.look.prefix_suffix'));
		right_align($tr, \$separator, $c_ref);
		$$c_ref .= $separator; # if XXX
		to_pos($tr, $c_ref);
	}
}

## repeat_control_codes -- repeat control codes previously seen (for linebreaks)
## $text - all codes in this text will be repeated
## returns control codes as a string
sub repeat_control_codes {
	my ($text) = @_;
	my $id_control = quotemeta fu8on weechat::string_remove_color($text, "\1");
	$id_control =~ s/\\\01/(.+?)/g;
	my @res = $text =~ /^()$id_control()$/;
	join '', @res
}

## calc_free_image -- create image of free window buffer
## $wininfo - window info hash with start_line_pos & chat_height
## $lines_ref - array ref of lines from download_lines
## returns a array reference to all lines in the image
sub calc_free_image {
	my ($wininfo, $lines_ref) = @_;
	my @image;
	my $i = 0;
	my $first_line = $wininfo->{'start_line_pos'};
	my $prev_line;
	for my $line (@$lines_ref) {
		my $max_length = [(length $line->[LINE]{'message'}),''];
		my @splits = ([0,''], message_splits($line), $max_length, $max_length);
		for (0 .. $line->[LAYOUT]{'count'}-1) {
			shift @splits if $splits[0][0] - $splits[1][0] >= 0;
			last if $i >= $wininfo->{'chat_height'};
			my $subm = substr $line->[LINE]{'message'}, $splits[0][0], $splits[1][0]-$splits[0][0];
			if ($_ >= $first_line) {
 				my $construction = '';
				unless ($_) {
					show_time($line, \$construction);
					show_buffername($line, \$construction);
					show_prefix($line, \$construction, $prev_line);
					$prev_line = $line if exists $line->[LINE]{'date'};
				}
				show_separator($line, \$construction, $_);
				$construction .= weechat::color('reset');
 				$construction .= repeat_control_codes(substr $line->[LINE]{'message'}, 0, $splits[0][0]);
				$subm =~ s/^ +// if $splits[0][1] =~ /[bn]/;
 				$construction .= $subm;
				$construction .= weechat::color('reset');
				
				push @image, $construction;
				$i++;
			}
			shift @splits;
		}
		$first_line = 0;
	}
	\@image
}

## capture_color_codes -- extract all weechat control codes from a message and store them with their original positions
## $msg - message from which to start
## returns a array ref with C<RES> (control codes), C<POS_S> (start position), C<POS_E> (end position) and optionally string without all codes
sub capture_color_codes {
	my ($msg) = @_;
	my $id_control = quotemeta fu8on weechat::string_remove_color($msg, "\1");
	$id_control =~ s/(\\\01)+/(.+?)/g;
	my @ctrl_res = $msg =~ /^()$id_control()$/;
	my @ctrl_pos_s = @-;
	my @ctrl_pos_e = @+;

	shift @ctrl_pos_s; shift @ctrl_pos_e;
	
	#my @chunks = split "\01+", $color_1, -1;

	my @ret = \( @ctrl_res, @ctrl_pos_s, @ctrl_pos_e );
	if (wantarray) {
		( \@ret, fu8on weechat::string_remove_color($msg, '') );
	}
	else {
		\@ret
	}
}

sub DEBUG_bracketing {
	my ($bracketing_r, $msg_r, $fx) = @_;
	return unless $fx;
	my $dumpline = ' ' x length $$msg_r;
	my @pair_pool = ('a'..'z');
	for (sort { $a eq 'oc' ? -1 : $b eq 'oc' ? 1 : $a <=> $b } keys %$bracketing_r) {
		my @l = @{ $bracketing_r->{$_} };
		if (@l) {
			my $ch = shift @pair_pool;
			substr $dumpline, $l[0], 1, $ch;
			substr $dumpline, $l[-2], 1, "\U$ch";
			push @pair_pool, $ch;
		}
	}
	print $fx $$msg_r."\n$dumpline\n";
}

## calculate_bracketing -- try to detect bracketing pairs
## $msg_r - reference to bracketed string 
## returns hash ref to detected bracketing
sub calculate_bracketing {
	my ($msg_r) = @_;
	my $braces = weechat::config_get_plugin('url_braces');
	my %br_open;
	while ($braces =~ s/^(.)(.*)(.)$/$2/) {
		$br_open{$3} = $1;
	}
	$br_open{$braces} = $braces if length $braces;
	my %bracketing;
	my $br_open = join '|', map { quotemeta } values %br_open;
	my $br_close = join '|', map { quotemeta } keys %br_open;
	while ($$msg_r =~ /($br_open|$br_close)/g) {
		my $char = $1;
		my $pos = $-[0];
		if ($char =~ /$br_close/ && @{ $bracketing{'oc'} || [] } && $bracketing{'oc'}[-1][-1] eq $br_open{$char}) {
			my $match = pop @{ $bracketing{'oc'} };
			push @$match, $pos, $char;
			$bracketing{$pos} = $bracketing{$match->[0]} = $match;
		}
		elsif ($char =~ /$br_open/) {
			push @{ $bracketing{'oc'} }, [ $pos, $char ];
		}
		else {
			$bracketing{$pos} = [ $pos, $char ];
		}
	}
	while (@{ $bracketing{'oc'} || [] }) {
		my $match = shift @{ $bracketing{'oc'} };
		$bracketing{$match->[0]} = $match;
	}
	\%bracketing
}

sub DEBUG_hyperlink {
	my ($s, $plain_msg, $e, $fx) = @_;
	return unless $fx;
	my $dumpline = ' ' x length $plain_msg;
	substr $dumpline, $s, 1, "\\";
	substr $dumpline, $e-1, 1, '/';
	print $fx '  '.$dumpline."\n";
	print $fx "----------\n";
}

## hyperlink_adjust_region -- removes bracketing and word end markers if detected around/at the end of region
## $sr - reference to start position of hyperlink
## $msg_r - reference to string with hyperlink
## $er - reference to end position of hyperlink
## $bracketing_r - calculated bracketing for this string
sub hyperlink_adjust_region {
	my ($sr, $msg_r, $er, $bracketing_r, $no_url) = @_;
	my $non_endings = weechat::config_get_plugin('url_non_endings');
	my $non_beginnings = weechat::config_get_plugin('url_non_beginnings');
	for (undef) {
		if (exists $bracketing_r->{$$er-1} && $bracketing_r->{$$er-1}[0] == $$sr) {
			++$$sr; --$$er; redo;
		}
		elsif (exists $bracketing_r->{$$er-1} && $bracketing_r->{$$er-1}[0] < $$sr) {
			--$$er; redo;
		}
		elsif (exists $bracketing_r->{$$sr} && $bracketing_r->{$$sr}[-2] > $$er-1) {
			++$$sr; redo;
		}
		unless ($no_url) {
			if ((substr $$msg_r, $$er-1, 1) =~ /$non_endings/) {
				--$$er; redo;
			}
			elsif ((substr $$msg_r, $$sr, 1) =~ /$non_beginnings/) {
				++$$sr; redo;
			}
		}
	}
}

sub trace_to_u8 {}

sub OLD_trace_to_u8 {
	my ($line) = @_;
	my $bytes_msg = $line->[LINE]{'message'};
	Encode::_utf8_off($bytes_msg);
	
	for (@{ $line->[TRACE] }) {
		s{^([bnx]:)(\d+)}{
			$1 . length fu8on substr $bytes_msg, 0, $2;
		}ge;
	}
}

## hyperlink_replay_code1 -- insert start/end of marking and adjust positions/trace
## $line - downloaded line with trace info to adjust
## $msg_r - reference to msg in which to insert
## $coder - reference to code to insert
## $tr - seek this much to the left when correcting trace profile
## @advs - references to arrays of positions to advance, first one will be shifted
## $fx - debug file handle
## $DBG - output debug info, prefix with $DBG
sub hyperlink_replay_code1 {
	my ($line, $msg_r, $coder, $tr, @advs, $fx, $DBG) = @_;
	unless (ref $advs[-1]) {
		$DBG = pop @advs;
		$fx = pop @advs;
	}
	my $pos_r = $advs[0];
	my $pos = shift @$pos_r;
	print $fx '[1]'."code:$$coder pos:$pos\n" if $fx;
	substr $$msg_r, $pos, 0, $$coder;
	print $fx $DBG.' '.$$msg_r."\n" if $fx;
	for (@advs) {
		$_ += length $$coder for @$_;
	}
	for (@{ $line->[TRACE] }) {
		s{^([bnx]:)(\d+)}{
			$1 . ( $2 + ($2 > $pos-$tr ? length $$coder : 0) )
		}ge;
	}
}

## hyperlink_replay_code2 -- reinsert color codes and adjust positions
## $ctrl - captured control codes from capture_color_codes
## $msg_r - reference to msg in which to insert
## @advs - references to arrays of positions to advance
## $fx - debug file handle
## $DBG - output debug info, prefix with $DBG
sub hyperlink_replay_code2 {
	my ($ctrl, $msg_r, @advs, $fx, $DBG) = @_;
	unless (ref $advs[-1]) {
		$DBG = pop @advs;
		$fx = pop @advs;
	}
	my $ctrl_s = shift @{$ctrl->[POS_S]};
	my $ctrl_e = shift @{$ctrl->[POS_E]};
	my $ctrl_r = shift @{$ctrl->[RES]};
	substr $$msg_r, $ctrl_s, 0, $ctrl_r;
	print $fx $DBG.' '.$$msg_r."\n" if $fx;
	for (@advs) {
		$_ += $ctrl_e-$ctrl_s for @$_;
	}
}


## hyperlink_replay_codes -- insert marker codes, reinsert control codes into plain msg
## $line - line with trace data to adjust
## $url_sr - reference to hyperlink starting position
## $msg_r - reference to message where positions apply
## $url_er - reference to hyperlink ending positions
## $ctrl - capture_color_codes result of control codes
## $active - reference that counts no of links and actives on "0"
## $fx - debug file handle
sub hyperlink_replay_codes {
	my ($line, $url_sr, $msg_r, $url_er, $ctrl, $active, $fx) = @_;

	my $ul = join '', map { weechat::color($_) } split '[.]',
		weechat::config_get_plugin('color.url_highlight');
	#my $UL = weechat::color('-underline').weechat::color('-reverse');

	my $ul_active = join '', map { weechat::color($_) } split '[.]',
		weechat::config_get_plugin('color.url_highlight_active');
	my $UL_active = weechat::color('reset');

	my $last_url_s;

	my $max_loop = 2*( @{$ctrl->[POS_S]} + @$url_sr + @$url_er );
	while (@{$ctrl->[POS_S]} || @$url_sr || @$url_er) {
		print $fx "<S> @$url_sr\n<E> @$url_er\n<C> @{$ctrl->[POS_S]}\n" if $fx;
	   #if (@$url_sr && $url_sr->[0] <= $url_er->[0] && (!@{$ctrl->[POS_S]} || $url_sr->[0] <= $ctrl->[POS_S][0])) # code goes before original ctl code
		if (@$url_sr && $url_sr->[0] <= $url_er->[0] && (!@{$ctrl->[POS_S]} || $url_sr->[0] < $ctrl->[POS_S][0])) {
			$last_url_s = $url_sr->[0];
			hyperlink_replay_code1($line, $msg_r, ($$active ? \$ul : \$ul_active), 0,
				$url_sr, $url_er, @{$ctrl}[POS_S,POS_E], $fx, 'S');
		}
		elsif (@$url_er && (!@{$ctrl->[POS_S]} || $url_er->[0] <= $ctrl->[POS_S][0])) {
			my $UL_active1 = $UL_active;
			if (defined $last_url_s) {
				# get part of message constructed thus far, and remove starting bracket
				my $msg_part1 = substr $$msg_r, 0, $url_er->[0];
				substr $msg_part1, $last_url_s, length ($$active ? $ul : $ul_active), '';
				$UL_active1 .= repeat_control_codes($msg_part1);
				$last_url_s = undef;
			}
			hyperlink_replay_code1($line, $msg_r, ($$active ? \$UL_active1 : \$UL_active1), 1,
				$url_er, $url_sr, @{$ctrl}[POS_S,POS_E], $fx, 'E');
			--$$active;
		}
		else { # ($ctrl->[POS_S][0] <= $url_sr->[0] && $ctrl->[POS_S][0] <= $url_er->[0])
			my $ip = $ctrl->[POS_E][0];
			my $needs_fixup = defined $last_url_s && $ctrl->[RES][0] =~ $UL_active;
			hyperlink_replay_code2($ctrl, $msg_r, $url_sr, $url_er, $fx, 'C');
			if ($needs_fixup) {
				$last_url_s = $ip;
				hyperlink_replay_code1($line, $msg_r, ($$active ? \$ul : \$ul_active), 0,
				[$ip], $url_sr, $url_er, @{$ctrl}[POS_S,POS_E], $fx, 'F');
			}
		}
		--$max_loop; die 'endless loop' if $max_loop < 0;
	}
}

## hyperlink_match_type_filter -- checks if current type filter applies to url info
## $url_info - hashref with a type property
## returns true or false
sub hyperlink_match_type_filter {
	my ($url_info) = @_;
	my $t = substr $url_info->{'type'}, 0, 1;
	$ACT_STR->[URL_TYPE_FILTER] =~ $t
}

## hyperlink_function -- highlight hyperlinks
## $lines_ref - downloaded lines
sub hyperlink_function {
	my ($lines_ref) = @_;
	my $fx;
	#open $fx, '>', ... || weechat::print('', "error:$!");
	my ($nicklist, $channels);
	if (Nlib::has_true_value(weechat::config_get_plugin('hyper_nicks'))) {
		$nicklist = join '|',
			map { quotemeta }
			sort { length $b <=> length $a }
			map { $_->{'name'} }
			grep { $_->{'type'} eq 'nick' && $_->{'visible'} && length $_->{'name'} }
			Nlib::i2h('nicklist', $ACT_STR->[WINDOWS]{'buffer'});
	}
	else {
		$nicklist = '(?!)';
	}
	$nicklist = '(?!)' unless length $nicklist; # stop infinite loop on empty pair
	if (Nlib::has_true_value(weechat::config_get_plugin('hyper_channels'))) {
		$channels = qr,[#]+(?:\w|[][./+^!&|~}{)(:\\*@?'-])+,;
	}
	else {
		$channels = '(?!)';
	}

	my $re = weechat::config_get_plugin('url_regex');
	$ACT_STR->[A_LINK] = -1 unless defined ${$ACT_STR}[A_LINK];
	my $a_link = -1;
	if (defined $ACT_STR->[URLS] && $ACT_STR->[A_LINK] < @{$ACT_STR->[URLS]}
	   && hyperlink_match_type_filter($ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO])) {
		for my $i (0 .. $ACT_STR->[A_LINK]) {
			++$a_link
				if hyperlink_match_type_filter($ACT_STR->[URLS][$i][URL_INFO]);
		}
	}
	my @urls;
	my $i = 0; # line index
	for my $line (@$lines_ref) {
		my %prefix_type = (type => 'prefix');
		my ($pfx_nick) = grep { /^nick_/ } @{ $line->[LINE]{'tag'} };

		if (Nlib::has_true_value(weechat::config_get_plugin('hyper_prefix')) &&
				$line->[LINE]{'prefix'} &&
					defined $pfx_nick && $pfx_nick =~ s/^nick_//) {
			push @urls, [ $line, -1, $pfx_nick, -1, $i, \%prefix_type ];

			if (hyperlink_match_type_filter(\%prefix_type)) {
				my $ul = join '', map { weechat::color($_) } split '[.]',
					weechat::config_get_plugin('color.url_highlight');

				my $ul_active = join '', map { weechat::color($_) } split '[.]',
					weechat::config_get_plugin('color.url_highlight_active');
				my $UL_active = weechat::color('reset');

				my ($ctrl, $plain_pfx) = capture_color_codes(fu8on $line->[LINE]{'prefix'});
				my $my_ul = $a_link ? $ul : $ul_active;
				substr $line->[LINE]{'prefix'}, $ctrl->[POS_E][-2], 0, $my_ul;
				substr $line->[LINE]{'prefix'}, $ctrl->[POS_E][-1]+length $my_ul, 0, $UL_active;
				--$a_link;
			}
		}
		my $msg = fu8on $line->[LINE]{'message'};
		my ($ctrl_codes, $plain_msg) = capture_color_codes($msg);
		my $bracketing_r = calculate_bracketing(\$plain_msg);
		DEBUG_bracketing($bracketing_r, \$plain_msg, $fx);
		my (@url_s, @url_res, @url_e);
		while ($plain_msg =~ /\b($nicklist)(?:(?=\W)|$)|(?:^|(?<=\W))($channels)\b|$re/gx) {
			my %typeinfo = (type => defined $1 ? 'nick' : defined $2 ? 'channel' : 'url');
			my ($s, $e) = ($-[0], $+[0]);
			DEBUG_hyperlink($s, $plain_msg, $e, $fx);
			
			hyperlink_adjust_region(\($s, $plain_msg, $e), $bracketing_r, $typeinfo{'type'} ne 'url')
				unless $typeinfo{'type'} eq 'nick';
			my $t = substr $plain_msg, $s, $e-$s;
			if (hyperlink_match_type_filter(\%typeinfo)) {
				push @url_s, $s;
				push @url_res, $t;
				push @url_e, $e;
			}
			DEBUG_hyperlink($s, $plain_msg, $e, $fx);
			push @urls, [ $line, $s, $t, $e, $i, \%typeinfo ];
		}
		
		print $fx "X $plain_msg\n" if $fx;
		trace_to_u8($line);
		hyperlink_replay_codes($line, \(@url_s, $plain_msg, @url_e), $ctrl_codes, \$a_link, $fx);
		$line->[LINE]{'message'} = $plain_msg;

		++$i;
	}
	$ACT_STR->[URLS] = \@urls;
	$ACT_STR->[A_LINK] = @{ $ACT_STR->[URLS] }
		if $ACT_STR->[A_LINK] < 0;
}

## copy_lines -- make a copy of downloaded lines (dumb dclone)
## $lines_ref - reference to copy
## returns a reference copy of the reference content
sub copy_lines {
	my ($lines_ref) = @_;
	my $lines_ref2 = [];
	push @$lines_ref2, [ +{%{$_->[LINE]}}, +{%{$_->[LAYOUT]}}, [@{$_->[TRACE]}] ]
		for @$lines_ref;
	$lines_ref2
}

## send_clip_external -- send clipboard to external app
## $text - text for clipboard
## $xterm_osc - xterm-compatible escape sequence
sub send_clip_external {
	my ($text, $xterm_osc) = @_;
	if (weechat::config_is_set_plugin('clipboard_command')) {
		my %presets = ( xsel => '|xsel -c', xclip => '|xclip' );
		my $external = weechat::config_get_plugin('clipboard_command');
		$external = $presets{$external} if exists $presets{$external};
		if ($external =~ /^\|/) {
			if (open my $ext, $external) {
				print $ext $text;
			}
			else {
				weechat::print('', weechat::prefix('error').'Clipboard: '.$!);
			}
		}
		elsif ($external =~ s/%q/\Q$text/ || $external =~ s/%x/\Q$xterm_osc/) {
			unless (system($external) >= 0) {
				weechat::print('', weechat::prefix('error').'Clipboard: '.$!);
			}
		}
		else {
			if ($external eq 'tmux') {
				unless (( system { $external } $external, 'deleteb' ) >= 0) {
					weechat::print('', weechat::prefix('error').'Clipboard: '.$!);
				}
				$external .= ' setb';
			}
			my @cmd = split ' ', $external;
			if (grep { $_ eq '%s' } @cmd) {
				@cmd = map { $_ eq '%s' ? $text : $_ } @cmd;
			}
			else {
				push @cmd, $text;
			}
			unless (( system { $cmd[0] } @cmd ) >= 0)  {
				weechat::print('', weechat::prefix('error').'Clipboard: '.$!);
			}
		}
	}
}

## send_clip -- send text to selection clipboard
## $text - text for clipboard
## $stor - storage unit (optional, default s0)
sub send_clip {
	my ($text, $stor) = @_;
	$stor = '' unless $stor;
	my $text_nu = $text;
	Encode::_utf8_off($text_nu);
	my $xterm_osc = "\e]52;$stor;".encode_base64($text_nu, '')."\a";
	my $compatible_terms = join '|', map { split /[,;]/ } split ' ',
		weechat::config_get_plugin('xterm_compatible');
	print STDERR $xterm_osc if $ENV{'TERM'} =~ /^xterm|$compatible_terms/;
	if ($ENV{'TMUX'}) {
		my @tmux_clients = `tmux lsc`;
		my $active_term;
		my $last_time = 0;
		for (@tmux_clients) {
			chomp;
			my ($path, $rest) = split ':', $_;
			next unless $rest =~ / (?:xterm|$compatible_terms)/;
			my $atime = -A $path;
			if ($last_time >= $atime) {
				$last_time = $atime;
				$active_term = $path;
			}
		}
		if ($active_term) {
			open my $pty, '>>', $active_term;
			print $pty $xterm_osc;
		}
	}	
	send_clip_external($text, $xterm_osc);
}

## hyperlink_to_clip -- send currently active link to clipboard
sub hyperlink_to_clip {
	if ($ACT_STR->[A_LINK] >= 0 && $ACT_STR->[A_LINK] < @{ $ACT_STR->[URLS] }) {
		my $url = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
		send_clip($url);
	}
}

## hyperlink_urlopen -- send url open signal for currently active link
sub hyperlink_urlopen {
	my $url = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
	send_clip($url, 's0x');
	weechat::hook_signal_send('urlopen', weechat::WEECHAT_HOOK_SIGNAL_STRING, $url);
}

## selection_to_clip -- send currently active selection to clipboard
sub selection_to_clip {
	if ($ACT_STR->[CUR][0*2] > -1 && $ACT_STR->[CUR][1*2] > -1) {
		my @range = sort { $a <=> $b } @{$ACT_STR->[CUR]}[0*2,1*2];
		my @lines = map { fu8on weechat::string_remove_color($_->[LINE]{'message'},'') } @{$ACT_STR->[LINES]}[$range[0]..$range[1]];
		my @prefixes = map { fu8on weechat::string_remove_color($_->[LINE]{'prefix'},'') } @{$ACT_STR->[LINES]}[$range[0]..$range[1]];
		my @cuts = map { $_->[1] } sort { $a->[0] <=> $b->[0] || $a->[1] <=> $b->[1] } ([@{$ACT_STR->[CUR]}[0*2,0*2+1]], [@{$ACT_STR->[CUR]}[1*2,1*2+1]]);
		$lines[0] = length $lines[0] >= $cuts[0] ? substr $lines[0], $cuts[0] : ''; #(substr outside of string?)
		$prefixes[0] = undef;# if $cuts[0];
		$lines[-1] = substr $lines[-1], 0, $range[0]==$range[1] ? $cuts[1]-$cuts[0] : $cuts[1];
		my $sel_text = join "\n", map { my $pfx = shift @prefixes; ($pfx ? "$pfx\t" : '') . $_ } @lines;
		send_clip($sel_text);
	}
}

## hyperlink_dispatch_input -- dispatch input from ** commands in hyperlink mode
## $args - input argument
## returns true value if processing is continued, false otherwise
sub hyperlink_dispatch_input {
	my ($args) = @_;
	if ($args eq '+') {
		++$ACT_STR->[A_LINK];
		$ACT_STR->[A_LINK] = 0
			if $ACT_STR->[A_LINK] > @{ $ACT_STR->[URLS] };
		until ($ACT_STR->[A_LINK] >= @{$ACT_STR->[URLS]}
				   || hyperlink_match_type_filter($ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO])) {
			++$ACT_STR->[A_LINK];
		}
		hyperlink_to_clip();
	}
	elsif ($args eq '-') {	
		--$ACT_STR->[A_LINK];
		until ($ACT_STR->[A_LINK] < 0
					 || hyperlink_match_type_filter($ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO])) {
			--$ACT_STR->[A_LINK];
		}
		$ACT_STR->[A_LINK] = @{ $ACT_STR->[URLS] }
			if $ACT_STR->[A_LINK] < 0;
		hyperlink_to_clip();
	}
	elsif ($args eq '!') {
		if ($ACT_STR->[A_LINK] >= 0 && $ACT_STR->[A_LINK] < @{ $ACT_STR->[URLS] }) {
			my $link_type = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO]{'type'};
			if ($link_type eq 'nick' || $link_type eq 'prefix') {
				my $nick = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
				if (Nlib::has_false_value(weechat::config_get_plugin('use_nick_menu'))) {
					weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/query $nick");
				}
				else {
					delayed_nick_menu($nick);
					close_copywin(); # XXX
				}
			}
			elsif ($link_type eq 'channel') {
				my $channel = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
				weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/join $channel");
			}
			else {
				hyperlink_urlopen();
			}
		}
		else {
			weechat::command($ACT_STR->[BUFPTR], '/input return');
		}
		return;
	}
	else {
		return;
	}
	1
}

## selection_dispatch_input -- dispatch input from ** commands in selectionmode
## $args - input argument
## returns true value if processing is continued, false otherwise
sub selection_dispatch_input {
	my ($args) = @_;
	if ($args eq '+') {
		++$ACT_STR->[CUR][0];
		$ACT_STR->[CUR][0] = -1 if $ACT_STR->[CUR][0] >= @{$ACT_STR->[LINES]};
	}
	elsif ($args eq '-') {	
		--$ACT_STR->[CUR][0];
		$ACT_STR->[CUR][0] = @{$ACT_STR->[LINES]}-1 if $ACT_STR->[CUR][0] < -1;
	}
	elsif ($args eq '>') {
		++$ACT_STR->[CUR][1];
		if ($ACT_STR->[CUR][0] < 0 && $ACT_STR->[CUR][1] < 0) {
			$ACT_STR->[CUR][1] = -1;
		}
		else {
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my $msglen = length $plain_msg;
			$ACT_STR->[CUR][1] = $msglen if $ACT_STR->[CUR][1] > $msglen;
		}
	}
	elsif ($args eq '<') {	
		--$ACT_STR->[CUR][1];
		if ($ACT_STR->[CUR][0] < 0) {
			$ACT_STR->[CUR][1] = -1 ;
		}
		elsif ($ACT_STR->[CUR][1] < 0) {
			$ACT_STR->[CUR][1] = 0;
		}
		else {
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my $msglen = length $plain_msg;
			$ACT_STR->[CUR][1] = $msglen-1 if $ACT_STR->[CUR][1] > $msglen;
		}
	}
	elsif ($args eq 'f') {
		if ($ACT_STR->[CUR][0] < 0) {
			$ACT_STR->[CUR][1] = -1 ;
		}
		else {
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my @breaks;
			push @breaks, @- while $plain_msg =~ /\b/g;
			$ACT_STR->[CUR][1] = (grep { $_ > $ACT_STR->[CUR][1] } @breaks)[0];
			unless (defined $ACT_STR->[CUR][1]) {
				my $msglen = length $plain_msg;
				$ACT_STR->[CUR][1] = $msglen;
			}
		}
	}
	elsif ($args eq 'b') {
		if ($ACT_STR->[CUR][0] < 0) {
			$ACT_STR->[CUR][1] = -1 ;
		}
		else {
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my @breaks;
			push @breaks, @- while $plain_msg =~ /\b/g;
			$ACT_STR->[CUR][1] = (grep { $_ < $ACT_STR->[CUR][1] } @breaks)[-1];
			unless (defined $ACT_STR->[CUR][1]) {
				$ACT_STR->[CUR][1] = 0;
			}
		}
	}
	elsif ($args eq 'e') {
		if ($ACT_STR->[CUR][0] < 0) {
			$ACT_STR->[CUR][1] = -1 ;
		}
		else {
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my $msglen = length $plain_msg;
			$ACT_STR->[CUR][1] = $msglen;
		}
	}
	elsif ($args eq 'a') {
		if ($ACT_STR->[CUR][0] < 0) {
			$ACT_STR->[CUR][1] = -1 ;
		}
		else {
			$ACT_STR->[CUR][1] = 0;
		}
	}
	elsif ($args eq '@') {
		if ($ACT_STR->[CUR][2] > -1) {
			@{$ACT_STR->[CUR]}[2,3] = (-1, -1);
		}
		else {
			@{$ACT_STR->[CUR]}[2,3] = @{$ACT_STR->[CUR]}[0,1];
		}
	}
	else {
		return;
	}
	if ($args =~ /^[><+fbea-]$/) {
		selection_to_clip();
	}
	1
}

## selection_replay_codes -- insert marker codes, reinsert control codes into plain msg
## $line - line with trace data to adjust
## $sel_s - start position of selection
## $msg_r - reference to message where positions apply
## $sel_e - end position of selection
## $ctrl - capture_color_codes result of control codes
## $cup - cursor position
## $fx - debug file handle
sub selection_replay_codes {
	my ($line, $sel_s, $msg_r, $sel_e, $ctrl, $cup, $fx) = @_;
	my @cup = grep { $_ > -1 } ($cup);

	my $se = join '', map { weechat::color($_) } split '[.]',
		weechat::config_get_plugin('color.selection');

	my $cu = join '', map { weechat::color($_) } split '[.]',
		weechat::config_get_plugin('color.selection_cursor');

	my @starts = grep { $_ > -1 } sort { $a <=> $b } ($sel_s, $cup);
	my @ends = grep { $_ > -1 } sort { $a <=> $b } ($sel_e, $cup+1);

	my $last_seq_s;

	print $fx "s<@starts> e<@ends> sel_s:$sel_s sel_e:$sel_e cup:$cup\n" if $fx;

	my $max_loop = 2*( @{$ctrl->[POS_S]} + @starts + @ends );
	while (@{$ctrl->[POS_S]} || @starts || @ends) {
		#if (@starts && $starts[0] <= $ends[0] && (!@{$ctrl->[POS_S]} || $starts[0] <= $ctrl->[POS_S][0])) #urlonly
		if (@starts && $starts[0] < $ends[0] && (!@{$ctrl->[POS_S]} || $starts[0] <= $ctrl->[POS_S][0])) {
			$last_seq_s = $starts[0];
			hyperlink_replay_code1($line, $msg_r, (@cup && $starts[0] == $cup[0] ? \$cu : \$se), 0,
				\@starts, \@ends, \@cup, @{$ctrl}[POS_S,POS_E], $fx, 'S');
		}
		elsif (@ends && (!@{$ctrl->[POS_S]} || $ends[0] <= $ctrl->[POS_S][0])) {
			my $active1 = weechat::color('reset');
			if (defined $last_seq_s) {
				# get part of message constructed thus far, and remove starting bracket
				my $msg_part1 = substr $$msg_r, 0, $ends[0];
				substr $msg_part1, $last_seq_s, length (@cup && $last_seq_s == $cup[0] ? $cu : $se), '';
				$active1 .= repeat_control_codes($msg_part1);
				$last_seq_s = undef;
			}
			hyperlink_replay_code1($line, $msg_r, \$active1, 1,
				\@ends, \@starts, \@cup, @{$ctrl}[POS_S,POS_E], $fx, 'E');
		}
		else { # ($ctrl->[POS_S][0] <= $starts[0] && $ctrl->[POS_S][0] <= $ends[0])
			my $ip = $ctrl->[POS_E][0];
			my $needs_fixup = defined $last_seq_s && $ctrl->[RES][0] =~ weechat::color('reset');
			hyperlink_replay_code2($ctrl, $msg_r, \@starts, \@ends, \@cup, $fx, 'C');
			if ($needs_fixup) {
				$last_seq_s = $ip;
				hyperlink_replay_code1($line, $msg_r, (@cup && $last_seq_s == $cup[0] ? \$cu : \$se), 0,
				[$ip], \@starts, \@ends, \@cup, @{$ctrl}[POS_S,POS_E], $fx, 'F');
			}
		}
		--$max_loop; die 'endless loop' if $max_loop < 0;
	}
}

## selection_function -- select text with cursor
## $lines_ref - downloaded lines
sub selection_function {
	my ($lines_ref) = @_;
	$ACT_STR->[CUR] = [ -1, -1, -1, -1 ] unless defined ${$ACT_STR}[CUR];
	my $cur = $ACT_STR->[CUR];
	my $lineno = 0;
	my $fx;
	#open $fx, '>', ...;
	print $fx "cur: @$cur\n" if $fx;
	for my $line (@$lines_ref) {
		my $msg = fu8on $line->[LINE]{'message'};
		my ($ctrl_codes, $plain_msg) = capture_color_codes($msg);
		my ($sel_s, $sel_e) = (-1, -1);
		my $lcur = $cur->[0*2] == $lineno ? $cur->[0*2+1] : -2;
		my $msglen = length $plain_msg;
		$lcur = -1+$msglen if $lcur >= $msglen;
		if ($cur->[0*2] > -1 && $cur->[1*2] > -1) { # we have a selection
			if ($cur->[0*2] < $cur->[1*2]) { # cursor is on line before selection
				if ($cur->[0*2] == $lineno) {
					#($sel_s, $sel_e) = ($cur->[0*2+1]+1, $msglen);
					($sel_s, $sel_e) = ($lcur+1, $msglen);
				}
				elsif ($cur->[0*2] < $lineno && $cur->[1*2] > $lineno) {
					($sel_s, $sel_e) = ('0 but true', $msglen);
				}
				elsif ($cur->[1*2] == $lineno) {
					($sel_s, $sel_e) = ('0 but true', $cur->[1*2+1]);
				}
			}
			elsif ($cur->[0*2] > $cur->[1*2]) { # cursor is on line after selection
				if ($cur->[0*2] == $lineno) {
					($sel_s, $sel_e) = ('0 but true', $cur->[0*2+1]);
				}
				elsif ($cur->[0*2] > $lineno && $cur->[1*2] < $lineno) {
					($sel_s, $sel_e) = ('0 but true', $msglen);
				}
				elsif ($cur->[1*2] == $lineno) {
					($sel_s, $sel_e) = ($cur->[1*2+1], $msglen);
				}
			}
			elsif ($cur->[0*2] == $lineno && $cur->[1*2] == $lineno) { # cursor is on same line as selection
				if ($cur->[0*2+1] < $cur->[1*2+1]) {
					($sel_s, $sel_e) = ($cur->[0*2+1]+1, $cur->[1*2+1]);
				}
				elsif ($cur->[0*2+1] > $cur->[1*2+1]) {
					($sel_s, $sel_e) = ($cur->[1*2+1], $cur->[0*2+1]);
				}
				else {
					($sel_s, $sel_e) = ($cur->[0*2+1], $cur->[0*2+1]+1);
					$lcur = -2;
				}
			}
		}
		if ($sel_s && $sel_s == 0) {
			$sel_s+=0;
			my $hl = weechat::color('reverse');
			my $HL = weechat::color('-reverse');
			if ($line->[LINE]{'prefix'}) {
				my $ctrl = capture_color_codes(fu8on $line->[LINE]{'prefix'});
				substr $line->[LINE]{'prefix'}, $ctrl->[POS_E][-2], 0, $hl;
				substr $line->[LINE]{'prefix'}, $ctrl->[POS_E][-1]+length $hl, 0, $HL;
			}
		}
		$sel_e = $msglen if $sel_e > $msglen;
		($sel_s, $sel_e) = (-1, -1)
			if $sel_s == $sel_e;
		trace_to_u8($line);
		selection_replay_codes($line, $sel_s, \$plain_msg, $sel_e, $ctrl_codes, $lcur, $fx);
		$line->[LINE]{'message'} = $plain_msg;
		++$lineno;
	}
}

## switchmode -- toggle between modes
sub switchmode {
	$ACT_STR->[MODE] = $ACT_STR->[MODE] eq 'hyperlink' ? 'selection' : 'hyperlink';
	my ($r_, $R_) = (weechat::color('reverse'), weechat::color('-reverse'));
	my $I = '▐';
	my $t_flt = hyper_get_valid_keys('t');
	$t_flt =~ s/$_/$_/i for split '', $ACT_STR->[URL_TYPE_FILTER];
	weechat::buffer_set($ACT_STR->[BUFPTR], 'title',
		($ACT_STR->[MODE] eq 'hyperlink' ?
		    $r_.' ↑ ↓'.$R_.'move to url'.
			$I.$r_.'RET' .$I.$R_.'send open'.
			$I.$r_.'/'   .$I.$R_.'sel.mode'.
			$I.$r_.$t_flt.$I.$R_.
			$I.$r_.'q'   .$I.$R_.'close'
						:
		    $r_.'←↑→↓'.$R_.'move cursor'.
			$I.$r_.'SPC'   .$I.$R_.'start selection'.
			$I.$r_.'/'     .$I.$R_.'url mode'.
			$I.$r_.'q'     .$I.$R_.'close').' '.
		$r_.$I.$R_.
			 weechat::buffer_get_string($ACT_STR->[WINDOWS]{'buffer'}, 'short_name').
		$I);
}

## apply_keybindings -- set up key bindings for copy buffer
sub apply_keybindings {
	my @wee_keys = Nlib::i2h('key');
	my @keys;
	my $custom_keys = weechat::config_get_plugin('copywin_custom_keys');
	my %custom_keys;
	if ($custom_keys) {
	    %custom_keys = ('' => split /(\S+):/, $custom_keys);
	    for (keys %custom_keys) {
		$custom_keys{$_} = [ grep { length } split ' ', $custom_keys{$_} ];
	    }
	}
	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_previous' ||
			   $_->{'command'} eq '/input history_global_previous' } @wee_keys;
	@keys = 'meta2-A' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **-') for @keys, @{$custom_keys{'-'}//[]}; # up arrow

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input history_next' ||
			   $_->{'command'} eq '/input history_global_next' } @wee_keys;
	@keys = 'meta2-B' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **+') for @keys, @{$custom_keys{'+'}//[]}; # down arrow

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_next_char' } @wee_keys;
	@keys = 'meta2-C' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **>') for @keys, @{$custom_keys{'>'}//[]}; # right arrow

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_previous_char' } @wee_keys;
	@keys = 'meta2-D' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **<') for @keys, @{$custom_keys{'<'}//[]}; # left arrow

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_next_word' } @wee_keys;
	@keys = 'meta-f' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **f') for @keys, @{$custom_keys{f}//[]}; # back word

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_previous_word' } @wee_keys;
	@keys = 'meta-b' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **b') for @keys, @{$custom_keys{b}//[]}; # forward word

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_end_of_line' } @wee_keys;
	@keys = 'ctrl-E' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **e') for @keys, @{$custom_keys{e}//[]};

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input move_beginning_of_line' } @wee_keys;
	@keys = 'ctrl-A' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **a') for @keys, @{$custom_keys{a}//[]};

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} eq '/input return' || $_->{'command'} eq '/input magic_enter' } @wee_keys;
	@keys = 'ctrl-M' unless @keys;
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **!') for @keys, @{$custom_keys{'!'}//[]}; # enter key

	@keys = ('ctrl-@', ' ');
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **@') for @keys, @{$custom_keys{'@'}//[]}; # ctrl+space or ctrl+@

	for my $cmd (@SIMPLE_MODE_KEYS) {
	    weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **'.$cmd) for $cmd, @{$custom_keys{$cmd}//[]};
	}

	@keys = map { $_->{'key'} }
		grep { $_->{'command'} =~ "^/@{[CMD_COPYWIN]}" } @wee_keys;
	push @keys, 'q' unless @{$custom_keys{q}//[]};
	weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **q') for @keys, @{$custom_keys{q}//[]};
}

## binding_mouse_fix -- disable one key bindings on mouse input
## () - signal handler
## $data - signal has true value if mouse input in progress, false if mouse input finished
sub binding_mouse_fix {
	my (undef, undef, $data) = @_;
	return weechat::WEECHAT_RC_OK unless $ACT_STR && $ACT_STR->[BUFPTR] && weechat::current_buffer() eq $ACT_STR->[BUFPTR];
	my $custom_keys = weechat::config_get_plugin('copywin_custom_keys');
	my %custom_keys;
	if ($custom_keys) {
	    %custom_keys = ('' => split /(\S+):/, $custom_keys);
	    for (keys %custom_keys) {
		$custom_keys{$_} = [ grep { length } split ' ', $custom_keys{$_} ];
	    }
	}
	if ($data) {
	    weechat::buffer_set($ACT_STR->[BUFPTR], "key_unbind_$_", '') for ' ', @SIMPLE_MODE_KEYS, 'q',
		    grep { 1 == length } map { @$_ } values %custom_keys;
	}
	else {
		weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **@') for ' ';
		weechat::buffer_set($ACT_STR->[BUFPTR], 'key_bind_/', '/'.CMD_COPYWIN.' **/');
		for my $cmd (@SIMPLE_MODE_KEYS) {
		    weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **'.$cmd) for $cmd, grep { 1 == length } @{$custom_keys{$cmd}//[]};
		}
		for my $cmd (split //, '@!aebf<>+-/') {
		    weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **'.$cmd) for grep { 1 == length } @{$custom_keys{$cmd}//[]};
		}
		if (@{$custom_keys{q}//[]}) {
		    weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_$_", '/'.CMD_COPYWIN.' **q') for @{$custom_keys{q}//[]};
		}
		else {
		    weechat::buffer_set($ACT_STR->[BUFPTR], "key_bind_q", '/'.CMD_COPYWIN.' **q');
		}
	}
	weechat::WEECHAT_RC_OK
}

## hyper_get_valid_keys -- get keys for type filter according to enabled settings
## $res - 't' for title, 'u' for upcase
sub hyper_get_valid_keys {
	my ($res) = @_;
	$res = '' unless defined $res;
	my $title = $res eq 't';
	my $uc = $res eq 'u';
	my $keys = 'u';
	$keys .= 'n' if Nlib::has_true_value(weechat::config_get_plugin('hyper_nicks'));
	$keys .= 'c' if Nlib::has_true_value(weechat::config_get_plugin('hyper_channels'));
	$keys .= 'p' if Nlib::has_true_value(weechat::config_get_plugin('hyper_prefix'));
	$keys = uc $keys if $title || $uc;
	if ($title) {
		length $keys == 1 ? " $keys  " :
			length $keys == 2 ? (substr $keys, 0, 1).' '.(substr $keys, 1).' ' :
				length $keys == 3 ? "$keys " :
					$keys;
	}
	else {
		$keys = "[$keys]";
		qr/^$keys$/;
	}
}

## hyper_set_type_filter -- sets the type of links shown in url view based on setting and args
## $args - command line arguments
## returns new args
sub hyper_set_type_filter {
	my ($args) = @_;
	my $valid_keys = hyper_get_valid_keys();
	$ACT_STR->[URL_TYPE_FILTER] = join '',
		keys %{+{ map { $_ => undef } grep { /$valid_keys/ } map { lc substr $_, 0, 1 } map { split /[,;]/ } split ' ',
				  weechat::config_get_plugin('hyper_show') }};
	$args = '' unless defined $args;
	my $urlfilter = $args;
	if ($urlfilter =~ s/^\/// && length $urlfilter) {
		$args = '/';
		$ACT_STR->[URL_TYPE_FILTER] = join '',
			keys %{+{ map { $_ => undef } grep { /$valid_keys/ } map { lc } split '', $urlfilter }};
	}
	elsif (length $urlfilter) {
		$ACT_STR->[URL_TYPE_FILTER] = join '',
			keys %{+{ map { $_ => undef } grep { /$valid_keys/ } map { lc substr $_, 0, 1 }
						  map { split /[,;]/ } split ' ', $urlfilter }};
		$args = '/' if length $ACT_STR->[URL_TYPE_FILTER];
	}
	$ACT_STR->[URL_TYPE_FILTER] = 'u' unless length $ACT_STR->[URL_TYPE_FILTER];
	$args
}

## make_new_copybuf -- creates a new copywin buffer from the current window
## $args - arguments to command, can set mode
sub make_new_copybuf {
	my ($args) = @_;
	my $winptr = weechat::current_window();
	my ($wininfo) = Nlib::i2h('window', $winptr);

	my $copybuf = weechat::buffer_new('['.$wininfo->{'width'}.'x'.$wininfo->{'height'}.
									  '+'.$wininfo->{'x'}.'+'.$wininfo->{'y'}.']',
									  '', '', '', '');
	# apply scroll keeping to current buffer if possible
	weechat::hook_signal_send('buffer_sk', weechat::WEECHAT_HOOK_SIGNAL_POINTER, $copybuf);
	$STR{$copybuf} = $ACT_STR = [ $copybuf ];
	$ACT_STR->[LINES] = download_lines($wininfo);	
	$ACT_STR->[WINDOWS] = $wininfo;
	unless ($copybuf) {
		$ACT_STR->[MODE] = 'FAIL';
		return;
	}
	$ACT_STR->[MODE] = 'hyperlink';
	$args = hyper_set_type_filter($args);
	weechat::buffer_set($copybuf, 'short_name', weechat::config_get_plugin('copybuf_short_name')) if $copybuf;
	weechat::buffer_set($copybuf, 'type', 'free');
	apply_keybindings();
	switchmode();
	switchmode() if $args eq '/';
}

sub copywin_cmd {
	my (undef, $bufptr, $args, $int) = @_;

	if ($int) {
	}
	elsif ($args =~ s/^\*\*//) {
		return weechat::WEECHAT_RC_OK unless exists $STR{$bufptr};
		$ACT_STR = $STR{$bufptr};
		if ($args eq 'q') {
			weechat::buffer_close($ACT_STR->[BUFPTR]);
			return weechat::WEECHAT_RC_OK;
		}
		elsif ($args eq '/') {
			hyper_set_type_filter()
				unless length $ACT_STR->[URL_TYPE_FILTER];
			switchmode();
		}
		elsif ($args =~ hyper_get_valid_keys()) {
			switchmode() if $ACT_STR->[MODE] eq 'hyperlink';
			$ACT_STR->[URL_TYPE_FILTER] = $args;
			switchmode();
		}
		elsif ($args =~ hyper_get_valid_keys('u')) {
			switchmode() if $ACT_STR->[MODE] eq 'hyperlink';
			my $t = lc $args;
			$ACT_STR->[URL_TYPE_FILTER] .= $t
				unless $ACT_STR->[URL_TYPE_FILTER] =~ s/$t//;
			switchmode() if length $ACT_STR->[URL_TYPE_FILTER];
		}
		elsif ($ACT_STR->[MODE] eq 'hyperlink') {
			return weechat::WEECHAT_RC_OK
				unless hyperlink_dispatch_input($args);
		}
		else {
			return weechat::WEECHAT_RC_OK
				unless selection_dispatch_input($args);			
		}
	}
	elsif ($args =~ /^\s*help\s*$/i) {
		Nlib::read_manpage(SCRIPT_FILE, SCRIPT_NAME);
		return weechat::WEECHAT_RC_OK
	}
	else {
		check_layout()
			unless $LAYOUT_OK;
		make_new_copybuf($args);
	}
	
	my $wininfo = $ACT_STR->[WINDOWS];
	my $lines_ref2 = copy_lines($ACT_STR->[LINES]);
	my $copybuf = $ACT_STR->[BUFPTR];

	if ($ACT_STR->[MODE] eq 'hyperlink') {
		hyperlink_function($lines_ref2);
	}
	elsif ($ACT_STR->[MODE] eq 'selection') {
		selection_function($lines_ref2);
	}


	my $printy = calc_free_image($wininfo, $lines_ref2);

	for my $i (0..$#$printy) {
		weechat::print_y($copybuf, $i, $printy->[$i]);
	}

	weechat::buffer_set($copybuf, 'display', 'auto');
	weechat::WEECHAT_RC_OK
}

sub real_screen {
	my ($screen_cursor, $text) = @_;
	my $l = length $text;
	for (my ($i, $j) = (0, 0); $i < $l; ++$i) {
		$j += screen_length(substr $text, $i, 1);
		return $i if $j > $screen_cursor;
	}
	$l
}

## mouse_coords_to_cursor -- calculate in line cursor according to rendering
## $r - local (in window) row of mouse cursor
## $c - local (in window) column of mouse cursor
## returns line index and position in plain text if found
sub mouse_coords_to_cursor {
	my ($r, $c) = @_; # wanted row & column

	my $wininfo = $ACT_STR->[WINDOWS];
	my $lines_ref = copy_lines($ACT_STR->[LINES]);

	my ($i, $l, $p) = (1, 0, 0); # current row, current line index, current line position
	my $first_line = $wininfo->{'start_line_pos'};
	my $prev_line;
	for my $line (@$lines_ref) {
		trace_to_u8($line);
		my $max_length = [(length fu8on $line->[LINE]{'message'}),''];
		my @splits = ([0,''], message_splits($line), $max_length, $max_length);
		for (0 .. $line->[LAYOUT]{'count'}-1) {
			shift @splits if $splits[0][0] - $splits[1][0] >= 0;
			last if $i > $wininfo->{'chat_height'};
			my $subm = substr $line->[LINE]{'message'}, $splits[0][0], $splits[1][0]-$splits[0][0];
			my $subm_u = fu8on weechat::string_remove_color($subm, '');
			my $subm_length = length $subm_u;
			if ($_ >= $first_line) {
				if ($r == $i) {
					my $subm_length_screen = screen_length $subm_u;
					my $construction = '';
					unless ($_) {
						show_time($line, \$construction);
						return ($l, undef, 'time')
							if (screen_length fu8on weechat::string_remove_color($construction, '')) >= $c;
						show_buffername($line, \$construction);
						return ($l, undef, 'buffername')
							if (screen_length fu8on weechat::string_remove_color($construction, '')) >= $c;
						show_prefix($line, \$construction, $prev_line);
						return ($l, undef, 'prefix')
							if (screen_length fu8on weechat::string_remove_color($construction, '')) >= $c;
						$prev_line = $line if exists $line->[LINE]{'date'};
					}
					show_separator($line, \$construction, $_);
					my $message_start_screen = screen_length fu8on weechat::string_remove_color($construction, '');
					return ($l) if $message_start_screen >= $c;
					if ($splits[0][1] =~ /[bn]/ && $subm =~ s/^( +)//) {
						my $l = length $1;
						$p += $l;
						$subm_u = substr $subm_u, $l;
					}
					if ($subm_length_screen >= $c - 1 - $message_start_screen) {
						return ($l, $p + real_screen($c - 1 - $message_start_screen, $subm_u));
					}
				}
				++$i;
			}
			$p += $subm_length;
			shift @splits;
		}
		$first_line = 0;
		++$l; $p = 0;
	}
}

## copywin_autoclose -- close copywin buffer
## () - this small function is a timer handler
sub copywin_autoclose {
	weechat::buffer_close($ACT_STR->[BUFPTR])
			if $ACT_STR && $ACT_STR->[MOUSE_AUTOMODE];
	$autoclose_in_progress = undef;
	weechat::WEECHAT_RC_OK
}

## get_autoclose_delay -- checks delay for autoclose of copywin buffer
## returns delay or false if autoclose is disabled
sub get_autoclose_delay {
	my $autoclose_delay = weechat::config_get_plugin('mouse.close_on_release');
	if (Nlib::has_false_value($autoclose_delay)) { 0 }
	elsif ($autoclose_delay =~ /\D/ || $autoclose_delay < 100) { 100 }
	else { $autoclose_delay }
}

## get_2nd_click_delay -- checks additional delay for autoclose of copywin buffer if 2nd click is needed to open url
## returns additional delay
sub get_2nd_click_delay {
	my $conf_2nd_click_delay = weechat::config_get_plugin('mouse.url_open_2nd_click');
	if (Nlib::has_false_value($conf_2nd_click_delay)) { 0 }
	elsif ($conf_2nd_click_delay =~ /\D/) { 2000 }
	else { $conf_2nd_click_delay }
}

## get_nick_2nd_click_delay -- checks additional delay for autoclose of copywin buffer if 2nd click is needed to query nick
## returns additional delay
sub get_nick_2nd_click_delay {
	my $conf_2nd_click_delay = weechat::config_get_plugin('mouse.nick_2nd_click');
	if (Nlib::has_false_value($conf_2nd_click_delay)) { 0 }
	elsif ($conf_2nd_click_delay =~ /\D/) { 500 }
	else { $conf_2nd_click_delay }
}

## mouse_window_at_pointer -- switch to window where clicked
## $row - mouse row
## $col - mouse column
## $wininfo - currently active window info
## returns true value if successful
sub mouse_window_at_pointer {
	my ($row, $col, $wininfo) = @_;
	my @all_windows = Nlib::i2h('window');
	my $in_any_win;
	for (@all_windows) {
		$in_any_win = $_ if Nlib::in_window($row, $col, $_);
	}
	return unless $in_any_win;
	my $steps = 0;
	for (@all_windows) {
		weechat::command('', '/window +1');
		++$steps;
		last if weechat::current_window() eq $in_any_win->{'pointer'};
	}
	my ($act_win_ind) = map { $_->[0] }
		grep { $_->[-1]{'pointer'} eq $wininfo->{'pointer'} }
			do {
				my $i = 0;
				map { [ $i++, $_ ] } @all_windows
			};
	my ($click_win_ind) = map { $_->[0] }
		grep { $_->[-1]{'pointer'} eq $in_any_win->{'pointer'} }
			do {
				my $i = 0;
				map { [ $i++, $_ ] } @all_windows
			};
	#weechat::print('',"steps:$steps, a:$act_win_ind, c:$click_win_ind, d:@{[$act_win_ind-$click_win_ind]}/@{[$click_win_ind-$act_win_ind]} #:".scalar @all_windows);
	1
}

## mouse_scroll_action -- handle mouse scroll
## () - signal passed on from mouse event handler
## $_[2] - mouse code
## $row - mouse row
## $col - mouse column
sub mouse_scroll_action {
	my (undef, undef, undef, $row, $col) = @_;
	return weechat::WEECHAT_RC_OK unless Nlib::has_true_value(weechat::config_get_plugin('mouse.handle_scroll'));

	my $winptr = weechat::current_window();
	my ($wininfo) = Nlib::i2h('window', $winptr);

	my $had_to_switch_win;

	unless (Nlib::in_window($row, $col, $wininfo)) {
		if (Nlib::has_true_value(weechat::config_get_plugin('mouse.scroll_inactive_pane'))) {
			return weechat::WEECHAT_RC_OK
				unless mouse_window_at_pointer($row, $col, $wininfo);
			$had_to_switch_win = $winptr;
			$winptr = weechat::current_window();
			($wininfo) = Nlib::i2h('window', $winptr);
		}
		else {
			if ($_[2] =~ /^`/) { weechat::command('', '/window scroll_up'); } #`
			elsif ($_[2] =~ /^a/) { weechat::command('', '/window scroll_down'); }			
		}
	}

	if (Nlib::in_window($row, $col, $wininfo)) {
		if (Nlib::in_chat_window($row, $col, $wininfo)) {
			if ($_[2] =~ /^`/) { weechat::command('', '/window scroll_up'); } #`
			elsif ($_[2] =~ /^a/) { weechat::command('', '/window scroll_down'); }
		}
		elsif (my $bar_infos = Nlib::find_bar_window($row, $col)) {
			my $dir = $bar_infos->[-1]{'filling_'.
		   			 ($bar_infos->[-1]{'position'} <= 1 ?
					  'top_bottom' : 'left_right')} ? 'y' : 'x';
			if ($_[2] =~ /^`/) { $dir .= '-' } #`
			elsif ($_[2] =~ /^a/) { $dir .= '+' }
			for ($bar_infos->[-1]{'name'}) {
				weechat::command('', '/bar scroll '.$_.' * '.$dir.'10%')
						if ($_ eq 'title' or $_ eq 'status' or $_ eq 'nicklist')
			}
		}
	}

	if ($had_to_switch_win) {
		my $steps = 0;
		for (Nlib::i2h('window')) {
			weechat::command('', '/window +1');
			++$steps;
			last if weechat::current_window() eq $had_to_switch_win;
		}
	}
	weechat::WEECHAT_RC_OK
}

## drag_speed_hack -- delay drag events
## () - timer handler
sub drag_speed_hack {
	$drag_speed_timer = undef;
	mouse_evt(undef, undef, $_[0]);
	weechat::WEECHAT_RC_OK
}

sub input_text_hlsel {
	my (undef, undef, $bufptr, $text) = @_;
	return $text unless defined $input_sel && $input_sel->[0] eq $bufptr;
	my ($ctrl_codes, $plain_msg) = capture_color_codes($text);
	my $npos = weechat::buffer_get_integer($bufptr, 'input_pos');
	my ($sel_s, $sel_e) = sort { $a <=> $b } ($npos, $input_sel->[-1]);
	return $text unless $sel_s < $sel_e;
	selection_replay_codes([[]], $sel_s, \$plain_msg, $sel_e, $ctrl_codes, -2);
	$plain_msg
}

sub window_of_bar {
	my ($barinfo) = @_;
	my @all_windows = Nlib::i2h('window');
	my $in_any_win;
	for (@all_windows) {
		$in_any_win = $_ if Nlib::in_window(1+$barinfo->[0]{'y'}, 1+$barinfo->[0]{'x'}, $_);
	}
	$in_any_win
}

## mouse_input_sel -- mouse select in input bar
## () - signal passed on from mouse event handler
## $_[2] - mouse code
## $row - mouse row
## $col - mouse column
sub mouse_input_sel {
	my (undef, undef, undef, $row, $col) = @_;
	my $plain;
	if (my $bar_infos = Nlib::find_bar_window($row, $col)) {
		if ($bar_infos->[-1]{'name'} eq 'input') {
			my $win = window_of_bar($bar_infos);
			my ($error, $idx, $content, $coords) = Nlib::bar_item_get_subitem_at
				($bar_infos, 'input_text', $col - $bar_infos->[0]{'x'}, $row - $bar_infos->[0]{'y'});
			if ($coords) {
				my $col_pos = $coords->[1]-$coords->[0] + ($coords->[4]-$coords->[3])*$bar_infos->[0]{'width'};
				$plain = fu8on weechat::string_remove_color($content, '');
				$input_sel = [ $win->{'buffer'}, real_screen($col_pos, $plain) ];
			}
			elsif ($error eq 'outside') {
				$plain = fu8on weechat::string_remove_color($content, '');
				$input_sel = [ $win->{'buffer'}, length $plain ];
			}
		}
	}
	if (defined $plain) {
		if ($_[2] =~ /^ /) {
			weechat::buffer_set($input_sel->[0], 'input_pos', $input_sel->[-1]);
		}
		else {
			my $npos = weechat::buffer_get_integer($input_sel->[0], 'input_pos');
			my ($sel_s, $sel_e) = sort { $a <=> $b } ($npos, $input_sel->[-1]);
			send_clip((substr $plain, $sel_s, $sel_e-$sel_s))
				if $sel_s < $sel_e;
		}
	}
	$input_sel = undef if $_[2] =~ /^#/;
}

## mouse_click_into_copy -- click when not in copy mode
## () - signal passed on from mouse event handler
## $_[2] - mouse code
## $row - mouse row
## $col - mouse column
## returns true value if copy mode should be turned on
sub mouse_click_into_copy {
	my (undef, undef, undef, $row, $col) = @_;

	mouse_input_sel(@_[0..2], $row, $col);
	return unless $_[2] =~ /^ /;

	my $winptr = weechat::current_window();
	my ($wininfo) = Nlib::i2h('window', $winptr);

	unless (Nlib::in_window($row, $col, $wininfo)) {
		return unless Nlib::has_true_value(weechat::config_get_plugin('mouse.click_select_pane'));
		return unless mouse_window_at_pointer($row, $col, $wininfo);
		$winptr = weechat::current_window();
		($wininfo) = Nlib::i2h('window', $winptr);
		return unless Nlib::has_true_value(weechat::config_get_plugin('mouse.click_through_pane'));
	}
	return unless Nlib::has_true_value(weechat::config_get_plugin('mouse.copy_on_click'));
	return unless Nlib::in_chat_window($row, $col, $wininfo);
	1
}

## mouse_delay_drag -- delay drag events
## () - signal passed on from mouse event handler
## $_[2] - mouse code
## returns true if this event should be delayed
sub mouse_delay_drag {
	my $drag_speed = weechat::config_get_plugin('mouse.drag_speed');
	unless (Nlib::has_false_value($drag_speed)) {
		$drag_speed = 50 if $drag_speed =~ /\D/;
		weechat::unhook($drag_speed_timer) if defined $drag_speed_timer;
		$drag_speed_timer = weechat::hook_timer($drag_speed, 0, 1, 'drag_speed_hack', $_[2]);
		return 1;
	}
	undef
}

## delayed_nick_menu -- open the nick menu
## () - timer handler
sub delayed_nick_menu {
	$delayed_nick_menu_timer = undef;
	weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/menu nick $_[0]")
			if $ACT_STR && Nlib::i2h('hook', '', 'command,menu');
	weechat::WEECHAT_RC_OK
}

## mouse_evt -- handle mouse clicks
## () - signal handler
## $_[2] - mouse code
sub mouse_evt {
	Encode::_utf8_on($_[2]);

	my $this_last_mouse_seq = $last_mouse_seq || '';
	if ($_[1] && $this_last_mouse_seq =~ /^@/ && $_[2] =~ /^@/) {
		return weechat::WEECHAT_RC_OK if mouse_delay_drag(@_[0..2])
	}
	$last_mouse_seq = $_[2];

	#return weechat::WEECHAT_RC_OK unless defined $ACT_STR && $ACT_STR->[BUFPTR] eq weechat::current_buffer();
	
	my $curbufptr = weechat::current_buffer();

    if ($_[2] =~ /^[#@ `a](.)(.)$/) {
        my $row = ord($2)-32;
		my $col = ord($1)-32;

		weechat::unhook($delayed_nick_menu_timer) if defined $delayed_nick_menu_timer;
		$delayed_nick_menu_timer = undef;

		return mouse_scroll_action(@_[0..2], $row, $col) if $_[2] =~ /^[`a]/;

		if (!defined $ACT_STR || $ACT_STR->[BUFPTR] ne $curbufptr) {
			return weechat::WEECHAT_RC_OK
				unless mouse_click_into_copy(@_[0..2], $row, $col);
			copywin_cmd(undef, $curbufptr, '/');
			return weechat::WEECHAT_RC_OK unless $ACT_STR->[BUFPTR] eq weechat::current_buffer();
			$ACT_STR->[MOUSE_AUTOMODE] = 1;
		}
		$ACT_STR->[CUR] = [ -1, -1, -1, -1 ] unless defined ${$ACT_STR}[CUR];

		my $winptr = weechat::current_window();
		my ($wininfo) = Nlib::i2h('window', $winptr);
		return weechat::WEECHAT_RC_OK unless Nlib::in_chat_window($row, $col, $wininfo);

		my $lrow = $row - $wininfo->{'chat_y'};
		my $lcol = $col - $wininfo->{'chat_x'};
		#weechat::print_y($ACT_STR->[BUFPTR], $lrow-1, ' 'x($lcol-1).'x'.$lrow.'/'.$lcol);
		my @cursor = mouse_coords_to_cursor($lrow, $lcol);
		#weechat::print($ACT_STR->[WINDOWS]{'buffer'}, 'cursor: '.join ',', map { defined $_ ? $_ : '?' } @cursor );

		my $one_click;
		if (@cursor == 3 && $cursor[2] eq 'prefix' &&
				$this_last_mouse_seq =~ /^ / && $_[2] =~ /^#/ &&
					((substr $this_last_mouse_seq, 1) eq (substr $_[2], 1))) { # click

			my @link = grep { $_->[-1][URL_LINE] == $cursor[LINE] &&
								  $_->[-1][URL_S] == -1 && $_->[-1][URL_E] == -1 }
				do {
					my $i = 0;
					map { [ $i++, $_ ] } @{$ACT_STR->[URLS]}
				};

			if (@link == 1) {
				$ACT_STR->[A_LINK] = $link[0][0];
				my $t = substr $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO]{'type'}, 0, 1;
				unless ($ACT_STR->[URL_TYPE_FILTER] =~ $t) {
					switchmode();
					$ACT_STR->[URL_TYPE_FILTER] = $t;
					switchmode();
				}
			}
			if ($ACT_STR->[MODE] eq 'hyperlink' && @link == 1) {
				hyperlink_to_clip();

				my ($nick) = grep { /^nick_/ } @{ $ACT_STR->[LINES][$cursor[LINE]][LINE]{'tag'} };
				if (defined $nick && $nick =~ s/^nick_//) {
					if (Nlib::has_false_value(weechat::config_get_plugin('mouse.nick_2nd_click'))) {
						delayed_nick_menu($nick);
					}
					elsif ($mouse_2nd_click && $mouse_2nd_click->[0] eq 'nick' &&
							   $mouse_2nd_click->[1] == $ACT_STR && $mouse_2nd_click->[2] eq $ACT_STR->[A_LINK]) {
						weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/query $nick");
					}
					elsif (!$mouse_2nd_click) {
						$one_click = [ 'nick', $ACT_STR, $ACT_STR->[A_LINK] ];
						$delayed_nick_menu_timer = weechat::hook_timer(get_nick_2nd_click_delay(), 0, 1, 'delayed_nick_menu', $nick);
					}
					else {
						delayed_nick_menu($nick);
					}
				}
			}
			copywin_cmd(undef, $ACT_STR->[BUFPTR], '**', 1);
		}

		unless (@cursor == 2) { # no valid text here
			$mouse_2nd_click = $one_click if $_[2] =~ /^#/;
			my $autoclose_delay = get_autoclose_delay();
			$autoclose_delay += get_nick_2nd_click_delay() if $one_click;
			$autoclose_in_progress = weechat::hook_timer($autoclose_delay, 0, 1, 'copywin_autoclose', '')
					if $autoclose_delay && $ACT_STR->[MOUSE_AUTOMODE] && $_[2] =~ /^#/ && !$autoclose_in_progress;
			return weechat::WEECHAT_RC_OK;
		}

		if ($_[2] =~ /^ /) { # button down
			@{$ACT_STR->[CUR]}[2,3] = (-1, -1);
			weechat::unhook($autoclose_in_progress) if $autoclose_in_progress;
			$autoclose_in_progress = undef;
		}
		elsif ($this_last_mouse_seq =~ /^ / &&
			   ($_[2] =~ /^@/ ||
				($_[2] =~ /^#/ && ((substr $this_last_mouse_seq, 1) ne (substr $_[2], 1)))
			   )) { # switch to drag
			switchmode() if $ACT_STR->[MOUSE_AUTOMODE] && $ACT_STR->[MODE] eq 'hyperlink';
			selection_dispatch_input('@');
		}
		if ($this_last_mouse_seq =~ /^ / && $_[2] =~ /^#/ &&
				((substr $this_last_mouse_seq, 1) eq (substr $_[2], 1))) { # click
			if ($mouse_2nd_click && $mouse_2nd_click->[0] eq 'sel' &&
				 $mouse_2nd_click->[1] == $ACT_STR) {
			}
			elsif (!$mouse_2nd_click) {
				$one_click = [ 'sel', $ACT_STR, [ @cursor ] ];
			}
		}
		@{$ACT_STR->[CUR]}[0,1] = @cursor;
		if ($mouse_2nd_click && $mouse_2nd_click->[0] eq 'sel' &&
			$mouse_2nd_click->[1] == $ACT_STR &&
			$ACT_STR->[MODE] eq 'selection' &&
			$ACT_STR->[CUR][2] >= 0 && $ACT_STR->[CUR][3] >= 0) {
			{ # fix cursor to word boundary
			my $msg = $ACT_STR->[LINES][$ACT_STR->[CUR][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my @breaks;
			push @breaks, @- while $plain_msg =~ /\b/g;
			if (($ACT_STR->[CUR][0] == $mouse_2nd_click->[-1][0] && $ACT_STR->[CUR][1] > $mouse_2nd_click->[-1][1])
			   || $ACT_STR->[CUR][0] > $mouse_2nd_click->[-1][0]) { #forward
				$ACT_STR->[CUR][1] = (grep { $_ >= $ACT_STR->[CUR][1] } @breaks)[0];
				unless (defined $ACT_STR->[CUR][1]) {
					my $msglen = length $plain_msg;
					$ACT_STR->[CUR][1] = $msglen;
				}
			}
			else { #backward
				$ACT_STR->[CUR][1] = (grep { $_ <= $ACT_STR->[CUR][1] } @breaks)[-1];
				unless (defined $ACT_STR->[CUR][1]) {
					$ACT_STR->[CUR][1] = 0;
				}
			} }
		
			{ # fix selection to word boundary
			my $msg = $ACT_STR->[LINES][$mouse_2nd_click->[-1][0]][LINE]{'message'};
			my $plain_msg = fu8on weechat::string_remove_color($msg, '');
			my @breaks;
			push @breaks, @- while $plain_msg =~ /\b/g;
			if (($mouse_2nd_click->[-1][0] == $ACT_STR->[CUR][0] && $mouse_2nd_click->[-1][1] > $ACT_STR->[CUR][1])
			   || $mouse_2nd_click->[-1][0] > $ACT_STR->[CUR][0]) { #forward
				$ACT_STR->[CUR][3] = (grep { $_ >= $mouse_2nd_click->[-1][1] } @breaks)[0];
				unless (defined $ACT_STR->[CUR][3]) {
					my $msglen = length $plain_msg;
					$ACT_STR->[CUR][3] = $msglen;
				}
			}
			else { #backward
				$ACT_STR->[CUR][3] = (grep { $_ <= $mouse_2nd_click->[-1][1] } @breaks)[-1];
				unless (defined $ACT_STR->[CUR][3]) {
					$ACT_STR->[CUR][3] = 0;
				}
			} }
		}
		my @link = grep { $_->[-1][URL_LINE] == $cursor[LINE] &&
						  $_->[-1][URL_S] <= $cursor[1] && $_->[-1][URL_E] > $cursor[1] }
			do {
				my $i = 0;
				map { [ $i++, $_ ] } @{$ACT_STR->[URLS]}
			};

# 		open my $fx, '>', ...;
# 		print $fx "link:@link cur:@cursor\n";
# 		map { print $fx $_->[0].'#url_line:'.$_->[-1][URL_LINE].' url_s:'.$_->[-1][URL_S].' url_e:'.$_->[-1][URL_E].' url:'.$_->[-1][URL]."\n" }
# 			do {
# 				my $i = 0;
# 				map { [ $i++, $_ ] } @{$ACT_STR->[URLS]}
# 			};

		if (@link == 1) {
			$ACT_STR->[A_LINK] = $link[0][0];
			my $t = substr $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO]{'type'}, 0, 1;
			unless ($ACT_STR->[URL_TYPE_FILTER] =~ $t) {
				switchmode();
				$ACT_STR->[URL_TYPE_FILTER] = $t;
				switchmode();
			}
		}
		if ($ACT_STR->[MODE] eq 'hyperlink' && @link == 1) {
			hyperlink_to_clip();
			if ($this_last_mouse_seq =~ /^ / && $_[2] =~ /^#/ &&
				((substr $this_last_mouse_seq, 1) eq (substr $_[2], 1))) { # click
				my $link_type = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL_INFO]{'type'};
				if ($link_type eq 'nick') {
					my $nick = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
					if (Nlib::has_false_value(weechat::config_get_plugin('mouse.nick_2nd_click'))) {
						delayed_nick_menu($nick);
					}
					elsif ($mouse_2nd_click && $mouse_2nd_click->[0] eq 'link' &&
						   $mouse_2nd_click->[1] == $ACT_STR && $mouse_2nd_click->[2] == $ACT_STR->[A_LINK]) {
						weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/query $nick");
					}
					elsif (!$mouse_2nd_click) {
						$one_click = [ 'link', $ACT_STR, $ACT_STR->[A_LINK] ];
						$delayed_nick_menu_timer = weechat::hook_timer(get_nick_2nd_click_delay(), 0, 1, 'delayed_nick_menu', $nick);
					}
					else {
						delayed_nick_menu($nick);
					}
				}
				elsif ($link_type eq 'channel') {
					my $channel = $ACT_STR->[URLS][$ACT_STR->[A_LINK]][URL];
					if ($mouse_2nd_click && $mouse_2nd_click->[0] eq 'link' &&
					    $mouse_2nd_click->[1] == $ACT_STR && $mouse_2nd_click->[2] == $ACT_STR->[A_LINK]) {
						weechat::command($ACT_STR->[WINDOWS]{'buffer'}, "/join $channel");
					}
					elsif (!$mouse_2nd_click) {
						$one_click = [ 'link', $ACT_STR, $ACT_STR->[A_LINK] ];
					}
				}
				else {
					if (Nlib::has_false_value(weechat::config_get_plugin('mouse.url_open_2nd_click')) ||
							($mouse_2nd_click && $mouse_2nd_click->[0] eq 'link' &&
							 $mouse_2nd_click->[1] == $ACT_STR && $mouse_2nd_click->[2] == $ACT_STR->[A_LINK])) {
						hyperlink_dispatch_input('!');
					}
					elsif (!$mouse_2nd_click) {
						$one_click = [ 'link', $ACT_STR, $ACT_STR->[A_LINK] ];
					}
				}
			}
		}
		else {
			selection_to_clip();
		}
		copywin_cmd(undef, $ACT_STR->[BUFPTR], '**', 1);
		if ($_[2] =~ /^#/) { # button up
			$mouse_2nd_click = $one_click;
			my $autoclose_delay = get_autoclose_delay();
			if ($one_click && $one_click->[0] eq 'link') {
				if ($one_click->[1][URLS][$one_click->[2]][URL_INFO]{'type'} eq 'nick') {
					$autoclose_delay += get_nick_2nd_click_delay();
				}
				else {
					$autoclose_delay += get_2nd_click_delay();
				}
			}
			$autoclose_in_progress = weechat::hook_timer($autoclose_delay, 0, 1, 'copywin_autoclose', '')
					if $autoclose_delay && $ACT_STR->[MOUSE_AUTOMODE] && !$autoclose_in_progress;
		}
	}
	weechat::WEECHAT_RC_OK
}

sub hsignal_evt {
	my %data = %{$_[2]};
	if ($data{_key} =~ /^(.*)-event-/) {
		my $msg = "\@chat($data{_buffer_full_name}):$1";
		for my $k (Nlib::i2h('key', '', 'mouse')) {
			next if $k->{'key'} =~ /-event/;
			(my $match = '^'.(quotemeta $k->{'key'})) =~ s/\\\*/.*/g;
			my $close = $msg =~ $match;
			last if $close and $k->{'command'} =~ /hsignal:@{[SCRIPT_NAME]}/;
			return weechat::WEECHAT_RC_OK if $close;
		}
	}
	if ($data{_key} =~ /-event-down/) {
		mouse_evt(undef, undef, join '', ' ', (pack 'U', 33+$data{_x2}), (pack 'U', 33+$data{_y2}));
		$hsignal_mouse_down_sent = 1;
	}
	elsif ($data{_key} =~ /-event-drag/) {
		mouse_evt(undef, undef, join '', '@', (pack 'U', 33+$data{_x2}), (pack 'U', 33+$data{_y2}));
	}
	else {
		mouse_evt(undef, undef, join '', ' ', (pack 'U', 33+$data{_x}), (pack 'U', 33+$data{_y}))
			unless $hsignal_mouse_down_sent;
		mouse_evt(undef, undef, join '', '#', (pack 'U', 33+$data{_x2}), (pack 'U', 33+$data{_y2}));
		$hsignal_mouse_down_sent = undef;
	}
	weechat::WEECHAT_RC_OK
}

## check_layout -- check if this weechat version knows about layout infolist
sub check_layout {
	return weechat::WEECHAT_RC_OK if $LAYOUT_OK;
#	my $winptr = weechat::current_window();
#	my ($wininfo) = Nlib::i2h('window', $winptr);
#	my ($lineinfo) = Nlib::i2h('buffer_lines', @{$wininfo}{'buffer','start_line'});
#	my ($layoutinfo) = Nlib::i2h('layout', $wininfo->{'pointer'}, $lineinfo->{'line'}, $listptr);
#	Nlib::l2l($listptr, 1);
# 	unless ($layoutinfo) {
# 		weechat::print('', weechat::prefix('error').
# 					   "You will need to have layout trace support in your WeeChat. Get it at\n".
# 					   " http://anti.teamidiot.de/static/nei/*/Code/WeeChat/display_traces.diff");
# 	}
# 	else {
		$LAYOUT_OK = 1;
#	}
# 	if (($ENV{'STY'} || $ENV{'TERM'} =~ /screen/) && !exists $ENV{'TMUX'}) {
# 		weechat::print('', weechat::prefix('error').
# 					  "Your terminal most likely doesn't support the selection clipboard control.");
# 	}
	weechat::WEECHAT_RC_OK
}


## garbage_str -- remove copywin storage when copywin buffer is closed
## () - signal handler
## $bufptr - signal comes with pointer of closed buffer
sub garbage_str {
	my (undef, undef, $bufptr) = @_;
	$ACT_STR = undef if $ACT_STR && $ACT_STR->[BUFPTR] eq $bufptr;
	delete $STR{$bufptr};
	weechat::WEECHAT_RC_OK
}

## decouple_mouse_scroll -- add coords script as mouse scrolling handler
sub decouple_mouse_scroll {
	my $main = weechat::buffer_search_main();
	my $mouse_scroll_ext = weechat::buffer_string_replace_local_var($main, '$mousescroll');
	unless (grep { $_ eq SCRIPT_NAME } split ',', $mouse_scroll_ext) {
		$script_old_mouse_scroll = $mouse_scroll_ext;
		if ($mouse_scroll_ext =~ /^\$/) {
			weechat::buffer_set($main, 'localvar_set_mousescroll', SCRIPT_NAME);
		}
		else {
			weechat::buffer_set($main, 'localvar_set_mousescroll', $mouse_scroll_ext.','.SCRIPT_NAME);
		}
	}
}

## restore_mouse_scroll -- restore mouse scrolling handler
sub restore_mouse_scroll {
	if (defined $script_old_mouse_scroll) {
		my $main = weechat::buffer_search_main();
		if ($script_old_mouse_scroll =~ /^\$/) {
			weechat::buffer_set($main, 'localvar_del_mousescroll', '');
		}
		else {
			weechat::buffer_set($main, 'localvar_set_mousescroll',
								join ',', grep { $_ ne SCRIPT_NAME } split ',', $script_old_mouse_scroll);
		}
	}
}

## default_options -- set up default option values on start and when unset
sub default_options {
	my %defaults = (
		url_braces => '[({<"'."''".'">})]',
		url_regex  =>
			 '\w+://\S+ | '.
			 '(?:^|(?<=\s))(?:\S+\.){2,}\w{2,5}(?:/\S*|(?=\s)|$) | '.
			 '(?:^|(?<=\s))(?:\S+\.)+\w{2,5}/(?:\S+)?',
		url_non_endings    => '[.,;:?!_-]',
		url_non_beginnings => '\W',
		hyper_nicks    => 'off',
		hyper_channels => 'off',
		hyper_prefix   => 'on',
		hyper_show     => 'url',
		use_nick_menu  => 'off',
		xterm_compatible => 'rxvt-uni',
		'mouse.copy_on_click'        => 'on',
		'mouse.close_on_release'     => '110',
		'mouse.click_select_pane'    => 'on',
		'mouse.click_through_pane'   => 'off',
		'mouse.url_open_2nd_click'   => 'off',
		'mouse.handle_scroll'        => 'off',
		'mouse.scroll_inactive_pane' => 'on',
		copybuf_short_name => '©',
		'color.selection_cursor' => 'reverse.underline',
		'color.selection'        => 'reverse.brown,black',
		'color.url_highlight'        => 'reverse.underline',
		'color.url_highlight_active' => 'reverse.brown,black',
	);
	for (keys %defaults) {
		weechat::config_set_plugin($_, $defaults{$_})
			unless weechat::config_is_set_plugin($_);
	}
	my $sf = SCRIPT_FILE;
	for (Nlib::get_settings_from_pod($sf)) {
		weechat::config_set_desc_plugin($_, Nlib::get_desc_from_pod($sf, $_));
	}
	if (Nlib::has_true_value(weechat::config_get_plugin('mouse.handle_scroll'))) {
		decouple_mouse_scroll();
	}
	else {
		restore_mouse_scroll();
	}
	weechat::WEECHAT_RC_OK
}

sub close_copywin {
	copywin_cmd(undef, $ACT_STR->[BUFPTR], '**q') if $ACT_STR;
	weechat::WEECHAT_RC_OK
}

sub init_coords {
	$listptr = weechat::list_new();
	weechat::hook_timer(1000, 0, 1, 'check_layout', '');
	default_options();
	weechat::WEECHAT_RC_OK
}

sub stop_coords {
	close_copywin();
	restore_mouse_scroll();
	weechat::list_free($listptr);
	weechat::WEECHAT_RC_OK
}
