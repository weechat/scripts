#
# Copyright (c) 2011-2019 by w8rabbit (w8rabbit[at]mail[dot]i2p)
# or from outside i2p: w8rabbit[at]i2pmail[dot]org
#
# Script is under GPL3.
#
# Script is inspired by NullPointerException's xchat script
#
# thanks to darrob for hard beta-testing
#
# 1.9.5: add compatibility with matrix-appservice-irc
# 1.9.4: add compatibility with other kind of messages than irc
# 1.9.3: add compatibility with new weechat_print modifier data (WeeChat >= 2.9)
# 1.9.2: add: i2pr-support
# 1.9.1: fix: uninitialized value (by arza)
#        fix: indentation
# 1.9:   add: Gitter support
# 1.8:   fix: regex on tags
# 1.7:   add: support of colors with format "${color:xxx}" (>= WeeChat 0.4.2)
# 1.6:   add: wildcard "*" for supported_bot_names.
# 1.5:   cleaned up code and make it more readable
# 1.4:   fix: problem with tag "prefix_nick_ccc"
#        improved:  Nicks will be displayed the same way in Nicklist like in channel buffer.
# 1.3:   fix: action message (/me) was printed twice for some remote server
# 1.2.1: fix: add_relay_nick_to_nicklist()
# 1.2:   add: a warning will be displayed if a wrecked message was received
#        add:  debug mode (especially for darrob :-)
#        improved:  whitespaces will be removed in front of message-text
# 1.1:   cleaned up code and made it more readable!!!
#        add: ACTION messages for "uuu" will be displayed now
#        improved:  relaynet_color option (read online help)
#        fix:  quoted "relaynet/relaynick" in cloudc2sd
# 1.0.1: add: new option "relaynet_color" and "relaynet_to_nicklist"
#        fix: network for cloudc2sd relaybot wasn't displayed
# 1.0:   add: cloudc2sd relaybot. (thanks to killyourtv for beta-testing)
# 0.9:   improved: tag-regex for latest weechat version (v0.3.8)
#        add: option "blacklist" to ignore relaynicks (suggested by darrob)
#        fix: regex for FLIP (by operhiem1)
#        improved: nick-modes from relaynicks will not be displayed in nicklist/nickname anymore (for nick auto-completion)
#        NOTE: weechat can handle more than one nick-mode internally, but it will only display the highest rated nick-mode in nicklist.
# 0.8:   improved: regex for FLIP bot (reported by user)
#        fix: problem with nicks in nicklist (thanks to KillYourTV and user)
#        fix: weechat crash when closing buffer with relay nicks in nicklist
#        fix: problem with not displaying first relay nick in nicklist
#        improved: support of colorize_lines script.
# 0.7:   relay nicks will be displayed in nicklist (in its own group)
#        new option "unexpected_msg_handling".
# 0.6:   FLIPRelayBot implemented (suggested by darrob)
# 0.5:   relay indicator for actions added
# 0.4:   hardcoded code removed (weechat 0.3.4 and higher required)
# 0.3:   option suppress_relaynet and suppress_relaynet_channels added.
#        multi-server support added.
# 0.2:   scriptname changed from parse_bot_msg to parse_relayed_msg (suggested by darrob)
#        added version check to use prio for hook_modifier()
# 0.1:   - initial release -


# http://w8rabbit.i2p/parse_relayed_msg.html
# http://h4pf2ydu43jadhckgzign5u4m4gfesbjt3uyne575adx7lh7xeuq.b32.i2p/

# ^(:)(\S+)(!\S+@\S+ )(PRIVMSG #thechannel :)<(\S+)> (.*)
# /rmodifier add relay irc_in_privmsg 1,5,3,4,6 ^(:)(\S+)(!\S+@\S+ )(PRIVMSG #thechannel :)<(\S+)> (.*)
# replace the first \S+ with the bot's nick
# flip bot:
# :FLIPRelayBot!RelayBot@irc2p PRIVMSG #flip-bridge :[nickname] here comes the message
# uuu bot:
# :u!u@public.chat.cloud PRIVMSG #anonet :\0305/IcannNet/Name\0308\0308> \0FWell it doesn't work on windows ...

use strict;
my $SCRIPT_NAME         = "parse_relayed_msg";
my $SCRIPT_VERSION      = "1.9.5";
my $SCRIPT_DESCR        = "proper integration of remote users' nicknames in channel and nicklist";
my $SCRIPT_AUTHOR       = "w8rabbit";
my $SCRIPT_LICENCE      = "GPL3";

