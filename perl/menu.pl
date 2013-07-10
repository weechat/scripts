use strict; use warnings;
$INC{'Encode/ConfigLocal.pm'}=1;
require Encode;

# menu.pl is written by Nei <anti.teamidiot.de>
# and licensed under the under GNU General Public License v3
# or any later version

# to read the following docs, you can use "perldoc menu.pl"

=head1 NAME

menu - menu and popup menu system for weechat (weechat edition)

=head1 SYNOPSIS

first, copy the file to your
F<.weechat/perl> directory. Then you can type

  /perl load menu.pl

in weechat to load the script. Use

  /menu

to open the main menu or (recommended) add a key binding to open the
menu. For example,

  /key bind meta-m /menu

would allow you to open the menu with Alt+M.

If your WeeChat comes with builtin cursor and mouse support, you can
bind the nick popup menu to the nicklist using

  /key bindctxt mouse @item(buffer_nicklist):button1 hsignal:menu

or if you want to use cursor mode, you can bind it to a key like this:

  /key bindctxt cursor @item(buffer_nicklist):m hsignal:menu;/cursor stop

=head1 DESCRIPTION

menu will give you a main menu and a popup menu to be able to use some
features through menu entries. A popup menu for the nicklist is
included by default.

=head1 USAGE

to open the main menu, hit the key you defined as a keybinding as
explained in the L</SYNOPSIS> or type C</menu>.

=head2 Menu navigation

after you open the main menu, you will be able to choose the main menu
entry using the left-arrow and right-arrow keys of your keyboard. You
can also type the underlined letters for quick access. To open a
submenu, just press the Return key while the menu entry is highlighted.

=head2 Submenus

Once you have opened a submenu, use the up-arrow and down-arrow to
choose a menu entry. To run a menu entry, confirm with Return again.

to close any menu, type Ctrl+X on your keyboard.

for mouse support, this script will listen to mouse input
signals. If your WeeChat does not have builtin cursor and mouse
support, another script is needed to supply these signals, such as
F<mouse.pl> which can be found in the same place as this script.

=head2 Nick menu

There is a popup menu for nick names which can be opened using

  /menu nick NICKNAME

whereby NICKNAME has to be replaced by a real nick. More conveniently,
when using the mouse this command is bound to clicks on the nicklist
so you can just click on a nick in the nicklist to open this popup
menu. It is navigated in the same way as a submenu.

=head1 CAVEATS

=over

=item *

per-buffer key bindings as are used by iset, urlgrab, coords, the man
page viewer (/menu help) and some game scripts B<always> override the
global key bindings, so you will not be able to navigate the menu in
this case.

=item *

unfortunately, WeeChat scrolls back the nicklist whenever a bar is
hidden or shown. Some hacks are in this script to scroll it back to
where it was before, but only when you clicked on the nicklist, not
when interacting with the main menu.

=item *

to scroll the nicklist using the mouse, as well as switching windows
on mouse click, another script such as C<coords.pl> might be
necessary.

=back

=head1 TODO

=over

=item *

would be nice to have popup menu on right click, name insertion on
left click and query (or default action) on double click on the
nicklist. Also, clicking on names in chat should scroll the nicklist
there and otherwise behave the same.

=item *

interactive menu entries are lacking yet (like Join channel, Connect
to server) due to the missing implementation of the

  /menu interactive

command. The entries are

  /menu interactive ask {Connect to server:} {Port:} /connect $0/$1
  /menu interactive ask {Join which channel?} /join $0
  /menu interactive yn {Are you sure?} /quit

=back

=head1 SETTINGS

the settings are usually found in the

  plugins.var.perl.menu

namespace, that is, type

  /set plugins.var.perl.menu.*

to see them and

  /set plugins.var.perl.menu.SETTINGNAME VALUE

to change a setting C<SETTINGNAME> to a new value C<VALUE>. Finally,

  /unset plugins.var.perl.menu.SETTINGNAME

will reset a setting to its default value.

the following settings are available:

=head2 sticky_menu

if this is set to on, a submenu is not closed when the entry is
confirmed but has to be closed manually using Ctrl+X.

=head2 active_help

this setting is documented for completeness, it reflects if the help
bar is visible and can be toggled from within the menu with Ctrl+H.

=head2 key_binding_hidden

if set to on, the friendly reminder how to open the main menu (by
default: /menu to open menu) will be removed from view. useful for
those people bothered by it.

=head2 main_menu_hidden

if set to on, the main menu bar will be always hidden. useful if you
don't care about clicking on the main menu and want to save one line
on your screen (due to internal reasons, the setting
weechat.bar.main_menu.hidden does not work reliably, use this instead.)

=head1 MENU CONFIGURATION

the whole menu is configurable through the file F<menu.conf> or

  /set menu.var.*

The syntax for a main menu is

  /set menu.var.#.name &Name

where C<#> is an unique number, C<Name> is the name of the menu and
the letter after the C<< & >> is the unique shortcut for this
menu. All menu entries in the submenu of this menu are of the form

  /set menu.var.#.1.name &Item
  /set menu.var.#.1.command /command

where C<#> is the number of the main menu, C<1> is an unique number
for this submenu item, C<Item> is the name of this item, the letter
after the C<< & >> is the unique shortcut for this item as
above. C</command> specifies the command to be executed, for multiple
commands create an alias first.

See the included main menu for an example.

=head2 Popup menus

Popup menus are configured through

  /set menu.var.POPUP.*

where C<POPUP> is the name of the popup menu. The popup menu entries
are configured in the same way as submenu entries above, with C<POPUP>
replacing C<#>. To open a popup menu, use

  /menu POPUP args

The value of C<args> is available in a popup command as I<$0>, I<$1>,
...

See the included C<nick> popup for an example.

=head2 Dynamic menus

Dynamic menu entries are configured through .command settings. There
must not be a .name on this level for dynamic menu generation to
work. The syntax is as follows:

  /set menu.var.#.name &Buffers
  /set menu.var.#.1.command "%gui_buffers.buffer% ${i} ${buffer.name} % /buffer ${buffer.full_name}"

The first part of command must be %HDATA_LIST.HDATA_NAME% (see the
weechat api docs for info on hdata).

The second part sets the .name of the dynamic items and the third part
sets the .command. They are seperated by % and evaluated with /eval
(see /help eval for more info).

Refer to the three dynamic menus that ship with the sample config.

For usage with scripts, another form of dynamic menu is supported:

  /set menu.var.POPUP.1.command "%#info_hashtable% $1 % $0"

The first part of command must be %#INFO_HASHTABLE_NAME% (see the
weechat api docs on weechat_hook_info_hashtable).

The second and third part are passed on to the hashtable function in
the hashtable parameter. The returned hashtable must contain suitable
1.command/1.name pairs to be added into the menu.

You can check the spell_menu script for an example of how to use this.

=head1 FUNCTION DESCRIPTION

