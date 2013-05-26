#
# Copyright (c) 2013 by Nils Görs <weechatter@arcor.de>
# based on irssi script stalker.pl from Kaitlyn Parkhurst (SymKat) <symkat@symkat.com>
# https://github.com/symkat/Stalker
#
# Records and correlates nick!user@host information
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
# History:
# version 0.5: nils_2@freenode.#weechat
# 2013-05-26: add: function 'count'
#
# version 0.4: nils_2@freenode.#weechat
# 2013-05-18: add: option 'tags'
#
# version 0.3: nils_2@freenode.#weechat
# 2013-05-05: fix: typos in help and description option (thanks FiXato)
#             add: 'ChanServ' to option 'guest_nick_regex'
#
# version 0.2: nils_2@freenode.#weechat
# 2013-05-01: fix: bug with regular expressions using /whois
#             removed: option 'allow_regex_for_search'
#             add: command option '-regex'
#
# version 0.1: nils_2@freenode.#weechat
# 2013-04-23: - initial release -
#
# thanks to firebird and mave_ for testing...
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# Requires:
#   DBI
#   DBD::SQLite
#
# How to install DBI:
# with cpan       : install DBI
# with deb-package: sudo apt-get install libdbi-perl
#
# How to install DBD::SQLite:
# with cpan       : install DBD::SQLite
# with deb-package: sudo apt-get install libdbd-sqlite3-perl libdbd-sqlite3

#use strict;
use warnings;
use File::Spec;
use DBI;

my $SCRIPT_NAME         = "stalker";
my $SCRIPT_VERSION      = "0.5";
my $SCRIPT_AUTHOR       = "Nils Görs <weechatter\@arcor.de>";
my $SCRIPT_LICENCE      = "GPL3";
my $SCRIPT_DESC         = "Records and correlates nick!user\@host information";


# internal values
my $weechat_version = "";

# default values
my %options = ('db_name'                => '%h/nicks.db',
               'debug'                  => 'off',
               'max_recursion'          => '20',
               'recursive_search'       => 'on',
               'ignore_guest_hosts'     => 'off',
               'ignore_guest_nicks'     => 'on',
               'guest_nick_regex'       => '^(guest|weebot|Floodbot|ChanServ).*',
               'guest_host_regex'       => '^webchat',
               'normalize_nicks'        => 'on',
               'search_this_network_only' => 'on',
               'use_localvar'           => 'off',
               'ignore_nickchange'      => 'off',
               'ignore_whois'           => 'off',
               'tags'                   => '',
#               '' => '',
);
my %desc_options = ('db_name'           => 'file containing the SQLite database where information is recorded. This database is created on loading of ' . $SCRIPT_NAME . ' if it does not exist. ("%h" will be replaced by WeeChat home, "~/.weechat" by default) (default: %h/nicks.db)',
                    'debug'             => 'Prints debug output to core buffer so you know exactly what is going on. This is far too verbose to be enabled when not actively debugging something. (default: off)',
                    'max_recursion'     => 'For each correlation between nick <-> host that happens, one point of recursion happens. A corrupt database, general evilness, or misfortune can cause the recursion to skyrocket. This is a ceiling number that says if after this many correlation attempts we have not found all nickname and hostname correlations, stop the process and return the list to this point.',
                    'recursive_search'  => 'When enabled, recursive search causes stalker to function better than a simple hostname to nickname map. Disabling the recursive search in effect turns stalker into a more standard hostname -> nickname map.',
                    'ignore_guest_hosts'=> 'See option guest_host_regex',
                    'guest_host_regex' => 'regex mask to ignore host masks',
                    'ignore_guest_nicks'=> 'See option guest_nick_regex',
                    'guest_nick_regex'  => 'Some networks set default nicknames when a user fails to identify to nickserv, other networks using relay-bots, some irc clients set default nicknames when someone connects and often these change from network to network depending on who is configuring the java irc clients. This allows a regular expression to be entered. When a nickname matches the regular expression and "ignore_guest_nicks" is enabled the nickname is dropped from the search as if it had never been seen. (default: ^(guest|weebot|Floodbot).*)',
                    'normalize_nicks' => 'this option will truncate special chars from username (like: ~) (default: on)',
                    'search_this_network_only' => 'When enabled searches are limited to within the network the window is currently set on. Turning this off is really only useful if multiple networks don\'t encode the hostmask. (default: on)',
                    'use_localvar'      => 'When enabled, only channels with a localvar \'stalker\' will be monitored. This option will not affect /NICK and /WHOIS monitoring. It\'s only for /JOIN messages. (default: off)',
                    'ignore_nickchange' => 'When enabled, /NICK changes won\'t be monitored. (default: off)',
                    'ignore_whois'      => 'When enabled, /WHOIS won\'t be monitored. (default: off)',
                    'tags'              => 'comma separated list of tags used in messages printed by stalker. See documentation for possible tags (e.g. \'no_log\', \'no_highlight\'). Debug messages will ignore this option.',
);