# =============== options ===============
my %option = (  "supported_bot_names"   => "i2pr,cloudrelay*,MultiRelay*,FLIPRelayBot*,i2pRelay,u2,uuu,RelayBot,lll,iRelay,fox,wolf,hawk,muninn,gribble,vulpine,*GitterBot",
                "supported_message_kinds" => "irc_privmsg,matrix_message",
                "debug"                 => "off",
                "blacklist"             => "",
                "servername"            => "i2p,freenet",
                "nick_mode"             => "⇅",
                "nick_mode_color"       => "yellow",
                "suppress_relaynet"     => "off",
                "relaynet_color"        => "blue",
                "relaynet_to_nicklist"  => "off",
                "suppress_relaynet_channels" => "",
                "timer"                 => "600",
                "unexpected_msg_handling" => "unchanged",     # drop, decrease notification level, unchanged
);

my %script_desc = ( "blacklist"           => "Comma-separated list of relayed nicknames to be ignored (similar to /ignore). The format is case-sensitive: <server>.<relaynick>",
                    "supported_bot_names" => "Comma-separated list of relay bots.",
                    "supported_message_kinds" => "Comma-separated list of message kinds.",
                    "debug"               => "Enable output of raw IRC messages. This is a developer feature and should generally be turned off. The format is:  <servername>:<botname> (default: off)",
                    "servername"          => "Comma-separated list of internal servers to enable $SCRIPT_NAME for. (default: i2p,freenet)",
                    "nick_mode"           => "Prefix character used to mark relayed nicknames. (default: ⇅). Since WeeChat 0.4.2 you can use format \${color:xxx} but this doesn't affect nicklist.",
                    "nick_mode_color"     => "Color of the prefix character. (default: yellow)",
                    "suppress_relaynet"   => "Hide nicknames' network part (if applicable). (default: off)",
                    "suppress_relaynet_channels" => "Comma-separated list of channels to activate suppress_relaynet in. Format: \"servername.channel\", e.g. \"i2p.#i2p-dev,freenode.#weechat\". (default: \"\" (i.e. global))",
                    "relaynet_color"      => "Color of nicknames' network part. Leave blank for altering colors. (default: \"\")",
                    "relaynet_to_nicklist" => "Include relaynets in the nicklist. (default: off)",
                    "timer"               => "Time (in s) after which relayed nicknames get removed from the nicklist. (default: 600)",
                    "unexpected_msg_handling" => "Ignore relay bot messages with unexpected syntax (drop/unchanged). (default: unchanged)",
);
# =============== internal values ===============
my $weechat_version             = "";
my @bot_nicks                   = "";
my @message_kinds               = "";
my @list_of_server              = "";
my @suppress_relaynet_channels  = "";
my @blacklist                   = "";

my $group_name = "relay_nicks";                                 # group name for nicklist
my %nick_timer          = ();
my %Hooks               = ();

