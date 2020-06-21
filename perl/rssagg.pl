# Copyright (c) 2012 by R1cochet <deltaxrho@gmail.com>
# All rights reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# rssagg, version 1.1, for weechat version 0.3.7 or later
# watch multiple RSS/RDF/Atom feeds and display the most current articles
# Thank you nils_2, Flashcode, Nei
#
# Requires Perl module XML::FeedPP
#
#
# Script will attempt to create a directory on first run: %h/perl/tmp
# A temp directory is needed in order for the module to work properly.
# You may change the directory location with the option: "rssagg.engine.temp_dir"
#
#
# Usage:
#   display all settings for script:
#     /set rssagg*
#   show RSS feed manager (you must have feeds added):
#     /rssagg
#   add a feed:
#     /rssagg add name http://example.com/rss.php
#   add a cookie to a feed:
#     /rssagg cookie name uid=1234;pass=abc123efg456;
#   buffer input shortcuts must be provided with the correct fields to be set
#
#
# History:
# 2020-06-21, Sebastien Helleu <flashcode@flashtux.org>:
#       v1.2:   Make call to bar_new compatible with WeeChat >= 2.9.
# 2013-04-06, R1cochet <deltaxrho@gmail.com>:
#       v1.1:   Added option "rssagg.engine.autostop". Added "last" option to /rssagg command.
#               Muted filter in rssagg buffer. Fixed partial feed callback. Other bug fixes.
# 2012-11-05, R1cochet <deltaxrho@gmail.com>:
#       v1.0:   Initial Public Release
#

use strict;
use warnings;
use POSIX qw(strftime);
use XML::FeedPP;

my $SCRIPT_NAME = "rssagg";
my $VERSION     = "1.2";
my $SCRIPT_DESC = "RSS/RDF/Atom feed aggregator for WeeChat";

######################### Global Vars #########################
my $config_file;            # config file pointer
my %config = ();            # config hash
my @feeds;                  # list of feed names
my %feeds = ();             # feed hash
my %partial_feed = ();      # for multiple url callbacks on large feeds
my $rssagg_buffer = "";     # pointer to buffer
my $rsslist_buffer = "";    # pointer to free buffer
my $rssagg_bar = "";        # pointer to bar
my @buffer_lines;           # buffer display lines
my @bar_lines;              # bar lines
my @bar_lines_time;         # bar line time
my $current_line = 0;       # current line in list buffer
my $list_max_name = 0;      # max name length
my $temp_dir = "";          # temp_dir

my %entity2char = (         # html entity hash
    # Some normal chars that have special meaning in SGML context
    amp => '&', 'gt' => '>', 'lt' => '<', quot => '"', apos => "'",
    # PUBLIC ISO 8879-1986//ENTITIES Added Latin 1//EN//HTML
    AElig   => chr(198), Aacute => chr(193), Acirc  => chr(194), Agrave => chr(192), Aring  => chr(197),
    Atilde  => chr(195), Auml   => chr(196), Ccedil => chr(199), ETH    => chr(208), Eacute => chr(201),
    Ecirc   => chr(202), Egrave => chr(200), Euml   => chr(203), Iacute => chr(205), Icirc  => chr(206),
    Igrave  => chr(204), Iuml   => chr(207), Ntilde => chr(209), Oacute => chr(211), Ocirc  => chr(212),
    Ograve  => chr(210), Oslash => chr(216), Otilde => chr(213), Ouml   => chr(214), THORN  => chr(222),
    Uacute  => chr(218), Ucirc  => chr(219), Ugrave => chr(217), Uuml   => chr(220), Yacute => chr(221),
    aacute  => chr(225), acirc  => chr(226), aelig  => chr(230), agrave => chr(224), aring  => chr(229),
    atilde  => chr(227), auml   => chr(228), ccedil => chr(231), eacute => chr(233), ecirc  => chr(234),
    egrave  => chr(232), eth    => chr(240), euml   => chr(235), iacute => chr(237), icirc  => chr(238),
    igrave  => chr(236), iuml   => chr(239), ntilde => chr(241), oacute => chr(243), ocirc  => chr(244),
    ograve  => chr(242), oslash => chr(248), otilde => chr(245), ouml   => chr(246), szlig  => chr(223),
    thorn   => chr(254), uacute => chr(250), ucirc  => chr(251), ugrave => chr(249), uuml   => chr(252),
    yacute  => chr(253), yuml   => chr(255),
    # Some extra Latin 1 chars that are listed in the HTML3.2 draft (21-May-96)
    copy => chr(169), reg => chr(174), nbsp => chr(160),
    # Additional ISO-8859/1 entities listed in rfc1866 (section 14)
    iexcl   => chr(161), cent   => chr(162), pound  => chr(163), curren => chr(164), yen    => chr(165),
    brvbar  => chr(166), sect   => chr(167), uml    => chr(168), ordf   => chr(170), laquo  => chr(171),
    'not'   => chr(172), shy    => chr(173), macr   => chr(175), deg    => chr(176), plusmn => chr(177),
    sup1    => chr(185), sup2   => chr(178), sup3   => chr(179), acute  => chr(180), micro  => chr(181),
    para    => chr(182), middot => chr(183), cedil  => chr(184), ordm   => chr(186), raquo  => chr(187),
    frac14  => chr(188), frac12 => chr(189), frac34 => chr(190), iquest => chr(191), 'times'=> chr(215),
    divide  => chr(247),
    ( $] > 5.007 ? (
        'OElig'     => chr(338), 'oelig'    => chr(339), 'Scaron'   => chr(352), 'scaron'   => chr(353),
        'Yuml'      => chr(376), 'fnof'     => chr(402), 'circ'     => chr(710), 'tilde'    => chr(732),
        'Alpha'     => chr(913), 'Beta'     => chr(914), 'Gamma'    => chr(915), 'Delta'    => chr(916),
        'Epsilon'   => chr(917), 'Zeta'     => chr(918), 'Eta'      => chr(919), 'Theta'    => chr(920),
        'Iota'      => chr(921), 'Kappa'    => chr(922), 'Lambda'   => chr(923), 'Mu'       => chr(924),
        'Nu'        => chr(925), 'Xi'       => chr(926), 'Omicron'  => chr(927), 'Pi'       => chr(928),
        'Rho'       => chr(929), 'Sigma'    => chr(931), 'Tau'      => chr(932), 'Upsilon'  => chr(933),
        'Phi'       => chr(934), 'Chi'      => chr(935), 'Psi'      => chr(936), 'Omega'    => chr(937),
        'alpha'     => chr(945), 'beta'     => chr(946), 'gamma'    => chr(947), 'delta'    => chr(948),
        'epsilon'   => chr(949), 'zeta'     => chr(950), 'eta'      => chr(951), 'theta'    => chr(952),
        'iota'      => chr(953), 'kappa'    => chr(954), 'lambda'   => chr(955), 'mu'       => chr(956),
        'nu'        => chr(957), 'xi'       => chr(958), 'omicron'  => chr(959), 'pi'       => chr(960),
        'rho'       => chr(961), 'sigmaf'   => chr(962), 'sigma'    => chr(963), 'tau'      => chr(964),
        'upsilon'   => chr(965), 'phi'      => chr(966), 'chi'      => chr(967), 'psi'      => chr(968),
        'omega'     => chr(969), 'thetasym' => chr(977), 'upsih'    => chr(978), 'piv'      => chr(982),
        'ensp'      => chr(8194), 'emsp'    => chr(8195), 'thinsp'  => chr(8201), 'zwnj'    => chr(8204),
        'zwj'       => chr(8205), 'lrm'     => chr(8206), 'rlm'     => chr(8207), 'ndash'   => chr(8211),
        'mdash'     => chr(8212), 'lsquo'   => chr(8216), 'rsquo'   => chr(8217), 'sbquo'   => chr(8218),
        'ldquo'     => chr(8220), 'rdquo'   => chr(8221), 'bdquo'   => chr(8222), 'dagger'  => chr(8224),
        'Dagger'    => chr(8225), 'bull'    => chr(8226), 'hellip'  => chr(8230), 'permil'  => chr(8240),
        'prime'     => chr(8242), 'Prime'   => chr(8243), 'lsaquo'  => chr(8249), 'rsaquo'  => chr(8250),
        'oline'     => chr(8254), 'frasl'   => chr(8260), 'euro'    => chr(8364), 'image'   => chr(8465),
        'weierp'    => chr(8472), 'real'    => chr(8476), 'trade'   => chr(8482), 'alefsym' => chr(8501),
        'larr'      => chr(8592), 'uarr'    => chr(8593), 'rarr'    => chr(8594), 'darr'    => chr(8595),
        'harr'      => chr(8596), 'crarr'   => chr(8629), 'lArr'    => chr(8656), 'uArr'    => chr(8657),
        'rArr'      => chr(8658), 'dArr'    => chr(8659), 'hArr'    => chr(8660), 'forall'  => chr(8704),
        'part'      => chr(8706), 'exist'   => chr(8707), 'empty'   => chr(8709), 'nabla'   => chr(8711),
        'isin'      => chr(8712), 'notin'   => chr(8713), 'ni'      => chr(8715), 'prod'    => chr(8719),
        'sum'       => chr(8721), 'minus'   => chr(8722), 'lowast'  => chr(8727), 'radic'   => chr(8730),
        'prop'      => chr(8733), 'infin'   => chr(8734), 'ang'     => chr(8736), 'and'     => chr(8743),
        'or'        => chr(8744), 'cap'     => chr(8745), 'cup'     => chr(8746), 'int'     => chr(8747),
        'there4'    => chr(8756), 'sim'     => chr(8764), 'cong'    => chr(8773), 'asymp'   => chr(8776),
        'ne'        => chr(8800), 'equiv'   => chr(8801), 'le'      => chr(8804), 'ge'      => chr(8805),
        'sub'       => chr(8834), 'sup'     => chr(8835), 'nsub'    => chr(8836), 'sube'    => chr(8838),
        'supe'      => chr(8839), 'oplus'   => chr(8853), 'otimes'  => chr(8855), 'perp'    => chr(8869),
        'sdot'      => chr(8901), 'lceil'   => chr(8968), 'rceil'   => chr(8969), 'lfloor'  => chr(8970),
        'rfloor'    => chr(8971), 'lang'    => chr(9001), 'rang'    => chr(9002), 'loz'     => chr(9674),
        'spades'    => chr(9824), 'clubs'   => chr(9827), 'hearts'  => chr(9829), 'diams'   => chr(9830),
    ) : ())
);

