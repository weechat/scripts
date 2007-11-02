############################################
#   Current Playing Script for Orpheus     #
# made by balrok < carl AT attem DOT de >  #
#    released under GNU GPL v2 or newer    #
############################################


weechat::register ("orpheus", "1.0", "", "orph cur_playing script (usage: /orpheus)");
weechat::add_command_handler ("orpheus", orphinfo);

sub orphinfo {
    if (! -e "$ENV{'HOME'}/.orpheus/currently_playing")
    {}
    else
    {
        open (fi, "<$ENV{'HOME'}/.orpheus/currently_playing");
        $db = <fi>;
        $db =~ s/[\n\r]/ /g;
        weechat::command("/me current playing: $db");
    }
    close (fi);
    $db='';
}