# =============== callback from hook_print() ===============
sub parse_relayed_msg_cb
{
    my ( $data, $modifier, $modifier_data, $string ) = @_;

    # its neither a channel nor a query buffer
    my $result = should_handle_modifier($modifier_data);
    return $string unless ($result);

    my $buffer = "";
    my $tags = "";
    if ($modifier_data =~ /0x/)
    {
        # WeeChat >= 2.9
        $modifier_data =~ m/([^;]*);(.*)/;
        $buffer = $1;
        $tags = $2;
    }
    else {
        # WeeChat <= 2.8
        $modifier_data =~ m/([^;]*);([^;]*);(.*)/;
        $buffer = weechat::buffer_search($1, $2);
        $tags = $3;
    }
    my $servername = weechat::buffer_get_string($buffer, "localvar_server");
    my $channelname = weechat::buffer_get_string($buffer, "localvar_channel");

    return $string if ($servername eq "" or $channelname eq "");

    return $string  if ( !grep /^$servername$/, @list_of_server );          # does server exists?

    my $buf_ptr = $buffer;

    $string =~ m/^(.*)\t(.*)/;                                              # nick[tab]string
    my $nick = $1;                                                          # get the nick name (with prefix!)
    my $line = $2;                                                          # get written text
#    $nick = weechat::string_remove_color($nick,"");                         # remove color-codes from nick
    $line = weechat::string_remove_color($line,"");                         # remove color-codes from line

    $modifier_data =~ m/(^|,)nick_([^,]*)(,|$)/;                            # get the nick name from modifier_data (without nick_mode and color codes!)
    $nick = $2;

    # display_mode : 0 = /, 1 = @
    my $result = string_mask_to_regex($nick);
    if ($result)
#    if ( grep /^$nick$/, @bot_nicks )                                       # does a bot exists?
    {
        my $blacklist_raw = weechat::config_get_plugin("blacklist");
        @blacklist = split( /,/,$blacklist_raw);
        # message from muninn bot!
        if ( $line =~ m/^<([^@]+)@([^>]+)\>\s(.+)$/ )
        {
            my ($relaynick, $relaynet, $relaymsg) = ($1,$2,$3);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,$relaynet,1);
            (undef,$relaymsg) = colorize_lines($modifier_data,$relaynick,$relaymsg);

            $string = create_string_with_relaynet($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,1);

            $modifier_data = change_tags_for_message($buf_ptr,$relaynick,$relaynet,$modifier_data,1);
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # message from fox, wolf, hawk bot!
        elsif ( $line =~ m/^<([^\s]+)\>\s(.+)$/ )
        {
            my ($relaynick, $relaymsg) = ($1,$2);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,"");
            (undef,$relaymsg) = colorize_lines($modifier_data,$relaynick,$relaymsg);

            $string = create_string_without_relaynet($servername,$channelname,$relaynick,$nick_mode,$relaymsg);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,"",$modifier_data, "" );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # PRIVMSG #i2p :[Freenode/nickname] here is the message.
        elsif ( $line =~ m/^[\(\[`](.+?)\/(.+?)[\)\]`] (.+)$/ )
        {
            my ($relayserver,$relaynick,$relaymsg) = ($1,$2,$3);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,"");
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_string_without_relaynet($servername,$channelname,$relaynick,$nick_mode,$relaymsg);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,"",$modifier_data,"" );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # message from matrix-appservice-irc
        elsif ( $line =~ m/^\[\w\] <@([^>]+)> (.+)$/ )
        {
            my ($relaynick,$relaymsg) = ($1,$2);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,"");
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_string_without_relaynet($servername,$channelname,$relaynick,$nick_mode,$relaymsg);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,"",$modifier_data,"" );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # message from FLIP & Gitter
        elsif ( $line =~ m/^[\(\[`](.+?)[\)\]`] (.+)$/ )
        {
            my ($relaynick,$relaymsg) = ($1,$2);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,"");
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_string_without_relaynet($servername,$channelname,$relaynick,$nick_mode,$relaymsg);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,"",$modifier_data,"" );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # message from cloudc2sd
        # :u2!u@irc2p PRIVMSG #relaytest :/botname/nickname> here comes the message
        elsif ( $line =~ m/^([^\/]+)\/([^\>]+)\>\s(.+)$/ )
        {
            my ($relaynet,$relaynick,$relaymsg) = ($1,$2,$3);

            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return "";                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,$relaynet,0);
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_string_with_relaynet($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,0);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,$relaynet,$modifier_data,0 );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }

# =============== ACTION (/me) messages ===============
        # from gribble
        elsif ( $line =~ /\*\s(.+)@([^\s]+)\s(.+)/ )
        {
            my ($relaynick, $relaynet, $relaymsg) = ($1,$2,$3);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return '';                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,$relaynet,1);
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_action_string_with_relaynet($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,1);
            return "" if ( $string eq "");

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,$relaynet,$modifier_data,1 );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # from fox, wolf, hawk bot
        elsif ( $line =~ /\*\s([^\s]+)\s(.+)/ )
        {
            my ($relaynick, $relaymsg) = ($1,$2);
            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return "";                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,"");
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_action_string_without_relaynet($servername,$channelname,$relaynick,$nick_mode,$relaymsg);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,"",$modifier_data,"" );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }
        # from uuu
        #:u!u@public.chat.cloud PRIVMSG #relaytest :\0305/irc2p2/KillYourTV\0308\0308> \0F\01ACTION tests...again\01
        elsif ( $line =~ m/^\/(.+)\/(.+)>\sACTION\s(.*)/ )
        {
            my ($relaynet,$relaynick,$relaymsg) = ($1,$2,$3);

            if ( grep /^$servername.$relaynick$/, @blacklist )              # check for ignored relay nicks
            {
                return "";                                                  # delete message from ignored relaynick
            }
            my $nick_mode = "";
            ($relaynick,$nick_mode) = check_nick_mode($buf_ptr,$relaynick);
            add_relay_nick_to_nicklist($buf_ptr,$relaynick,$relaynet,0);
            (undef, $relaymsg) = colorize_lines($modifier_data,$relaynick, $relaymsg);

            $string = create_action_string_with_relaynet($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,0);

            $modifier_data = change_tags_for_message( $buf_ptr,$relaynick,$relaynet,$modifier_data,0 );
            weechat::print_date_tags($buf_ptr,0,$modifier_data,$string);
            return "";
        }

        # drop, decrease notification level, unchanged
        return "" if ( $option{unexpected_msg_handling} eq "drop");
    }     # end of BOT
    return $string;
}

