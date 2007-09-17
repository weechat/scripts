# A script which print currently played track (format is configurable) in xmms2 to a channel or private window.
# This script is BSD licensed.
# Konstantin Merenkov @ 17.09.2007 11:20:57 MSD
# kmerenkov AT gmail DOT com

use strict;
use warnings;
use Audio::XMMSClient;

weechat::register("xmms2", "0.1", "", "Prints currently played track info to a channel");

weechat::add_command_handler("xmms2", "xmms2", "Prints currently played track info to a channel");

sub get_npformat {
    my $np_format = weechat::get_plugin_config("npformat");
    if (!$np_format) {
        $np_format = 'np: $artist - $title';
        if (weechat::set_plugin_config("npformat", $np_format) == 0) {
            weechat::print("Error on setting xmms2.npformat option");
        }
    }
    return $np_format;
}

sub xmms2 {
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

                }
                else {
                    my $info = $result->value;
                    my $format = get_npformat;
                    foreach my $key (keys %{$info}) {
                        $format =~ s/\$$key/$info->{$key}/g;
                    }
                    weechat::command("/me ".$format);
                }
            }
        }
    }
    return weechat::PLUGIN_RC_OK;
}
