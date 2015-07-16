# Copyright (c) 2015 by apendragon <cpandragon@gmail.com>
# Released under Artistic License (2.0).

use strict;
use IO::Handle;
use constant {
  _SCRIPT_NAME    => 'dzen_notifier',
  _VERSION        => '0.2',
  _AUTHOR         => 'apendragon',
  _LICENSE        => 'artistic_2',
  _DESC           => 'weechat dzen notifier script',
  _SHUTDOWN_F     => 'shutdown',
  _CHARSET        => 'UTF-8',
  _BITLBEE_CHAN   => '&bitlbee',
  _UNKNOWN_SENDER => 'stranger',
  _DEBUG          => 0,
};

my %options = (
  icon     => '', # example: '^i(/home/johndoe/.dzen/icons/xbm8x8/cat.xbm)',
  dzen_cmd => "dzen2 -ta l -h 18 -fn 'snap' -bg '#111111' -fg '#b3b3b3' -w 200 -x 1000",
);

weechat::register(_SCRIPT_NAME(), _AUTHOR(), _VERSION(), _LICENSE(), _DESC(), _SHUTDOWN_F(), _CHARSET());

=head1 NAME

dzen_notifier.pl

=head1 SYNOPSIS

dzen_notifier.pl

does not take any args.

Just put it in ~/.weechat/perl/autoload dir or load it manually with /script

=head1 DESCRIPTION

dzen_notifier.pl perl script will notify dzen when you receive a private message in weechat.

The form of notification is C<${icon} [${nb_pv_sender}] ${last_sender} (${nb_msg_of_last_sender})>

where

=over 4

=item * C<${icon}> is a parameterized icon or nothing by default I<(see icon option)>

=item * C<${nb_pv_sender}> is number of unread buffers of private messages

=item * C<${last_sender}> the nick of the last sender who wrote you a private message you did not read or C<stranger>
        if the last sender is not in your bitlbee buddy list I<(see L</Bitlbee> for more details)>.

=item * C<${nb_msg_of_last_sender}> is number of unread messages in your last sender buffer

=back

See L</EXAMPLE>.

=head2 Set private message as read

If you switch to private message buffer that has been notified, it will automatically be removed from stack of private messages notified.
Then C<${nb_pv_sender}> will be decreased, C<${last_sender}> will switch to preceding last sender who wrote you a private message
you did not read (or nothing if there is not), and C<${nb_msg_of_last_sender}> will begin the number of unread messages of this
preceding sender (or nothing if there is not).

=head2 Bitlbee

If you use L<bitlbee|http://www.bitlbee.org>, you know that if you receive private message of somebody who is not in your buddy list, it will
appear in C<&bitlbee> buffer. dzen_notifier.pl handles this case and will notify dzen with C<stranger> private message notification.
C<stranger> nickname is used because more than one unknow body may send you private message at the same time in this buffer. All these
private message notifications will be removed from private messages stack when you will swich to C<&bitlbee> buffer.

=head2 OPTIONS

Options can directly be set in C<%options> hash.

=over 4

=item * C<dzen_cmd> is the dzen command where dzen_notifier.pl will pipe output notifications.

By default it is

        dzen2 -ta l -h 18 -fn 'snap' -bg '#111111' -fg '#b3b3b3' -w 200 -x 1000.

Of course you have to customize it with your own dzen settings, like x position, font, width, etc.

=item * C<icon> is the icon path you want to use front of your notification.

By example

        ^i(/home/johndoe/.dzen/icons/xbm8x8/cat.xbm)

=back

=head1 EXAMPLE

if dzen notification looks like

C<[4] johndoe (2)>

it means you have C<4> private message buffers you have not already read, the last private message you received is in C<johndoe> buffer,
and he wrote C<2> unread messages in this buffer.

=head1 AUTHOR

Thomas Cazali

=head1 SOURCE

The source code repository for C<dzen_notifier.pl> can be found at L<https://github.com/apendragon/weechat-dzen-notifier>

=head1 BUGS

Please report any bugs or feature requests to L<https://github.com/apendragon/weechat-dzen-notifier/issues>.

=head1 SUPPORT

You can find documentation for this script at

L<https://github.com/apendragon/weechat-dzen-notifier/wiki>

=over 4

=item * github repository issues tracker (report bugs here)

L<https://github.com/apendragon/weechat-dzen-notifier/issues>

=back

=head1 LICENSE AND COPYRIGHT

Copyright 2015 Thomas Cazali.

This program is free software; you can redistribute it and/or modify it
under the terms of the the Artistic License (2.0). You may obtain a
copy of the full license at:

L<http://www.perlfoundation.org/artistic_license_2_0>

Any use, modification, and distribution of the Standard or Modified
Versions is governed by this Artistic License. By using, modifying or
distributing the Package, you accept this license. Do not use, modify,
or distribute the Package, if you do not accept this license.

If your Modified Version has been derived from a Modified Version made
by someone other than you, you are nevertheless required to ensure that
your Modified Version complies with the requirements of this license.

This license does not grant you the right to use any trademark, service
mark, tradename, or logo of the Copyright Holder.

