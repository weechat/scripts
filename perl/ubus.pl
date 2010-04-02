# WeeChat ubus notifications 
# Arvid Picciani <aep at hereticlinux dot org>
# Released under GPL3.

use strict;
use FileHandle;
weechat::register("ubus", "Arvid Picciani <aep at hereticlinux dot org>", 
                  "0.1",  "GPL3", "Ubus Notification", "ubus_shutdown", "");

my %fds=();
my @signals=qw(weechat_pv weechat_highlight);

foreach(@signals){
    weechat::hook_signal($_, "ubus_signal", "");
    my $f;
    open($f,"|ubus tap ~/.ipc/weechat/$_");
    $fds{$_}=$f;
    $f->autoflush(1);
}

sub ubus_signal{
    print {$fds{$_[1]}} "$_[2]\n";
    return weechat::WEECHAT_RC_OK;
}

sub ubus_shutdown{
    foreach(@signals){
        close ($fds{$_});
    }
}