# =============== create string to display in weechat ===============
sub create_string_without_relaynet
{
    my ($servername,$channelname,$relaynick,$nick_mode,$relaymsg) = @_;
    my $string;
    $relaymsg =~ s/^\s+//;                                              # kill leading space
    if ($relaymsg eq "")
    {
        $string = wrecked_msg($servername,$channelname,$relaynick,"","");
        return $string;
    }
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);# get nick-color
    $string = _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                    $nick_mode .
                    $nick_color .
                    $relaynick .
                    "\t" .
                    $relaymsg;
    return $string;
}

sub create_string_with_relaynet
{
    my ($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,$display_mode) = @_;
    my $string;
    $relaymsg =~ s/^\s+//;                                              # kill leading space
    if ($relaymsg eq "")
    {
        $string = wrecked_msg($servername,$channelname,$relaynick,$relaynet,$display_mode);
        return $string;
    }
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);# get nick-color

    if ( $option{suppress_relaynet} eq "on" and $option{suppress_relaynet_channels} eq "" or ( grep /^$servername.$channelname$/, @suppress_relaynet_channels) ){
        # suppress relaynet
        $string = _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                                $nick_mode .
                                $nick_color .
                                $relaynick .
                                "\t" .
                                $relaymsg;
    }else
    {
        # show relaynet
        my $relay_and_nick = relay_and_nick($relaynet,$relaynick,$display_mode);
        $string = _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                                $nick_mode .
                                $relay_and_nick.
                                "\t" .
                                $relaymsg;
    }
    return $string;
}

sub create_action_string_without_relaynet
{
    my ($servername,$channelname,$relaynick,$nick_mode,$relaymsg) = @_;
    my $string;
    $relaymsg =~ s/^\s+//;                                              # kill leading space
    if ($relaymsg eq "")
    {
        $string = wrecked_msg($servername,$channelname,$relaynick,"","");
        return $string;
    }
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);# get nick-color
    my $prefix_action = weechat::config_string(weechat::config_get("weechat.look.prefix_action"));
    my $prefix_color  = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_prefix_action")));
    $string = _color_str($prefix_color, $prefix_action) .
                $nick_mode .
                "\t" .
                _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                $nick_color .
                $relaynick .
                weechat::color("default") .
                " " .
                $relaymsg;
    return $string;
}

sub create_action_string_with_relaynet
{
    my ($servername,$channelname,$relaynick,$relaynet,$nick_mode,$relaymsg,$display_mode) = @_;
    my $string;
    $relaymsg =~ s/^\s+//;                                              # kill leading space
    if ($relaymsg eq "")
    {
        $string = wrecked_msg($servername,$channelname,$relaynick,$relaynet,$display_mode);
        return $string;
    }
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);
    my $prefix_action = weechat::config_string(weechat::config_get("weechat.look.prefix_action"));
    my $prefix_color  = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_prefix_action")));

    if ( $option{suppress_relaynet} eq "on" and $option{suppress_relaynet_channels} eq "" or ( grep /^$servername.$channelname$/, @suppress_relaynet_channels) )
    {
        $string = _color_str($prefix_color, $prefix_action) .
                    $nick_mode .
                    "\t" .
                    _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                    $nick_color .
                    $relaynick .
                    weechat::color("default") .
                    " " .
                    $relaymsg;
    }else
    {
        # show relaynet
        my $relay_and_nick = relay_and_nick($relaynet,$relaynick,$display_mode);
        $string = _color_str($prefix_color, $prefix_action) .
                    $nick_mode .
                    "\t" .
                    _color_str( $option{nick_mode_color}, $option{nick_mode} ) .
                    $relay_and_nick .
                    weechat::color("default") .
                    " " .
                    $relaymsg;
    }
    return $string;
}