weechat::register($SCRIPT_NAME, 'R1cochet', $VERSION, 'GPL3', $SCRIPT_DESC, "", "");
my $wee_version_number = weechat::info_get("version_number", "") || 0;
if ($wee_version_number < 0x00030700) {
    weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: requires at least WeeChat v0.3.7");
    weechat::command("","/wait 1ms /perl unload $SCRIPT_NAME");
}

######################### Initial config #########################
sub init_config {
    $config_file = weechat::config_new($SCRIPT_NAME, "config_reload_cb", "");
    return if (!$config_file);

    # create new section in config file
    $config{'sections'}{'color'} = weechat::config_new_section($config_file, "color", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'color'}) {
        weechat::config_free($config_file);
        return;
    }   # add the options to the section
    $config{'options'}{'buffer_title_running'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "buffer_title_running", "color",
                                                                       "Color of active feeds in feeds buffer title.", "", 0, 0, "lightmagenta", "lightmagenta", 0, "", "", "", "", "", "",);
    $config{'options'}{'item'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "item", "color",
                                                                       "Color of the feed article title.", "", 0, 0, "default", "default", 0, "", "", "", "", "", "",);
    $config{'options'}{'link'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "link", "color",
                                                                       "Color of the feed article link.", "", 0, 0, "cyan", "cyan", 0, "", "", "", "", "", "",);
    $config{'options'}{'status_cookie'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "status_cookie", "color",
                                                                       "Color for status \"cookie\" (\"C\")", "", 0, 0, "lightmagenta", "lightmagenta", 0, "", "", "", "", "", "",);
    $config{'options'}{'status_running'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "status_running", "color",
                                                                       "Color for status \"running\" (\"r\")", "", 0, 0, "lightgreen", "lightgreen", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_bg_selected'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_bg_selected", "color",
                                                                       "Text color of feed delay in list buffer.", "", 0, 0, "red", "red", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_delay'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_delay", "color",
                                                                       "Text color of feed delay in list buffer.", "", 0, 0, "magenta", "magenta", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_delay_selected'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_delay_selected", "color",
                                                                       "Text color of feed delay in list buffer.", "", 0, 0, "lightmagenta", "lightmagenta", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_last'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_last", "color",
                                                                       "Text color of feed last call in list buffer.", "", 0, 0, "white", "white", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_last_selected'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_last_selected", "color",
                                                                       "Text color of feed last call in list buffer.", "", 0, 0, "white", "white", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_link'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_link", "color",
                                                                       "Text color of feed URL in list buffer.", "", 0, 0, "default", "default", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_link_selected'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_link_selected", "color",
                                                                       "Text color of feed URL in list buffer.", "", 0, 0, "white", "white", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_name'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_name", "color",
                                                                       "Text color of feed name in list buffer.", "", 0, 0, "cyan", "cyan", 0, "", "", "", "", "", "",);
    $config{'options'}{'text_name_selected'} = weechat::config_new_option($config_file, $config{'sections'}{'color'}, "text_name_selected", "color",
                                                                       "Text color of feed name in list buffer.", "", 0, 0, "lightcyan", "lightcyan", 0, "", "", "", "", "", "",);

    $config{'sections'}{'engine'} = weechat::config_new_section($config_file, "engine", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'engine'}) {
        weechat::config_free($config_file);
        return;
    }
    $config{'options'}{'autostart_delay'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "autostart_delay", "integer",
                                                                       "Set the delay of time in minutes between autostart of feeds. The first feed will be started right away. Each feed thereafter will be started in (n-1)*d, where n = the feed number and d = delay.",
                                                                       "", 0, 5, "1", "1", 0, "", "", "", "", "", "",);
    $config{'options'}{'autostart_on_add'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "autostart_on_add", "boolean",
                                                                       "Automatically start a feed once added.", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);
    $config{'options'}{'autostart_on_load'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "autostart_on_load", "boolean",
                                                                       "Automatically start all feeds on script load.", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);
    $config{'options'}{'autostop'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "autostop", "integer",
                                                                       "Automatically stop feed after n number of fails (set to 0 to disable).", "", 0, 20, "3", "3", 0, "", "", "", "", "", "",);
    $config{'options'}{'default_delay'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "default_delay", "integer",
                                                                       "Set the default delay for fetching feeds (mins).", "", 10, 240, "60", "60", 0, "", "", "", "", "", "",);
    $config{'options'}{'max_headlines'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "max_headlines", "integer",
                                                                       "Set the maximum amount of feed articles to save.", "", 5, 300, "20", "20", 0, "", "", "", "", "", "",);
    $config{'options'}{'timeout'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "timeout", "integer",
                                                                       "Set the default timeout limit for fetching feeds (secs).", "", 10, 120, "20", "20", 0, "", "", "", "", "", "",);
    $config{'options'}{'tmp_dir'} = weechat::config_new_option($config_file, $config{'sections'}{'engine'}, "temp_dir", "string",
                                                                       "Set the location to save old feeds to.", "", 0, 0, "%h/perl/tmp", "%h/perl/tmp", 0, "", "", "", "", "", "",);

    $config{'sections'}{'look'} = weechat::config_new_section($config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'look'}) {
        weechat::config_free($config_file);
        return;
    }
    $config{'options'}{'bar_autoscroll'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "bar_autoscroll", "boolean",
                                                                       "Autoscroll bar when feeds are updated.", "", 0, 0, "on", "on", 0, "", "", "", "", "", "",);
    $config{'options'}{'bar_max_headlines'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "bar_max_headlines", "integer",
                                                                       "Set the maximum amount of feed articles to keep in the bar.", "", 1, 40, "20", "20", 0, "", "", "", "", "", "",);
    $config{'options'}{'bar_prefix_align'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "bar_prefix_align", "integer",
                                                                       "Set the alignment of the prefix in the bar. This mimics option \"weechat.look.prefix_align\"", "left|right|none", 0, 0, "right", "right", 0, "", "", "", "", "", "",);
    $config{'options'}{'buffer_highlight_strings'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "buffer_highlight_strings", "string",
                                                                       "Comma separated list of strings to highlight in buffer mode. ( \"-\" = none )", "", 0, 0, "-", "-", 0, "", "", "", "", "", "",);
    $config{'options'}{'buffer_max_headlines'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "buffer_max_headlines", "integer",
                                                                       "Set the maximum amount of feed articles to keep when switching to buffer mode.", "", 1, 200, "40", "40", 0, "", "", "", "", "", "",);
    $config{'options'}{'channel_prefix'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "channel_prefix", "string",
                                                                       "Set the rss channel prefix.", "", 0, 0, "#", "#", 1, "", "", "", "", "", "",);
    $config{'options'}{'color_channel'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "color_channel", "boolean",
                                                                       "Color the rss channel a semi-random color.", "", 0, 0, "on", "on", 0, "", "", "", "", "", "",);
    $config{'options'}{'filter_mode'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "filter_mode", "integer",
                                                                       "Set rssagg buffer filter mode. Set to \"reverse\" to show only lines containing string.", "normal|reverse", 0, 0, "normal", "normal", 0, "", "", "", "", "", "",);
    $config{'options'}{'format'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "format", "string",
                                                                       "Set the format of the print line. ( \%C = channel header, \%I = item, \%L = URL, \%t = tab )", "", 0, 0, "%C%t%I %L", "%C%t%I %L", 0, "", "", "", "", "", "",);
    $config{'options'}{'output'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "output", "integer",
                                                                       "Where new feeds will be sent.", "bar|buffer", 0, 0, "buffer", "buffer", 0, "", "", "", "", "", "",);
    $config{'options'}{'scroll_horiz'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "scroll_horiz", "integer",
                                                                       "Scroll content of rsslist buffer n%.", "", 1, 100, "10", "10", 0, "", "", "", "", "", "",);
    $config{'options'}{'show_in_hotlist'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "show_in_hotlist", "boolean",
                                                                       "Show in hotlist (status bar/buffer.pl).", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);
    $config{'options'}{'show_on_start'} = weechat::config_new_option($config_file, $config{'sections'}{'look'}, "show_on_start", "boolean",
                                                                       "Show initial feeds when timer first started.", "", 0, 0, "off", "off", 0, "", "", "", "", "", "",);

    # User added config options
    $config{'sections'}{'feeds'} = weechat::config_new_section($config_file, "feeds", 1, 1, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'feeds'}) {
        weechat::config_free($config_file);
        return;
    }
    $config{'sections'}{'delay'} = weechat::config_new_section($config_file, "delay", 1, 1, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'delay'}) {
        weechat::config_free($config_file);
        return;
    }
    $config{'sections'}{'cookies'} = weechat::config_new_section($config_file, "cookies", 1, 1, "", "", "", "", "", "", "", "", "", "");
    if (!$config{'sections'}{'cookies'}) {
        weechat::config_free($config_file);
        return;
    }

    my %init_hash = ();
    my $home_dir = weechat::info_get("weechat_dir", "");
    if (-e "$home_dir/$SCRIPT_NAME.conf") {
        open(my $fh, "<:encoding(UTF-8)", "$home_dir/$SCRIPT_NAME.conf") || weechat::print("", "can't open UTF-8 encoded filename: $!");
        my $section;
        while (<$fh>) {
            chomp;
            if (/^\s*\[(\w+)\].*/) {
                $section = $1;
            }
            if (/^(\w+)\s=?\s(\"?.*\"?)?$/) {
                my $keyword = $1;
                my $value = $2 ;
                # put them into hash
                $init_hash{$section}{$keyword} = $value;
            }
        }
        close ($fh);

        # add the feed links and delays to the config hash
        for my $section (sort keys %init_hash) {
            if ($section =~ /feeds/) {
                for my $key (sort keys %{ $init_hash{$section} } ) {
                    if ($key !~ /_delay$/) {
                        push @feeds, "$key";
                        # pointer to feed link
                        $feeds{"$key"}{'link'} = weechat::config_new_option($config_file, $config{'sections'}{'feeds'}, "$key", "string",
                                                                              "This is the link to the feed", "", 0, 0, "$init_hash{$section}{$key}", "$init_hash{$section}{$key}", 0, "", "", "", "", "", "",);
                        # pointer to feed delay
                        $feeds{"$key"}{'delay'} = weechat::config_new_option($config_file, $config{'sections'}{'feeds'}, "$key"."_delay", "integer",
                                                                             "Feed fetch delay (mins).", "", 10, 720, $init_hash{"feeds"}{$key."_delay"}, $init_hash{"feeds"}{$key."_delay"}, 0, "", "", "", "", "", "",);
                    }
                    # pointer to cookie if cookie exists
                    if (exists $init_hash{'cookies'}{$key}) {
                        # pointer to the feed cookie
                        $feeds{"$key"}{'cookie'} = weechat::config_new_option($config_file, $config{'sections'}{'cookies'}, "$key", "string",
                                                                         "Cookie to send when fetching feed.", "", 0, 0, "$init_hash{cookies}{$key}", "$init_hash{cookies}{$key}", 0, "", "", "", "", "", "",);
                    }
                }
            }
        }
    }
    @feeds = sort(@feeds);  # sort feeds for interactive buffer
}
# config callbacks
sub config_reload_cb {      # reload config file
    return weechat::config_reload($config_file);
}
sub config_read {           # read my config file
    return weechat::config_read($config_file);
}
sub config_write {          # write to my config file
    return weechat::config_write($config_file);
}
init_config();              # load config
config_read();              # get options if already in config file