for full pod documentation, filter this script with

  perl -pE'
  (s/^## (.*?) -- (.*)/=head2 $1\n\n$2\n\n=over\n/ and $o=1) or
   s/^## (.*?) - (.*)/=item I<$1>\n\n$2\n/ or
  (s/^## (.*)/=back\n\n$1\n\n=cut\n/ and $o=0,1) or
  ($o and $o=0,1 and s/^sub /=back\n\n=cut\n\nsub /)'

=cut

use constant SCRIPT_NAME => 'menu';
weechat::register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', '0.8', 'GPL3', 'menu system', 'stop_menu', '') || return;
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
## $_[0] - arg pointer or hdata list name
## $_[1] - hdata name
## $_[2..$#_] - hdata variable name
## $_[-1] - hashref with key/value to update (optional)
## returns value of hdata, and hdata name in list ctx, or number of variables updated
sub hdh {
	if (@_ > 1 && $_[0] !~ /^0x/ && $_[0] !~ /^\d+$/) {
		my $arg = shift;
		unshift @_, weechat::hdata_get_list(weechat::hdata_get($_[0]), $arg);
	}
	while (@_ > 2) {
		my ($arg, $name, $var) = splice @_, 0, 3;
		my $hdata = weechat::hdata_get($name);
		unless (ref $var eq 'HASH') {
			$var =~ s/!(.*)/weechat::hdata_get_string($hdata, $1)/e;
			(my $plain_var = $var) =~ s/^\d+\|//;
			my $type = weechat::hdata_get_var_type_string($hdata, $plain_var);
			if ($type eq 'pointer') {
				my $name = weechat::hdata_get_var_hdata($hdata, $var);
				unshift @_, $name if $name;
			}

			my $fn = "weechat::hdata_$type";
			unshift @_, do { no strict 'refs';
							 &$fn($hdata, $arg, $var) };
		}
		else {
			return weechat::hdata_update($hdata, $arg, $var);
		}
	}
	wantarray ? @_ : $_[0]
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
			$row > $_->{y} && $row <= $_->{y}+$_->{height} &&
				$col > $_->{x} && $col <= $_->{x}+$_->{width} &&
					(($bar_info)=i2h('bar', $_->{bar})) && !$bar_info->{hidden};
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
	$row > $wininfo->{y} &&
		$row <= $wininfo->{y}+$wininfo->{height} &&
			$col > $wininfo->{x} &&
				$col <= $wininfo->{x}+$wininfo->{width}
}

## has_true_value -- some constants for "true"
## $v - value string
## returns true if string looks like a true thing
sub has_true_value {
	my $v = shift || '';
	$v =~ /^(?:on|yes|y|true|t|1)$/i
}

## hook_dynamic -- weechat::hook something and store hook reference
## $hook_call - hook type (e.g. modifier)
## $what - event type to hook (depends on $hook_call)
## $sub - subroutine name to install
## @params - parameters
sub hook_dynamic {
	my ($hook_call, $what, $sub, @params) = @_;
	my $caller_package = (caller)[0];
	eval qq{
		package $caller_package;
		no strict 'vars';
		\$DYNAMIC_HOOKS{\$what}{\$sub} =
			weechat::hook_$hook_call(\$what, \$sub, \@params)
				unless exists \$DYNAMIC_HOOKS{\$what} &&
					exists \$DYNAMIC_HOOKS{\$what}{\$sub};
	};
	die $@ if $@;
}

## unhook_dynamic -- weechat::unhook something where hook reference has been stored with hook_dynamic
## $what - event type that was hooked
## $sub - subroutine name that was installed
sub unhook_dynamic {
	my ($what, $sub) = @_;
	my $caller_package = (caller)[0];
	eval qq{
		package $caller_package;
		no strict 'vars';
		weechat::unhook(\$DYNAMIC_HOOKS{\$what}{\$sub})
			if exists \$DYNAMIC_HOOKS{\$what} &&
				exists \$DYNAMIC_HOOKS{\$what}{\$sub};
		delete \$DYNAMIC_HOOKS{\$what}{\$sub};
		delete \$DYNAMIC_HOOKS{\$what} unless \%{\$DYNAMIC_HOOKS{\$what}};
	};	
	die $@ if $@;
}

## bar_filling -- get current filling according to position
## $bar_infos - info about bar (from find_bar_window)
## returns filling as an integer number
sub bar_filling {
	my ($bar_infos) = @_;
	($bar_infos->[-1]{position} <= 1 ? $bar_infos->[-1]{filling_top_bottom}
	 : $bar_infos->[-1]{filling_left_right})
}

sub fu8on(@) {
	Encode::_utf8_on($_) for @_; wantarray ? @_ : shift
}

use Text::CharWidth;

sub screen_length($) {
	Text::CharWidth::mbswidth($_[0])
}

## bar_column_max_length -- get max item length for column based filling
## $bar_infos - info about bar (from find_bar_window)
## returns max item length
sub bar_column_max_length {
	my ($bar_infos) = @_;
	my @items;
	for (@{ $bar_infos->[0]{items_content} }) {
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
	for (@{ $bar_infos->[-1]{items_array} }) {
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
	while ($$prefix_col_r > $bar_infos->[0]{width}) {
		++$$prefix_y_r;
		$$prefix_col_r -= $bar_infos->[0]{width};
	}
}

## bar_lines_column_vert -- count lines in column layout
## $bar_infos - info about bar (from find_bar_window)
## returns lines needed for columns_horizontal layout
sub bar_lines_column_vert {
	my ($bar_infos) = @_;
	my @items;
	for (@{ $bar_infos->[0]{items_content} }) {
		push @items, split "\n", join "\n", @$_;
	}
	my $max_length = bar_column_max_length($bar_infos);
	my $dummy_col = 1;
	my $lines = 1;
	for (@items) {
		if ($dummy_col+$max_length > 1+$bar_infos->[0]{width}) {
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
	$col += $bar_infos->[0]{scroll_x};
	$row += $bar_infos->[0]{scroll_y};
	my ($item_pos_a, $item_pos_b, $found) = 
		find_bar_item_pos($bar_infos, $search);

	return 'item position not found' unless $found;

	# extract items to skip
	my $item_join = 
		(bar_filling($bar_infos) <= 1 ? '' : "\n");
	my @prefix;
	for (my $i = 0; $i < $item_pos_a; ++$i) {
		push @prefix, split "\n", join $item_join, @{ $bar_infos->[0]{items_content}[$i] };
	}
	push @prefix, split "\n", join $item_join, @{ $bar_infos->[0]{items_content}[$item_pos_a] }[0..$item_pos_b-1] if $item_pos_b;

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
			if ($prefix_col+$item_max_length > 1+$bar_infos->[0]{width}) {
				++$prefix_y;
				$prefix_col = 1;
			}
		}
	}
	elsif (bar_filling($bar_infos) == 3) {
		$item_max_length = bar_column_max_length($bar_infos);
		$col_vert_lines = $bar_infos->[-1]{position} <= 1 ? bar_lines_column_vert($bar_infos) : $bar_infos->[0]{height};
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

	$col += $bar_infos->[0]{scroll_x};
	$row += $bar_infos->[0]{scroll_y};

	return $error if $error;
	
	return 'no viable position'
		unless (($row == $prefix_y  && $col >= $prefix_col) || $row > $prefix_y || bar_filling($bar_infos) >= 3);

	my @subitems = split "\n", $bar_infos->[0]{items_content}[$item_pos_a][$item_pos_b];
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

			if ($prefix_col+$item_max_length > 1+$bar_infos->[0]{width}) {
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

## bar_item_get_item_and_subitem_at -- gets item and subitem at position
## $bar_infos - info about bar
## $col - pointer column
## $row - pointer row
## returns generic item, error if outside subitem, index of subitem and text of subitem
sub bar_item_get_item_and_subitem_at {
	my ($bar_infos, $col, $row) = @_;
	my $item_pos_a = 0;
	my $item_pos_b;
	for (@{ $bar_infos->[-1]{items_array} }) {
		$item_pos_b = 0;
		for (@$_) {
			my $g_item = "^\Q$_\E\$";
			my ($error, @rest) =
				bar_item_get_subitem_at($bar_infos, $g_item, $col, $row);
			return ($_, $error, @rest)
				if (!defined $error || $error =~ /^outside/);
			return () if $error eq 'no viable position';
			++$item_pos_b;
		}
		++$item_pos_a;
	}
	()
}

## mangle_man_for_wee -- turn man output into weechat codes
## @_ - list of grotty lines that should be turned into weechat attributes
## returns modified lines and modifies lines in-place
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

	my $width = $wininfo->{chat_width};
	--$width if $wininfo->{chat_width} < $wininfo->{width} || ($wininfo->{width_pct} < 100 && (grep { $_->{y} == $wininfo->{y} } Nlib::i2h('window'))[-1]{x} > $wininfo->{x});
	$width -= 2; # when prefix is shown

	weechat::buffer_set($buf, 'time_for_each_line', 0);
	eval qq{
		package $caller_package;
		weechat::buffer_set(\$buf, 'display', 'auto');
	};
	die $@ if $@;

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input history_previous' ||
			   $_->{command} eq '/input history_global_previous' } @wee_keys;
	@keys = 'meta2-A' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll -1') for @keys;

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input history_next' ||
			   $_->{command} eq '/input history_global_next' } @wee_keys;
	@keys = 'meta2-B' unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window scroll +1') for @keys;

	weechat::buffer_set($buf, 'key_bind_ ', '/window page_down');

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input delete_previous_char' } @wee_keys;
	@keys = ('ctrl-?', 'ctrl-H') unless @keys;
	weechat::buffer_set($buf, "key_bind_$_", '/window page_up') for @keys;

	weechat::buffer_set($buf, 'key_bind_g', '/window scroll_top');
	weechat::buffer_set($buf, 'key_bind_G', '/window scroll_bottom');

	weechat::buffer_set($buf, 'key_bind_q', '/buffer close');

	weechat::print($buf, " \t".mangle_man_for_wee($_)) # weird bug with \t\t showing nothing?
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

weechat::bar_item_new('main_menu', 'bar_item_main_menu', '');
weechat::bar_item_new('sub_menu', 'bar_item_sub_menu', '');
weechat::bar_item_new('menu_help', 'bar_item_menu_help', '');
weechat::bar_item_new('window_popup_menu', 'bar_item_window_popup_menu', '');
weechat::hook_command(SCRIPT_NAME, 'open the menu', '[name] [args] || reset',
					  (join "\n",
					   'without arguments, open the main menu.',
					   'if name is given, open the popup menu with that name - this is usually done by scripts.',
					   'args are passed on to the menu commands, see the manual for more info.',
					   'Example: /menu nick yournick',
					   'reset: resets the menu system to its initial config (also required if ',
					   '       you want to load new default menus, e.g after upgrade of script)',
					   'use '.weechat::color('bold').'/menu help'.weechat::color('-bold').' to read the manual'
					  ), '', 'open_menu', '');
weechat::hook_signal('buffer_closed', 'invalidate_popup_buffer', '');
weechat::hook_signal('mouse', 'mouse_evt', '');
weechat::hook_signal('input_flow_free', 'menu_input_mouse_fix', '');
weechat::hook_config('plugins.var.perl.'.SCRIPT_NAME.'.*', 'script_config', '');
weechat::hook_config(SCRIPT_NAME.'.var.*', 'menu_config', '');
weechat::hook_command_run('/key *', 'update_main_menu', '');
# is there builtin mouse support?
if ((weechat::info_get('version_number', '') || 0) >= 0x00030600) {
	weechat::hook_hsignal('menu', 'hsignal_evt', '');
	weechat::key_bind('mouse', +{
		map { $_ => 'hsignal:menu' }
		'@bar(*_menu):button1',
		'@item(buffer_nicklist):button1'
	});
}

our %ACT_MENU;
our $POPUP_MENU_BUFFER;
our $POPUP_MENU;
our $POPUP_MENU_ARGS;
our $MENU_OPEN;
our $MOUSE_IN_PROGRESS;

our ($CFG_FILE, $CFG_FILE_SECTION);

our $last_mouse_seq;

our $LAST_NICK_COLOR;

our ($NICKLIST_RESCROLL_X, $NICKLIST_RESCROLL_Y);
our ($LAST_NICKLIST_RESCROLL_X, $LAST_NICKLIST_RESCROLL_Y);

use constant DEBUG_MENU => 0;

init_menu();

## make_menu -- convert menu entries to bar items
## $items - array ref of menu entries
## $active - reference to active menu item (gets corrected for bounds)
## $prefix - prefix for all items
## $info - info to show when menu closed
## $title - menu title (if applicable)
## returns bar item structure of menu items
sub make_menu {
	my ($items, $active, $prefix, $info, $title) = @_;
	if (defined $$active) {
		$$active = $#$items if $$active < 0;
		$$active = 0 if $$active > $#$items;
	}
	my ($ul, $UL) = map { weechat::color($_) } ('underline', '-underline');
	s/&(.)/$ul$1$UL/g for @$items;
	my $I = '▐';
	my $act_menu = $MENU_OPEN && defined $$active ? $$active : -1;
	my $act = weechat::color('reverse');
	my $ACT = weechat::color('-reverse');
	join "\n", (defined $title ? $title !~ /\S/ ? $title : $I.$act.$title.$I.$ACT : ()),
		map { $prefix.$_ } map { $act_menu-- ? $_ : $act.$_ } @$items,
			(($MENU_OPEN || !$info) ? () : $I.$act.$info.$I.$ACT)
}

## MAIN_MENU -- return main menu items
sub MAIN_MENU {
	map { $_->{value} }
	grep { $_->{option_name} =~ /^\d+[.]name$/ }
	Nlib::i2h('option', '', 'menu.var.*')
	#qw(&File &Edit &View C&mds &Tools &Options &Buffers &Perl)
}

## bar_item_main_menu -- return main menu as bar items
sub bar_item_main_menu {
	my @items = MAIN_MENU();
	my ($keybinding) = grep { $_->{command} eq '/menu' } Nlib::i2h('key');
	if ($keybinding) {
		my %arrow = ('A' => '↑', 'B' => '↓', 'C' => '→', 'D' => '←', 'E' => '·');
		my %inspg = (2 => 'Ins', 3 => 'Del', 5 => 'PgUp', 6 => 'PgDn',
			1 => 'Find', 28 => 'Help', 29 => 'Copy', 32 => 'Paste', 34 => 'Cut',
			(map { 10+$_ => "F$_" } 1..5),
			(map { 11+$_ => "F$_" } 6..10),
			(map { 12+$_ => "F$_" } 11..12),
		);
		my %fkeys = ('P' => 'F1', 'Q' => 'F2', 'R' => 'F3', 'S' => 'F4');
		my %homend = ('H' => 'Home', 'F' => 'End');
		my %homend1 = (7 => $homend{H}, 8 => $homend{F});
		my %homend2 = (1 => $homend{H}, 4 => $homend{F});
		my %some_keys = (
			'meta2-P' => 'Pause',

			'ctrl-@' => 'C-SPC',

			'ctrl-I'        =>   'Tab',
			'meta2-Z'       => 'S-Tab',
			'meta2-27;5;9~' => 'C-Tab',

			'ctrl-M'         =>   'RET',
			'meta2-27;5;13~' => 'C-RET',
			'meta2-27;2;13~' => 'S-RET',
			'meta-ctrl-M'    => 'M-RET',

			'ctrl-?'      =>     'BS',
			'ctrl-H'      =>   'C-BS',
			'meta-ctrl-?' =>   'M-BS',
			'meta-ctrl-H' => 'C-M-BS',

			(map { ( "meta2-$_"      =>    $arrow{$_}  ) } keys %arrow),
			(map { ( "meta2-1;5$_"   => "C-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta-O$_"      => "C-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta-O\l$_"    => "C-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta2-1;2$_"   => "S-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta2-\l$_"    => "S-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta2-1;3$_"   => "M-$arrow{$_}" ) } keys %arrow),
			(map { ( "meta-meta2-$_" => "M-$arrow{$_}" ) } keys %arrow),

			(map { ( "meta-O$_"      =>    $fkeys{$_}  ) } keys %fkeys),
			(map { ( "meta2-1;5$_"   => "C-$fkeys{$_}" ) } keys %fkeys),
			(map { ( "meta2-1;2$_"   => "S-$fkeys{$_}" ) } keys %fkeys),
			(map { ( "meta2-1;3$_"   => "M-$fkeys{$_}" ) } keys %fkeys),
			(map { ( "meta-meta-O$_" => "M-$fkeys{$_}" ) } keys %fkeys),

			(map { ( "meta2-$_"    =>    $homend{$_}  ) } keys %homend),
			(map { ( "meta2-1;5$_" => "C-$homend{$_}" ) } keys %homend),
			(map { ( "meta2-1;2$_" => "S-$homend{$_}" ) } keys %homend),
			(map { ( "meta2-1;3$_" => "M-$homend{$_}" ) } keys %homend),

			(map { ( "meta2-$_~"        =>    $inspg{$_}  ) } keys %inspg),
			(map { ( "meta2-$_;5~"      => "C-$inspg{$_}" ) } keys %inspg),
			(map { ( "meta2-${_}ctrl-^" => "C-$inspg{$_}" ) } keys %inspg),
			(map { ( "meta2-$_;2~"      => "S-$inspg{$_}" ) } keys %inspg),
			(map { ( "meta2-$_\$"       => "S-$inspg{$_}" ) } keys %inspg),
			(map { ( "meta2-$_;3~"      => "M-$inspg{$_}" ) } keys %inspg),
			(map { ( "meta-meta2-$_~"   => "M-$inspg{$_}" ) } keys %inspg),

			(map { ( "meta2-$_~"        =>    $homend1{$_}  ) } keys %homend1),
			(map { ( "meta2-${_}ctrl-^" => "C-$homend1{$_}" ) } keys %homend1),
			(map { ( "meta2-$_\$"       => "S-$homend1{$_}" ) } keys %homend1),
			(map { ( "meta-meta2-$_~"   => "M-$homend1{$_}" ) } keys %homend1),
			(map { ( "meta-meta2-$_~"   => "M-$homend2{$_}" ) } keys %homend2),
		);
		$keybinding = $keybinding->{key};
		if (exists $some_keys{$keybinding}) {
			$keybinding = $some_keys{$keybinding};
		}
		else {
			$keybinding =~ s/meta-/M-/;
			$keybinding =~ s/ctrl-(.)/C-\l$1/;
			$keybinding =~ s/M-C-/C-M-/;
		}
	}
	else {
		$keybinding = '/menu';
	}
	my $key_hint_text = "$keybinding to open menu";
	$key_hint_text = '' if weechat::config_is_set_plugin('key_binding_hidden') && Nlib::has_true_value(weechat::config_get_plugin('key_binding_hidden'));
	make_menu(\@items, (!$MENU_OPEN || $MENU_OPEN < 3 ? \$ACT_MENU{main} : \undef), '', $key_hint_text)
}

## menu_input_run -- dispatch /input actions to menu
## () - event handler
## $cmd - executed /input command
sub menu_input_run {
	my (undef, undef, $cmd) = @_;
	return weechat::WEECHAT_RC_OK unless $MENU_OPEN;
	$cmd =~ s/ (?:insert \\x0a|magic_enter)/ return/;
	if ($cmd eq '/input delete_previous_char') {
		my $bar = weechat::bar_search('menu_help');
		my $hidden = (Nlib::i2h('bar', $bar))[0]{hidden};
		weechat::bar_set($bar, 'hidden', $hidden ? 0 : 1);
		weechat::bar_set(weechat::bar_search('sub_menu'), 'separator', $hidden ? 0 : 1);
		weechat::config_set_plugin('active_help', $hidden ? 'on' : 'off');
		if ($MENU_OPEN == 3 && $POPUP_MENU eq 'nick') {
			weechat::command(weechat::current_buffer(), "/bar scroll nicklist * x+$LAST_NICKLIST_RESCROLL_X") if $LAST_NICKLIST_RESCROLL_X;
			weechat::command(weechat::current_buffer(), "/bar scroll nicklist * y+$LAST_NICKLIST_RESCROLL_Y") if $LAST_NICKLIST_RESCROLL_Y;
		}
	}
	elsif ($MENU_OPEN == 1) {
		if ($cmd eq '/input switch_active_buffer') {
			close_menu();
		}
		elsif ($cmd eq '/input move_previous_char') {
			--$ACT_MENU{main};
			update_main_menu();
		}
		elsif ($cmd eq '/input move_next_char') {
			++$ACT_MENU{main};
			update_main_menu();
		}
		elsif ($cmd eq '/input return') {
			++$MENU_OPEN;
			open_submenu();
		}
	}
	elsif ($MENU_OPEN == 2) {
		if ($cmd eq '/input switch_active_buffer') {
			close_submenu();
			--$MENU_OPEN;
		}
		elsif ($cmd eq '/input history_previous' || $cmd eq '/input history_global_previous') {
			--$ACT_MENU{sub};
			update_sub_menu();
		}
		elsif ($cmd eq '/input history_next' || $cmd eq '/input history_global_next') {
			++$ACT_MENU{sub};
			update_sub_menu();
		}
		elsif ($cmd eq '/input return') {
			exec_submenu();
			open_menu() unless weechat::config_is_set_plugin('sticky_menu') && Nlib::has_true_value(weechat::config_get_plugin('sticky_menu'));
		}
		#return weechat::WEECHAT_RC_OK
	}
	elsif ($MENU_OPEN == 3) {
		if ($cmd eq '/input switch_active_buffer') {
			close_window_popup_menu();
			close_menu();
		}
		elsif ($cmd eq '/input history_previous' || $cmd eq '/input history_global_previous') {
			--$ACT_MENU{window_popup};
			update_window_popup_menu();
		}
		elsif ($cmd eq '/input history_next' || $cmd eq '/input history_global_next') {
			++$ACT_MENU{window_popup};
			update_window_popup_menu();
		}
		elsif ($cmd eq '/input return') {
			exec_popupmenu();
			open_menu() unless weechat::config_is_set_plugin('sticky_menu') && Nlib::has_true_value(weechat::config_get_plugin('sticky_menu'));
		}
	}
	else {
		if ($cmd eq '/input switch_active_buffer') {
			open_menu(); # close here
		}		
	}
	weechat::WEECHAT_RC_OK_EAT
}

## menu_input_mouse_fix -- disable shortcuts during mouse input
## () - signal handler
sub menu_input_mouse_fix {
	(undef, undef, $MOUSE_IN_PROGRESS) = @_;
	weechat::WEECHAT_RC_OK
}

## menu_stuff -- get active menu
## returns active item storage, update func and menu item func of active menu
sub menu_stuff {
	if ($MENU_OPEN == 1) {
		\($ACT_MENU{main},
		  &update_main_menu,
		  &MAIN_MENU)
	}
	elsif ($MENU_OPEN == 2) {
		\($ACT_MENU{sub},
		  &update_sub_menu,
		  &SUB_MENU)
	}
	elsif ($MENU_OPEN == 3) {
		\($ACT_MENU{window_popup},
		  &update_window_popup_menu,
		  &WINDOW_POPUP_MENU)
	}
	else {
		(\'', sub {}, sub {})
	}
}

## menu_input_text -- read input shortcut keys
## () - event handler
## $_[3] - current content of input buffer
## removes input shortcut key and returns old content of input buffer
sub menu_input_text {
	Encode::_utf8_on($_[3]);
	return $_[3] unless $MENU_OPEN;
	return $_[3] if $MOUSE_IN_PROGRESS;
	my $buf = weechat::current_buffer();
	my $npos = weechat::buffer_get_integer($buf, 'input_pos')-1;
	my $input_key = substr $_[3], $npos, 1, '';
	my ($act_store, $update_fun, $menu_fun) = menu_stuff();
	my ($pos) = map { $_->[0] }
		grep { $_->[-1] =~ /&\Q$input_key/i }
			do { my $i = 0; map { [ $i++, $_ ] } $menu_fun->() };
	if (defined $pos) {
		$$act_store = $pos;
		$update_fun->();
	}
	weechat::buffer_set($buf, 'input_pos', $npos);
	$_[3]
}

## menu_input_text_display -- display on input bar
## () - event handler
## $_[3] - current content of input buffer
## returns text to be displayed on input bar
sub menu_input_text_display {
	Encode::_utf8_on($_[3]);
	return $_[3] unless $MENU_OPEN;
	'[menu open'.($MOUSE_IN_PROGRESS ? ' (mouse input)' : '').'] '. $_[3]
}

## mouse_nicklist -- handle mouse click on nicklist
## () - forwarded signal handler
## $_[2] - mouse code
## $bar_infos - info about bar
## $in_any_win - info about parent window
## $col - pointer column in bar
## $row - pointer row in bar
sub mouse_nicklist {
	my (undef, undef, undef, $bar_infos, $in_any_win, $col, $row) = @_;
	my ($error, $idx, $item) =
		Nlib::bar_item_get_subitem_at($bar_infos, qr/\bbuffer_nicklist\b/, $col, $row);
	return weechat::WEECHAT_RC_OK if $error;
	my @nick_format = split "\01", weechat::string_remove_color($item, "\1");
	weechat::print('', join ' :: ', @nick_format) if DEBUG_MENU;
	my $nick = @nick_format ? $nick_format[-1] : undef;
	return weechat::WEECHAT_RC_OK unless defined $nick;
	return weechat::WEECHAT_RC_OK unless $in_any_win;
	my $bufptr = $in_any_win->{buffer};
	mouse_nicklist_barcode($bar_infos, undef, $_[2], $bufptr, $nick, $item);
}

sub mouse_nicklist_barcode {
	my ($bar_infos, undef, undef, $bufptr, $nick, $item) = @_;
	my $nickptr = weechat::nicklist_search_nick($bufptr, '', $nick);
	if ($nickptr) {
		my @funargs = ($bufptr, $nickptr, 'color');
		weechat::nicklist_nick_set(@$LAST_NICK_COLOR) if $LAST_NICK_COLOR;
		$LAST_NICK_COLOR = [ @funargs, weechat::nicklist_nick_get_string(@funargs) ];
		weechat::nicklist_nick_set(@funargs, 'reverse');
	}
	($NICKLIST_RESCROLL_X, $NICKLIST_RESCROLL_Y) =
		($bar_infos->[0]{scroll_x},$bar_infos->[0]{scroll_y}) if defined $bar_infos;

	weechat::command(weechat::current_buffer(), "/menu nick $nick") if $_[2] =~ /^#/;
	weechat::WEECHAT_RC_OK
}

## mouse_evt -- handle mouse clicks
## () - signal handler
## $_[2] - mouse code
sub mouse_evt {
	Encode::_utf8_on($_[2]);
	my $this_last_mouse_seq = $last_mouse_seq || '';
	$last_mouse_seq = $_[2];

    if ($_[2] =~ /^[# ](.)(.)$/) {
        my $row = ord($2)-32;
		my $col = ord($1)-32;

		my $bar_infos = Nlib::find_bar_window($row, $col);
		return weechat::WEECHAT_RC_OK unless $bar_infos;

		my @all_windows = Nlib::i2h('window');
		my $in_any_win;
		for (@all_windows) {
			$in_any_win = $_ if Nlib::in_window($row, $col, $_);
		}

		$col -= $bar_infos->[0]{x};
		$row -= $bar_infos->[0]{y};

		weechat::print('', join ' :: ', $bar_infos->[-1]{name},
					   (map { defined $_ ? $_ : '(undef)' }
						Nlib::bar_item_get_item_and_subitem_at
						($bar_infos, $col, $row))) if DEBUG_MENU;

		return mouse_nicklist(@_[0..2], $bar_infos, $in_any_win, $col, $row)
			if $bar_infos->[-1]{name} eq 'nicklist';

		return weechat::WEECHAT_RC_OK
			unless $bar_infos->[-1]{name} =~ '_menu$';

		return mouse_evt_barcode($bar_infos, undef, $_[2],
			Nlib::bar_item_get_subitem_at($bar_infos, qr/_menu\b/, $col, $row));

	}
    weechat::WEECHAT_RC_OK
}

sub mouse_evt_barcode {
	my ($bar_infos, undef, undef, $error, $idx, $item) = @_;
	my $close_menu_in_empty = qr/_menu\b/; # qr/\bmain_menu\b/;
	if ($error) {
		open_menu() # closes the menu here
			if ($MENU_OPEN && !defined $idx && $bar_infos->[-1]{name} =~ $close_menu_in_empty && $_[2] =~ /^#/);

		if (DEBUG_MENU) {
			$idx = '(undef)' unless defined $idx;
			$item = '(undef)' unless defined $item;
			weechat::print('', "thing: $error @ $idx [ $item ]");
		}
		return weechat::WEECHAT_RC_OK;
	}
	if ($bar_infos->[-1]{name} =~ /\bmain_menu\b/) {
		open_menu() unless $MENU_OPEN;
		if ($ACT_MENU{main} == $idx && $MENU_OPEN == 2 && $_[2] =~ /^#/
		   ) {
			#open_menu();
			#return weechat::WEECHAT_RC_OK
		}
		menu_input_run('', '', '/input switch_active_buffer')
			while ($MENU_OPEN > 1);
		$ACT_MENU{main} = $idx;
		update_main_menu();
		menu_input_run('', '', '/input return') if $_[2] =~ /^#/;
	}
	elsif ($bar_infos->[-1]{name} =~ /\bsub_menu\b/) {
		open_menu() unless $idx;
		$ACT_MENU{sub} = $idx-1 if $idx;
		update_sub_menu();
		menu_input_run('', '', '/input return') if $_[2] =~ /^#/;
	}
	elsif ($bar_infos->[-1]{name} =~ /\bwindow_popup_menu\b/) {
		open_menu() unless $idx;
		$ACT_MENU{window_popup} = $idx-1 if $idx;
		update_window_popup_menu();
		menu_input_run('', '', '/input return') if $_[2] =~ /^#/;
	}
	weechat::WEECHAT_RC_OK
}

sub hsignal_evt {
	my %data = %{$_[2]};
	return mouse_nicklist_barcode(undef,
		undef,
		'#',
		$data{_buffer}, $data{nick})
			if $data{_bar_name} eq 'nicklist';
	mouse_evt_barcode([+{ name => $data{_bar_name} }],
		undef,
		'#',
		$data{_bar_item_name} ne $data{_bar_name},
		$data{_bar_item_name} ? $data{_bar_item_line} : undef);
}

## SUB_MENU -- return sub menu items
sub SUB_MENU {
	my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
	my @menu_entries = 	Nlib::i2h('option', '', 'menu.var.*');
	my ($main_menu_id) =
	map { $_->{option_name} =~ /^(\d+)[.]/ && $1 }
	grep { $_->{option_name} =~ /^\d+[.]name$/ && $_->{value} eq $active_main_menu }
	@menu_entries;
	map { $_->{value} }
	grep { $_->{option_name} =~ /^$main_menu_id[.]\d+[.]name$/ }
	@menu_entries
	#('Connect to &server', 'Open new &window', '&Close window', '&Leave WeeChat')
}

## WINDOW_POPUP_MENU -- return popup menu items
sub WINDOW_POPUP_MENU {
	return () unless $POPUP_MENU;
	map { $_->{value} }
	grep { $_->{option_name} =~ /^\Q$POPUP_MENU\E[.]\d+[.]name$/ }
	Nlib::i2h('option', '', "menu.var.$POPUP_MENU.*")
}

## exec_submenu -- run command of active sub menu item
sub exec_submenu {
	my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
	my $active_sub_menu = (SUB_MENU())[$ACT_MENU{sub}];
	my @menu_entries = 	Nlib::i2h('option', '', 'menu.var.*');
	my ($main_menu_id) =
	map { $_->{option_name} =~ /^(\d+)[.]/ && $1 }
	grep { $_->{option_name} =~ /^\d+[.]name$/ && $_->{value} eq $active_main_menu }
	@menu_entries;
	my ($sub_menu_id) =
	map { $_->{option_name} =~ /^\d+[.](\d+)[.]/ && $1 }
	grep { $_->{option_name} =~ /^$main_menu_id[.]\d+[.]name$/ && $_->{value} eq $active_sub_menu }
	@menu_entries;
	my ($command) =
	map { $_->{value} }
	grep { $_->{option_name} =~ /^$main_menu_id[.]$sub_menu_id[.]command$/ }
	@menu_entries;
	local $MENU_OPEN;
	weechat::command(weechat::current_buffer(), $command) if $command
}

## exec_popupmenu -- run command of active popup menu item
sub exec_popupmenu {
	my $active_popup_entry = (WINDOW_POPUP_MENU())[$ACT_MENU{window_popup}];
	my @menu_entries = Nlib::i2h('option', '', "menu.var.$POPUP_MENU.*");
	my ($popup_entry_id) =
	map { $_->{option_name} =~ /^\Q$POPUP_MENU\E[.](\d+)[.]/ && $1 }
	grep { $_->{option_name} =~ /^\Q$POPUP_MENU\E[.]\d+[.]name$/ && $_->{value} eq $active_popup_entry }
	@menu_entries;
	my ($command) =
	map { $_->{value} }
	grep { $_->{option_name} =~ /^\Q$POPUP_MENU\E[.]$popup_entry_id[.]command$/ }
	@menu_entries;
	$command =~ s/\$(\d)/$POPUP_MENU_ARGS->[$1]/g if $command;
	local $MENU_OPEN;
	weechat::command($POPUP_MENU_BUFFER, $command) if $command
}

## bar_item_sub_menu -- return sub menu as bar items
sub bar_item_sub_menu {
	my @items = SUB_MENU();
	my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
	$active_main_menu =~ y/&//d;
	make_menu(\@items, \$ACT_MENU{sub}, '==>', '', $active_main_menu);
}

## bar_item_window_popup_menu -- return popup menu as bar items
sub bar_item_window_popup_menu {
	my @items = WINDOW_POPUP_MENU();
	my $title = $POPUP_MENU_ARGS && @$POPUP_MENU_ARGS ? $POPUP_MENU_ARGS->[0] : '';
	make_menu(\@items, \$ACT_MENU{window_popup}, '==>', '', $title);
}

## bar_item_menu_help -- return help bar for menu operation
sub bar_item_menu_help {
	return '' unless $MENU_OPEN;
	join "\n",
		'Use the arrow '.($MENU_OPEN > 1 ? 'up/down' : 'left/right').' keys or highlighted shortcuts to '.
		'select a menu entry,',
		'C-x to close menu',
		'C-h to toggle the help window',
		'RET to open'
}

## close_menu -- close main menu
sub close_menu {
	my $last_open_menu = $MENU_OPEN;
	$MENU_OPEN = undef;
	weechat::bar_set(weechat::bar_search('menu_help'), 'hidden', 1);
	weechat::bar_set(weechat::bar_search('main_menu'), 'hidden', 1) if weechat::config_is_set_plugin('main_menu_hidden') && Nlib::has_true_value(weechat::config_get_plugin('main_menu_hidden'));
	update_main_menu();
	if ($last_open_menu && $last_open_menu == 3 && $POPUP_MENU eq 'nick') {
		weechat::command(weechat::current_buffer(), "/bar scroll nicklist * x+$LAST_NICKLIST_RESCROLL_X") if $LAST_NICKLIST_RESCROLL_X;
		weechat::command(weechat::current_buffer(), "/bar scroll nicklist * y+$LAST_NICKLIST_RESCROLL_Y") if $LAST_NICKLIST_RESCROLL_Y;
		($LAST_NICKLIST_RESCROLL_X, $LAST_NICKLIST_RESCROLL_Y) = (0, 0);
	}
	Nlib::unhook_dynamic('1200|/input *', 'menu_input_run');
	Nlib::unhook_dynamic('input_text_content', 'menu_input_text');
	Nlib::unhook_dynamic('input_text_display_with_cursor', 'menu_input_text_display');
}


## close_window_popup_menu -- close popup menu and clean up after feature extensions (nicklist)
sub close_window_popup_menu {
	weechat::bar_set(weechat::bar_search('window_popup_menu'), 'hidden', 1);
	$ACT_MENU{window_popup} = undef;
	if ($LAST_NICK_COLOR && $POPUP_MENU eq 'nick') {
		weechat::nicklist_nick_set(@$LAST_NICK_COLOR);
		$LAST_NICK_COLOR = undef
	}
}

sub expand_dynamic_menus {
	my (@menu_entries, $key);
	if ($MENU_OPEN == 2) {
		my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
		@menu_entries = Nlib::i2h('option', '', 'menu.var.*');
		my ($main_menu_id) =
		map { $_->{option_name} =~ /^(\d+)[.]/ && $1 }
		grep { $_->{option_name} =~ /^\d+[.]name$/ && $_->{value} eq $active_main_menu }
		@menu_entries;
		$key = $main_menu_id;
	}
	elsif ($MENU_OPEN == 3) {
		@menu_entries = Nlib::i2h('option', '', "menu.var.$POPUP_MENU.*");
		$key = quotemeta $POPUP_MENU;
	}
	my %opt_table;
	for (map { [ $_->{option_name}, $_->{value} ] }
		 grep { $_->{option_name} =~ /^$key[.]\d+[.](?:name|command)$/ }
		 @menu_entries) {
		my ($pfx, $dig, $t) = $_->[0] =~ /^(.*)[.](\d+)[.](name|command)$/;
		$opt_table{$dig}{$t} = [ $pfx, $_->[1] ];
	}
	for my $dig (sort keys %opt_table) {
		next if exists $opt_table{$dig}{name};
		next unless $opt_table{$dig}{command}[1] =~ /^%/;
		my $pfx = $opt_table{$dig}{command}[0];
		my $raw = $dig . '090';
		weechat::command('', "/mute /unset menu.var.$pfx.$raw*");
		# %#info_hashtable
		# %gui_buffers.buffer<50% ${buffer.number} ${buffer.name} % /buffer ${buffer.number}
		my (undef, $hdata, $name, $command) = split /\s?%\s?/, $opt_table{$dig}{command}[1], 4;
		my $limit;
		($hdata, $limit) = split /</, $hdata, 2;

		if ($hdata =~ s/^#//) { # info_hashtable case
			my $r = weechat::info_get_hashtable($hdata, +{ name => $name, command => $command });
			for my $k (sort keys %$r) {
				next unless $k =~ /^(\d+)[.](?:name|command)$/;
				weechat::command('', "/mute /set menu.var.$pfx.$raw$k ${$r}{$k}");
			}

			next; ###
		}

		my @hdata = Nlib::hdh(split '[.]', $hdata);
		my @a = (undef, 1..9, 0, 'a'..'z');
		my $i = 0;
		while ($hdata[0]) {
			$i = sprintf '%04d', $i + 1;
			my %pointer = reverse @hdata;
			my %vars = (i => 0+$i, a => ($i < @a ? $a[$i] : ' '));
			weechat::command('', "/mute /set menu.var.$pfx.$raw$i.name @{[weechat::string_eval_expression($name, \%pointer, \%vars)]}");
			weechat::command('', "/mute /set menu.var.$pfx.$raw$i.command @{[weechat::string_eval_expression($command, \%pointer, \%vars)]}");
			@hdata = Nlib::hdh(@hdata, '!var_next');
			last if defined $limit && $i >= $limit;
		}
	}
}

## open_menu -- open main menu or close main and sub menu if already open
## () - command handler
## $_[1] - buffer
## $_[2] - arguments
sub open_menu {
	if ($_[2] && $_[2] eq 'reset') {
		initial_menus(1);
		return weechat::WEECHAT_RC_OK;
	}
	elsif ($_[2] && $_[2] =~ /^\s*help\s*$/i) {
		Nlib::read_manpage(SCRIPT_FILE, SCRIPT_NAME);
		return weechat::WEECHAT_RC_OK
	}
	my @args;
	@args = split ' ', $_[2]
		if $_[2];
	if ($MENU_OPEN && !@args) {
		close_window_popup_menu() if $MENU_OPEN == 3;
		close_submenu() if $MENU_OPEN == 2;
		close_menu();
		return weechat::WEECHAT_RC_OK;
	}
	Nlib::hook_dynamic('command_run', '1200|/input *', 'menu_input_run', '');
	Nlib::hook_dynamic('modifier', 'input_text_content', 'menu_input_text', '');
	Nlib::hook_dynamic('modifier', 'input_text_display_with_cursor', 'menu_input_text_display', '');
	unless (@args) {
		$MENU_OPEN = 1;
		weechat::bar_set(weechat::bar_search('main_menu'), 'hidden', 0);
	}
	elsif ($args[0]) {
		my @menu_entries = Nlib::i2h('option', '', "menu.var.$args[0].*");
		if ($args[0] eq 'nick' && !@menu_entries && $LAST_NICK_COLOR) {
			weechat::nicklist_nick_set(@$LAST_NICK_COLOR);
			$LAST_NICK_COLOR = undef
		}
		return weechat::WEECHAT_RC_OK
			unless @menu_entries;
		$POPUP_MENU_BUFFER = $_[1];
		$POPUP_MENU = $args[0];
		$POPUP_MENU_ARGS = [ @args[1..$#args] ];
		close_submenu() if $MENU_OPEN && $MENU_OPEN == 2;
		$MENU_OPEN = 3;
		expand_dynamic_menus();
		$ACT_MENU{window_popup} = 0;
		weechat::bar_set(weechat::bar_search('window_popup_menu'), 'hidden', 0);
		update_window_popup_menu();
	}
	weechat::bar_set(weechat::bar_search('menu_help'), 'hidden', 0) if !weechat::config_is_set_plugin('active_help') || Nlib::has_true_value(weechat::config_get_plugin('active_help'));
	update_main_menu();
	update_menu_help();
	if (@args && $args[0] eq 'nick' && $POPUP_MENU eq 'nick') {
		weechat::command(weechat::current_buffer(), "/bar scroll nicklist * x+$NICKLIST_RESCROLL_X") if $NICKLIST_RESCROLL_X;
		weechat::command(weechat::current_buffer(), "/bar scroll nicklist * y+$NICKLIST_RESCROLL_Y") if $NICKLIST_RESCROLL_Y;
		($LAST_NICKLIST_RESCROLL_X, $LAST_NICKLIST_RESCROLL_Y) =
			($NICKLIST_RESCROLL_X, $NICKLIST_RESCROLL_Y);
		($NICKLIST_RESCROLL_Y, $NICKLIST_RESCROLL_X) = (0, 0);
	}
	weechat::WEECHAT_RC_OK
}

## close_submenu -- close sub menu (does not reset $MENU_OPEN counter)
sub close_submenu {
	$ACT_MENU{sub} = undef;
	my $bar = weechat::bar_search('sub_menu');
	weechat::bar_set($bar, 'hidden', 1);
	weechat::bar_set($bar, 'separator', 1);
	update_menu_help();
	weechat::WEECHAT_RC_OK
}

## open_submenu -- open sub menu (does not reset $MENU_OPEN counter)
sub open_submenu {
	expand_dynamic_menus();
	$ACT_MENU{sub} = 0;
	my $bar = weechat::bar_search('sub_menu');
	weechat::bar_set($bar, 'hidden', 0);
	weechat::bar_set($bar, 'separator', 0) unless (Nlib::i2h('bar', weechat::bar_search('menu_help')))[0]{hidden};
	update_sub_menu();
	update_menu_help();
	weechat::WEECHAT_RC_OK
}

## setup_menu_bar -- create bars with bar menu items
sub setup_menu_bar {
	if (my $bar = weechat::bar_search('main_menu')) {
		weechat::bar_set($bar, 'hidden', 0);
		weechat::bar_set($bar, 'items', '*,main_menu') unless (Nlib::i2h('bar', $bar))[0]{items} =~ /\bmain_menu\b/;
	}
	else {
		weechat::bar_new('main_menu', 'off', 10000, 'root', '', 'top', 'horizontal', 'vertical', 0, 0, 'gray', 'lightblue', 'darkgray', 'off', '*,main_menu');
	}
	if (my $bar = weechat::bar_search('sub_menu')) {
		weechat::bar_set($bar, 'hidden', 1);
		weechat::bar_set($bar, 'items', '*sub_menu') unless (Nlib::i2h('bar', $bar))[0]{items} =~ /\bsub_menu\b/;
	}
	else {
		weechat::bar_new('sub_menu', 'on', 9999, 'root', '', 'top', 'columns_vertical', 'vertical', 0, 0, 'black', 'lightmagenta', 'gray', 'on', '*sub_menu');
	}
	if (my $bar = weechat::bar_search('menu_help')) {
		weechat::bar_set($bar, 'hidden', 1);
		weechat::bar_set($bar, 'items', 'menu_help') unless (Nlib::i2h('bar', $bar))[0]{items} =~ /\bmenu_help\b/;
	}
	else {
		weechat::bar_new('menu_help', 'on', 9998, 'root', '', 'top', 'horizontal', 'vertical', 0, 0, 'darkgray', 'default', 'gray', 'on', 'menu_help');
	}

	if (my $bar = weechat::bar_search('window_popup_menu')) {
		weechat::bar_set($bar, 'hidden', 1);
		weechat::bar_set($bar, 'items', '*window_popup_menu') unless (Nlib::i2h('bar', $bar))[0]{items} =~ /\bwindow_popup_menu\b/;
	}
	else {
		weechat::bar_new('window_popup_menu', 'on', 0, 'window', 'active', 'bottom', 'columns_vertical', 'vertical', 0, 0, 'black', 'lightmagenta', 'gray', 'on', '*window_popup_menu');
	}

	weechat::WEECHAT_RC_OK
}

## invalidate_popup_buffer -- delete popup buffer ptr if buffer is closed
## () - signal handler
## $bufptr - signal comes with pointer of closed buffer
sub invalidate_popup_buffer {
	my (undef, undef, $bufptr) = @_;
	$POPUP_MENU_BUFFER = weechat::current_buffer()
		if $bufptr eq $POPUP_MENU_BUFFER;
	weechat::WEECHAT_RC_OK
}

## config_create_opt -- create config option callback
## () - callback handler
## $_[3] - option name
sub config_create_opt {
	return weechat::WEECHAT_CONFIG_OPTION_SET_OPTION_NOT_FOUND unless
		$_[3] =~ /^(?:\w+[.])?\d+[.](?:name|command)$/;
	weechat::config_new_option(@_[1..$#_-1], 'string', '', '', 0, 0, '', $_[-1], 0, '', '', '', '', '', '');
	weechat::WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE
}

## load_config -- create and read menu config file
sub load_config {
	$CFG_FILE = weechat::config_new(SCRIPT_NAME, '', '');
	$CFG_FILE_SECTION = weechat::config_new_section($CFG_FILE, 'var', 1, 1, '', '', '', '', '', '', 'config_create_opt', '', '', '');
	weechat::config_read($CFG_FILE);
	weechat::WEECHAT_RC_OK
}

## hide_menu_bar -- hide all the menu bars
sub hide_menu_bar {
	setup_menu_bar();
	weechat::bar_set(weechat::bar_search('main_menu'), 'hidden', 1);
	weechat::bar_set(weechat::bar_search('sub_menu'), 'hidden', 1);
	weechat::bar_set(weechat::bar_search('menu_help'), 'hidden', 1);
	weechat::bar_set(weechat::bar_search('window_popup_menu'), 'hidden', 1);
	weechat::WEECHAT_RC_OK
}

## update_sub_menu -- update sub menu bar item
sub update_sub_menu {
	weechat::bar_item_update('sub_menu');
	#weechat::bar_update('sub_menu');
	weechat::WEECHAT_RC_OK
}

## update_main_menu -- update main menu bar item
sub update_main_menu {
	weechat::bar_item_update('main_menu');
	#weechat::bar_update('sub_menu');
	weechat::WEECHAT_RC_OK
}

## update_menu_help -- update menu help bar item
sub update_menu_help {
	weechat::bar_item_update('menu_help');
	weechat::WEECHAT_RC_OK
}

## update_window_popup_menu -- update window popup menu bar item
sub update_window_popup_menu {
	weechat::bar_item_update('window_popup_menu');
	weechat::WEECHAT_RC_OK
}

## script_config -- check config in plugin namespace
sub script_config {
	weechat::bar_set(weechat::bar_search('main_menu'), 'hidden', (!$MENU_OPEN || $MENU_OPEN > 2) && weechat::config_is_set_plugin('main_menu_hidden') && Nlib::has_true_value(weechat::config_get_plugin('main_menu_hidden')) ? 1 : 0);
	update_main_menu() if (!$MENU_OPEN || $MENU_OPEN > 2);
	weechat::WEECHAT_RC_OK
}

## menu_config -- what is to do on updates in menu option
sub menu_config {
	update_window_popup_menu();
	update_sub_menu();
	update_main_menu();
	weechat::WEECHAT_RC_OK
}

sub initial_menus {
	weechat::command('', '/mute /unset menu.var.*') if $_[0];
	my @menu_entries = Nlib::i2h('option', '', 'menu.var.*');
	return if @menu_entries;
	my %initial_menu = (
		'1.1.command' => '/close',
		'1.1.name' => '&Close buffer',
		'1.2.command' => '/quit',
		'1.2.name' => '&Quit WeeChat',
		'1.name' => '&File',
		'2.1.command' => '/window splith',
		'2.1.name' => 'Split &horizontally',
		'2.2.command' => '/window splitv',
		'2.2.name' => 'Split &vertically',
		'2.3.command' => '/window zoom',
		'2.3.name' => '&Maximize / Restore',
		'2.4.command' => '/window merge',
		'2.4.name' => '&Close the other window',
		'2.5.command' => '/window merge all',
		'2.5.name' => 'Close &all other windows',
		'2.name' => '&Window',
		'3.1.command' => '/xfer',
		'3.1.name' => 'Transfer &list',
		'3.name' => '&DCC',
		'4.1.command' => '/copywin',
		'4.1.name' => '&Copy window',
		'4.2.command' => '/copywin /',
		'4.2.name' => '&URL highlight window',
		'4.3.command' => '/coords_shell',
		'4.3.name' => '&Perl debug shell',
		'4.4.command' => '/iset',
		'4.4.name' => '&Settings editor',
		'4.name' => '&Tools',
		'5.1.command' => '%irc_servers.irc_server% ${irc_server.name} % /connect ${irc_server.name}',
		'5.name' => '&Connect',
		'6.1.command' => '%gui_buffers.buffer% ${i} ${buffer.name} % /buffer ${buffer.full_name}',
		'6.name' => '&Buffers',
		'7.1.command' => '%gui_windows.window% ${window.number} ${window.buffer.name} % /window ${window.number}',
		'7.name' => 'Win&list',
		'9.1.name' => 'Menu system by Nei',
		'9.2.name' => '&Help',
		'9.2.command' => '/menu help',
		'9.name' => '&About',
		'nick.1.command' => '/query $0',
		'nick.1.name' => '&Query',
		'nick.2.command' => '/wii $0',
		'nick.2.name' => '&Whois',
		'nick.3.command' => '/op $0',
		'nick.3.name' => '&Op',
		'nick.4.command' => '/voice $0',
		'nick.4.name' => '&Voice',
		'nick.5.command' => '/kick $0',
		'nick.5.name' => '&Kick',
		'nick.6.command' => '/ban $0',
		'nick.6.name' => '&Ban',
		'buffer1.1.command' => '/buffer close',
		'buffer1.1.name' => '&Close',
		'buffer1.2.command' => '/buffer clear',
		'buffer1.2.name' => 'Clea&r',
		'buffer1.3.command' => '/buffer unmerge',
		'buffer1.3.name' => '&Unmerge',
		'buffer1.4.command' => '/buffer notify none',
		'buffer1.4.name' => '&Ignore',
		'buffer1.5.command' => '/buffer notify reset',
		'buffer1.5.name' => 'U&nignore',
		'buffer2.1.command' => '/buffer close $1-$2',
		'buffer2.1.name' => '&Close range',
		'buffer2.2.command' => '/buffer swap $1 $2',
		'buffer2.2.name' => '&Swap',
		'buffer2.3.command' => '/buffer merge $2',
		'buffer2.3.name' => '&Merge',
	);
	weechat::config_new_option($CFG_FILE, $CFG_FILE_SECTION, $_, 'string', '', '', 0, 0, '', $initial_menu{$_}, 0, '', '', '', '', '', '') for sort keys %initial_menu;
	#weechat::command('', '/key bind meta2-P /menu');
}

sub init_menu {
	$ACT_MENU{main} = 0;
	$POPUP_MENU_BUFFER = weechat::current_buffer();
	load_config();
	initial_menus();
	setup_menu_bar();
	script_config();
	update_main_menu();
	weechat::WEECHAT_RC_OK
}

sub stop_menu {
	hide_menu_bar();
	weechat::config_write($CFG_FILE);
	weechat::config_section_free_options($CFG_FILE_SECTION);
	weechat::config_section_free($CFG_FILE_SECTION);
	weechat::config_free($CFG_FILE);
	weechat::WEECHAT_RC_OK
}
