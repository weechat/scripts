# Copyright (c) 2008 Ben <dumbtech@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

use File::ReadBackwards;

weechat::register('histecho', '0.2', '',
    'Displays the last few log lines at the start of each chat.');

my $lines = weechat::get_plugin_config('lines');
if ($lines eq '') { $lines = 5 }
my $log_path = weechat::get_config('log_path');
my $weechat_dir = weechat::get_info('weechat_dir');
$log_path =~ s/\%h/$weechat_dir/;

weechat::add_event_handler('buffer_open', 'echo');
sub echo {
    my $server  = weechat::get_info('server');
    my $channel = weechat::get_info('channel');
    my $bw = File::ReadBackwards->new("$log_path$server.$channel.weechatlog");
    my $i = 0;
    my @hist;

    while (defined(my $log_line = $bw->readline) && $i < $lines) {
        if ($log_line =~ /<\S+>/) {
            chomp($log_line);
            push(@hist, $log_line);
            $i++;
        }
    }
    foreach (reverse(@hist)) { weechat::print($_) }

    return weechat::PLUGIN_RC_OK;
}
