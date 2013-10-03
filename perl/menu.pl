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

=begin comment

first, copy the file to your
F<.weechat/perl> directory. Then you can type

  /perl load menu.pl

in weechat to load the script.

=end comment

Use

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
signals. You need WeeChat with builtin cursor and mouse
support.

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
to server) due to the missing implementation of a interactive command.

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

=begin comment

=head1 FUNCTION DESCRIPTION

for full pod documentation, filter this script with

  perl -pE'
  (s/^## (.*?) -- (.*)/=head2 $1\n\n$2\n\n=over\n/ and $o=1) or
   s/^## (.*?) - (.*)/=item I<$1>\n\n$2\n/ or
  (s/^## (.*)/=back\n\n$1\n\n=cut\n/ and $o=0,1) or
  ($o and $o=0,1 and s/^sub /=back\n\n=cut\n\nsub /)'

=end comment

=cut

use constant SCRIPT_NAME => 'menu';
our $VERSION = '0.9';

#$$$ autoloaded{
BEGIN { { package WeeP::Tie::hash_accessor;
  use strict; use warnings;
  use Carp;
  use parent 'Tie::Hash';
  sub TIEHASH {
	  my $class = shift;
	  my (undef, $P) = @_;
	  bless +{ proxy => $P }, $class;
  }
  sub FETCH {
	  my $self = shift->_init;
	  my $key = shift;
	  croak "Attempt to access non-existent key '$key' in hdata '$${$self->{proxy}}{ns}[-1]'"
		  unless exists $self->{visible_keys}{$key};
	  $self->{visible_keys}{$key}->()
  }
  ## method _s_o -- spawn new object or hdata object
  ## $_s - name of class or hdata
  ## $_o - object pointer
  sub _s_o {
	  my $self = shift;
	  my ($name, $o) = @_;
	  return $o unless $o;

	  my $nbase = (ref $self->{proxy})->new;

	  my $name_ = $name . '_';
	  my $O = eval { local $SIG{__DIE__}; $nbase->$name_ };
	  if ($@) {
		  $O = $nbase->hdata_;
		  push @{ $$O->{ns} }, $name;
	  }
	  $O->_o($o)
  }
  sub _init {
	  my $self = shift;
	  return $self if $self->{visible_keys};

	  my $P = $self->{proxy};
	  my $nbase = (ref $P)->new;

	  $self->{hdata} //= $nbase->hdata_get($$P->{ns}[-1]);
	  $self->{visible_keys} = $self->{hdata} ? +{
		  map {
			  my $key = $_;
			  my $array = $self->{hdata}->get_var_array_size_string('', $key);
			  my $type = $self->{hdata}->get_var_type_string($key);
			  my $name = $self->{hdata}->get_var_hdata($_) || 'void_ptr' if $type eq 'pointer';
			  if ($array) {
				  my @array_accessor;
				  tie @array_accessor, 'WeeP::Tie::hdata_var_array', $self, $key, $array, $type, $name;
				  ( $key => sub { \@array_accessor } )
			  }
			  elsif ($type eq 'pointer') {
				  ( $key => sub { $self->_s_o($name,
											  $self->{hdata}->$type($P, $key)); } )
			  }
			  else {
				  ( $key => sub { $self->{hdata}->$type($P, $key) } )
			  }
		  } split ',', $self->{hdata}->get_string('var_keys')
	  }

		  :

	  $$P->{ns}[-1] eq 'hdata' ? do {
		  my $name = 'void_ptr';
		  for ($nbase->_infolist('hook', '', 'hdata')) {
			  if ($nbase->hdata_get($_->{hdata_name}) eq $P) {
				  $name = $_->{hdata_name};
				  last
			  }
		  }
		  +{
			  map {
				  my $key = $_;
				  ( $key => sub { $self->_s_o($name, $P->get_list($key)) } )
			  } split ',', $P->get_string('list_keys')
		  }
	  }

		  :

      +{};
	  $self
  }
  sub STORE {
	  my $self = shift->_init;
	  my $key = shift;
	  my $value = shift;
	  if ($self->{hdata}->update('', +{ __update_allowed => $key })) {
		  $self->{hdata}->update($self->{proxy}, +{ $key => $value })
	  }
	  else {
		  $self->{proxy}->set($key, $value);
	  }
  }
  sub EXISTS {
	  my $self = shift->_init;
	  my $key = shift;
	  exists $self->{visible_keys}{$key}
  }
  sub FIRSTKEY {
	  my $self = shift->_init;
	  my $a = keys %{$self->{visible_keys}}; # reset
	  $self->NEXTKEY(@_)
  }
  sub NEXTKEY {
	  my $self = shift->_init;
	  my $k = each %{$self->{visible_keys}};
	  wantarray ? ($k, $self->FETCH($k)) : $k
  }
  sub SCALAR {
	  my $self = shift->_init;
	  scalar keys %{$self->{visible_keys}}
  }
1}

{ package WeeP::Tie::hdata_var_array;
  use strict; use warnings;
  use parent 'Tie::Array';
  sub TIEARRAY {
	  my $class = shift;
	  my ($parent, $key, $sizekey, $type, $name) = @_;
	  bless +{
		  parent  => $parent,
		  key 	  => $key,
		  sizekey => $sizekey,
		  type 	  => $type,
		  name 	  => $name,
	  }, $class
  }
  sub FETCH {
	  my $self = shift;
	  my $idx = shift;
	  my $type = $self->{type};
	  my $key = join '|', $idx, $self->{key};
	  my $rv = $self->{parent}{hdata}->$type($self->{parent}{proxy}, $key);
	  if ($type eq 'pointer') {
		  $self->{parent}->_s_o($self->{name}, $rv);
	  }
	  else {
		  $rv
	  }
  }
  sub FETCHSIZE {
	  my $self = shift;
	  exists $self->{parent}{proxy}{ $self->{sizekey} } ?
		  $self->{parent}{proxy}{ $self->{sizekey} } :
		  $self->{parent}{hdata}->get_var_array_size($self->{parent}{proxy}, $self->{key})
  }

1}

{ package WeeP::Tie::hdata_list;
  use strict; use warnings;
  use Carp;
  use parent 'Tie::Array';
  BEGIN { our $NEGATIVE_INDICES = 1 }
  sub TIEARRAY {
	  my $class = shift;
	  my ($parent) = @_;
	  bless +{
		  parent  => $parent,
	  }, $class
  }
  sub FETCH {
	  my $self = shift;
	  my $idx = shift;
	  my $P = $self->{parent}{proxy};
	  my $nbase = (ref $P)->new;

	  if ($self->{parent}{hdata} //= $nbase->hdata_get($$P->{ns}[-1])) {
		  my $o = $self->{parent}{hdata}->move($P, $idx);
		  return $o unless $o;
		  my $O = (ref $P)->new;
		  $$O->{ns} = [ @{ $$P->{ns} } ];
		  $O->_o($o)
	  }
	  else {
		  croak "Attempt to access non-existent hdata in '$${$P}{ns}[-1]'"
	  }
  }
  sub FETCHSIZE { 0 }
1}

{ package Weechat;
  use strict; use warnings;
  use Carp;
  use Hash::Util;
  use Scalar::Util qw(weaken);
  use overload (
	  fallback => 1,
	  '""' => sub {
		  my $I = shift;
		  $$I->{o} // join '', ref $I, '::', join '_', @{ $$I->{ns} }
	  },
	  '%{}' => sub { ${+shift}->{_hdata} },
	  '@{}' => sub { ${+shift}->{_hdata_move} },
	 );

  my ($pkg, %TypeMap, %AdviceReturn, %AdviceCallback, %_object_table);
  BEGIN {
	  $pkg = 'weechat::';
	  %TypeMap = (
		  b => 'buffer',
		  s => 'string',
		  c => 'config_option',
		  w => 'window',
		  i => 'infolist',
		  h => 'hdata',
		  C => 'WEECHAT',
		  F => 'config', # _file
		  S => 'config_section',
		  B => 'bar',
		 );
	  Hash::Util::lock_hash(%TypeMap);
	  %AdviceReturn = (
		  infolist_get 		 => 'i',
		  hdata_get 		 => 'h',
		  config_get 		 => 'c',
		  current_window 	 => 'w',
		  current_buffer 	 => 'b',
		  buffer_new 		 => 'b',
		  buffer_search		 => 'b',
		  buffer_search_main => 'b',
		  config_new => 'F',
		  config_new_section => 'S',
		  bar_search => 'B',
		  bar_new => 'B',
		 );
	  Hash::Util::lock_hash(%AdviceReturn);
	  %AdviceCallback = (
		  hook_command => '.....cd|xb.',
		  buffer_new   => '.cdcd|xb.|xb',
		 );
	  Hash::Util::lock_hash(%AdviceCallback);
  }


  sub AUTOLOAD {
	  our $AUTOLOAD;
	  return if '::DESTROY' eq substr $AUTOLOAD, -9;

	  my $I = $_[0];
	  if (!ref $I && $AUTOLOAD eq __PACKAGE__.'::new') {
		  my $O = bless \ +{
			  ns => [],
			  o => undef,
			  _hdata => {},
			  _hdata_move => [],
		  }, $I;
		  tie @{ $$O->{_hdata_move} }, 'WeeP::Tie::hdata_list',
			  tie %{ $$O->{_hdata} }, 'WeeP::Tie::hash_accessor', '__auto__', $O;
		  return $O
	  }
	  if (ref $I) {
		  my ($fn) = $AUTOLOAD =~ /::(.*)/;
		  if ($fn =~ s/_$//) {
			  my %MapType = reverse %TypeMap;
			  exists $MapType{$fn} || croak "Unknown namespace: $fn";
			  return $I->ns($MapType{$fn})
		  }

		  unless (defined $$I->{o}) { shift }
		  my @ns = @{ $$I->{ns} };
		  do {
			  my $n = join '_', @ns, $fn;
			  my $sub = $pkg . $n;
			  if (exists &$sub) {
				  if (exists $AdviceCallback{$n}) {
					  my ($mangle, @bless) = split /\|/, $AdviceCallback{$n};
					  my $i = 0;
					  my @c;
					  for my $x (split //, $mangle) {
						  next if $x eq '.';
						  if ($x eq 'c') {
						      push @c, length $_[$i] ?
							  splice @_, $i, 1, '::'.(ref $I).'::GenericCallback' : '';
						  }
						  elsif ($x eq 'd') {
						      splice @_, $i, 1, join '|', shift @bless, shift @c, $_[$i];
						  }
					  }
					  continue {
						  ++$i;
					  }
				  }
				  if (exists $AdviceReturn{$n}) {
					  no strict 'refs';
					  return (ref $I)->new->na($AdviceReturn{$n} => &$sub);
				  }
				  goto &$sub;
			  }
		  } while pop @ns;
		  croak "Method \"$fn\" not found in namespace \"$pkg@{[ join '_', @{ $$I->{ns} } ]}\"";
	  }
	  croak "Invalid call to &$AUTOLOAD";
  }

  ## method na -- bless strings into namespace objects
  ## $_[0] - namespace letter format string
  ## @_[1..$#_] - arguments
  ## returns arguments
  sub na {
      my $I = shift;
      croak "Cannot call method na on an existing namespace ($pkg@{[ join '_', @{ $$I->{ns} } ]})" if @{$$I->{ns}};
      my @format = split '', +shift;
      my $i = 0;
      for my $e (@_) {
	  next if $format[$i] eq '.';
	  $e = $I->ns($format[$i])->_o($e);
      }
      continue {
	  ++$i;
      }
      @format == 1 ? $_[0] : @_ > 1 ? @_ : return
  }

  ## method ns -- get namespace handler
  ## $f - namespace letter
  ## returns handler
  sub ns {
      my $I = shift;
      croak "Cannot call method ns on an existing namespace ($pkg@{[ join '_', @{ $$I->{ns} } ]})" if @{$$I->{ns}};
      my $f = shift;
      exists $TypeMap{$f} || croak "Invalid format: $f";
      my $t = $TypeMap{$f};
      my $O = (ref $I)->new;
      $$O->{ns} = [ split '_', $t ];
      $O
  }

  ## mutator method _o -- set object address
  ## returns the new object to be used
  ## usage: $obj = $obj->_o($addr)
  sub _o {
      my $I = shift;
      croak "Cannot call method _o on an existing object ($pkg@{[ join '_', @{ $$I->{ns} } ]}#@{[ $$I->{o} ]})" if $$I->{o};
      $$I->{o} = shift;
      unless ($_object_table{$I}) {
	  $_object_table{$I} = $I;
	  weaken $_object_table{$I};
      }
      $_object_table{$I}
  }

  ## method _infolist -- copy weechat infolist content into perl hash
  ## $infolist - name of the infolist in weechat [ONLY when called on base class]
  ## $ptr - pointer argument (infolist dependend) [ONLY when called on base class or namespace]
  ## @args - arguments to the infolist (list dependend)
  ## $fields - string of ref type "fields" if only certain keys are needed (optional)
  ## returns perl list with perl hashes for each infolist entry
  sub _infolist {
	  my $I = shift;
	  my %i2htm = (i => 'integer', s => 'string', p => 'pointer', b => 'buffer', t => 'time');
	  local *weechat::infolist_buffer = sub { '(not implemented)' }; weechat::infolist_buffer();

	  my $name = @{$$I->{ns}} ?
	      ($$I->{ns}[0] eq 'hdata' ? $$I->{ns}[-1] : join '_', @{ $$I->{ns} })
		  : shift;
	  my $ptr = $$I->{o} ? $I : shift;
	  $ptr ||= "";

	  my $fields = ref $_[-1] eq 'fields' ? ${ +pop } : undef;
	  my $infptr = (ref $I)->new->infolist_get($name, $ptr, join ',', @_);
	  my @infolist;
	  while ($infptr->next) {
		  my @fields = map {
			  my ($t, $v) = split ':', $_, 2;
			  bless \$v, $i2htm{$t};
		  } split ',', ($fields || $infptr->fields);

		  push @infolist, +{ do {
			  my (%list, %local, @local);
			  map {
				  my $fn = ref $_;
				  my $r = $infptr->$fn($$_);
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
	  $infptr->free;
	  !wantarray && @infolist ? ($$I->{o} && @infolist == 1) ? $infolist[0] : \@infolist : @infolist
  }

  sub _prev {
	  shift->[-1]
  }
  sub _next {
	  shift->[1]
  }

  sub _list_full {
	  my $I = shift;
	  my @list = $I;
	  my ($l, $r) = ($I->_prev, $I->_next);
	  while ($l || $r) {
		  if ($l) {
			  unshift @list, $l;
			  $l = $l->_prev;
		  }
		  if ($r) {
			  push @list, $r;
			  $r = $r->_next;
		  }
	  }
	  !wantarray && @list ? \@list : @list
  }

  ## class method GenericCallback -- called for callback to do advisory typing
  ## $_[0] - hopefully the user data :)
  sub GenericCallback {
	  my ($bless, $fn, $args) = split /\|/, +shift, 3;
	  if ($bless =~ s/^x/./) {
		  unshift @_, $args;
		  __PACKAGE__->new->na($bless => @_);
		  $fn = join '::', '', (caller)[0], $fn;
		  goto &$fn;
	  }
  }
1}
 };
#$$$ }autoloaded

# define some abbreviations
use constant W 	  => new Weechat; # weechat::
use constant WC   => W->WEECHAT_; # weechat::WEECHAT_
use constant Wstr => W->string_;  # weechat::string_

BEGIN { # import constants and functions into Nlib class
    *Nlib::W = \&W;
}

#$$$ autoloaded{
BEGIN { { package Nlib;
# this is a weechat perl library
use strict; use warnings;

# to read the following docs, you can use "perldoc Nlib.pm"


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
## @_ - list of grotty lines that should be turned into weechat attributes
## returns modified lines and modifies lines in-place
sub mangle_man_for_wee {
	for (@_) {
		s/_\x08(.)/W->color('underline').$1.W->color('-underline')/ge;
		s/(.)\x08\1/W->color('bold').$1.W->color('-bold')/ge;
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

	if (my $obuf = W->buffer_search('perl', "man $name")) {
		eval qq{
			package $caller_package;
			weechat::buffer_close(\$obuf);
		};
	}

	my @wee_keys = W->_infolist('key');
	my @keys;

	my $win = W->current_window();
	my $buf = W->buffer_new("man $name", '', '', '', '');
	return WC->RC_OK unless $buf;

	my $width = $win->{win_chat_width};
	--$width if $win->{win_chat_width} < $win->{win_width} || ($win->{win_width_pct} < 100 && (grep { $_->{win_y} == $win->{win_y} } W->hdata_get('window')->{gui_windows}->_list_full)[-1]{win_x} > $win->{win_x});
	$width -= 2; # when prefix is shown

	$buf->{time_for_each_line} = 0;
	eval qq{
		package $caller_package;
		weechat::buffer_set(\$buf, 'display', 'auto');
	};
	die $@ if $@;

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input history_previous' ||
			   $_->{command} eq '/input history_global_previous' } @wee_keys;
	@keys = 'meta2-A' unless @keys;
	$buf->set("key_bind_$_" => '/window scroll -1') for @keys;

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input history_next' ||
			   $_->{command} eq '/input history_global_next' } @wee_keys;
	@keys = 'meta2-B' unless @keys;
	$buf->set("key_bind_$_" => '/window scroll +1') for @keys;

	$buf->set('key_bind_ ' => '/window page_down');

	@keys = map { $_->{key} }
		grep { $_->{command} eq '/input delete_previous_char' } @wee_keys;
	@keys = ('ctrl-?', 'ctrl-H') unless @keys;
	$buf->set("key_bind_$_" => '/window page_up') for @keys;

	@keys = map { $_->{key} }
	    grep { $_->{command} eq '/input move_beginning_of_line' } @wee_keys;
	push @keys, 'g';
	$buf->set("key_bind_$_" => '/window scroll_top') for @keys;

	@keys = map { $_->{key} }
	    grep { $_->{command} eq '/input move_end_of_line' } @wee_keys;
	push @keys, 'G';
	$buf->set("key_bind_$_" => '/window scroll_bottom') for @keys;

	$buf->set('key_bind_q' => '/buffer close');

	$buf->print(" \t".mangle_man_for_wee($_))
			for `pod2man \Q$file\E 2>/dev/null | GROFF_NO_SGR=1 nroff -mandoc -rLL=${width}n -rLT=${width}n -Tutf8 2>/dev/null`;
	$buf->command('/window scroll_top');

	unless ($buf->{lines}{lines_count} > 0) {
	    $buf->print(W->prefix('error').$_)
		for ("Unfortunately, your @{[W->color('underline')]}nroff".
			 "@{[W->color('-underline')]} command did not produce".
			     " any output.",
		     "Working pod2man and nroff commands are required for the ".
			 "help viewer to work.",
		     "In the meantime, please use the command ", '',
		     "\tperldoc $file", '',
		     "on your shell instead in order to read the manual.",
		     "Thank you and sorry for the inconvenience.");
	}
}

1
 } };
#$$$ }autoloaded

W->register(SCRIPT_NAME, 'Nei <anti.teamidiot.de>', $VERSION, 'GPL3', 'menu system', 'stop_menu', '')
    || return;
our $SCRIPT_FILE = W->_infolist('perl_script', '', SCRIPT_NAME)->[0]{filename};

W->bar_item_new('main_menu', 'bar_item_main_menu', '');
W->bar_item_new('sub_menu', 'bar_item_sub_menu', '');
W->bar_item_new('menu_help', 'bar_item_menu_help', '');
W->bar_item_new('window_popup_menu', 'bar_item_window_popup_menu', '');
W->hook_command(SCRIPT_NAME, 'open the menu', '[name] [args] || reset',
		(join "\n",
		 'without arguments, open the main menu.',
		 'if name is given, open the popup menu with that name - this is usually done by scripts.',
		 'args are passed on to the menu commands, see the manual for more info.',
		 'Example: /menu nick yournick',
		 'reset: resets the menu system to its initial config (also required if ',
		 '       you want to load new default menus, e.g after upgrade of script)',
		 'use '.W->color('bold').'/menu help'.W->color('-bold').' to read the manual'
		), '', 'open_menu', '');
W->hook_signal('input_flow_free', 'multiline_fix', '');
W->hook_signal('buffer_closed', 'invalidate_popup_buffer', '');
W->hook_config('plugins.var.perl.'.SCRIPT_NAME.'.*', 'script_config', '');
W->hook_config(SCRIPT_NAME.'.var.*', 'menu_config', '');
W->hook_command_run('/key *', 'update_main_menu', '');
# is there builtin mouse support?
if ((W->info_get('version_number', '') || 0) >= 0x00030600) {
    W->hook_hsignal('menu', 'hsignal_evt', '');
    W->key_bind('mouse', +{
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
our $INPUT_IN_PROGRESS;

our $LAST_NICK_COLOR;

our ($CFG_FILE, $CFG_FILE_SECTION);

init_menu();

sub bool_value { W->config_string_to_boolean(@_) }
sub wee_eval {
    if ((W->info_get('version_number', '') || 0) >= 0x00040200) {
	push @_, '';
    }
    Wstr->eval_expression(@_);
}

## make_menu -- convert menu entries to bar items
## $items - array ref of menu entries
## $active - reference to active menu item (gets corrected for bounds)
## $prefix - prefix for all items
## $info - info to show when menu closed
## $title - menu title (if applicable)
## returns bar item structure of menu items
sub make_menu {
    my ($items, $active, $prefix, $info, $title) = @_;
    my @items = @$items;
    if (defined $$active) {
	$$active = $#items if $$active < 0;
	$$active = 0 if $$active > $#items;
    }
    my ($ul, $UL) = map { W->color($_) } ('underline', '-underline');
    s/&(.)/$ul$1$UL/g for @items;
    my $I = '▐';
    my $act_menu = $MENU_OPEN && defined $$active ? $$active : -1;
    my $act = W->color('reverse');
    my $ACT = W->color('-reverse');
    join "\n", (defined $title ? $title !~ /\S/ ? $title : "$I$act$title$I$ACT" : ()),
	map { "$prefix$_" } map { $act_menu-- ? $_ : "$act$_" } @items,
	    (($MENU_OPEN || !$info) ? () : "$I$act$info$I$ACT")
}

## MAIN_MENU -- return main menu items
sub MAIN_MENU {
    map { $_->{value} }
    grep { $_->{option_name} =~ /^\d+[.]name$/ }
    W->_infolist('option', '', 'menu.var.*')
}

{
    my %int_repl = ('meta-' => "\1[", 'meta2-' => "\1[[", 'ctrl-' => "\1");
    my $int_repl = join '|', map { quotemeta } sort { length $b <=> length $a } keys %int_repl;
    my %int_repl_rev = reverse %int_repl;
    my $int_repl_rev = join '|', map { quotemeta } sort { length $b <=> length $a } keys %int_repl_rev;
    my $area_re = qr/\@(?:\w|[](.>*)[])*:/;

    my %arrow = (A => '↑', B => '↓', C => '→', D => '←', E => '·');
    my %no_arrow = (Up => '↑', Down => '↓', Right => '→', Left => '←', Begin => '·');
    my %no_arrow_disp = reverse %no_arrow;
    $no_arrow{KP5} = $no_arrow{Center} = $no_arrow{Begin};
    my %inspg = (2 => 'Ins', 3 => 'Del', 5 => 'PgUp', 6 => 'PgDn',
		 1 => 'Find', 4 => 'Select',
		 28 => 'Help', 29 => 'Copy', 32 => 'Paste', 34 => 'Cut',
		 (map { 11+$_ => "F$_" } 6..10),
		 (map { 12+$_ => "F$_" } 11..12),
		);
    my %fkeys = (P => 'F1', Q => 'F2', R => 'F3', S => 'F4');
    my %homend = (H => 'Home', F => 'End');
    my %homend1 = (7 => $homend{H}, 8 => $homend{F},
		   (map { 10+$_ => "F$_" } 1..5),
		  );
    my %homend2 = (1 => $homend{H}, 4 => $homend{F});
    # C-M-S-
    my %csi_mod_map = (2 => 'S-', 3 => 'M-', 4 => 'M-S-', 5 => 'C-', 6 => 'C-S-', 7 => 'C-M-', 8 => 'C-M-S-');
    my %csi_mod_meta = (         9 => 'M-', 10 => 'M-S-',                       13 => 'C-M-', 14 => 'C-M-S-');
    # 11 => 'M-A-', 12 => 'M-A-S-', 15 => 'C-M-A-', 16 => 'C-M-A-S-'
    my %rxvt_mod_map = ('^' => 'C-', '$' #'
			    => 'S-', '@' => 'C-S-');
    ## &$apply_tpl -- apply template parameters according to variable hash
    ## $r - hashref with key template in key 't'. %X are replaced by $r->{X}
    ## returns pair of keyseq and label/tag
    my $apply_tpl = sub {
	my $r = shift;
	my @r = ($r->{t}[0], ref $r->{t}[1] ? [ @{$r->{t}[1]} ] : [ $r->{t}[1] ]);
	push @{$r[1]}, 'meta' if exists $r->{E} && $r->{E}[0] =~ /^\d+$/ && $r->{E}[0] >= 9;
	$r[0] =~ s/%(\w)/${$r}{$1}[0]/g;
	$r[0] =~ s/\\l(.)/\l$1/g;
	for ($r[1][0]) {
	    s/\%(\w)/${$r}{$1}[1]/g;
	    s/M-C-/C-M-/g;
	}
	$r[1] = $r[1][0] if @{$r[1]} == 1;
	@r
    };

    ## &$map_key_add -- adds keys and its values to template replacement hash
    ## $rr - template hashref
    ## $f - variable name (1 char)
    ## $t - hashref with keys/values to iterate through
    ## $subr - subroutine ref that is called for each key/value
    ## returns list of $subr results applied to all entries in $t
    my $map_key_add = sub {
	my ($rr, $f, $t, $subr) = @_;
	map {
	    $rr->{$f} = [ $_ => $t->{$_} ];
	    $subr->($rr)
	} keys %$t
    };

    ## &$map_hashlist -- call &$map_key_add for all hashrefs in list
    ## $rr - template hashref
    ## $f - variable name (1 char)
    ## @list - list of hashrefs with keys/values to iterate through
    ## $subr - subroutine ref that is called for each key/value
    ## returns list of $subr results applied to all entries in all hashs of @list
    my $map_hashlist = sub {
	my ($rr, $f, @list) = @_;
	my $subr = pop @list;
	map {
	    $map_key_add->($rr, $f, $_, $subr)
	} @list
    };

    ## &$apply_tpl_fun -- functor to run &$apply_tpl
    ## $_[0] - hashref with template and parameters
    ## see &$apply_tpl
    my $apply_tpl_fun = sub {
	$apply_tpl->(+shift)
    };

    ## &$variable_e -- calls &$map_hashlist for keys and a list of hashes that are used for the %E template variable
    ## $e - arrayref of hashrefs which provide values for %E
    ## $_[1] - key template
    ## $_[2..$#@] - list of hashrefs which provide key seqs and definitions (%K)
    ## returns list of template expansion applied to all %E and %K values
    my $variable_e = sub {
	my $e = shift;
	$map_hashlist->(
	    +{ t => +shift },
	    K => @_,
	    sub {
		$map_hashlist->(
		    +shift,
		    E => @$e,
		    $apply_tpl_fun
		   )
	    }
	   )
    };

    my %H = (
	## &$H{def_end} -- apply %K template like meta2-%K => %K
	## $_[0] - key template
	## $_[1..$#@] - list of hashrefs providing %K
	## returns list of template expansion applied to all %K values
	def_end => sub {
	    $map_hashlist->(
		+{ t => +shift },
		K => @_,
		$apply_tpl_fun
	       )
	},
	## &$H{csi_end} -- apply %E%K template, %E iterates over csi codes
	## $_[0] - key template
	## $_[1..$#@] - list of hashrefs providing %K
	## returns list of template expansion applied to all %E and %K values
	csi_end => sub {
	    $variable_e->(
		[\(%csi_mod_map, %csi_mod_meta)],
		@_
	       )
	},
	## &$H{rxvt_end} -- apply %E%K template, %E iterates over rxvt modifier codes (note: there is no modifier for meta)
	## $_[0] - key template
	## $_[1..$#@] - list of hashrefs providing %K
	## returns list of template expansion applied to all %E and %K values
	rxvt_end => sub {
	    $variable_e->(
		[\%rxvt_mod_map],
		@_
	       )
	},
	## &$H{and_meta_pfx} -- add meta-/M- to the list of key mappings
	## @_ - list of sequence => name/tag pairs to which to add a meta variant
	## returns the original hash plus a copy of it with meta- added in front
	and_meta_pfx => sub {
	    my %ht = @_;
	    map {
		($_ => $ht{$_},
		 "meta-$_" => do {
		     my @r = ref $ht{$_} ? @{$ht{$_}} : $ht{$_};
		     $r[0] = "M-$r[0]";
		     $r[0] =~ s/M-C-/C-M-/g;
		     @r == 1 ? $r[0] : \@r })
	    } keys %ht
	},
       );
    my %reverse_some_keys;
    my %some_keys = (
	'meta2-P' => 'Pause',

	'ctrl-@' => 'C-SPC',

	'ctrl-I'        =>   'Tab',
	'meta2-Z'       => 'S-Tab',
	'meta2-27;5;9~' => 'C-Tab',

	$H{and_meta_pfx}(
	    'ctrl-M'         =>   'RET',
	   ),
	'meta2-27;5;13~' => 'C-RET',
	'meta2-27;2;13~' => 'S-RET',

	$H{and_meta_pfx}(
	    'ctrl-?'      =>     'BS',
	    'ctrl-H'      =>   'C-BS',
	   ),

	$H{def_end}([ 'meta2-%K'      =>   '%K'         ], \%arrow, \%homend),
	$H{csi_end}([ 'meta2-1;%E%K'  => '%E%K'         ], \%arrow, \%fkeys, \%homend),

	$H{def_end}([ 'meta-O%K'      =>['C-%K','tmux'] ], \%arrow),
	$H{def_end}([ 'meta-O\l%K'    =>['C-%K','rxvt'] ], \%arrow),
	$H{def_end}([ 'meta2-\l%K'    =>['S-%K','rxvt'] ], \%arrow),
	$H{def_end}([ 'meta-meta2-%K' =>['M-%K','rxvt'] ], \%arrow),

	$H{def_end}([ 'meta-O%K'      =>   '%K'         ], \%fkeys),
	$H{def_end}([ 'meta-meta-O%K' =>['M-%K','tmux'] ], \%fkeys),

	$H{def_end}([ 'meta2-%K~'     =>   '%K'         ], \%inspg),
	$H{csi_end}([ 'meta2-%K;%E~'  => '%E%K'         ], \%inspg),

	$H{and_meta_pfx}(
	    $H{rxvt_end}(['meta2-%K%E'    =>['%E%K','rxvt'] ], \%inspg),
	   ),
	$H{def_end}([ 'meta-meta2-%K~'=>['M-%K','rxvt'] ], \%inspg),

	$H{and_meta_pfx}(
	    $H{def_end}([ 'meta2-%K~'     =>[  '%K','rxvt'] ], \%homend1),
	    $H{rxvt_end}(['meta2-%K%E'    =>['%E%K','rxvt'] ], \%homend1),
	   ),

	$H{def_end}([ 'meta-meta2-%K~'=>['M-%K','screen']],\%homend2),

	'meta2-200~' => 'PasteBegin',
	'meta2-201~' => 'PasteEnd',
       );
    my %int_some_keys = ("\1[" => 'M-', "\1" => 'C-', "\1[[" => 'meta2-');
    my $no_arrow_disp = '[' . (join '', keys %no_arrow_disp) . ']';
    for (sort { ref $some_keys{$a} && ref $some_keys{$b}
		    ? $some_keys{$a}[0] cmp $some_keys{$b}[0]
			: ref $some_keys{$b} ? -1
			    : ref $some_keys{$a} ? 1
				: $some_keys{$a} cmp $some_keys{$b} } keys %some_keys) {
	push @{$reverse_some_keys{ ref $some_keys{$_} ? $some_keys{$_}[0] : $some_keys{$_} }},
	    ref $some_keys{$_} ? [ $_, $some_keys{$_}[1] ] : $_;
	my $o = $_;
	s/($int_repl)/$int_repl{$1}/g;
	$int_some_keys{$_} = $some_keys{$o};
    }
    for (keys %no_arrow) {
	for my $pfx ('', 'C-', 'S-', 'M-', 'C-M-', 'C-S-', 'C-M-S-', 'M-S-') {
	    push @{$reverse_some_keys{"$pfx$_"}}, @{$reverse_some_keys{"$pfx$no_arrow{$_}"}}
		if exists $reverse_some_keys{"$pfx$no_arrow{$_}"};
	}
    }
    my $keys_internal = join '|', map { quotemeta } sort { length $b <=> length $a } keys %int_some_keys;

    sub rename_key {
	my $keybinding = shift;
	return wantarray ? ($keybinding->{key}, []) : $keybinding->{key}
	    if $keybinding->{key} eq $keybinding->{key_internal};
	$keybinding = $keybinding->{key_internal};
	my $area = $1 if $keybinding =~ s/^($area_re)//;
	my @ann;
	$keybinding =~ s{($keys_internal|\w|\p{Print})}{
	    (exists $int_some_keys{$1}
		 ? ref $int_some_keys{$1}
		     ? ((push @ann, $int_some_keys{$1}[1]),
			$int_some_keys{$1}[0])
			 : $int_some_keys{$1}
			     : $1).' '}ge;
	$keybinding =~ s/C- \K(\w)/\L$1/g;
	$keybinding =~ s/M- O (?=\p{Print})/meta-O /g;
	$keybinding =~ s/M-C-/C-M-/g;
	$keybinding =~ s/\w-\K //g;
	$keybinding = "$area$keybinding" if defined $area;
	unshift @ann, '|unknown|' if $keybinding =~ /meta(?:2-|-O)/;
	wantarray ? ($keybinding, \@ann) : $keybinding
    }
}

## bar_item_main_menu -- return main menu as bar items
sub bar_item_main_menu {
    my @items = MAIN_MENU();
    my ($keybinding) = grep { $_->{command} eq '/menu' } W->_infolist('key');
    if ($keybinding) {
	$keybinding = rename_key($keybinding);
    }
    else {
	$keybinding = '/menu';
    }
    my $key_hint_text = "$keybinding to open menu";
    $key_hint_text = '' if W->config_is_set_plugin('key_binding_hidden') && bool_value(W->config_get_plugin('key_binding_hidden'));
    make_menu(\@items, (!$MENU_OPEN || $MENU_OPEN < 3 ? \$ACT_MENU{main} : \undef), '', $key_hint_text)
}

## menu_input_run -- dispatch /input actions to menu
## () - event handler
## $cmd - executed /input command
sub menu_input_run {
    my (undef, undef, $cmd) = @_;
    return WC->RC_OK unless $MENU_OPEN;
    $cmd =~ s/ (?:insert \\x0a|magic_enter)/ return/;
    if ($cmd eq '/input delete_previous_char') { # toggle help
	my $bar = W->bar_search('menu_help');
	$bar->{hidden} = 0 + !$bar->_infolist->{hidden};
	W->bar_search('sub_menu')->{separator} = 0 + $bar->_infolist->{hidden};
	W->config_set_plugin('active_help', $bar->_infolist->{hidden} ? 'on' : 'off');
    }
    else {
	my $mo = menu_stuff();
	if ($cmd eq '/input switch_active_buffer') {
	    $mo->{close}->();
	    --$MENU_OPEN if defined $MENU_OPEN;
	}
	elsif ($cmd eq '/input move_previous_char'
	    || $cmd eq '/input history_previous' || $cmd eq '/input history_global_previous') {
	    --${ $mo->{act} };
	    $mo->{update}->();
	}
	elsif ($cmd eq '/input move_next_char'
	    || $cmd eq '/input history_next' || $cmd eq '/input history_global_next') {
	    ++${ $mo->{act} };
	    $mo->{update}->();
	}
	elsif ($cmd eq '/input return') {
	    $mo->{exec}->();
	    open_menu() unless $mo->{main}
		|| (W->config_is_set_plugin('sticky_menu') && bool_value(W->config_get_plugin('sticky_menu')));
	}
    }
    WC->RC_OK_EAT
}

## menu_stuff -- get active menu
## returns active item storage, update func and menu item func of active menu
{
    my %MENU_STUFF = (
	1 => +{
	    close => \&close_menu,
	    update => \&update_main_menu,
	    main => 1,
	    exec => sub {
		++$MENU_OPEN;
		open_submenu();
	    },
	    act => \($ACT_MENU{main}),
	    items => \&MAIN_MENU
	   },
	2 => +{
	    close => \&close_submenu,
	    update => \&update_sub_menu,
	    exec => \&exec_submenu,
	    act => \($ACT_MENU{sub}),
	    items => \&SUB_MENU
	   },
	3 => +{
	    close => sub {
		close_window_popup_menu();
		close_menu();
	    },
	    update => \&update_window_popup_menu,
	    exec => \&exec_popupmenu,
	    act => \($ACT_MENU{window_popup}),
	    items => \&WINDOW_POPUP_MENU
	   },
	'' => +{
	    close => \&open_menu,
	    main => 1,
	    update => sub{},
	    exec => \&open_menu,
	    act => \(my $o = 0),
	    items => sub{},
	}
       );

    sub menu_stuff {
	$MENU_STUFF{$MENU_OPEN} || $MENU_STUFF{''};
    }
}

## menu_input_mouse_fix -- disable shortcuts during mouse input
## () - signal handler
sub multiline_fix {
	(undef, undef, $INPUT_IN_PROGRESS) = @_;
	weechat::WEECHAT_RC_OK
}

## menu_input_text -- read input shortcut keys
## () - event handler
## $_[3] - current content of input buffer
## removes input shortcut key and returns old content of input buffer
sub menu_input_text {
    Encode::_utf8_on($_[3]);
    return $_[3] unless $MENU_OPEN;
    return $_[3] if $INPUT_IN_PROGRESS;
    my $mo = menu_stuff;
    my $buf = W->current_buffer();
    my $npos = $buf->{input_buffer_pos}-1;
    my $input_key = substr $_[3], $npos, 1, '';
    my ($pos) = map { $_->[0] }
	grep { $_->[-1] =~ /&\Q$input_key/i }
	    do { my $i = 0; map { [ $i++, $_ ] } $mo->{items}->() };
    if (defined $pos) {
	${ $mo->{act} } = $pos;
	$mo->{update}->();
    }
    $buf->{input_pos} = $npos;
    $_[3]
}

## menu_input_text_display -- display on input bar
## () - event handler
## $_[3] - current content of input buffer
## returns text to be displayed on input bar
sub menu_input_text_display {
    Encode::_utf8_on($_[3]);
    return $_[3] unless $MENU_OPEN;
    '[menu open] '. $_[3]
}

sub mouse_nicklist_barcode {
	my (undef, undef, undef, $bufptr, $nick, $item) = @_;
	my $nickptr = $bufptr->nicklist_search_nick('', $nick);
	if ($nickptr) {
		my @funargs = ($bufptr, $nickptr, 'color');
		W->nicklist_nick_set(@$LAST_NICK_COLOR) if $LAST_NICK_COLOR;
		$LAST_NICK_COLOR = [ @funargs, W->nicklist_nick_get_string(@funargs) ];
		W->nicklist_nick_set(@funargs, 'reverse');
	}
	W->current_buffer()->command("/menu nick $nick");
	WC->RC_OK
}

sub mouse_evt_barcode {
	my (undef, undef, undef, $error, $idx, $item, $bar_name) = @_;
	my $close_menu_in_empty = qr/_menu\b/; # qr/\bmain_menu\b/;
	if ($error) {
		open_menu() # closes the menu here
			if ($MENU_OPEN && !defined $idx && $bar_name =~ $close_menu_in_empty);

		return WC->RC_OK;
	}
	if ($bar_name =~ /\bmain_menu\b/) {
		open_menu() unless $MENU_OPEN;
		menu_input_run('', '', '/input switch_active_buffer')
			while ($MENU_OPEN > 1);
		$ACT_MENU{main} = $idx;
		update_main_menu();
		menu_input_run('', '', '/input return');
	}
	elsif ($bar_name =~ /\bsub_menu\b/) {
		open_menu() unless $idx;
		$ACT_MENU{sub} = $idx-1 if $idx;
		update_sub_menu();
		menu_input_run('', '', '/input return');
	}
	elsif ($bar_name =~ /\bwindow_popup_menu\b/) {
		open_menu() unless $idx;
		$ACT_MENU{window_popup} = $idx-1 if $idx;
		update_window_popup_menu();
		menu_input_run('', '', '/input return');
	}
	WC->RC_OK
    }

sub hsignal_evt {
    my %data = %{$_[2]};
    W->na(b => $data{_buffer});
    return mouse_nicklist_barcode(undef,
				  undef,
				  '#',
				  $data{_buffer}, $data{nick})
	if $data{_bar_name} eq 'nicklist';
    mouse_evt_barcode(undef,
		      undef,
		      '#',
		      $data{_bar_item_name} ne $data{_bar_name},
		      $data{_bar_item_name} ? $data{_bar_item_line} : undef,
		      undef,
		      $data{_bar_name});
}

## SUB_MENU -- return sub menu items
sub SUB_MENU {
    my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
    my @menu_entries = 	W->_infolist('option', '', 'menu.var.*');
    my ($main_menu_id) =
    map { $_->{option_name} =~ /^(\d+)[.]/ && $1 }
    grep { $_->{option_name} =~ /^\d+[.]name$/ && $_->{value} eq $active_main_menu }
    @menu_entries;
    map { $_->{value} }
    grep { $_->{option_name} =~ /^$main_menu_id[.]\d+[.]name$/ }
    @menu_entries
}

## WINDOW_POPUP_MENU -- return popup menu items
sub WINDOW_POPUP_MENU {
    return () unless $POPUP_MENU;
    map { $_->{value} }
    grep { $_->{option_name} =~ /^\Q$POPUP_MENU\E[.]\d+[.]name$/ }
    W->_infolist('option', '', "menu.var.$POPUP_MENU.*")
}

## exec_submenu -- run command of active sub menu item
sub exec_submenu {
    my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
    my $active_sub_menu = (SUB_MENU())[$ACT_MENU{sub}];
    my @menu_entries = 	W->_infolist('option', '', 'menu.var.*');
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
    W->current_buffer()->command($command) if $command
}

## exec_popupmenu -- run command of active popup menu item
sub exec_popupmenu {
	my $active_popup_entry = (WINDOW_POPUP_MENU())[$ACT_MENU{window_popup}];
	my @menu_entries = W->_infolist('option', '', "menu.var.$POPUP_MENU.*");
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
	W->command($POPUP_MENU_BUFFER, $command) if $command
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
    join "\n", (
	'Use the arrow '.($MENU_OPEN > 1 ? 'up/down' : 'left/right').' keys or highlighted shortcuts to '.
	    'select a menu entry,',
	'C-x to close menu',
	'C-h to toggle the help window',
	'RET to open')
}

## close_menu -- close main menu
sub close_menu {
    my $last_open_menu = $MENU_OPEN;
    $MENU_OPEN = undef;
    W->bar_search('menu_help')->{hidden} = 1;
    W->bar_search('main_menu')->{hidden} = 1
	if W->config_is_set_plugin('main_menu_hidden') && bool_value(W->config_get_plugin('main_menu_hidden'));
    update_main_menu();
    Nlib::unhook_dynamic('1200|/input *', 'menu_input_run');
    Nlib::unhook_dynamic('input_text_content', 'menu_input_text');
    Nlib::unhook_dynamic('input_text_display_with_cursor', 'menu_input_text_display');
    W->bar_item_update('input_text');
}

## close_window_popup_menu -- close popup menu and clean up after feature extensions (nicklist)
sub close_window_popup_menu {
    W->bar_search('window_popup_menu')->{hidden} = 1;
    $ACT_MENU{window_popup} = undef;
    if ($LAST_NICK_COLOR && $POPUP_MENU eq 'nick') {
	W->nicklist_nick_set(@$LAST_NICK_COLOR);
	$LAST_NICK_COLOR = undef
    }
}

sub expand_dynamic_menus {
    my (@menu_entries, $key);
    if ($MENU_OPEN == 2) {
	my $active_main_menu = (MAIN_MENU())[$ACT_MENU{main}];
	@menu_entries = W->_infolist('option', '', 'menu.var.*');
	my ($main_menu_id) =
	    map { $_->{option_name} =~ /^(\d+)[.]/ && $1 }
	    grep { $_->{option_name} =~ /^\d+[.]name$/ && $_->{value} eq $active_main_menu }
		@menu_entries;
	$key = $main_menu_id;
    }
    elsif ($MENU_OPEN == 3) {
	@menu_entries = W->_infolist('option', '', "menu.var.$POPUP_MENU.*");
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
	W->command('', "/mute /unset menu.var.$pfx.$raw*");
	# %#info_hashtable
	# %gui_buffers.buffer<50% ${buffer.number} ${buffer.name} % /buffer ${buffer.number}
	my (undef, $hdata, $name, $command) = split /\s?%\s?/, $opt_table{$dig}{command}[1], 4;
	my $limit;
	($hdata, $limit) = split /</, $hdata, 2;

	if ($hdata =~ s/^#//) { # info_hashtable case
	    my $r = W->info_get_hashtable($hdata, +{ name => $name, command => $command });
	    for my $k (sort keys %$r) {
		next unless $k =~ /^(\d+)[.](?:name|command)$/;
		W->command('', "/mute /set menu.var.$pfx.$raw$k ${$r}{$k}");
	    }

	    next; ###
	}

	my ($list, $hd, @path) = split '[.]', $hdata;
	my $hdh = W->hdata_get($hd)->{$list} if $hd;
	while ($hdh && @path) {
	    $hdh = $hdh->{ +shift @path };
	}
	my @a = (undef, 1..9, 0, 'a'..'z');
	my $i = 0;
	while ($hdh) {
	    $i = sprintf '%04d', $i + 1;
	    my %pointer = ($$hdh->{ns}[-1] => $hdh);
	    my %vars = (i => 0+$i, a => ($i < @a ? $a[$i] : ' '));
	    W->command('', "/mute /set menu.var.$pfx.$raw$i.name @{[wee_eval($name, \%pointer, \%vars)]}");
	    W->command('', "/mute /set menu.var.$pfx.$raw$i.command @{[wee_eval($command, \%pointer, \%vars)]}");
	    $hdh = $hdh->_next;
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
	return WC->RC_OK;
    }
    elsif ($_[2] && $_[2] =~ /^\s*help\s*$/i) {
	Nlib::read_manpage($SCRIPT_FILE, SCRIPT_NAME);
	return WC->RC_OK
    }
    my @args;
    @args = split ' ', $_[2]
	if $_[2];
    if ($MENU_OPEN && !@args) {
	close_window_popup_menu() if $MENU_OPEN == 3;
	close_submenu() if $MENU_OPEN == 2;
	close_menu();
	return WC->RC_OK;
    }
    Nlib::hook_dynamic('command_run', '1200|/input *', 'menu_input_run', '');
    Nlib::hook_dynamic('modifier', 'input_text_content', 'menu_input_text', '');
    Nlib::hook_dynamic('modifier', 'input_text_display_with_cursor', 'menu_input_text_display', '');
    unless (@args) {
	$MENU_OPEN = 1;
	W->bar_search('main_menu')->{hidden} = 0;
    }
    elsif ($args[0]) {
	my @menu_entries = W->_infolist('option', '', "menu.var.$args[0].*");
	if ($args[0] eq 'nick' && !@menu_entries && $LAST_NICK_COLOR) {
	    W->nicklist_nick_set(@$LAST_NICK_COLOR);
	    $LAST_NICK_COLOR = undef
	}
	return WC->RC_OK
	    unless @menu_entries;
	$POPUP_MENU_BUFFER = $_[1];
	$POPUP_MENU = $args[0];
	$POPUP_MENU_ARGS = [ @args[1..$#args] ];
	close_submenu() if $MENU_OPEN && $MENU_OPEN == 2;
	$MENU_OPEN = 3;
	expand_dynamic_menus();
	$ACT_MENU{window_popup} = 0;
	W->bar_search('window_popup_menu')->{hidden} = 0;
	update_window_popup_menu();
    }
    W->bar_search('menu_help')->{hidden} = 0
	if !W->config_is_set_plugin('active_help') || bool_value(W->config_get_plugin('active_help'));
    update_main_menu();
    update_menu_help();
    WC->RC_OK
}

## close_submenu -- close sub menu (does not reset $MENU_OPEN counter)
sub close_submenu {
    $ACT_MENU{sub} = undef;
    my $bar = W->bar_search('sub_menu');
    $bar->{hidden} = 1;
    $bar->{separator} = 1;
    update_menu_help();
    WC->RC_OK
}

## open_submenu -- open sub menu (does not reset $MENU_OPEN counter)
sub open_submenu {
    expand_dynamic_menus();
    $ACT_MENU{sub} = 0;
    my $bar = W->bar_search('sub_menu');
    $bar->{hidden} = 0;
    $bar->{separator} = 0 unless W->bar_search('menu_help')->_infolist->{hidden};
    update_sub_menu();
    update_menu_help();
    WC->RC_OK
}

## setup_menu_bar -- create bars with bar menu items
sub setup_menu_bar {
    if (my $bar = W->bar_search('main_menu')) {
	$bar->{hidden} = 0;
	$bar->{items} = '*,main_menu' unless $bar->_infolist->{items} =~ /\bmain_menu\b/;
    }
    else {
	W->bar_new('main_menu', 'off', 10000, 'root', '', 'top', 'horizontal', 'vertical',
		   0, 0, 'gray', 'lightblue', 'darkgray', 'off', '*,main_menu');
    }
    if (my $bar = W->bar_search('sub_menu')) {
	$bar->{hidden} = 1;
	$bar->{items} = '*sub_menu' unless $bar->_infolist->{items} =~ /\bsub_menu\b/;
    }
    else {
	W->bar_new('sub_menu', 'on', 9999, 'root', '', 'top', 'columns_vertical', 'vertical',
		   0, 0, 'black', 'lightmagenta', 'gray', 'on', '*sub_menu');
    }
    if (my $bar = W->bar_search('menu_help')) {
	$bar->{hidden} = 1;
	$bar->{items} = 'menu_help' unless $bar->_infolist->{items} =~ /\bmenu_help\b/;
    }
    else {
	W->bar_new('menu_help', 'on', 9998, 'root', '', 'top', 'horizontal', 'vertical',
		   0, 0, 'darkgray', 'default', 'gray', 'on', 'menu_help');
    }

    if (my $bar = W->bar_search('window_popup_menu')) {
	$bar->{hidden} = 1;
	$bar->{items} = '*window_popup_menu' unless $bar->_infolist->{items} =~ /\bwindow_popup_menu\b/;
    }
    else {
	W->bar_new('window_popup_menu', 'on', 0, 'window', 'active', 'bottom', 'columns_vertical', 'vertical',
		   0, 0, 'black', 'lightmagenta', 'gray', 'on', '*window_popup_menu');
    }

    WC->RC_OK
}

## invalidate_popup_buffer -- delete popup buffer ptr if buffer is closed
## () - signal handler
## $bufptr - signal comes with pointer of closed buffer
sub invalidate_popup_buffer {
    my (undef, undef, $bufptr) = @_;
    $POPUP_MENU_BUFFER = W->current_buffer()
	if $bufptr eq $POPUP_MENU_BUFFER;
    WC->RC_OK
}

## config_create_opt -- create config option callback
## () - callback handler
## $_[3] - option name
sub config_create_opt {
    return WC->CONFIG_OPTION_SET_OPTION_NOT_FOUND unless
	$_[3] =~ /^(?:\w+[.])?\d+[.](?:name|command)$/;
    W->config_new_option(@_[1..$#_-1], 'string', '', '', 0, 0, '', $_[-1], 0, '', '', '', '', '', '');
    WC->CONFIG_OPTION_SET_OK_SAME_VALUE
}

## load_config -- create and read menu config file
sub load_config {
    $CFG_FILE = W->config_new(SCRIPT_NAME, '', '');
    $CFG_FILE_SECTION = $CFG_FILE->new_section('var', 1, 1, '', '', '', '', '', '', 'config_create_opt', '', '', '');
    $CFG_FILE->read;
    WC->RC_OK
}

## hide_menu_bar -- hide all the menu bars
sub hide_menu_bar {
    setup_menu_bar();
    W->bar_search('main_menu')->{hidden} = 1;
    W->bar_search('sub_menu')->{hidden} = 1;
    W->bar_search('menu_help')->{hidden} = 1;
    W->bar_search('window_popup_menu')->{hidden} = 1;
    WC->RC_OK
}

## update_sub_menu -- update sub menu bar item
sub update_sub_menu {
    W->bar_item_update('sub_menu');
    WC->RC_OK
}

## update_main_menu -- update main menu bar item
sub update_main_menu {
    W->bar_item_update('main_menu');
    WC->RC_OK
}

## update_menu_help -- update menu help bar item
sub update_menu_help {
    W->bar_item_update('menu_help');
    WC->RC_OK
}

## update_window_popup_menu -- update window popup menu bar item
sub update_window_popup_menu {
    W->bar_item_update('window_popup_menu');
    WC->RC_OK
}

## script_config -- check config in plugin namespace
sub script_config {
    W->bar_search('main_menu')->{hidden} = 0 + ((!$MENU_OPEN || $MENU_OPEN > 2)
	&& W->config_is_set_plugin('main_menu_hidden') && bool_value(W->config_get_plugin('main_menu_hidden')));
    update_main_menu() if (!$MENU_OPEN || $MENU_OPEN > 2);
    WC->RC_OK
}

## menu_config -- what is to do on updates in menu option
sub menu_config {
    update_window_popup_menu();
    update_sub_menu();
    update_main_menu();
    WC->RC_OK
}

## $_[0] - reset all menus to default
sub initial_menus {
    W->command('', '/mute /unset menu.var.*') if $_[0];
    my @menu_entries = W->_infolist('option', '', 'menu.var.*');
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
    $CFG_FILE->new_option($CFG_FILE_SECTION, $_, 'string', '', '',
			  0, 0, '', $initial_menu{$_}, 0, '', '', '', '', '', '')
	for sort keys %initial_menu;
}

sub init_menu {
    $ACT_MENU{main} = 0;
    $POPUP_MENU_BUFFER = W->current_buffer();
    load_config();
    initial_menus();
    setup_menu_bar();
    script_config();
    for (Nlib::get_settings_from_pod($SCRIPT_FILE)) {
	W->config_set_desc_plugin($_, Nlib::get_desc_from_pod($SCRIPT_FILE, $_));
    }
    update_main_menu();
    WC->RC_OK
}

sub stop_menu {
    hide_menu_bar();
    $CFG_FILE->write;
    $CFG_FILE_SECTION->free_options;
    $CFG_FILE_SECTION->free;
    $CFG_FILE->free;
    WC->RC_OK
}
