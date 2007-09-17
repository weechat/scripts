# A script which automatically changes IRC modes of other users when they join
# This script is BSD licensed.
# Konstantin Merenkov @ 16.09.2007 22:19:56 MSD
# kmerenkov AT gmail DOT com

use warnings;

weechat::register("auto-mode", "0.1", "", "A script which automatically changes IRC modes of other users when they join");
weechat::add_message_handler("JOIN", set_mode);

sub set_mode {
    my @argv = @_;
    # ~/.weechat/mode_list.txt is the file where you are supposed to keep your settings
    open(FILE, "<", $ENV{"HOME"}."/.weechat/mode_list.txt") || die $!;
    while(<FILE>) {
        chomp;
        # mode_list.txt has the following format:
        #     network channel mask mode
        # For example:
        #     freenode #weechat FlashCode!.* o
        # So, if FlashCode joins #weechat on freenode network, his mode will be set to o (channel operator).
        # Just make sure that you don't use spaces in any of your regex.
        # PS: Actually this code was never tested on freenode, but I hope
        #     that their JOIN doesn't differ from JOIN on other servers.
        if (m/(.+) (.+) (.+) (.+)/) {
            my ($server, $chan, $mask, $mode) = ($1, $2, $3, $4);
            if ($argv[0] eq $server) {
                if ($argv[1] =~ m/^:(.+)\!(.+) JOIN :(.+)$/) {
                    my ($inc_nick, $inc_mask, $inc_chan) = ($1, "$1!$2", $3);
                    if ($inc_mask =~ m/$mask/) {
                        weechat::command("/mode $inc_chan $mode $inc_nick", $inc_chan, $argv[0]);
                        last;
                    }
                }
                else {
                    weechat::print("Error parsing JOIN irc command:");
                    weechat::print("\tnetwork:\t$argv[0]");
                    weechat::print("\tirc line:\t$argv[1]");
                    weechat::print("Contact author of this script or feel free to fix it yourself");
                }
            }
        }
    }
    close(FILE);
    return weechat::PLUGIN_RC_OK;
}