my $count;
my %data;
my $str;
my $DBH;
my $DBH_child;
my $hook_process = 0;
my $last_nick = "";
my $last_host = "";

# -----------------------------[ Database ]-----------------------------------
sub open_database {
    my $db = weechat_dir();

    stat_database( $db );
    my ($db_user, $db_pass);
    # my $db_host = '127.0.0.1';
    # my $db_port = 3306;

    $DBH = DBI->connect(
        'dbi:SQLite:dbname='.$db, $db_user, $db_pass,
        {
            RaiseError => 1,
#            AutoCommit => 1,
            sqlite_use_immediate_transaction => 1,
        }
    );

    # DBI::SQLite and fork() don't mix. Do it anyhow but keep the parent and child DBH separate?
    # Ideally the child should open its own connection.
    $DBH_child = DBI->connect(
        'dbi:SQLite:dbname='.$db, $db_user, $db_pass,
        {
            RaiseError => 1,
#            AutoCommit => 1,
            sqlite_use_immediate_transaction => 1,
        }
    );

    # async data
    my @records_to_add; # Queue of records to add
}


# Automatic Database Creation And Checking
sub stat_database {
    my ( $db_file ) = @_;
    my $do = 0;

    DEBUG('info', 'Stat database');
    if ( ! -e $db_file  ) {
        open my $fh, '>', $db_file
            or die 'Cannot create database file.  Abort.';
        close $fh;
        $do = 1;
    }
    my $DBH = DBI->connect(
        'dbi:SQLite:dbname='.$db_file, "", "",
        {
            RaiseError => 1,
#            AutoCommit => 1,
            sqlite_use_immediate_transaction => 1,
        }
    );

    create_database( $DBH ) if $do;

    my $sth = $DBH->prepare( "SELECT nick from records WHERE serv = ?" );
    $sth->execute( 'script-test-string' );
    my $sane = $sth->fetchrow_array;

    create_database( $DBH ) if ($sane eq '');

    # Magical testing for the new "added" column; this column was added later
    # Need to test for its existance and "add" it if missing
    $sth = $DBH->prepare( "SELECT * FROM records WHERE serv = ?;" );
    $sth->execute( 'script-test-string' );
    my @arr = $sth->fetchrow_array; # I can't convert to a row count without storing in an array first
    if( scalar(@arr) == 4 ) { # 4 columns is the old format
        DEBUG("info", "Add timestamp column to existing database.");
        add_timestamp_column($DBH);
    }
    elsif( scalar(@arr) != 5 ) { # 5 is the new. Anything else is ... wrong
        die "The DB should have 4 or 5 columns. Found " . scalar(@arr);
    }

    index_db( $DBH );
}

sub create_database {
    my ( $DBH ) = @_;

    my @queries = (
        "DROP TABLE IF EXISTS records",
        "CREATE TABLE records (nick TEXT NOT NULL," .
            "user TEXT NOT NULL, host TEXT NOT NULL, serv TEXT NOT NULL, " .
            "added DATE NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "INSERT INTO records (nick, user, host, serv) VALUES( 1, 1, 1, 'script-test-string' )"
    );

    # Drop table is exists
    # Create the table and indices
    # Insert test record
    for my $query (@queries) {
        my $sth = $DBH->prepare($query) or die "Failed to prepare '$query'. " . $sth->err;
        $sth->execute() or die "Failed to execute '$query'. " . $sth->err;
    }
    index_db( $DBH );
}

# Add indices to the DB. If they already exist, no harm done.
# Is there an easy way to test if they exist already?
sub index_db {
    my ( $DBH ) = @_;

    my @queries = (
        "CREATE INDEX index1 ON records (nick)",
        "CREATE INDEX index2 ON records (host)",
    );
    $DBH->{RaiseError} = 0;
    $DBH->{PrintError} = 0;
    for my $query (@queries) {
        $DBH->do( $query );
    }
    $DBH->{RaiseError} = 1;
    $DBH->{PrintError} = 1;
}

