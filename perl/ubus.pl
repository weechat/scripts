# WeeChat ubus notifications 
# Arvid Picciani <aep at hereticlinux dot org>
# Released under GPL3.
#
# 0.2 uses spec single ubus interface now.

use strict;
use FileHandle;
weechat::register("ubus", "Arvid Picciani <aep at hereticlinux dot org>", 
                  "0.2",  "GPL3", "Ubus Notification", "", "");


my @signals=qw(weechat_pv weechat_highlight);

foreach(@signals){
    weechat::hook_signal($_, "ubus_signal", "");
}

sub ubus_signal{
    my $u;
    open($u,"|ubus-connect ~/.ubus/amvient/notify >/dev/null 2>/dev/null");
    $u->autoflush(1);
    my @b = split(/\t/,$_[2]);
    print {$u} "<font color=\"red\">$_[1]</font>  &nbsp; &lt;$b[0]&gt; &nbsp; $b[1]\n";
    close $u;
    return weechat::WEECHAT_RC_OK;
}