This license includes the non-exclusive, worldwide, free-of-charge
patent license to make, have made, use, offer to sell, sell, import and
otherwise transfer the Package with respect to any patent claims
licensable by the Copyright Holder that are necessarily infringed by the
Package. If you institute patent litigation (including a cross-claim or
counterclaim) against any party alleging that the Package constitutes
direct or contributory patent infringement, then this Artistic License
to you shall terminate on the date that such litigation is filed.

Disclaimer of Warranty: THE PACKAGE IS PROVIDED BY THE COPYRIGHT HOLDER
AND CONTRIBUTORS "AS IS' AND WITHOUT ANY EXPRESS OR IMPLIED WARRANTIES.
THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, OR NON-INFRINGEMENT ARE DISCLAIMED TO THE EXTENT PERMITTED BY
YOUR LOCAL LAW. UNLESS REQUIRED BY LAW, NO COPYRIGHT HOLDER OR
CONTRIBUTOR WILL BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, OR
CONSEQUENTIAL DAMAGES ARISING IN ANY WAY OUT OF THE USE OF THE PACKAGE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

=cut

open my ($io_fh), "|$options{dzen_cmd}";
$io_fh->autoflush(1);
my %buffered_pv_msg = ();
my @stacked_notif = ();

weechat::hook_print('', '', '', 1, 'print_author_and_count_priv_msg', '');
weechat::hook_signal('buffer_switch', 'unnotify_on_private', '');

sub get_msg_sender {
  my ($tags) = @_;
  my $nick = '';
  $nick = $1 if (defined($tags) && $tags =~ m/(?:^|,)nick_([^,]*)(?:,|$)/);
  $nick;
}

sub is_my_message {
  my ($tags, $buffer) = @_;
  my $my_nick = weechat::buffer_get_string($buffer, 'localvar_nick');
  my $nick = get_msg_sender($tags);
  $nick eq $my_nick;
}

sub is_private_message {
  my ($buffer, $tags) = @_;
  my $private_buff = weechat::buffer_get_string($buffer, 'localvar_type') eq 'private';
  $private_buff && $tags =~ m/(?:^|,)notify_private(?:,|$)/;
}

sub is_bitlbee_private_message {
  my ($buffer, $tags, $highlight, $message) = @_;
  my $bitlbee_buff = weechat::buffer_get_string($buffer, 'localvar_channel') eq _BITLBEE_CHAN();
  my $my_nick = weechat::buffer_get_string($buffer, 'localvar_nick');
  $highlight && $bitlbee_buff && $message =~ m/^$my_nick:/;
}

sub notify {
  my ($sender) = @_;
  my $count = scalar keys %buffered_pv_msg;
  $count ? print $io_fh "$options{icon} [$count] $sender ($buffered_pv_msg{$sender})\n" : print $io_fh "\n";
  weechat::WEECHAT_RC_OK;
}

sub notify_on_private {
  my ($buffer, $tags, $highlight, $message) = @_;
  my $is_bitlbee_pv_msg = is_bitlbee_private_message($buffer, $tags, $highlight, $message);
  my $closure = sub {
    my $sender = $is_bitlbee_pv_msg ? _UNKNOWN_SENDER() : get_msg_sender($tags);
    rm_from_stack($sender);
    push(@stacked_notif, $sender);
    $buffered_pv_msg{$sender}++;
    notify $sender;
  };
  ($is_bitlbee_pv_msg || is_private_message($buffer, $tags)) ? $closure->() : weechat::WEECHAT_RC_OK;
}

sub print_author_and_count_priv_msg {
  my ($data, $buffer, $date, $tags, $displayed, $highlight, $prefix, $message) = @_;
  my $dispatch = {
    0 => sub { weechat::WEECHAT_RC_OK }, # return if message is filtered
    1 => sub {
      is_my_message($tags, $buffer)
        ? weechat::WEECHAT_RC_OK
        : notify_on_private($buffer, $tags, $highlight, $message);
    },
  };
  $dispatch->{$displayed}->();
}

sub unnotify {
  my ($sender) = @_;
  rm_sender_notif($sender);
  scalar(@stacked_notif) ? notify($stacked_notif[-1]) : notify();
}

sub unnotify_on_private {
  my ($signal, $type_data, $signal_data) = @_;
  my $type=weechat::buffer_get_string($signal_data, 'localvar_type');
  my $channel=weechat::buffer_get_string($signal_data, 'localvar_channel');
  my $dispatch = {
    'private'  => sub {
       unnotify($channel);
    },
    'channel' => sub {
      $channel eq _BITLBEE_CHAN() && $buffered_pv_msg{_UNKNOWN_SENDER()}
        ? unnotify(_UNKNOWN_SENDER())
        : weechat::WEECHAT_RC_OK;
    },
  };
  ($dispatch->{$type} || sub { weechat::WEECHAT_RC_OK })->();
}

sub rm_from_stack {
  my ($sender) = @_;
  my @stack = ();
  foreach (@stacked_notif) { push(@stack, $_) if ($_ ne $sender) }
  @stacked_notif = @stack;
}

sub rm_sender_notif {
  my ($sender) = @_;
  delete($buffered_pv_msg{$sender});
  rm_from_stack($sender);
}

sub shutdown {
  #weechat::log_print("shutdown") if _DEBUG();
  close $io_fh;
}