# Create a new table with the extra column, move the data over. delete old table and alter name
sub add_timestamp_column {
    my ( $DBH ) = @_;

    weechat::print("","Adding a timestamp column to the nicks db. Please wait...");

    # Save the old records
    $DBH->do( "ALTER TABLE records RENAME TO old_records" );

    # Create the new table
    create_database( $DBH );

    # Copy the old records over and drop them
    my @queries = (
        "INSERT INTO records (nick,user,host,serv) SELECT nick,user,host,serv FROM old_records",
        "DROP TABLE old_records",
    );
    for my $query (@queries) {
        my $sth = $DBH->prepare($query) or die "Failed to prepare '$query'. " . $sth->err;
        $sth->execute() or die "Failed to execute '$query'. " . $sth->err;
    }
}

sub normalize {
    my ( @nicks ) = @_;
    my ( %nicks, %ret ) = map { $_, 1 } @nicks;

    for my $nick ( @nicks ) {
        (my $base = $nick ) =~ s/[\Q-_~^`\E]//g;
        $ret{ exists $nicks{$base} ? $base : $nick }++;
    }
    return keys %ret;
}

sub add_record
{
    my ( $nick, $user, $host, $serv ) = @_;
    return unless ($nick and $user and $host and $serv);

    DEBUG("info", "Start child process, to add record to database");

    my ($command) = db_add_record($nick, $user, $host, $serv);

    if ($hook_process)
    {
        $hook_process = weechat::hook_process($command, 1000 * 1, "my_hook_process_cb", "");
    }else
    {
        $hook_process = 0;
    }
}

sub db_add_record
{
    my ($nick, $user, $host, $serv) = @_;

    # Check if we already have this record.
    my $q = "SELECT nick FROM records WHERE nick = ? AND user = ? AND host = ? AND serv = ?";
    my $sth = $DBH_child->prepare( $q );
    $sth->execute( $nick, $user, $host, $serv );
    my $result = $sth->fetchrow_hashref;

    if ( defined $result->{nick} )
    {
        if ( $result->{nick} eq $nick ) {
            DEBUG( "info", "Record for $nick skipped - already exists." );
            return 1;
        }
    }

    DEBUG("info", "Adding to DB: nick = $nick, user = $user, host = $host, serv = $serv" );

    # We don't have the record, add it.
    $sth = $DBH_child->prepare
        ("INSERT INTO records (nick,user,host,serv) VALUES( ?, ?, ?, ? )" );
    eval { $sth->execute( $nick, $user, $host, $serv ) };
    if ($@) {
        DEBUG("error", "Failed to process record, database said: $@" );
    }

    DEBUG("info", "Added record for $nick!$user\@$host to $serv" );
    return 0;
}

# function called when data from child is available, or when child has ended, arguments and return value
sub my_hook_process_cb
{
    my ( $data, $command, $return_code, $out, $err ) = @_;
    $hook_process = 0;
    return weechat::WEECHAT_RC_OK;
}

sub get_host_records {
    # suppress output? yes|no
    # type = host|nick, $query = name, $serv = server, @return = "."
    my ( $suppress, $type, $query, $serv, @return ) = @_;

    $count = 0; %data = (  );
    my %data = _r_search( $suppress, $serv, $type, $query );
    for my $k ( keys %data ) {
        DEBUG( "info", "$type query for records on $query from server $serv returned: $k" );
        push @return, $k if $data{$k} eq 'host';
    }

    # case-insensitive sort
    return sort {uc($a) cmp uc($b)} @return;
}

sub get_nick_records
{
    # type = host|nick, $query = nick, $serv = server, use_regex = 0|1, @return = "."
    my ( $suppress, $type, $query, $serv, $use_regex, @return ) = @_;

    $count = 0; %data = (  );
    my %data = _r_search( $suppress, $serv, $type, $use_regex, $query );
    for my $k ( keys %data ) {
        DEBUG( "info", "$type query for database records on $query from server $serv. returned: $k" );
        push @return, $k if $data{$k} eq 'nick';
    }

    if (lc($options{'normalize_nicks'}) eq "on" ) {
        @return = normalize(@return);
    }

    # case-insensitive sort
    return sort {uc($a) cmp uc($b)} @return;
}

sub _r_search {
    my ( $suppress, $serv, $type, $use_regex, @input ) = @_;

    return %data if $count > 1000;
    return %data if $count > $options{'max_recursion'};
    return %data if $count == 2 and ! $options{'recursive_search'};

    DEBUG( "info", "Recursion Level: $count" );

    if ( $type eq 'nick' ) {
        $count++;
        for my $nick ( @input ) {
            next if exists $data{$nick};

            $data{$nick} = 'nick';
            my @hosts = _get_hosts_from_nick( $nick, $serv, $use_regex );
            # use regex only for nick search!
            $use_regex = 0 if ( $use_regex );
            _r_search( $suppress, $serv, 'host', $use_regex, @hosts );
        }
    } elsif ( $type eq 'host' ) {
        $count++;
        for my $host ( @input ) {
            next if exists $data{$host};
            $data{$host} = 'host';
            my @nicks = _get_nicks_from_host( $host, $serv, $use_regex );
            my $a = @nicks;
            next if ($a <= 0);

            my $ptr_buffer = weechat::current_buffer();

            my $output = weechat::color('chat_prefix_network').
                         weechat::prefix('network').
                         weechat::color('chat_delimiters').
                         "[".
                         weechat::color('chat_nick').
                         $SCRIPT_NAME.
                         weechat::color('chat_delimiters').
                         "] ".
                         weechat::color('reset').
                         "Found nicks: ".
                         join( " , ", @nicks ).
                         " from host $host";

            if ( $options{'tags'} ne '' )
            {
                weechat::print_date_tags($ptr_buffer,0,$options{'tags'},$output) if ($suppress eq 'no');
            }
            else
            {
                weechat::print($ptr_buffer,$output) if ($suppress eq 'no');
            }

            # use regex only for host search!
            $use_regex = 0 if ( $use_regex );
            _r_search( $suppress, $serv, 'nick', $use_regex, @nicks );
        }
    }
    return %data;
}

sub _get_hosts_from_nick {
    my ( $nick, $serv, $use_regex, @return ) = @_;

    my $sth;

    if ( lc($options{'search_this_network_only'}) eq "on" )
    {
        if ( $use_regex )
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE nick REGEXP ? AND serv = ?" );
            $sth->execute( $nick, $serv );
        }
        else
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE nick = ? AND serv = ?" );
            $sth->execute( $nick, $serv );
        }
    }
    else
    {
        if ( $use_regex )
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE nick REGEXP ?");
        }
        else
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE nick = ?" );
        }
        $sth->execute( $nick );
    }
    # nothing found in database
#    return '' if (not defined $sth->fetchrow_hashref);
    return _ignore_guests( 'host', $sth );
}

sub _get_nicks_from_host {
    my ( $host, $serv, $use_regex, @return ) = @_;

    my $sth;
    if ( lc($options{'search_this_network_only'}) eq "on" )
    {
        if ( $use_regex )
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE host REGEXP ? AND serv = ?" );
            $sth->execute( $host, $serv );
        }
        else
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE host = ? AND serv = ?" );
            $sth->execute( $host, $serv );
        }
    }
    else
    {
        if ( $use_regex )
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE host REGEXP ?" );
        }
        else
        {
            $sth = $DBH->prepare( "SELECT nick, host FROM records WHERE host = ?" );
        }
        $sth->execute( $host );
    }
    # nothing found in database
#    return '' if (not defined $sth->fetchrow_hashref);
    return _ignore_guests( 'nick', $sth );
}

sub _ignore_guests {
    my ( $field, $sth ) = @_;
    my @return;

    while ( my $row = $sth->fetchrow_hashref ) {
        if ( lc($options{'ignore_guest_nicks'}) eq "on" ) {
            my $regex = $options{'guest_nick_regex'};
            next if( $row->{nick} =~ m/$regex/i );
        }
        if ( lc($options{'ignore_guest_hosts'}) eq "on" ) {
            my $regex = $options{'guest_host_regex'};
            next if( $row->{host} =~ m/$regex/i );
        }
        push @return, $row->{$field};
    }
    return @return;
}
# -----------------------------[ debug ]-----------------------------------
sub DEBUG {
    my $DEBUG_prefix;
    my $color;

    if ( $_[0] eq 'info')
    {
        $DEBUG_prefix = 'info';
        $color = "default";
    }
    elsif ( $_[0] eq 'error')
    {
        $DEBUG_prefix = weechat::config_string(weechat::config_get("weechat.look.prefix_error"));
        $color  = weechat::color(weechat::config_color(weechat::config_get("weechat.color.chat_prefix_error")));
    }
    else
    {
        $DEBUG_prefix = '***';
        $color = 'default';
    }
        weechat::print('', _color_str($color, $DEBUG_prefix) . "\t$SCRIPT_NAME: $_[1]") if (lc($options{debug}) eq 'on');
}

sub _color_str {
    my ($color_name, $string) = @_;
    weechat::color($color_name) . $string  . weechat::color('reset');
}
# -------------------------------[ subroutines ]-------------------------------------
sub weechat_dir
{
    my $dir = $options{'db_name'};
    if ( $dir =~ /%h/ )
    {
        my $weechat_dir = weechat::info_get( 'weechat_dir', '');
        $dir =~ s/%h/$weechat_dir/;
    }
    return $dir;
}
# -------------------------------[ main ]-------------------------------------
sub stalker_command_cb
{
    my ($data, $buffer, $args) = ($_[0], $_[1], $_[2]);
    my @args_array=split(/ /,$args);
    my $number = @args_array;

    return weechat::WEECHAT_RC_OK if ($number <= 0);

    if (lc($args_array[0]) eq 'count')
    {
        my $ptr_buffer = weechat::current_buffer();
        my ($count) = $DBH->selectrow_array("SELECT count(*) FROM records");
        my $output = weechat::color('chat_prefix_network').
                     weechat::prefix('network').
                     weechat::color('chat_delimiters').
                     "[".
                     weechat::color('chat_nick').
                     $SCRIPT_NAME.
                     weechat::color('chat_delimiters').
                     "] ".
                     weechat::color('reset').
                     "number of rows: ".
                     $count;

        if ( $options{'tags'} ne '' )
        {
            weechat::print_date_tags($ptr_buffer,0,$options{'tags'},$output);
        }
        else
        {
            weechat::print($ptr_buffer,$output);
        }
        return weechat::WEECHAT_RC_OK;
    }
    # get localvar from current buffer
    my $name = weechat::buffer_get_string(weechat::current_buffer(),'localvar_name');
    my $server = weechat::buffer_get_string(weechat::current_buffer(),'localvar_server');
    my $type = weechat::buffer_get_string(weechat::current_buffer(),'localvar_type');

    if ( weechat::buffer_get_string(weechat::current_buffer(),'plugin') ne 'irc' and lc($args_array[0]) eq 'scan' )
    {
        my $text = 'command must be executed on irc buffer (server or channel)';
        my $color  = weechat::color(weechat::config_color(weechat::config_get('weechat.color.chat_prefix_error')));
        my $DEBUG_prefix = weechat::config_string(weechat::config_get('weechat.look.prefix_error'));
        weechat::print('', _color_str($color, $DEBUG_prefix) . "\t$SCRIPT_NAME: $text");
        return weechat::WEECHAT_RC_OK;
    }

    if (lc($args_array[0]) eq 'scan' && $type eq 'channel' && $number == 1)
    {
        channel_scan(weechat::current_buffer());
#        channel_scan_41(weechat::current_buffer());
        return weechat::WEECHAT_RC_OK;
    }

    # at least, we have two arguments
    return weechat::WEECHAT_RC_OK if ($number <= 1);

    my $use_regex = 0;

    if (lc($args_array[0]) eq 'scan' && $args_array[1] ne "")
    {
        $args_array[1] =~ s/\./,/;                      # info_get() needs an "," instead of "."
        my $ptr_buffer = weechat::info_get('irc_buffer',$args_array[1]);
#        channel_scan_41($ptr_buffer) if ( $ptr_buffer ne "");
        channel_scan($ptr_buffer) if ( $ptr_buffer ne "");
    }
    elsif (lc($args_array[0]) eq 'nick' or lc($args_array[0]) eq 'host')
    {
        if ( defined $args_array[2] and $args_array[2] eq "-regex" )
        {
            $use_regex = 1;
        }
        else
        {
            $server = $args_array[2] if ( defined $args_array[2] and $args_array[2] ne "" );
        }

        if ( defined $args_array[3] and $args_array[3] eq "-regex" )
        {
            $use_regex = 1;
        }

        if ( $server eq "" )
        {
            my $text = 'command must be executed on irc buffer (server or channel) or a server must be given';
            my $color  = weechat::color(weechat::config_color(weechat::config_get('weechat.color.chat_prefix_error')));
            my $DEBUG_prefix = weechat::config_string(weechat::config_get('weechat.look.prefix_error'));
            weechat::print('', _color_str($color, $DEBUG_prefix) . "\t$SCRIPT_NAME: $text");
            return weechat::WEECHAT_RC_OK;
        }
        # $args_array[0]: 'nick' or 'host', $args_array[1]: nick or host name
        my $nicks_found = join( ", ", (get_nick_records('no', $args_array[0], $args_array[1], $server, $use_regex)));
    }
    return weechat::WEECHAT_RC_OK;
}

# hdata_search()
# hdata: hdata pointer
# pointer: pointer to a WeeChat/plugin object
# search: expression to evaluate, default pointer in expression is the name of hdata (and this pointer changes for each element in list); for help on expression, see command /eval in WeeChat User’s guide
# move: number of jump(s) to execute after unsuccessful search (negative or positive integer, different from 0)

sub channel_scan_41
{
    my $ptr_buffer = $_[0];

    my $server_name = weechat::buffer_get_string($ptr_buffer, "localvar_server");
    my $channel_name = weechat::buffer_get_string($ptr_buffer, "localvar_channel");
    return if ($server_name eq "" or $channel_name eq "");

#my %hdata = { map { $_ => weechat::hdata_get( "irc_" . $_ ) } qw( server channel nick ) };
    my $hdata_server = weechat::hdata_get("irc_server");
    my $hdata_channel = weechat::hdata_get("irc_channel");
    my $hdata_nick = weechat::hdata_get("irc_nick");

    my $ptr_server = weechat::hdata_search($hdata_server, weechat::hdata_get_list($hdata_server, 'irc_servers'), '${irc_server.name} == ' . $server_name, 1);
    if ($ptr_server)
    {
        my $ptr_channel = weechat::hdata_search($hdata_channel, weechat::hdata_pointer($hdata_server, $ptr_server, 'channels'), '${irc_channel.name} == ' . $channel_name, 1);

        if ($ptr_channel)
        {
            my $nick = weechat::hdata_pointer($hdata_channel, $ptr_channel, 'nicks');
            while ( $nick )
            {
                my $nick_name = weechat::hdata_string($hdata_nick, $nick, 'name');
                my $host_name = weechat::hdata_string($hdata_nick, $nick, 'host');
                $host_name =~ /(.*)\@/;
                my $user_name = $1;

                add_record( $nick_name, $user_name, $host_name, $server_name);

                $nick = weechat::hdata_move($hdata_nick, $nick, 1);
            }
        }

    }
#    weechat::print("",$ptr_buffer);
#    weechat::print("",$server_name);

#    if ($ptr_servers)
#    {
#        my $channel = weechat::hdata_search(hdata['channel'], weechat.hdata_pointer(hdata['server'], server, 'channels'), '${irc_channel.name} == #test', 1)
#    }
}
sub channel_scan
{
    my $ptr_buffer = $_[0];
    my $infolist = weechat::infolist_get('nicklist', $ptr_buffer, '');
    # don't stalk yourself
    my $my_nick = weechat::buffer_get_string($ptr_buffer,'localvar_nick');

    my $nick_counter;

    while (weechat::infolist_next($infolist))
    {
        my $nick = weechat::infolist_string($infolist, 'name');
        if ((weechat::infolist_string($infolist, 'type') eq 'nick')
            && ($nick ne $my_nick))
        {
            my $ptr_nick = weechat::nicklist_search_nick($ptr_buffer, '', $nick);
            my $localvar_server = weechat::buffer_get_string($ptr_buffer,'localvar_server');
            my $localvar_channel = weechat::buffer_get_string($ptr_buffer,'localvar_channel');

            my $infolist_nick = weechat::infolist_get('irc_nick','',$localvar_server.','.$localvar_channel.','.$nick);
            weechat::infolist_next($infolist_nick);
            my $host = weechat::infolist_string($infolist_nick,'host');
            weechat::infolist_free($infolist_nick);

            next unless ($nick or $host or $localvar_server);
            $host =~ /(.*)\@/;
            $user = $1;

            add_record( $nick, $user, $host, $localvar_server);

#            $user=~ s/[\Q-_~^`\E]//g;
#            my $hdata = weechat::hdata_get("irc_nick");
#            my $hdata_host = weechat::hdata_string($hdata, $ptr_nick, "host");
#            next if ($host eq $name);

        }
    }
    weechat::infolist_free($infolist);
}