sub wrecked_msg
{
    my ($servername,$channelname,$relaynick,$relaynet,$display_mode) = @_;
    return "" if ( $option{unexpected_msg_handling} eq "drop");
    my $string;
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);
    my $relay_and_nick;

    if (not defined $relaynet or $relaynet eq "")
    {
        $relay_and_nick = $nick_color . $relaynick;
    }else
    {
        if ( $option{suppress_relaynet} eq "off" )
        {
            $relay_and_nick = relay_and_nick($relaynet,$relaynick,$display_mode);
        }elsif ( $option{suppress_relaynet} eq "on" )
        {
            unless ( $option{suppress_relaynet_channels} eq "" or ( grep /^$servername.$channelname$/, @suppress_relaynet_channels) ){
                $relay_and_nick = relay_and_nick($relaynet,$relaynick,$display_mode);
            }else
            {
                return "";
            }
        }
    }

    my $prefix_error = weechat::config_string(weechat::config_get("weechat.look.prefix_error"));
    my $prefix_color  = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_prefix_error")));

    $string = _color_str($prefix_color, $prefix_error) .
                "\t" .
                "wrecked message from: ".
                $relay_and_nick;
    return $string;
}

sub relay_and_nick
{
    my ($relaynet,$relaynick,$display_mode) = @_;
    my $nick_color = weechat::info_get('irc_nick_color', $relaynick);
    my $relaynet_color;
    if ( $option{relaynet_color} eq "")
    {
        $relaynet_color = weechat::color(weechat::info_get('irc_nick_color_name', $relaynet));
    }else
    {
        $relaynet_color = weechat::color($option{relaynet_color});
    }
    my $relay_and_nick;

    if ($display_mode eq 0)
    {
        $relay_and_nick = $relaynet_color .
                    $relaynet .
                    weechat::color("default") .
                    "/".
                    $nick_color .
                    $relaynick;
    }elsif ($display_mode eq 1)
    {
        $relay_and_nick = $nick_color .
                    $relaynick .
                    weechat::color("default") .
                    "@" .
                    $relaynet_color .
                    $relaynet;
    }
    return $relay_and_nick;
}
# =============== check for a nick mode and extract it ===============
sub check_nick_mode
{
    my ($buf_ptr, $relaynick) = @_;
    $relaynick = weechat::string_remove_color($relaynick,"");                                   # remove color-codes from nick
    my $nick_mode = "";

    if ($relaynick  =~ m/^\@|^\%|^\+|^\~|^\*|^\&|^\!|^\-/)                                      # check for nick modes (@%+~*&!-) in nickname (without color)
    {
        $nick_mode = substr($relaynick,0,1);                                                    # get original nick_mode
        $relaynick = substr($relaynick,1,length($relaynick)-1);                                 # remove original nick-mode
    }
    return $relaynick,$nick_mode;
}
# =============== change message tags() ===============
sub change_tags_for_message
{
    my ( $buf_ptr,$relaynick, $relaynet, $modifier_data, $display_mode ) = @_;

    my $servername = weechat::buffer_get_string($buf_ptr,"localvar_server");
    my $channelname = weechat::buffer_get_string($buf_ptr,"localvar_channel");

    if (not defined $relaynet or $relaynet eq "")
    {
        $relaynick = $relaynick;
    }elsif ( $option{suppress_relaynet} eq "off" and $option{relaynet_to_nicklist} eq "on" )
    {
        $relaynick = $relaynick . "/" . $relaynet if ($display_mode eq 0);
        $relaynick = $relaynick . "@" . $relaynet if ($display_mode eq 1);
    }elsif ( $option{suppress_relaynet} eq "on" and $option{relaynet_to_nicklist} eq "on")
    {
        unless ( $option{suppress_relaynet_channels} eq "" or ( grep /^$servername.$channelname$/, @suppress_relaynet_channels) ){
            $relaynick = $relaynick . "/" . $relaynet if ($display_mode eq 0);
            $relaynick = $relaynick . "@" . $relaynet if ($display_mode eq 1);
        }
    }
    my $nick_color = weechat::info_get('irc_nick_color_name', $relaynick);
    if (($weechat_version ne "") && ($weechat_version >= 0x00030800))
    {
        $modifier_data =~ s/(^|,)prefix_nick_(.*),/,prefix_nick_$nick_color,nick_$relaynick,/;
    }
    else
    {
        $modifier_data =~ s/(^|,)nick_(.*),/nick_$relaynick,/;
    }
    return $modifier_data;
}