######################### Subroutines #########################
# get tmp dir
sub tmp_dir {
    my $dir = weechat::config_string($config{'options'}{'tmp_dir'});
    if ($dir =~ /%h/) {
        my $homedir = weechat::info_get("weechat_dir", "");
        $dir =~ s/%h/$homedir/;
    }
    if ($dir !~ /\/$/) { $dir .= "/"; }
    return $dir;
}
# create tmp dir
sub create_tmp_dir {
    my $tmp_dir = tmp_dir();
    $tmp_dir =~ s/\/$//;
    unless (-d "$tmp_dir") {
        use File::Path qw(make_path);
        weechat::print("", "Could not find tmpdir.\nAttempting to create: $tmp_dir");
        make_path("$tmp_dir") or weechat::print("", "Unable to create $tmp_dir: $!");
    }
    return;
}
# delete old .xml files
sub clean_tmp {
    my ($file, $dir) = (shift, tmp_dir());
    if ($file eq "all") {   # unlink all .xml files
        my @files = <$dir*.xml>;
        unlink @files;
    }
    else {  # unlink
        unlink "$dir/$file.xml";
    }
    return;
}
# max feed name length
sub list_max_legth {
    my $max = 20;
    foreach (@feeds) {
        $max = length($_) if (length($_) > $max);
    }
    return $max;
}
# color lines
sub item_color {        # item or link color
    my ($option, $line) = @_;
    $line = weechat::color(weechat::config_color($config{'options'}{"$option"})) . $line . weechat::color("reset");
    return $line;
}
# create bar delimiter
sub build_delimiter {
    my $delimiter = weechat::config_string(weechat::config_get("weechat.look.prefix_suffix"));
    $delimiter = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_prefix_suffix"))) . $delimiter . weechat::color("reset");
    return $delimiter;
}
# clean feed items
sub clean_item {
    my $item = shift;
    $item =~ s/^\s*//;
    $item =~ s/\s*$//;
    $item =~ s/\n*$//;
    return $item;
}
# clean array of feeds
sub clean_array {
    my @array = @_;
    foreach my $line (@array) {
        $line =~ s/^\s*//;
        $line =~ s/\s*$//;
    }
    @array = grep !/^\s*$/, @array;
    return @array;
}
# shrink array of feeds
sub shrink_array {
    my ($option, @array) = @_;     # max_headlines
    my $max_lines = weechat::config_integer($config{'options'}{"$option"});
    while ($#array > $max_lines) {
        shift(@array);
    }
    return @array;
}
# set agg buffer title
sub set_buffer_title {
    if ($rssagg_buffer ne "") {
        my $filters = "f=filter";
        my $filter_active = infolist_filter();
        if ($filter_active eq "rssagg") {
            $filters .= "*";
        }
        my $filter_mode = weechat::config_string($config{'options'}{'filter_mode'});
        my $feeds_title = "| ";
        if (@feeds) {
            foreach (sort @feeds) {
                my $feed = $_;          # use this var to prevent renaming of @feeds elements
                if (exists $feeds{"$_"}{'timer'}) {
                    $feed = weechat::color(weechat::config_color($config{'options'}{'buffer_title_running'})) . $feed . weechat::color("reset");     # color feed if active
                }
                $feeds_title .= "$feed ";
            }
        }
        else { $feeds_title = " "; }
        weechat::buffer_set($rssagg_buffer, "title", "RSS Feed Monitor | a=add c=cookie d=delete $filters l=list m=$filter_mode r=restart s=start z=stop $feeds_title");           # buffer title
        return weechat::WEECHAT_RC_OK;
    }
    return;
}
# create timestamp to use in bar
sub bar_time_format {
    my $time = strftime(weechat::config_string(weechat::config_get("weechat.look.buffer_time_format")), localtime);
    if ($time =~ /\$\{\w+\}/) {
        while ($time =~ /\$\{(\w+)\}/) {
            my $color = weechat::color($1);
            $time =~ s/\$\{\w+\}/$color/;
        }
    }
    else {
        my $color = weechat::color(weechat::config_string(weechat::config_get("weechat.color.chat_time_delimiters")));
        my $reset = weechat::color("reset");
        $time =~ s/(\d*)(.)(\d*)/$1$color$2$reset$3/g;
    }
    return $time;
}
# color rss channel name
sub title_build {
    my $name = shift;
    # get prefix
    my $channel_prefix = weechat::config_string($config{'options'}{'channel_prefix'});
    if ($channel_prefix ne "") {
        $name = $channel_prefix . $name;
    }
    # create color
    if (weechat::config_boolean($config{'options'}{'color_channel'})) {
        my $color = 0;
        my @chars = split //, $name;
        foreach my $char (@chars) {
            $color += ord($char);
        }
        $color = ($color % 10) + 1;
        $name = weechat::color($color) . $name . weechat::color("reset");
    }
    return $name;
}
# wrap channel name with prefix and suffix
sub feed_name_format {
    my $name = shift;
    # get buffer print prefix and suffix
    my $prefix = weechat::color(weechat::config_color(weechat::config_get("irc.color.nick_prefix"))) . weechat::config_string(weechat::config_get("irc.look.nick_prefix")) . weechat::color("reset");
    my $suffix = weechat::color(weechat::config_color(weechat::config_get("irc.color.nick_suffix"))) . weechat::config_string(weechat::config_get("irc.look.nick_suffix")) . weechat::color("reset");
    # format the channel name
    $name = title_build($name);
    $name = $prefix . $name . $suffix;
    return $name;
}
# print feeds
sub print_feeds {
    my ($name, $articles) = @_;
    my $refresh_name = $name;
    $name = feed_name_format($name);
    my @articles = split /\n/, $articles;       # most current is first
    @articles = reverse(@articles);             # reverse so most recent is printed last. both in buffer and bar
    my @formatted_lines;                        # used for printing in buffer mode
    my $time = bar_time_format();               # create a timestamp and push it onto @bar_lines_time
    my $format = weechat::config_string($config{'options'}{'format'});

    foreach my $line (@articles) {
        my $print_line = $format;
        my ($title,  $link) = split "_:_", $line, 2;
        $title = item_color("item", $title);
        $link = item_color("link", $link);
        $print_line =~ s/%C/$name/g;
        $print_line =~ s/%t/\t/g;
        $print_line =~ s/%I/$title/g;
        $print_line =~ s/%L/$link/g;
        push @formatted_lines, "$print_line";       # what we print right now
        push @buffer_lines, "$print_line";          # append to max_buffer_headlines for recall
        push @bar_lines, "$print_line";             # append to max_bar_headlines for update
        push @bar_lines_time, $time;
    }
    @buffer_lines = shrink_array("buffer_max_headlines", @buffer_lines);

    if (weechat::config_string($config{'options'}{'output'})  eq "bar") { # print to bar do
        if ($rssagg_bar ne "") {        # update bar
            weechat::bar_item_update("rssagg");
            if (weechat::config_boolean($config{'options'}{'bar_autoscroll'})) { #autoscroll on
                weechat::command("", "/bar scroll rssagg * ye");
            }
        }
        else {
            weechat::print("", weechat::prefix("error")."$SCRIPT_NAME Error: No bar found to print too.");
        }
    }
    else {
        if ($rssagg_buffer ne "") {     # print to buffer
            weechat::print($rssagg_buffer, "$_") for @formatted_lines;
        }
        else {
            weechat::print("", weechat::prefix("error")."$SCRIPT_NAME Error: No buffer found to print too.");
        }
    }
    return;
}
# create agg buffer
sub buffer_create_agg {
    $rssagg_buffer = weechat::buffer_search("perl", "rssagg");
    if ($rssagg_buffer eq "") {
        $rssagg_buffer = weechat::buffer_new("rssagg", "buffer_input", "", "buffer_close", "");
    }
    if (!weechat::config_boolean($config{'options'}{'show_in_hotlist'})) {
        weechat::buffer_set($rssagg_buffer, "notify", "0");                 # turn off show in hotlist
    }
    my $highlights = weechat::config_string($config{'options'}{'buffer_highlight_strings'});
    weechat::buffer_set($rssagg_buffer, "highlight_words", "$highlights");  # highlights
    weechat::buffer_set($rssagg_buffer, "localvar_set_no_log", "1");        # turn off logging
    return weechat::WEECHAT_RC_OK;
}
# create list buffer
sub buffer_create_list {
    $current_line = 0;
    $rsslist_buffer = weechat::buffer_search("perl", "rsslist");
    if ($rsslist_buffer eq "") {
        $rsslist_buffer = weechat::buffer_new("rsslist", "buffer_input", "", "buffer_close", "");
    }
    weechat::buffer_set($rsslist_buffer, "type", "free");                   # allows you to use print_y
    weechat::buffer_set($rsslist_buffer, "title", "RSS Feed Manager | Alt+key d=delete r=restart t=toggle | Input: q=close a=add c=cookie d=delete r=restart s=start z=stop");    # buffer title
    weechat::buffer_set($rsslist_buffer, "notify", "0");                    # turn off show in hotlist
    weechat::buffer_set($rsslist_buffer, "highlight_words", "-");           # no highlights
    weechat::buffer_set($rsslist_buffer, "localvar_set_no_log", "1");       # turn off logging
    weechat::buffer_set($rsslist_buffer, "display", "1");                   # switch to this buffer
    weechat::buffer_set($rsslist_buffer, "key_bind_meta2-A",        "/$SCRIPT_NAME **up");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta2-B",        "/$SCRIPT_NAME **down");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta2-23~",      "/$SCRIPT_NAME **left");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta2-24~",      "/$SCRIPT_NAME **right");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta-meta2-1~",  "/$SCRIPT_NAME **scroll_top");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta-meta2-4~",  "/$SCRIPT_NAME **scroll_bottom");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta-d",         "/$SCRIPT_NAME **del");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta-r",         "/$SCRIPT_NAME **restart");
    weechat::buffer_set($rsslist_buffer, "key_bind_meta-t",         "/$SCRIPT_NAME **toggle");
    return weechat::WEECHAT_RC_OK;
}
# sub get window number
sub get_window_number {
    if ($rsslist_buffer ne "") {
        my $window = weechat::window_search_with_buffer($rsslist_buffer);
        return "-window ".weechat::window_get_integer ($window, "number")." " if ($window ne "");
    }
    return "";
}
# sub refresh full list buffer
sub refresh_full {
    if ($rsslist_buffer ne "") {
        if ($feeds[0]) {            # if we have at least one feed
            @feeds = sort(@feeds);
            $current_line = 0;
            for (0..$#feeds) {      # print lines in buffer
                refresh_line($_);
            }
        }
        else {
            weechat::command($rsslist_buffer, "/close");
        }
    }
}
# sub refresh line
sub refresh_line {
    if ($rsslist_buffer ne "") {
        my $y = shift;
        if ($y <= $#feeds && exists $feeds{"$feeds[$y]"}{'delay'}) {    # check if hash element exists incase adding new feed
            $list_max_name = list_max_legth();
            my $format = sprintf("%%s %%s%%s%%-2s%%s%%-%ds %%s%%-4s%%s%%-7s%%s%%s", $list_max_name);
            my ($running, $cookie, $last_call) = (" ", " ", " ");
            $running = "r" if (exists $feeds{"$feeds[$y]"}{'timer'});
            $cookie = "C" if (exists $feeds{"$feeds[$y]"}{'cookie'});
            $last_call = $feeds{"$feeds[$y]"}{'last_call'} if (exists $feeds{"$feeds[$y]"}{'last_call'});
            my ($c_run, $c_cookie) = (weechat::color(weechat::config_color($config{'options'}{'status_running'})), weechat::color(weechat::config_color($config{'options'}{'status_cookie'})));
            my ($c_name, $c_delay) =  (weechat::color(weechat::config_color($config{'options'}{'text_name'})), weechat::color(weechat::config_color($config{'options'}{'text_delay'})));
            my ($c_last, $c_link) = (weechat::color(weechat::config_color($config{'options'}{'text_last'})), weechat::color(weechat::config_color($config{'options'}{'text_link'})));

            if ($y == $current_line) {
                $c_run = weechat::color(weechat::config_color($config{'options'}{'status_running'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
                $c_cookie = weechat::color(weechat::config_color($config{'options'}{'status_cookie'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
                $c_name = weechat::color(weechat::config_color($config{'options'}{'text_name_selected'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
                $c_delay = weechat::color(weechat::config_color($config{'options'}{'text_delay_selected'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
                $c_last = weechat::color(weechat::config_color($config{'options'}{'text_last_selected'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
                $c_link = weechat::color(weechat::config_color($config{'options'}{'text_link_selected'}).",".weechat::config_color($config{'options'}{'text_bg_selected'}));
            }
            my $strline = sprintf($format, $c_run, $running, $c_cookie, $cookie, $c_name, $feeds[$y],
                                    $c_delay, weechat::config_integer($feeds{"$feeds[$y]"}{'delay'}),
                                    $c_last, $last_call, $c_link, weechat::config_string($feeds{"$feeds[$y]"}{'link'}));
            weechat::print_y($rsslist_buffer, $y, "$strline");       #;
        }
    }
}
# sub refresh line by feed name
sub refresh_feed_line {
    my $feed = shift;
    for (0..$#feeds) {      # print lines in buffer
        if ($feeds[$_] eq "$feed") {
            refresh_line($_);
        }
    }
}
# check if line is outside view
sub line_outside_window {
    if ($rsslist_buffer ne "") {
        undef my $infolist;
        my $window = weechat::window_search_with_buffer($rsslist_buffer);
        $infolist = weechat::infolist_get("window", $window, "") if $window;
        if ($infolist) {
            if (weechat::infolist_next($infolist)) {
                my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
                my $chat_height = weechat::infolist_integer($infolist, "chat_height");
                my $window_number = "-window ".weechat::infolist_integer($infolist, "number")." ";
                if ($start_line_y > $current_line) {
                    weechat::command($rsslist_buffer, "/window scroll ".$window_number."-".($start_line_y - $current_line));
                }
                else {
                    if ($start_line_y <= $current_line - $chat_height) {
                        weechat::command($rsslist_buffer, "/window scroll ".$window_number."+".($current_line - $start_line_y - $chat_height + 1));
                    }
                }
            }
        }
        weechat::infolist_free($infolist);
    }
}
# sub set the current line
sub set_current_line {
    my $new_current_line = shift;
    my $old_current_line = $current_line;
    $current_line = $new_current_line;
    $current_line = $#feeds if ($current_line > $#feeds);
    if ($old_current_line != $current_line) {
        refresh_line($old_current_line);
        refresh_line($current_line);
    }
}
# sub bar_create
sub bar_create {
    $rssagg_bar = weechat::bar_search("rssagg");
    if ($rssagg_bar eq "") {
        if ($wee_version_number >= 0x02090000) {
            $rssagg_bar = weechat::bar_new("rssagg", "off", 0, "root", "", "top", "vertical", "vertical", "4", "20", "default", "cyan", "default", "default", 'off', "rssagg");
        } else {
            $rssagg_bar = weechat::bar_new("rssagg", "off", 0, "root", "", "top", "vertical", "vertical", "4", "20", "default", "cyan", "default", 'off', "rssagg");
        }
    }
    weechat::bar_item_new("rssagg", "rssagg_bar_build", "");
    return weechat::WEECHAT_RC_OK;
}
# sub bar_destroy
sub bar_destroy {
    $rssagg_bar = weechat::bar_search("rssagg");
    if ($rssagg_bar ne "") {
        weechat::bar_remove($rssagg_bar);
    }
    my $rssagg_bar_item = weechat::bar_item_search("rssagg");
    if ($rssagg_bar_item ne "") {
        weechat::bar_item_remove($rssagg_bar_item);
    }
    return weechat::WEECHAT_RC_OK;
}
# sub filter infolist
sub infolist_filter {
    my $filter = "";
    my $infolist = weechat::infolist_get("filter", "", "rssagg");
    if ($infolist ne "") {
        weechat::infolist_next($infolist);
        $filter = weechat::infolist_string($infolist, "name");
    }
    weechat::infolist_free($infolist);
    return $filter;
}
# sub filter string
sub filter_string {
    my $filter_string = "";
    my $infolist = weechat::infolist_get("filter", "", "rssagg");
    if ($infolist ne "") {
        weechat::infolist_next($infolist);
        $filter_string = weechat::infolist_string($infolist, "regex");
    }
    weechat::infolist_free($infolist);
    return $filter_string;
}

######################### Callbacks #########################
# buffer input callback
sub buffer_input {
    my ($data, $buffer, $string) = @_;
    my @commands = split " ", $string;
    if (@commands) {
        my $hdata = weechat::hdata_get("buffer");
        my $buffer_name = weechat::hdata_string($hdata, $buffer, "name");

        if (lc($commands[0]) eq "a" && $commands[1] && $commands[2]) {
            weechat::command("", "/rssagg add $commands[1] $commands[2]");
        }
        if (lc($commands[0]) eq "c" && $commands[1] && $commands[2]) {
            weechat::command("", "/rssagg cookie $commands[1] $commands[2]");
        }
        if (lc($commands[0]) eq "d" && $commands[1]) {
            weechat::command("", "/rssagg del $commands[1]");
        }
        if (lc($commands[0]) eq "r" && $commands[1]) {
            weechat::command("", "/rssagg restart $commands[1]");
        }
        if (lc($commands[0]) eq "s" && $commands[1]) {
            weechat::command("", "/rssagg start $commands[1]");
        }
        if (lc($commands[0]) eq "z" && $commands[1]) {
            weechat::command("", "/rssagg stop $commands[1]");
        }
        if ($buffer_name eq "rsslist") {
            if ($commands[0] eq "q") {
                weechat::command($buffer, "/close");
            }
        }
        if ($buffer_name eq "rssagg") {
            if ($commands[0] eq "f") {
                my $filter = infolist_filter();
                if ($filter eq "rssagg") {
                        weechat::command("", "/mute /filter del rssagg");
                }
                if ($commands[1]) {
                    if (weechat::config_string($config{'options'}{'filter_mode'}) eq "reverse") {
                        $commands[1] = "!".$commands[1];
                        $commands[1] =~ s/,/,!/g;
                    }
                    weechat::command("", "/mute /filter add rssagg perl.rssagg * $commands[1]");
                }
                set_buffer_title();
            }
            if ($commands[0] eq "l") {
                weechat::command("", "/rssagg list");
            }
            if ($commands[0] eq "m") {
                if (weechat::config_string($config{'options'}{'filter_mode'}) eq "normal") {
                    weechat::command("", "/mute /set rssagg.look.filter_mode reverse");
                }
                else {
                    weechat::command("", "/mute /set rssagg.look.filter_mode normal");
                }
            }
        }
    }
    return weechat::WEECHAT_RC_OK;
}
# buffer close callback
sub buffer_close {
    my $buffer = $_[1];
    my $hdata = weechat::hdata_get("buffer");       # get buffer name
    my $buffer_name = weechat::hdata_string($hdata, $buffer, "name");
    if ($buffer_name eq "rsslist") {
        $rsslist_buffer = "";
    }
    else {
        $rssagg_buffer = "";
    }
    return weechat::WEECHAT_RC_OK;
}
# buffer scrolled callback
sub window_scrolled_cb {
    my ($data, $signal, $signal_data) = @_;
    if ($rsslist_buffer ne "") {
        my $infolist = weechat::infolist_get("window", $signal_data, "");
        if (weechat::infolist_next($infolist))  {
            my $old_current_line = $current_line;
            my $new_current_line = $current_line;
            my $start_line_y = weechat::infolist_integer($infolist, "start_line_y");
            my $chat_height = weechat::infolist_integer($infolist, "chat_height");
            $new_current_line += $chat_height if ($new_current_line < $start_line_y);
            $new_current_line -= $chat_height if ($new_current_line >= $start_line_y + $chat_height);
            $new_current_line = $start_line_y if ($new_current_line < $start_line_y);
            $new_current_line = $start_line_y + $chat_height - 1 if ($new_current_line >= $start_line_y + $chat_height);
            set_current_line($new_current_line);
        }
        weechat::infolist_free($infolist);
    }
    return weechat::WEECHAT_RC_OK;
}
# bar item build
sub rssagg_bar_build {
    my ($string, $align_num, $count) = ('', 0, 0);
    @bar_lines = shrink_array("bar_max_headlines", @bar_lines);
    @bar_lines_time = shrink_array("bar_max_headlines", @bar_lines_time);

    my @string = @bar_lines;            # dont change @bar_lines incase switch to buffer
    if (@string) {
        my $delim = build_delimiter();  # create delimiter
        foreach(@string) {              # create prefix number foreach loop
            my $prefix_num = (index(weechat::string_remove_color($_, ""), "\t"));
            $align_num = $prefix_num if ($prefix_num > $align_num);
        }
        foreach my $line (@string) {    # format each line for printing
            my $prefix_num = (index(weechat::string_remove_color($line, ""), "\t"));
            my ($channel, $line_item) = split /\t/, $line, 2;
            if (weechat::config_string($config{'options'}{'bar_prefix_align'}) eq "left") {
                $string .= $bar_lines_time[$count] . " $channel" . (" " x ($align_num - $prefix_num)) . " $delim " . $line_item . "\n";
            }
            elsif (weechat::config_string($config{'options'}{'bar_prefix_align'}) eq "right") {
                $string .= $bar_lines_time[$count] . (" " x ($align_num - $prefix_num)) . " $channel" . " $delim " . $line_item . "\n";
            }
            else {
                $string .= $bar_lines_time[$count] . " $channel " . $line_item . "\n";
            }
            $count++;
        }
    }
    return $string;
}
# hooked proccess_hash
sub process_cb {
    my ($data, $command, $return_code, $out, $err) = @_;
    if ($return_code > 0) {         # cURL error
        weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: cURL error: ($return_code) $err");
        weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: Command: $command");
        if (weechat::config_integer($config{'options'}{'autostop'}) ) {
            $feeds{"$data"}{"autostop"}++;
            if ($feeds{"$data"}{"autostop"} >= weechat::config_integer($config{'options'}{'autostop'}) ) {
                weechat::command("", "/rssagg stop $data");
                $feeds{"$data"}{"autostop"} = 0;
            }
        }
        $partial_feed{"$data"} = ""; # delete if defined
    }
    elsif ($return_code == weechat::WEECHAT_HOOK_PROCESS_ERROR) {
        weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: Error with fetching of feed: \"$data\". Maybe the site is down.");
        if (weechat::config_integer($config{'options'}{'autostop'}) ) {
            $feeds{"$data"}{"autostop"}++;
            if ($feeds{"$data"}{"autostop"} >= weechat::config_integer($config{'options'}{'autostop'}) ) {
                weechat::command("", "/rssagg stop $data");
                $feeds{"$data"}{"autostop"} = 0;
            }
        }
        $partial_feed{"$data"} = "";
    }
    elsif ($return_code == weechat::WEECHAT_HOOK_PROCESS_RUNNING) {      # handle multiple callbacks. Long feeds
        $partial_feed{"$data"} .= $out;
        return weechat::WEECHAT_RC_OK;
    }
    elsif ($return_code == 0 && $out) {
        my $feed;
        if ($partial_feed{"$data"} ne "") {
            $partial_feed{"$data"} .= $out;
            if ($partial_feed{"$data"} !~ /\<\?xml version=/) {   # RSS feeds have <channel> and <item> tags
                weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: Feed with name \"$data\" does not appear to be an RSS/Atom feed. The fetched document is not a valid feed.");
                if (weechat::config_integer($config{'options'}{'autostop'}) ) {
                    $feeds{"$data"}{"autostop"}++;
                    if ($feeds{"$data"}{"autostop"} >= weechat::config_integer($config{'options'}{'autostop'}) ) {
                        weechat::command("", "/rssagg stop $data");
                        $feeds{"$data"}{"autostop"} = 0;
                    }
                }
                $partial_feed{"$data"} = "";
                return weechat::WEECHAT_RC_OK;
            }
            else {
                $feed = XML::FeedPP->new($partial_feed{"$data"}, -type => 'string', utf8_flag => 1);
                $partial_feed{"$data"} = "";
            }
        }
        else {
            if ($out !~ /\<\?xml version=/) {            # Atom feeds have <entry> tag
                weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: Feed with name \"$data\" does not appear to be an RSS/RDF/Atom feed. The fetched document is not a valid feed.");
                if (weechat::config_integer($config{'options'}{'autostop'}) ) {
                    $feeds{"$data"}{"autostop"}++;
                    if ($feeds{"$data"}{"autostop"} >= weechat::config_integer($config{'options'}{'autostop'}) ) {
                        weechat::command("", "/rssagg stop $data");
                        $feeds{"$data"}{"autostop"} = 0;
                    }
                }
                $partial_feed{"$data"} = "";
                return weechat::WEECHAT_RC_OK;
            }
            else {
                $feed = XML::FeedPP->new($out, -type => 'string', utf8_flag => 1);
                $partial_feed{"$data"} = "";
            }
        }
        if ($feed ne "") {
            my $articles = "";      # articles: newest first; $headline_:_$url
            my $tmpdir = tmp_dir();

            if (-e $tmpdir.$data.".xml") {
                my $old = XML::FeedPP->new($tmpdir.$data.".xml", -type => 'file', utf8_flag => 1);
                $feed->merge($old);
                $feed->normalize();
                $feed->limit_item(weechat::config_integer($config{'options'}{'max_headlines'}));

                my (@old, @new, @unseen);
                foreach my $item ($old->get_item()) {
                    push @old, $item->title();
                }
                foreach my $item ($feed->get_item()) {
                    push @new, $item->title();
                }
                @unseen=grep!${{map{$_,1}@old}}{$_},@new;       # remove old from new

                foreach my $unseen (@unseen) { # my $unseen
                    my $item = $feed->match_item(title => qr/\Q$unseen\E/);
                    if ($item && $item->title() =~ /\Q$unseen\E/) {
                        my $title = clean_item($item->title());
                        $title =~ s/&#(\d+);/pack("U",$1)/ge;
                        $title =~ s/&(\w+\d*);/$entity2char{$1} if (exists $entity2char{$1})/ge;
                        $articles .= $title . "_:_" . clean_item($item->link()) . "\n";
                    }
                    else { weechat::print("", clean_item($item->title())); }
                }
            }
            else {
                if (weechat::config_boolean($config{'options'}{'show_on_start'})) {
                    $feed->normalize();
                    $feed->limit_item(weechat::config_integer($config{'options'}{'max_headlines'}));
                    foreach my $item ($feed->get_item()) {
                        my $title = clean_item($item->title());
                        $title =~ s/&#(\d+);/pack("U",$1)/ge;
                        $title =~ s/&(\w+\d*);/$entity2char{$1} if (exists $entity2char{$1})/ge;
                        $articles .= $title . "_:_" . clean_item($item->link()) . "\n";
                    }
                }
            }
            $feed->to_file($tmpdir.$data.".xml");

            if ($articles ne "") {
                print_feeds($data, $articles);
            }
        }
        else {
            weechat::print("", weechat::prefix("error")."$SCRIPT_NAME: Error: failed to parse feed: $data\nTry restarting the feed in a couple minutes.");
            weechat::command("", "/rssagg stop $data");
        }
        $partial_feed{"$data"} = "";     # reset $partial_feed
    }
    return weechat::WEECHAT_RC_OK;
}
# hooked timer
sub timer_cb {      # hook process_hashtable to fetch feed
    my ($data, $remaining) = @_;
    my $url = weechat::config_string($feeds{"$data"}{'link'});
    if (exists $feeds{"$data"}{'cookie'}) {
        my $cookie = weechat::config_string($feeds{"$data"}{'cookie'});
        if ($url =~ /^https/) {
            weechat::hook_process_hashtable("url:$url", { "ssl_verifypeer" => 0, "cookie" => $cookie }, weechat::config_integer($config{'options'}{'timeout'}) * 1000, "process_cb", $data);
        }
        else {
            weechat::hook_process_hashtable("url:$url", { "cookie" => $cookie }, weechat::config_integer($config{'options'}{'timeout'}) * 1000, "process_cb", $data);
        }
    }
    else {
        if ($url =~ /^https/) {
            weechat::hook_process_hashtable("url:$url", { "ssl_verifypeer" => 0 }, weechat::config_integer($config{'options'}{'timeout'}) * 1000, "process_cb", $data);
        }
        else {
            weechat::hook_process("url:$url", weechat::config_integer($config{'options'}{'timeout'}) * 1000, "process_cb", $data);
        }
    }
    $feeds{"$data"}{'last_call'} = strftime "%H:%M", localtime;
    if ($rsslist_buffer ne "") {    # update rsslist window
        @feeds = sort(@feeds);
        refresh_feed_line($data);
    }
    return weechat::WEECHAT_RC_OK;
}
# hooked autostart timer
sub autostart_cb {
    my ($feed, $remaining) = @_;
    unless (exists  $feeds{"$feed"}{'timer'}) {
        $partial_feed{"$feed"} = "";
        timer_cb($feed);
        $feeds{"$feed"}{'timer'} = weechat::hook_timer(weechat::config_integer($feeds{"$feed"}{'delay'}) * 60000, 0, 0, "timer_cb", $feed);
        refresh_feed_line($feed);
    }
    delete $feeds{"$feed"}{'autostart'} if (exists $feeds{"$feed"}{'autostart'});
    return weechat::WEECHAT_RC_OK;
}
# hooked config options
sub config_cb {
    my ($data, $option, $value) = @_;
    return weechat::WEECHAT_RC_OK if ($option !~ /^rssagg\./);

    if ($option =~ /^rssagg\.color/) {
        if ($option !~ /(color\.item|color\.link)$/) {
            if ($option =~ /rssagg.color.buffer_title_running/) {
                set_buffer_title();
            }
            else {
                refresh_full();
            }
        }
    }
    elsif ($option =~ /^rssagg\.engine/) {
        if ($option =~ /\.temp_dir$/) {
            create_tmp_dir();
            my $new_temp_dir = tmp_dir();
            # move all files to new dir
            use File::Copy qw(move);
            my @files = <$temp_dir*.xml>;
            foreach (@files) {
                my $file = $_;
                $file =~ s/^\Q$temp_dir\E/$new_temp_dir/;
                move($_, $file);
            }
            $temp_dir = $new_temp_dir;
        }
    }
    elsif ($option =~ /^rssagg\.look/) {
        if ($option =~ /bar_prefix_align/) {   # update bar
            if ($rssagg_bar ne "") {
                weechat::bar_item_update("rssagg");
            }
        }
        if ($option =~ /\.buffer_highlight_strings$/) {
            weechat::buffer_set($rssagg_buffer, "highlight_words", "$value");
        }
        if ($option =~ /\.filter_mode/) {      # m=normal/reverse
            my $filter_string = filter_string();
            if ($filter_string ne "") {
                $filter_string =~ s/!//g;
                weechat::command($rssagg_buffer, "f $filter_string");
            }
            set_buffer_title();
        }
        if ($option =~ /\.output$/) {
            if ($value eq "bar") {            # changing to bar
                $rssagg_buffer = weechat::buffer_search("perl", "rssagg");
                if ($rssagg_buffer ne "") {
                    weechat::buffer_close($rssagg_buffer);                  # destroy buffer
                }
                bar_create();                                               # create bar
                if (weechat::config_boolean($config{'options'}{'bar_autoscroll'})) { #autoscroll bar
                    weechat::command("", "/bar scroll rssagg * ye");
                }
            }
            elsif ($value eq "buffer") {
                bar_destroy();                                              # destroy bar
                buffer_create_agg();                                        # create agg buffer
                set_buffer_title();                                         # set agg buffer title
                weechat::print($rssagg_buffer, "$_") for @buffer_lines;     # update agg buffer
            }
        }
        if ($option =~ /show_in_hotlist$/) {
            if ($rssagg_buffer ne "") {
                my $notify = 0;
                $notify = 1 if ($value eq "on");
                weechat::buffer_set($rssagg_buffer, "notify", "$notify");
            }
        }
    }
    else {      # all other option changes affect feed. restart if running
        my @opts = split /\./, $option;
        if ($opts[2]) {
            $opts[2] =~ s/_delay$//;
            for (0..$#feeds) {
                if ($opts[2] eq "$feeds[$_]") {
                    refresh_line($_);
                }
            }
            if (exists $feeds{"$opts[2]"}{'timer'}) {
                weechat::command("", "/rssagg restart $opts[2]");
            }
        }
    }
    return weechat::WEECHAT_RC_OK;
}
# hooked command completion
sub command_completion_cb {
    my ($data, $completion_item, $buffer, $completion) = @_;
    if (@feeds) {
        foreach my $feed (@feeds) {
            weechat::hook_completion_list_add($completion, "$feed", 0, weechat::WEECHAT_LIST_POS_SORT);
        }
    }
    return weechat::WEECHAT_RC_OK;
}
# hooked command callback
sub command_rss {
    my ($data, $buffer, @args) = ($_[0], $_[1], split " ", $_[2], 4);
    my $hdata = weechat::hdata_get("buffer");       # get buffer name
    my $buffer_name = weechat::hdata_string($hdata, $buffer, "name");

    if (!$args[0] || $args[0] eq "list") {
        if (@feeds) {                       # list feeds
            buffer_create_list();           # create free buffer
            refresh_full();
            if ($rsslist_buffer ne "") {    # set to active buffer
                weechat::buffer_set($rsslist_buffer, "display", "1");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: No feeds added yet.");
        }
        return weechat::WEECHAT_RC_OK;
    }
    if ($args[0] eq "last") {
        if (@buffer_lines) {
            if ($args[1] && ($args[1] =~ /^\d+$/)) {
                my $last = weechat::config_integer($config{'options'}{'buffer_max_headlines'});
                $last = $args[1] if ($args[1] < $last);
                for (my $i = scalar @buffer_lines - $last; $i <= $#buffer_lines; $i++) {   
                    weechat::print($buffer, "$buffer_lines[$i]");
                }
            }
            else {
                weechat::print($buffer, "$_") for @buffer_lines;
            }
        }
    }
    if ($args[0] eq "add") {
        if ($args[2]) {
            if (weechat::config_search_option($config_file, $config{'sections'}{'feeds'}, "$args[1]")) {
                weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Feed already exists. You must remove the old feed before adding a new one with the same name.");
            }
            else {      # add the options
                push @feeds, $args[1];
                @feeds = sort(@feeds);
                $feeds{"$args[1]"}{'link'} = weechat::config_new_option($config_file, $config{'sections'}{'feeds'}, "$args[1]", "string",
                                                                              "This is the link to the feed", "", 0, 0, "$args[2]", "$args[2]", 0, "", "", "", "", "", "",);
                my $delay = weechat::config_integer($config{'options'}{'default_delay'});
                $feeds{"$args[1]"}{'delay'} = weechat::config_new_option($config_file, $config{'sections'}{'feeds'}, $args[1]."_delay", "integer",
                                                                              "Feed fetch delay (mins).", "", 10, 720, "$delay", "$delay", 0, "", "", "", "", "", "",);
                weechat::print($buffer, "New feed added: $args[1] $args[2]") if ($buffer_name ne "rsslist");
                if (weechat::config_integer($config{'options'}{'autostart_on_add'})) {
                    weechat::command("", "/rssagg start $args[1]");
                }
                set_buffer_title();
                refresh_full();
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a name and link to add a feed.");
        }
    }
    if ($args[0] eq "cookie") {
        if ($args[1]) {
            if (exists $feeds{"$args[1]"}{'link'}) {
                if ($args[2]) {
                    if (exists $feeds{"$args[1]"}{'cookie'}) {
                        weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Feed already has a cookie set.");
                    }
                    else {      # add cookie option
                        $feeds{"$args[1]"}{'cookie'} = weechat::config_new_option($config_file, $config{'sections'}{'cookies'}, "$args[1]", "string",
                                                                         "Cookie to send when fetching feed.", "", 0, 0, "$args[2]", "$args[2]", 0, "", "", "", "", "", "",);
                        weechat::print($buffer, "Cookie added to feed: $args[1]. You need to restart the feed for changes to take effect.") if ($buffer_name ne "rsslist");
                        refresh_feed_line($args[1]);
                    }
                }
                else {
                    weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a value for the cookie.");
                }
            }
            else {
                weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Feed does not exist.");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a feed name to add a cookie too.");
        }
    }
    if ($args[0] eq "del") {
        if ($args[1]) {
            if (exists $feeds{"$args[1]"}{'link'}) {
                # delete feed options
                weechat::config_option_unset($feeds{"$args[1]"}{'link'});
                weechat::config_option_unset($feeds{"$args[1]"}{'delay'});
                if (exists $feeds{"$args[1]"}{'cookie'}) {
                    weechat::config_option_unset($feeds{"$args[1]"}{'cookie'});
                }
                my $rc = weechat::WEECHAT_CONFIG_OPTION_UNSET_OK_REMOVED;
                # remove trigger from trigger array and config hash, unhoook timer
                weechat::print_y($rsslist_buffer, $#feeds, "") if ($rsslist_buffer ne "");#;
                @feeds = grep !/\Q$args[1]\E\z/, @feeds;
                @feeds = sort(@feeds);
                weechat::unhook($feeds{"$args[1]"}{'timer'}) if (exists $feeds{"$args[1]"}{'timer'});
                delete $feeds{"$args[1]"};
                weechat::print($buffer, "Deleted Feed: $args[1]") if ($buffer_name ne "rsslist");
                set_buffer_title();
                weechat::command($rsslist_buffer, "/close") unless ($feeds[0]);
                refresh_full();
            }
            else {
                weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Cannot find feed: $args[1]");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a feed name to delete.");
        }
    }
    if ($args[0] eq "start") {
        if ($args[1]) {
            if (exists  $feeds{"$args[1]"}{'timer'}) {      # timer object exists print already started
                weechat::print("", "Feed is already running: $args[1]");
            }
            elsif (exists $feeds{"$args[1]"}{'link'}) {
                $partial_feed{"$args[1]"} = "";
                timer_cb($args[1]);                         # hook process for initial feed fetch
                # hook timer
                $feeds{"$args[1]"}{'timer'} = weechat::hook_timer(weechat::config_integer($feeds{"$args[1]"}{'delay'}) * 60000, 0, 0, "timer_cb", $args[1]);
                weechat::print($buffer, "Started feed: $args[1]") if ($buffer_name ne "rsslist");
                set_buffer_title();
                refresh_feed_line($args[1]);
                if (exists $feeds{"$args[1]"}{'autostart'}) {
                    weechat::unhook($feeds{"$args[1]"}{'autostart'});
                    delete $feeds{"$args[1]"}{'autostart'};
                }
            }
            else {
                weechat::print($buffer, "Cannot find feed: $args[1]");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a feed name to start, or \"all\" to start all feeds.");
        }
    }
    if ($args[0] eq "stop") {
        if ($args[1]) {
            if (exists  $feeds{"$args[1]"}{'timer'}) {
                weechat::unhook($feeds{"$args[1]"}{'timer'});   # unhook timer
                # destroy feed timer
                delete $feeds{"$args[1]"}{'timer'};
                delete $feeds{"$args[1]"}{'last_call'};
                delete $partial_feed{"$args[1]"};
                clean_tmp("$args[1]");
                weechat::print($buffer, "Stopped feed: $args[1]") if ($buffer_name ne "rsslist");
                set_buffer_title();
                refresh_feed_line($args[1]);
            }
            else {
                weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Timer does not exists for feed: $args[1]");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a feed name to stop, or \"all\" to stop all feeds.");
        }
    }
    if ($args[0] eq "restart") {
        if ($args[1]) {
            if (exists $feeds{"$args[1]"}{'timer'}) {       # restart the feed
                weechat::unhook($feeds{"$args[1]"}{'timer'});
                delete $feeds{"$args[1]"}{'timer'};
                delete $feeds{"$args[1]"}{'last_call'};

                timer_cb($args[1]);                 # hook process for initial feed fetch
                # hook timer
                $feeds{"$args[1]"}{'timer'} = weechat::hook_timer(weechat::config_integer($feeds{"$args[1]"}{'delay'}) * 60000, 0, 0, "timer_cb", $args[1]);
                weechat::print($buffer, "Started feed: $args[1]") if ($buffer_name ne "rsslist");
                set_buffer_title();
                refresh_feed_line($args[1]);
            }
            else {
                weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: Feed is not running.") if ($buffer_name ne "rsslist");
            }
        }
        else {
            weechat::print($buffer, weechat::prefix("error")."$SCRIPT_NAME Error: You must supply a feed name to restart.");
        }
    }
    if ($args[0] eq "**up") {
        if ($current_line > 0) {
            $current_line--;
            refresh_line($current_line + 1);
            refresh_line($current_line);
            line_outside_window();
        }
    }
    if ($args[0] eq "**down") {
        if ($current_line < $#feeds) {
            $current_line++;
            refresh_line($current_line - 1);
            refresh_line($current_line);
            line_outside_window();
        }
    }
    if ($args[0] eq "**left") {
        weechat::command($rsslist_buffer, "/window scroll_horiz ".get_window_number()."-".weechat::config_integer($config{'options'}{'scroll_horiz'})."%");
    }
    if ($args[0] eq "**right") {
        weechat::command($rsslist_buffer, "/window scroll_horiz ".get_window_number().weechat::config_integer($config{'options'}{'scroll_horiz'})."%");
    }
    if ($args[0] eq "**scroll_top") {
        my $old_current_line = $current_line;
        $current_line = 0;
        refresh_line($old_current_line);
        refresh_line($current_line);
        weechat::command($rsslist_buffer, "/window scroll_top ".get_window_number());
    }
    if ($args[0] eq "**scroll_bottom") {
        my $old_current_line = $current_line;
        $current_line = $#feeds;
        refresh_line($old_current_line);
        refresh_line($current_line);
        weechat::command($rsslist_buffer, "/window scroll_bottom ".get_window_number());
    }
    if ($args[0] eq "**close") {
        weechat::command($rsslist_buffer, "/close");
    }
    if ($args[0] eq "**del") {
        weechat::command("", "/rssagg del $feeds[$current_line]");
    }
    if ($args[0] eq "**restart") {
        weechat::command("", "/rssagg restart $feeds[$current_line]");
    }
    if ($args[0] eq "**toggle") {
        if (exists $feeds{"$feeds[$current_line]"}{'timer'}) {
            weechat::command("", "/rssagg stop $feeds[$current_line]");
        }
        else {
            weechat::command("", "/rssagg start $feeds[$current_line]");
        }
        set_buffer_title();
        refresh_line($current_line);
    }
    return weechat::WEECHAT_RC_OK;
}

######################### Hooks #########################
weechat::hook_config("rssagg.*", "config_cb", "");
weechat::hook_completion("rssagg_feeds", "List of RSS feeds", "command_completion_cb", "");
weechat::hook_command($SCRIPT_NAME, $SCRIPT_DESC,                                                           # command, command description
    "last <number> || list || add <name> <url> || cookie <name> <cookie> || del <name> || restart <name> || start <name> || stop <name>",     # args
    "   last:   Show last n number of feeds in current buffer (defaults to rssagg.look.buffer_max_headlines)\n".
    "   list:   List all feeds (you must have at least one feed)\n".                                               # args description
    "    add:   Add a new feed\n".
    " cookie:   Add a cookie to a feed\n".
    "    del:   Delete an existing feed\n".
    "restart:   Restart a running feed\n".
    "  start:   Start an existing feed\n".
    "   stop:   Stop a running feed\n\n".
    "Without argument, this command opens a buffer with list of feeds.\n\n".
    "On rsslist buffer, the possible status for each feed are:\n".
    "  r C\n".
    "  | |\n".
    "  | cookie\n".
    "  running\n\n".
    "Keys on rsslist buffer:\n".
    "  alt+d  delete feed\n".
    "  alt+r  restart a feed\n".
    "  alt+t  toggle a feed on or off\n\n".
    "Input allowed on rsslist buffer:\n".
    "  d/r  action on named feed (same as keys above)\n".
    "  a    add a new feed\n".
    "  c    add a cookie to a feed\n".
    "  q    close buffer\n".
    "  s    start a feed\n".
    "  z    stop a feed\n\n".
    "Input allowed on rssagg buffer:\n".
    "  a/c/d/r/s/z  action on named feed (same as input above)\n".
    "  f            filter lines containing string(s)\n".
    "  l            show rsslist buffer\n".
    "  m            change \"rssagg.look.filter_mode\"\n\n".
    "Examples:\n".
    "  list all feeds, their status, and their link:\n".
    "    /rssagg list\n".
    "  add a new feed with name \"feed1\" and link \"http://www.myfeed.com\":\n".
    "    /rssagg add feed1 http://www.myfeed.com\n".
    "  add a cookie to an existing feed with name \"feed1\":\n".
    "    /rssagg cookie feed1 uid=1234;pass=abc123efg456;\n".
    "  delete an existing feed with name \"feed1\":\n".
    "    /rssagg del feed1\n".
    "  restart an already running feed:\n".
    "   /rssagg restart feed1\n".
    "  start a feed with name \"feed2\":\n".
    "    /rssagg start feed2\n".
    "  stop a running feed with name \"feed2\":\n".
    "    /rssagg stop feed2",
    "last * %-|| list %-|| add * * %-|| cookie %(rssagg_feeds) * %-|| del %(rssagg_feeds) %-|| restart %(rssagg_feeds) %-|| start %(rssagg_feeds) %-|| stop %(rssagg_feeds) %-",  # completion
    "command_rss", "");         # callback, callback data

######################### STARTUP #########################
create_tmp_dir();
clean_tmp("all");
$temp_dir = tmp_dir();
if (weechat::config_string($config{'options'}{'output'}) eq "bar") {
    bar_create();
}
else {
    buffer_create_agg();
    set_buffer_title();
}
## start initial feeds
if (weechat::config_integer($config{'options'}{'autostart_on_load'})) {
    for (my $i = 0; $i <= $#feeds; $i++) {
        if ($feeds[$i]) {
            my $interval = $i * 60000 * weechat::config_integer($config{'options'}{'autostart_delay'}) + 1;
            $feeds{"$feeds[$i]"}{'autostart'} = weechat::hook_timer($interval, 0, 1, "autostart_cb", $feeds[$i]);
        }
    }
}