# simple check for last nick/host
# to prevent multiple requests (e.g. "/nick|join nick" for several channels!)
# 0 = failed
# 1 = found
sub check_last_nick_host
{
    my ($nick,$host) = @_;
    my $rc = 0;

    $rc = 1 if ($nick eq $last_nick && $host eq $last_host);

    $last_nick = $nick;
    $last_host = $host;
#    weechat::print("","nick: $nick   rc: $rc");
    return $rc;
}
# -------------------------------[ hooks ]-------------------------------------
# :old_nick!~user@host NICK :new_nick
# /NICK command called
# this is a server command
sub irc_in2_nick_cb
{
    my ($signal, $callback, $callback_data) = @_;
    my ($server,undef) = split(',',$callback);

    return weechat::WEECHAT_RC_OK if ( lc($options{'ignore_nickchange'}) eq "on" );

    my $hashtable = weechat::info_get_hashtable("irc_message_parse" => + { "message" => $callback_data });

    # $old_nick = $hashtable->{nick}
    my ($old_nick, $host) = split('!', $hashtable->{host});
    my $nick = $hashtable->{arguments};
    $nick =~ s/^.//;                            # remove leading ":"
    my ($user,undef) = split("@",$host);

    return weechat::WEECHAT_RC_OK if check_last_nick_host($nick,$host);

    add_record( $nick, $user, $host, $server);

    return weechat::WEECHAT_RC_OK;
}