# =============== nicklist ===============
sub add_relay_nick_to_nicklist
{
    my ( $buf_ptr, $relaynick , $relaynet ,$display_mode ) = @_;
    return if ($buf_ptr eq "");
    return if ($relaynick eq "");
    my $current_time = time();
    # search for group.
    my $ptr_group = "";
    $ptr_group = weechat::nicklist_search_group($buf_ptr,"",$group_name);
    # create group if it does not exists.
    if ( $ptr_group eq "")
    {
        $ptr_group = weechat::nicklist_add_group($buf_ptr,"",$group_name,"weechat.color.nicklist_group",1);
    }
    return if ( $ptr_group eq "");

    my $servername = weechat::buffer_get_string($buf_ptr,"localvar_server");
    my $channelname = weechat::buffer_get_string($buf_ptr,"localvar_channel");

    if (not defined $relaynet or $relaynet eq ""){
        $relaynick = $relaynick;
    }elsif ( $option{suppress_relaynet} eq "off" and $option{relaynet_to_nicklist} eq "on" )
    {
        if (defined $display_mode and $display_mode eq 0)
        {
            $relaynick = $relaynick . "/" . $relaynet;
        }elsif (defined $display_mode and $display_mode eq 1)
        {
            $relaynick = $relaynick . "@" . $relaynet;
        }
    }elsif ( $option{suppress_relaynet} eq "on" and $option{relaynet_to_nicklist} eq "on")
    {
        unless ( $option{suppress_relaynet_channels} eq "" or ( grep /^$servername.$channelname$/, @suppress_relaynet_channels) )
        {
            if (defined $display_mode and $display_mode eq 0)
            {
                $relaynick = $relaynick . "/" . $relaynet;
            }elsif (defined $display_mode and $display_mode eq 1)
            {
               $relaynick = $relaynick . "@" . $relaynet;
            }
        }
    }

    $nick_timer{$buf_ptr.".".$relaynick} = $current_time;                                # set new timer
    # get nick color
    my $nick_color = weechat::info_get('irc_nick_color_name', $relaynick);
    # nick already exists in group?
    my $ptr_nick_gui = weechat::nicklist_search_nick($buf_ptr,$ptr_group,$relaynick);
    # add nick to nicklist, if my $group exists
    if ( $ptr_nick_gui eq "" )
    {
        my $test = weechat::string_remove_color( _color_str($option{nick_mode_color},$option{nick_mode}),"" );
        weechat::nicklist_add_nick($buf_ptr,$ptr_group,$relaynick,$nick_color,$test,$option{nick_mode_color},1);
#        weechat::nicklist_add_nick($buf_ptr,$ptr_group,$relaynick,$nick_color,$option{nick_mode},$option{nick_mode_color},1);
        weechat::nicklist_nick_set($buf_ptr,$ptr_nick_gui,"prefix",$option{nick_mode});
        weechat::nicklist_nick_set($buf_ptr,$ptr_nick_gui,"prefix_color",$option{nick_mode_color});
    }
}

# check out every x minutes if nick is not too old
sub check_own_nicklist
{
    my ($data, $signal, $signal_data) = @_;
    my $current_time = time();
    my $timer = $option{"timer"};
    while (my ($name, $time) = each %nick_timer)
    {
        if ( $current_time - $time >= $timer )
        {
            # delete nick from %hash and from nicklist
            my ($buf_ptr, $relaynick) = split( /\./, $name );
            my $ptr_group = weechat::nicklist_search_group($buf_ptr,"",$group_name);
            next if ( $ptr_group eq "" );
            my $ptr_nick_gui = weechat::nicklist_search_nick($buf_ptr, $ptr_group, $relaynick);
            if ( $ptr_nick_gui ne "" )
            {
                weechat::nicklist_remove_nick($buf_ptr,$ptr_nick_gui);
                delete $nick_timer{$name};
            }
        }
    }
}
sub _color_str
{
    my ($color_name, $string) = @_;
    # use eval for colors-codes (${color:red} eg in weechat.look.prefix_error)
    $string = weechat::string_eval_expression($string, {}, {},{}) if ($weechat_version >= 0x00040200);
    return weechat::color($color_name) . $string  . weechat::color('reset');
}

