# Copyright (c) 2012 Yoran Heling
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.



# This is a simple weechat script that displays the number of unread emails in
# the status bar. The unread mail count is fetched from one of more (local)
# directories in Maildir format. If there is no unread mail, nothing will be
# displayed.
#
# Written by Yoran Heling <projects@yorhel.nl>
#
#
# Usage:
# - Copy/save this script to $HOME/.weechat/perl/maildir.pl
# - In weechat, type:
#     /perl load perl/maildir.pl
# - Add the string "[maildir]" somewhere to /set weechat.bar.status.items
# - Set the directory to watch:
#     /set plugins.var.perl.maildir.dir /home/yorhel/.mail/inbox
#   You can specify multiple directories by separating them with a comma.
# - (Optionally) set the update interval:
#     /set plugins.var.perl.maildir.interval 30
#     /perl reload maildir
#   The default of 10 seconds will usually work fine.
#
#
# 2012-11-26 - 1.1
#   - Use empty string to clear bar item.
#
# 2012-10-07 - 1.0
#   - Initial version

use strict;
use warnings;
use utf8;

my $count = 0;

sub mail_count {
  return $count ? weechat::color('bold').'✉'.$count.weechat::color('-bold') : '';
}


sub mail_update {
  my @l = map glob("$_/new/*"), split /,/, weechat::config_get_plugin('dir');
  my $new = @l;
  if($new != $count) {
    $count = $new;
    weechat::bar_item_update('maildir');
  }
}


weechat::register('maildir', 'Yorhel', '1.1', 'MIT', 'Maildir notification thing', '', '');
weechat::config_set_plugin('dir', "$ENV{HOME}/Mail") if !weechat::config_is_set_plugin('dir');
weechat::config_set_plugin('interval', 10) if !weechat::config_is_set_plugin('interval');
weechat::bar_item_new('maildir', "mail_count", "");
mail_update;
weechat::hook_timer(weechat::config_get_plugin('interval')*1000, 0, 0, 'mail_update', '');