sub irc_in2_whois_cb
{
    my ($signal, $callback, $callback_data) = @_;
    my ($server,undef) = split(',',$callback);

    my $ptr_buffer = '';

    my (undef, undef, undef, $nick, $user, $host, undef) = split(' ', $callback_data);
    my $msgbuffer_whois = weechat::config_string(weechat::config_get('irc.msgbuffer.whois'));

    # check for nick_regex
    if ( lc($options{'ignore_guest_nicks'}) eq "on" )
    {
        my $regex = $options{'guest_nick_regex'};
        return weechat::WEECHAT_RC_OK if( $nick =~ m/$regex/i );
    }

    my $complete_host = $user."@".$host;

    unless ( check_last_nick_host($nick,$complete_host) or lc($options{'ignore_whois'}) eq "on" )
    {
        add_record( $nick, $user, $complete_host, $server);
    }

    # output for /whois
    if ($msgbuffer_whois eq 'server')
    {
        $ptr_buffer = weechat::info_get('irc_buffer',$server);
#        $ptr_buffer = weechat::buffer_search('irc', 'server.' . $server);
    }
    elsif ($msgbuffer_whois eq 'weechat')
    {
        $ptr_buffer = weechat::buffer_search_main();
    }
    elsif  ($msgbuffer_whois eq 'current')
    {
        $ptr_buffer = weechat::current_buffer();
    }
    elsif ($msgbuffer_whois eq 'private')
    {
        $ptr_buffer = weechat::info_get('irc_buffer',$server.','.$nick);
        if ($ptr_buffer eq '')
        {
            $msgbuffer_whois = weechat::config_string(weechat::config_get('irc.look.msgbuffer_fallback'));
            $ptr_buffer = weechat::info_get('irc_buffer', $server) if ($msgbuffer_whois eq 'server');
        }
    }

    my $use_regex = 0;
    my $nicks_found = join( ", ", (get_nick_records('yes', 'nick', $nick, $server, $use_regex)));

    # only the given nick is returned?
    return weechat::WEECHAT_RC_OK if ($nicks_found eq $nick);

    # more than one nick was returned from sqlite
    my $prefix_network = weechat::prefix('network');
    my $color_chat_delimiter = weechat::color('chat_delimiters');
    my $color_chat_nick = weechat::color('chat_nick');

    my $output = weechat::color('chat_prefix_network').
                  weechat::prefix('network').
                  weechat::color('chat_delimiters').
                  "[".
                  weechat::color('chat_nick').
                  $SCRIPT_NAME.
                  weechat::color('chat_delimiters').
                  "] ".
                  $nicks_found;

    # fallback buffer..
    $ptr_buffer = weechat::buffer_search_main() unless ($ptr_buffer);

    # print /WHOIS with [stalker] line
    if ( $options{'tags'} ne '' )
    {
        weechat::print_date_tags($ptr_buffer,0,$options{'tags'},$output);
    }
    else
    {
        weechat::print($ptr_buffer,$output);
    }

    return weechat::WEECHAT_RC_OK;
}

