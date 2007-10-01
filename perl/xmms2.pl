# A script which print currently played track (format is configurable) in xmms2 to a channel or private window.
# This script is BSD licensed.
# Konstantin Merenkov @ 17.09.2007 11:20:57 MSD
# kmerenkov AT gmail DOT com
#
# changelog:
# 30.09.2007 23:53:12 MSD: 0.2: added xmms2print, which doesn't send information to a channel but just prints it to a buffer
# 17.09.2007 11:20:57 MSD: 0.1: initial version, can send information about the played song to a channel

use strict;
use warnings;
use Audio::XMMSClient;

weechat::register("xmms2", "0.2", "", "Prints currently played track info to a channel");

weechat::add_command_handler("xmms2", "xmms2", "Sends currently played track info to a channel");
weechat::add_command_handler("xmms2print", "xmms2print", "Prints currently played track to a buffer");

sub get_npformat {
    my $np_format = weechat::get_plugin_config("npformat");
    if (!$np_format) {
        # format is pretty simple:
        # just prefix any key returned from medialib_get_info with $ to get it replaced.
        # Example: np: $artist - $album ($date) - $title
        $np_format = 'np: $artist - $title';
        if (weechat::set_plugin_config("npformat", $np_format) == 0) {
            weechat::print("Error on setting xmms2.npformat option");
        }
    }
    return $np_format;
}

sub xmms2 {
    my $retval = get_line();
    if (length($retval) > 0) {
        weechat::command("/me $retval");
        return weechat::PLUGIN_RC_OK;
    }
    return weechat::PLUGIN_RC_KO;
}

sub xmms2print {
    my $retval = get_line();
    weechat::print("xmms2: $retval");
    return weechat::PLUGIN_RC_OK;
}

sub get_line {
    my $xmms = Audio::XMMSClient->new("weechat-script");
    if (!$xmms->connect) {
        weechat::print("Connection to xmms2 failed: ".$xmms->get_last_error);
    }
    else {
        my $result = $xmms->playback_current_id;
        $result->wait;
        if ($result->iserror) {
            weechat::print("Playback current id returned error: ".$result->get_error);
        }
        else {
            my $id = $result->value;
            if ($id == 0) {
                weechat::print("Nothing is playing in xmms2");
            }
            else {
                $result = $xmms->medialib_get_info($id);
                $result->wait;
                if ($result->iserror) {
                    weechat::print("Error while getting information about currently playing song");
                }
                else {
                    # here's a small caveat
                    # if you don't have 'date' key returned (i.e. it is not in metadata for your currently playing song
                    # and have $date in format string, it won't be replaced (keep your metadata in a good state :p)
                    # it applies to any keyword, not only 'date'
                    my $info = $result->value;
                    my $format = get_npformat;
                    foreach my $key (keys %{$info}) {
                        $format =~ s/\$$key/$info->{$key}/g;
                    }
                    return $format;
                }
            }
        }
    }
    return "";
}