# =============== config ===============
sub init_config
{
    foreach my $opt (keys %option)
    {
        if (!weechat::config_is_set_plugin($opt))
        {
            weechat::config_set_plugin($opt, $option{$opt});
        }else
        {
            $option{$opt} = weechat::config_get_plugin($opt);
        }
    }
    
    @bot_nicks = split( /,/, $option{supported_bot_names} );                                # read bot names
    @message_kinds = split( /,/, $option{supported_message_kinds} );                        # read supported_message_kinds
    @list_of_server = split( /,/, $option{servername} );                                    # read server
    @suppress_relaynet_channels = split( /,/, $option{suppress_relaynet_channels} );        # read channels
    @blacklist = split( /,/, $option{blacklist} );                                          # read blacklist of relay nicks
    
    if (($weechat_version ne "") && ($weechat_version >= 0x00030500))
    {
        foreach my $option ( keys %script_desc )
        {
            weechat::config_set_desc_plugin( $option,$script_desc{$option} );
        }

    }
}
# =============== hooks() and shutdown ===============
sub toggle_config_by_set
{
    my ( $pointer, $name, $value ) = @_;
    $name = substr($name,length("plugins.var.perl.".$SCRIPT_NAME."."),length($name));           # don't forget the "."
    $option{$name} = $value;

    if ( $name eq "supported_bot_names" )
    {
        @bot_nicks = "";
        @bot_nicks = split( /,/, $option{supported_bot_names} );
    }
    if ( $name eq "supported_message_kinds" )
    {
        @message_kinds = "";
        @message_kinds = split( /,/, $option{supported_message_kinds} );
    }
    if ( $name eq "servername" )
    {
        @list_of_server = "";
        @list_of_server = split( /,/, $option{servername} );
    }
    if ( $name eq "suppress_relaynet_channels" )
    {
        @suppress_relaynet_channels = "";
        @suppress_relaynet_channels = split( /,/, $option{suppress_relaynet_channels} );
    }
    if ( $name eq "timer" )
    {
        hook_timer($value);
    }
    if ( $name eq "debug" )
    {
        hook_debug($value);
    }
    return weechat::WEECHAT_RC_OK;
}

sub hook_timer
{
    my $value = $_[0];
    if ( $value eq 0 )
    {
        weechat::unhook($Hooks{timer}) if $Hooks{timer};
        $Hooks{timer} = "";
    }
    else
    {
        weechat::unhook($Hooks{timer}) if $Hooks{timer};
        $Hooks{timer} = weechat::hook_timer( $value * 1000, 60, 0, "check_own_nicklist", "");
    }
    return weechat::WEECHAT_RC_OK;
}

sub hook_debug
{
    my $value = $_[0];
    if ( lc($value) eq "off" or $value eq "")
    {
        weechat::unhook($Hooks{debug}) if $Hooks{debug};
        $Hooks{debug} = "";
    }else
    {
        weechat::unhook($Hooks{debug}) if $Hooks{debug};
        my ($server, $nick) = split(/\:/,$option{"debug"});
        $Hooks{debug} = weechat::hook_signal( $server . ",irc_raw_in_PRIVMSG","debug_cb","") if (defined $server and $server ne "");
    }
    return weechat::WEECHAT_RC_OK;
}

sub buffer_closing
{
    my ($signal, $callback, $callback_data) = @_;

    while (my ($name, $time) = each %nick_timer)
    {
        my ($buf_ptr, $relaynick) = split( /\./, $name );
        my $ptr_group = weechat::nicklist_search_group($buf_ptr,"",$group_name);
        # remove nicks before closing buffer
        delete $nick_timer{$name} if ($buf_ptr eq $callback_data);
        if ($buf_ptr eq $callback_data and $ptr_group ne "")
        {
            weechat::nicklist_remove_group($buf_ptr,$ptr_group);
        }
    }
    return weechat::WEECHAT_RC_OK;
}