# callback_data:   :nick!~user_2@host JOIN #channel
sub irc_in2_join_cb
{
    my ($signal, $callback, $callback_data) = @_;
    my ($server,$irc_signal) = split(',',$callback);
    my ($nick,$host,$channel) = ($callback_data =~ /\:(.*)\!(.*) JOIN (.*)/);

    $host =~ /(.*)\@/;
    my $user = $1;

    my $ptr_buffer = weechat::info_get('irc_buffer',$server . ',' . $channel);
    return weechat::WEECHAT_RC_OK unless ($ptr_buffer);
#    my $ptr_buffer = weechat::buffer_search('irc', $server . '.' . $channel);

    my $my_nick = weechat::buffer_get_string($ptr_buffer,'localvar_nick');
    # don't stalk yourself
    return weechat::WEECHAT_RC_OK if ($nick eq $my_nick);

    return weechat::WEECHAT_RC_OK if check_last_nick_host($nick,$host);

    # check for localvar "stalker"
    if ( lc($options{'use_localvar'}) eq "on" )
    {
        return weechat::WEECHAT_RC_OK if (not weechat::config_string_to_boolean(weechat::buffer_get_string($ptr_buffer, 'localvar_stalker')) );
    }

    add_record( $nick, $user, $host, $server);

    return weechat::WEECHAT_RC_OK;
}