# shutting down script will remove the relay nicks from nicklist
sub shutdown
{
    while (my ($name, $time) = each %nick_timer)
    {
        my ($buf_ptr, $relaynick) = split( /\./, $name );
        my $ptr_group = weechat::nicklist_search_group($buf_ptr,"",$group_name);
        next if ( $ptr_group eq "" );

        my $ptr_nick_gui = weechat::nicklist_search_nick($buf_ptr, $ptr_group, $relaynick);
        weechat::nicklist_remove_nick($buf_ptr,$ptr_nick_gui);
    }
return weechat::WEECHAT_RC_OK;
}

sub should_handle_modifier
{
    my ($modifier_data) = @_;

    foreach ( @message_kinds ){
        my $message_kind = weechat::string_mask_to_regex($_);
        if (index( $modifier_data,$message_kind ) != -1)
        {
            return 1;
        }
    }

    return 0;
}

# ========= string_mask_to_regex() =========
sub string_mask_to_regex
{
    my ($nick) = @_;
    foreach ( @bot_nicks ){
        my $bot_nick = weechat::string_mask_to_regex($_);
        if ($nick =~ /^$bot_nick$/i)
        {
            return 1;
        }
    }
    return 0;
}

# ========= colorize_lines =========
sub colorize_lines
{
    my ( $modifier_data, $nick, $string ) = @_;
    # change nick name in modifier_data! Take care of tag "prefix_nick_ccc"
    if (($weechat_version ne "") && ($weechat_version >= 0x00030800))
    {
        $modifier_data =~ s/(^|,)nick_(.*),/,nick_$nick,/;
    }
    else
    {
        $modifier_data =~ s/(^|,)nick_(.*),/nick_$nick,/;
    }

    my $infolist = weechat::infolist_get("perl_script","","colorize_lines");
    weechat::infolist_next($infolist);

    if ( "colorize_lines" eq weechat::infolist_string($infolist,"name") )
    {
        $string =  weechat::hook_modifier_exec( "colorize_lines",$modifier_data,"$nick\t$string");
        if ($string ne "")
        {
            $string =~ m/^(.*)\t(.*)/;                                                                   # get the nick name: nick[tab]string
            $nick = $1;                                                                                  # nick
            $string = $2;                                                                                # message
        }
#        my @array = "";
#        my $color_code_reset = weechat::color('reset');
#        @array=split(/$color_code_reset/,$line);
#        my $new_line = "";
#        foreach (@array){
#          $new_line .=  $nick_color . $_ . weechat::color('reset');
#        }
#        $new_line =~ s/\s+$//g;                                                                 # remove space at end
#        $line = $new_line;
    }
    weechat::infolist_free($infolist);
    return ($nick,$string);
}

sub debug_cb
{
    my ($signal, $callback, $callback_data) = @_;
    # "nick": nick
    # "host": host
    # "command": command
    # "channel": channel
    # "arguments": arguments (includes channel)
    if (($weechat_version eq "") or ($weechat_version < 0x00030400))
    {
        weechat::print("",weechat::prefix("error").
                          "$SCRIPT_NAME: Debug mode needs WeeChat >= 0.3.4");
        return weechat::WEECHAT_RC_OK;
    }

    my $hashtable = weechat::info_get_hashtable("irc_message_parse" => + { "message" => $callback_data });
    my ($server, $nick) = split(/\:/,$option{"debug"});
    my @split = split(/\,/,$callback);
    if (defined $server and $server eq $split[0]){
        if ( not defined $nick or $nick eq ""){
            weechat::print("","raw message: $callback_data");
        }elsif ($nick eq $hashtable->{nick}){
            weechat::print("","raw message: $callback_data");
        }
    }
    return weechat::WEECHAT_RC_OK;
}
# ========= main =========
    weechat::register($SCRIPT_NAME, $SCRIPT_AUTHOR, $SCRIPT_VERSION,
                  $SCRIPT_LICENCE, $SCRIPT_DESCR, "shutdown", "") || return;
    $weechat_version = weechat::info_get("version_number", "");

    init_config();

    weechat::hook_config( "plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "" );
    weechat::hook_signal("buffer_closing", "buffer_closing", "");

    if (($weechat_version ne "") && ($weechat_version >= 0x00030400)){                          # v0.3.4
        weechat::hook_modifier("500|weechat_print","parse_relayed_msg_cb", "");                  # use lower prio (standard: 1000)
    }
    else
    {
        weechat::hook_modifier("weechat_print","parse_relayed_msg_cb", "");
    }

    $Hooks{timer} = weechat::hook_timer( $option{"timer"} * 1000, 60, 0, "check_own_nicklist", "");