# -----------------------------[ config ]-----------------------------------
sub init_config{

    foreach my $option (keys %options){
        if (!weechat::config_is_set_plugin($option)){
            weechat::config_set_plugin($option, $options{$option});
        }
        else{
            $options{$option} = weechat::config_get_plugin($option);
        }
    }
  # set help text for options
  if ( ($weechat_version ne '') && (weechat::info_get('version_number', '') >= 0x00030500) ) {    # v0.3.5
    foreach my $desc_options (keys %desc_options)
    {
      weechat::config_set_desc_plugin($desc_options,$desc_options{$desc_options});
    }
  }

}

sub toggle_config_by_set
{
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.$SCRIPT_NAME."), length($name));
    $options{$name} = $value;
# insert a refresh here
    return weechat::WEECHAT_RC_OK;
}

# -------------------------------[ init ]-------------------------------------
# first function called by a WeeChat-script.
weechat::register($SCRIPT_NAME, $SCRIPT_AUTHOR, $SCRIPT_VERSION,
                  $SCRIPT_LICENCE, $SCRIPT_DESC, '', '');

    $weechat_version = weechat::info_get('version_number', '');

    if ( ($weechat_version ne '') && (weechat::info_get('version_number', '') <= 0x00030400) )
    {
        weechat::print('',weechat::prefix('error') . 'You need WeeChat >= 0.3.4. Visit: www.weechat.org');
        weechat::command('',"/wait 1ms /perl unload $SCRIPT_NAME");
    }
    else
    {
        init_config();
        open_database();

        weechat::hook_command($SCRIPT_NAME, $SCRIPT_DESC, "host <host> [server] [-regex] || nick <nick> [server] [-regex] || scan [<server.channel>] || count",
                      "   host : look for hostname\n".
                      "   nick : look for nick\n".
                      "   scan : scan a channel (be careful; scanning large channels takes a while!)\n".
                      "          you should manually /WHO #channel first or use /quote PROTOCTL UHNAMES\n".
                      "   count: display the number of rows in database\n".
                      "\n\n".
                      "Stalker will add nick!user\@host to database monitoring JOIN/WHOIS/NICK messages.\n\n".
                      "\n".
                      "Monitor specific channels:\n".
                      "==========================\n".
                      "Set following option:\n".
                      "    /set plugins.var.perl.".$SCRIPT_NAME.".use_localvar \"on\"  (default: off)\n".
                      "Now you'll have to set a localvar for those channels to monitor:\n".
                      "    /buffer set localvar_set_stalker [value]\n".
                      "       values: \"on\", \"true\", \"t\", \"yes\", \"y\", \"1\")\n".
                      "\n".
                      "Regex:\n".
                      "======\n".
                      "$SCRIPT_NAME performs standard perl regular expression matching with option '-regex'.\n".
                      "Note that regex matching will not use SQLite indices, but will iterate over all rows, so it could be quite costly in terms of performance.\n".
                      "\n".
                      "Tags:\n".
                      "======\n".
                      $SCRIPT_NAME." can use tags to display messages. See documentation for most commonly used tags and add them in following option:\n".
                      "    /set plugins.var.perl.".$SCRIPT_NAME.".tags \"no_log\"\n".
                      "\n".
                      "Examples:\n".
                      "  search for nick 'nils_2'\n".
                      "    /".$SCRIPT_NAME." nick nils_2\n".
                      "  search for nick 'nils_2' on a different server named 'unknown'\n".
                      "    /".$SCRIPT_NAME." nick nils_2 unknown\n".
                      "  search for nicks starting with 'ni'\n".
                      "    /".$SCRIPT_NAME." nick \\bni.* -regex\n".
                      "  search all hosts located in '.de'\n".
                      "    /".$SCRIPT_NAME." host .*\\.de -regex\n".
                      "",
                      "count %-||".
                      "host %% %(irc_servers)|-regex %-||".
                      "nick %(nick) %(irc_servers)|-regex -regex %-||".
                      "scan %(buffers_names) %-", "stalker_command_cb", "");

        weechat::hook_config("plugins.var.perl.$SCRIPT_NAME.*", "toggle_config_by_set", "");
        weechat::hook_signal('*,irc_in2_join', 'irc_in2_join_cb', '');
        weechat::hook_signal('*,irc_in2_311', 'irc_in2_whois_cb', '');
        weechat::hook_signal('*,irc_in2_NICK', 'irc_in2_nick_cb', '');
    }
